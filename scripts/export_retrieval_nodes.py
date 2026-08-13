#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_rag.nodes import build_retrieval_nodes, write_nodes


def iter_nodes(documents_dir: Path, max_words: int, overlap_units: int):
    for path in sorted(documents_dir.glob("context_*.json")):
        with path.open(encoding="utf-8") as stream:
            document = json.load(stream)
        yield from build_retrieval_nodes(document, max_words, overlap_units)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export article-family retrieval chunks from legal tree JSON files")
    parser.add_argument("--documents-dir", type=Path, default=Path("outputs/cleaned/documents"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/rag/nodes.jsonl"))
    parser.add_argument("--max-words", type=int, default=900)
    parser.add_argument("--overlap-units", type=int, default=1)
    args = parser.parse_args()
    count = write_nodes(iter_nodes(args.documents_dir, args.max_words, args.overlap_units), args.output)
    print(json.dumps({"output": str(args.output), "nodes": count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
