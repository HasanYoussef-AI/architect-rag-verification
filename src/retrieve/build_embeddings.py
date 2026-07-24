"""Generate and commit the corpus embeddings. Build-only, run once.

    uv run --group embed python -m src.retrieve.build_embeddings

Downloads the pinned ONNX weight, proves no chunk truncates at the 512 cap and
that batching does not change a vector (padded attention masking is correct), then
embeds all chunks in canonical order at batch size 1 and writes the float32 .npy
plus the chunk-id order.
"""

from __future__ import annotations

import json

import numpy as np

from src.retrieve.embed import (
    MAX_SEQ,
    OUTPUT_DIR,
    download_onnx,
    embed_texts,
    make_session,
    token_lengths,
)
from src.retrieve.retriever import load_corpus_chunks

BATCH_SIZE = 1


class BuildError(RuntimeError):
    pass


def check_no_truncation(chunk_ids: list[str], texts: list[str]) -> list[int]:
    lengths = token_lengths(texts)
    over = [(chunk_ids[i], lengths[i]) for i, n in enumerate(lengths) if n > MAX_SEQ]
    if over:
        raise BuildError(f"chunks truncate at the {MAX_SEQ} cap, freeze violation: {over[:5]}")
    return lengths


def check_batch_invariance(session, texts: list[str]) -> float:
    """Embed one chunk alone and inside a padded batch of longer chunks; max abs diff."""
    ordered = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    short = texts[ordered[len(ordered) // 4]]
    longer = [texts[ordered[-1]], texts[ordered[-2]], texts[ordered[-3]]]
    alone = embed_texts([short], session, batch_size=1)[0]
    batched = embed_texts([short] + longer, session, batch_size=4)[0]
    return float(np.max(np.abs(alone - batched)))


def build() -> dict:
    onnx_path = download_onnx()
    session = make_session(onnx_path)
    chunks = load_corpus_chunks()
    chunk_ids = [c["chunk_id"] for c in chunks]
    texts = [c["text"] for c in chunks]

    lengths = check_no_truncation(chunk_ids, texts)
    max_abs_diff = check_batch_invariance(session, texts)
    if max_abs_diff > 1e-4:
        raise BuildError(f"batch invariance violated, max abs diff {max_abs_diff}")

    embeddings = embed_texts(texts, session, batch_size=BATCH_SIZE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT_DIR / "embeddings.npy", embeddings)
    (OUTPUT_DIR / "chunk_order.json").write_text(
        json.dumps(chunk_ids, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "n_chunks": len(chunk_ids),
        "shape": list(embeddings.shape),
        "dtype": str(embeddings.dtype),
        "max_token_length": max(lengths),
        "chunks_at_cap": sum(1 for n in lengths if n == MAX_SEQ),
        "batch_invariance_max_abs_diff": max_abs_diff,
    }


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
