"""The retrieval-ordering gate, as one definition two callers share.

PREREGISTRATION.md commits a query set and its embeddings BEFORE retrieval runs on that set, so no
code path may execute retrieval against a set whose results are not committed yet. The gate is
what makes that ordering enforced rather than intended.

WHY THIS LIVES IN src/ RATHER THAN IN A TEST MODULE. It used to be a property on a dataclass
inside tests/test_query_embeddings_provenance.py, so the only thing that could consult it was that
file. The scoring module must refuse a gated set too, and a predicate two callers share is a
predicate that cannot drift between them.

WHAT THE PREVIOUS FORM GOT WRONG, recorded because the correction is the point. The gate read
`self.results is None` against a `Path | None` field whose value for the sealed set was the
literal `None` in the registry. That is a flag someone has to remember to flip, wearing a path's
type. Measured before this rewrite: a set pointing at a results path that did not exist on disk
reported itself OPEN. Its own test then asserted `rank_reproduction_gated is (results is None)`,
which is the same expression on both sides and therefore could not fail. The docstring claimed the
gate "cannot be flipped by editing a flag" while editing exactly one literal was what opened it.

The gate now reads the filesystem. Every set carries its results path unconditionally, present or
absent, so `None` is unrepresentable rather than merely discouraged, and the gate opens on the
commit that adds the file and closes again if it is removed, with nobody editing anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.ingest.corpus_integrity import REPO_ROOT

EVAL = REPO_ROOT / "eval"


@dataclass(frozen=True)
class QuerySet:
    """A committed query set and the artifacts that must travel with it.

    `results` is a Path always, never None. A set whose retrieval has not run yet names the path
    its results will occupy; the file simply is not there.
    """

    name: str
    queries: Path
    embeddings: Path
    results: Path

    @property
    def rank_reproduction_gated(self) -> bool:
        """True while no code path may execute retrieval against this set.

        Derived from the results file being absent from disk, which is the fact the ordering
        constraint is about. Nothing else is consulted, so the gate cannot be held closed against
        a committed results file or forced open without one.
        """
        return not self.results.exists()


QUERY_SETS = (
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
        EVAL / "test_retrieval_results.json",
    ),
)

GATE_MESSAGE = (
    "{name}: retrieval is gated for this set. PREREGISTRATION.md commits the queries and their "
    "embeddings before retrieval runs on them, so no code path may execute retrieval against this "
    "set until its retrieval results are committed. Rank reproduction turns on at that commit."
)


def gate_reason(query_set: QuerySet) -> str | None:
    """The refusal message for a gated set, or None when the set is open.

    Returning the message rather than raising keeps this importable by a test that wants to skip
    and by a module that wants to raise, without either dictating the other's control flow.
    """
    if not query_set.rank_reproduction_gated:
        return None
    return GATE_MESSAGE.format(name=query_set.name)
