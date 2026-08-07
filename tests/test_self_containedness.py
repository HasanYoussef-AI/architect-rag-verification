"""Tests for the self-containedness candidate generator.

Every deterministic check in this repository ships with tests, and a detector that reports a pass
or an absence is trusted only once it has been shown capable of failing. Both forms V20 names have
bitten this repository, so each detector here is run against the defect it exists to catch.
"""

from __future__ import annotations

import json

import pytest

from src.goldset.calibrate_self_containedness import build, positive_and_negative_units
from src.goldset.self_containedness import (
    CLASS_ARTICLE_OR_ANNEX,
    CLASS_EXTERNAL_INSTRUMENT,
    DEFINITIONS_UNIT,
    ChunkCorpus,
    _INVENTORY_RE,
    article_3_inventory,
    defined_term_deference,
    inventory_fingerprint,
    named_references,
    screen,
)
from src.ingest.corpus_integrity import REPO_ROOT

# The eleven eu_ai_act single-hop picks. No test here evaluates an arm against one of them.
_FRAME = json.loads((REPO_ROOT / "eval" / "test_frame.json").read_text(encoding="utf-8"))
_EU = _FRAME["strata"]["single_hop"]["sources"]["eu_ai_act"]
PICKS = set(_EU["draw_order"][: _EU["allocation"]])

# Held out: single-hop draw indices 193, 131 and 135 respectively.
ART_98 = "eu_ai_act:art_98"
ART_102 = "eu_ai_act:art_102"
ART_109 = "eu_ai_act:art_109"


@pytest.fixture(scope="module")
def corpus() -> ChunkCorpus:
    return ChunkCorpus.load()


@pytest.fixture(scope="module")
def inventory(corpus: ChunkCorpus) -> list[str]:
    return article_3_inventory(corpus)


# --------------------------------------------------------------------------- inventory


def test_inventory_is_derived_from_the_definitions_unit(corpus, inventory):
    assert corpus.chunks_for(DEFINITIONS_UNIT)[0]["heading"] == "Definitions"
    assert len(inventory) == 67
    assert inventory == sorted(set(inventory))
    for term in ("AI system", "provider", "deployer", "intended purpose"):
        assert term in inventory


def test_arm2_does_not_reach_high_risk_ai_system_and_that_limit_is_pinned(inventory):
    """A stated scope limit of arm 2, not an accident of the extraction pattern.

    "high-risk AI system" is one of the Act's most load-bearing terms and it is NOT defined in
    Article 3; classification lives in Article 6. Arm 2 is an Article 3 inventory, so it does not
    reach it, and a unit deferring by using that term produces no arm 2 candidate on that ground.
    Pinned here so the limit is visible in the suite rather than discovered later.
    """
    assert "high-risk AI system" not in inventory
    assert [t for t in inventory if "high-risk" in t.lower()] == []


def test_inventory_fingerprint_is_pinned(inventory):
    assert (
        inventory_fingerprint(inventory)
        == "18edc31bbebfead08f3f54e285c4106738630df03af76261f24fcce3079ecf2f"
    )


def test_inventory_pattern_is_capable_of_missing():
    """The negative control Rule 12 requires: the pattern must be shown able to fail.

    A pattern that matched everything would report a complete inventory on any input, which is the
    blindness form of V20. These three definition shapes are real drafting forms the pattern does
    not cover, and its recall is bounded by that rather than assumed.
    """
    assert _INVENTORY_RE.search("‘AI system’ means a machine-based system") is not None
    for missed in (
        "‘AI system’ shall mean a machine-based system",
        '"AI system" means a machine-based system',
        "AI system means a machine-based system",
    ):
        assert _INVENTORY_RE.search(missed) is None


def test_inventory_unit_id_is_exact_and_not_a_prefix(corpus):
    """Regression. startswith("eu_ai_act:art_3") also matches art_30 through art_39.

    Reading the definitions unit by prefix pulls in ten unrelated articles and would inflate the
    inventory with any quoted-term-plus-means construction they happen to contain.

    The inventory count happens to be unchanged at 67 either way, because art_30 to art_39 contain
    no quoted-term-plus-means construction. That is a fact about this corpus and not a property
    the extraction can rely on, so this test pins the structural defect, foreign unit text
    entering the read, rather than a count difference that does not currently exist.
    """
    assert DEFINITIONS_UNIT == "eu_ai_act:art_3"
    by_prefix = [u for u in corpus.unit_ids() if u.startswith("eu_ai_act:art_3")]
    assert len(by_prefix) == 11
    assert "eu_ai_act:art_30" in by_prefix

    exact_text = "".join(r["text"] for r in corpus.chunks_for(DEFINITIONS_UNIT))
    prefix_text = "".join(r["text"] for unit in by_prefix for r in corpus.chunks_for(unit))
    foreign = "".join(r["text"] for r in corpus.chunks_for("eu_ai_act:art_30"))

    assert corpus.chunks_for("eu_ai_act:art_30")[0]["heading"] == "Notification procedure"
    assert foreign in prefix_text
    assert foreign not in exact_text
    assert len(prefix_text) > 2 * len(exact_text)


# --------------------------------------------------------------------------- arm 1


def test_arm1_names_the_external_instrument_class_explicitly(corpus):
    """The three committed target_defers_out_of_corpus positives, caught by name.

    Reaching this class only through an adjacent deference locution would leave a unit that names
    an out-of-corpus instrument with no locution invisible, which is the failure the class exists
    to close.
    """
    expected = {
        ART_98: "Regulation (EU) No 182/2011",
        ART_102: "Regulation (EC) No 300/2008",
        ART_109: "Regulation (EU) 2019/2144",
    }
    for unit, instrument in expected.items():
        block = named_references(unit, corpus)
        surfaces = {
            c["surface"] for c in block["candidates"] if c["class"] == CLASS_EXTERNAL_INSTRUMENT
        }
        assert instrument in surfaces, f"{unit} did not surface {instrument!r}"


def test_arm1_excludes_the_acts_own_number_but_not_other_instruments(corpus):
    """The one exclusion in arm 1, shown to remove the right thing and only that thing."""
    block = named_references(ART_102, corpus)
    removed = block["funnel"]["removed_self_reference"]
    assert removed["count"] >= 1
    for item in removed["removed_items"]:
        assert "2024/1689" in item["sentence"] or "2024/1689" in item["surface"]
    kept = {c["surface"] for c in block["candidates"] if c["class"] == CLASS_EXTERNAL_INSTRUMENT}
    assert "Regulation (EC) No 300/2008" in kept
    assert not any("2024/1689" in s for s in kept)


def test_arm1_is_capable_of_returning_nothing(corpus):
    """V20. A detector that never returns empty proves nothing when it returns non-empty."""
    synthetic = ChunkCorpus(
        records={
            "synthetic:unit_1": [
                {
                    "chunk_id": "synthetic:unit_1",
                    "seq": 0,
                    "text": "The weather was mild and the harvest came in early that year.",
                }
            ]
        }
    )
    block = named_references("synthetic:unit_1", synthetic)
    assert block["funnel"]["candidates"] == 0
    assert block["candidates"] == []


def test_arm1_funnel_closes_on_every_eu_unit(corpus):
    """V10. Starting population equals what was removed plus what survived, on every unit."""
    checked = 0
    for unit in corpus.unit_ids():
        if not unit.startswith("eu_ai_act:") or unit in PICKS:
            continue
        funnel = named_references(unit, corpus)["funnel"]
        assert funnel["starting_population"] == (
            funnel["removed_self_reference"]["count"] + funnel["candidates"]
        ), unit
        checked += 1
    assert checked == 295


def test_no_candidate_spans_a_chunk_boundary(corpus):
    """Regression on the concatenation defect, checked exhaustively rather than sampled.

    attributability.Corpus builds unit text by concatenating chunk text with no separator, and 90
    adjacent chunk pairs in eu_ai_act join with no whitespace on either side. A candidate matched
    across such a join would quote a string that appears in no committed record and could not be
    attributed to a chunk_id. Every candidate's recorded offsets must slice its own chunk record
    back to its own surface.
    """
    by_chunk = {
        record["chunk_id"]: record["text"]
        for records in corpus.records.values()
        for record in records
    }
    checked = 0
    for unit in corpus.unit_ids():
        if unit in PICKS:
            continue
        for candidate in named_references(unit, corpus)["candidates"]:
            text = by_chunk[candidate["chunk_id"]]
            sliced = text[candidate["char_start_in_chunk"]: candidate["char_end_in_chunk"]]
            assert sliced == candidate["surface"], candidate
            checked += 1
    # Pinned rather than bounded. The exact population is derived from the run, and it serves two
    # purposes: it proves the sweep was not silently empty, and it flags any change to the
    # candidate population that a pattern edit would cause. It is not a threshold judging the
    # observations, so V15 does not bite.
    assert checked == 2760


def test_concatenation_would_fabricate_a_match_that_per_record_reading_does_not(corpus):
    """The defect made visible: the same text, concatenated, yields a match that does not exist.

    This is the detector run against the defect it exists to catch. Chunk one ends mid-phrase and
    chunk two begins with the rest; concatenating with no separator fabricates "Annex IV", which
    appears in neither record.
    """
    split = ChunkCorpus(
        records={
            "synthetic:unit_2": [
                {"chunk_id": "synthetic:unit_2#p1", "seq": 0, "text": "documented in Annex"},
                {"chunk_id": "synthetic:unit_2#p2", "seq": 1, "text": "IV of the file."},
            ]
        }
    )
    per_record = named_references("synthetic:unit_2", split)
    surfaces = {
        c["surface"] for c in per_record["candidates"] if c["class"] == CLASS_ARTICLE_OR_ANNEX
    }
    assert surfaces == set()

    concatenated = "".join(r["text"] for r in split.records["synthetic:unit_2"])
    assert concatenated == "documented in AnnexIV of the file."
    joined = ChunkCorpus(
        records={
            "synthetic:unit_3": [
                {"chunk_id": "synthetic:unit_3", "seq": 0, "text": "documented in Annex IV of it."}
            ]
        }
    )
    joined_surfaces = {
        c["surface"]
        for c in named_references("synthetic:unit_3", joined)["candidates"]
        if c["class"] == CLASS_ARTICLE_OR_ANNEX
    }
    assert joined_surfaces == {"Annex IV"}


# --------------------------------------------------------------------------- arm 2


def test_arm2_funnel_closes_and_reports_the_inventory(corpus, inventory):
    block = defined_term_deference(ART_109, corpus, inventory)
    funnel = block["funnel"]
    assert funnel["starting_population"] == len(inventory)
    assert block["inventory"]["n_terms"] == len(inventory)
    assert block["inventory"]["source_unit"] == DEFINITIONS_UNIT
    used = len(block["distinct_terms_used"])
    assert funnel["removed_term_absent_from_unit"]["count"] == len(inventory) - used


def test_arm2_excludes_the_definitions_units_own_definitions(corpus, inventory):
    """A unit's use of a term it itself defines is not deference, and the exclusion is reported."""
    block = defined_term_deference(DEFINITIONS_UNIT, corpus, inventory)
    assert block["funnel"]["candidates"] == 0
    assert block["funnel"]["removed_units_own_definitions"]["count"] > 0
    other = defined_term_deference(ART_109, corpus, inventory)
    assert other["funnel"]["removed_units_own_definitions"]["count"] == 0


def test_arm2_is_capable_of_returning_nothing(corpus, inventory):
    synthetic = ChunkCorpus(
        records={
            "synthetic:unit_4": [
                {"chunk_id": "synthetic:unit_4", "seq": 0, "text": "The harvest came in early."}
            ]
        }
    )
    block = defined_term_deference("synthetic:unit_4", synthetic, inventory)
    assert block["funnel"]["candidates"] == 0
    assert block["distinct_terms_used"] == []


# --------------------------------------------------------------------------- schema


def test_row_carries_four_named_parts_and_the_rollup_is_not_a_conjunction(corpus, inventory):
    """The fix for the objection that two empty funnels read as a verified property."""
    row = screen(ART_98, corpus, inventory)
    for part in (
        "named_references",
        "defined_term_deference",
        "unnamed_substantive_deference",
        "self_containedness_verdict",
    ):
        assert part in row

    arm3 = row["unnamed_substantive_deference"]
    assert arm3["covered_by_committed_method"] is False
    assert arm3["human_verdict"] is None
    assert "NO COMMITTED METHOD" in arm3["statement"]

    rollup = row["self_containedness_verdict"]
    assert rollup["verdict"] is None
    assert rollup["set_by"] == "human"
    assert "NOT the conjunction" in rollup["is_not_the_conjunction_of_the_parts"]


def test_every_arm_block_carries_predicate_command_and_reproducibility_level(corpus, inventory):
    row = screen(ART_98, corpus, inventory)
    for part in ("named_references", "defined_term_deference"):
        block = row[part]
        assert block["predicate"]
        assert block["command"]
        assert block["reproducibility_level"] == 1
        assert "funnel" in block


def test_screen_carries_chunk_ids_for_a_multi_chunk_unit(corpus, inventory):
    multi = next(
        u
        for u in corpus.unit_ids()
        if u.startswith("eu_ai_act:") and u not in PICKS and len(corpus.chunks_for(u)) > 1
    )
    row = screen(multi, corpus, inventory)
    assert len(row["chunk_ids"]) == len(corpus.chunks_for(multi))
    assert row["chunk_ids"] == [r["chunk_id"] for r in corpus.chunks_for(multi)]


# --------------------------------------------------------------------------- calibration


def test_role_split_is_derived_from_the_record_not_named(corpus):
    """Twelve positives and six negatives, derived from reason_code rather than hardcoded."""
    positive, negative, funnel = positive_and_negative_units()
    assert len(positive) == 12
    assert len(negative) == 6
    assert not set(positive) & set(negative)
    assert funnel["starting_population"] == 19
    assert funnel["rows_kept"] == 10


def test_no_calibration_unit_is_a_single_hop_pick():
    positive, negative, _ = positive_and_negative_units()
    assert not (set(positive) | set(negative)) & PICKS


def test_positive_arm_fires_on_every_unit_the_record_establishes(corpus):
    """The calibration claim that can fail, pinned so reversing it requires deleting this test."""
    record = build(corpus)
    arm = record["positive_arm"]
    assert arm["n_units"] == 12
    assert arm["units_producing_no_candidate"] == []
    assert arm["passed"] is True
    for unit in arm["units"]:
        assert unit["arm1_candidates"] >= 1


def test_register_arm_population_excludes_picks_first(corpus):
    record = build(corpus)
    funnel = record["register_arm"]["funnel"]
    assert funnel["starting_population"] == 180
    assert funnel["removed_is_a_single_hop_pick"]["count"] == len(
        [p for p in PICKS if ":rct_" in p]
    )
    assert funnel["population"] == (
        funnel["starting_population"]
        - funnel["removed_is_a_single_hop_pick"]["count"]
        - funnel["removed_carries_a_named_article_or_annex_reference"]["count"]
    )


def test_negative_arm_states_that_it_does_not_control_the_instrument(corpus):
    record = build(corpus)
    arm = record["negative_arm"]
    assert arm["controls_the_instrument"] is False
    assert arm["controls_the_verdict_step"] is True
    assert len(arm["units_where_arm1_fires"]) == 6


def test_committed_calibration_record_matches_a_fresh_run(corpus):
    """The committed record is reproducible from the committed corpus by the stated command."""
    path = REPO_ROOT / "eval" / "self_containedness_calibration.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == build(corpus)
