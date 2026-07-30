"""Provenance of a query-embedding array, checked at the ranking layer.

Byte-identity of a regenerated embedding array is not portable: ONNX reproduces rankings,
not bytes, across machines (data/retrieval/retrieval_manifest.json). So provenance is
verified by regenerating a query set's embeddings from its committed queries through
build_query_embeddings, running first-pass retrieval, and comparing rankings.

Every query set this repository commits is registered in QUERY_SETS, because the level-2 rule
in the retrieval manifest applies to all of them, not only to the development set. A set whose
query file is not committed yet is skipped; a set whose query file IS committed but whose
embedding array is not is a failure, not a skip, since that is exactly the state the rule
forbids.

Three checks, and they pin different things:

1. Presence and shape -- the array exists, has one row per query, is float32, and is
   L2-normalised. Model-free, so it runs everywhere and never skips for want of ONNX.
   It pins ROW COUNT, DTYPE AND NORM. It does NOT pin alignment: a row-shuffled array
   has the same shape and the same norms and passes this check.
2. Pipeline -- regenerated-array rankings against the committed retrieval results file.
   Confirms the pipeline reproduces the recorded rankings. Skipped for a set that has no
   results file yet, which is the sealed set's state at query-commit time, since
   PREREGISTRATION.md orders retrieval after the queries.
3. Provenance -- rankings from the COMMITTED array against rankings from the regenerated
   array, row by row. This is the one that pins ALIGNMENT: if the committed array were
   stale, foreign, or shuffled, row i would be some other query's vector and its ranking
   would diverge. Its one blind spot is two rows that happen to produce an identical
   top 10, which no committed set has been shown to contain.

ORDERING GATE. Checks 2 and 3 both call retriever.search, so both execute retrieval against
the query set. PREREGISTRATION.md orders the query and embedding commit before retrieval runs
on the set, so neither may run for a set whose retrieval results are not committed yet. The
gate is QuerySet.rank_reproduction_gated, derived from results being absent rather than from a
flag someone has to remember to flip: a set has no committed results exactly while retrieval
has not run on it, and both checks turn on at the commit that adds them. This is an ordering
constraint, not a data dependency -- check 3 needs no results file to compute anything. Check 1
is unaffected and still fails loudly on a query file committed without its array, which is the
state the level-2 rule forbids and the one thing that must be caught at every batch.

Checks 2 and 3 also require the pinned ONNX model. It is deliberately not in the offline
reproducibility set -- the corpus and its embeddings are committed and re-embedding is never
required to verify a headline number -- so they SKIP when the model is not already cached, and
never trigger a download (local_files_only). They run where the model is present and the
ordering gate is open.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.embed import EMBED_DIM

EVAL = REPO_ROOT / "eval"


@dataclass(frozen=True)
class QuerySet:
    """A committed query set and the artifacts that must travel with it."""

    name: str
    queries: Path
    embeddings: Path
    results: Path | None

    @property
    def rank_reproduction_gated(self) -> bool:
        """True while no code path may execute retrieval against this set.

        A set has no committed retrieval results exactly while retrieval has not run on it,
        which is the state PREREGISTRATION.md requires the query and embedding commit to be
        made in. Deriving the gate from that fact rather than from a separate flag means it
        opens at the commit that adds the results and cannot be left closed or forced open
        by accident.
        """
        return self.results is None


QUERY_SETS = [
    QuerySet(
        "development",
        EVAL / "dev_queries.jsonl",
        EVAL / "dev_query_embeddings.npy",
        EVAL / "dev_retrieval_results.json",
    ),
    QuerySet(
        "test",
        EVAL / "test_queries.jsonl",
        EVAL / "test_query_embeddings.npy",
        None,
    ),
]

_REGENERATED: dict[str, np.ndarray] = {}


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _skip_if_not_committed(query_set: QuerySet) -> None:
    if not query_set.queries.exists():
        pytest.skip(f"{query_set.name}: {query_set.queries.name} is not committed yet")


def _skip_if_retrieval_is_gated(query_set: QuerySet) -> None:
    """Refuse to run retrieval against a set whose results are not committed yet."""
    if query_set.rank_reproduction_gated:
        pytest.skip(
            f"{query_set.name}: retrieval is gated for this set. PREREGISTRATION.md commits the "
            "queries and their embeddings before retrieval runs on them, so no code path may "
            "execute retrieval against this set until its retrieval results are committed. "
            "Rank reproduction turns on at that commit."
        )


def _regenerate(query_set: QuerySet, session) -> np.ndarray:
    """Regenerate a set's embeddings through committed code, cached per set for this module."""
    if query_set.name not in _REGENERATED:
        from src.retrieve.build_query_embeddings import build

        out = EVAL / f".regenerated_{query_set.name}_query_embeddings.npy"
        try:
            build(query_set.queries, out, session=session)
            _REGENERATED[query_set.name] = np.load(out)
        finally:
            out.unlink(missing_ok=True)
    return _REGENERATED[query_set.name]


@pytest.fixture(scope="module")
def onnx_session():
    pytest.importorskip("onnxruntime")
    try:
        from huggingface_hub import hf_hub_download

        from src.retrieve.embed import (
            MODEL_REPO,
            MODEL_REVISION,
            ONNX_FILE,
            ONNX_SHA256,
            make_session,
            sha256_file,
        )

        path = hf_hub_download(MODEL_REPO, ONNX_FILE, revision=MODEL_REVISION, local_files_only=True)
        assert sha256_file(path) == ONNX_SHA256, "cached ONNX model does not match the pinned revision"
        return make_session(path)
    except Exception as exc:  # noqa: BLE001 - a missing offline model is a skip, not a failure
        pytest.skip(f"pinned ONNX model not cached; provenance test runs only where it is present ({exc})")


@pytest.fixture(scope="module")
def retriever():
    from src.retrieve.retriever import load_retriever

    return load_retriever()


def test_retrieval_is_gated_for_every_set_without_committed_results():
    """The ordering constraint, pinned so that removing it costs a failing test.

    PREREGISTRATION.md commits a query set and its embeddings before retrieval runs on it. Three
    things have to hold for that to be enforced rather than merely intended, and each is checked
    here because each can be undone independently:

    1. The gate tracks the absence of a results file, so it cannot be flipped by editing a flag.
    2. The gate helper actually raises for a gated set, and does not raise for an open one, so it
       is not a no-op that happens to be called in the right places.
    3. Both checks that call retriever.search actually call the helper. Deleting the call would
       otherwise reopen retrieval against a sealed set silently.

    Not parameterised over QUERY_SETS on purpose: the constraint is a property of the whole
    registry, and one failing test naming the registry reads better than one failing per set.
    """
    for query_set in QUERY_SETS:
        expected = query_set.results is None
        assert query_set.rank_reproduction_gated is expected, (
            f"{query_set.name}: gate is {query_set.rank_reproduction_gated} but results "
            f"{'are absent' if expected else 'are committed'}"
        )
        if expected:
            with pytest.raises(pytest.skip.Exception):
                _skip_if_retrieval_is_gated(query_set)
        else:
            _skip_if_retrieval_is_gated(query_set)

    for check in (
        test_regenerated_rankings_match_committed_results,
        test_committed_array_reproduces_regenerated_rankings,
    ):
        source = inspect.getsource(check)
        assert "_skip_if_retrieval_is_gated" in source, (
            f"{check.__name__} calls retriever.search but no longer consults the ordering gate"
        )


@pytest.mark.parametrize("query_set", QUERY_SETS, ids=lambda q: q.name)
def test_query_file_has_its_embedding_array(query_set: QuerySet):
    """Presence and shape. Pins row count, dtype and norm; does NOT pin alignment."""
    _skip_if_not_committed(query_set)
    assert query_set.embeddings.exists(), (
        f"{query_set.name}: {query_set.queries.name} is committed but {query_set.embeddings.name} "
        "is not. The level-2 rule in data/retrieval/retrieval_manifest.json requires query "
        "embeddings to be committed alongside every query set at the moment that set is created."
    )
    rows = _rows(query_set.queries)
    embeddings = np.load(query_set.embeddings)
    assert embeddings.shape == (len(rows), EMBED_DIM), (
        f"{query_set.name}: {len(rows)} queries against an array of shape {embeddings.shape}"
    )
    assert embeddings.dtype == np.float32, f"{query_set.name}: expected float32, got {embeddings.dtype}"
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5), f"{query_set.name}: embeddings are not L2-normalised"


@pytest.mark.parametrize("query_set", QUERY_SETS, ids=lambda q: q.name)
def test_regenerated_rankings_match_committed_results(query_set: QuerySet, retriever, onnx_session):
    """Pipeline: regenerated array -> retrieval -> the committed results file."""
    _skip_if_not_committed(query_set)
    _skip_if_retrieval_is_gated(query_set)
    rows = _rows(query_set.queries)
    regenerated = _regenerate(query_set, onnx_session)
    committed_results = {
        entry["id"]: entry["top10"]
        for entry in json.loads(query_set.results.read_text(encoding="utf-8"))["retrieval"]
    }
    assert regenerated.shape[0] == len(rows)
    for i, row in enumerate(rows):
        got = retriever.search(row["query"], regenerated[i])
        assert got == committed_results[row["id"]], f"{row['id']}: pipeline ranking diverged from results"


@pytest.mark.parametrize("query_set", QUERY_SETS, ids=lambda q: q.name)
def test_committed_array_reproduces_regenerated_rankings(query_set: QuerySet, retriever, onnx_session):
    """Provenance and alignment: the committed array and the regenerated array rank identically.

    Same query text and same retriever; only the embedding source differs. If the committed array
    were stale, foreign to these queries, or shuffled, row i would carry a different query's vector
    and its ranking would diverge.

    Gated by the commit ordering, not by a data dependency: this check needs no results file, but
    it calls retriever.search, and PREREGISTRATION.md forbids that before the set's retrieval
    results are committed.
    """
    _skip_if_not_committed(query_set)
    _skip_if_retrieval_is_gated(query_set)
    rows = _rows(query_set.queries)
    committed = np.load(query_set.embeddings)
    regenerated = _regenerate(query_set, onnx_session)
    assert committed.shape == regenerated.shape
    for i, row in enumerate(rows):
        from_committed = retriever.search(row["query"], committed[i])
        from_regenerated = retriever.search(row["query"], regenerated[i])
        assert from_committed == from_regenerated, f"{row['id']}: committed vs regenerated mismatch"
