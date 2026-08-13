#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_rag.config import RAGConfig
from legal_rag.io import load_jsonl, write_jsonl
from legal_rag.models import RetrievalHit
from legal_rag.nodes import load_nodes
from legal_rag.reranker import TransformersReranker, rerank


def main() -> None:
    parser = argparse.ArgumentParser(description="Rerank dense candidates with Vietnamese_Reranker")
    parser.add_argument("--candidates", type=Path, default=Path("outputs/rag/candidates.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("artifacts/rag/nodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("outputs/rag/reranked.jsonl"))
    parser.add_argument("--model", default=RAGConfig.reranker_model)
    parser.add_argument("--device")
    parser.add_argument("--top-k", type=int, default=RAGConfig.rerank_top_k)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    node_lookup = {node.node_id: node for node in load_nodes(args.nodes)}
    scorer = TransformersReranker(args.model, args.device, RAGConfig.reranker_max_length, args.batch_size)

    def records():
        for record in load_jsonl(args.candidates):
            hits = [RetrievalHit(node_lookup[item["node_id"]], float(item["dense_score"])) for item in record["hits"]]
            ranked = rerank(scorer, record["question"], hits, args.top_k)
            yield {"id": str(record["id"]), "question": record["question"], "hits": [
                {"node_id": hit.node.node_id, "dense_score": hit.dense_score, "rerank_score": hit.rerank_score}
                for hit in ranked
            ]}

    count = write_jsonl(args.output, records())
    print(json.dumps({"output": str(args.output), "questions": count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
