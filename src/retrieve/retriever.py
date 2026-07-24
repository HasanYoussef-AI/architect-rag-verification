"""Hybrid retriever: BM25 plus dense, fused with reciprocal rank fusion.

Applied identically to both the raw and the layered conditions. Every parameter
here is recorded in the retrieval manifest with its reasoning, and the query set
and gold passages are built after this is settled, so nothing here can be fitted
to them.

  first-pass retrieval depth per arm : 100
  fused output passed to the model   : 10
  BM25 : from-scratch Okapi, k1=1.5, b=0.75, non-negative IDF, untuned
  dense: cosine over committed bge-base-en-v1.5 embeddings, CLS-pooled, L2-normalised
  fusion: RRF, k=60
  tie-break: chunk id ascending, within each arm and after fusion
"""

from __future__ import annotations

import json

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.bm25 import BM25
from src.retrieve.dense import dense_scores
from src.retrieve.fuse import RRF_K, rank_within_arm, reciprocal_rank_fusion
from src.retrieve.tokenize import document_length, tokenize_document, tokenize_query

CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
EMBEDDINGS_PATH = REPO_ROOT / "data" / "retrieval" / "embeddings.npy"
CHUNK_ORDER_PATH = REPO_ROOT / "data" / "retrieval" / "chunk_order.json"

# The canonical corpus order for embeddings and every array index in retrieval.
CANONICAL_DOC_ORDER = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")

ARM_DEPTH = 100
OUTPUT_DEPTH = 10


def load_corpus_chunks() -> list[dict]:
    """Every chunk in canonical order: document order, then file order within a document."""
    chunks: list[dict] = []
    for doc in CANONICAL_DOC_ORDER:
        path = CHUNKS_DIR / f"{doc}.chunks.jsonl"
        chunks.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    return chunks


class Retriever:
    def __init__(self, chunks: list[dict], embeddings: np.ndarray):
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"chunks {len(chunks)} != embeddings {embeddings.shape[0]}")
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.texts = [c["text"] for c in chunks]
        self.embeddings = embeddings
        self.bm25 = BM25(
            [tokenize_document(t) for t in self.texts],
            [document_length(t) for t in self.texts],
            idf_variant="nonneg",
        )

    def bm25_ranking(self, query_text: str, depth: int = ARM_DEPTH) -> list[str]:
        return rank_within_arm(self.bm25.scores(tokenize_query(query_text)), self.chunk_ids, depth)

    def dense_ranking(self, query_vector: np.ndarray, depth: int = ARM_DEPTH) -> list[str]:
        return rank_within_arm(dense_scores(query_vector, self.embeddings), self.chunk_ids, depth)

    def search(
        self, query_text: str, query_vector: np.ndarray, output_depth: int = OUTPUT_DEPTH
    ) -> list[str]:
        """Fused top chunk ids passed to the model as context."""
        return reciprocal_rank_fusion(
            [self.bm25_ranking(query_text), self.dense_ranking(query_vector)],
            output_depth=output_depth,
            k=RRF_K,
        )


def load_retriever() -> Retriever:
    """Build the retriever from the committed chunks and embeddings.

    The committed chunk-id order is asserted against the frozen chunk ids so a
    reordering fails loudly rather than mismatching vectors to chunks silently.
    """
    chunks = load_corpus_chunks()
    embeddings = np.load(EMBEDDINGS_PATH)
    recorded = json.loads(CHUNK_ORDER_PATH.read_text(encoding="utf-8"))
    live = [c["chunk_id"] for c in chunks]
    if recorded != live:
        raise ValueError("committed chunk order does not match the frozen chunk ids")
    return Retriever(chunks, embeddings)
