#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_rag.config import RAGConfig
from legal_rag.embedding import encode_normalized, load_embedding_model
from legal_rag.index import FaissStore
from legal_rag.io import load_questions, write_jsonl
from legal_rag.query import analyze_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Dense retrieval for a JSON question set")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--nodes", type=Path, default=Path("artifacts/rag/nodes.jsonl"))
    parser.add_argument("--index", type=Path, default=Path("artifacts/rag/index.faiss"))
    parser.add_argument("--output", type=Path, default=Path("outputs/rag/candidates.jsonl"))
    parser.add_argument("--model", default=RAGConfig.embedding_model)
    parser.add_argument("--device")
    parser.add_argument("--top-k", type=int, default=RAGConfig.dense_top_k)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    questions = load_questions(args.questions)
    store = FaissStore.load(args.index, args.nodes)
    model = load_embedding_model(args.model, args.device, RAGConfig.embedding_max_length)
    analyses = [(qid, analyze_question(question)) for qid, question in questions.items()]
    vectors = encode_normalized(model, [analysis.search_text for _, analysis in analyses], args.batch_size)

    def records():
        for (qid, analysis), vector in zip(analyses, vectors):
            hits = [{"node_id": store.nodes[row].node_id, "dense_score": score} for row, score in store.search(vector, args.top_k)]
            yield {"id": qid, "question": analysis.original, "hits": hits}

    count = write_jsonl(args.output, records())
    print(json.dumps({"output": str(args.output), "questions": count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
