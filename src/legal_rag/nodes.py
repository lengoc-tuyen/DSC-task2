import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from .models import RetrievalNode


def build_retrieval_nodes(document: dict[str, Any], max_words: int = 900, overlap_units: int = 1) -> list[RetrievalNode]:
    if max_words <= 0:
        raise ValueError("max_words must be positive")
    if overlap_units < 0:
        raise ValueError("overlap_units cannot be negative")
    if document.get("status") == "failed":
        return []
    metadata = document.get("metadata") or {}
    document_path = tuple(value for value in (_document_label(metadata), metadata.get("title")) if value)
    output: list[RetrievalNode] = []
    for part in document.get("tree", {}).get("parts", []):
        part_path = document_path + ((part.get("part_title"),) if part.get("part_title") else ())
        for block in part.get("unstructured_blocks", []):
            output.extend(_text_chunks(document, part, block.get("block_id"), block.get("content"), part_path, max_words))
        for article in part.get("articles", []):
            output.extend(_article_chunks(document, part, article, part_path, max_words, overlap_units))
        for section in part.get("sections", []):
            output.extend(_section_articles(document, part, section, part_path, max_words, overlap_units))
        for chapter in part.get("chapters", []):
            chapter_path = part_path + (_label("Chương", chapter.get("number"), chapter.get("title")),)
            for article in chapter.get("articles", []):
                output.extend(_article_chunks(document, part, article, chapter_path, max_words, overlap_units))
            for section in chapter.get("sections", []):
                output.extend(_section_articles(document, part, section, chapter_path, max_words, overlap_units))
    return output


def load_nodes(path: Path) -> list[RetrievalNode]:
    return list(iter_nodes(path))


def iter_nodes(path: Path) -> Iterator[RetrievalNode]:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield RetrievalNode.from_dict(json.loads(line))


def write_nodes(nodes: Iterable[RetrievalNode], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8") as stream:
        for node in nodes:
            stream.write(json.dumps(node.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    temporary.replace(path)
    return count


def _section_articles(document, part, section, path, max_words, overlap):
    section_path = path + (_label("Mục", section.get("number"), section.get("title")),)
    return [node for article in section.get("articles", []) for node in _article_chunks(document, part, article, section_path, max_words, overlap)]


def _article_chunks(document, part, article, path, max_words, overlap):
    article_path = path + (_label("Điều", article.get("number"), article.get("title")),)
    units = []
    if article.get("content"):
        units.append((article.get("content"), None, ()))
    for clause in article.get("clauses", []):
        content = "\n".join(value for value in [clause.get("content"), *[point.get("content") for point in clause.get("points", [])]] if value)
        units.append((content, clause.get("number"), tuple(point.get("label") for point in clause.get("points", []) if point.get("label"))))
    for point in article.get("points", []):
        units.append((point.get("content"), None, (point.get("label"),)))
    chunks = _group_units(_split_oversize_units(units, max_words), max_words, overlap)
    output = []
    for index, chunk in enumerate(chunks, 1):
        contents = [unit[0] for unit in chunk if unit[0]]
        clauses = tuple(unit[1] for unit in chunk if unit[1])
        points = tuple(label for unit in chunk for label in unit[2] if label)
        content = "\n".join(contents)
        chunk_path = article_path + tuple(f"Khoản {number}" for number in clauses)
        output.append(RetrievalNode(
            f"{article.get('article_id')}:retrieval:{index}", document.get("document_id"), part.get("part_id"),
            "article_chunk", content, "\n".join((*chunk_path, content)), chunk_path,
            article.get("article_id"), article.get("number"), clauses, points, document.get("metadata") or {},
        ))
    return output


def _group_units(units, max_words, overlap):
    if not units:
        return []
    chunks = []
    current = []
    words = 0
    for unit in units:
        size = len((unit[0] or "").split())
        if current and words + size > max_words:
            chunks.append(current)
            current = current[-min(overlap, len(current)):] if overlap else []
            words = sum(len((item[0] or "").split()) for item in current)
            if current and words + size > max_words:
                current = []
                words = 0
        current.append(unit)
        words += size
    if current:
        chunks.append(current)
    return chunks


def _split_oversize_units(units, max_words):
    expanded = []
    for content, clause, points in units:
        words = (content or "").split()
        if len(words) <= max_words:
            expanded.append((content, clause, points))
            continue
        for start in range(0, len(words), max_words):
            expanded.append((" ".join(words[start:start + max_words]), clause, points))
    return expanded


def _text_chunks(document, part, node_id, content, path, max_words):
    words = (content or "").split()
    result = []
    for index, start in enumerate(range(0, len(words), max_words), 1):
        text = " ".join(words[start:start + max_words])
        result.append(RetrievalNode(f"{node_id}:retrieval:{index}", int(document.get("document_id")), str(part.get("part_id") or ""), "unstructured", text, "\n".join((*path, text)), path, metadata=document.get("metadata") or {}))
    return result


def _document_label(metadata):
    return " ".join(value for value in (metadata.get("document_type"), metadata.get("document_number")) if value) or metadata.get("name")


def _label(kind, number, title):
    return f"{kind} {number or ''}{': ' + title if title else ''}".strip()
