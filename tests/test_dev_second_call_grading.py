"""The development second-call artifacts, per tier, re-derived and asserted.

Two artifacts, one producer, and both re-derived here so neither can drift from the code that
made it. eval/dev_second_call_flagged.json carries the lists the second-call bodies were built
from; eval/dev_second_call_grading.json carries the second answers graded by the grader frozen at
15e31d5.

THE GRADER IS FROZEN AND NOTHING HERE MOVES IT. eval/generation_predictions.md section 5.4 says the
development second-call answers are graded after the freeze only to show the path executes, and
that no threshold moves on what they show. These assertions record what they showed.

Reproducibility level 1: the committed first-pass answers, the committed second-call answers, the
committed development retrieval and the committed chunk store. No model, no key, no clock.
"""

from __future__ import annotations

import hashlib
import json

from src.score.run_dev_second_call_grading import (
    FLAGGED_PATH,
    GRADING_PATH,
    build,
)

FLAGGED_SHA256 = "a59509e16077bf7768da074b804dfea9422a4809f36dea5ebd7ac50bc0f18e75"
FLAGGED_BYTES = 10625
GRADING_SHA256 = "7c76a9ee657e75a6f7cdbe0beba43f3260b9a10a2f28ad8c85e8d4dfbc56eebd"
GRADING_BYTES = 64974

PER_TIER = {
    "haiku45": {
        "rows": 11,
        "layer_abstaining_rows": 3,
        "answered_rows": 8,
        "claim_units": 65,
        "ungrounded_units": 19,
        "unsupported_claim_rate": 0.292308,
        "layer_abstention_rate": 0.272727,
        "rows_repeating_a_flagged_unit_unchanged": 7,
        "flagged_units_in": 33,
        "flagged_units_repeated_unchanged": 14,
        "flagged_units_repeated_now_grounded": 0,
        "flagged_units_not_returned": 19,
        "first_pass_abstentions_with_a_substantive_second_answer": 1,
        "rows_fully_grounded_at_first_pass_then_layer_abstains": 0,
    },
    "sonnet5": {
        "rows": 11,
        "layer_abstaining_rows": 3,
        "answered_rows": 8,
        "claim_units": 44,
        "ungrounded_units": 7,
        "unsupported_claim_rate": 0.159091,
        "layer_abstention_rate": 0.272727,
        "rows_repeating_a_flagged_unit_unchanged": 1,
        "flagged_units_in": 11,
        "flagged_units_repeated_unchanged": 1,
        "flagged_units_repeated_now_grounded": 0,
        "flagged_units_not_returned": 10,
        "first_pass_abstentions_with_a_substantive_second_answer": 1,
        "rows_fully_grounded_at_first_pass_then_layer_abstains": 1,
    },
    "opus48": {
        "rows": 11,
        "layer_abstaining_rows": 2,
        "layer_abstention_rate": 0.181818,
        "answered_rows": 9,
        "claim_units": 31,
        "ungrounded_units": 8,
        "unsupported_claim_rate": 0.258065,
        "rows_repeating_a_flagged_unit_unchanged": 2,
        "flagged_units_in": 8,
        "flagged_units_repeated_unchanged": 3,
        "flagged_units_repeated_now_grounded": 0,
        "flagged_units_not_returned": 5,
        "first_pass_abstentions_with_a_substantive_second_answer": 1,
        "rows_fully_grounded_at_first_pass_then_layer_abstains": 0,
    },
}


def _grading() -> dict:
    return json.loads(GRADING_PATH.read_text(encoding="utf-8"))


def test_both_artifacts_exist_and_ship():
    for path, size in ((FLAGGED_PATH, FLAGGED_BYTES), (GRADING_PATH, GRADING_BYTES)):
        assert path.exists(), f"{path.name} is pinned here but is not in the tree"
        assert path.stat().st_size == size, (
            f"{path.name} is {path.stat().st_size} bytes against {size}"
        )


def test_both_artifacts_match_their_digests():
    assert hashlib.sha256(FLAGGED_PATH.read_bytes()).hexdigest() == FLAGGED_SHA256
    assert hashlib.sha256(GRADING_PATH.read_bytes()).hexdigest() == GRADING_SHA256


def test_the_committed_artifacts_equal_a_fresh_render():
    """Shape asserted on both sides before comparing, since two absent sides compare equal."""
    flagged, grading = build()
    for payload, path in ((flagged, FLAGGED_PATH), (grading, GRADING_PATH)):
        fresh = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
        committed = path.read_text(encoding="utf-8")
        assert len(fresh) > 1000 and len(committed) > 1000
        assert payload["produced_by"] and json.loads(committed)["produced_by"]
        assert fresh == committed, f"{path.name} is stale against its producer"


def test_the_population_is_the_eleven_the_corrective_pass_fires_on_per_tier():
    grading = _grading()
    assert grading["tiers"] == ["haiku45", "sonnet5", "opus48"]
    assert len(grading["rows"]) == 33
    assert not any(k.endswith("dev_07") for k in grading["rows"]), (
        "dev_07 is the row the corrective pass is silent on and carries no second call"
    )
    for tier in grading["tiers"]:
        assert sum(1 for k in grading["rows"] if f"__{tier}__" in k) == 11


def test_the_per_tier_second_call_figures():
    per_tier = _grading()["per_tier"]
    assert set(per_tier) == set(PER_TIER)
    for tier, expected in PER_TIER.items():
        for key, value in expected.items():
            assert per_tier[tier][key] == value, (
                f"{tier} {key}: {per_tier[tier][key]} against {value}"
            )


def test_no_flagged_unit_returned_verbatim_became_grounded_on_either_tier():
    """Measured on both tiers and recorded rather than assumed.

    A flagged unit that comes back byte-identical is graded against the AUGMENTED context, so it
    could become grounded if the corrective pass fetched something that supports it. On neither
    tier did that happen once. The rate fell because units were dropped or rewritten.
    """
    per_tier = _grading()["per_tier"]
    for tier, figures in per_tier.items():
        assert figures["flagged_units_repeated_now_grounded"] == 0, tier
        assert figures["flagged_units_repeated_unchanged"] > 0, (
            f"{tier}: no unit came back verbatim, so the zero above proves nothing"
        )


def test_a_row_grounded_at_the_first_pass_can_become_a_layer_abstention():
    """dev_02 on sonnet5, which contradicted a prediction and is pinned rather than smoothed.

    Its first answer was one unit scoring 1.0000. Nothing was flagged, so the second-call body
    carried the literal (none). The model rewrote the sentence anyway and the rewrite scores below
    the threshold, so the row abstains by the zero-grounded half. The second call made a fully
    grounded row worse, and this records that the rule and the predicate together allow it.
    """
    row = _grading()["rows"]["dev__second_call__sonnet5__dev_02"]
    assert row["first_pass_class"] == "answered"
    assert row["n_flagged_in"] == 0
    assert row["n_units"] == 1 and row["n_grounded"] == 0
    assert row["abstained_zero_grounded_after_second_call"] is True


def test_the_flagged_lists_are_the_first_pass_ungrounded_units():
    """Section 5.3's cross-check on the exact lists the bodies carried.

    The flagged list comes from src/complete/flagging.py and the first-pass grading records
    src/score/grounding.py's verdict. They are separate implementations and must agree.
    """
    flagged = json.loads(FLAGGED_PATH.read_text(encoding="utf-8"))["rows"]
    first = json.loads(
        (GRADING_PATH.parent / "dev_first_pass_grading.json").read_text(encoding="utf-8")
    )["rows"]
    for key, record in flagged.items():
        _, _, tier, query_id = key.split("__")
        ungrounded = [
            u["text"]
            for u in first[f"dev__raw__{tier}__{query_id}"]["units"]
            if not u["grounded"]
        ]
        assert record["flagged_units"] == ungrounded, f"{tier} {query_id}: flagged list differs"


def test_the_two_abstention_predicates_are_both_exercised():
    """Section 6.1's layer rule has two halves and this run exercised each at least once."""
    rows = _grading()["rows"]
    by_marker = [k for k, r in rows.items() if r["abstained_marker_either_pass"]]
    by_zero = [k for k, r in rows.items() if r["abstained_zero_grounded_after_second_call"]]
    assert by_marker, "no row abstained by the marker half"
    assert by_zero, "no row abstained by the zero-grounded half"
    expected = sum(v["layer_abstaining_rows"] for v in PER_TIER.values())
    assert len(set(by_marker) | set(by_zero)) == expected


def test_a_first_pass_abstention_is_not_recovered_by_a_substantive_second_answer():
    """A consequence of the committed rule, pinned because it is easy to read past.

    Section 6.1 says the layer abstains when the marker is returned on EITHER pass. dev_11
    abstained at the first pass, the corrective pass then fetched into its context, and the second
    answer is substantive with a grounded unit; the row still counts as a layer abstention. The
    rule is the committed one and this test records what it does rather than changing it.
    """
    row = _grading()["rows"]["dev__second_call__haiku45__dev_11"]
    assert row["first_pass_class"] == "abstained"
    assert row["second_call_class"] == "answered"
    assert row["n_units"] > 0 and row["n_grounded"] > 0
    assert row["abstained_marker_either_pass"] is True


def test_the_zero_grounded_half_does_not_fire_on_opus48():
    """P-o8 predicted it would fire on one of the nine comparable rows. It fired on none.

    The prediction is recorded as contradicted and pinned here so the reading cannot be reversed
    without deleting a failing test. Every opus48 abstention is by the marker half, and both of
    them are rows that abstained at the FIRST pass; no row answered at the first pass was turned
    into an abstention by the second call on this tier. The same predicate did fire on the other
    two tiers, on haiku45's dev_09 and sonnet5's dev_02, so the zero here is a property of the
    tier's answers and not of a predicate that never fires.
    """
    rows = _grading()["rows"]
    opus = {k: r for k, r in rows.items() if "__opus48__" in k}
    assert len(opus) == 11
    by_zero = [k for k, r in opus.items() if r["abstained_zero_grounded_after_second_call"]]
    assert by_zero == [], f"the zero-grounded half fired on {by_zero}"
    by_marker = sorted(k.split("__")[-1] for k, r in opus.items() if r["abstained_marker_either_pass"])
    assert by_marker == ["dev_11", "dev_12"]
    elsewhere = [
        k for k, r in rows.items()
        if r["abstained_zero_grounded_after_second_call"] and "__opus48__" not in k
    ]
    assert sorted(elsewhere) == [
        "dev__second_call__haiku45__dev_09",
        "dev__second_call__sonnet5__dev_02",
    ], "the predicate must be shown able to fire, or the empty above proves nothing"


def test_the_two_first_pass_implementations_agree_on_every_row():
    """V4 on all 33 rows.

    `first_pass_ungrounded` is src/score/grounding.py, the grader of record, over the first answer
    against the first-pass context. `n_flagged_in` is src/complete/flagging.py, the operational
    implementation, over the same answer and the same context. They are separate implementations
    and the artifact carries both, so a disagreement is visible rather than assumed away.
    """
    rows = _grading()["rows"]
    assert len(rows) == 33
    for key, row in rows.items():
        assert row["first_pass_ungrounded"] == row["n_flagged_in"], key
    assert sum(r["n_flagged_in"] for r in rows.values()) == 52, (
        "if every row carried zero the agreement above would be vacuous"
    )


def test_the_figures_are_capable_of_failing():
    """V20. An assertion set that could only pass would certify nothing."""
    per_tier = _grading()["per_tier"]
    assert per_tier["haiku45"]["claim_units"] != 64
    assert per_tier["sonnet5"]["claim_units"] != 43
    assert per_tier["opus48"]["claim_units"] != 30
    assert PER_TIER["sonnet5"]["claim_units"] == per_tier["sonnet5"]["claim_units"]
