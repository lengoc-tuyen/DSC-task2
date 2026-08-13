#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from legal_parser.pipeline import process_file
from legal_parser.tree import build_legal_tree


def rebuild(input_dir: Path, output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(input_dir.glob("context_*.json"))
    processed = 0
    failed = 0
    for path in paths:
        result = process_file(path)
        if result.document is None:
            failed += 1
            continue
        tree = build_legal_tree(result.document.to_dict())
        tree["source_hash"] = path.name
        target = output_dir / path.name
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, target)
        processed += 1
    return {"files": len(paths), "processed": processed, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild schema v2 trees from original context JSON")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(rebuild(args.input_dir, args.output_dir))


if __name__ == "__main__":
    main()
