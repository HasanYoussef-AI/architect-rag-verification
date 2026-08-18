"""The retrieval-ordering gate, and the two-direction demonstration it never had.

PREREGISTRATION.md commits a query set and its embeddings before retrieval runs on that set. The
gate is what enforces that ordering rather than merely stating it, and this file is what shows the
gate capable of both answers.

WHAT THIS REPLACES. tests/test_query_embeddings_provenance.py carried a single test whose first
assertion was `query_set.rank_reproduction_gated is (query_set.results is None)` against a gate
whose whole body was `return self.results is None`. Both sides were the same expression, so that
assertion could not fail whatever the gate did. Its docstring claimed the gate "tracks the absence
of a results file, so it cannot be flipped by editing a flag" while the sealed set's `results` was
the literal `None` in the registry and editing that one literal was exactly what opened it.
Measured before the rewrite: a set naming a results path that did not exist reported itself OPEN.

The third part of that test was not tautological and is kept verbatim in
tests/test_query_embeddings_provenance.py: the inspect.getsource check that both retrieval-running
checks still consult the helper.
"""

from __future__ import annotations

from pathlib import Path

from src.score.gate import QUERY_SETS, QuerySet, gate_reason


def _set_over(tmp: Path, name: str, with_results: bool) -> QuerySet:
    """A QuerySet under tmp_path whose results file is written or deliberately not."""
    queries = tmp / f"{name}_queries.jsonl"
    embeddings = tmp / f"{name}_embeddings.npy"
    results = tmp / f"{name}_results.json"
    queries.write_text("{}\n", encoding="utf-8")
    embeddings.write_bytes(b"")
    if with_results:
        results.write_text("{}\n", encoding="utf-8")
    return QuerySet(name, queries, embeddings, results)


def test_the_gate_tracks_a_file_and_not_a_literal(tmp_path):
    """Present opens and absent closes, both exercised here so neither direction can rot alone.

    This is the check the superseded form could not make. It builds two sets that differ in one
    thing, whether the results file was written, and asserts the gate answers differently. A gate
    reading a literal would answer identically for both, because both name a path.
    """
    open_set = _set_over(tmp_path, "open", with_results=True)
    closed_set = _set_over(tmp_path, "closed", with_results=False)

    assert open_set.results.exists() and not closed_set.results.exists(), (
        "the fixture did not produce the two states this test compares"
    )
    assert open_set.rank_reproduction_gated is False, (
        "gate reports closed for a results file that exists on disk"
    )
    assert closed_set.rank_reproduction_gated is True, (
        "gate reports open for a results path that does not exist"
    )

    # And the gate follows the file rather than the object: remove the file, the gate closes.
    open_set.results.unlink()
    assert open_set.rank_reproduction_gated is True, (
        "gate stayed open after its results file was removed, so it is not reading the filesystem"
    )


def test_the_gate_helper_raises_for_a_gated_set_and_not_for_an_open_one(tmp_path):
    """The refusal is a real refusal in one direction and silent in the other.

    Both directions are asserted because a helper that always refuses and a helper that never
    refuses are equally useless, and only running both tells them apart.
    """
    open_set = _set_over(tmp_path, "open", with_results=True)
    closed_set = _set_over(tmp_path, "closed", with_results=False)

    assert gate_reason(open_set) is None, (
        "the gate refused a set whose results are committed"
    )
    reason = gate_reason(closed_set)
    assert reason is not None, "the gate did not refuse a set whose results are absent"
    assert "closed" in reason and "PREREGISTRATION.md" in reason, (
        f"the refusal names neither the set nor the rule it enforces: {reason!r}"
    )


def test_no_registered_set_declares_a_null_results_path():
    """The flag is unrepresentable, not merely discouraged.

    `QuerySet.results` is typed `Path`, so a None would be a type error rather than a value the
    gate quietly honours. Asserted at runtime as well, because a type annotation is not a check.
    """
    for query_set in QUERY_SETS:
        assert isinstance(query_set.results, Path), (
            f"{query_set.name} carries results={query_set.results!r}; the gate is a literal again"
        )


def test_the_registry_reflects_the_repository_as_it_stands():
    """Both registered sets, and which of them is gated right now, from the files themselves.

    FLIPPED AT THE RESULTS COMMIT, which is what this test exists to force. Until then it read
    that the sealed set had no results and was gated, and it turned red the moment
    eval/test_retrieval_results.json was written. That red was designed: it is the one place the
    repository records which side of the retrieval ordering it is on, and the flip is landed in
    the same commit as the artifact so no commit in history has the two disagreeing.

    Both sets are now open, and both are asserted open from the files rather than from a literal.
    Nothing here can be satisfied by editing a flag: deleting either results file turns this red
    again, which is the property the superseded gate did not have.
    """
    by_name = {q.name: q for q in QUERY_SETS}
    assert set(by_name) == {"development", "test"}

    dev = by_name["development"]
    assert dev.results.exists(), f"{dev.results} is missing; the development set has results"
    assert dev.rank_reproduction_gated is False

    sealed = by_name["test"]
    assert sealed.results.exists(), (
        f"{sealed.results} is missing. Retrieval has run on the sealed set and its results are "
        "committed, so this file's absence means the artifact was removed rather than that the "
        "ordering was restored; the two provenance checks this governs would silently skip again"
    )
    assert sealed.rank_reproduction_gated is False


def test_the_gate_is_not_consulted_by_the_outcome_guard():
    """The two orderings are different things and are kept apart.

    The verification file's outcome guard is unconditional: where an outcome lives is a question
    about the artifact, not about when retrieval ran. This asserts the guard's module never
    imports the gate, so a later edit cannot quietly make it conditional.
    """
    source = (Path(__file__).parent / "test_test_query_verification.py").read_text(
        encoding="utf-8"
    )
    assert "src.score.gate" not in source and "rank_reproduction_gated" not in source, (
        "the outcome guard's module now consults the retrieval gate. The guard is unconditional "
        "by decision: prediction outcomes belong in the results artifact and the log entry, and "
        "the verification file stays a pre-registration record whatever the gate says"
    )
