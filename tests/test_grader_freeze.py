"""The freeze: digest pins over the four grader modules.

WHAT THE FREEZE IS. eval/generation_predictions.md section 5.4 separates two acts. The MODULE
COMMIT, 9e1e021, built the grader and carried the section 5.2 thresholds as candidates. The FREEZE
COMMIT, this one, follows the development first pass and precedes the development second calls, and
records that no threshold moved. After it, no threshold moves again for any reason.

This file makes that mechanical rather than declared. Any edit to any of the four modules turns it
red, so reversing the freeze requires deleting a failing test, which is V13 applied to a decision
rather than to a defect.

WHAT THIS PIN DOES NOT COVER, STATED SO IT IS NOT MISTAKEN FOR COMPLETE. The four modules import
src/complete/references.py, src/ingest/normalize.py, src/retrieve/tokenize.py and, for the marker,
src/generate/prompts.py. An edit to any of those changes what the grader does while every digest
here stays green. The behavioural pin closes that surface: tests/test_dev_grading.py re-derives the
grading from the committed answers and asserts the figures, so a dependency change that alters a
verdict turns THAT red. The two pins cover different things and only together cover the grader.

WHY DIGESTS AND NOT A BEHAVIOURAL PIN ALONE. A behavioural pin passes on any edit that does not
change a verdict on these thirty-six answers, and the development set is small enough that many
real changes would not. The freeze is a claim about the code, not only about its output on one
sample, so the code is pinned as bytes.

Pinned at the freeze commit, following tests/test_layer_results_digest.py and
tests/test_results_digest.py: presence and size first, because a pin over a missing file passes by
raising somewhere unhelpful, then the digest.
"""

from __future__ import annotations

import hashlib

import pytest

from src.ingest.corpus_integrity import REPO_ROOT

# The grader of record and its second implementation, as frozen. Computed at the freeze commit.
FROZEN_MODULES = {
    "src/score/claims.py": ("a6daae1c4839f5c89e4142c4c7f9f61d80d47bc05a04fb0337dca7b7c9ee2260", 6657),
    "src/score/grounding.py": ("8e26746d9343a6bfbcbace0868c537f72c987f9282cdf92dd02b318845f0f59e", 9532),
    "src/score/adversarial.py": ("bf4d2fa4237920ca154de1717e539a57fc95eca914fdca0784ffee0108975907", 9318),
    "src/complete/flagging.py": ("289892cc845ff1a9e0440f33f3f51a367cbfb702d83bc021d12a12daa81b681b", 7321),
}


@pytest.mark.parametrize("relative", sorted(FROZEN_MODULES))
def test_the_frozen_module_exists_and_ships(relative):
    path = REPO_ROOT / relative
    expected_size = FROZEN_MODULES[relative][1]
    assert path.exists(), f"{relative} is pinned by the freeze but is not in the tree"
    assert path.stat().st_size == expected_size, (
        f"{relative} is {path.stat().st_size} bytes against the frozen {expected_size}"
    )


@pytest.mark.parametrize("relative", sorted(FROZEN_MODULES))
def test_the_frozen_module_matches_its_digest(relative):
    path = REPO_ROOT / relative
    expected = FROZEN_MODULES[relative][0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (
        f"{relative}: sha256 {actual} against the frozen {expected}. This module is frozen by "
        "eval/generation_predictions.md section 5.4. After the freeze commit no threshold moves "
        "and the grader does not change. Editing it means deleting this assertion, which is the "
        "point: the decision is reversed in the open or not at all."
    )


def test_the_freeze_covers_all_four_modules_and_no_others():
    """The set is the one section 13 names, so a module cannot be dropped from the freeze quietly."""
    assert set(FROZEN_MODULES) == {
        "src/score/claims.py",
        "src/score/grounding.py",
        "src/score/adversarial.py",
        "src/complete/flagging.py",
    }


def test_the_digest_check_is_capable_of_failing():
    """V20. A pin that could only pass would certify nothing.

    The predicate is run against the same file with one byte appended, in memory, and must reject
    it. Nothing on disk is touched.
    """
    path = REPO_ROOT / "src/score/grounding.py"
    real = path.read_bytes()
    assert hashlib.sha256(real).hexdigest() == FROZEN_MODULES["src/score/grounding.py"][0]
    mutated = real + b"\n"
    assert hashlib.sha256(mutated).hexdigest() != FROZEN_MODULES["src/score/grounding.py"][0]
    assert len(mutated) != FROZEN_MODULES["src/score/grounding.py"][1]
