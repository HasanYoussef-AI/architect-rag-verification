"""The digest pin over the layer results artifact.

IN ITS OWN FILE, following tests/test_results_digest.py and for the same reason. The five sealed
digests are pre-registration artifacts whose purpose is to have existed unchanged since before any
result did. eval/test_layer_results.json is a result, produced at 3be93d2, and it could not have
existed before the components it measures. Mixing it into SEALED_DIGESTS would assert that a result
is pre-registration, which is the one thing the commit ordering exists to make false.

It is pinned separately from the first-pass results for a different reason again: the two are both
results, but they are results of different conditions, and a single pin over both would let a
change in one be absorbed by a re-pin nominally about the other. Each condition's artifact carries
its own digest and moves only by a logged Rule 4 correction that moves its pin in the same commit,
so no commit in history has an artifact and its digest disagreeing.

WHY PIN IT AT ALL. It is the file every layer-condition number reproduces from. The
recovered-passage recall figures, the per-row context set sizes, the recovery sets, the scored
predictions including the one recorded as contradicted, and the drops funnel are all read out of
it, and the generation scope will be scored against the context sets it records. An unpinned result
is a result that can drift under claims already made about it.

REPRODUCIBILITY, STATED WITH ITS CONDITION RATHER THAN AS A UNIVERSAL. Like the first-pass pin and
unlike the embedding array's, this is not a same-machine check. The artifact is reproducibility
level 1 over three committed inputs, the first-pass results, the chunk store and the unit index,
with no model, no key and no optional dependency. A clone holds these bytes on every platform,
because `.gitattributes` disables end-of-line translation for the whole tree. A reviewer
re-running `python -m src.score.run_layer_eval` reproduces them under a runtime whose text mode
writes LF; the runner opens its output in text mode, so a runtime that writes CRLF produces
different bytes without changing a single figure, and a mismatch under that condition is a
platform difference rather than a divergence. tests/test_layer_eval.py asserts that rebuild
directly; this file pins the bytes it produced.

CORRECTED. This paragraph read "A reviewer re-running `python -m src.score.run_layer_eval` on any
machine should reproduce these bytes, so a mismatch here is a real divergence rather than a
platform difference." That was false in both halves at the time it was written, for the reasons
tests/test_results_digest.py records against the same sentence: the repository then carried no
`.gitattributes`, and the producer's text-mode write makes the re-run half platform-dependent
whatever git does. The checkout half is now true by mechanism and the re-run half is stated with
its condition.
"""

from __future__ import annotations

import hashlib
import json

from src.ingest.corpus_integrity import REPO_ROOT

LAYER_RESULTS = REPO_ROOT / "eval" / "test_layer_results.json"

# Computed at 3be93d2, the commit that produced the artifact.
LAYER_RESULTS_SHA256 = "7497e19c9a2a18b8ca5080f20c8b6df9d4bd791c3c0e375a4fa153531e4baffb"
LAYER_RESULTS_BYTES = 104326


def test_the_layer_results_artifact_exists_and_ships():
    """A pin over a missing file passes by raising somewhere unhelpful, so presence comes first."""
    assert LAYER_RESULTS.exists(), (
        f"{LAYER_RESULTS.name} is pinned here but is not in the tree. The layer measurement has run "
        "on the sealed set and its results are committed; this file's absence means the artifact "
        "was removed"
    )
    assert LAYER_RESULTS.stat().st_size == LAYER_RESULTS_BYTES, (
        f"{LAYER_RESULTS.name} is {LAYER_RESULTS.stat().st_size} bytes against the recorded "
        f"{LAYER_RESULTS_BYTES}"
    )


def test_the_layer_results_artifact_matches_its_pinned_digest():
    actual = hashlib.sha256(LAYER_RESULTS.read_bytes()).hexdigest()
    assert actual == LAYER_RESULTS_SHA256, (
        f"{LAYER_RESULTS.name}: sha256 {actual} against the pinned {LAYER_RESULTS_SHA256}. This is "
        "the layer condition's result, which every layer figure reproduces from. It moves only by "
        "an explicit owner-directed Rule 4 correction logged in the commit message and the session "
        "log, and that correction must update this pin in the same commit"
    )


def test_the_layer_results_digest_pin_can_fail():
    """V20, in the pattern the first-pass pin uses.

    The weak form, deliberately and for the same stated reason: a stronger companion would have to
    mutate the committed artifact during a test run, and mutating a result to demonstrate a check is
    not a trade worth making. What is shown is that the comparison distinguishes, that both sides
    are the same shape so a mismatch cannot be an artefact of comparing a hash against something
    that is not one, and that the reader reaches the real file.
    """
    fabricated = hashlib.sha256(b"not the layer results artifact").hexdigest()
    assert len(fabricated) == len(LAYER_RESULTS_SHA256) == 64
    assert fabricated != LAYER_RESULTS_SHA256

    real = hashlib.sha256(LAYER_RESULTS.read_bytes()).hexdigest()
    assert real == LAYER_RESULTS_SHA256
    assert real != fabricated


def test_the_two_result_pins_are_over_different_artifacts():
    """A pin copied from the first-pass file would guard the wrong bytes while passing every check
    above. The two digests and the two paths are asserted distinct."""
    from tests.test_results_digest import RESULTS, RESULTS_SHA256

    assert LAYER_RESULTS != RESULTS
    assert LAYER_RESULTS_SHA256 != RESULTS_SHA256
    assert hashlib.sha256(RESULTS.read_bytes()).hexdigest() == RESULTS_SHA256


def test_the_pinned_artifact_is_the_one_the_layer_figures_are_read_from():
    """The pin guards the file the claims are made about, not a file with the right name.

    A digest over an artifact nobody reads certifies nothing, so this asserts the pinned file
    carries the shape the report's figures are quoted from: fifty rows under the `layer` key, the
    aggregate denominator at 42, the eight gold-empty rows marked rather than dropped, the headline
    pair under two different labels, and the six scored predictions with section 6.3 recorded as
    contradicted.
    """
    doc = json.loads(LAYER_RESULTS.read_text(encoding="utf-8"))
    assert doc["reproducibility_level"] == 1
    assert doc["produced_by"] == "python -m src.score.run_layer_eval"
    assert len(doc["layer"]) == 50, "the artifact does not hold the fifty sealed rows"

    overall = doc["aggregates"]["overall"]
    assert overall["n_queries"] == 42, (
        "the aggregate denominator is not 42, so the adversarial exclusion is not what the report "
        "records"
    )
    marked = [row for row in doc["layer"] if row["recovered_passage_recall"] is None]
    assert len(marked) == 8, f"{len(marked)} rows carry a null layer recall, not the eight adversarial"
    assert all(row["metrics_note"] for row in marked), "a gold-empty row is unmarked"

    # The round-five convention, guarded at the pin as well as at the runner: two conditions, two
    # labels, and no rank-based figure for the layer.
    assert "recall_at_10_first_pass" in overall
    assert "recovered_passage_recall_layer" in overall
    assert "recall_at_10" not in overall
    for banned in ("precision_at_10", "ndcg_at_10", "mrr"):
        assert banned not in overall

    verdicts = {entry["section"]: entry["verdict"] for entry in doc["predictions_scored"]}
    assert verdicts == {
        "6.1": "held", "6.2": "held", "6.3": "contradicted",
        "6.4": "held", "6.5": "held", "6.6": "held",
    }, "the scored predictions are not the six the report records"
