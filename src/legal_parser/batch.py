import hashlib
import json
import logging
import os
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Severity, ValidationIssue
from .pipeline import process_file

LOGGER = logging.getLogger(__name__)


def process_corpus(input_dir: Path, output_dir: Path, limit: int | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    documents_dir = output_dir / "documents"
    documents_dir.mkdir(exist_ok=True)
    paths = sorted(input_dir.glob("context_*.json"), key=lambda path: path.name)
    if limit is not None:
        paths = paths[:limit]

    id_counts = Counter(_read_source_id(path) for path in paths)
    reports: list[dict[str, Any]] = []
    for path in paths:
        target = documents_dir / path.name
        source_hash = _file_hash(path)
        if _is_current(target, source_hash):
            previous = _read_json(target)
            reports.append({
                "file": path.name,
                "document_id": previous.get("document_id"),
                "status": "failed" if previous.get("status") == "failed" else "skipped",
                "resumed": True,
                "source_hash": source_hash,
                "issues": previous.get("issues", []),
                "stats": previous.get("stats", {}),
            })
            continue
        result = process_file(path)
        issues = list(result.issues)
        document = result.document
        if document and id_counts[document.document_id] > 1:
            issues.append(ValidationIssue("duplicate_id", f"duplicate id {document.document_id}"))
        effective_status = document.status if document else "failed"
        if any(issue.severity == Severity.ERROR for issue in issues):
            effective_status = "failed"
        if document:
            payload = document.to_dict()
            payload["source_hash"] = source_hash
            if issues:
                payload["issues"] = [asdict(issue) for issue in issues]
                if any(issue.severity == Severity.ERROR for issue in issues):
                    payload["status"] = "failed"
            _atomic_json(target, payload)
        reports.append({
            "file": path.name,
            "document_id": document.document_id if document else None,
            "status": effective_status,
            "source_hash": source_hash,
            "issues": [asdict(issue) for issue in issues],
            "stats": document.stats if document else {},
        })
        LOGGER.info("processed %s", path.name)

    summary = {
        "input_files": len(paths),
        "processed": sum(not report.get("resumed", False) for report in reports),
        "skipped": sum(report["status"] == "skipped" for report in reports),
        "failed": sum(report["status"] == "failed" for report in reports),
        "reports": reports,
    }
    _atomic_json(output_dir / "report.json", summary)
    _write_nodes_jsonl(documents_dir, output_dir / "nodes.jsonl")
    return summary


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_source_id(path: Path) -> int | None:
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
        return source.get("id") if isinstance(source, dict) and isinstance(source.get("id"), int) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _is_current(path: Path, source_hash: str) -> bool:
    try:
        return _read_json(path).get("source_hash") == source_hash
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    temporary.write_text(serialized, encoding="utf-8")
    os.replace(temporary, path)


def _write_nodes_jsonl(documents_dir: Path, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for document_path in sorted(documents_dir.glob("context_*.json")):
            document = _read_json(document_path)
            if document.get("status") == "failed":
                continue
            for node in document.get("nodes", []):
                if node.get("indexable"):
                    stream.write(json.dumps(node, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
