"""The digest pin over the alignment control artifact.

IN ITS OWN FILE, following tests/test_layer_results_digest.py and for the same reason: a pin over
one artifact does not belong inside a file whose subject is another, or a re-pin nominally about
one can absorb a change in the other.

NOT ONE OF THE THREE RESULT PINS, AND THE BOUNDARY IS STATED RATHER THAN ASSUMED.
eval/test_retrieval_results.json, eval/test_layer_results.json and eval/test_grading_results.json
are the outputs of the three measured conditions, and the disagreement check in each of those three
files asserts they are pins over different artifacts. eval/test_flagged_alignment_control.json is
not a fourth condition. It is a property of the grading predicate measured over a population the
grading artifact defines, which is why it is classed in its own text as an instrument measurement
and pinned here rather than folded into that family. The check below still compares this digest
against all three of theirs, because a pin copied from another file would guard the wrong bytes
while passing every other assertion in this file.

WHY PIN IT AT ALL. docs/RESULTS.md states that every figure it carries is read from a digest-pinned
artifact. The retrospective that will cite this measurement needs that sentence to stay true
without qualification, and a figure published ahead of a pinned producer is the ordering V16 exists
to prevent.

REPRODUCIBILITY, WITH NO PLATFORM CONDITION. Level 1 over committed inputs: the three flagged
lists, the grading results, the sealed queries and the chunk store, with no model, no key, no
network and no optional dependency. A clone holds these bytes on every platform because
`.gitattributes` disables end-of-line translation for the whole tree, and a reviewer re-running the
producer reproduces them on every platform because it passes `newline="\n"` rather than inheriting
the runtime's text-mode translation. tests/test_flagged_alignment_control.py asserts that rebuild
directly; this file pins the bytes it produced.
"""

from __future__ import annotations

import hashlib
import json

from src.ingest.corpus_integrity import REPO_ROOT

CONTROL = REPO_ROOT / "eval" / "test_flagged_alignment_control.json"

# Computed at the commit that produced the artifact.
CONTROL_SHA256 = "375253251d7910bb4e8a390f5420630d7643dbfee477fb1a3191ce33cb5f868d"
CONTROL_BYTES = 261299


def test_the_control_artifact_exists_and_ships():
    """A pin over a missing file passes by raising somewhere unhelpful, so presence comes first."""
    assert CONTROL.exists(), (
        f"{CONTROL.name} is pinned here but is not in the tree. It is the measurement behind the "
        "flagged-unit alignment figures, and its absence means the artifact was removed"
    )
    assert CONTROL.stat().st_size == CONTROL_BYTES, (
        f"{CONTROL.name} is {CONTROL.stat().st_size} bytes against the recorded {CONTROL_BYTES}"
    )


def test_the_control_artifact_matches_its_pinned_digest():
    actual = hashlib.sha256(CONTROL.read_bytes()).hexdigest()
    assert actual == CONTROL_SHA256, (
        f"{CONTROL.name}: sha256 {actual} against the pinned {CONTROL_SHA256}. This is the "
        "measurement every flagged-unit alignment figure reproduces from. It moves only by an "
        "explicit owner-directed correction logged in the commit message and the session log, and "
        "that correction must update this pin in the same commit"
    )


def test_the_control_digest_pin_can_fail():
    """V20, in the pattern the three result pins use.

    The weak form, deliberately and for their stated reason: a stronger companion would have to
    mutate the committed artifact during a test run. What is shown is that the comparison
    distinguishes, that both sides are the same shape so a pass cannot be an artefact of comparing
    a hash against something that is not one, and that the reader reaches the real file.
    """
    fabricated = hashlib.sha256(b"not the alignment control artifact").hexdigest()
    assert len(fabricated) == len(CONTROL_SHA256) == 64
    assert fabricated != CONTROL_SHA256

    real = hashlib.sha256(CONTROL.read_bytes()).hexdigest()
    assert real == CONTROL_SHA256
    assert real != fabricated


def test_this_pin_is_over_different_bytes_from_every_result_pin():
    """A digest copied from another artifact's pin would guard the wrong file while passing above.

    Compared against all three result pins rather than one, on the reasoning those three files
    already record: a check against a single other pin leaves the rest unexamined.
    """
    from tests.test_grading_results_digest import GRADING_RESULTS, GRADING_RESULTS_SHA256
    from tests.test_layer_results_digest import LAYER_RESULTS, LAYER_RESULTS_SHA256
    from tests.test_results_digest import RESULTS, RESULTS_SHA256

    paths = [CONTROL, LAYER_RESULTS, GRADING_RESULTS, RESULTS]
    digests = [CONTROL_SHA256, LAYER_RESULTS_SHA256, GRADING_RESULTS_SHA256, RESULTS_SHA256]
    assert len(set(paths)) == 4, paths
    assert len(set(digests)) == 4, digests
    for path, pinned in zip(paths, digests, strict=True):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned, path


def test_the_pinned_artifact_is_the_one_the_alignment_figures_are_read_from():
    """The pin guards the file the claims are made about, not a file with the right name.

    A digest over an artifact nobody reads certifies nothing, so this asserts the pinned file
    carries the shape the figures are quoted from: the 109 flagged units, the enumerated null with
    one pair per unit per foreign row, the paired counts, the per-tier block, and the continuity
    figures that record there is no cut to read off.
    """
    doc = json.loads(CONTROL.read_text(encoding="utf-8"))
    assert doc["reproducibility_level"] == 1
    assert doc["produced_by"] == "python -m src.score.run_flagged_alignment_control"
    assert len(doc["units"]) == 109, "the artifact does not hold the 109 flagged units"
    assert doc["population"]["flagged_units"] == 109

    assert doc["null_distribution"]["pairs"] == 109 * 49, (
        "the null is not the enumerated one, so the sampling decision the artifact states is not "
        "the one it carries"
    )
    assert doc["coverage"]["sealed_rows"] == 50

    paired = doc["paired_result"]
    assert paired["beats_every_foreign_row"] + paired["does_not_beat_every_foreign_row"] == 109

    assert set(doc["tier_heterogeneity"]["per_tier"]) == {"haiku45", "sonnet5", "opus48"}

    # The continuity block is what says a threshold would have to be invented. If it ever reports a
    # gap that dominates the range, that is a finding and not a formatting change.
    continuity = doc["continuity"]
    assert continuity["overlap_max_largest_gaps"][0]["gap"] < continuity["overlap_max_range"] / 5
