"""The sealed Haiku first pass and no-context run, pinned against the bodies that produced it.

WHAT THIS FILE EXISTS TO CHECK, AND WHY IT IS NOT A RESTATEMENT OF THE ARTIFACT. A committed
answer file is only evidence if a reviewer can tell which request produced each answer. The
batch record names one digest over the whole set, which says the hundred bodies together were
sent and says nothing about which row got which. Every result record therefore carries
`body_sha256`, and this file re-derives that digest for all fifty rows in both conditions from
the committed assembler, the committed retrieval results and the committed chunk store, with no
key and no network. A row whose answer was matched to the wrong body fails here.

NOTHING HERE GRADES. No claim unit is segmented and no rate is computed. Rule 9 puts scoring in
a separate invocation over committed files, and the grading of record happens at its own commit.
What is asserted is the run's own integrity: shape, provenance, and the two stop conditions the
generation predictions declared before any call.
"""

from __future__ import annotations

import json

import pytest

from src.generate.assemble import (
    build_body,
    build_no_context,
    build_raw,
    load_chunk_store,
    load_rows,
    request_body_digest,
)
from src.generate.batch import max_tokens_stops
from src.generate.manifest import MAX_TOKENS, TIERS
from src.ingest.corpus_integrity import REPO_ROOT

RUNS = REPO_ROOT / "data" / "runs"
TIER = "haiku45"
QUERY_SET = "test"
CONDITIONS = ("raw", "no_context")
EXPECTED_ROWS = 50

# eval/generation_predictions.md section 11.1, the count_tokens figures of record for this
# tier and set. They were measured before the sealed run and are the gate it opened on.
COMMITTED_INPUT_TOKENS = {"raw": 140787, "no_context": 4559}


def _records(condition: str) -> list[dict]:
    path = RUNS / f"{QUERY_SET}.{condition}.{TIER}.jsonl"
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _batch_record(condition: str) -> dict:
    path = RUNS / f"{QUERY_SET}.{condition}.{TIER}.batch.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _bodies(condition: str) -> dict[str, dict]:
    """Re-derive every request body from committed files. No key, no network."""
    store = load_chunk_store()
    rows = load_rows(QUERY_SET)
    tier = TIERS[TIER]
    if condition == "raw":
        requests = [build_raw(QUERY_SET, row, store) for row in rows]
    else:
        requests = [build_no_context(QUERY_SET, row) for row in rows]
    bodies = [build_body(request, tier) for request in requests]
    return {body["custom_id"]: body for body in bodies}


@pytest.mark.parametrize("condition", CONDITIONS)
def test_fifty_records_keyed_and_sorted_by_custom_id(condition):
    records = _records(condition)
    assert len(records) == EXPECTED_ROWS
    ids = [r["custom_id"] for r in records]
    assert len(set(ids)) == EXPECTED_ROWS
    assert ids == sorted(ids), "records are not in custom_id order"
    assert all(i.startswith(f"{QUERY_SET}__{condition}__{TIER}__") for i in ids)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_every_record_names_the_body_that_produced_it(condition):
    """The provenance check. Re-derives all fifty digests from committed files."""
    records = _records(condition)
    bodies = _bodies(condition)
    assert len(bodies) == EXPECTED_ROWS
    checked = 0
    for record in records:
        expected = request_body_digest(bodies[record["custom_id"]])
        assert len(expected) == 64
        assert len(record["body_sha256"]) == 64
        assert record["body_sha256"] == expected, record["custom_id"]
        checked += 1
    assert checked == EXPECTED_ROWS, "the loop compared fewer rows than the file holds"


@pytest.mark.parametrize("condition", CONDITIONS)
def test_the_provenance_check_is_capable_of_failing(condition):
    """V20. A body whose parameters moved must not match the committed digest."""
    bodies = _bodies(condition)
    key = sorted(bodies)[0]
    committed = {r["custom_id"]: r["body_sha256"] for r in _records(condition)}
    mutated = json.loads(json.dumps(bodies[key]))
    mutated["params"]["max_tokens"] = MAX_TOKENS + 1
    assert request_body_digest(mutated) != committed[key]
    mutated_text = json.loads(json.dumps(bodies[key]))
    mutated_text["params"]["messages"][0]["content"] += " "
    assert request_body_digest(mutated_text) != committed[key]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_no_answer_was_truncated(condition):
    records = _records(condition)
    assert max_tokens_stops(records) == []
    reasons = {r["response"]["message"]["stop_reason"] for r in records}
    assert reasons == {"end_turn"}
    assert _batch_record(condition)["max_tokens_stops"] == []


@pytest.mark.parametrize("condition", CONDITIONS)
def test_every_request_succeeded_on_the_requested_model(condition):
    records = _records(condition)
    assert {r["result_type"] for r in records} == {"succeeded"}
    assert {r["response"]["message"]["model"] for r in records} == {TIERS[TIER].model}
    counts = _batch_record(condition)["request_counts"]
    assert counts["succeeded"] == EXPECTED_ROWS
    for failure in ("errored", "expired", "canceled", "processing"):
        assert counts[failure] == 0, failure


@pytest.mark.parametrize("condition", CONDITIONS)
def test_usage_totals_reconcile_with_the_records_and_the_committed_figure(condition):
    """V21. The batch record's totals are re-derived from the file beside it, not trusted."""
    records = _records(condition)
    derived_in = sum(r["response"]["message"]["usage"]["input_tokens"] for r in records)
    derived_out = sum(r["response"]["message"]["usage"]["output_tokens"] for r in records)
    batch = _batch_record(condition)
    assert batch["usage_totals"]["input_tokens"] == derived_in
    assert batch["usage_totals"]["output_tokens"] == derived_out
    assert derived_in == COMMITTED_INPUT_TOKENS[condition]
    assert batch["count_tokens_total"]["measured"] == COMMITTED_INPUT_TOKENS[condition]
    assert batch["count_tokens_total"]["committed_figure"] == COMMITTED_INPUT_TOKENS[condition]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_the_decoding_block_is_the_committed_manifest_setting(condition):
    tier = TIERS[TIER]
    decoding = _batch_record(condition)["decoding"]
    assert decoding["temperature"] == tier.temperature == 0
    assert decoding["thinking"] == tier.thinking is None
    assert decoding["effort"] == tier.effort is None
    assert decoding["max_tokens"] == MAX_TOKENS == 16000
    assert _batch_record(condition)["model_requested"] == tier.model


@pytest.mark.parametrize("condition", CONDITIONS)
def test_the_thinking_detail_field_is_recorded_as_measured(condition):
    """Present on every record and null on every record, counted rather than described.

    The development record for this tier carries the same signature, and a committed note
    beside it calls the field absent. It is not absent; it is present and null. The count
    ships so the reading is not a matter of recollection.
    """
    records = _records(condition)
    present = [r for r in records if "output_tokens_details" in r["response"]["message"]["usage"]]
    non_null = [
        r for r in present if r["response"]["message"]["usage"]["output_tokens_details"] is not None
    ]
    assert len(present) == EXPECTED_ROWS
    assert non_null == []
    block = _batch_record(condition)["output_tokens_details"]
    assert block["records_carrying_the_key"] == len(present)
    assert block["records_whose_value_is_not_null"] == len(non_null)
    assert block["of"] == EXPECTED_ROWS
