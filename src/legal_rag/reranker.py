import math
from typing import Protocol, Sequence

from .models import RetrievalHit


class PairScorer(Protocol):
    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> Sequence[float]: ...


def rerank(scorer: PairScorer, question: str, hits: Sequence[RetrievalHit], top_n: int) -> list[RetrievalHit]:
    if not hits:
        return []
    scores = scorer.score_pairs([(question, hit.node.embedding_text) for hit in hits])
    if len(scores) != len(hits) or any(not math.isfinite(float(score)) for score in scores):
        raise ValueError("reranker returned invalid scores")
    ranked = [hit.with_rerank_score(float(score)) for hit, score in zip(hits, scores)]
    return sorted(ranked, key=lambda hit: (-(hit.rerank_score or 0.0), -hit.dense_score, hit.node.node_id))[:top_n]


class TransformersReranker:
    def __init__(self, model_id: str, device: str | None = None, max_length: int = 2304, batch_size: int = 4):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id, torch_dtype="auto").to(device or ("cuda" if torch.cuda.is_available() else "cpu")).eval()
        self.device = next(self.model.parameters()).device
        self.max_length = max_length
        self.batch_size = batch_size

    def score_pairs(self, pairs):
        output = []
        for start in range(0, len(pairs), self.batch_size):
            inputs = self.tokenizer(list(pairs[start:start + self.batch_size]), padding=True, truncation=True, max_length=self.max_length, return_tensors="pt").to(self.device)
            with self.torch.inference_mode():
                output.extend(self.model(**inputs, return_dict=True).logits.view(-1).float().cpu().tolist())
        return output
