"""Tests for EU AI Act ingestion.

The counts are asserted against the document's true structure, 113 Articles,
13 Annexes, 180 Recitals. That is not a cosmetic check: enumerated lists are
laid out as HTML tables and all 180 Recitals exist ONLY as tables, so a parser
that skipped tables would drop every list item and every Recital while still
appearing to succeed. These assertions are what make that failure loud.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.chunk_schema import SCHEMA_VERSION
from src.ingest.eu_ai_act import DOC_ID, OUTPUT_DIR, build, pack_blocks
from src.ingest.normalize import normalize_block, normalize_spaces
from src.ingest.tokenization import MAX_TOKENS, count_tokens

EXPECTED_UNITS = {"article": 113, "annex": 13, "recital": 180}


@pytest.fixture(scope="module")
def ingested():
    manifest = build()
    chunks = [
        json.loads(line)
        for line in (OUTPUT_DIR / f"{DOC_ID}.chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    xrefs = [
        json.loads(line)
        for line in (OUTPUT_DIR / f"{DOC_ID}.xrefs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    text = (OUTPUT_DIR / f"{DOC_ID}.normalized.txt").read_text(encoding="utf-8")
    return manifest, chunks, xrefs, text


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

def test_non_breaking_space_is_normalised():
    """EUR-Lex writes "Article" + U+00A0 + "6"; plain-space matching must work."""
    assert normalize_spaces("Article 6") == "Article 6"
    assert normalize_block("ANNEX III") == "ANNEX III"


def test_normalisation_collapses_runs_but_preserves_characters():
    assert normalize_block("a\n\n  b\tc") == "a b c"
    # Typographic characters in the Official Journal are preserved exactly.
    assert normalize_block("‘quoted’ … ellipsis") == "‘quoted’ … ellipsis"


def test_structural_matching_would_fail_without_normalisation():
    raw = "Article 6"
    assert "Article 6" not in raw
    assert "Article 6" in normalize_spaces(raw)


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------

def test_unit_counts_match_the_documents_own_structure(ingested):
    manifest, _, _, _ = ingested
    assert manifest["counts"]["units"] == EXPECTED_UNITS


def test_all_180_recitals_are_present(ingested):
    """Recitals exist only as HTML tables. A table-skipping parser loses them all."""
    _, chunks, _, _ = ingested
    recitals = {c["parent_id"] for c in chunks if c["unit_type"] == "recital"}
    assert len(recitals) == 180
    assert recitals == {f"{DOC_ID}:rct_{n}" for n in range(1, 181)}


def test_all_113_articles_and_13_annexes_are_present(ingested):
    _, chunks, _, _ = ingested
    articles = {c["parent_id"] for c in chunks if c["unit_type"] == "article"}
    annexes = {c["parent_id"] for c in chunks if c["unit_type"] == "annex"}
    assert articles == {f"{DOC_ID}:art_{n}" for n in range(1, 114)}
    assert len(annexes) == 13


def test_enumerated_list_items_survive_ingestion(ingested):
    """List items are table rows; losing them would silently gut Annex III."""
    _, chunks, _, _ = ingested
    annex_iii = " ".join(c["text"] for c in chunks if c["parent_id"] == f"{DOC_ID}:anx_III")
    assert "Biometrics" in annex_iii
    assert "remote biometric identification systems" in annex_iii


def test_the_last_article_is_not_contaminated_by_the_annexes(ingested):
    """Regression: an anchor-to-anchor window made art_113 absorb the Annexes."""
    _, chunks, _, _ = ingested
    art_113 = " ".join(c["text"] for c in chunks if c["parent_id"] == f"{DOC_ID}:art_113")
    assert "ANNEX I" not in art_113
    assert len(art_113.split()) < 400


# --------------------------------------------------------------------------
# Chunk invariants
# --------------------------------------------------------------------------

def test_no_chunk_is_empty(ingested):
    _, chunks, _, _ = ingested
    assert all(c["text"].strip() for c in chunks)


def test_no_chunk_exceeds_the_token_cap(ingested):
    """The cap is bge-base-en-v1.5's real 512-position ceiling, so an overflowing
    chunk would be silently truncated at embedding time."""
    _, chunks, _, _ = ingested
    over = [(c["chunk_id"], c["token_count"]) for c in chunks if c["token_count"] > MAX_TOKENS]
    assert over == []


def test_recorded_token_counts_match_the_pinned_tokenizer(ingested):
    _, chunks, _, _ = ingested
    for chunk in chunks[:40]:
        assert chunk["token_count"] == count_tokens(chunk["text"])


def test_chunk_ids_are_unique(ingested):
    _, chunks, _, _ = ingested
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_every_parent_id_resolves_to_a_real_unit(ingested):
    _, chunks, _, _ = ingested
    units = {c["parent_id"] for c in chunks}
    assert all(c["parent_id"] in units for c in chunks)
    assert len(units) == sum(EXPECTED_UNITS.values())


def test_split_chunk_ids_are_derived_from_the_parent(ingested):
    """IDs must come from the document's own anchors, never a corpus-wide index."""
    _, chunks, _, _ = ingested
    for chunk in chunks:
        if chunk["n_chunks_in_unit"] > 1:
            assert chunk["chunk_id"] == f"{chunk['parent_id']}#p{chunk['seq']}"
        else:
            assert chunk["chunk_id"] == chunk["parent_id"]


def test_unsplit_chunk_id_equals_its_parent_id(ingested):
    """Makes the gold-passage rule uniform across split and unsplit units."""
    _, chunks, _, _ = ingested
    unsplit = [c for c in chunks if c["n_chunks_in_unit"] == 1]
    assert unsplit
    assert all(c["chunk_id"] == c["parent_id"] for c in unsplit)


def test_a_units_chunks_are_numbered_contiguously_from_one(ingested):
    _, chunks, _, _ = ingested
    by_parent: dict[str, list[int]] = {}
    for chunk in chunks:
        by_parent.setdefault(chunk["parent_id"], []).append(chunk["seq"])
    for parent, seqs in by_parent.items():
        assert sorted(seqs) == list(range(1, len(seqs) + 1)), parent


def test_chunk_text_is_an_exact_substring_at_its_offsets(ingested):
    """Offsets must be verifiable against the persisted text, not merely plausible."""
    _, chunks, _, text = ingested
    for chunk in chunks:
        assert text[chunk["char_start"] : chunk["char_end"]] == chunk["text"]


def test_every_chunk_carries_source_provenance(ingested):
    _, chunks, _, _ = ingested
    manifest, *_ = ingested
    for chunk in chunks:
        assert chunk["source_sha256"] == manifest["source"]["sha256"]
        assert chunk["schema_version"] == SCHEMA_VERSION


def test_packing_never_splits_below_a_block():
    blocks = ["short one.", "short two.", "short three."]
    groups = pack_blocks(blocks)
    assert [i for group in groups for i in group] == [0, 1, 2]


def test_packing_starts_a_new_chunk_rather_than_overflowing():
    big = " ".join(["word"] * 400)
    groups = pack_blocks([big, big])
    assert len(groups) == 2


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------

def test_two_consecutive_runs_produce_identical_output(ingested):
    first, *_ = ingested
    second = build()
    assert first["outputs"] == second["outputs"]
    assert first == second


# --------------------------------------------------------------------------
# Cross-reference graph, corpus level
# --------------------------------------------------------------------------

def test_no_internal_edge_points_at_a_unit_that_does_not_exist(ingested):
    """Referential integrity: 'Article 290 TFEU' cannot be internal, the Act has 113."""
    _, chunks, xrefs, _ = ingested
    units = {c["parent_id"] for c in chunks}
    dangling = [t for r in xrefs for t in r["refs_internal"] if t not in units]
    assert dangling == []


def test_article_108_contributes_no_internal_edges(ingested):
    _, _, xrefs, _ = ingested
    record = next(r for r in xrefs if r["unit_id"] == f"{DOC_ID}:art_108")
    assert record["refs_internal"] == []
    assert record["refs_dropped"]


def test_article_7_keeps_its_internal_annex_edge(ingested):
    """The Mode A fix must not over-trigger: art_7 amends this Act."""
    _, _, xrefs, _ = ingested
    record = next(r for r in xrefs if r["unit_id"] == f"{DOC_ID}:art_7")
    assert f"{DOC_ID}:anx_III" in record["refs_internal"]


def test_dropped_references_are_recorded_rather_than_discarded(ingested):
    _, _, xrefs, _ = ingested
    dropped = [d for r in xrefs for d in r["refs_dropped"]]
    assert dropped
    for record in dropped:
        assert record["reason"]
        assert record["sentence"]


def test_the_graph_is_labelled_as_a_candidate_extraction(ingested):
    """The manifest must never claim this is the Act's complete structure."""
    manifest, *_ = ingested
    cross = manifest["cross_references"]
    assert "candidate" in cross["status"]
    assert "not the complete cross-reference structure" in cross["warning"]
    assert "individually read and verified" in cross["use_in_ground_truth"]


def test_the_known_source_artifact_is_recorded(ingested):
    """The stray backtick in Article 1's heading is in the published Regulation."""
    manifest, chunks, _, _ = ingested
    assert "art_1_heading_stray_backtick" in manifest["known_source_artifacts"]
    art_1 = next(c for c in chunks if c["parent_id"] == f"{DOC_ID}:art_1")
    assert art_1["heading"] == "Subject matter`"
