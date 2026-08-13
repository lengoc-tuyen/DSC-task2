#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path

from legal_parser.tree import extract_document_header


def validate(directory: Path) -> dict:
    counts = Counter()
    invalid_files: list[str] = []
    masthead_files: list[str] = []
    failed_files: list[str] = []
    for path in sorted(directory.glob("context_*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("schema_version") != "2.0" or not isinstance(document.get("tree", {}).get("parts"), list):
                invalid_files.append(path.name)
                continue
            counts["documents"] += 1
            counts.update(document.get("stats") or {})
            if extract_document_header(document.get("passage") or "").removed_text:
                masthead_files.append(path.name)
            if document.get("status") == "failed":
                failed_files.append(path.name)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
            invalid_files.append(path.name)
    return {
        "schema_version": "2.0",
        "counts": dict(counts),
        "invalid_files": invalid_files,
        "masthead_files": masthead_files,
        "failed_files": failed_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate schema v2 legal tree corpus")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.directory)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
