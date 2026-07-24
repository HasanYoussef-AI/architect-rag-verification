"""Reciprocal rank fusion and the deterministic chunk-id tie-break.

Ties are guaranteed in this corpus, not hypothetical, so the tie-break is what
keeps fusion reproducible. It is chunk id ascending, applied within each arm and
again after fusion.
"""

from __future__ import annotations

import numpy as np

from src.retrieve.fuse import rank_within_arm, reciprocal_rank_fusion


def test_within_arm_tie_broken_by_chunk_id_ascending():
    ids = ["c", "a", "b"]
    scores = np.array([1.0, 1.0, 1.0])
    assert rank_within_arm(scores, ids, 3) == ["a", "b", "c"]


def test_within_arm_score_dominates_then_id():
    ids = ["a", "b", "c"]
    scores = np.array([0.5, 0.9, 0.9])
    assert rank_within_arm(scores, ids, 3) == ["b", "c", "a"]


def test_rrf_contribution_is_one_over_k_plus_rank():
    assert reciprocal_rank_fusion([["x", "y"]], output_depth=2, k=60) == ["x", "y"]


def test_rrf_tie_broken_by_chunk_id_after_fusion():
    # arm A ranks y,x; arm B ranks x,y. Fused scores are equal, so chunk id decides.
    fused = reciprocal_rank_fusion([["y", "x"], ["x", "y"]], output_depth=2, k=60)
    assert fused == ["x", "y"]


def test_absent_from_an_arm_contributes_nothing():
    fused = reciprocal_rank_fusion([["a"], ["b"]], output_depth=2, k=60)
    assert fused == ["a", "b"]  # each 1/61, tie broken by id
