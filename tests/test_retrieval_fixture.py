"""The known-item fixture pins the retriever's rank-1 for every chunk, exactly.

This is the headline determinism check. It proves the lexical path is wired end
to end and the vector store is ordered correctly. It is not a test of retrieval
quality, which is untested until real queries exist. Any change in tokenisation,
scoring, fusion, quantisation, or the embeddings surfaces here as a readable diff
rather than passing on a criterion nobody can defend.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.retriever import load_corpus_chunks, load_retriever

FIXTURE = REPO_ROOT / "data" / "retrieval" / "known_item_fixture.json"
EMBEDDINGS = REPO_ROOT / "data" / "retrieval" / "embeddings.npy"
CATEGORIES = {"self", "raw_verbatim_twin", "normalised_twin", "near_duplicate"}


@pytest.fixture(scope="module")
def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def retriever():
    return load_retriever()


def test_embeddings_sha_matches_the_fixture(fixture):
    sha = hashlib.sha256(EMBEDDINGS.read_bytes()).hexdigest()
    assert sha == fixture["generated_from"]["embeddings_sha256"]


def test_chunk_order_matches_frozen_ids(retriever):
    live = [c["chunk_id"] for c in load_corpus_chunks()]
    assert retriever.chunk_ids == live


def test_no_row_is_a_dissimilar_rank1(fixture):
    seen = {row["category"] for row in fixture["rows"]}
    assert seen <= CATEGORIES


def test_known_item_rank1_is_exact(fixture, retriever):
    rows = fixture["rows"]
    assert len(rows) == len(retriever.chunk_ids) == 1294
    position = {cid: i for i, cid in enumerate(retriever.chunk_ids)}
    mismatches = []
    for row in rows:
        i = position[row["query"]]
        got = retriever.search(retriever.texts[i], retriever.embeddings[i], output_depth=1)[0]
        if got != row["expected_rank1"]:
            mismatches.append((row["query"], row["expected_rank1"], got))
    assert not mismatches, f"{len(mismatches)} rank-1 mismatches, e.g. {mismatches[:3]}"


def test_genuine_preference_decomposition_holds(fixture):
    dec = fixture["genuine_preference_decomposition"]
    genuine = [r for r in fixture["rows"] if r["genuine_preference"]]
    assert len(genuine) == dec["total"] == dec["block_near_duplicate"] + dec["cross_document_statement"]
    blocks = [
        r["query"]
        for r in genuine
        if r["query"].endswith(".ai_transparency_resources") or ".references" in r["query"]
    ]
    assert len(blocks) == dec["block_near_duplicate"]
