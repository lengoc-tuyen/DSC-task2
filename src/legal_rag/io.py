import json
from pathlib import Path
from typing import Any


def load_questions(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("question file must be a JSON object")
    questions: dict[str, str] = {}
    for raw_id, record in value.items():
        question = record.get("question") if isinstance(record, dict) else None
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"question {raw_id!r} is missing a non-empty question")
        questions[str(raw_id)] = question.strip()
    return questions


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path: Path, records) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    temporary.replace(path)
    return count


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
