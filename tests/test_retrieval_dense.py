"""Dense scoring and its cross-platform quantisation.

Quantisation to a fixed decimal grain before the tie-break collapses sub-grain
float noise, the deviation between BLAS matvec paths, into exact ties the tie-break
then resolves deterministically. It is a determinism rule, not an acceptance
criterion.
"""

from __future__ import annotations

import numpy as np

from src.retrieve.dense import SCORE_DECIMALS, dense_scores


def test_score_decimals_is_four():
    assert SCORE_DECIMALS == 4


def test_dense_scores_are_rounded_to_the_grain():
    emb = np.array([[1, 0, 0], [0, 1, 0], [0.6, 0.8, 0]], dtype=np.float32)
    q = emb[0]
    assert np.array_equal(dense_scores(q, emb), np.round(emb @ q, SCORE_DECIMALS))


def test_self_similarity_is_one():
    emb = np.array([[0.6, 0.8], [0.8, 0.6]], dtype=np.float32)
    assert dense_scores(emb[0], emb)[0] == 1.0


def test_sub_grain_difference_becomes_an_exact_tie():
    # cos(q, second) is 0.99999, within the 1e-4 grain of 1.0, so both round equal
    second = np.array([0.99999, np.sqrt(1.0 - 0.99999**2)], dtype=np.float64)
    emb = np.array([[1.0, 0.0], second])
    scores = dense_scores(np.array([1.0, 0.0]), emb)
    assert scores[0] == scores[1] == 1.0
