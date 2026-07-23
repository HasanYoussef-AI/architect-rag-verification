"""Tests for NIST AI 100-1 ingestion.

A PDF declares nothing about its own structure, so the invariants asserted here
are what stand in for the ELI anchors the EU AI Act provided. In particular the
partition proof and the exact-substring assertion are not conveniences: they are
what make silent content loss and text reconstruction detectable rather than
plausible-looking.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.nist_ai_100_1 import (
    DOC_ID,
    OUTPUT_DIR,
    build,
    match_form,
    parse_toc,
)
from src.ingest.pdf_extract import SOFT_HYPHEN_BREAK, extract_pages
from src.ingest.tokenization import MAX_TOKENS, count_tokens

EXPECTED_PER_FUNCTION = {"GOVERN": 19, "MANAGE": 13, "MAP": 18, "MEASURE": 22}


@pytest.fixture(scope="module")
def ingested():
    manifest = build()

    def read(name: str) -> str:
        return (OUTPUT_DIR / name).read_text(encoding="utf-8")

    chunks = [json.loads(x) for x in read(f"{DOC_ID}.chunks.jsonl").splitlines()]
    relations = [json.loads(x) for x in read(f"{DOC_ID}.relations.jsonl").splitlines()]
    duplication = json.loads(read(f"{DOC_ID}.duplication_map.json"))
    return manifest, chunks, relations, duplication, read(f"{DOC_ID}.normalized.txt")


# --------------------------------------------------------------------------
# Partition proof
# --------------------------------------------------------------------------

def test_partition_is_complete(ingested):
    """Every content character lands in exactly one unit. No gaps, no overlaps."""
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    assert proof["complete"] is True
    assert proof["unassigned_content_lines"] == 0
    assert proof["lines_assigned_more_than_once"] == 0
    assert proof["assigned_to_units_chars"] == proof["content_chars"]


def test_discards_are_named_and_bounded(ingested):
    """Discarding is allowed, discarding silently is not."""
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    assert set(proof["discarded_chars_by_class"]) == {
        "front_matter",
        "page_footer",
        "running_header",
        "table_continuation",
    }
    assert proof["discarded_fraction_of_lines"] < 0.10
    assert (
        proof["content_chars"] + proof["discarded_chars_total"] == proof["line_chars"]
    )


def test_the_last_unit_does_not_run_to_the_end_of_the_document(ingested):
    """The overrun failure mode: a final unit swallowing everything after it."""
    _, chunks, _, _, _ = ingested
    last = [c for c in chunks if c["parent_id"] == f"{DOC_ID}:app_D"]
    assert last
    assert sum(c["token_count"] for c in last) < 2000


# --------------------------------------------------------------------------
# Structure, validated against the document's own Table of Contents
# --------------------------------------------------------------------------

def test_every_declared_toc_entry_is_located(ingested):
    manifest, *_ = ingested
    structure = manifest["structure"]
    assert structure["anchors_located"] == structure["toc_entries_declared"]
    assert structure["toc_entries_declared"] >= 30


def test_toc_parses_the_documents_declared_structure():
    toc = parse_toc(extract_pages(OUTPUT_DIR.parent.parent / "corpus/nist_ai_rmf/raw/NIST.AI.100-1.pdf"))
    keys = [key for key, _ in toc]
    assert "Executive Summary" in keys
    assert "Part 1" in keys and "Part 2" in keys
    assert "Appendix A" in keys and "Appendix D" in keys
    assert "5.1" in keys


def test_exactly_72_subcategories_with_the_expected_distribution(ingested):
    """72 is derived from the document, and matches the Playbook independently."""
    manifest, chunks, _, _, _ = ingested
    assert manifest["structure"]["subcategories"] == 72
    assert manifest["structure"]["subcategories_per_function"] == EXPECTED_PER_FUNCTION
    units = {c["parent_id"] for c in chunks if c["unit_type"] == "subcategory"}
    assert len(units) == 72


def test_enumerated_list_items_in_appendices_are_not_mistaken_for_sections(ingested):
    """Appendices C and D contain "3. Use clear and plain language..." style items.

    They look exactly like section headings and appear in no TOC, so they must
    not become units.
    """
    _, chunks, _, _, _ = ingested
    units = {c["parent_id"] for c in chunks}
    assert f"{DOC_ID}:sec_9" not in units
    assert f"{DOC_ID}:sec_7" not in units


# --------------------------------------------------------------------------
# The no-reconstruction guarantee
# --------------------------------------------------------------------------

def test_every_chunk_is_an_exact_substring_of_the_persisted_text(ingested):
    """Text originating anywhere other than the PDF fails this mechanically."""
    _, chunks, _, _, text = ingested
    for chunk in chunks:
        assert text[chunk["char_start"] : chunk["char_end"]] == chunk["text"], chunk["chunk_id"]


def test_no_soft_hyphen_marker_survives_into_chunks(ingested):
    _, chunks, _, _, _ = ingested
    assert not any(SOFT_HYPHEN_BREAK in c["text"] for c in chunks)


def test_a_known_split_word_is_rejoined(ingested):
    _, _, _, _, text = ingested
    assert "integrated" in text
    assert f"inte{SOFT_HYPHEN_BREAK}grated" not in text


# The class of defect the hyphen resolver exists to prevent: a real compound
# hyphen deleted at a line break, welding two words into one. Pinned both
# directions, so reintroducing the delete-the-hyphen rule fails these tests.
THIRDPARTY_DEFECT_CLASS = [
    ("thirdparty", "third-party"),
    ("decisionmaking", "decision-making"),
    ("humanAI", "human-AI"),
    ("privacyenhancing", "privacy-enhancing"),
    ("contextspecific", "context-specific"),
]


def test_the_thirdparty_defect_class_is_fixed_both_directions(ingested):
    """Corrupted joined forms are gone and the correct hyphenated forms are present."""
    _, chunks, _, _, text = ingested
    chunk_text = "\n".join(c["text"] for c in chunks)
    for corrupted, fixed in THIRDPARTY_DEFECT_CLASS:
        assert corrupted not in text, f"corrupted {corrupted!r} present in normalized text"
        assert corrupted not in chunk_text, f"corrupted {corrupted!r} present in chunk text"
        assert fixed in text, f"fixed {fixed!r} absent from normalized text"
        assert fixed in chunk_text, f"fixed {fixed!r} absent from chunk text"


def test_applied_hyphenation_agrees_with_the_committed_decision_log():
    """The result applied to the document must match the committed corpus-wide log.

    Every hyphen decision applied to AI 100-1's content must match the reviewed
    decision log exactly. The eight log decisions not applied are markers in
    discarded front matter and headers that never reach a unit.
    """
    from collections import Counter

    from src.ingest.nist_ai_100_1 import applied_hyphen_decisions

    log_path = OUTPUT_DIR.parent / "hyphenation" / "decision_log.jsonl"
    log = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()]
    key_fields = (
        "left", "right", "hyphenated", "joined",
        "hyphen_evidence", "joined_evidence", "rule", "outcome",
    )
    log_multiset = Counter(
        tuple(row[k] for k in key_fields) for row in log if row["doc_id"] == DOC_ID
    )
    applied_multiset = Counter(
        tuple(getattr(d, k) for k in key_fields) for d in applied_hyphen_decisions()
    )
    assert not (applied_multiset - log_multiset), "an applied decision does not match the log"
    assert sum((log_multiset - applied_multiset).values()) == 8


# --------------------------------------------------------------------------
# Chunk invariants
# --------------------------------------------------------------------------

def test_no_chunk_is_empty(ingested):
    _, chunks, _, _, _ = ingested
    assert all(c["text"].strip() for c in chunks)


def test_no_chunk_exceeds_the_token_cap(ingested):
    _, chunks, _, _, _ = ingested
    assert [c["chunk_id"] for c in chunks if c["token_count"] > MAX_TOKENS] == []


def test_token_counts_match_the_pinned_tokenizer(ingested):
    _, chunks, _, _, _ = ingested
    for chunk in chunks[:30]:
        assert chunk["token_count"] == count_tokens(chunk["text"])


def test_chunk_ids_are_unique(ingested):
    _, chunks, _, _, _ = ingested
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_ids_are_derived_from_printed_identifiers(ingested):
    """Never positional. Subcategory ids carry the document's own numbering."""
    _, chunks, _, _, _ = ingested
    assert f"{DOC_ID}:sub_GOVERN_1.1" in {c["parent_id"] for c in chunks}
    assert f"{DOC_ID}:sec_1.2.1" in {c["parent_id"] for c in chunks}
    assert f"{DOC_ID}:app_A" in {c["parent_id"] for c in chunks}


def test_every_parent_id_resolves_and_split_ids_derive_from_it(ingested):
    _, chunks, _, _, _ = ingested
    units = {c["parent_id"] for c in chunks}
    for chunk in chunks:
        assert chunk["parent_id"] in units
        if chunk["n_chunks_in_unit"] > 1:
            assert chunk["chunk_id"] == f"{chunk['parent_id']}#p{chunk['seq']}"
        else:
            assert chunk["chunk_id"] == chunk["parent_id"]


def test_two_consecutive_runs_produce_identical_output(ingested):
    first, *_ = ingested
    assert first == build()


# --------------------------------------------------------------------------
# Relations and duplication
# --------------------------------------------------------------------------

def test_structural_join_and_prose_xrefs_are_separate_fields(ingested):
    _, _, relations, _, _ = ingested
    assert relations
    for record in relations:
        assert "structural_join" in record
        assert "prose_xrefs" in record
        assert isinstance(record["structural_join"], list)
        assert isinstance(record["prose_xrefs"], list)


def test_structural_join_reproduces_the_documents_coverage(ingested):
    """72 subcategories reach the Playbook, only 49 reach AI 600-1."""
    _, _, relations, _, _ = ingested
    joins = [j for r in relations for j in r["structural_join"]]
    assert sum(1 for j in joins if j["doc_id"] == "nist_playbook") == 72
    assert sum(1 for j in joins if j["doc_id"] == "nist_ai_600_1") == 49


def test_every_dropped_prose_xref_carries_a_reason_and_sentence(ingested):
    _, _, relations, _, _ = ingested
    dropped = [d for r in relations for d in r["prose_xrefs_dropped"]]
    assert dropped
    for record in dropped:
        assert record["reason"]
        assert record["sentence"]


def test_prose_xrefs_resolve_to_real_units(ingested):
    _, chunks, relations, _, _ = ingested
    units = {c["parent_id"] for c in chunks}
    for record in relations:
        for reference in record["prose_xrefs"]:
            assert reference["target"] in units
            assert reference["target"] != record["unit_id"]


def test_duplication_map_is_derived_mechanically(ingested):
    """Exact substring matching, never judgment."""
    _, _, _, duplication, _ = ingested
    assert len(duplication) == 72
    for row in duplication:
        assert row["source_unit_id"].startswith(f"{DOC_ID}:sub_")
        for entry in row["duplicated_in"]:
            assert entry["doc_id"] in {"nist_playbook", "nist_ai_600_1"}


def test_duplication_is_recorded_not_removed(ingested):
    """Duplication is a near-miss trap to keep, not a problem to erase."""
    manifest, _, _, duplication, _ = ingested
    assert manifest["duplication_map"]["duplicated_in_playbook"] > 30
    assert sum(1 for r in duplication if r["duplicated_in"]) > 30


def test_ai_600_1_partial_coverage_is_recorded(ingested):
    manifest, *_ = ingested
    warning = manifest["duplication_map"]["ai_600_1_coverage_warning"]
    assert "49 of the 72" in warning


def test_match_form_is_punctuation_and_case_insensitive():
    assert match_form("Legal and regulatory requirements") == "legal and regulatory requirements"
    assert match_form("GOVERN 1.1: Legal, and  regulatory") == "govern 1 1 legal and regulatory"


def test_partition_accounts_for_the_entire_raw_extraction(ingested):
    """The proof must cover raw_chars, not a derived line inventory.

    Otherwise content could hide in the difference between the raw text and the
    stripped lines the units are built from.
    """
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


def test_the_raw_to_line_delta_is_only_structural_whitespace(ingested):
    """No document text lives in the gap, only newlines and trimmed padding."""
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    classes = proof["structural_whitespace_by_class"]
    assert set(classes) <= {
        "intra_page_newlines",
        "page_separators",
        "stripped_line_whitespace",
        "blank_line_chars",
        "blank_lines",
    }
    assert proof["raw_chars"] - proof["line_chars"] == proof["structural_whitespace_total"]


def test_duplication_method_is_recorded_reproducibly(ingested):
    """The map feeds pre-registration, so its method must be exactly reproducible."""
    manifest, *_ = ingested
    detail = manifest["duplication_map"]["method_detail"]
    assert "ENTIRE match form" in detail
    assert "not a prefix match" in detail
    assert "U+FFFE" in detail


def test_duplication_uses_full_statement_not_prefix_matching(ingested):
    """Pins the committed method: full-statement match gives 48 and 47.

    Stated correction: these were 47 and 46 before the U+FFFE hyphen resolver was
    wired in. Resolving line-break hyphens consistently on both the AI 100-1
    statements and the target documents revealed two true duplications the old
    delete-the-hyphen rule had hidden: MAP 1.1 now matches AI 600-1 via
    "context-specific", and MEASURE 4.3 now matches the Playbook via
    "context-relevant". Both had been corrupted to a joined form that did not
    match the target's correctly hyphenated text.
    """
    manifest, *_ = ingested
    summary = manifest["duplication_map"]
    assert summary["duplicated_in_playbook"] == 48
    assert summary["duplicated_in_ai_600_1"] == 47


def test_subcategories_without_a_near_miss_twin_are_named(ingested):
    """They behave differently in the distractor bucket, so they are recorded.

    Stated correction: this was 13 before the hyphen resolver was wired in. The
    same two duplications revealed by consistent hyphen resolution, MAP 1.1 and
    MEASURE 4.3, each gained a twin, so the count without a twin dropped to 11.
    """
    manifest, _, _, duplication, _ = ingested
    summary = manifest["duplication_map"]
    assert summary["no_near_miss_twin_count"] == 11
    named = set(summary["no_near_miss_twin"])
    assert len(named) == 11
    for row in duplication:
        assert row["has_near_miss_twin"] == (row["subcategory"] not in named)


def test_token_convention_matches_part_one(ingested):
    """Both ingestion steps feed one retriever, so the convention must be identical."""
    from tokenizers import Tokenizer

    from src.ingest.tokenization import TOKENIZER_FILE

    _, chunks, _, _, _ = ingested
    tokenizer = Tokenizer.from_file(str(TOKENIZER_FILE))
    largest = max(chunks, key=lambda c: c["token_count"])
    encoded = tokenizer.encode(largest["text"])
    assert len(encoded.ids) == largest["token_count"]
    assert encoded.tokens[0] == "[CLS]"
    assert encoded.tokens[-1] == "[SEP]"
    assert largest["token_count"] <= MAX_TOKENS


def test_downstream_normalisation_requirement_is_recorded(ingested):
    """Chunks keep PDF line breaks; grounding comparison must normalise both sides."""
    manifest, *_ = ingested
    note = manifest["downstream_notes"]["comparison_time_whitespace_normalisation"]
    assert "BOTH sides" in note
    assert "comparison time ONLY" in note
    assert "never" in note


def test_bimodal_length_is_recorded_as_a_known_property(ingested):
    manifest, *_ = ingested
    assert "length normalisation" in manifest["downstream_notes"]["bimodal_chunk_length"]


def test_the_equal_whitespace_classes_are_equal_by_construction(ingested):
    """Two identical numbers must not look like one was copied from the other."""
    manifest, *_ = ingested
    proof = manifest["partition_proof"]
    classes = proof["structural_whitespace_by_class"]
    assert classes["intra_page_newlines"] == classes["stripped_line_whitespace"]
    assert "by construction" in proof["why_two_classes_are_equal"]
    assert "one trailing space" in proof["why_two_classes_are_equal"]
