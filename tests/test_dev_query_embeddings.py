"""The development-query embedding path shares the corpus's comparison normalisation.

embed_texts and token_lengths both encode normalise_for_comparison(text), so the
query side folds the publisher's typographic characters exactly as the corpus side
does. Without that fold a query typed with an ASCII apostrophe would miss a chunk
carrying the curly one. This pins the shared path so a refactor cannot let them drift.
"""

from __future__ import annotations

import json

import numpy as np
from tokenizers import Tokenizer

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison
from src.retrieve.embed import EMBED_DIM, TOKENIZER_FILE

QUERIES = REPO_ROOT / "eval" / "dev_queries.jsonl"
QUERY_EMB = REPO_ROOT / "eval" / "dev_query_embeddings.npy"


def test_embedding_input_is_comparison_normalised():
    tok = Tokenizer.from_file(str(TOKENIZER_FILE))
    curly = "the model’s pre–deployment review"  # curly apostrophe, en dash
    plain = "the model's pre-deployment review"
    # normalised, the two spellings encode identically; unnormalised they differ, so
    # the fold is doing the work rather than the tokenizer folding them anyway.
    assert tok.encode(normalise_for_comparison(curly)).ids == tok.encode(normalise_for_comparison(plain)).ids
    assert tok.encode(curly).ids != tok.encode(plain).ids


def test_dev_query_embeddings_align_with_queries():
    rows = [json.loads(x) for x in QUERIES.read_text(encoding="utf-8").splitlines() if x.strip()]
    emb = np.load(QUERY_EMB)
    assert emb.shape == (len(rows), EMBED_DIM)
    assert emb.dtype == np.float32
    assert np.allclose(np.linalg.norm(emb, axis=1), 1.0, atol=1e-5)


def test_every_dev_query_is_development_split():
    rows = [json.loads(x) for x in QUERIES.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 12
    assert all(r["split"] == "development" for r in rows)
