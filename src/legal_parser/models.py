from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass(frozen=True)
class Part:
    part_id: str
    part_type: str
    part_title: str | None
    start_offset: int
    end_offset: int
    indexable: bool = True
    confidence: float = 1.0


@dataclass(frozen=True)
class Node:
    node_id: str
    document_id: int
    part_id: str
    parent_id: str | None
    node_type: str
    content: str
    embedding_text: str
    start_offset: int
    end_offset: int
    indexable: bool = True
    chapter_number: str | None = None
    chapter_title: str | None = None
    article_number: str | None = None
    article_title: str | None = None
    clause_number: str | None = None
    point_number: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ProcessedDocument:
    document_id: int
    raw_passage: str
    clean_passage: str
    metadata: dict[str, Any]
    parts: tuple[Part, ...] = field(default_factory=tuple)
    nodes: tuple[Node, ...] = field(default_factory=tuple)
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    status: str = "ok"
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileResult:
    document: ProcessedDocument | None
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
