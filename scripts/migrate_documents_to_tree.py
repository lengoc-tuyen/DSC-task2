#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from legal_parser.tree import build_legal_tree, clean_repeated_header


def migrate(directory: Path, limit: int | None = None) -> dict[str, int]:
    paths = sorted(directory.glob("context_*.json"))
    if limit is not None:
        paths = paths[:limit]
    migrated = 0
    skipped = 0
    failed = 0
    for path in paths:
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
            if source.get("schema_version") == "2.0":
                result = clean_repeated_header(source)
                if result == source:
                    skipped += 1
                    continue
            else:
                result = build_legal_tree(source)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            json.loads(temporary.read_text(encoding="utf-8"))
            os.replace(temporary, path)
            migrated += 1
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            failed += 1
    return {"files": len(paths), "migrated": migrated, "skipped": skipped, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate flat legal documents to schema v2 tree")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    print(migrate(args.directory, args.limit))


if __name__ == "__main__":
    main()
