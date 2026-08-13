from typing import Protocol, Sequence


class Encoder(Protocol):
    def encode(self, texts: Sequence[str], **kwargs): ...


def encode_normalized(encoder: Encoder, texts: Sequence[str], batch_size: int):
    import numpy as np
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    vectors = np.asarray(encoder.encode(list(texts), batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False), dtype=np.float32)
    if vectors.ndim != 2 or not np.isfinite(vectors).all():
        raise ValueError("encoder returned invalid vectors")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("encoder returned zero vectors")
    return np.ascontiguousarray(vectors / norms, dtype=np.float32)


def load_embedding_model(model_id: str, device: str | None = None, max_length: int = 2048):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_id, device=device)
    model.max_seq_length = max_length
    return model
