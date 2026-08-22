"""The development second-call artifacts for the Haiku tier, re-derived and asserted.

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

FLAGGED_SHA256 = "07e22e39cf3ba1812de9dce4a0b578483a23cebad0c131cda0717e6fa6612655"
FLAGGED_BYTES = 5367
GRADING_SHA256 = "b8ad5e3608df7e3dade68730df032ca80a09b270fbd42bb6120116cbf0c0a781"
GRADING_BYTES = 21056

POOLED = {
    "rows": 11,
    "layer_abstaining_rows": 3,
    "answered_rows": 8,
    "claim_units": 65,
    "ungrounded_units": 19,
    "unsupported_claim_rate": 0.292308,
    "rows_repeating_a_flagged_unit_unchanged": 7,
    "flagged_units_repeated_unchanged": 14,
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


def test_the_population_is_the_eleven_the_corrective_pass_fires_on():
    rows = _grading()["rows"]
    assert len(rows) == 11
    assert not any(k.endswith("dev_07") for k in rows), (
        "dev_07 is the row the corrective pass is silent on and carries no second call"
    )


def test_the_pooled_second_call_figures():
    pooled = _grading()["pooled"]
    for key, expected in POOLED.items():
        assert pooled[key] == expected, f"pooled {key}: {pooled[key]} against {expected}"


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
        query_id = key.split("__")[-1]
        ungrounded = [
            u["text"]
            for u in first[f"dev__raw__haiku45__{query_id}"]["units"]
            if not u["grounded"]
        ]
        assert record["flagged_units"] == ungrounded, f"{query_id}: flagged list differs"


def test_the_two_abstention_predicates_are_both_exercised():
    """Section 6.1's layer rule has two halves and this run exercised each at least once."""
    rows = _grading()["rows"]
    by_marker = [k for k, r in rows.items() if r["abstained_marker_either_pass"]]
    by_zero = [k for k, r in rows.items() if r["abstained_zero_grounded_after_second_call"]]
    assert by_marker, "no row abstained by the marker half"
    assert by_zero, "no row abstained by the zero-grounded half"
    assert len(set(by_marker) | set(by_zero)) == POOLED["layer_abstaining_rows"]


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


def test_the_figures_are_capable_of_failing():
    """V20. An assertion set that could only pass would certify nothing."""
    pooled = _grading()["pooled"]
    assert pooled["claim_units"] != 64
    assert POOLED["claim_units"] == pooled["claim_units"]
