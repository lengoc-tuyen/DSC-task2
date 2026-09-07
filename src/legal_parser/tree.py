import re
from dataclasses import dataclass
from typing import Any


_NATIONAL_HEADER = re.compile(
    r"CỘNG\s+(?:HÒA|HOÀ)\s+(?:XÃ|XÁ)\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM",
    re.IGNORECASE,
)
_MOTTO = re.compile(
    r"Độc\s+lập\s*-\s*Tự\s+do\s*-\s*Hạnh\s+phúc", re.IGNORECASE
)
_DOCUMENT_NUMBER = re.compile(r"\bSố\s*:\s*([0-9]+/[A-ZĐ0-9./-]+)", re.IGNORECASE)
_DATE = re.compile(r"\bngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}\b", re.IGNORECASE)
_PLACE_DATE = re.compile(
    r"(?P<place>[A-ZÀ-ỸĐ][a-zà-ỹđ]+(?:\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+){0,3}),\s*"
    r"(?P<date>ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})",
    re.IGNORECASE,
)
_DOCUMENT_TYPE = re.compile(
    r"(?m)^(LUẬT|BỘ LUẬT|PHÁP LỆNH|NGHỊ QUYẾT|NGHỊ ĐỊNH|QUYẾT ĐỊNH|"
    r"THÔNG TƯ|CHỈ THỊ|CÔNG VĂN|QUY CHẾ|KẾ HOẠCH|THÔNG BÁO)\b"
)
_LEGAL_ANCHOR = re.compile(
    r"(?:Căn cứ|Chiếu theo|Xét|Theo đề nghị|Kính gửi|(?m:^Điều\s+\d+)|QUYẾT NGHỊ\s*:)",
    re.IGNORECASE,
)
_SEPARATOR = re.compile(r"^-{3,}$")
_SIGNER_LINE = re.compile(
    r"^(?:PHÓ\s+)?(?:CHỦ\s+TỊCH|THỦ\s+TƯỚNG|BỘ\s+TRƯỞNG|BỘ\s+TRƯỞNG\s+BỘ|"
    r"TỔNG\s+CỤC\s+TRƯỞNG|CỤC\s+TRƯỞNG|VIỆN\s+TRƯỞNG|CHÁNH\s+ÁN|GIÁM\s+ĐỐC)\b",
    re.IGNORECASE,
)
_TITLE_CASE_WORD = re.compile(r"^[A-ZÀ-ỸĐ][a-zà-ỹđ]+$")

TREE_SCHEMA_VERSION = "2.0"


@dataclass(frozen=True)
class HeaderExtraction:
    passage: str
    removed_text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class StructuralHeading:
    start: int
    end: int
    content: str | None
    title: str | None


def extract_document_header(passage: str) -> HeaderExtraction:
    prefix_window = passage[: min(len(passage), 6000)]
    national = _NATIONAL_HEADER.search(prefix_window)
    motto = _MOTTO.search(prefix_window)
    number = _DOCUMENT_NUMBER.search(prefix_window)
    date = _DATE.search(prefix_window)
    place_date = _PLACE_DATE.search(prefix_window)
    document_type = _DOCUMENT_TYPE.search(prefix_window)
    anchor = _LEGAL_ANCHOR.search(prefix_window)
    administrative_prefix = passage[: national.start()] if national else ""
    near_number = bool(number and motto and 0 <= number.start() - motto.end() <= 500)
    near_date = bool(date and motto and 0 <= date.start() - motto.end() <= 800)
    has_masthead = bool(
        national and motto and (
            near_number or near_date or national.start() == 0
            or _looks_administrative_prefix(administrative_prefix)
        )
    )

    body_start = 0
    if has_masthead:
        masthead_end = motto.end() if motto else national.end() if national else 0
        candidates = [
            match.start() for match in (document_type, anchor)
            if match and match.start() >= masthead_end
        ]
        if candidates:
            body_start = min(candidates)
        else:
            body_start = max(match.end() for match in (national, motto, number, date) if match)
    removed = passage[:body_start].strip()
    substantive = passage[body_start:].strip()
    issuer = _extract_issuer(passage[: national.start()] if national else removed)
    title = _extract_title(prefix_window, document_type, anchor)
    metadata = {
        "issuing_agency": issuer,
        "national_header": national.group(0) if national else None,
        "motto": motto.group(0) if motto else None,
        "document_number": number.group(1) if number else None,
        "issued_place": _clean_place(place_date.group("place")) if place_date else None,
        "issued_date": (place_date.group("date") if place_date else date.group(0) if date else None),
        "document_type": document_type.group(1) if document_type else None,
        "title": title,
    }
    return HeaderExtraction(substantive, removed, metadata)


def build_legal_tree(document: dict[str, Any]) -> dict[str, Any]:
    clean = document.get("clean_passage") or ""
    raw = document.get("raw_passage") or clean
    clean_header = extract_document_header(clean)
    raw_header = extract_document_header(raw)
    source_metadata = document.get("metadata") or {}
    metadata = {
        "name": source_metadata.get("name"),
        "link": source_metadata.get("link"),
        **raw_header.metadata,
    }
    nodes = document.get("nodes") or []
    nodes_by_id = {node.get("node_id"): node for node in nodes if node.get("node_id")}
    parts = [
        _build_part(part, clean, nodes, nodes_by_id, index)
        for index, part in enumerate(document.get("parts") or [], 1)
    ]
    preamble_text = _extract_preamble(clean_header.passage)
    return {
        "schema_version": TREE_SCHEMA_VERSION,
        "document_id": document.get("document_id"),
        "metadata": metadata,
        "administrative_header": {
            "removed": bool(clean_header.removed_text),
            "removed_char_count": len(clean_header.removed_text),
        },
        "preamble": {
            "text": preamble_text or None,
            "legal_bases": _extract_segments(preamble_text, ("căn cứ", "chiếu theo")),
            "proposals": _extract_segments(preamble_text, ("xét", "theo đề nghị")),
            "enactment_formula": _extract_enactment_formula(preamble_text),
        },
        "passage": clean_header.passage,
        "tree": {"parts": parts},
        "issues": document.get("issues") or [],
        "status": document.get("status") or "failed",
        "source_hash": document.get("source_hash"),
        "stats": _tree_stats(parts, len(clean), len(clean_header.passage)),
    }


def clean_repeated_header(document: dict[str, Any]) -> dict[str, Any]:
    passage = document.get("passage") or ""
    extraction = extract_document_header(passage)
    if not extraction.removed_text:
        return document
    metadata = {
        **(document.get("metadata") or {}),
        **{key: value for key, value in extraction.metadata.items() if value is not None},
    }
    cleaned_parts = [_clean_part_header(part) for part in document.get("tree", {}).get("parts", [])]
    removed_count = int(document.get("administrative_header", {}).get("removed_char_count") or 0)
    return {
        **document,
        "metadata": metadata,
        "administrative_header": {
            "removed": True,
            "removed_char_count": removed_count + len(extraction.removed_text),
        },
        "passage": extraction.passage,
        "tree": {"parts": cleaned_parts},
        "stats": {**(document.get("stats") or {}), "passage_chars": len(extraction.passage)},
    }


def _clean_part_header(part: dict[str, Any]) -> dict[str, Any]:
    direct = part.get("direct_text")
    clean_direct = extract_document_header(direct).passage if direct else direct
    blocks = []
    for block in part.get("unstructured_blocks", []):
        content = block.get("content") or ""
        blocks.append({**block, "content": extract_document_header(content).passage})
    return {**part, "direct_text": clean_direct, "unstructured_blocks": blocks}


def _build_part(
    part: dict[str, Any], clean: str, nodes: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]], ordinal: int,
) -> dict[str, Any]:
    part_id = part.get("part_id")
    part_nodes = [node for node in nodes if node.get("part_id") == part_id]
    chapters: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    articles: list[dict[str, Any]] = []
    chapter_map: dict[str, dict[str, Any]] = {}
    section_map: dict[str, dict[str, Any]] = {}
    heading_map = _structural_headings(part_nodes, clean)

    for node in part_nodes:
        if node.get("node_type") == "chapter":
            chapter = _chapter(node, heading_map)
            chapters.append(chapter)
            chapter_map[node["node_id"]] = chapter
    for node in part_nodes:
        if node.get("node_type") == "section":
            section = _section(node, heading_map)
            section_map[node["node_id"]] = section
            parent = chapter_map.get(node.get("parent_id"))
            (parent["sections"] if parent else sections).append(section)
    for node in part_nodes:
        if node.get("node_type") != "article":
            continue
        article = _article(node, part_nodes, nodes_by_id)
        parent_id = node.get("parent_id")
        if parent_id in section_map:
            section_map[parent_id]["articles"].append(article)
        elif parent_id in chapter_map:
            chapter_map[parent_id]["articles"].append(article)
        else:
            articles.append(article)

    start = max(0, int(part.get("start_offset") or 0))
    end = min(len(clean), int(part.get("end_offset") or len(clean)))
    top_intervals = [
        _node_interval(node, heading_map)
        for node in part_nodes
        if node.get("node_type") in {"chapter", "section", "article", "administrative"}
    ]
    direct_text = _subtract_absolute(clean, start, end, top_intervals)
    if ordinal == 1:
        direct_text = extract_document_header(direct_text).passage
    has_structure = bool(chapters or sections or articles)
    unstructured = ([{"block_id": f"{part_id}:block:1", "content": direct_text, "indexable": True}]
                    if direct_text and not has_structure else [])
    return {
        "part_id": part_id,
        "part_type": part.get("part_type") or "unknown",
        "part_title": part.get("part_title"),
        "reference": None,
        "direct_text": direct_text if direct_text and has_structure else None,
        "chapters": chapters,
        "sections": sections,
        "articles": articles,
        "unstructured_blocks": unstructured,
    }


def _chapter(node: dict[str, Any], heading_map: dict[str, StructuralHeading]) -> dict[str, Any]:
    heading = heading_map.get(node.get("node_id"))
    return {
        "chapter_id": node.get("node_id"), "number": node.get("chapter_number"),
        "title": (heading.title if heading and heading.title else node.get("chapter_title")),
        "content": (heading.content if heading and heading.content else node.get("content") or None),
        "sections": [], "articles": [],
    }


def _section(node: dict[str, Any], heading_map: dict[str, StructuralHeading]) -> dict[str, Any]:
    heading = heading_map.get(node.get("node_id"))
    content = heading.content if heading and heading.content else node.get("content") or ""
    number, title = _parse_section_heading(content)
    return {
        "section_id": node.get("node_id"), "number": number,
        "title": title,
        "content": content or None, "articles": [],
    }


def _article(node: dict[str, Any], part_nodes: list[dict[str, Any]], nodes_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clauses = [child for child in part_nodes if child.get("node_type") == "clause" and child.get("parent_id") == node.get("node_id")]
    direct_points = [child for child in part_nodes if child.get("node_type") == "point" and child.get("parent_id") == node.get("node_id")]
    return {
        "article_id": node.get("node_id"), "number": node.get("article_number"),
        "title": node.get("article_title"),
        "content": _direct_node_content(node, clauses + direct_points),
        "clauses": [_clause(child, part_nodes) for child in clauses],
        "points": [_point(child) for child in direct_points],
    }


def _clause(node: dict[str, Any], part_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    points = [child for child in part_nodes if child.get("node_type") == "point" and child.get("parent_id") == node.get("node_id")]
    return {
        "clause_id": node.get("node_id"), "number": node.get("clause_number"),
        "content": _direct_node_content(node, points),
        "points": [_point(child) for child in points],
    }


def _point(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "point_id": node.get("node_id"), "label": node.get("point_number"),
        "content": node.get("content") or None, "children": [],
    }


def _direct_node_content(node: dict[str, Any], children: list[dict[str, Any]]) -> str | None:
    content = node.get("content") or ""
    start = int(node.get("start_offset") or 0)
    intervals = [
        (max(0, int(child.get("start_offset") or 0) - start), max(0, int(child.get("end_offset") or 0) - start))
        for child in children
    ]
    return _subtract_relative(content, intervals) or None


def _subtract_absolute(text: str, start: int, end: int, intervals: list[tuple[int, int]]) -> str:
    relative = [(max(0, left - start), min(end - start, right - start)) for left, right in intervals if right > start and left < end]
    return _subtract_relative(text[start:end], relative)


def _subtract_relative(text: str, intervals: list[tuple[int, int]]) -> str:
    cursor = 0
    chunks: list[str] = []
    for start, end in sorted(intervals):
        if start > cursor:
            chunks.append(text[cursor:start])
        cursor = max(cursor, end)
    chunks.append(text[cursor:])
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()


def _extract_issuer(prefix: str) -> str | None:
    lines = [line.strip() for line in prefix.splitlines() if line.strip() and not _SEPARATOR.fullmatch(line.strip())]
    return " ".join(lines[:3]) or None


def _looks_administrative_prefix(prefix: str) -> bool:
    value = " ".join(line.strip() for line in prefix.splitlines() if line.strip() and not _SEPARATOR.fullmatch(line.strip()))
    letters = [character for character in value if character.isalpha()]
    return len(value) <= 200 and bool(letters) and all(character.isupper() for character in letters)


def _clean_place(value: str) -> str:
    words = value.strip().split()
    trailing: list[str] = []
    for word in reversed(words):
        if _TITLE_CASE_WORD.fullmatch(word):
            trailing.append(word)
        else:
            break
    return " ".join(reversed(trailing)) if trailing else value.strip()


def _extract_title(text: str, document_type: re.Match[str] | None, anchor: re.Match[str] | None) -> str | None:
    if not document_type:
        return None
    end = anchor.start() if anchor and anchor.start() > document_type.end() else min(len(text), document_type.end() + 500)
    candidate = text[document_type.end():end]
    lines = [_normalize_inline_spaces(line) for line in candidate.splitlines()]
    filtered: list[str] = []
    for line in lines:
        normalized = line.strip(" .:-")
        if not normalized or _SEPARATOR.fullmatch(normalized):
            continue
        if _SIGNER_LINE.match(normalized):
            break
        filtered.append(normalized)
    title = " ".join(filtered).strip()
    return re.sub(r"\s+", " ", title) or None


def _extract_preamble(passage: str) -> str:
    article = re.search(r"(?m)^Điều\s+\d+", passage, re.IGNORECASE)
    return passage[: article.start()].strip() if article else ""


def _extract_segments(text: str, prefixes: tuple[str, ...]) -> list[str]:
    output: list[str] = []
    prefix_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(prefix) for prefix in prefixes) + r")\b",
        re.IGNORECASE,
    )
    for segment in re.split(r";\s*", text):
        match = prefix_pattern.search(segment)
        if match:
            output.append(segment[match.start():].strip())
    return output


def _extract_enactment_formula(text: str) -> str | None:
    match = re.search(r"(?im)^(QUYẾT NGHỊ|QUYẾT ĐỊNH|BAN HÀNH)\s*:?\s*$", text)
    return match.group(0).strip() if match else None


def _structural_headings(part_nodes: list[dict[str, Any]], clean: str) -> dict[str, StructuralHeading]:
    headings: dict[str, StructuralHeading] = {}
    indexed_nodes = [node for node in part_nodes if node.get("node_type") in {"chapter", "section", "article", "administrative"}]
    for node in part_nodes:
        if node.get("node_type") not in {"chapter", "section"}:
            continue
        start = max(0, int(node.get("start_offset") or 0))
        node_content = node.get("content") or ""
        located = clean.find(node_content, max(0, start - 128), min(len(clean), start + len(node_content) + 128))
        if located >= 0:
            start = located
        base_end = max(start, int(node.get("end_offset") or start))
        if located >= 0:
            base_end = start + len(node_content)
        next_start = min(
            (
                _located_node_start(clean, other)
                for other in indexed_nodes
                if other is not node and _located_node_start(clean, other) > start
            ),
            default=base_end,
        )
        full_end = next_start if next_start > base_end else base_end
        content = clean[start:full_end].strip() or None
        title = _structural_title(node.get("node_type") or "", content)
        headings[node.get("node_id")] = StructuralHeading(
            start=start,
            end=full_end if title else base_end,
            content=content if content else None,
            title=title,
        )
    return headings


def _located_node_start(clean: str, node: dict[str, Any]) -> int:
    stated = max(0, int(node.get("start_offset") or 0))
    content = node.get("content") or ""
    located = clean.find(content, max(0, stated - 128), min(len(clean), stated + len(content) + 128))
    return located if located >= 0 else stated


def _node_interval(
    node: dict[str, Any], heading_map: dict[str, StructuralHeading]
) -> tuple[int, int]:
    heading = heading_map.get(node.get("node_id"))
    if heading:
        return heading.start, heading.end
    return int(node.get("start_offset") or 0), int(node.get("end_offset") or 0)


def _structural_title(node_type: str, content: str | None) -> str | None:
    if not content:
        return None
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return None
    if node_type == "chapter":
        if len(lines) > 1:
            return " ".join(lines[1:]).strip(" .:") or None
        return None
    if node_type == "section":
        _, title = _parse_section_heading(content)
        return title
    return None


def _parse_section_heading(content: str) -> tuple[str | None, str | None]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    first = lines[0] if lines else ""
    match = re.match(r"^(?:Mục|Tiểu mục)\s+([IVXLCDM0-9]+)\b\s*(.*)", first, re.I)
    trailing_title = " ".join(lines[1:]).strip(" .:")
    inline_title = match.group(2).strip(" .:") if match and match.group(2) else ""
    number = match.group(1) if match else None
    title = trailing_title or inline_title or None
    return number, title


def _normalize_inline_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _tree_stats(parts: list[dict[str, Any]], source_chars: int, passage_chars: int) -> dict[str, int]:
    counts = {"parts": len(parts), "chapters": 0, "sections": 0, "articles": 0, "clauses": 0, "points": 0}
    for part in parts:
        counts["chapters"] += len(part["chapters"])
        counts["sections"] += len(part["sections"]) + sum(len(chapter["sections"]) for chapter in part["chapters"])
        all_sections = part["sections"] + [section for chapter in part["chapters"] for section in chapter["sections"]]
        all_articles = part["articles"] + [article for chapter in part["chapters"] for article in chapter["articles"]] + [article for section in all_sections for article in section["articles"]]
        counts["articles"] += len(all_articles)
        counts["clauses"] += sum(len(article["clauses"]) for article in all_articles)
        counts["points"] += sum(len(article["points"]) + sum(len(clause["points"]) for clause in article["clauses"]) for article in all_articles)
    return {"source_chars": source_chars, "passage_chars": passage_chars, **counts}
