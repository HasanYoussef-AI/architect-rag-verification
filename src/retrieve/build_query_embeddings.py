"""Build query embeddings for a query file, through the same path as the corpus.

Reads a query jsonl (one JSON object per line, each with a ``query`` field), embeds
each query string through :func:`src.retrieve.embed.embed_texts` -- which applies
``normalise_for_comparison`` before the ONNX tokenizer, identically to the corpus side --
and writes a float32 ``.npy`` aligned row for row with the input file.

This exists so a reviewer can regenerate a committed query-embedding array from the
committed queries through committed code, instead of trusting an array that was produced
by an ad-hoc call. It is used for the sealed test queries and, as a cross-check, to
regenerate the development array. Cross-machine, ONNX reproduces rankings, not bytes (see
data/retrieval/retrieval_manifest.json), so byte-identity of the output is a local
measurement, never a portable assertion; the portable checks live in the tests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.embed import (
    EMBED_DIM,
    MAX_SEQ,
    download_onnx,
    embed_texts,
    make_session,
    token_lengths,
)


class BuildError(RuntimeError):
    pass


def load_queries(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build(input_path: Path, output_path: Path, session=None) -> dict:
    """Embed a query file. ``session`` may be an already-verified ONNX session; if
    omitted, the pinned model is resolved and its checksum verified via download_onnx.
    Tests pass a session built under local_files_only so the path never hits the network."""
    rows = load_queries(input_path)
    texts = [row["query"] for row in rows]

    over = [i for i, n in enumerate(token_lengths(texts)) if n > MAX_SEQ]
    if over:
        raise BuildError(f"queries exceeding the {MAX_SEQ}-token cap at rows {over}")

    if session is None:
        session = make_session(download_onnx())
    embeddings = embed_texts(texts, session)
    if embeddings.shape != (len(texts), EMBED_DIM):
        raise BuildError(f"expected shape {(len(texts), EMBED_DIM)}, got {embeddings.shape}")
    embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-5):
        raise BuildError("embeddings are not L2-normalised within tolerance")

    np.save(output_path, embeddings)
    return {"n_queries": len(texts), "dim": EMBED_DIM, "output": str(output_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="query jsonl with a 'query' field per row")
    parser.add_argument("--output", required=True, type=Path, help="destination .npy, row-aligned to the input")
    args = parser.parse_args()
    result = build(args.input.resolve(), args.output.resolve())
    print(f"wrote {Path(result['output']).relative_to(REPO_ROOT)}: {result['n_queries']} x {result['dim']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
