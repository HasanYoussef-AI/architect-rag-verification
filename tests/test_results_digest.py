"""The digest pin over the retrieval results artifact.

DELIBERATELY NOT IN tests/test_sealed_set_digests.py, and the separation is the point.

Those five files are pre-registration artifacts: the queries, their gold sets, the per-edge
verification records, the pass-one designations and the frame. PREREGISTRATION.md orders them
before retrieval runs, and their whole purpose is to have existed unchanged since before any
result did. eval/test_retrieval_results.json is the opposite kind of object. It is a RESULT,
produced by retrieval at 356f23d, and it could not have existed earlier without breaking the
ordering it now closes.

What the two regimes share is the correction rule and nothing else. This file moves only by a
logged Rule 4 correction that moves the pin in the same commit, so no commit in history has the
artifact and its digest disagreeing. Mixing it into SEALED_DIGESTS would say that a result is
pre-registration, which is the one thing the commit ordering exists to make false.

WHY PIN IT AT ALL. It is the file every downstream number reproduces from. The four frozen metrics,
the per-stratum aggregates, the miss list and the carrier counts are all read out of it, and the
generation runs will be scored against the rankings it records. An unpinned result is a result that
can drift under the claims made about it, and the claims are already written into the session log.

REPRODUCIBILITY, STATED WITH ITS CONDITION RATHER THAN AS A UNIVERSAL. Unlike the embedding
array's pin, this one is not a same-machine check. The artifact is reproducibility level 1: its
inputs are the committed query file, the committed query embeddings, the committed chunk
embeddings and the committed chunk order, and the runner uses no model and no key. A clone holds
these bytes on every platform, because `.gitattributes` disables end-of-line translation for the
whole tree. A reviewer who re-runs `python -m src.score.run_retrieval_eval` reproduces them under
a runtime whose text mode writes LF; the runner opens its output in text mode, so a runtime that
writes CRLF produces different bytes without changing a single figure, and a mismatch under that
condition is a platform difference rather than a divergence.

CORRECTED. This paragraph read "A reviewer who re-runs `python -m src.score.run_retrieval_eval` on
any machine should reproduce these bytes exactly, so a mismatch here is a real divergence rather
than a platform difference." That was false in both halves at the time it was written: the
repository then carried no `.gitattributes`, so a checkout configured to translate line endings
changed the bytes of every text artifact in the tree, and the producer's text-mode write makes the
re-run half platform-dependent whatever git does. The checkout half is now true by mechanism and
the re-run half is stated with its condition. A pin whose failure mode a reader cannot distinguish
is a pin that gets deleted the first time it fires.
"""

from __future__ import annotations

import hashlib
import json

from src.ingest.corpus_integrity import REPO_ROOT

RESULTS = REPO_ROOT / "eval" / "test_retrieval_results.json"

# Computed at 356f23d, the commit that produced the artifact.
RESULTS_SHA256 = "daf58a42a9d77acf91ef0cb168f940f774bc395a08da17dafff27eb91bd763d2"
RESULTS_BYTES = 71723


def test_the_results_artifact_exists_and_ships():
    """A pin over a missing file passes by raising somewhere unhelpful, so presence comes first."""
    assert RESULTS.exists(), (
        f"{RESULTS.name} is pinned here but is not in the tree. Retrieval has run on the sealed "
        "set and its results are committed; this file's absence means the artifact was removed"
    )
    assert RESULTS.stat().st_size == RESULTS_BYTES, (
        f"{RESULTS.name} is {RESULTS.stat().st_size} bytes against the recorded {RESULTS_BYTES}"
    )


def test_the_results_artifact_matches_its_pinned_digest():
    """The artifact, against the digest recorded when it was produced."""
    actual = hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    assert actual == RESULTS_SHA256, (
        f"{RESULTS.name}: sha256 {actual} against the pinned {RESULTS_SHA256}. This is the "
        "retrieval result every downstream number reproduces from. It moves only by an explicit "
        "owner-directed Rule 4 correction logged in the commit message and the session log, and "
        "that correction must update this pin in the same commit"
    )


def test_the_results_digest_pin_can_fail():
    """V20, in the pattern the sealed pins use.

    The weak form, deliberately and for the same reason: a stronger companion would have to mutate
    the committed artifact during a test run, and mutating a result to demonstrate a check is not
    a trade worth making. What is shown is that the comparison distinguishes, that both sides are
    the same shape so a mismatch cannot be an artefact of comparing a hash against something that
    is not one, and that the reader reaches the real file.
    """
    fabricated = hashlib.sha256(b"not the results artifact").hexdigest()
    assert len(fabricated) == len(RESULTS_SHA256) == 64
    assert fabricated != RESULTS_SHA256

    real = hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    assert real == RESULTS_SHA256
    assert real != fabricated


def test_the_pinned_artifact_is_the_one_the_metrics_are_read_from():
    """The pin guards the file the claims are made about, not a file with the right name.

    A digest over an artifact nobody reads certifies nothing, so this asserts the pinned file
    carries the shape the session log's figures are quoted from: fifty rows under the `retrieval`
    key, the aggregate denominator at 42, and the eight gold-empty rows marked rather than dropped.
    """
    doc = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert doc["reproducibility_level"] == 1
    assert doc["produced_by"] == "python -m src.score.run_retrieval_eval"
    assert len(doc["retrieval"]) == 50, "the artifact does not hold the fifty sealed rows"
    assert doc["aggregates"]["overall"]["n_queries"] == 42, (
        "the aggregate denominator is not 42, so the adversarial exclusion is not what the log "
        "records"
    )
    marked = [q for q in doc["retrieval"] if q["metrics"] is None]
    assert len(marked) == 8, f"{len(marked)} rows carry metrics null, not the eight adversarial"
    assert all(q["metrics_note"] for q in marked), "a gold-empty row is unmarked"
