from typing import Sequence

from .models import RetrievalHit


def build_context(hits: Sequence[RetrievalHit], max_words: int) -> str:
    blocks = []
    used = 0
    seen = set()
    for hit in hits:
        if hit.node.node_id in seen:
            continue
        path = " > ".join(hit.node.path)
        block = f"[Nguồn {len(blocks) + 1}] {path}\n{hit.node.content}"
        size = len(block.split())
        if blocks and used + size > max_words:
            break
        blocks.append(block)
        used += size
        seen.add(hit.node.node_id)
    return "\n\n".join(blocks)
