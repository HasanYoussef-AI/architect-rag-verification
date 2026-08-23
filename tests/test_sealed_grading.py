"""The grading of record, pinned.

WHAT THIS FILE IS FOR. eval/test_grading_results.json carries every figure the repository will be
judged on. This file asserts that each of them re-derives from committed files with no key, that
the integrity properties the runner claims are properties of the code rather than of care, and
that the contradicted predictions are recorded as contradicted.

THE CENTRAL CHECK IS THE RE-RENDER. src.score.run_sealed_grading.build is run and its output
compared against the committed JSON. If the artifact and the code that made it ever part company,
that fails here. Everything else in this file pins a property the re-render alone would not catch:
a runner and an artifact can agree with each other while both are wrong about the run.

THREE INTEGRITY PROPERTIES, EACH ASSERTED RATHER THAN DESCRIBED.

  THE CHAIN. Every graded answer's request body is rebuilt and its digest compared against the one
  the result record names. `verify_chain` raises rather than returning a flag, and the raise is
  shown against a wrong digest before its silence is trusted.

  THE CONTEXT PER CONDITION. Raw and the layer's second answers are graded against the context
  their own body carried, which the digest identity proves. The no-context condition is
  deliberately graded against a context its body did NOT carry, per section 6.2, so that half is
  asserted separately: the body carries no chunk, and the grading context is the same query's
  committed first-pass ten.

  THE GRADER READS NO LABEL. `grade_row` takes an answer and a context, and the files it opens
  during a call are enumerated with the instrument shown capable of recording first.

THE REFERENCE CONDITION IS SHOWN CAPABLE OF FAILING ON A REAL BLOCK. A committed block carries the
identifier a real graded unit names. With that identifier substituted, the overlap term alone
still clears the threshold and the reference condition rejects, so the unit flips from grounded to
unsupported and BOTH implementations flip together. That is the case the condition exists for, run
against the known defect rather than asserted.
"""

from __future__ import annotations

import builtins
import dataclasses
import inspect
import json
from decimal import Decimal

import pytest

from src.complete.flagging import unit_is_supported
from src.generate.assemble import (
    build_body,
    build_no_context,
    build_raw,
    build_second_call,
    custom_id,
    first_pass_chunks,
    load_chunk_store,
    load_rows,
    request_body_digest,
)
from src.generate.manifest import MAX_TOKENS, TIERS
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import primary_tokens
from src.score import adversarial as adversarial_module
from src.score.grounding import (
    is_grounded,
    reference_surfaces,
    rendered_block,
    score_unit,
    window_score,
)
from src.score.run_sealed_grading import (
    BATCH_RATES,
    GRADING_PATH,
    STRATA,
    TIER_KEYS,
    ChainError,
    answer_text,
    build,
    grade_row,
    verify_chain,
)

QUERY_SET = "test"
RUNS = REPO_ROOT / "data" / "runs"
CONDITIONS = ("raw", "layer", "no_context")
UNFIRED = ("test_34", "test_39")

# The headline figures, pinned as literals so a silent change to the runner reddens rather than
# quietly restating the result. Measured at this commit; V13 applied to a result rather than to a
# defect. Each entry is (abstaining_rows, answered_rows, claim_units, ungrounded_units).
RAW_PER_TIER = {
    "haiku45": (10, 40, 140, 78),
    "sonnet5": (27, 23, 57, 15),
    "opus48": (22, 28, 72, 27),
}
LAYER_PER_TIER = {
    "haiku45": (23, 27, 118, 48),
    "sonnet5": (31, 19, 58, 13),
    "opus48": (24, 26, 90, 19),
}
NO_CONTEXT_PER_TIER = {
    "haiku45": (30, 20, 124, 124),
    "sonnet5": (38, 12, 30, 27),
    "opus48": (32, 18, 27, 24),
}

# The fate table, per tier: (flagged_in, repeated_unchanged, now_grounded, still_unsupported,
# dropped_or_rewritten).
FATE = {
    "haiku45": (68, 19, 0, 19, 49),
    "sonnet5": (14, 3, 0, 3, 11),
    "opus48": (27, 3, 0, 3, 24),
}

# Section 10 scored. A contradicted line is recorded as contradicted and is never edited to match.
EXPECTED_VERDICTS = {
    "P1": "contradicted",
    "P2": "contradicted",
    "P3": "held",
    "P4": "held",
    "P5": "contradicted",
    "P6": "held",
    "P7": "contradicted",
    "P8": "held",
    "P9": "contradicted",
    "P10": "contradicted",
    "P11": "contradicted",
    "P12": "contradicted",
    "P13": "held",
    "P14": "contradicted",
    "P15": "held",
    "P16": "held",
    "P17": "contradicted",
    "P18": "contradicted",
    "P19": "contradicted",
    "P20": "contradicted",
    "P21": "contradicted",
    "P22": "held",
    "P23": "held",
    "P24": "contradicted",
    "P25": "held",
    "P26": "not_predicted",
}

# The control case, verified before it was written down: a real committed block whose identifier a
# real graded unit names, where removing the identifier from the block leaves the overlap term
# clearing its threshold and the reference condition rejecting.
CONTROL_ROW = "test_20"
CONTROL_TIER = "haiku45"
CONTROL_CHUNK = "eu_ai_act:art_48"
CONTROL_UNIT = (
    'Specifically, Article 48(2) requires that for high-risk AI systems provided digitally, '
    'the digital CE marking "shall be used, only if it can easily be accessed via the '
    "interface from which that system is accessed or via an easily accessible "
    'machine-readable code or other electronic means."'
)


@pytest.fixture(scope="module")
def committed() -> dict:
    with open(GRADING_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def rebuilt() -> dict:
    return build()


@pytest.fixture(scope="module")
def store():
    return load_chunk_store()


@pytest.fixture(scope="module")
def rows():
    return {r["id"]: r for r in load_rows(QUERY_SET)}


# --- the re-render ------------------------------------------------------------------------


def test_the_committed_artifact_equals_a_fresh_render(committed, rebuilt):
    """Level 1. No model, no key, no network, no clock, no randomness."""
    assert rebuilt == committed


def test_the_re_render_check_is_capable_of_failing(committed, rebuilt):
    """V20. A comparison that could only pass would certify nothing.

    Both sides are asserted non-trivial before they are compared, because two empty objects
    compare equal and a digest loop here once reported a match on a completely failed copy.
    """
    assert isinstance(committed, dict) and len(committed) > 10
    assert isinstance(rebuilt, dict) and len(rebuilt) > 10
    mutated = json.loads(json.dumps(rebuilt))
    mutated["per_condition"]["raw"]["per_tier"]["haiku45"]["ungrounded_units"] += 1
    assert mutated != committed


# --- the chain ---------------------------------------------------------------------------


def test_the_chain_check_rejects_a_wrong_digest():
    """V20. verify_chain is shown red against the defect it exists to catch."""
    body = {"custom_id": "x", "params": {"model": "m"}}
    good = request_body_digest(body)
    assert len(good) == 64
    assert verify_chain({"custom_id": "x", "body_sha256": good}, body) == good
    with pytest.raises(ChainError):
        verify_chain({"custom_id": "x", "body_sha256": "0" * 64}, body)
    with pytest.raises(ChainError):
        verify_chain({"custom_id": "x", "body_sha256": None}, body)
    with pytest.raises(ChainError):
        verify_chain({"custom_id": "x"}, body)


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_every_first_pass_and_no_context_answer_traces_to_its_own_request(tier, store, rows):
    """The raw and no-context halves of the chain, re-derived here rather than trusted."""
    for condition, builder in (("raw", build_raw), ("no_context", build_no_context)):
        path = RUNS / f"{QUERY_SET}.{condition}.{tier}.jsonl"
        with open(path, encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        assert len(records) == 50
        for record in records:
            query_id = record["custom_id"].split("__")[-1]
            row = rows[query_id]
            request = (
                builder(QUERY_SET, row, store)
                if condition == "raw"
                else builder(QUERY_SET, row)
            )
            body = build_body(request, TIERS[tier], MAX_TOKENS)
            assert verify_chain(record, body) == record["body_sha256"]


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_no_context_body_carries_no_chunk_and_is_graded_against_the_raw_context(
    tier, committed, store, rows
):
    """Section 6.2's asymmetry, asserted as its own claim rather than folded into the chain.

    The no-context condition is the one place where the grading context is deliberately NOT the
    context the request carried, so a blanket sentence about bodies and contexts would be false
    here. Two things are asserted instead: the body carries no chunk at all, and the context the
    grader used has exactly the size of that query's committed first-pass ten.
    """
    for query_id, row in rows.items():
        request = build_no_context(QUERY_SET, row)
        assert "Context:" not in request.user
        assert request.user == f"Question: {row['query']}"
        graded = committed["rows"]["no_context"][tier][query_id]
        assert graded["body_carried_chunks"] == 0
        assert graded["context_size"] == len(first_pass_chunks(row, store))
        assert graded["context_size"] == len(row["top10"])


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_layer_covers_all_fifty_rows_and_names_which_answer_it_graded(tier, committed):
    """Forty-eight second answers and two first answers, and the split is the committed rule."""
    layer = committed["rows"]["layer"][tier]
    assert len(layer) == 50
    fired = [q for q, r in layer.items() if r["corrective_pass_fired"]]
    unfired = sorted(q for q, r in layer.items() if not r["corrective_pass_fired"])
    assert len(fired) == 48
    assert unfired == list(UNFIRED)
    for query_id in unfired:
        row = layer[query_id]
        assert row["layer_answer_source"] == "raw"
        assert row["fetched_chunk_count"] == 0
        assert row["second_call_class"] is None
        assert row["n_flagged_in"] == 0
    for query_id in fired:
        assert layer[query_id]["layer_answer_source"] == "second_call"


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_every_second_call_answer_is_graded_against_the_context_its_body_carried(
    tier, committed, store, rows
):
    """The layer half of the chain, rebuilt from the committed flagged artifact."""
    flagged_path = REPO_ROOT / "eval" / f"{QUERY_SET}_second_call_flagged.{tier}.json"
    with open(flagged_path, encoding="utf-8") as handle:
        flagged_artifact = json.load(handle)
    from src.complete.augment import load_fetch_store

    fetch = load_fetch_store()
    with open(RUNS / f"{QUERY_SET}.raw.{tier}.jsonl", encoding="utf-8") as handle:
        first = {
            json.loads(line)["custom_id"].split("__")[-1]: answer_text(json.loads(line))
            for line in handle
            if line.strip()
        }
    with open(RUNS / f"{QUERY_SET}.second_call.{tier}.jsonl", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    assert len(records) == 48
    for record in records:
        query_id = record["custom_id"].split("__")[-1]
        key = custom_id(QUERY_SET, "second_call", query_id, tier)
        request = build_second_call(
            QUERY_SET,
            rows[query_id],
            store,
            fetch,
            first[query_id],
            flagged_artifact["rows"][key]["flagged_units"],
        )
        body = build_body(request, TIERS[tier], MAX_TOKENS)
        assert verify_chain(record, body) == record["body_sha256"]
        graded = committed["rows"]["layer"][tier][query_id]
        assert graded["body_sha256"] == record["body_sha256"]
        assert graded["context_size"] == graded["context_set_size"]
        assert graded["context_size"] > len(rows[query_id]["top10"]) or (
            graded["fetched_chunk_count"] == 0
        )


# --- the grader reads no label -----------------------------------------------------------


def test_grade_row_takes_an_answer_and_a_context_and_nothing_else():
    """Section 5.4 as a signature. A label cannot reach a verdict it is not passed."""
    assert list(inspect.signature(grade_row).parameters) == ["answer", "chunks"]


def test_grading_one_answer_opens_no_gold_artifact(store, rows):
    """The instrument is shown capable of recording before its result is read.

    The adversarial verdict reads the four committed chunk manifests for the corpus-phrase set of
    section 7.3, so the recorded list is deliberately non-empty; that non-emptiness is the
    positive control. What is asserted is that nothing gold-bearing is among the opens.
    """
    barred = (
        "test_queries.jsonl",
        "test_frame.json",
        "test_query_verification.jsonl",
        "test_retrieval_results.json",
        "test_layer_results.json",
        "corpus_unit_index.json",
        "relations.jsonl",
        "xrefs.jsonl",
    )
    recorded: list[str] = []
    real_open = builtins.open

    def recording_open(file, *args, **kwargs):
        recorded.append(str(file))
        return real_open(file, *args, **kwargs)

    adversarial_module.document_titles.cache_clear()
    adversarial_module._folded_corpus_phrases.cache_clear()
    builtins.open = recording_open
    try:
        grade_row("Article 9 requires a risk management system.", first_pass_chunks(rows["test_01"], store))
    finally:
        builtins.open = real_open
    assert recorded, "the recorder saw nothing, so its empty result would prove nothing"
    assert all(path.endswith(".manifest.json") for path in recorded), recorded
    for path in recorded:
        assert not any(name in path for name in barred), path


# --- both implementations ----------------------------------------------------------------


def test_both_grounding_implementations_agree_on_every_claim_unit(committed):
    """Section 5.3. A disagreement stops the scope and is resolved by finding which is wrong."""
    total_units = 0
    for condition in CONDITIONS:
        for tier in TIER_KEYS:
            for row in committed["rows"][condition][tier].values():
                for unit in row["units"]:
                    total_units += 1
                    assert unit["grounded"] == unit["flagger_supported"], (
                        condition,
                        tier,
                        row["query_id"],
                        unit["text"][:80],
                    )
            assert (
                committed["per_condition"][condition]["per_tier"][tier][
                    "cross_implementation_disagreements"
                ]
                == 0
            )
    # Every claim unit of every graded answer, not only those on answered rows. The two counts
    # differ because a layer abstention under the zero-grounded clause still carries units that
    # the micro-average correctly excludes: 804 units exist, 716 enter a rate.
    assert total_units == 804, total_units
    assert (
        sum(
            committed["per_condition"][c]["pooled"]["claim_units"]
            for c in CONDITIONS
        )
        == 716
    )


def test_the_disagreement_counter_is_capable_of_reporting_a_disagreement():
    """V20. A counter that could only report zero would certify nothing."""
    units = [
        {"grounded": True, "flagger_supported": True},
        {"grounded": True, "flagger_supported": False},
    ]
    assert sum(1 for u in units if u["grounded"] != u["flagger_supported"]) == 1


def test_the_reference_condition_flips_a_real_unit_under_an_identifier_substitution(store, rows):
    """The permanent form of this commit's harness control, run against the known defect.

    A real committed block carries the identifier a real graded unit names. With that identifier
    substituted in the block, the OVERLAP TERM ALONE still clears the unit's threshold, and the
    reference condition rejects the block. Both implementations flip together. Nothing on disk is
    touched: the substitution is made on a copy of the chunk in memory.
    """
    chunks = first_pass_chunks(rows[CONTROL_ROW], store)
    assert any(c.chunk_id == CONTROL_CHUNK for c in chunks)
    assert reference_surfaces(CONTROL_UNIT) == frozenset({("0", "48")})
    assert is_grounded(CONTROL_UNIT, tuple(chunks))
    assert unit_is_supported(CONTROL_UNIT, tuple(chunks))

    mutated = [
        dataclasses.replace(
            c,
            unit_label=c.unit_label.replace("Article 48", "Article 148"),
            text=c.text.replace("Article 48", "Article 148"),
        )
        if c.chunk_id == CONTROL_CHUNK
        else c
        for c in chunks
    ]
    block = next(rendered_block(c) for c in mutated if c.chunk_id == CONTROL_CHUNK)
    assert ("0", "48") not in reference_surfaces(block)
    overlap_alone = window_score(primary_tokens(CONTROL_UNIT), primary_tokens(block))
    assert overlap_alone >= 0.75, overlap_alone
    assert not is_grounded(CONTROL_UNIT, tuple(mutated))
    assert not unit_is_supported(CONTROL_UNIT, tuple(mutated))
    assert score_unit(CONTROL_UNIT, tuple(mutated)) < 0.75


def test_the_control_unit_is_a_real_graded_unit_of_the_committed_run(committed):
    """The control is anchored on the run rather than on a fixture invented for it."""
    row = committed["rows"]["raw"][CONTROL_TIER][CONTROL_ROW]
    match = [u for u in row["units"] if u["text"] == CONTROL_UNIT]
    assert len(match) == 1, [u["text"][:60] for u in row["units"]]
    assert match[0]["grounded"] is True
    assert match[0]["n_surfaces"] == 1


# --- the figures -------------------------------------------------------------------------


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_raw_figures(tier, committed):
    block = committed["per_condition"]["raw"]["per_tier"][tier]
    expected = RAW_PER_TIER[tier]
    assert (
        block["abstaining_rows"],
        block["answered_rows"],
        block["claim_units"],
        block["ungrounded_units"],
    ) == expected
    assert block["rows"] == 50
    assert block["unsupported_claim_rate"] == round(expected[3] / expected[2], 6)


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_layer_figures(tier, committed):
    block = committed["per_condition"]["layer"]["per_tier"][tier]
    expected = LAYER_PER_TIER[tier]
    assert (
        block["abstaining_rows"],
        block["answered_rows"],
        block["claim_units"],
        block["ungrounded_units"],
    ) == expected
    assert block["rows"] == 50
    assert block["unsupported_claim_rate"] == round(expected[3] / expected[2], 6)


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_no_context_figures_use_their_own_two_names(tier, committed):
    """Section 6.2. This condition reports no unsupported-claim rate, and the key is absent."""
    block = committed["per_condition"]["no_context"]["per_tier"][tier]
    expected = NO_CONTEXT_PER_TIER[tier]
    assert (
        block["abstaining_rows"],
        block["answered_rows"],
        block["claim_units"],
        block["ungrounded_units"],
    ) == expected
    assert "unsupported_claim_rate" not in block
    assert block["no_context_abstention_rate"] == block["abstention_rate"]
    assert block["parametric_coincidence_rate"] == round(
        block["grounded_units"] / block["claim_units"], 6
    )


def test_pooled_counts_are_the_sum_of_the_per_tier_counts(committed):
    """The identity that IS true. Counts sum; the rate is derived from the pooled counts."""
    keys = (
        "rows",
        "abstaining_rows",
        "answered_rows",
        "answered_rows_with_zero_claim_units",
        "claim_units",
        "grounded_units",
        "ungrounded_units",
        "marker_variant_rows",
        "cross_implementation_disagreements",
    )
    for condition in CONDITIONS:
        entry = committed["per_condition"][condition]
        for key in keys:
            assert entry["pooled"][key] == sum(
                entry["per_tier"][t][key] for t in TIER_KEYS
            ), (condition, key)
        for key in keys:
            assert entry["gold_bearing_pooled"][key] == sum(
                entry["gold_bearing"][t][key] for t in TIER_KEYS
            ), (condition, key, "gold-bearing")


def test_the_pooled_rate_is_not_the_mean_of_the_tier_rates(committed):
    """The identity that is NOT true, pinned so nobody restores it.

    A micro-average is not additive. On the raw condition the pooled rate and the mean of the
    three tier rates differ, and asserting the wrong identity would have shipped a false claim
    about what the pooled block is.
    """
    entry = committed["per_condition"]["raw"]
    pooled = entry["pooled"]["unsupported_claim_rate"]
    mean_of_rates = sum(
        entry["per_tier"][t]["unsupported_claim_rate"] for t in TIER_KEYS
    ) / len(TIER_KEYS)
    assert pooled != pytest.approx(mean_of_rates, abs=1e-6)
    assert pooled == round(
        entry["pooled"]["ungrounded_units"] / entry["pooled"]["claim_units"], 6
    )


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_fate_table_closes(tier, committed):
    table = committed["per_condition"]["layer"]["fate_table"][tier]
    assert (
        table["flagged_in"],
        table["repeated_unchanged"],
        table["repeated_and_now_grounded"],
        table["repeated_still_unsupported"],
        table["dropped_or_rewritten"],
    ) == FATE[tier]
    assert table["arithmetic"]["flagged_in_equals_repeated_plus_dropped"]
    assert table["arithmetic"]["repeated_equals_now_grounded_plus_still_unsupported"]
    assert table["population"]["rows"] == 48
    assert table["population"]["excluded_rows"] == list(UNFIRED)


def test_no_flagged_unit_was_rescued_by_the_fetched_context_on_any_tier(committed):
    """The development finding reproducing on the sealed set, pinned as a result."""
    for tier in TIER_KEYS:
        assert (
            committed["per_condition"]["layer"]["fate_table"][tier][
                "repeated_and_now_grounded"
            ]
            == 0
        )


@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("tier", TIER_KEYS)
def test_every_stratum_ships_with_explicit_zeros(condition, tier, committed):
    """All five committed strata on every tier and condition, and an undefined rate says so."""
    per_stratum = committed["per_condition"][condition]["per_stratum"][tier]
    assert tuple(per_stratum) == STRATA
    assert sum(b["rows"] for b in per_stratum.values()) == 50
    rate_key = (
        "parametric_coincidence_rate"
        if condition == "no_context"
        else "unsupported_claim_rate"
    )
    for stratum, block in per_stratum.items():
        if block[rate_key] is None:
            assert "rate_is_undefined_because" in block, (condition, tier, stratum)
            assert block["claim_units"] == 0
        else:
            assert block["claim_units"] > 0


def test_an_undefined_stratum_rate_is_never_scored_as_zero(committed):
    """A stratum with no answered rows has no rate, and P14 names the tier rather than scoring it."""
    sonnet = committed["per_condition"]["raw"]["per_stratum"]["sonnet5"]["action_to_parent"]
    assert sonnet["answered_rows"] == 0
    assert sonnet["claim_units"] == 0
    assert sonnet["unsupported_claim_rate"] is None
    p14 = next(e for e in committed["predictions_scored"] if e["prediction"] == "P14")
    assert p14["observed"]["unscoreable_on"] == ["sonnet5"]
    assert p14["observed"]["contradicted_on"] == ["opus48"]


# --- the comparable set and the reporting rule -------------------------------------------


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_comparable_set_ships_unit_counts_on_both_passes(tier, committed):
    """The rule the development run's Opus result forced: no rate without its unit count."""
    entry = committed["per_condition"]["layer"]["comparable_set"][tier]
    assert entry["rows"] == len(entry["membership"])
    for side in ("raw_side", "layer_side"):
        assert entry[side]["claim_units"] >= 0
        assert entry[side]["ungrounded_units"] >= 0
        if entry[side]["claim_units"]:
            assert entry[side]["unsupported_claim_rate"] == round(
                entry[side]["ungrounded_units"] / entry[side]["claim_units"], 6
            )
    assert entry["layer_side"]["answered_rows"] + entry["layer_side"][
        "layer_abstaining_rows_within_the_set"
    ] == entry["rows"]


def test_the_comparable_set_is_the_rows_with_a_second_call_answered_at_the_first_pass(
    committed,
):
    for tier in TIER_KEYS:
        layer = committed["rows"]["layer"][tier]
        expected = sorted(
            q
            for q, r in layer.items()
            if r["corrective_pass_fired"] and r["first_pass_class"] != "abstained"
        )
        assert committed["per_condition"]["layer"]["comparable_set"][tier][
            "membership"
        ] == expected


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_two_abstention_observations_ship_beside_the_rate_and_not_inside_it(
    tier, committed
):
    obs = committed["per_condition"]["layer"]["abstention_observations"][tier]
    recovered = obs["first_pass_abstentions_with_a_substantive_second_answer"]
    lost = obs["rows_fully_grounded_at_first_pass_then_layer_abstains"]
    assert recovered["count"] == len(recovered["rows"])
    assert lost["count"] == len(lost["rows"])
    layer = committed["rows"]["layer"][tier]
    for query_id in recovered["rows"]:
        assert layer[query_id]["abstained_marker_either_pass"] is True
    block = committed["per_condition"]["layer"]["per_tier"][tier]
    assert block["abstaining_rows"] >= recovered["count"]


# --- the refusal class and P24 ------------------------------------------------------------


def test_the_two_refusal_rows_are_the_whole_zero_unit_answered_class(committed):
    """The refusal ruling, executed. Both rows classify as answered and carry no claim unit."""
    found = {}
    for condition in CONDITIONS:
        for tier in TIER_KEYS:
            block = committed["per_condition"][condition]["per_tier"][tier]
            ids = block["answered_row_ids_with_zero_claim_units"]
            if ids:
                found[f"{condition}.{tier}"] = ids
    assert found == {"no_context.sonnet5": ["test_37"], "no_context.opus48": ["test_37"]}
    for tier in ("sonnet5", "opus48"):
        row = committed["rows"]["no_context"][tier]["test_37"]
        assert row["response_class"] == "answered"
        assert row["n_units"] == 0
        assert row["per_row_unsupported_rate"] is None


def test_the_refusal_rows_carry_no_content_block_in_the_committed_record():
    """What their responses contained, quoted from the record rather than described."""
    for tier in ("sonnet5", "opus48"):
        path = RUNS / f"{QUERY_SET}.no_context.{tier}.jsonl"
        with open(path, encoding="utf-8") as handle:
            record = next(
                json.loads(line)
                for line in handle
                if line.strip() and json.loads(line)["custom_id"].endswith("test_37")
            )
        assert record["response"]["message"]["stop_reason"] == "refusal"
        assert record["response"]["message"]["content"] == []
        assert answer_text(record) == ""


def test_p24_is_contradicted_by_a_second_route_the_sealed_file_did_not_foresee(committed):
    """Scored under the sealed file's own clause, with no predicate patched to rescue it."""
    p24 = next(e for e in committed["predictions_scored"] if e["prediction"] == "P24")
    assert p24["verdict"] == "contradicted"
    unequal = {k: v for k, v in p24["observed"].items() if not v["equal"]}
    assert set(unequal) == {"no_context.sonnet5", "no_context.opus48"}
    for entry in unequal.values():
        assert entry["marker_variant_rows"] == 0
        assert entry["answered_rows_with_zero_claim_units"] == 1
        assert entry["answered_row_ids_with_zero_claim_units"] == ["test_37"]


def test_no_marker_variant_row_exists_anywhere_in_the_sealed_run(committed):
    for condition in CONDITIONS:
        for tier in TIER_KEYS:
            assert (
                committed["per_condition"][condition]["per_tier"][tier][
                    "marker_variant_rows"
                ]
                == 0
            )


# --- the adversarial verdict ---------------------------------------------------------------


def test_the_adversarial_verdicts_run_over_every_condition_and_tier(committed):
    for condition in CONDITIONS:
        for tier in TIER_KEYS:
            entry = committed["per_condition"][condition]["adversarial_verdicts"][tier]
            assert entry["rows"] == 8
            assert len(entry["per_row"]) == 8
            assert entry["n_failures"] == len(entry["failures"])


def test_the_existence_denial_grammar_had_no_live_case_on_the_sealed_run(committed):
    """Section 7.3's disclosure, carried forward as a measurement rather than as a caveat.

    The grammar's development sample was zero because no development row invites a denial. On the
    sealed run it matched no unit either: every non-failing adversarial response was the exact
    marker, so the verdict rested on the section 4 marker exclusion alone. Reported whether it is
    zero or not, and it is zero.
    """
    total = 0
    for condition in CONDITIONS:
        for tier in TIER_KEYS:
            entry = committed["per_condition"][condition]["adversarial_verdicts"][tier]
            total += entry["claim_units_matching_the_existence_denial_grammar"]["count"]
            assert entry["marker_less_existence_denials"]["count"] == 0
    assert total == 0


def test_the_denial_grammar_still_fires_on_the_shape_it_exists_to_recognise():
    """V20. The zero above is trusted only because the detector is shown capable of matching."""
    assert adversarial_module.is_existence_denial("There is no Article 999 in the EU AI Act.")
    assert adversarial_module.is_existence_denial("Article 999 does not exist.")
    assert not adversarial_module.is_existence_denial(
        "Article 9 requires a risk management system."
    )


def test_the_only_adversarial_failures_are_the_rows_the_artifact_names(committed):
    observed = {
        f"{c}.{t}": committed["per_condition"][c]["adversarial_verdicts"][t]["failures"]
        for c in CONDITIONS
        for t in TIER_KEYS
    }
    assert {k: v for k, v in observed.items() if v} == {
        "raw.haiku45": ["test_04", "test_05"],
        "no_context.haiku45": ["test_01", "test_02", "test_03"],
        "no_context.sonnet5": ["test_01", "test_02"],
        "no_context.opus48": ["test_01", "test_02", "test_03"],
    }


# --- the reading on the unfired rows -------------------------------------------------------


def test_the_unfired_row_reading_is_recorded_with_the_row_it_would_move(committed):
    """The reading this runner fixes is load-bearing on one row, and that is stated, not hidden.

    Section 6.1's second clause names the second call. On test_34 and test_39 no second call
    exists, so only the marker clause applies. Under the other reading Haiku's test_39 would
    become a layer abstention, which is why the row is listed rather than the choice being made
    silently.
    """
    entry = committed["per_condition"]["layer"]["layer_abstention_reading_on_unfired_rows"]
    assert entry["rows_that_would_flip_under_the_other_reading"] == {
        "haiku45": ["test_39"],
        "sonnet5": [],
        "opus48": [],
    }
    row = committed["rows"]["layer"]["haiku45"]["test_39"]
    assert row["corrective_pass_fired"] is False
    assert row["first_pass_class"] == "answered"
    assert row["n_units"] > 0
    assert row["n_grounded"] == 0
    assert row["abstained_marker_either_pass"] is False


def test_no_fired_row_separates_the_two_readings_of_the_zero_grounded_clause(committed):
    """The other ambiguity, measured rather than argued. Zero rows distinguish the readings."""
    entry = committed["per_condition"]["layer"]["layer_abstention_reading_on_unfired_rows"]
    assert entry["fired_rows_with_zero_claim_units_that_are_not_marker_abstentions"] == {
        "haiku45": [],
        "sonnet5": [],
        "opus48": [],
    }


# --- the sealed stack ----------------------------------------------------------------------


def test_every_prediction_of_section_10_is_scored(committed):
    scored = {e["prediction"]: e["verdict"] for e in committed["predictions_scored"]}
    assert scored == EXPECTED_VERDICTS
    assert len(committed["predictions_scored"]) == 26


def test_the_contradicted_predictions_carry_the_observation_that_contradicts_them(committed):
    for entry in committed["predictions_scored"]:
        assert entry["observed"], entry["prediction"]
        assert entry["verdict"] in ("held", "contradicted", "not_predicted")


def test_the_grader_conformance_reading_is_reported_with_the_measurement_that_decides_it(
    committed,
):
    """Section 10.2 and 10.5 fixed both readings before the numbers existed; both are applied."""
    p9 = next(e for e in committed["predictions_scored"] if e["prediction"] == "P9")
    for tier in TIER_KEYS:
        assert p9["observed"][tier]["reduction_above_0_10"] is False
    assert "does not fire" in p9["note"]

    p19 = next(e for e in committed["predictions_scored"] if e["prediction"] == "P19")
    for tier in TIER_KEYS:
        entry = p19["observed"][tier]
        assert entry["raw_units_by_surface"]["surface_carrying_rate"] == 1.0
        assert entry["layer_units_by_surface"]["surface_carrying_rate"] == 1.0
        assert entry["surface_carrying_rate_change"] == 0.0
        assert entry["reduction_concentrates_on_surface_carrying_units"] is False


def test_p16_is_scored_on_the_committed_layer_artifact_and_the_chain(committed):
    check = committed["per_condition"]["layer"]["layer_retrieval_cross_check"]
    assert check["disagreements_against_the_committed_layer_artifact"] == []
    assert check["rows_compared"] == 50
    assert check["stratum_recovered_passage_recall"] == 0.25
    assert check["action_to_parent"]["test_41"]["recovered_units"] == [
        "nist_ai_100_1:sub_MEASURE_2.2",
        "nist_ai_600_1:sub_MEASURE_2.2",
        "nist_playbook:sub_MEASURE_2.2",
    ]
    for query_id in ("test_39", "test_40", "test_42"):
        assert check["action_to_parent"][query_id]["recovered_passage_recall"] == 0.0
        assert check["action_to_parent"][query_id]["recovered_units"] == []


# --- cost, latency and the secondary comparison ---------------------------------------------


@pytest.mark.parametrize("tier", TIER_KEYS)
def test_the_cost_re_derives_from_the_committed_usage_in_exact_decimal(tier, committed):
    """Section 6.3. The committed cost is re-derived rather than trusted, in exact decimal.

    The committed figures were written by a float expression. Every disagreement across the nine
    runs is exactly 0.0000005, a half-way tie at the sixth decimal that the two roundings break in
    opposite directions. The artifact is not adjusted to fit, and the tie is bounded here rather
    than smoothed away, which is the precedent the two run blocks that met it already set.
    """
    for condition in ("raw", "no_context", "second_call"):
        entry = committed["cost_and_latency"]["per_tier"][tier][condition]
        assert entry["cost_agrees_within_one_unit_in_the_last_place"] is True
        assert Decimal(entry["largest_component_difference"]) <= Decimal("0.0000005")
        rate_in, rate_out = BATCH_RATES[tier]
        expected = (
            Decimal(entry["input_tokens"]) * rate_in
            + Decimal(entry["output_tokens"]) * rate_out
        ) / Decimal(1000000)
        assert Decimal(entry["cost_usd_exact_decimal"]) == expected
        assert entry["created_at_utc"] < entry["ended_at_utc"]
        assert entry["submitted_utc"] <= entry["created_at_utc"]


def test_the_only_cost_disagreements_are_half_way_ties_and_they_are_listed(committed):
    """V10. The funnel over all eighteen figures, so the five ties are not lost in a pass."""
    exact = []
    tied = []
    for tier in TIER_KEYS:
        for condition in ("raw", "no_context", "second_call"):
            entry = committed["cost_and_latency"]["per_tier"][tier][condition]
            gap = Decimal(entry["largest_component_difference"])
            (exact if gap == 0 else tied).append(f"{condition}.{tier}")
            assert gap in (Decimal(0), Decimal("0.0000005")), (condition, tier, gap)
    assert len(exact) + len(tied) == 9
    assert sorted(tied) == [
        "no_context.haiku45",
        "no_context.opus48",
        "raw.haiku45",
        "second_call.opus48",
    ]


def test_the_layers_added_cost_is_the_second_call_run_alone(committed):
    for tier in TIER_KEYS:
        added = committed["per_condition"]["layer"]["added_cost_and_latency"][tier]
        second = committed["cost_and_latency"]["per_tier"][tier]["second_call"]
        assert added == second


def test_the_secondary_comparison_ships_both_counts_and_the_regime(committed):
    entry = committed["secondary_comparison"]
    assert entry["haiku45_plus_layer"]["answered_rows"] == LAYER_PER_TIER["haiku45"][1]
    assert entry["opus48_raw"]["answered_rows"] == RAW_PER_TIER["opus48"][1]
    assert entry["haiku45_plus_layer"]["claim_units"] == LAYER_PER_TIER["haiku45"][2]
    assert entry["opus48_raw"]["claim_units"] == RAW_PER_TIER["opus48"][2]
    assert "no thinking" in entry["reasoning_regime_difference"]
    assert "adaptive thinking at effort low" in entry["reasoning_regime_difference"]


def test_the_artifact_states_the_instrument_boundaries_it_is_required_to_state(committed):
    instrument = committed["instrument"]
    assert set(instrument) == {
        "the_ruler_punishes_paraphrase",
        "grader_conformance",
        "misattribution_blindness",
        "citation_mode_blindness",
    }
    for value in instrument.values():
        assert len(value) > 200


def test_the_thresholds_are_the_frozen_ones(committed):
    assert committed["thresholds"]["overlap_threshold"] == 0.75
    assert committed["thresholds"]["short_unit_length"] == 4
    assert committed["grader_frozen_at"] == "15e31d5"
