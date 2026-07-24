"""Reciprocal rank fusion, with a deterministic tie-break.

Ties are guaranteed in this corpus, not hypothetical: verbatim-duplicated
subcategory statements produce identical BM25 scores, and RRF sums collide too.
Without an explicit tie-break, order would fall back on input order and platform
sort stability, which quietly breaks the reproducibility claim. The tie-break is
chunk id, lexicographic ascending, applied WITHIN each arm before ranks are
assigned and AGAIN after fusion.

The fusion constant k is 60, the published default from Cormack, Clarke and
Buettcher's original RRF work, adopted untuned.
"""

from __future__ import annotations

import numpy as np

RRF_K = 60


def rank_within_arm(scores: np.ndarray, chunk_ids: list[str], depth: int) -> list[str]:
    """Top-`depth` chunk ids by score descending, ties broken by chunk id ascending.

    Scores are ranked as given; quantisation for determinism happens in the arm that
    needs it (the dense arm, see src.retrieve.dense.SCORE_DECIMALS). The chunk-id
    tie-break resolves any exact ties, including those the dense quantisation creates.
    """
    order = sorted(range(len(chunk_ids)), key=lambda i: (-scores[i], chunk_ids[i]))
    return [chunk_ids[i] for i in order[:depth]]


def reciprocal_rank_fusion(
    arm_rankings: list[list[str]], output_depth: int, k: int = RRF_K
) -> list[str]:
    """Fuse per-arm ranked chunk-id lists into one, tie-broken by chunk id ascending.

    Each arm contributes 1 / (k + rank), rank 1-based. A chunk absent from an arm
    contributes nothing from that arm.
    """
    fused: dict[str, float] = {}
    for ranking in arm_rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    # The fused score is not quantised. It is a function of the arm ranks alone, no
    # raw arm score enters this sum, and the dense ranks are already made deterministic
    # by dense quantisation, so 1/(k+rank) is exact-reproducible float64 and the fused
    # ranking is reproducible without rounding. Rounding it at the dense-derived grain
    # was measured to reshuffle 369 of 1294 top-10s by merging fused scores that differ
    # by ~1e-5, finer than that grain, so it would coarsen the ranking it exists to
    # stabilise. See the retrieval manifest.
    order = sorted(fused, key=lambda cid: (-fused[cid], cid))
    return order[:output_depth]
