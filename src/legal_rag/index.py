from pathlib import Path
from typing import Iterable

from .models import RetrievalNode


class FaissStore:
    def __init__(self, index, nodes: list[RetrievalNode]):
        if index.ntotal != len(nodes):
            raise ValueError("FAISS row count does not match node metadata")
        self.index = index
        self.nodes = nodes

    def search(self, vector, top_k):
        import numpy as np
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if top_k <= 0:
            return []
        if query.shape[1] != self.index.d:
            raise ValueError(f"query dimension {query.shape[1]} does not match index dimension {self.index.d}")
        if not np.isfinite(query).all():
            raise ValueError("query vector contains non-finite values")
        scores, rows = self.index.search(query, min(top_k, len(self.nodes)))
        return [(int(row), float(score)) for row, score in zip(rows[0], scores[0]) if row >= 0]

    @classmethod
    def load(cls, index_path: Path, nodes_path: Path):
        import faiss
        from .nodes import load_nodes
        return cls(faiss.read_index(str(index_path)), load_nodes(nodes_path))


def build_index(vectors, index_path: Path):
    return build_index_from_batches((vectors,), index_path)


def build_index_from_batches(vector_batches: Iterable, index_path: Path):
    import faiss
    import numpy as np

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index = None
    total = 0
    for batch in vector_batches:
        vectors = np.ascontiguousarray(batch, dtype=np.float32)
        if vectors.size == 0:
            continue
        if vectors.ndim != 2 or not vectors.shape[0] or not vectors.shape[1]:
            raise ValueError("vectors must be a non-empty 2D matrix")
        if not np.isfinite(vectors).all():
            raise ValueError("vectors contain non-finite values")
        if index is None:
            index = faiss.IndexFlatIP(vectors.shape[1])
        elif vectors.shape[1] != index.d:
            raise ValueError(f"vector dimension {vectors.shape[1]} does not match index dimension {index.d}")
        index.add(vectors)
        total += int(vectors.shape[0])
    if index is None or total == 0:
        raise ValueError("vectors must be a non-empty 2D matrix")
    temporary = index_path.with_suffix(index_path.suffix + ".tmp")
    faiss.write_index(index, str(temporary))
    temporary.replace(index_path)
    return index
