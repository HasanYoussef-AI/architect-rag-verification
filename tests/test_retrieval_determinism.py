"""Cross-implementation determinism of the fused ranking, pinned as a regression.

Defect 6: the residual worst-case was first measured by an enumeration that
excluded identical-vector pairs as deterministic. That is true for the per-query
matvec but false for a batched matrix product, which reduces identical rows in
different tile orders and breaks their tie by ~1e-7. Reciprocal rank fusion then
amplifies a single dense-rank flip by roughly 1/70 - 1/71, three orders of
magnitude larger than the score difference, so a tiny score change makes a
discrete fused change. The enumeration under-counted 63 as 4. This test pins the
direct measurement, the strongest cross-path difference producible on one machine,
so a refactor that reintroduces the instability fails loudly.
"""

from __future__ import annotations

import json

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.dense import SCORE_DECIMALS, dense_scores
from src.retrieve.fuse import RRF_K, rank_within_arm
from src.retrieve.retriever import load_retriever
from src.retrieve.tokenize import tokenize_query

ACTIONS = REPO_ROOT / "data" / "chunks" / "nist_ai_600_1.relations.jsonl"


def _fused_top10(bmr, chunk_ids, dense_row):
    der = rank_within_arm(dense_row, chunk_ids, 100)
    fused: dict[str, float] = {}
    for ranking in (bmr, der):
        for rank, cid in enumerate(ranking, start=1):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(fused, key=lambda c: (-fused[c], c))[:10]


def test_shipped_dense_scoring_is_the_per_query_matvec():
    # dense_scores is a matrix-vector product, quantised; not a batched matrix product.
    emb = np.array([[1, 0, 0], [0, 1, 0], [0.6, 0.8, 0]], dtype=np.float32)
    q = emb[0]
    assert np.array_equal(dense_scores(q, emb), np.round(emb @ q, SCORE_DECIMALS))


def test_matmul_and_matvec_paths_agree_after_quantisation():
    ret = load_retriever()
    emb = ret.embeddings
    cids = ret.chunk_ids
    idx = {c: i for i, c in enumerate(cids)}
    batched = emb @ emb.T  # the batched matrix-product path

    queries = list(range(len(cids)))  # known-item, each chunk queries itself
    for line in ACTIONS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for edge in row.get("action_subcategory", []):
            queries.append(idx[row["unit_id"]])

    membership = ordering = 0
    for qi in queries:
        bmr = rank_within_arm(ret.bm25.scores(tokenize_query(ret.texts[qi])), cids, 100)
        matvec = np.round(emb @ emb[qi], SCORE_DECIMALS)   # per-query, shipped
        matmul = np.round(batched[qi], SCORE_DECIMALS)     # batched
        a, b = _fused_top10(bmr, cids, matvec), _fused_top10(bmr, cids, matmul)
        if a == b:
            continue
        if set(a) != set(b):
            membership += 1
        else:
            ordering += 1
    # Zero membership changes across all queries, at most the single documented
    # ordering-only residual case. Unquantised this is 63; quantisation earns its place.
    assert membership == 0, f"{membership} membership changes across BLAS paths"
    assert ordering <= 1, f"{ordering} ordering-only changes, expected at most 1"
