"""Digest pins over the sealed pre-registration artifacts.

PREREGISTRATION.md orders the specification, then the instantiated queries with their gold sets,
their per-edge verification records and their query embeddings, then retrieval, then generation.
Once any result exists these files are immutable except by a logged owner-directed correction.
The commit history is the proof that the scoring rules predate the results, and a digest pin is
what makes an edit to one of them cost a visible line rather than pass as an ordinary diff.

WHAT A RED HERE MEANS. Not that the file is wrong. That it moved. A Rule 4 correction is a
legitimate reason for it to move, and the rule this file adds is that such a correction must move
the pinned digest in the same commit, so the pin and the artifact are never out of step across a
commit boundary. A digest updated in a later commit than the edit is the shape this pin exists to
prevent, because it leaves one commit in history where the record disagrees with itself.

THE EMBEDDING ARRAY'S PIN IS A LOCAL-INTEGRITY CHECK, NOT A PORTABILITY CLAIM. The retrieval
manifest records that regenerating embeddings from ONNX at the pinned revision reproduces
rankings and not bytes across machines, so a reviewer who regenerates the array will not match
this digest and is not expected to. What the pin catches is a local edit, a truncated write, or a
file swapped for another. Its portable properties, shape, dtype, row alignment and L2 norm, are
asserted in tests/test_query_embeddings_provenance.py and are the checks a reviewer runs.
"""

from __future__ import annotations

import hashlib

from src.ingest.corpus_integrity import REPO_ROOT

# Computed at f9dc582, immediately after the Rule 4 correction to eval/test_query_verification.
# jsonl, so the pins freeze corrected bytes rather than the bytes that correction replaced.
SEALED_DIGESTS = {
    "eval/test_queries.jsonl":
        "5c65bc891645d75633126f8127aafb0f7b286a6569ed96c8482fec37323f9f51",
    "eval/test_query_verification.jsonl":
        "04db2449e432274aff97b3c95b8557d10f28f4232d55b09f234f71d57980c117",
    "eval/test_query_embeddings.npy":
        "b354e8de49a8aab966541926a92946fb4cc9c9313f837d11cb9029430a9775bf",
    "eval/pass_one_designations.jsonl":
        "a40140deeb322685d1dbb9256acd90fccb9857d6d729073094c2c52a24c2e2cd",
    "eval/test_frame.json":
        "2f20da0c60eb92028d3fafccbed19573961fb20b6cb40356fd0df6ea6b22942c",
}


def _digest(rel: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()


def test_every_pinned_file_exists_and_ships():
    """A pin over a missing file would pass by raising nowhere useful, so presence comes first."""
    for rel in SEALED_DIGESTS:
        path = REPO_ROOT / rel
        assert path.exists(), f"{rel} is pinned here but is not in the tree"
        assert path.stat().st_size > 0, f"{rel} is present but empty"


def test_the_sealed_artifacts_match_their_pinned_digests():
    """Each sealed file, against the digest recorded when it was last legitimately moved."""
    for rel, expected in SEALED_DIGESTS.items():
        actual = _digest(rel)
        assert actual == expected, (
            f"{rel}: sha256 {actual} against the pinned {expected}. This file is sealed under "
            "PREREGISTRATION.md. It may move only by an explicit owner-directed Rule 4 "
            "correction logged in the commit message and the session log, and that correction "
            "must update this pin in the same commit"
        )


def test_the_digest_pin_can_fail():
    """V20. A hash check never shown to detect a difference certifies nothing.

    The weak form deliberately. A stronger companion would have to mutate a sealed artifact
    during a test run, and mutating a sealed artifact to demonstrate a check is not a trade this
    repository should make. What is shown is that the comparison distinguishes: a digest over
    different bytes differs from every pin, and is the same length, so a mismatch cannot be an
    artefact of comparing a hash against something that is not one.
    """
    fabricated = hashlib.sha256(b"not any sealed artifact").hexdigest()
    assert len(fabricated) == 64
    for rel, expected in SEALED_DIGESTS.items():
        assert len(expected) == 64, f"{rel} carries a pin that is not a sha256"
        assert fabricated != expected, f"{rel} matched a digest over fabricated bytes"

    # And the reader is driven against a real file, so the accessor is shown to work.
    real = _digest("eval/test_frame.json")
    assert real == SEALED_DIGESTS["eval/test_frame.json"]
    assert real != fabricated
