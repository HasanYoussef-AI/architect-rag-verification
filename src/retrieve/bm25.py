"""From-scratch Okapi BM25, deterministic and auditable.

Written rather than taken from a library for the same reason the grader is: the
formula is pinned and documented here, and the choice of IDF variant is explicit
rather than inherited. Correctness is proved against rank-bm25 in the tests, on
the matching variant; the shipped retriever then uses the non-negative variant.

Two IDF variants:
  "robertson" : ln((N - n + 0.5) / (n + 0.5)), the classic Robertson-Sparck-Jones
                form, which goes NEGATIVE for terms in more than half the corpus.
                rank-bm25's BM25Okapi floors those negatives to epsilon times the
                average IDF (epsilon = 0.25). Implemented identically here only so
                the cross-check can prove our formula matches theirs.
  "nonneg"    : ln(1 + (N - n + 0.5) / (n + 0.5)), the Lucene form, always
                positive, no flooring needed. THIS IS THE SHIPPED VARIANT.

Scoring is decoupled from tokenisation: the index is given pre-tokenised documents
and their lengths, so the caller controls that index tokens may include expansion
parts while document length counts primary tokens only (see src.retrieve.tokenize).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np

K1_DEFAULT = 1.5
B_DEFAULT = 0.75
RANK_BM25_EPSILON = 0.25


class BM25:
    def __init__(
        self,
        doc_tokens: list[list[str]],
        doc_lengths: list[int],
        k1: float = K1_DEFAULT,
        b: float = B_DEFAULT,
        idf_variant: str = "nonneg",
    ):
        if idf_variant not in ("nonneg", "robertson"):
            raise ValueError(f"unknown idf_variant: {idf_variant}")
        self.k1 = k1
        self.b = b
        self.idf_variant = idf_variant
        self.n_docs = len(doc_tokens)
        self.doc_len = np.asarray(doc_lengths, dtype=np.float64)
        # avgdl from an exact integer sum rather than np.mean. Document lengths are
        # integers, so their sum is exact and order-independent, which removes the one
        # floating-point reduction from the BM25 path and makes cross-platform
        # reproducibility unconditional instead of resting on the sum staying below
        # 2^53. Measured bitwise-identical to np.mean over this corpus; a test pins the
        # value so a refactor back to a reduction fails loudly.
        self.avgdl = sum(int(length) for length in doc_lengths) / len(doc_lengths)

        # term frequency per document, and document frequency per term
        self.postings: dict[str, dict[int, int]] = defaultdict(dict)
        df: Counter = Counter()
        for index, tokens in enumerate(doc_tokens):
            counts = Counter(tokens)
            for term, freq in counts.items():
                self.postings[term][index] = freq
            df.update(counts.keys())
        self.idf = self._compute_idf(df)

    def _compute_idf(self, df: Counter) -> dict[str, float]:
        n = self.n_docs
        if self.idf_variant == "nonneg":
            return {t: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for t, freq in df.items()}
        # robertson, with rank-bm25's negative-IDF floor
        idf = {t: math.log((n - freq + 0.5) / (freq + 0.5)) for t, freq in df.items()}
        average_idf = sum(idf.values()) / len(idf)
        floor = RANK_BM25_EPSILON * average_idf
        return {t: (v if v >= 0 else floor) for t, v in idf.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        score = np.zeros(self.n_docs, dtype=np.float64)
        denom_len = self.k1 * (1 - self.b + self.b * self.doc_len / self.avgdl)
        for term in query_tokens:
            idf = self.idf.get(term)
            if idf is None:
                continue
            postings = self.postings.get(term)
            if not postings:
                continue
            idx = np.fromiter(postings.keys(), dtype=np.int64, count=len(postings))
            tf = np.fromiter(postings.values(), dtype=np.float64, count=len(postings))
            score[idx] += idf * (tf * (self.k1 + 1)) / (tf + denom_len[idx])
        return score
