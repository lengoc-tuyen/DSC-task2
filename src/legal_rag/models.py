from dataclasses import asdict, dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class RetrievalNode:
    node_id: str
    document_id: int
    part_id: str
    node_type: str
    content: str
    embedding_text: str
    path: tuple[str, ...]
    article_id: str | None = None
    article_number: str | None = None
    clause_numbers: tuple[str, ...] = field(default_factory=tuple)
    point_labels: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        # This field is deterministically reconstructed and otherwise doubles
        # the largest text payload in the on-disk corpus.
        value.pop("embedding_text", None)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RetrievalNode":
        path = tuple(value.get("path", ()))
        content = value.get("content", "")
        embedding_text = value.get("embedding_text") or "\n".join((*path, content))
        return cls(**{**value, "embedding_text": embedding_text, "path": path, "clause_numbers": tuple(value.get("clause_numbers", ())), "point_labels": tuple(value.get("point_labels", ()))})


@dataclass(frozen=True)
class RetrievalHit:
    node: RetrievalNode
    dense_score: float
    rerank_score: float | None = None

    def with_rerank_score(self, score: float) -> "RetrievalHit":
        return replace(self, rerank_score=score)


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    hits: tuple[RetrievalHit, ...]
    prompt: str
