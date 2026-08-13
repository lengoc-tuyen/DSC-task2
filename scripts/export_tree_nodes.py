#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterator


def iter_nodes(document: dict[str, Any]) -> Iterator[dict[str, Any]]:
    document_id = document.get("document_id")
    metadata = document.get("metadata") or {}
    document_context = [metadata.get("document_type"), metadata.get("document_number"), metadata.get("title")]
    for part in document.get("tree", {}).get("parts", []):
        part_context = [part.get("part_title")]
        for block in part.get("unstructured_blocks", []):
            yield _node(document_id, block.get("block_id"), "block", block.get("content"), document_context + part_context)
        for article in part.get("articles", []):
            yield from _article_nodes(document_id, article, document_context + part_context)
        for section in part.get("sections", []):
            yield from _section_nodes(document_id, section, document_context + part_context)
        for chapter in part.get("chapters", []):
            chapter_context = part_context + [_label("Chương", chapter.get("number"), chapter.get("title"))]
            for article in chapter.get("articles", []):
                yield from _article_nodes(document_id, article, document_context + chapter_context)
            for section in chapter.get("sections", []):
                yield from _section_nodes(document_id, section, document_context + chapter_context)


def _section_nodes(document_id: int, section: dict[str, Any], context: list[str | None]) -> Iterator[dict[str, Any]]:
    section_context = context + [_label("Mục", section.get("number"), section.get("title"))]
    for article in section.get("articles", []):
        yield from _article_nodes(document_id, article, section_context)


def _article_nodes(document_id: int, article: dict[str, Any], context: list[str | None]) -> Iterator[dict[str, Any]]:
    article_label = _label("Điều", article.get("number"), article.get("title"))
    article_context = context + [article_label]
    content = article.get("content")
    if content:
        yield _node(document_id, article.get("article_id"), "article", content, article_context)
    for point in article.get("points", []):
        yield _node(document_id, point.get("point_id"), "point", point.get("content"), article_context)
    for clause in article.get("clauses", []):
        clause_context = article_context + [_label("Khoản", clause.get("number"), None)]
        if clause.get("content"):
            yield _node(document_id, clause.get("clause_id"), "clause", clause.get("content"), clause_context)
        for point in clause.get("points", []):
            yield _node(document_id, point.get("point_id"), "point", point.get("content"), clause_context)


def _node(document_id: int, node_id: str, node_type: str, content: str | None, context: list[str | None]) -> dict[str, Any]:
    path = [value for value in context if value]
    return {
        "node_id": node_id,
        "document_id": document_id,
        "node_type": node_type,
        "path": path,
        "content": content,
        "embedding_text": "\n".join([*path, content] if content else path),
    }


def _label(kind: str, number: str | None, title: str | None) -> str | None:
    if not number and not title:
        return None
    return f"{kind} {number or ''}{': ' + title if title else ''}".strip()


def export(documents_dir: Path, output: Path) -> int:
    temporary = output.with_suffix(output.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8") as stream:
        for path in sorted(documents_dir.glob("context_*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("status") == "failed":
                continue
            for node in iter_nodes(document):
                if node["content"]:
                    stream.write(json.dumps(node, ensure_ascii=False, separators=(",", ":")) + "\n")
                    count += 1
    os.replace(temporary, output)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export retrieval nodes from schema v2 legal trees")
    parser.add_argument("documents_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print({"nodes": export(args.documents_dir, args.output)})


if __name__ == "__main__":
    main()
