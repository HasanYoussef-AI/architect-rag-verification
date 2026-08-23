"""The sealed second calls, and the flagged lists the bodies were built from.

THE CENTRAL CHECK IS THAT THE FLAGGED ARTIFACT RE-DERIVES. A second-call body carries three
things a reviewer cannot see in the answer file: the augmented context, the first answer, and
the flagged claim units. The first two are already reproducible from committed files. The third
is the flagged artifact, so this file rebuilds it with src.complete.run_second_call_flagged.build
and asserts the committed JSON equals the rebuild, at level 1 with no key and no network. If the
artifact and the code that made it ever part company, that fails here.

THE POPULATION IS CHECKED TWO WAYS. Once from the corrective module directly, and once against
the committed layer artifact's own per-row fetch counts. Those are independent records of the
same fact, and the test compares them rather than trusting either.

NOTHING HERE GRADES. No claim unit is scored and no rate is computed. Rule 9 puts scoring in a
separate invocation, and the grading of record is its own commit.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from src.complete.augment import augment, load_fetch_store
from src.complete.run_second_call_flagged import build, output_path
from src.generate.assemble import (
    build_body,
    build_second_call,
    first_pass_chunks,
    load_chunk_store,
    load_rows,
    request_body_digest,
)
from src.generate.batch import max_tokens_stops
from src.generate.manifest import MAX_TOKENS, TIERS
from src.ingest.corpus_integrity import REPO_ROOT

RUNS = REPO_ROOT / "data" / "runs"
QUERY_SET = "test"
CONDITION = "second_call"
TIERS_UNDER_TEST = ("haiku45",)

SEALED_ROWS = 50
NOT_FIRED = ["test_34", "test_39"]
FIRING_ROWS = SEALED_ROWS - len(NOT_FIRED)

# eval/generation_predictions.md section 11.2: the measured empty-slot context figure and the
# two-ceiling bound of record, per tier over the 48 firing rows.
EMPTY_SLOT_FIGURE = {"haiku45": 389427}
BOUND_OF_RECORD = {"haiku45": 1925427}

# Measured before submission and reported by the API afterwards. Equal on this run.
COUNT_TOKENS_TOTAL = {"haiku45": 395720}
USAGE_INPUT_TOTAL = {"haiku45": 395720}

EXPECTED_STOP_REASONS = {"haiku45": ["end_turn"]}
EXPECTED_THINKING = {"haiku45": {"present": 48, "non_null": 0, "rows_above_zero": 0, "total": 0}}
TRUE_RATES = {"haiku45": (0.50, 2.50)}


def _records(tier: str) -> list[dict]:
    path = RUNS / f"{QUERY_SET}.{CONDITION}.{tier}.jsonl"
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _batch_record(tier: str) -> dict:
    path = RUNS / f"{QUERY_SET}.{CONDITION}.{tier}.batch.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _committed_flagged(tier: str) -> dict:
    with open(output_path(tier), encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_flagged_artifact_re_derives_from_committed_files(tier):
    """Level 1. The committed JSON equals what its producer builds now, with no key."""
    committed = _committed_flagged(tier)
    rebuilt = build(tier)
    assert committed == rebuilt


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_flagged_artifact_re_derivation_is_capable_of_failing(tier):
    """V20. A rebuild with one flagged unit removed must not compare equal."""
    committed = _committed_flagged(tier)
    mutated = json.loads(json.dumps(committed))
    key = next(k for k, v in mutated["rows"].items() if v["n_flagged"] > 0)
    mutated["rows"][key]["flagged_units"] = mutated["rows"][key]["flagged_units"][:-1]
    mutated["rows"][key]["n_flagged"] -= 1
    assert mutated != build(tier)


def test_the_firing_set_is_the_corrective_pass_and_agrees_with_the_layer_artifact():
    """Two independent records of one fact, compared rather than either trusted."""
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = load_rows(QUERY_SET)
    assert len(rows) == SEALED_ROWS

    by_module = {}
    for row in rows:
        result = augment(row["query"], first_pass_chunks(row, store), fetch)
        by_module[row["id"]] = result

    fired = sorted(i for i, r in by_module.items() if r.triggered)
    silent = sorted(i for i, r in by_module.items() if not r.triggered)
    assert silent == NOT_FIRED
    assert len(fired) == FIRING_ROWS

    with open(REPO_ROOT / "eval" / "test_layer_results.json", encoding="utf-8") as handle:
        layer = {e["id"]: e for e in json.load(handle)["layer"]}
    assert len(layer) == SEALED_ROWS
    for query_id, result in by_module.items():
        entry = layer[query_id]
        assert len(result.fetched_chunks) == entry["fetched_chunk_count"], query_id
        assert result.size == entry["context_set_size"], query_id
        assert list(result.fetched_units) == list(entry["fetched_units"]), query_id
    by_artifact = sorted(i for i, e in layer.items() if e["fetched_chunk_count"] > 0)
    assert by_artifact == fired


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_run_covers_the_firing_set_exactly(tier):
    records = _records(tier)
    assert len(records) == FIRING_ROWS
    ids = [r["custom_id"] for r in records]
    assert len(set(ids)) == FIRING_ROWS
    assert ids == sorted(ids), "records are not in custom_id order"
    rows = {r["custom_id"].rsplit("__", 1)[1] for r in records}
    assert set(NOT_FIRED).isdisjoint(rows), "a non-firing row received a second call"
    assert rows == set(_committed_flagged(tier)["rows"][k]["query_id"]
                       for k in _committed_flagged(tier)["rows"])


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_every_record_names_the_body_that_produced_it(tier):
    """Rebuilds all 48 bodies from committed files and re-derives their digests."""
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = {r["id"]: r for r in load_rows(QUERY_SET)}
    flagged = _committed_flagged(tier)["rows"]
    answers = {}
    with open(RUNS / f"{QUERY_SET}.raw.{tier}.jsonl", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            answers[record["custom_id"].split("__")[-1]] = "".join(
                b.get("text", "") for b in record["response"]["message"]["content"]
                if b.get("type") == "text")

    config = TIERS[tier]
    expected = {}
    for key in sorted(flagged):
        entry = flagged[key]
        request = build_second_call(
            QUERY_SET, rows[entry["query_id"]], store, fetch,
            answers[entry["query_id"]], tuple(entry["flagged_units"]))
        expected[key] = request_body_digest(build_body(request, config))

    checked = 0
    for record in _records(tier):
        assert record["body_sha256"] == expected[record["custom_id"]], record["custom_id"]
        assert len(record["body_sha256"]) == 64
        checked += 1
    assert checked == FIRING_ROWS


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_provenance_check_is_capable_of_failing(tier):
    """V20. A body built with the flagged list dropped must not match."""
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = {r["id"]: r for r in load_rows(QUERY_SET)}
    flagged = _committed_flagged(tier)["rows"]
    key = next(k for k, v in flagged.items() if v["n_flagged"] > 0)
    entry = flagged[key]
    answers = {}
    with open(RUNS / f"{QUERY_SET}.raw.{tier}.jsonl", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            answers[record["custom_id"].split("__")[-1]] = "".join(
                b.get("text", "") for b in record["response"]["message"]["content"]
                if b.get("type") == "text")
    committed = {r["custom_id"]: r["body_sha256"] for r in _records(tier)}
    without = build_second_call(
        QUERY_SET, rows[entry["query_id"]], store, fetch, answers[entry["query_id"]], ())
    assert request_body_digest(build_body(without, TIERS[tier])) != committed[key]


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_no_answer_was_truncated(tier):
    records = _records(tier)
    assert max_tokens_stops(records) == []
    assert _batch_record(tier)["max_tokens_stops"] == []
    reasons = sorted({r["response"]["message"]["stop_reason"] for r in records})
    assert reasons == EXPECTED_STOP_REASONS[tier]
    assert _batch_record(tier)["stop_reasons"] == reasons


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_every_request_succeeded_on_the_requested_model(tier):
    records = _records(tier)
    assert {r["result_type"] for r in records} == {"succeeded"}
    assert {r["response"]["message"]["model"] for r in records} == {TIERS[tier].model}
    counts = _batch_record(tier)["request_counts"]
    assert counts["succeeded"] == FIRING_ROWS
    for failure in ("errored", "expired", "canceled", "processing"):
        assert counts[failure] == 0, failure


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_usage_reconciles_and_the_input_sits_below_the_bound(tier):
    records = _records(tier)
    derived_in = sum(r["response"]["message"]["usage"]["input_tokens"] for r in records)
    derived_out = sum(r["response"]["message"]["usage"]["output_tokens"] for r in records)
    batch = _batch_record(tier)
    assert batch["usage_totals"]["input_tokens"] == derived_in == USAGE_INPUT_TOTAL[tier]
    assert batch["usage_totals"]["output_tokens"] == derived_out
    counted = batch["count_tokens_total"]
    assert counted["measured"] == COUNT_TOKENS_TOTAL[tier]
    assert counted["bound_of_record"] == BOUND_OF_RECORD[tier]
    assert counted["measured"] <= counted["bound_of_record"]
    assert counted["at_or_below_bound"] is True
    assert counted["measured_empty_slot_figure"] == EMPTY_SLOT_FIGURE[tier]
    assert counted["fill_delta"] == counted["measured"] - EMPTY_SLOT_FIGURE[tier]
    assert counted["fill_delta"] > 0, "the slots were filled, so the total must exceed the empty figure"
    assert derived_in - counted["measured"] == batch["input_token_divergence"]["total"]


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_decoding_block_is_the_committed_manifest_setting(tier):
    config = TIERS[tier]
    decoding = _batch_record(tier)["decoding"]
    assert decoding["temperature"] == config.temperature
    assert decoding["thinking"] == config.thinking
    assert decoding["effort"] == config.effort
    assert decoding["max_tokens"] == MAX_TOKENS == 16000
    assert _batch_record(tier)["model_requested"] == config.model


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_thinking_detail_field_is_recorded_as_measured(tier):
    records = _records(tier)
    expected = EXPECTED_THINKING[tier]
    usages = [r["response"]["message"]["usage"] for r in records]
    present = [u for u in usages if "output_tokens_details" in u]
    non_null = [u for u in present if u["output_tokens_details"] is not None]
    assert len(present) == expected["present"]
    assert len(non_null) == expected["non_null"]
    batch = _batch_record(tier)
    assert batch["output_tokens_details"]["records_carrying_the_key"] == len(present)
    assert batch["output_tokens_details"]["records_whose_value_is_not_null"] == len(non_null)
    assert len(batch["rows_with_thinking_above_zero"]) == expected["rows_above_zero"]
    assert batch["thinking_tokens_total"] == expected["total"]


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_the_recorded_cost_re_derives_from_the_tiers_true_rates(tier):
    rate_in, rate_out = TRUE_RATES[tier]
    batch = _batch_record(tier)
    usage, cost = batch["usage_totals"], batch["cost_usd"]
    for name, tokens, rate in (("input", usage["input_tokens"], rate_in),
                               ("output", usage["output_tokens"], rate_out)):
        exact = Decimal(tokens) * Decimal(str(rate)) / Decimal(1_000_000)
        assert abs(Decimal(str(cost[name])) - exact) <= Decimal("0.0000005"), name
    assert f"${rate_in:.2f} / MTok" in cost["rates"]
    assert f"${rate_out:.2f} / MTok" in cost["rates"]


@pytest.mark.parametrize("tier", TIERS_UNDER_TEST)
def test_an_abstained_first_pass_still_received_a_second_call_with_an_empty_flagged_list(tier):
    """The development precedent, asserted on the sealed set.

    dev_11 and dev_12 abstained on this tier and both carry a second call whose flagged list is
    empty. The same shape holds here, and it is the case where augmentation can rescue a miss,
    so a change that stopped issuing these calls would remove the measurement rather than a cost.
    """
    flagged = _committed_flagged(tier)["rows"]
    abstained = {k: v for k, v in flagged.items() if v["first_pass_class"] == "abstained"}
    assert abstained, "no first-pass abstention on this tier; the assertion would be vacuous"
    for key, entry in abstained.items():
        assert entry["flagged_units"] == [], key
        assert entry["n_flagged"] == 0, key
    issued = {r["custom_id"] for r in _records(tier)}
    assert set(abstained).issubset(issued)
