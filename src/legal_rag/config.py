from dataclasses import dataclass


@dataclass(frozen=True)
class RAGConfig:
    embedding_model: str = "AITeamVN/Vietnamese_Embedding"
    reranker_model: str = "AITeamVN/Vietnamese_Reranker"
    generator_model: str = "AITeamVN/Vi-Qwen2-3B-RAG"
    dense_top_k: int = 50
    rerank_top_k: int = 30
    context_top_k: int = 6
    embedding_max_length: int = 2048
    reranker_max_length: int = 2304
    max_context_words: int = 5000
    max_new_tokens: int = 1024
