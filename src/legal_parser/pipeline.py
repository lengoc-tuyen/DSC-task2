import json
import re
from pathlib import Path
from typing import Any

from .lines import ARTICLE_PATTERN, LineType, reconstruct_lines, render_lines
from .models import FileResult, Node, Part, ProcessedDocument, Severity, ValidationIssue
from .normalize import normalize_passage, preservation_snapshot


def process_document(
    source: dict[str, Any], max_chunk_tokens: int = 900, chunk_overlap: int = 100
) -> ProcessedDocument:
    document_id = source.get("id")
    raw = source.get("passage")
    issues: list[ValidationIssue] = []
    if not isinstance(document_id, int):
        issues.append(ValidationIssue("invalid_id", "id must be an integer"))
        document_id = -1
    if not isinstance(raw, str):
        issues.append(ValidationIssue("invalid_passage", "passage must be a string"))
        raw = ""
    if not raw.strip():
        issues.append(ValidationIssue("empty_passage", "passage is empty"))
    normalized = normalize_passage(raw)
    lines = reconstruct_lines(normalized)
    clean = render_lines(lines)
    if preservation_snapshot(raw) != preservation_snapshot(clean):
        issues.append(ValidationIssue("legal_token_mismatch", "important legal tokens changed"))

    parts = _build_parts(document_id, clean, lines)
    nodes = _build_nodes(document_id, clean, lines, parts, max_chunk_tokens, chunk_overlap)
    if clean and not any(node.node_type == "article" for node in nodes):
        issues.append(ValidationIssue("no_articles", "no articles parsed", Severity.WARNING))
    status = "failed" if any(issue.severity == Severity.ERROR for issue in issues) else "ok"
    metadata = {key: source.get(key) for key in ("name", "link") if key in source}
    stats = {
        "raw_chars": len(raw),
        "clean_chars": len(clean),
        "parts": len(parts),
        "nodes": len(nodes),
        "indexable_nodes": sum(node.indexable for node in nodes),
    }
    return ProcessedDocument(
        document_id, raw, clean, metadata, tuple(parts), tuple(nodes), tuple(issues), status, stats
    )


def process_file(path: str | Path) -> FileResult:
    source_path = Path(path)
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError, OSError) as exc:
        return FileResult(None, (ValidationIssue("invalid_json", str(exc)),))
    if not isinstance(source, dict):
        return FileResult(None, (ValidationIssue("invalid_object", "JSON root must be an object"),))
    document = process_document(source)
    issues = list(document.issues)
    match = re.fullmatch(r"context_(\d+)\.json", source_path.name)
    if match and source.get("id") != int(match.group(1)):
        issues.append(ValidationIssue("filename_id_mismatch", "filename ID differs from object ID"))
        document = ProcessedDocument(
            document.document_id, document.raw_passage, document.clean_passage, document.metadata,
            document.parts, document.nodes, tuple(issues), "failed", document.stats
        )
    return FileResult(document, tuple(issues))


def _build_parts(document_id: int, clean: str, lines: tuple) -> list[Part]:
    boundaries = [0]
    for line in lines:
        if line.line_type == LineType.PART_HEADER and re.match(
            r"^(?:QUY CHẾ|PHỤ LỤC|DANH MỤC|BIỂU MẪU)(?:\s|$)", line.text
        ) and line.start_offset > 0:
            boundaries.append(line.start_offset)
    boundaries = sorted(set(boundaries))
    parts: list[Part] = []
    for ordinal, start in enumerate(boundaries, 1):
        end = boundaries[ordinal] - 1 if ordinal < len(boundaries) else len(clean)
        first = next((line for line in lines if line.start_offset >= start), None)
        part_type = "main" if ordinal == 1 else _part_type(first.text if first else "")
        parts.append(Part(f"doc:{document_id}:part:{ordinal}", part_type, first.text if ordinal > 1 and first else None, start, end))
    return parts


def _part_type(title: str) -> str:
    folded = title.casefold()
    for label, value in (("quy chế", "regulation"), ("phụ lục", "appendix"), ("danh mục", "list"), ("biểu mẫu", "form")):
        if folded.startswith(label):
            return value
    return "attachment"


def _build_nodes(document_id: int, clean: str, lines: tuple, parts: list[Part], max_tokens: int, overlap: int) -> list[Node]:
    nodes: list[Node] = []
    for part in parts:
        part_lines = [line for line in lines if part.start_offset <= line.start_offset < part.end_offset]
        structural, ancestry = _structural_nodes(document_id, part, clean, part_lines)
        nodes.extend(structural)
        article_positions = [index for index, line in enumerate(part_lines) if line.line_type == LineType.ARTICLE]
        for ordinal, position in enumerate(article_positions, 1):
            line = part_lines[position]
            article_lines = [line]
            for following in part_lines[position + 1:]:
                if following.line_type in {
                    LineType.ARTICLE, LineType.CHAPTER, LineType.SECTION,
                    LineType.PART_HEADER, LineType.ADMINISTRATIVE_NOISE,
                }:
                    break
                article_lines.append(following)
            end = article_lines[-1].end_offset
            match = ARTICLE_PATTERN.match(line.text)
            number = match.group(1) if match else None
            title = line.text[match.end():].strip() if match else None
            node_id = f"{part.part_id}:article:{ordinal}"
            administrative = line.line_type == LineType.ADMINISTRATIVE_NOISE
            content = clean[line.start_offset:end]
            parent_id, chapter_number, chapter_title = ancestry[position]
            embedding = _embedding_text(part, chapter_number, chapter_title, number, title, content)
            nodes.append(Node(
                node_id, document_id, part.part_id, parent_id, "article", content, embedding,
                line.start_offset, end, not administrative, chapter_number=chapter_number,
                chapter_title=chapter_title, article_number=number, article_title=title
            ))
            if len(content.split()) > max_tokens:
                nodes.extend(_chunk_article(nodes[-1], clean, max_tokens, overlap))
            nodes.extend(_article_children(nodes[-1], clean, article_lines))
        for ordinal, line in enumerate(part_lines, 1):
            if line.line_type == LineType.ADMINISTRATIVE_NOISE:
                nodes.append(Node(f"{part.part_id}:administrative:{ordinal}", document_id, part.part_id, None, "administrative", clean[line.start_offset:line.end_offset], "", line.start_offset, line.end_offset, False))
    return nodes


def _article_children(article: Node, clean: str, article_lines: list) -> list[Node]:
    children: list[Node] = []
    clause_positions = [
        index for index, line in enumerate(article_lines) if line.line_type == LineType.CLAUSE
    ]
    for clause_ordinal, position in enumerate(clause_positions, 1):
        line = article_lines[position]
        next_clause = clause_positions[clause_ordinal] if clause_ordinal < len(clause_positions) else len(article_lines)
        clause_lines = article_lines[position:next_clause]
        clause_match = re.match(r"^(\d+)\.\s+", line.text)
        clause_number = clause_match.group(1) if clause_match else None
        clause_id = f"{article.node_id}:clause:{clause_ordinal}"
        clause_end = clause_lines[-1].end_offset
        clause_content = clean[line.start_offset:clause_end]
        context = _node_context(article)
        children.append(Node(
            clause_id, article.document_id, article.part_id, article.node_id, "clause",
            clause_content, f"{context}\nKhoản {clause_number}: {clause_content}",
            line.start_offset, clause_end, True, chapter_number=article.chapter_number,
            chapter_title=article.chapter_title, article_number=article.article_number,
            article_title=article.article_title, clause_number=clause_number,
        ))
        point_positions = [
            index for index, child_line in enumerate(clause_lines)
            if child_line.line_type == LineType.POINT
        ]
        for point_ordinal, point_position in enumerate(point_positions, 1):
            point_line = clause_lines[point_position]
            next_point = point_positions[point_ordinal] if point_ordinal < len(point_positions) else len(clause_lines)
            point_lines = clause_lines[point_position:next_point]
            point_match = re.match(r"^([a-zđ])\)\s+", point_line.text, re.IGNORECASE)
            point_number = point_match.group(1).casefold() if point_match else None
            point_end = point_lines[-1].end_offset
            point_content = clean[point_line.start_offset:point_end]
            children.append(Node(
                f"{clause_id}:point:{point_ordinal}", article.document_id, article.part_id,
                clause_id, "point", point_content,
                f"{context}\nKhoản {clause_number}\nĐiểm {point_number}: {point_content}",
                point_line.start_offset, point_end, True, chapter_number=article.chapter_number,
                chapter_title=article.chapter_title, article_number=article.article_number,
                article_title=article.article_title, clause_number=clause_number,
                point_number=point_number,
            ))
    return children


def _node_context(article: Node) -> str:
    values = [
        f"Chương {article.chapter_number}: {article.chapter_title or ''}".rstrip()
        if article.chapter_number else None,
        f"Điều {article.article_number}: {article.article_title or ''}".rstrip()
        if article.article_number else None,
    ]
    return "\n".join(value for value in values if value)


def _structural_nodes(document_id: int, part: Part, clean: str, part_lines: list) -> tuple[list[Node], dict[int, tuple[str | None, str | None, str | None]]]:
    output: list[Node] = []
    ancestry: dict[int, tuple[str | None, str | None, str | None]] = {}
    chapter_id = None
    chapter_number = None
    chapter_title = None
    section_id = None
    chapter_count = 0
    section_count = 0
    for position, line in enumerate(part_lines):
        if line.line_type == LineType.CHAPTER:
            chapter_count += 1
            match = re.match(r"^Chương\s+([IVXLCDM0-9]+)\b\s*(.*)", line.text, re.IGNORECASE)
            chapter_number = match.group(1) if match else None
            chapter_title = match.group(2).strip(" .:") if match and match.group(2) else None
            chapter_id = f"{part.part_id}:chapter:{chapter_count}"
            section_id = None
            output.append(Node(
                chapter_id, document_id, part.part_id, None, "chapter",
                clean[line.start_offset:line.end_offset], line.text, line.start_offset, line.end_offset,
                chapter_number=chapter_number, chapter_title=chapter_title
            ))
        elif line.line_type == LineType.SECTION:
            section_count += 1
            section_id = f"{part.part_id}:section:{section_count}"
            output.append(Node(
                section_id, document_id, part.part_id, chapter_id, "section",
                clean[line.start_offset:line.end_offset], line.text, line.start_offset, line.end_offset,
                chapter_number=chapter_number, chapter_title=chapter_title
            ))
        ancestry[position] = (section_id or chapter_id, chapter_number, chapter_title)
    return output, ancestry


def _embedding_text(part: Part, chapter_number: str | None, chapter_title: str | None, number: str | None, title: str | None, content: str) -> str:
    prefix = [
        part.part_title,
        f"Chương {chapter_number}: {chapter_title or ''}".rstrip() if chapter_number else None,
        f"Điều {number}: {title}" if number else None,
    ]
    return "\n".join(value for value in (*prefix, content) if value)


def _chunk_article(article: Node, clean: str, max_tokens: int, overlap: int) -> list[Node]:
    if max_tokens <= 0 or overlap < 0 or overlap >= max_tokens:
        raise ValueError("chunk settings require max_tokens > overlap >= 0")
    token_matches = list(re.finditer(r"\S+", article.content))
    chunks: list[Node] = []
    step = max_tokens - overlap
    for ordinal, start_index in enumerate(range(0, len(token_matches), step), 1):
        selected = token_matches[start_index : start_index + max_tokens]
        if not selected:
            break
        start = article.start_offset + selected[0].start()
        end = article.start_offset + selected[-1].end()
        content = clean[start:end]
        chunks.append(Node(
            f"{article.node_id}:chunk:{ordinal}", article.document_id, article.part_id, article.node_id,
            "chunk", content, f"{article.embedding_text.splitlines()[0]}\n{content}", start, end, True,
            article_number=article.article_number, article_title=article.article_title
        ))
        if start_index + max_tokens >= len(token_matches):
            break
    return chunks
