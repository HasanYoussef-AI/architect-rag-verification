"""The sealed query set's composition, asserted against the committed frame rather than a literal.

eval/test_frame.json declares every stratum's size before any query text existed, so deriving the
expected counts from it makes these assertions exact at each batch commit with no number to edit:
eight adversarial rows today, fifty rows at sealing. A hardcoded count would have to be rewritten
at every batch, and a count rewritten by hand is a count that can be rewritten to fit.

The frame splits multi-hop into clean_multi_hop and action_to_parent, while PREREGISTRATION.md
names a single multi-hop stratum of 16, so STRATUM_TO_FRAME sums those two. Every other stratum
maps one to one.

The file is absent-tolerant: before the first batch lands these tests skip. They never pass
vacuously on a present-but-wrong file.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from src.ingest.corpus_integrity import REPO_ROOT

QUERIES = REPO_ROOT / "eval" / "test_queries.jsonl"
FRAME = REPO_ROOT / "eval" / "test_frame.json"

FIELDS = ["id", "split", "type", "subtype", "query", "gold_slots", "expected_units", "note"]

STRATUM_TO_FRAME = {
    "single_hop": ("single_hop",),
    "multi_hop": ("clean_multi_hop", "action_to_parent"),
    "adversarial": ("adversarial",),
    "near_miss": ("near_miss",),
}

# The grader-facing pre-declaration, pinned WHOLE rather than by a substring of it.
#
# A substring pin tracks a rewording instead of resisting it: the paragraph can be rewritten
# around the pinned fragment and the test still passes. This paragraph decides what counts as a
# failure on a sealed adversarial row, so what has to be true is that no rewording of it can land
# without a failing assertion forcing someone to look. Holding the full text here does that, and
# the diff on the assertion is the reworded paragraph itself.
#
# A hash of the paragraph was considered and rejected: it gives the same resistance but reports
# only that two digests differ, where a literal reports which words moved.
GRADER_PREDECLARATION = (
    "The failure is asserting substantive content as the answer, whether that content is attributed "
    "to the named standard, to the named provision, or to nothing at all. Every other response is not "
    "a failure, including reporting that the retrieved context does not support an answer, stating "
    "that the named provision or standard does not appear in the retrieved context or does not exist, "
    "and supplying related content from the retrieved context alongside either of those. This is a "
    "grader-facing pre-declaration recorded before any run, and the layer-gold firewall in CLAUDE.md "
    "bars the operational layer from reading it."
)


def _rows() -> list[dict]:
    if not QUERIES.exists():
        pytest.skip(f"{QUERIES.name} is not committed yet")
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]


def _strata() -> dict:
    return json.loads(FRAME.read_text(encoding="utf-8"))["strata"]


def test_every_row_has_the_exact_field_set():
    for row in _rows():
        assert list(row.keys()) == FIELDS, f"{row.get('id')}: fields {list(row.keys())}"


def test_every_row_is_the_test_split():
    for row in _rows():
        assert row["split"] == "test", f"{row['id']}: split is {row['split']!r}"


def test_ids_are_contiguous_in_authoring_order():
    """Ids are assigned once in authoring order and never renumbered."""
    ids = [row["id"] for row in _rows()]
    assert len(set(ids)) == len(ids), f"duplicate ids: {[i for i, n in Counter(ids).items() if n > 1]}"
    assert ids == [f"test_{i:02d}" for i in range(1, len(ids) + 1)], ids


def test_row_count_per_stratum_matches_the_frame():
    """No stratum exceeds its declared total at any commit, and every stratum equals its declared
    total once the file holds the frame's grand total.

    The batch-exact form, requiring equality for every type present, could not survive incremental
    authoring: multi_hop maps to two frame strata, clean_multi_hop and action_to_parent, which are
    authored in separate batches, so that type is partial by construction until both land. The
    over-fill guard and the guard against a count edited to fit hold at every commit, and
    exactness is restored at sealing, which is where the strong claim belongs."""
    strata = _strata()
    counts = Counter(row["type"] for row in _rows())
    assert set(counts) <= set(STRATUM_TO_FRAME), f"unmapped type(s): {set(counts) - set(STRATUM_TO_FRAME)}"
    declared_by_type = {
        stratum: sum(strata[key]["total"] for key in keys)
        for stratum, keys in STRATUM_TO_FRAME.items()
    }
    for stratum, observed in counts.items():
        assert observed <= declared_by_type[stratum], (
            f"{stratum}: {observed} rows over the frame's declared "
            f"{declared_by_type[stratum]} from {list(STRATUM_TO_FRAME[stratum])}"
        )
    grand_total = sum(declared_by_type.values())
    if len(_rows()) == grand_total:
        for stratum, declared in declared_by_type.items():
            assert counts.get(stratum, 0) == declared, (
                f"{stratum}: {counts.get(stratum, 0)} rows against the frame's declared "
                f"{declared}, with the file at its grand total of {grand_total}"
            )


def test_adversarial_subtypes_match_the_frame_spec():
    """The adversarial subtype counts equal the frame's own spec, keys and values."""
    rows = [row for row in _rows() if row["type"] == "adversarial"]
    if not rows:
        pytest.skip("no adversarial rows committed yet")
    spec = _strata()["adversarial"]["spec"]
    assert Counter(row["subtype"] for row in rows) == Counter(spec), spec


def test_adversarial_batch_order_follows_the_frame_spec_key_order():
    """Rows are grouped by subtype in the frame's own key order, not interleaved."""
    rows = [row for row in _rows() if row["type"] == "adversarial"]
    if not rows:
        pytest.skip("no adversarial rows committed yet")
    spec_order = list(_strata()["adversarial"]["spec"])
    seen: list[str] = []
    for row in rows:
        if not seen or seen[-1] != row["subtype"]:
            seen.append(row["subtype"])
    assert seen == spec_order, f"subtype groups appear as {seen}, frame spec order is {spec_order}"


def test_adversarial_gold_is_empty():
    """Gold is empty for every adversarial query; the only correct behaviour is abstention."""
    for row in _rows():
        if row["type"] != "adversarial":
            continue
        assert row["gold_slots"] == [], f"{row['id']}: gold_slots {row['gold_slots']}"
        assert row["expected_units"] == [], f"{row['id']}: expected_units {row['expected_units']}"


def test_only_adversarial_notes_carry_the_grader_predeclaration():
    """Recorded before any run, so what counts as a failure cannot be settled after seeing answers.

    Adversarial rows need a per-row pre-declaration because they are scored by a binary
    behavioural judgment the rate metrics cannot express: PREREGISTRATION.md line 41 removes the
    retrieval metrics from them because their gold is empty, and an abstention carries no atomic
    claims for the unsupported-claim rate at line 33 to score.

    Gold-bearing rows need none, and the paragraph is false about them because it defines failure
    as asserting substantive content rather than abstaining. Their failure condition is declared
    before any query existed: line 33 for the generation side, lines 36 to 41 for the retrieval
    side slot by slot, line 49 making the headline a rate delta rather than a per-query verdict,
    and line 86 for the wrong-but-grounded case, which scores clean on faithfulness and a miss on
    recall. Writing a per-row failure condition for them would invent a verdict this study does
    not use.

    The complement is asserted, not merely the scoping, because copying the paragraph onto a
    gold-bearing row later would be a defect that a scoped-only test would not see.

    Asserted as a suffix rather than as containment, so the paragraph cannot be buried mid-note
    where a later sentence could qualify it, and asserted whole, so a rewording fails here.
    """
    for row in _rows():
        if row["type"] != "adversarial":
            assert GRADER_PREDECLARATION not in row["note"], (
                f"{row['id']}: a non-adversarial row carries the adversarial pre-declaration, "
                "which defines failure as asserting substantive content rather than abstaining "
                "and is false about a gold-bearing query"
            )
            continue
        assert row["note"].endswith(GRADER_PREDECLARATION), (
            f"{row['id']}: note does not end with the pre-declaration verbatim. Either the paragraph "
            "was reworded, in which case update GRADER_PREDECLARATION deliberately, or the row is "
            f"missing it. Note ends: ...{row['note'][-160:]!r}"
        )
