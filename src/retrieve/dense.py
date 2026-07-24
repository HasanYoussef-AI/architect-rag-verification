"""Dense retrieval scoring over the committed embeddings.

Both the corpus embeddings and the query embedding are L2-normalised, so cosine
similarity is the dot product. The embeddings are generated once from the pinned
model revision and committed; see src.retrieve.embed and the retrieval manifest.
"""

from __future__ import annotations

import numpy as np

# Dense score quantisation for cross-platform determinism, not an acceptance
# criterion. This matmul is the only float reduction in retrieval whose result
# depends on BLAS build: the measured max per-score deviation between the
# full-matrix and per-query paths on one machine is 1.49e-6, so a reviewer on
# different hardware would order near-ties differently and the top-10 context
# handed to the model at generation would drift. Rounding to a fixed decimal grain
# before the locked chunk-id tie-break collapses sub-grain float noise into exact
# ties the tie-break then resolves deterministically. The grain is derived from the
# measured deviation, not fitted to any result: 1e-4 sits 67x above 1.49e-6, the
# finest decimal at least an order of magnitude above it, since 1e-5 would be only
# 6.7x. BM25 carries no such deviation, its cross-path difference measured exactly
# zero because it has no BLAS reduction, so it is not quantised: doing so would
# change rankings for no reproducibility gain. The fused score is a function of the
# quantised ranks alone, so it needs no rounding either. Recorded in the manifest.
SCORE_DECIMALS = 4


def dense_scores(query_vector: np.ndarray, corpus_embeddings: np.ndarray) -> np.ndarray:
    """Cosine similarity of one query vector against every corpus embedding, quantised.

    The scores are rounded to SCORE_DECIMALS so BLAS-dependent float noise below the
    grain does not decide near-tie order; the chunk-id tie-break in rank_within_arm
    resolves the exact ties this creates.
    """
    return np.round(corpus_embeddings @ query_vector, SCORE_DECIMALS)
