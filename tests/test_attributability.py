"""The two-armed attributability scan, calibrated against the two cases the last scope published.

The instrument exists because no committed relation covers near-verbatim restatement outside the
NIST subcategory statements, and none covers the EU AI Act at all. It decides nothing, so what is
pinned here is that it can see, not that it judges correctly.

The V20 property is why this file is longer than the module. A detector that reports an absence is
trusted only once it has been shown capable of failing, and this one has a failure mode a careful
reading does not surface: segmenting on sentence terminators alone buries the matching clause of
the published 0.894 case inside a 768-character block and returns nothing. Both the blind form and
the shipped form are driven over the same pair here.

Calibration, not fitting. Case A and case B are positives published in
eval/test_frame_rejections.jsonl before this instrument existed, on picks already rejected. They
are held-out ground truth, not observations this instrument will judge. The floor never moves and
the segmenter is frozen before any single-hop span is designated.

One discrepancy is pinned rather than reconciled. Case A reproduces the published 0.940 exactly.
Case B does not reproduce the published 0.894 under six normalisations, either difflib
granularity, or three span-boundary variants; the instrument derives 0.8982. The original method
was never committed, so no diagnosis beyond that is available, and case A reproducing to the digit
bounds the disagreement to case B rather than to the method. Tuning until a variant hit 0.894
would select that variant because it hit 0.894.
"""

from __future__ import annotations

import difflib
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.goldset.attributability import (
    CHUNK_JOIN,
    CHUNKS,
    DENSE_TOP_N,
    DOCUMENTS,
    LEXICAL_FLOOR,
    MANIFEST,
    SEGMENT_INDEX,
    SEGMENT_VECTORS,
    Corpus,
    carries_alphabetic_content,
    comparable_segments,
    dense_arm,
    exclusion_report,
    is_own_heading,
    lexical_arm,
    load_segment_cache,
    normalise_for_lexical,
    onnx_session,
    ratio_matcher,
    scan,
    segmentation_funnel,
    segments,
    unit_of,
)

EVAL = REPO_ROOT / "eval"

# Both sides of the published 0.940 case, quoted verbatim from the reason field of the
# eu_ai_act:art_26 / eu_ai_act:art_72 row of eval/test_frame_rejections.jsonl.
CASE_A_LEFT = (
    "This obligation shall not cover sensitive operational data of deployers of AI systems "
    "which are law enforcement authorities"
)
CASE_A_RIGHT = (
    "This obligation shall not cover sensitive operational data of deployers which are "
    "law-enforcement authorities"
)
CASE_A_PUBLISHED = 0.940

# The published 0.894 case. The Annex IV side is quoted verbatim from the reason field of the
# eu_ai_act:anx_IV / eu_ai_act:art_13 row; the Article 13(3)(d) side verbatim from the corpus.
CASE_B_ARTICLE = (
    "the human oversight measures referred to in Article 14, including the technical measures "
    "put in place to facilitate the interpretation of the outputs of the high-risk AI systems "
    "by the deployers"
)
CASE_B_ANNEX = (
    "the human oversight measures needed in accordance with Article 14, including the technical "
    "measures put in place to facilitate the interpretation of the outputs of AI systems by the "
    "deployers"
)
CASE_B_PUBLISHED = 0.894
CASE_B_DERIVED = 0.8982


@pytest.fixture(scope="module")
def corpus():
    return Corpus.load()


def _ratio(left: str, right: str) -> float:
    return ratio_matcher(normalise_for_lexical(left), normalise_for_lexical(right)).ratio()


# Calibration against the two published positives


def test_case_a_reproduces_the_published_ratio():
    """0.940, the case that motivated the original check. Hyphen folding is what gets it there."""
    assert round(_ratio(CASE_A_LEFT, CASE_A_RIGHT), 3) == CASE_A_PUBLISHED


def test_case_a_needs_the_hyphen_fold_and_would_miss_without_it():
    """V20 on the normalisation: the fold is shown load-bearing, not assumed to be.

    0.931 to 0.9397 on folding alone. The normalisation is load-bearing, not cosmetic.
    """
    unfolded = difflib.SequenceMatcher(None, CASE_A_LEFT.lower(), CASE_A_RIGHT.lower()).ratio()
    assert round(unfolded, 3) == 0.931
    assert round(unfolded, 3) != CASE_A_PUBLISHED


def test_case_a_would_be_missed_by_an_exact_match_check():
    """The recorded reason for building a ratio check at all: the pair is near-verbatim."""
    assert normalise_for_lexical(CASE_A_LEFT) != normalise_for_lexical(CASE_A_RIGHT)
    assert _ratio(CASE_A_LEFT, CASE_A_RIGHT) >= LEXICAL_FLOOR


def test_case_b_derived_value_is_pinned_and_the_published_gap_is_recorded():
    """Case B does not reproduce. The derived value is pinned; the gap is not reconciled.

    The verdict does not move: both values clear the 0.60 floor and the pick stays rejected for
    the same reason, so the number is exposition and the verdict is robust to it.
    """
    derived = _ratio(CASE_B_ARTICLE, CASE_B_ANNEX)
    assert round(derived, 4) == CASE_B_DERIVED
    assert round(derived, 3) != CASE_B_PUBLISHED
    assert derived >= LEXICAL_FLOOR and CASE_B_PUBLISHED >= LEXICAL_FLOOR


# V20, the segmentation blindness


def test_period_only_segmentation_is_blind_to_the_published_case():
    """The shipped segmenter is trusted only because the blind form is shown to fail here."""
    block = _annex_iv_point_3()
    period_only = [s.strip() for s in re.split(r"(?<=[.!?])\s+", block) if s.strip()]
    best_blind = max(_ratio(CASE_B_ARTICLE, s) for s in period_only)
    assert best_blind < LEXICAL_FLOOR, "the blind form was expected to miss and did not"
    # SUPERSEDED VALUE, autojunk: this was 0.2968 while every ratio was built with difflib's
    # autojunk default, which junks characters appearing in more than one percent of the second
    # sequence once it reaches 200 elements. The 768-character period-only span is well past that
    # threshold, so the blind form's score depended on the length of the span it was blind to.
    # The control is unaffected in what it demonstrates: 0.3621 is still far below the 0.60 floor
    # and the semicolon companion is unmoved at 0.8982, so the segmenter decision stands on the
    # same evidence.
    assert round(best_blind, 4) == 0.3621

    best_shipped = max(_ratio(CASE_B_ARTICLE, s) for s in segments(block))
    assert best_shipped >= LEXICAL_FLOOR
    assert round(best_shipped, 4) == CASE_B_DERIVED


def test_segmentation_splits_on_semicolons():
    """Pins the specific defect. Reverting to sentence terminators alone breaks this."""
    assert segments("alpha beta; gamma delta") == ["alpha beta;", "gamma delta"]
    assert segments("one. two; three\nfour") == ["one.", "two;", "three", "four"]


def _annex_iv_point_3() -> str:
    """Annex IV point 3, read from the committed corpus rather than restated here."""
    text = ""
    for line in (REPO_ROOT / "data" / "chunks" / "eu_ai_act.chunks.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            row = json.loads(line)
            if unit_of(row["chunk_id"]) == "eu_ai_act:anx_IV":
                text += row["text"]
    start = text.index("3. Detailed information about the monitoring")
    end = text.index("4. A description of the appropriateness")
    block = text[start:end]
    assert "human oversight measures needed in accordance with Article 14" in block
    return block


# One segmenter, both arms


def test_both_arms_consume_the_same_segmentation(corpus):
    """The condition that makes a two-armed result mean anything.

    Two segmenters would let a pick pass one arm and fail the other for a segmentation reason.
    The dense cache is built from Corpus.ordered_segments and the lexical arm walks
    Corpus.unit_segments, so this asserts they are the same objects in the same order.
    """
    ordered = corpus.ordered_segments()
    walked = [(u, s) for u in sorted(corpus.unit_segments) for s in corpus.unit_segments[u]]
    assert ordered == walked
    assert len(ordered) == corpus.funnel["comparable_segments"]


def test_segmentation_fingerprint_changes_when_the_segmentation_changes(corpus):
    """The staleness guard is only as good as the fingerprint, so it is shown to move."""
    baseline = corpus.segmentation_fingerprint()
    assert len(baseline) == 64
    mutated = Corpus(
        unit_text=corpus.unit_text,
        unit_label=corpus.unit_label,
        unit_segments={**corpus.unit_segments, "eu_ai_act:art_37": ["a different segmentation"]},
        funnel=corpus.funnel,
    )
    assert mutated.segmentation_fingerprint() != baseline


def test_a_stale_segment_cache_raises_rather_than_scoring_the_wrong_text(corpus, tmp_path):
    """Absent is a skip; stale is an error. Scoring a segmentation nobody is comparing is the
    both-sides-absent failure V20 exists to catch, so it must not degrade quietly."""
    if not SEGMENT_INDEX.exists():
        pytest.skip("no segment cache built; the staleness path needs one to be stale against.")
    mutated = Corpus(
        unit_text=corpus.unit_text,
        unit_label=corpus.unit_label,
        unit_segments={**corpus.unit_segments, "eu_ai_act:art_37": ["not the real segmentation"]},
        funnel=corpus.funnel,
    )
    with pytest.raises(ValueError, match="stale"):
        load_segment_cache(mutated)


# The two exclusion predicates, reported rather than performed silently


def test_bare_paragraph_numbers_are_not_comparable_segments():
    """Pins the defect the twelve-row check surfaced.

    Segmenting an EU article yields its bare paragraph numbers, and "1." against "1." scores a
    perfect 1.0. The module's original reasoning, that no length filter was needed because a short
    segment cannot reach the floor against a long span, holds for a long span and is false for
    short against short. It was a belief written down as a measurement.
    """
    assert carries_alphabetic_content("This obligation shall not cover data")
    assert not carries_alphabetic_content("1.")
    assert not carries_alphabetic_content("(3)")
    assert (
        difflib.SequenceMatcher(
            None, normalise_for_lexical("1."), normalise_for_lexical("1.")
        ).ratio()
        == 1.0
    ), "the pair the predicate exists to remove really does score 1.0"
    # the shared segmenter keeps it out while the raw segmentation still produces it
    assert "1." in segments("1. Alpha beta.\n2. Gamma delta.")
    assert "1." not in comparable_segments("1. Alpha beta.\n2. Gamma delta.", None)


def test_heading_predicate_is_identity_against_the_unit_s_own_label():
    """Not a cut point. Byte identity against committed chunk metadata."""
    assert is_own_heading("Article 92", "Article 92")
    assert is_own_heading("  Article 92  ", "Article 92")
    assert not is_own_heading("Article 91", "Article 92")
    assert not is_own_heading("The provider shall supply the information requested.", "Article 92")
    assert not is_own_heading("Article 92", None)


def test_heading_predicate_removes_only_headings_enumerated_over_every_unit(corpus):
    """Exhaustive, both sides, because a predicate with no enumerated false positives is not a
    heuristic and one with unenumerated false positives is.

    An earlier report claimed no content segment matches any label. That claim rested on ONE
    content segment, not an enumeration, and is corrected here by enumerating all 1150 units.
    """
    removed = [
        (u, s)
        for u, t in corpus.unit_text.items()
        for s in segments(t)
        if is_own_heading(s, corpus.unit_label[u])
    ]
    assert len(removed) == 341
    assert removed, "positive control: the corpus really does contain such segments"
    # none of them can carry a claim
    assert max(len(s.split()) for _, s in removed) == 2
    assert max(len(s) for _, s in removed) == 17
    assert not [s for _, s in removed if len(s.split()) > 6]

    # the narrowness is load-bearing: segments equal to some OTHER unit's label are kept
    labels = {v.strip() for v in corpus.unit_label.values() if v}
    cross = [
        (u, s)
        for u, t in corpus.unit_text.items()
        for s in segments(t)
        if s.strip() in labels and not is_own_heading(s, corpus.unit_label[u])
    ]
    assert len(cross) == 16
    assert all(not is_own_heading(s, corpus.unit_label[u]) for u, s in cross)


def test_every_unit_carries_a_committed_unit_label(corpus):
    """The predicate rests on committed metadata, so its absence would silently disable it."""
    assert len(corpus.unit_label) == 1150
    assert sum(1 for v in corpus.unit_label.values() if v) == 1150
    assert corpus.unit_label["eu_ai_act:art_92"] == "Article 92"
    assert corpus.unit_label["eu_ai_act:anx_VIII"] == "ANNEX VIII"


def test_the_exclusion_funnel_is_reported_and_balances(corpus):
    """A reviewer sees the whole funnel and can disagree with a predicate on the record."""
    report = exclusion_report(corpus)
    assert report["starting_population"] == 14770
    assert report["removed_no_alphabetic_word"]["count"] == 1113
    assert report["removed_own_heading"]["count"] == 341
    assert report["comparable_segments"] == 13316
    assert (
        report["starting_population"]
        - report["removed_no_alphabetic_word"]["count"]
        - report["removed_own_heading"]["count"]
        == report["comparable_segments"]
    )
    for key in ("removed_no_alphabetic_word", "removed_own_heading"):
        assert report[key]["predicate"].strip()


def test_unit_text_reconstructs_the_source_on_every_unit(corpus):
    """Regression on the concatenation defect. Reversing the join fails this test.

    Corpus.load previously joined a unit's chunks with no separator, which dropped the newline the
    chunker recorded and fabricated tokens that appear in no committed record: "this
    Regulation.For example", "AI models.They should". Every one of the 144 inter-chunk gaps in the
    normalised files is a single newline, and BLOCK_SEPARATOR in the ingest modules is the same
    value, so the join is a reconstruction of the source and not a chosen separator.

    Enumerated over all 1150 units rather than sampled. Under the previous join this passes on
    1053 units and fails on the other 97.
    """
    assert CHUNK_JOIN == "\n"
    checked = 0
    for doc in DOCUMENTS:
        normalised = (CHUNKS / f"{doc}.normalized.txt").read_text(encoding="utf-8")
        by_unit: dict[str, list[dict]] = {}
        for line in (CHUNKS / f"{doc}.chunks.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                by_unit.setdefault(unit_of(record["chunk_id"]), []).append(record)
        for unit, records in by_unit.items():
            records.sort(key=lambda r: r["seq"])
            source = normalised[records[0]["char_start"]: records[-1]["char_end"]]
            assert corpus.unit_text[unit] == source, unit
            checked += 1
    assert checked == 1150


def test_no_segment_spans_a_chunk_boundary(corpus):
    """The consequence of the join, checked on the segmentation the arms actually consume.

    Under the previous join, 144 raw segments straddled an inter-chunk boundary and 141 of them
    survived into the comparable segmentation the committed cache embedded. A segment that
    straddles a boundary contains text from two chunk records joined by a character that is in
    neither.
    """
    for doc in DOCUMENTS:
        by_unit: dict[str, list[dict]] = {}
        for line in (CHUNKS / f"{doc}.chunks.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                by_unit.setdefault(unit_of(record["chunk_id"]), []).append(record)
        for unit, records in by_unit.items():
            if len(records) < 2:
                continue
            records.sort(key=lambda r: r["seq"])
            texts = [r["text"] for r in records]
            for segment in corpus.unit_segments[unit]:
                assert any(segment in t for t in texts), (unit, segment[:80])


def test_the_funnel_balances_for_every_single_unit(corpus):
    """Not sampled. The population is 1150 and enumerable, so it is enumerated."""
    for unit, text in corpus.unit_text.items():
        f = segmentation_funnel(text, corpus.unit_label[unit])
        assert (
            f["raw_segments"]
            - f["removed_no_alphabetic_word"]
            - f["removed_own_heading"]
            == f["comparable_segments"]
        )
        assert f["comparable_segments"] == len(corpus.unit_segments[unit])


# Lexical arm


def test_lexical_arm_finds_the_case_b_clause_in_the_real_corpus(corpus):
    result = lexical_arm(CASE_B_ARTICLE, {"eu_ai_act:art_13"}, corpus)
    assert "eu_ai_act:anx_IV" in {p["unit"] for p in result["pairs_at_or_above_floor"]}
    assert result["top_ratio"] >= LEXICAL_FLOOR


def test_lexical_arm_finds_case_a_partner_in_the_corpus(corpus):
    """Scanning the Article 26(5) span must surface Article 72(2), which is the whole point."""
    result = lexical_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus)
    assert result["pairs_at_or_above_floor"][0]["unit"] == "eu_ai_act:art_72"
    assert result["pairs_at_or_above_floor"][0]["ratio"] == 0.9397


def test_lexical_arm_excludes_gold_units(corpus):
    with_gold = lexical_arm(CASE_A_LEFT, set(), corpus)
    without = lexical_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus)
    assert "eu_ai_act:art_26" in {p["unit"] for p in with_gold["pairs_at_or_above_floor"]}
    assert "eu_ai_act:art_26" not in {p["unit"] for p in without["pairs_at_or_above_floor"]}
    assert without["units_compared"] == with_gold["units_compared"] - 1


def test_prefilter_does_not_change_the_result(corpus):
    """quick_ratio and real_quick_ratio are upper bounds, so the prefilter must be lossless."""
    span, gold = CASE_B_ARTICLE, {"eu_ai_act:art_13"}
    shipped = lexical_arm(span, gold, corpus)
    target = normalise_for_lexical(span)
    reference = []
    for unit, segs in sorted(corpus.unit_segments.items()):
        if unit in gold:
            continue
        for segment in segs:
            candidate = normalise_for_lexical(segment)
            if candidate:
                ratio = ratio_matcher(target, candidate).ratio()
                if ratio >= LEXICAL_FLOOR:
                    reference.append((unit, round(ratio, 4), segment))
    assert reference, "positive control: the unfiltered reference must find something"
    assert {(u, r, s) for u, r, s in reference} == {
        (p["unit"], p["ratio"], p["segment"]) for p in shipped["pairs_at_or_above_floor"]
    }


def test_an_unattributed_span_reports_empty_with_a_control(corpus):
    """An empty result is only trustworthy beside a control showing the arm can find hits."""
    invented = (
        "The zzqx committee shall publish a quarterly bulletin of neon marmalade quotas before "
        "the vernal equinox in each biennium"
    )
    empty = lexical_arm(invented, set(), corpus)
    assert empty["pairs_at_or_above_floor"] == []
    assert empty["top_ratio"] is None
    assert empty["segments_compared"] > 10000, "control: the arm really did compare the corpus"
    assert lexical_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus)["pairs_at_or_above_floor"]


def test_lexical_arm_reports_its_own_command_and_predicate(corpus):
    """The gap this instrument closes against the committed duplication_scan blocks."""
    result = lexical_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus)
    for field in ("predicate", "command", "reproducibility_level", "floor", "segments_compared"):
        assert field in result
    assert result["reproducibility_level"] == 1


# Corpus


def test_corpus_covers_every_committed_unit(corpus):
    index = json.loads((EVAL / "corpus_unit_index.json").read_text(encoding="utf-8"))
    assert set(corpus.unit_text) == {u["unit_id"] for u in index["units"]}
    assert len(corpus.unit_text) == 1150


def test_unit_of_uses_the_prefix_form():
    assert unit_of("eu_ai_act:art_37") == "eu_ai_act:art_37"
    assert unit_of("eu_ai_act:rct_111#p2") == "eu_ai_act:rct_111"


# Dense arm


def test_dense_arm_records_its_absence_rather_than_omitting_it(corpus):
    """A caller with no session gets a recorded reason, never a silently missing arm.

    The not-run block carries the predicate, the command and the reproducibility level too. The
    reviewer who reaches this block is by definition the one without the pinned model, so a bare
    reason string would be a dead end for the reader who most needs to know what was skipped and
    how to run it.
    """
    block = scan(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus=corpus, session=None)
    assert block["dense_arm"]["ran"] is False
    assert "reason" in block["dense_arm"]
    for field in ("predicate", "command", "reproducibility_level"):
        assert field in block["dense_arm"], f"not-run dense block is missing {field}"
    assert block["dense_arm"]["reproducibility_level"] == 3
    assert block["lexical_arm"]["pairs_at_or_above_floor"]
    assert block["segmenter"]["shared_by_both_arms"] is True
    assert block["exclusion_funnel"]["comparable_segments"] == 13316


# --- the two paths out of onnx_session, which must not report alike -----------------------------

def test_a_checksum_mismatch_raises_rather_than_reading_as_an_absent_model(monkeypatch):
    """A model that is present and wrong must not report the same as a model that is absent.

    The catch in `onnx_session` swallowed every exception, so a weight that failed its SHA-256
    returned None and the dense arm skipped with a message saying the model was not cached. An
    integrity check whose failure is indistinguishable from absence is not an integrity check, and
    this repository's whole argument is that verification has to be able to fail.

    Pinned here so the swallow cannot come back without deleting a failing test.
    """
    from src.retrieve import embed

    def tampered(*_args, **_kwargs):
        raise ValueError(f"ONNX checksum mismatch: expected {embed.ONNX_SHA256}, got {'0' * 64}")

    monkeypatch.setattr(embed, "download_onnx", tampered)
    with pytest.raises(ValueError, match="ONNX checksum mismatch"):
        onnx_session()


def test_an_absent_dependency_still_returns_none_rather_than_raising(monkeypatch):
    """The other path, unchanged: absence is a skip and not a failure.

    `huggingface_hub` is in the build-only `embed` group, so a default install cannot reach the
    model at all. That has to keep returning None, or every fresh clone fails the dense arm instead
    of skipping it, which is the behaviour the four dense-arm skips depend on.
    """
    from src.retrieve import embed

    def absent(*_args, **_kwargs):
        raise ImportError("No module named 'huggingface_hub'")

    monkeypatch.setattr(embed, "download_onnx", absent)
    assert onnx_session() is None


def test_an_absent_onnxruntime_still_returns_none_rather_than_raising(monkeypatch):
    """The second absence path, which fails later than the first and must report the same.

    The weight can be present and verified while `onnxruntime` is missing, because they arrive from
    different places. Narrowing the catch must not turn that into a failure either.
    """
    from src.retrieve import embed

    def no_runtime(*_args, **_kwargs):
        raise ImportError("No module named 'onnxruntime'")

    monkeypatch.setattr(embed, "download_onnx", lambda *a, **k: "/nonexistent/model.onnx")
    monkeypatch.setattr(embed, "make_session", no_runtime)
    assert onnx_session() is None


def _dense_or_skip(corpus):
    session = onnx_session()
    if session is None:
        pytest.skip(
            "the pinned ONNX model is not cached. It is deliberately outside the offline "
            "reproducibility set, so its absence skips the dense arm rather than failing it."
        )
    if load_segment_cache(corpus) is None:
        pytest.skip(
            "no segment embedding cache. It is deliberately not committed; build it with "
            "python -m src.goldset.build_segment_embeddings."
        )
    return session


def test_dense_arm_at_segment_granularity_finds_the_case_a_partner(corpus):
    """The payoff, and the reason the arm was re-pointed off chunk embeddings.

    A chunk-level dense arm ranked eu_ai_act:art_72 at 207 of 1149, cosine 0.5895, because the
    123-character span is 5.3 percent of art_72's 2318 characters. That was a wrong prediction
    made and measured before this change. At segment granularity both arms compare like with
    like.
    """
    session = _dense_or_skip(corpus)
    result = dense_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus, session)
    assert len(result["top_units"]) == DENSE_TOP_N
    assert "eu_ai_act:art_26" not in {u["unit"] for u in result["top_units"]}
    assert result["top_units"][0]["unit"] == "eu_ai_act:art_72"
    cosines = [u["cosine"] for u in result["top_units"]]
    assert cosines == sorted(cosines, reverse=True)


def test_dense_arm_applies_no_floor_and_declares_level_3(corpus):
    """A fixed N is reported whatever the scores are, so nothing is excluded by score."""
    session = _dense_or_skip(corpus)
    invented = (
        "The zzqx committee shall publish a quarterly bulletin of neon marmalade quotas before "
        "the vernal equinox in each biennium"
    )
    result = dense_arm(invented, set(), corpus, session)
    assert len(result["top_units"]) == DENSE_TOP_N, "a floor would have emptied this"
    assert result["reproducibility_level"] == 3
    assert result["model_revision"] == "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"


def test_dense_arm_scores_the_shared_segments(corpus):
    """The shared-segmenter condition, asserted on the dense side too."""
    session = _dense_or_skip(corpus)
    result = dense_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus, session)
    assert result["segments_scored"] == len(corpus.ordered_segments()) == 13316
    for entry in result["top_units"]:
        assert entry["segment"] in corpus.unit_segments[entry["unit"]]


# The reproduction manifest


def _manifest_or_skip():
    if not MANIFEST.exists():
        pytest.skip(
            "no reproduction manifest. It is emitted by the generator; build the cache with "
            "python -m src.goldset.build_segment_embeddings."
        )
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_carries_everything_needed_to_reproduce_the_cache():
    """The cache is 40.6 MB and does not ship, so the manifest is what keeps the arm checkable."""
    m = _manifest_or_skip()
    for field in (
        "cache_sha256",
        "cache_bytes",
        "n_segments",
        "segmentation_fingerprint",
        "segmenter",
        "exclusion_funnel",
        "model_repo",
        "model_revision",
        "generator_command",
        "reproducibility_level",
        "cache_sha256_determinism",
    ):
        assert field in m, f"manifest is missing {field}"
    assert m["model_revision"] == "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"
    assert m["generator_command"] == "python -m src.goldset.build_segment_embeddings"
    assert m["reproducibility_level"] == 3
    assert len(m["cache_sha256"]) == 64


def test_manifest_matches_the_cache_it_describes(corpus):
    """A manifest that drifted from its cache would certify the wrong artifact."""
    m = _manifest_or_skip()
    if not SEGMENT_VECTORS.exists():
        pytest.skip("the cache itself is not present; only the manifest ships.")
    actual = hashlib.sha256(SEGMENT_VECTORS.read_bytes()).hexdigest()
    assert m["cache_sha256"] == actual, "manifest digest does not match the cache on disk"
    assert m["cache_bytes"] == SEGMENT_VECTORS.stat().st_size
    assert m["segmentation_fingerprint"] == corpus.segmentation_fingerprint()
    assert m["n_segments"] == len(corpus.ordered_segments())
    assert m["exclusion_funnel"] == exclusion_report(corpus)


def test_the_digest_comparison_can_fail():
    """V20: a hash check that has never been shown to detect a difference certifies nothing."""
    m = _manifest_or_skip()
    mutated = hashlib.sha256(b"not the cache").hexdigest()
    assert mutated != m["cache_sha256"]
    assert len(mutated) == len(m["cache_sha256"]) == 64


def test_the_manifest_takes_no_value_from_the_untracked_index(corpus, tmp_path, monkeypatch):
    """No committed value is copied from an artifact nothing re-derives.

    The manifest ships. embeddings_cache/segment_index.json does not, and no committed test can
    re-derive it, because it is written by the generator and read by nothing else that ships. A
    manifest field copied out of it is therefore a committed number whose only source is a file a
    reviewer never sees, and the divergence is silent: the funnel in the same manifest is derived
    from the corpus, so a copied count can contradict its own neighbour without anything raising.

    Measured before this test existed. Moving n_segments to 13317 in the untracked index and
    re-running the generator's own write_manifest moved the committed manifest to 13317, where it
    disagreed with its corpus-derived comparable_segments of 13316, and nothing raised.

    Driven through the real write_manifest with both paths redirected, so what is exercised is the
    shipped derivation and not a restatement of it. The index handed in carries deliberately wrong
    counts and the correct fingerprint, so the staleness guard passes and the counts are the only
    thing under test.
    """
    if not SEGMENT_VECTORS.exists():
        pytest.skip("the cache itself is not present; only the manifest ships.")
    import src.goldset.build_segment_embeddings as gen

    corrupted = json.loads(SEGMENT_INDEX.read_text(encoding="utf-8"))
    corrupted["n_segments"] = 13317
    corrupted["n_units"] = 999
    index_path = tmp_path / "segment_index.json"
    index_path.write_text(json.dumps(corrupted, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    out = tmp_path / "segment_embedding_manifest.json"
    monkeypatch.setattr(gen, "SEGMENT_INDEX", index_path)
    monkeypatch.setattr(gen, "MANIFEST", out)

    emitted = gen.write_manifest(corpus)

    pairs = corpus.ordered_segments()
    assert emitted["n_segments"] == len(pairs), (
        f"n_segments is {emitted['n_segments']} against {len(pairs)} segments derived from the "
        "corpus. It was taken from the untracked index rather than re-derived"
    )
    assert emitted["n_units"] == len({unit for unit, _ in pairs}), (
        f"n_units is {emitted['n_units']} and was taken from the untracked index"
    )
    assert emitted["n_segments"] == emitted["exclusion_funnel"]["comparable_segments"], (
        "the manifest disagrees with its own funnel, which is the shape the copied value produced"
    )


def test_the_index_carries_no_wall_clock_field(corpus):
    """build_seconds made the index non-byte-deterministic, and it is gone.

    Two clean-state generations produced byte-identical arrays and byte-identical manifests, and
    indexes that differed in this field alone. Removing it is what lets the index be compared
    across runs at all.

    Asserted against the generator's emitted payload and deliberately not against the file on
    disk. The payload is the property this repository can hold for every reviewer's build; a local
    cache written before this change is stale environment, not a repository defect, and after the
    manifest stopped reading values from the index a leftover field there reaches nothing that
    ships. Asserting on the file would turn one operator's un-regenerated cache into a red suite
    and would be checking the machine rather than the code.
    """
    import src.goldset.build_segment_embeddings as gen

    emitted = gen.index_payload(corpus, n_segments=13316)
    assert "build_seconds" not in emitted, (
        "build_seconds is back in the index payload. It records wall time, so it makes the index "
        "differ between two runs that produced identical embeddings"
    )
    assert not any("second" in k for k in emitted), f"a wall-clock field remains: {sorted(emitted)}"


def test_the_index_payload_is_a_function_of_the_corpus_alone(corpus):
    """V20 companion: the emitted payload is shown to be reproducible and to be able to differ.

    Two calls with the same arguments are equal, and a call with a different segment count is not,
    so the equality above is a property of the payload rather than of the comparison.
    """
    import src.goldset.build_segment_embeddings as gen

    a = gen.index_payload(corpus, n_segments=13316)
    b = gen.index_payload(corpus, n_segments=13316)
    assert a == b, "two identical calls disagreed"
    c = gen.index_payload(corpus, n_segments=13317)
    assert a != c, "the comparison cannot distinguish two different payloads"
    assert c["n_segments"] == 13317


def test_the_dense_arm_compares_the_segment_population_not_chunks():
    """The invariant that replaces a regression test the removed code path can no longer support.

    What must not silently revert is not that chunk granularity was once wrong, which is a dead
    failure with nothing left to drive it. It is that both arms compare the same population. This
    is asserted at the source so it holds without the pinned model, and again at runtime wherever
    the cache is present.

    A return to chunk granularity fails here: it would have to index the committed chunk order and
    the committed chunk embeddings, and it would stop walking the shared segmentation.
    """
    source = inspect.getsource(dense_arm)
    assert "corpus.ordered_segments()" in source, (
        "the dense arm no longer walks the shared segment population"
    )
    assert "chunk_order" not in source, "the dense arm reads the committed chunk order again"
    assert "embeddings.npy" not in source, "the dense arm reads the committed chunk embeddings again"

    # Semantic rather than textual: prose in the docstrings names data/retrieval and should. What
    # must not exist is a path CONSTANT pointing there, or a non-docstring literal building one.
    module = sys.modules[dense_arm.__module__]
    retrieval_dir = REPO_ROOT / "data" / "retrieval"
    pointing = [
        name
        for name, value in vars(module).items()
        if isinstance(value, Path) and retrieval_dir in value.parents
    ]
    assert not pointing, f"module holds path constants under data/retrieval: {pointing}"

# A textual scan over the module was tried and abandoned: the docstrings name
    # data/retrieval deliberately, to say what the module does NOT read and to cite the
    # manifest's reproducibility levels, so any text-matching form fights its own prose. The
    # path-constant check above is the semantic one, and the dense_arm source assertions are
    # what catch an actual return to chunk granularity.


def test_the_dense_arm_scored_population_equals_the_segment_population(corpus):
    """The runtime half of the invariant, wherever the model and cache are present."""
    session = _dense_or_skip(corpus)
    result = dense_arm(CASE_A_LEFT, {"eu_ai_act:art_26"}, corpus, session)
    assert result["segments_scored"] == len(corpus.ordered_segments())
    assert result["segments_scored"] == corpus.funnel["comparable_segments"] == 13316
    for entry in result["top_units"]:
        assert entry["segment"] in corpus.unit_segments[entry["unit"]]
