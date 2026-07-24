"""Tests for the NIST AI RMF Playbook ingestion.

The Playbook prints the Core statement then five blocks per subcategory. The Core
statement is a separate unit from its blocks, the References blocks are chunked
and tagged rather than excluded, and the 'N of 142' footer is discarded
positionally so it never joins the text on either side of it.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from src.ingest.nist_playbook import DOC_ID, OUTPUT_DIR, applied_hyphen_decisions, build
from src.ingest.tokenization import MAX_TOKENS


@pytest.fixture(scope="module")
def ingested():
    manifest = build()

    def read(name):
        return (OUTPUT_DIR / name).read_text(encoding="utf-8")

    chunks = [json.loads(x) for x in read(f"{DOC_ID}.chunks.jsonl").splitlines()]
    relations = [json.loads(x) for x in read(f"{DOC_ID}.relations.jsonl").splitlines()]
    audit = [json.loads(x) for x in read(f"{DOC_ID}.prose_xref_audit.jsonl").splitlines()]
    return manifest, chunks, relations, audit, read(f"{DOC_ID}.normalized.txt")


def test_partition_accounts_for_the_entire_raw_extraction(ingested):
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    assert proof["raw_fully_accounted"] is True
    assert (
        proof["content_chars"]
        + proof["discarded_chars_total"]
        + proof["structural_whitespace_total"]
        == proof["raw_chars"]
    )
    assert proof["unassigned_content_lines"] == 0
    assert proof["lines_assigned_more_than_once"] == 0


def test_the_positional_footer_is_a_named_discard_class(ingested):
    manifest, *_ = ingested
    assert "page_footer" in manifest["partition_proof"]["discarded_chars_by_class"]
    assert "page_footer_is_positional" in manifest["downstream_notes"]


def test_every_chunk_is_an_exact_substring_of_the_persisted_text(ingested):
    _, chunks, _, _, normalized = ingested
    for chunk in chunks:
        assert normalized[chunk["char_start"] : chunk["char_end"]] == chunk["text"], chunk["chunk_id"]


def test_72_subcategory_statements_and_five_blocks_each(ingested):
    manifest, chunks, _, _, _ = ingested
    assert manifest["structure"]["subcategory_statements"] == 72
    by_type = Counter(c["unit_type"] for c in chunks)
    for block in (
        "playbook_about",
        "playbook_suggested_actions",
        "playbook_transparency_documentation",
        "playbook_ai_transparency_resources",
    ):
        assert by_type[block] >= 72, block


def test_the_core_statement_is_a_separate_unit_from_its_blocks(ingested):
    _, chunks, _, _, _ = ingested
    parents = {c["parent_id"] for c in chunks}
    assert f"{DOC_ID}:sub_GOVERN_1.1" in parents
    assert f"{DOC_ID}:sub_GOVERN_1.1.about" in parents


def test_references_blocks_are_chunked_and_tagged_not_excluded(ingested):
    manifest, chunks, _, _, _ = ingested
    references = [c for c in chunks if c["unit_type"] == "playbook_references"]
    assert len(references) >= 72
    assert "references_blocks_are_bibliography" in manifest["downstream_notes"]


def test_chunk_ids_unique_and_no_chunk_over_cap(ingested):
    _, chunks, _, _, _ = ingested
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
    assert [c["chunk_id"] for c in chunks if c["token_count"] > MAX_TOKENS] == []


def test_structural_join_is_symmetric_to_both_documents(ingested):
    """Symmetric: 72 edges to AI 100-1 (all 72 subcategories) and 49 to AI 600-1."""
    manifest, _, relations, _, _ = ingested
    decomposition = Counter(
        join["doc_id"] for r in relations for join in r.get("structural_join", [])
    )
    assert manifest["relations"]["structural_join_edges"] == 121
    assert decomposition == {"nist_ai_100_1": 72, "nist_ai_600_1": 49}
    for record in relations:
        for join in record.get("structural_join", []):
            assert join["unit_id"].startswith(f"{join['doc_id']}:sub_")


def test_the_one_prose_reference_is_external_iso(ingested):
    """The Playbook's single prose reference is Section 6 of ISO/IEC CD 5339."""
    _, _, _, audit, _ = ingested
    assert len(audit) == 1
    assert audit[0]["classification"] == "external"
    assert "ISO" in audit[0]["detail"]


def test_two_consecutive_runs_produce_identical_output(ingested):
    first, *_ = ingested
    assert first == build()


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
    assert notes["non_ascii_inventory"]
