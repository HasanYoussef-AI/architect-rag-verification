"""The freeze's basis: the development first-pass grading, re-derived and asserted.

THE FIGURES ARE THE FREEZE'S EVIDENCE. eval/generation_predictions.md section 5.4 requires the
freeze commit to record what the reference condition turned, whether that is zero or not. It turned
zero, and section 5.4 says a sample of zero is a disclosed condition on the instrument and not a
reason to widen anything. These assertions are what make that reviewable: a reviewer runs them with
no key and gets the same numbers the judgment was made on.

THIS IS ALSO THE BEHAVIOURAL HALF OF THE FREEZE. tests/test_grader_freeze.py pins the four modules
as bytes; it cannot see a change in a module they import. Everything here re-derives from the
committed answers through the committed grader, so a change in src/complete/references.py,
src/ingest/normalize.py or src/retrieve/tokenize.py that alters a verdict turns these red.

REPRODUCIBILITY LEVEL 1. No model, no key, no network, no clock. The re-derivation and the
committed artifact are asserted equal, so the artifact cannot drift from the code that produced it.
"""

from __future__ import annotations

import hashlib
import json

from src.score.run_dev_grading import GRADING_PATH, build

GRADING_SHA256 = "7da42a825018c97a476b122be063d3cf13a094bffc76adf70925c728be6a87e3"
GRADING_BYTES = 57218

POOLED = {
    "rows": 36,
    "abstained": 6,
    "marker_variant": 0,
    "answered_rows": 30,
    "answered_rows_with_zero_units": 0,
    "claim_units": 148,
    "ungrounded_units": 59,
    "unsupported_claim_rate": 0.398649,
    "short_units": 12,
    "surface_carrying_units": 26,
    "units_turned_by_the_reference_condition": 0,
    "cross_implementation_disagreements": 0,
}

PER_TIER = {
    "haiku45": {"claim_units": 79, "ungrounded_units": 36},
    "sonnet5": {"claim_units": 36, "ungrounded_units": 12},
    "opus48": {"claim_units": 33, "ungrounded_units": 11},
}


def _committed() -> dict:
    return json.loads(GRADING_PATH.read_text(encoding="utf-8"))


def test_the_grading_artifact_exists_and_ships():
    assert GRADING_PATH.exists(), "the freeze's basis is pinned here but is not in the tree"
    assert GRADING_PATH.stat().st_size == GRADING_BYTES, (
        f"{GRADING_PATH.name} is {GRADING_PATH.stat().st_size} bytes against {GRADING_BYTES}"
    )


def test_the_grading_artifact_matches_its_digest():
    actual = hashlib.sha256(GRADING_PATH.read_bytes()).hexdigest()
    assert actual == GRADING_SHA256


def test_the_committed_artifact_equals_a_fresh_render():
    """Shape asserted on both sides before comparing, since two absent sides compare equal."""
    fresh = json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    committed = GRADING_PATH.read_text(encoding="utf-8")
    assert len(fresh) > 1000 and len(committed) > 1000
    assert json.loads(fresh)["produced_by"] and _committed()["produced_by"]
    assert fresh == committed, "eval/dev_first_pass_grading.json is stale against the grader"


def test_the_pooled_figures_are_the_ones_the_freeze_was_judged_on():
    pooled = _committed()["pooled"]
    for key, expected in POOLED.items():
        assert pooled[key] == expected, f"pooled {key}: {pooled[key]} against {expected}"


def test_the_per_tier_figures_are_the_ones_the_freeze_was_judged_on():
    per_tier = _committed()["per_tier"]
    assert set(per_tier) == {"haiku45", "sonnet5", "opus48"}
    for tier, expected in PER_TIER.items():
        for key, value in expected.items():
            assert per_tier[tier][key] == value, f"{tier} {key}: {per_tier[tier][key]} against {value}"
    assert sum(v["claim_units"] for v in per_tier.values()) == POOLED["claim_units"]
    assert sum(v["ungrounded_units"] for v in per_tier.values()) == POOLED["ungrounded_units"]


def test_the_reference_condition_turned_nothing_and_that_is_disclosed_not_repaired():
    """Section 5.4 requires the count reported whether it is zero or not. It is zero.

    Not because the condition is inert by construction: 26 of the 148 units carry a reference
    surface, so the condition was evaluated on them and admitted every one. The single development
    near-miss row, the stratum the condition exists for, returned the abstention marker on all
    three tiers and so contributed no units at all.
    """
    pooled = _committed()["pooled"]
    assert pooled["units_turned_by_the_reference_condition"] == 0
    assert pooled["surface_carrying_units"] == 26, "the condition must have had units to evaluate"


def test_the_thresholds_recorded_in_the_artifact_are_the_frozen_ones():
    from src.score.grounding import OVERLAP_THRESHOLD, SHORT_UNIT_LENGTH

    thresholds = _committed()["thresholds"]
    assert thresholds["overlap_threshold"] == OVERLAP_THRESHOLD == 0.75
    assert thresholds["short_unit_length"] == SHORT_UNIT_LENGTH == 4


def test_the_figures_are_capable_of_failing():
    """V20. An assertion set that could only pass would certify nothing."""
    pooled = _committed()["pooled"]
    assert pooled["claim_units"] != 147 and pooled["ungrounded_units"] != 58
    assert POOLED["claim_units"] == pooled["claim_units"]
