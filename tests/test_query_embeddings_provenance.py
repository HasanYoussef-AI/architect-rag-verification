"""Provenance of a query-embedding array, checked at the ranking layer.

Byte-identity of a regenerated embedding array is not portable: ONNX reproduces rankings,
not bytes, across machines (data/retrieval/retrieval_manifest.json). So provenance is
verified by regenerating the development query embeddings from the committed development
queries through build_query_embeddings, running first-pass retrieval, and making two
comparisons:

1. Pipeline -- regenerated-array rankings against the committed development results file.
   This confirms the pipeline reproduces the recorded rankings.
2. Provenance -- regenerated-array rankings against rankings computed from the COMMITTED
   development embedding array. This is the one that verifies the committed array came
   from these queries through this path; comparison 1 alone does not.

Both require the pinned ONNX model. It is deliberately not in the offline reproducibility
set -- the corpus and its embeddings are committed and re-embedding is never required to
verify a headline number -- so these tests SKIP when the model is not already cached, and
never trigger a download (local_files_only). They run where the model is present.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from src.ingest.corpus_integrity import REPO_ROOT

QUERIES = REPO_ROOT / "eval" / "dev_queries.jsonl"
COMMITTED_EMB = REPO_ROOT / "eval" / "dev_query_embeddings.npy"
RESULTS = REPO_ROOT / "eval" / "dev_retrieval_results.json"


@pytest.fixture(scope="module")
def onnx_session():
    pytest.importorskip("onnxruntime")
    try:
        from huggingface_hub import hf_hub_download

        from src.retrieve.embed import (
            MODEL_REPO,
            MODEL_REVISION,
            ONNX_FILE,
            ONNX_SHA256,
            make_session,
            sha256_file,
        )

        path = hf_hub_download(MODEL_REPO, ONNX_FILE, revision=MODEL_REVISION, local_files_only=True)
        assert sha256_file(path) == ONNX_SHA256, "cached ONNX model does not match the pinned revision"
        return make_session(path)
    except Exception as exc:  # noqa: BLE001 - a missing offline model is a skip, not a failure
        pytest.skip(f"pinned ONNX model not cached; provenance test runs only where it is present ({exc})")


@pytest.fixture(scope="module")
def retriever():
    from src.retrieve.retriever import load_retriever

    return load_retriever()


@pytest.fixture(scope="module")
def regenerated(onnx_session):
    from src.retrieve.build_query_embeddings import build

    out = REPO_ROOT / "eval" / ".regenerated_dev_query_embeddings.npy"
    try:
        build(QUERIES, out, session=onnx_session)
        return np.load(out)
    finally:
        out.unlink(missing_ok=True)


def _rows() -> list[dict]:
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_regenerated_rankings_match_committed_results(retriever, regenerated):
    """Pipeline: regenerated array -> retrieval -> committed development results file."""
    rows = _rows()
    committed_results = {
        entry["id"]: entry["top10"]
        for entry in json.loads(RESULTS.read_text(encoding="utf-8"))["retrieval"]
    }
    assert regenerated.shape[0] == len(rows)
    for i, row in enumerate(rows):
        got = retriever.search(row["query"], regenerated[i])
        assert got == committed_results[row["id"]], f"{row['id']}: pipeline ranking diverged from results file"


def test_committed_array_reproduces_regenerated_rankings(retriever, regenerated):
    """Provenance: the committed array and the regenerated array give identical rankings.

    Same query text and same retriever; only the embedding source differs. If the committed
    dev_query_embeddings.npy were stale or foreign to these queries, rankings would diverge.
    """
    rows = _rows()
    committed = np.load(COMMITTED_EMB)
    assert committed.shape == regenerated.shape
    for i, row in enumerate(rows):
        from_committed = retriever.search(row["query"], committed[i])
        from_regenerated = retriever.search(row["query"], regenerated[i])
        assert from_committed == from_regenerated, f"{row['id']}: committed vs regenerated ranking mismatch"
