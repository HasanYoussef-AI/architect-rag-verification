"""The digest pin over the grading results artifact.

IN ITS OWN FILE, following tests/test_results_digest.py and tests/test_layer_results_digest.py and
for the reason they both give. The five sealed digests are pre-registration artifacts whose purpose
is to have existed unchanged since before any result did. eval/test_grading_results.json is a
result, produced at 3c4afec, and it could not have existed before the answers it grades. Mixing it
into SEALED_DIGESTS would assert that a result is pre-registration, which is the one thing the
commit ordering exists to make false.

It is pinned separately from the retrieval and layer results for the reason that separates those
two from each other: all three are results, they are results of different measurements, and a
single pin over several would let a change in one be absorbed by a re-pin nominally about another.
Each artifact carries its own digest and moves only by a logged Rule 4 correction that moves its
pin in the same commit, so no commit in history has an artifact and its digest disagreeing.

WHY PIN IT AT ALL. This is the file every headline number in the study reproduces from: the
unsupported-claim rates, the abstention rates and answered-row counts under the per-condition
predicates, the per-stratum blocks, the flagged-unit fate tables, the two abstention observations,
the adversarial per-row verdicts, the comparable-set comparison and the twenty-six scored sealed
predictions. An unpinned result is a result that can drift under claims already made about it.

THIS PIN AND THE RE-DERIVATION TESTS COVER DIFFERENT SURFACES, AND NEITHER SUBSUMES THE OTHER. That
is why both exist rather than one being redundant.

  tests/test_sealed_grading.py rebuilds the artifact with src.score.run_sealed_grading.build and
  compares the PARSED OBJECTS. It catches the runner and the artifact parting company. It is blind
  to any byte change that preserves the parsed object: reordered keys, changed whitespace, a
  different unicode escaping, translated line endings.

  This file compares BYTES. It catches every one of those, and it is blind to a runner change that
  is never written to disk, which is exactly what the other file catches.

Together they mean reversing either check requires deleting a failing test. Neither alone does.

REPRODUCIBILITY, AND IT NO LONGER CARRIES A PLATFORM CONDITION. The artifact is reproducibility
level 1: its inputs are the nine committed result files under data/runs/, the three committed
flagged artifacts, the committed sealed retrieval results, the committed chunk store and the
committed unit index, and the runner uses no model, no key, no network and no clock. Both halves of
the claim are now true by mechanism. A clone holds these bytes on every platform, because
`.gitattributes` disables end-of-line translation for the whole tree. A reviewer re-running
`python -m src.score.run_sealed_grading` reproduces them on every platform, because the runner
passes `newline="\n"` and pins LF rather than inheriting the runtime's text-mode translation. A
mismatch here is therefore a real divergence, which is what a pin is for.

The re-run half carried a stated condition until the writer was pinned: the runner opened its
output in default text mode, so a runtime writing CRLF produced different bytes without changing a
single figure. That condition was true of the code it described and is now removed at its source
rather than restated, which is preferable to stating it well: a pin whose failure mode a reader
cannot distinguish is a pin that gets deleted the first time it fires, and the way to fix that is
to remove the indistinguishable failure mode.

CORRECTED at the commit that added `.gitattributes`. This paragraph read "This repository carries
no `.gitattributes`, so a checkout configured to translate line endings changes the bytes of every
text artifact in the tree", which was true when written and is false of the tree this file now
ships in. The same commit corrected the stronger claim the two older pins carried, which asserted
reproduction on any machine without either condition.
"""

from __future__ import annotations

import hashlib
import json

from src.ingest.corpus_integrity import REPO_ROOT

GRADING_RESULTS = REPO_ROOT / "eval" / "test_grading_results.json"

# Computed at 3c4afec, the commit that produced the artifact, over the committed blob and over the
# working tree alike. A constant taken from disk alone could differ from what a fresh clone holds.
GRADING_RESULTS_SHA256 = "188dacfb105d5f08ad606bcef2af8e31d836e8000877ca364a3eba8a27ede494"
GRADING_RESULTS_BYTES = 836853


def test_the_grading_results_artifact_exists_and_ships():
    """A pin over a missing file passes by raising somewhere unhelpful, so presence comes first."""
    assert GRADING_RESULTS.exists(), (
        f"{GRADING_RESULTS.name} is pinned here but is not in the tree. The grading of record has "
        "run over all nine sealed run and tier sets and its results are committed; this file's "
        "absence means the artifact was removed"
    )
    assert GRADING_RESULTS.stat().st_size == GRADING_RESULTS_BYTES, (
        f"{GRADING_RESULTS.name} is {GRADING_RESULTS.stat().st_size} bytes against the recorded "
        f"{GRADING_RESULTS_BYTES}"
    )


def test_the_grading_results_artifact_matches_its_pinned_digest():
    """The artifact, against the digest recorded when it was produced."""
    actual = hashlib.sha256(GRADING_RESULTS.read_bytes()).hexdigest()
    assert actual == GRADING_RESULTS_SHA256, (
        f"{GRADING_RESULTS.name}: sha256 {actual} against the pinned {GRADING_RESULTS_SHA256}. "
        "This is the grading of record, which every headline figure in the study reproduces from. "
        "It moves only by an explicit owner-directed Rule 4 correction logged in the commit "
        "message and the session log, and that correction must update this pin in the same commit"
    )


def test_the_grading_results_digest_pin_can_fail():
    """V20, in the pattern both existing result pins use.

    THE WEAK FORM, DELIBERATELY, AND FOR THE REASON THOSE FILES GIVE: a stronger shipped companion
    would have to mutate the committed artifact during a test run, and mutating a result to
    demonstrate a check is not a trade worth making. The strong form was run once, at the commit
    that placed this file, by flipping one byte of the artifact on disk, showing this test red
    naming the mismatch, and restoring the file byte-identically with the digest shown on both
    sides.

    What is shown here is that the comparison distinguishes, that both sides are the same shape so
    a mismatch cannot be an artefact of comparing a digest against something that is not one, and
    that the reader reaches the real file rather than an empty one. Two absent values compare
    equal, which is the failure mode V20 names.
    """
    fabricated = hashlib.sha256(b"not the grading results artifact").hexdigest()
    assert len(fabricated) == len(GRADING_RESULTS_SHA256) == 64
    assert fabricated != GRADING_RESULTS_SHA256

    raw = GRADING_RESULTS.read_bytes()
    assert len(raw) == GRADING_RESULTS_BYTES
    real = hashlib.sha256(raw).hexdigest()
    assert real == GRADING_RESULTS_SHA256
    assert real != fabricated

    # The predicate applied to the same bytes with one appended, in memory. Nothing on disk moves.
    assert hashlib.sha256(raw + b"\n").hexdigest() != GRADING_RESULTS_SHA256


def test_the_three_result_pins_are_over_different_artifacts():
    """A constant copied from another pin would guard the wrong bytes while passing every check
    above.

    COMPARED AGAINST EVERY OTHER RESULT PIN AND NOT AGAINST ONE. With two result pins a pairwise
    check was complete; with three it is not, and a check against a single other pin leaves a pair
    unexamined and narrows further as pins are added. That is the shape widened at d4a32b6 for the
    cross-tier body-digest check, applied here at the pin's first landing rather than after the
    same gap is found again.
    """
    from tests.test_layer_results_digest import LAYER_RESULTS, LAYER_RESULTS_SHA256
    from tests.test_results_digest import RESULTS, RESULTS_SHA256

    paths = [GRADING_RESULTS, LAYER_RESULTS, RESULTS]
    digests = [GRADING_RESULTS_SHA256, LAYER_RESULTS_SHA256, RESULTS_SHA256]
    assert len(set(paths)) == 3, paths
    assert len(set(digests)) == 3, digests
    for path, pinned in zip(paths, digests, strict=True):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned, path


def test_the_pinned_artifact_is_the_one_the_headline_figures_are_read_from():
    """The pin guards the file the claims are made about, not a file with the right name.

    A digest over an artifact nobody reads certifies nothing, and a detector that matches on
    structure while the claim lives in content passes by blindness. This asserts that the pinned
    bytes carry the shape the report's figures are quoted from: three conditions on three tiers,
    the pooled raw and layer rates, zero cross-implementation disagreements, the twenty-six scored
    predictions with their verdict tally, and the no-context condition reporting under its own two
    names rather than as an unsupported-claim rate.
    """
    doc = json.loads(GRADING_RESULTS.read_text(encoding="utf-8"))
    assert doc["reproducibility_level"] == 1
    assert doc["produced_by"] == "python -m src.score.run_sealed_grading"
    assert doc["grader_frozen_at"] == "15e31d5"
    assert doc["conditions"] == ["raw", "layer", "no_context"]
    assert doc["tiers"] == ["haiku45", "sonnet5", "opus48"]

    for condition in doc["conditions"]:
        rows = doc["rows"][condition]
        assert set(rows) == {"haiku45", "sonnet5", "opus48"}
        for tier_rows in rows.values():
            assert len(tier_rows) == 50, "the artifact does not hold the fifty sealed rows"
        assert (
            doc["per_condition"][condition]["pooled"]["cross_implementation_disagreements"] == 0
        )

    raw_pooled = doc["per_condition"]["raw"]["pooled"]
    layer_pooled = doc["per_condition"]["layer"]["pooled"]
    assert (raw_pooled["ungrounded_units"], raw_pooled["claim_units"]) == (120, 269)
    assert (layer_pooled["ungrounded_units"], layer_pooled["claim_units"]) == (80, 266)
    assert raw_pooled["unsupported_claim_rate"] == 0.446097
    assert layer_pooled["unsupported_claim_rate"] == 0.300752

    # Section 6.2: this condition reports two figures under their own names and no third.
    no_context_pooled = doc["per_condition"]["no_context"]["pooled"]
    assert "unsupported_claim_rate" not in no_context_pooled
    assert no_context_pooled["parametric_coincidence_rate"] == 0.033149

    verdicts = [entry["verdict"] for entry in doc["predictions_scored"]]
    assert len(verdicts) == 26, "the artifact does not score the twenty-six sealed predictions"
    assert verdicts.count("held") == 10
    assert verdicts.count("contradicted") == 15
    assert verdicts.count("not_predicted") == 1
