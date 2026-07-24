"""BM25 correctness and cross-platform determinism.

Correctness is proved by reproducing rank-bm25 exactly under the matching IDF
variant, on primary tokens with no expansion, since rank-bm25 has no expansion.
The shipped retriever then uses the non-negative variant. Determinism is pinned
by the exact-integer avgdl, whose value a refactor back to np.mean must not move.
"""

from __future__ import annotations

import numpy as np
import pytest
from rank_bm25 import BM25Okapi

from src.retrieve.bm25 import BM25
from src.retrieve.retriever import load_corpus_chunks, load_retriever
from src.retrieve.tokenize import document_length, tokenize_query

K1, B, EPSILON = 1.5, 0.75, 0.25


@pytest.fixture(scope="module")
def corpus_primary_tokens():
    texts = [c["text"] for c in load_corpus_chunks()]
    return [tokenize_query(t) for t in texts]  # primary tokens, no expansion


def test_reproduces_rank_bm25_under_robertson(corpus_primary_tokens):
    ours = BM25(
        corpus_primary_tokens,
        [len(d) for d in corpus_primary_tokens],
        k1=K1,
        b=B,
        idf_variant="robertson",
    )
    theirs = BM25Okapi(corpus_primary_tokens, k1=K1, b=B, epsilon=EPSILON)
    queries = [["ai", "system"], ["govern", "1.1"], ["risk"], ["transparency", "documentation"]]
    for q in queries:
        diff = np.max(np.abs(ours.scores(q) - np.asarray(theirs.get_scores(q))))
        assert diff < 1e-10, f"query {q}: max abs diff {diff}"


def test_shipped_idf_is_non_negative():
    bm25 = load_retriever().bm25
    assert bm25.idf_variant == "nonneg"
    assert all(v >= 0.0 for v in bm25.idf.values())


def test_avgdl_is_the_pinned_exact_value():
    bm25 = load_retriever().bm25
    # Exact integer sum, order-independent, no floating-point reduction. A refactor
    # back to np.mean would reintroduce the reduction; this pins the value bitwise.
    assert bm25.avgdl == 128.4242658423493


def test_avgdl_is_exact_integer_sum():
    lengths = [document_length(c["text"]) for c in load_corpus_chunks()]
    assert load_retriever().bm25.avgdl == sum(lengths) / len(lengths)


def test_unknown_idf_variant_rejected():
    with pytest.raises(ValueError):
        BM25([["a"]], [1], idf_variant="nope")
