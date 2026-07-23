"""Tests for NIST AI 600-1 ingestion, the Generative AI Profile.

The invariants that stand in for a PDF's absent structure are the same three as
AI 100-1: a partition proof over the full raw extraction, structure-derived
identifiers, and an exact-substring assertion. Two things are specific here: the
212th action id is garbled in the source PDF and recovered under a single
documented exception, and the action-to-subcategory relation is its own field.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from src.ingest.nist_ai_600_1 import (
    DOC_ID,
    OUTPUT_DIR,
    _ACTION_STRICT,
    _ACTION_TOLERANT,
    applied_hyphen_decisions,
    build,
)
from src.ingest.tokenization import MAX_TOKENS


@pytest.fixture(scope="module")
def ingested():
    manifest = build()

    def read(name):
        return (OUTPUT_DIR / name).read_text(encoding="utf-8")

    chunks = [json.loads(x) for x in read(f"{DOC_ID}.chunks.jsonl").splitlines()]
    relations = [json.loads(x) for x in read(f"{DOC_ID}.relations.jsonl").splitlines()]
    audit = [json.loads(x) for x in read(f"{DOC_ID}.prose_xref_audit.jsonl").splitlines()]
    normalized = read(f"{DOC_ID}.normalized.txt")
    extracted = read(f"{DOC_ID}.extracted.txt")
    return manifest, chunks, relations, audit, normalized, extracted


# --------------------------------------------------------------------------
# Partition and no-reconstruction
# --------------------------------------------------------------------------

def test_partition_accounts_for_the_entire_raw_extraction(ingested):
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    assert proof["raw_fully_accounted"] is True
    assert proof["raw_chars_accounted"] == proof["raw_chars"]
    assert (
        proof["content_chars"]
        + proof["discarded_chars_total"]
        + proof["structural_whitespace_total"]
        == proof["raw_chars"]
    )
    assert proof["unassigned_content_lines"] == 0
    assert proof["lines_assigned_more_than_once"] == 0


def test_the_table_header_is_a_named_discard_class(ingested):
    """The repeated 'Action ID Suggested Action GAI Risks' header on 48 pages."""
    manifest, *_ = ingested
    assert "table_header" in manifest["partition_proof"]["discarded_chars_by_class"]


def test_every_chunk_is_an_exact_substring_of_the_persisted_text(ingested):
    manifest, chunks, _, _, normalized, _ = ingested
    for chunk in chunks:
        assert normalized[chunk["char_start"] : chunk["char_end"]] == chunk["text"], chunk["chunk_id"]


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------

def test_49_subcategories_and_212_actions(ingested):
    manifest, *_ = ingested
    assert manifest["structure"]["subcategories_referenced"] == 49
    assert manifest["structure"]["action_identifiers"] == 212


def test_chunk_ids_unique_and_no_chunk_over_cap(ingested):
    _, chunks, _, _, _, _ = ingested
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
    assert [c["chunk_id"] for c in chunks if c["token_count"] > MAX_TOKENS] == []


def test_the_references_appendix_is_chunked_and_tagged_not_excluded(ingested):
    _, chunks, _, _, _, _ = ingested
    references = [c for c in chunks if c["unit_type"] == "references"]
    assert references, "the References bibliography must be kept, chunked and tagged"
    assert all(c["parent_id"] == f"{DOC_ID}:app_B" for c in references)


def test_two_consecutive_runs_produce_identical_output(ingested):
    first, *_ = ingested
    assert first == build()


# --------------------------------------------------------------------------
# The single documented garbled-identifier exception
# --------------------------------------------------------------------------

def test_the_garbled_action_id_is_recovered_under_the_documented_exception(ingested):
    """GV-4.3-001 prints garbled as GV4.3--001 in the source PDF, recovered by
    the tolerant anchor which validates its three components."""
    manifest, chunks, _, _, _, extracted = ingested
    exception = manifest["garbled_identifier_exception"]
    assert exception["stored_surface"] == "GV4.3--001"
    assert exception["derived_unit_id"] == f"{DOC_ID}:act_GV-4.3-001"
    # stored text keeps the garble verbatim, so the exact-substring assertion holds
    assert "GV4.3--001" in extracted
    assert any("GV4.3--001" in c["text"] for c in chunks)
    # the derived key exists as a real action unit
    assert f"{DOC_ID}:act_GV-4.3-001" in {c["parent_id"] for c in chunks}


def test_tolerant_recovers_exactly_one_row_beyond_strict_and_it_is_this_one(ingested):
    manifest, chunks, _, _, _, _ = ingested
    assert manifest["structure"]["action_identifiers_strict"] == 211
    assert manifest["structure"]["action_identifiers_recovered"] == 1
    assert _ACTION_TOLERANT.match("GV4.3--001")
    assert not _ACTION_STRICT.match("GV4.3--001")
    assert _ACTION_STRICT.match("GV-4.3-002")


def test_no_duplicate_action_ids_and_the_recovery_fills_a_gap(ingested):
    _, chunks, _, _, _, _ = ingested
    actions = sorted({c["parent_id"] for c in chunks if c["unit_type"] == "action"})
    assert len(actions) == 212
    # GV-4.3 now runs 001, 002, 003 with no gap and no collision
    gv43 = sorted(a for a in actions if a.startswith(f"{DOC_ID}:act_GV-4.3-"))
    assert gv43 == [f"{DOC_ID}:act_GV-4.3-00{n}" for n in (1, 2, 3)]


# --------------------------------------------------------------------------
# Relations
# --------------------------------------------------------------------------

def test_action_subcategory_is_its_own_field_and_resolves(ingested):
    _, chunks, relations, _, _, _ = ingested
    unit_ids = {c["parent_id"] for c in chunks}
    edges = [e for r in relations for e in r.get("action_subcategory", [])]
    assert len(edges) == 212
    for edge in edges:
        assert edge["unit_id"] in unit_ids
        assert edge["unit_id"].startswith(f"{DOC_ID}:sub_")


def test_structural_join_kept_separate_from_action_and_prose(ingested):
    _, _, relations, _, _, _ = ingested
    for record in relations:
        assert "structural_join" in record
        assert "action_subcategory" in record
        assert "prose_xrefs" in record


def test_the_two_demonstrated_prose_collisions_classify_correctly(ingested):
    """Section X of EO 14110 is external; See Appendix A of the AI RMF is cross-document."""
    _, _, _, audit, _, _ = ingested
    external = [a for a in audit if a["classification"] == "external"]
    assert any(a["surface"].startswith("Section") and "EO" in a["detail"] for a in external)
    cross = [a for a in audit if a["classification"] == "cross_document"]
    assert any(a.get("target") == "nist_ai_100_1:app_A" for a in cross)


def test_every_prose_reference_has_a_class(ingested):
    _, _, _, audit, _, _ = ingested
    assert audit
    assert all(a["classification"] in {"internal", "cross_document", "external"} for a in audit)


# --------------------------------------------------------------------------
# Hyphen resolution agreement and non-ASCII
# --------------------------------------------------------------------------

def test_applied_hyphenation_agrees_with_the_committed_decision_log():
    log_path = OUTPUT_DIR.parent / "hyphenation" / "decision_log.jsonl"
    log = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()]
    key_fields = (
        "left", "right", "hyphenated", "joined",
        "hyphen_evidence", "joined_evidence", "rule", "outcome",
    )
    log_ms = Counter(
        tuple(row[k] for k in key_fields) for row in log if row["doc_id"] == DOC_ID
    )
    applied_ms = Counter(
        tuple(getattr(d, k) for k in key_fields) for d in applied_hyphen_decisions()
    )
    assert not (applied_ms - log_ms), "an applied decision does not match the committed log"


def test_non_ascii_inventory_and_comparison_note_recorded(ingested):
    manifest, *_ = ingested
    notes = manifest["downstream_notes"]
    assert "comparison_time_normalisation" in notes
    inventory = notes["non_ascii_inventory"]
    assert inventory
    handlings = {entry["handling"] for entry in inventory}
    assert "normalise_at_comparison_time" in handlings
    assert "leave_alone_genuine_content" in handlings
