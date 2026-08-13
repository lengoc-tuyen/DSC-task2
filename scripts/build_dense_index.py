#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_rag.config import RAGConfig
from legal_rag.embedding import encode_normalized, load_embedding_model
from legal_rag.index import build_index_from_batches
from legal_rag.nodes import iter_nodes


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def iter_vector_batches(nodes_path: Path, model, batch_size: int):
    batch_texts: list[str] = []
    for node in iter_nodes(nodes_path):
        batch_texts.append(node.embedding_text)
        if len(batch_texts) >= batch_size:
            yield encode_normalized(model, batch_texts, batch_size)
            batch_texts = []
    if batch_texts:
        yield encode_normalized(model, batch_texts, batch_size)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a normalized FAISS IndexFlatIP index")
    parser.add_argument("--nodes", type=Path, default=Path("artifacts/rag/nodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/rag/index.faiss"))
    parser.add_argument("--model", default=RAGConfig.embedding_model)
    parser.add_argument("--device")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    model = load_embedding_model(args.model, args.device, RAGConfig.embedding_max_length)
    index = build_index_from_batches(iter_vector_batches(args.nodes, model, args.batch_size), args.output)
    manifest = {
        "index_type": "IndexFlatIP", "model": args.model, "dimension": index.d,
        "node_count": index.ntotal, "nodes_sha256": file_sha256(args.nodes),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
