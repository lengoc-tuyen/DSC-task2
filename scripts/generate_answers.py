#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_rag.config import RAGConfig
from legal_rag.context import build_context
from legal_rag.generation import TransformersGenerator, build_prompt
from legal_rag.io import atomic_write_json, load_jsonl
from legal_rag.models import RetrievalHit
from legal_rag.nodes import load_nodes


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grounded answers with Vi-Qwen2-3B-RAG")
    parser.add_argument("--reranked", type=Path, default=Path("outputs/rag/reranked.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("artifacts/rag/nodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("outputs/rag/submission.json"))
    parser.add_argument("--resume-state", type=Path, default=Path("outputs/rag/generation_state.json"))
    parser.add_argument("--model", default=RAGConfig.generator_model)
    parser.add_argument("--device")
    parser.add_argument("--context-top-k", type=int, default=RAGConfig.context_top_k)
    parser.add_argument("--max-context-words", type=int, default=RAGConfig.max_context_words)
    parser.add_argument("--max-new-tokens", type=int, default=RAGConfig.max_new_tokens)
    parser.add_argument("--quantize-4bit", action="store_true")
    args = parser.parse_args()
    node_lookup = {node.node_id: node for node in load_nodes(args.nodes)}
    records = load_jsonl(args.reranked)
    completed = json.loads(args.resume_state.read_text(encoding="utf-8")) if args.resume_state.exists() else {}
    generator = TransformersGenerator(args.model, args.device, args.quantize_4bit)
    for record in records:
        qid = str(record["id"])
        if qid in completed and completed[qid].get("question") == record["question"] and completed[qid].get("answer"):
            continue
        hits = [RetrievalHit(node_lookup[item["node_id"]], float(item["dense_score"]), float(item["rerank_score"])) for item in record["hits"][:args.context_top_k]]
        context = build_context(hits, args.max_context_words)
        answer = generator.generate(build_prompt(record["question"], context), max_new_tokens=args.max_new_tokens).strip()
        if not answer:
            raise RuntimeError(f"Model returned an empty answer for question {qid}")
        completed = {**completed, qid: {"question": record["question"], "answer": answer}}
        atomic_write_json(args.resume_state, completed)
    submission = {qid: {"answer": value["answer"]} for qid, value in completed.items()}
    atomic_write_json(args.output, submission)
    print(json.dumps({"output": str(args.output), "questions": len(completed)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
