#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path

from legal_parser.batch import process_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and parse Vietnamese legal documents")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    summary = process_corpus(args.input_dir, args.output_dir, args.limit)
    print(
        f"input={summary['input_files']} processed={summary['processed']} "
        f"skipped={summary['skipped']} failed={summary['failed']}"
    )


if __name__ == "__main__":
    main()
