from .context import build_context
from .embedding import encode_normalized
from .generation import build_prompt
from .models import AnswerResult, RetrievalHit
from .query import analyze_question
from .reranker import rerank


class LegalRAGPipeline:
    def __init__(self, embedder, store, nodes, reranker_model, generator, dense_top_k=50, rerank_top_k=30, context_top_k=6, max_context_words=5000):
        self.embedder = embedder
        self.store = store
        self.nodes = nodes
        self.reranker_model = reranker_model
        self.generator = generator
        self.dense_top_k = dense_top_k
        self.rerank_top_k = rerank_top_k
        self.context_top_k = context_top_k
        self.max_context_words = max_context_words

    def answer(self, question: str) -> AnswerResult:
        analysis = analyze_question(question)
        vector = encode_normalized(self.embedder, [analysis.search_text], 1)[0]
        hits = [RetrievalHit(self.nodes[row], score) for row, score in self.store.search(vector, self.dense_top_k)]
        ranked = rerank(self.reranker_model, analysis.normalized, hits, self.rerank_top_k)
        selected = ranked[:self.context_top_k]
        context = build_context(selected, self.max_context_words)
        prompt = build_prompt(analysis.normalized, context)
        answer = self.generator.generate(prompt).strip()
        if not answer:
            raise ValueError("generator returned an empty answer")
        return AnswerResult(answer, tuple(selected), prompt)
