"""The alignment control: rebuild, the join to the grading artifact, and the memoisation.

WHAT THIS FILE COVERS AND WHAT THE DIGEST PIN COVERS. tests/test_flagged_alignment_control_digest.py
pins the committed bytes. This file asserts the producer re-derives them from committed inputs, and
asserts the properties a digest cannot see: that the measured side is read out of the grading
artifact rather than recomputed, that the null is enumerated rather than sampled, and that the
memoisation the producer uses for speed is a memoisation rather than an approximation. The two pins
cover different things and only together cover the artifact, which is the division the three
existing result artifacts already use.

THE NAIVE CROSS-CHECK IS AN INDEPENDENT IMPLEMENTATION, not a second call into the same helper.
V4 wants two implementations disagreeing to be information. The producer scores each unit against
each distinct block once and takes a maximum per row; the check below walks a row's chunks in
order, renders and tokenises each one itself, and keeps a running maximum, with no cache and no
shared state, over a fixed stride through BOTH populations. A disagreement would mean the
memoisation is dropping or reusing a value it should not.

THE READ GUARD IS TOTAL RATHER THAN SAMPLED. Every file the producer opens is opened inside
load_flagged or load_foreign_blocks, and window_score opens nothing, so patching open around those
two functions covers the producer's whole file surface. That is why the guard runs in under a
second while the full build does not.
"""

from __future__ import annotations

import builtins
import json

import pytest

from src.generate.assemble import first_pass_chunks, load_chunk_store, load_rows
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import primary_tokens
from src.score import run_flagged_alignment_control as control
from src.score.grounding import rendered_block, window_score

CONTROL_PATH = REPO_ROOT / "eval" / "test_flagged_alignment_control.json"
GRADING_PATH = REPO_ROOT / "eval" / "test_grading_results.json"

# Paths that would mean the producer reached for a model or an embedding array. It reads committed
# text and nothing else, so every one of these must stay untouched.
MODEL_PATH_MARKERS = (
    "data/retrieval/embeddings.npy",
    "eval/test_query_embeddings.npy",
    "eval/dev_query_embeddings.npy",
    "/vendor/",
)

# Every third unit, so the naive cross-check spans all three tiers and both ends of the
# distribution without rebuilding 109 units by hand. Fixed before any value was read.
NAIVE_CHECK_STRIDE = 3


@pytest.fixture(scope="module")
def committed():
    return json.loads(CONTROL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rebuilt():
    return control.build()


def test_the_control_artifact_exists_and_ships():
    assert CONTROL_PATH.exists(), (
        "eval/test_flagged_alignment_control.json is the alignment control's artifact and is "
        "missing"
    )


def test_rebuilding_reproduces_the_committed_artifact_byte_for_byte(committed, rebuilt):
    """The strongest form of the level-1 claim: the producer re-run over committed inputs
    reproduces the committed bytes, not merely the committed numbers."""
    payload = json.dumps(rebuilt, indent=1, ensure_ascii=False) + "\n"
    assert payload == CONTROL_PATH.read_text(encoding="utf-8")
    assert rebuilt == committed


def test_the_rebuild_comparison_can_fail(rebuilt):
    """V20. A comparison that could only pass would certify nothing.

    Both sides are asserted to be non-empty strings of the same shape before they are compared, so
    a pass cannot come from comparing two absences, which is the failure mode V20 names.
    """
    payload = json.dumps(rebuilt, indent=1, ensure_ascii=False) + "\n"
    on_disk = CONTROL_PATH.read_text(encoding="utf-8")
    assert len(payload) > 1000 and len(on_disk) > 1000
    assert payload == on_disk

    mutated = payload.replace('"reproducibility_level": 1', '"reproducibility_level": 2', 1)
    assert mutated != payload, "the mutation did not apply, so the check below proves nothing"
    assert mutated != on_disk


def test_the_null_is_enumerated_and_not_sampled(committed):
    """The sampling decision, asserted rather than trusted to the prose that records it.

    Every unit of BOTH populations carries a figure for every sealed row except its own. A sampled
    version would carry fewer, and the count is what separates the two.
    """
    rows = committed["coverage"]["sealed_rows"]
    assert committed["sampling_decision"]["decision"] == "enumerated, not sampled"
    for key, name in (("units", "flagged"), ("supported_units", "supported")):
        for unit in committed[key]:
            assert unit["foreign_rows"] == rows - 1, (name, unit["query_id"])
            assert len(unit["foreign_overlap_max_by_row"]) == rows - 1
            assert unit["query_id"] not in unit["foreign_overlap_max_by_row"], (
                "a unit was scored against its own row, which would not be a foreign context"
            )
        block = committed["populations"][name]
        assert block["null_distribution"]["pairs"] == len(committed[key]) * (rows - 1)


def test_the_own_side_is_read_from_the_grading_artifact_and_not_recomputed(committed):
    """The measured side comes out of the grader's committed output, exactly.

    If this file recomputed it instead, the two could disagree while both passed their own checks.
    Asserted over every unit rather than a sample, because the population is 109.
    """
    grading = json.loads(GRADING_PATH.read_text(encoding="utf-8"))
    checked = 0
    for unit in committed["units"] + committed["supported_units"]:
        graded = grading["rows"]["raw"][unit["tier"]][unit["query_id"]]
        matches = [u for u in graded["units"] if u["text"] == unit["text"]]
        assert len(matches) == 1, (unit["tier"], unit["query_id"])
        source = matches[0]
        assert unit["own_overlap_max"] == source["overlap_max"]
        assert unit["own_score"] == source["score"]
        assert unit["own_grounded"] == source["grounded"]
        assert unit["n_tokens"] == source["n_tokens"]
        assert unit["n_surfaces"] == source["n_surfaces"]
        assert unit["threshold"] == source["threshold"]
        checked += 1
    assert checked == len(committed["units"]) + len(committed["supported_units"]) == 251


def test_the_population_is_the_committed_flagged_lists(committed):
    """The funnel, re-derived from the three flagged artifacts rather than read from this file."""
    expected: list[tuple[str, str, str]] = []
    for tier in control.TIER_KEYS:
        artifact = json.loads(control.flagged_path(tier).read_text(encoding="utf-8"))
        for row in sorted(artifact["rows"].values(), key=lambda r: r["query_id"]):
            for text in row["flagged_units"]:
                expected.append((tier, row["query_id"], text))
    actual = [(u["tier"], u["query_id"], u["text"]) for u in committed["units"]]
    assert actual == expected
    funnel = committed["populations"]["flagged"]["funnel"]
    assert funnel["flagged_units"] == len(expected) == 109


def test_the_memoised_foreign_scores_match_a_naive_recomputation(committed):
    """V4. An independent walk over the same pairs, with no cache and its own tokenisation."""
    store = load_chunk_store()
    rows = {row["id"]: row for row in load_rows(control.QUERY_SET)}
    row_ids = sorted(rows)

    sample = (
        committed["units"][::NAIVE_CHECK_STRIDE]
        + committed["supported_units"][::NAIVE_CHECK_STRIDE]
    )
    compared = 0
    for unit in sample:
        unit_tokens = primary_tokens(unit["text"])
        for query_id in row_ids:
            if query_id == unit["query_id"]:
                continue
            best = 0.0
            for chunk in first_pass_chunks(rows[query_id], store):
                score = window_score(unit_tokens, primary_tokens(rendered_block(chunk)))
                if score > best:
                    best = score
            assert unit["foreign_overlap_max_by_row"][query_id] == best, (
                unit["tier"], unit["query_id"], query_id
            )
            compared += 1
    assert compared == len(sample) * (len(row_ids) - 1)
    assert compared > 3000, "the cross-check covered too few pairs to mean anything"


def test_the_naive_crosscheck_can_fail(committed):
    """V20 companion. The comparison above must reject a value it should reject.

    A real pair is recomputed and compared against a deliberately wrong figure, so the assertion
    form used above is shown to distinguish rather than to pass on anything.
    """
    store = load_chunk_store()
    rows = {row["id"]: row for row in load_rows(control.QUERY_SET)}
    unit = committed["units"][0]
    foreign = sorted(unit["foreign_overlap_max_by_row"])[0]

    unit_tokens = primary_tokens(unit["text"])
    best = 0.0
    for chunk in first_pass_chunks(rows[foreign], store):
        score = window_score(unit_tokens, primary_tokens(rendered_block(chunk)))
        if score > best:
            best = score
    assert unit["foreign_overlap_max_by_row"][foreign] == best
    assert unit["foreign_overlap_max_by_row"][foreign] != best + 0.5


def test_the_producer_opens_no_embedding_array_and_no_model():
    """It resolves and compares committed text. It embeds nothing and ranks nothing.

    Total rather than sampled: load_flagged and load_foreign_blocks are where every open() in the
    producer lives, and window_score opens nothing, so this covers the whole file surface.
    """
    real_open = builtins.open
    touched: list[str] = []

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for marker in MODEL_PATH_MARKERS:
            if marker in text:
                touched.append(text)
        return real_open(file, *args, **kwargs)

    builtins.open = guard
    try:
        control.load_flagged()
        control.load_foreign_blocks()
    finally:
        builtins.open = real_open
    assert touched == []


def test_the_read_guard_can_fail():
    """V20 companion. A guard matching nothing would pass the test above against any code at all."""
    real_open = builtins.open
    touched: list[str] = []

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for marker in MODEL_PATH_MARKERS:
            if marker in text:
                touched.append(text)
        return real_open(file, *args, **kwargs)

    builtins.open = guard
    try:
        with open(REPO_ROOT / "eval" / "test_query_embeddings.npy", "rb"):
            pass
    finally:
        builtins.open = real_open
    assert len(touched) == 1 and touched[0].endswith("eval/test_query_embeddings.npy")


def test_the_two_cuts_each_partition_the_population(committed):
    """The paired test and the quantile cut are different cuts, and each sums to 109 on its own.

    Pinned because pairing a count from one with a count from the other is exactly the arithmetic
    error that produced a 106 out of a population of 109 while this measurement was being drafted.
    """
    total = len(committed["units"])
    paired = committed["populations"]["flagged"]["paired_result"]
    assert paired["beats_every_foreign_row"] + paired["does_not_beat_every_foreign_row"] == total
    assert paired["of"] == total

    cut = committed["pooled_quantile_cut"]
    assert cut["above"] + cut["at_or_below"] == total
    assert cut["of"] == total

    assert paired["beats_every_foreign_row"] != cut["above"], (
        "the two cuts returning the same count would not be an error, but it would make the "
        "distinction this test exists to keep invisible; if it ever becomes true, say so rather "
        "than deleting the test"
    )

    per_tier = committed["populations"]["flagged"]["per_tier"]
    assert sum(v["units"] for v in per_tier.values()) == total
    assert sum(v["beats_every_foreign_row"] for v in per_tier.values()) == (
        paired["beats_every_foreign_row"]
    )
    assert sum(v["above_the_pooled_flagged_null_q95"] for v in per_tier.values()) == cut["above"]


def test_the_artifact_carries_the_caveats_a_reader_of_its_numbers_needs(committed):
    """The limits live in the artifact, not only in a report that does not ship with it."""
    assert "upper bound on chance" in committed["foreign_context_caveat"]
    for name in ("flagged", "supported"):
        assert "upper bound" in committed["populations"][name]["null_distribution"]["caveat"]
    assert "punishes paraphrase" in committed["what_this_cannot_settle"]
    assert "V15" in committed["decides_nothing"]
    assert committed["sampling_decision"]["reason"].startswith("CLAUDE.md V5")
    assert committed["reproducibility_level"] == 1
    assert committed["produced_by"] == "python -m src.score.run_flagged_alignment_control"


def test_the_score_bimodality_block_reports_the_mechanism_and_not_a_source_signal(committed):
    """The low mode of `score` is the reference condition. Re-derived here from the units."""
    block = committed["score_bimodality"]
    zeros = [u for u in committed["units"] if u["own_score"] == 0.0]
    assert block["units_with_score_exactly_zero"] == len(zeros)
    assert all(u["n_surfaces"] > 0 for u in zeros)
    assert block["all_of_them_carry_a_reference_surface"] is True
    assert block["their_overlap_max_max"] > 0.5, (
        "a unit scoring exactly zero under the grader while aligning well above the threshold on "
        "the overlap term alone is the whole point of this block"
    )
    no_surface = [u for u in committed["units"] if u["n_surfaces"] == 0]
    assert all(u["own_score"] == u["own_overlap_max"] for u in no_surface)
    assert block["units_carrying_no_reference_surface"] == len(no_surface)


def test_the_two_populations_partition_the_raw_condition_over_the_fired_rows(committed):
    """The control's population is the exact complement of the flagged one, re-derived here.

    If the two did not partition, the comparison would be between overlapping or incomplete sets
    and every rate in it would be about something other than what it claims.
    """
    grading = json.loads(GRADING_PATH.read_text(encoding="utf-8"))
    fired = {}
    for tier in control.TIER_KEYS:
        artifact = json.loads(control.flagged_path(tier).read_text(encoding="utf-8"))
        fired[tier] = {row["query_id"] for row in artifact["rows"].values()}

    expected_flagged, expected_supported, all_units = 0, 0, 0
    for tier in control.TIER_KEYS:
        for query_id, row in grading["rows"]["raw"][tier].items():
            all_units += len(row["units"])
            if query_id not in fired[tier]:
                continue
            for unit in row["units"]:
                if unit["grounded"]:
                    expected_supported += 1
                else:
                    expected_flagged += 1

    assert len(committed["units"]) == expected_flagged == 109
    assert len(committed["supported_units"]) == expected_supported == 142
    assert expected_flagged + expected_supported == 251

    funnel = committed["populations"]["supported"]["funnel"]
    assert funnel["raw_claim_units_on_those_pairs"] == 251
    assert funnel["of_those_grounded_which_is_this_population"] == 142
    assert funnel["of_those_ungrounded_which_are_the_flagged_population"] == 109

    reconciliation = funnel["reconciliation_over_all_fifty_rows"]
    assert reconciliation["raw_claim_units"] == all_units == 269
    assert reconciliation["grounded"] == 149
    assert reconciliation["ungrounded"] == 120
    assert reconciliation["ungrounded_on_the_two_unfired_rows"] == 11
    assert reconciliation["grounded"] + reconciliation["ungrounded"] == 269

    pooled = grading["per_condition"]["raw"]["pooled"]
    assert pooled["claim_units"] == 269
    assert pooled["grounded_units"] == 149
    assert pooled["ungrounded_units"] == 120


def test_the_three_way_split_sums_to_its_population_and_matches_the_margins(committed):
    """Strictly beats, ties and strictly worse partition each population, re-derived from margins.

    The strict-inequality rate collapses ties into losses, and a tie is the same block appearing in
    another row's top ten rather than a failure to detect support. Pinned so the collapse cannot
    come back silently.
    """
    for key, name in (("units", "flagged"), ("supported_units", "supported")):
        units = committed[key]
        three = committed["populations"][name]["paired_result"]["three_way"]
        beats = sum(1 for u in units if u["margin"] > 0)
        ties = sum(1 for u in units if u["margin"] == 0)
        worse = sum(1 for u in units if u["margin"] < 0)
        assert beats + ties + worse == len(units)
        assert three["strictly_beats"] == beats
        assert three["ties_its_best_foreign_row"] == ties
        assert three["strictly_worse_than_its_best_foreign_row"] == worse
        assert three["at_least_ties"] == beats + ties
        assert three["strictly_beats"] == (
            committed["populations"][name]["paired_result"]["beats_every_foreign_row"]
        )
        # Every tie is an exact equality with the best foreign row, which is what makes a tie a
        # statement about duplication rather than about detection.
        assert three["ties_whose_foreign_max_equals_their_own_overlap_max"] == ties
        for unit in units:
            assert unit["margin"] == round(unit["own_overlap_max"] - unit["foreign_max"], 6)


def test_the_positive_control_states_what_it_cannot_reach(committed):
    """The circularity is disclosed in the artifact, not left for a reader to notice.

    Grounded means the overlap term reached the threshold, so every supported unit carries an
    own-context overlap at or above its threshold by construction. That is asserted here as well as
    stated, because a disclosure that is false about the file it ships in is worse than none.
    """
    assert "near-verbatim" in committed["what_the_positive_control_cannot_reach"]
    assert "paraphrase" in committed["what_the_positive_control_cannot_reach"]
    assert "ragas" in committed["what_the_positive_control_cannot_reach"].lower()
    assert "emptiness-claim" in committed["why_the_second_population_is_here"]

    for unit in committed["supported_units"]:
        assert unit["own_grounded"] is True
        assert unit["own_score"] >= unit["threshold"]
        assert unit["own_overlap_max"] >= unit["own_score"]
    for unit in committed["units"]:
        assert unit["own_grounded"] is False


def test_the_shared_null_question_is_answered_from_the_two_populations(committed):
    """The two nulls are reported side by side, and the difference is re-derived here.

    A comparison that assumed one baseline would be comparing two things if the baselines differ,
    so the artifact carries both rather than one.
    """
    shared = committed["comparison"]["shared_null"]
    for name, key in (("flagged", "flagged_null"), ("supported", "supported_null")):
        assert shared[key] == committed["populations"][name]["null_distribution"]["summary"]
    assert shared["median_difference"] == round(
        shared["supported_null"]["median"] - shared["flagged_null"]["median"], 6
    )
    assert shared["supported_null"]["n"] == 142 * 49
    assert shared["flagged_null"]["n"] == 109 * 49
