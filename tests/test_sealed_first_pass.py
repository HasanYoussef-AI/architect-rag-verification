"""The sealed first passes and no-context runs, pinned against the bodies that produced them.

WHAT THIS FILE EXISTS TO CHECK, AND WHY IT IS NOT A RESTATEMENT OF THE ARTIFACT. A committed
answer file is only evidence if a reviewer can tell which request produced each answer. The
batch record names one digest over the whole set, which says the fifty bodies together were
sent and says nothing about which row got which. Every result record therefore carries
`body_sha256`, and this file re-derives that digest for all fifty rows in every committed
condition from the committed assembler, the committed retrieval results and the committed chunk
store, with no key and no network. A row whose answer was matched to the wrong body fails here.

ONE FILE OVER EVERY TIER, NOT ONE FILE PER TIER. The provenance check is the same check on
every tier and duplicating it per tier would put two copies in the tree that can drift. What
differs between tiers is data, so it is a table: the decoding the manifest fixes, the token
figures, the thinking signature, the stop reasons. A tier is added by adding a row.

WHAT IS PINNED IS WHAT HAPPENED, INCLUDING WHAT WAS NOT PREDICTED. The Sonnet no-context run
carries one refused response and one input-token divergence, and both are asserted here rather
than tolerated by a loosened predicate. Reversing either requires deleting a failing test.

NOTHING HERE GRADES. No claim unit is segmented and no rate is computed. Rule 9 puts scoring in
a separate invocation over committed files, and the grading of record happens at its own commit.
What is asserted is each run's own integrity: shape, provenance, and the stop conditions the
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
from src.generate.prompts import ANSWERED, classify_response
from src.ingest.corpus_integrity import REPO_ROOT

RUNS = REPO_ROOT / "data" / "runs"
QUERY_SET = "test"
CONDITIONS = ("raw", "no_context")
TIERS_UNDER_TEST = ("haiku45", "sonnet5")
CASES = [(tier, condition) for tier in TIERS_UNDER_TEST for condition in CONDITIONS]
EXPECTED_ROWS = 50

# eval/generation_predictions.md section 11.1, the count_tokens figures of record per tier and
# condition. They were measured before each sealed run and are the gate each opened on.
COUNT_TOKENS_FIGURE = {
    ("haiku45", "raw"): 140787,
    ("haiku45", "no_context"): 4559,
    ("sonnet5", "raw"): 202612,
    ("sonnet5", "no_context"): 6468,
}

# usage.input_tokens as the API reported it. A different measurement from the one above, and on
# one run the two differ: see EXPECTED_DIVERGENCE.
EXPECTED_USAGE_INPUT = {
    ("haiku45", "raw"): 140787,
    ("haiku45", "no_context"): 4559,
    ("sonnet5", "raw"): 202612,
    ("sonnet5", "no_context"): 6515,
}

# Rows where usage.input_tokens exceeds the count_tokens measurement over the same body, with
# the excess. The token-counting documentation permits counts that include tokens added for
# system optimizations and are not billed, so the divergence is one-directional by design.
EXPECTED_DIVERGENCE = {
    ("haiku45", "raw"): {},
    ("haiku45", "no_context"): {},
    ("sonnet5", "raw"): {},
    ("sonnet5", "no_context"): {"test_37": 47},
}

# The decoding each tier runs under, from data/runs/run_manifest.json as committed at 50bd34a.
# None means the parameter is omitted from the request body.
EXPECTED_DECODING = {
    "haiku45": {"temperature": 0, "thinking": None, "effort": None},
    "sonnet5": {"temperature": None, "thinking": None, "effort": None},
}

# The output_tokens_details signature per run, as three counts rather than as a word. Haiku
# carries the key with a null value on every record; Sonnet carries a populated object on every
# record, and on five of its hundred rows the thinking figure is above zero.
EXPECTED_THINKING = {
    ("haiku45", "raw"): {"present": 50, "non_null": 0, "rows_above_zero": 0, "total": 0},
    ("haiku45", "no_context"): {"present": 50, "non_null": 0, "rows_above_zero": 0, "total": 0},
    ("sonnet5", "raw"): {"present": 50, "non_null": 50, "rows_above_zero": 1, "total": 122},
    ("sonnet5", "no_context"): {"present": 50, "non_null": 50, "rows_above_zero": 4, "total": 485},
}

EXPECTED_STOP_REASONS = {
    ("haiku45", "raw"): ["end_turn"],
    ("haiku45", "no_context"): ["end_turn"],
    ("sonnet5", "raw"): ["end_turn"],
    ("sonnet5", "no_context"): ["end_turn", "refusal"],
}

# Batch records written before the Sonnet run carry a smaller field set. The Haiku records
# landed at f9a4599, before that run surfaced a refusal and an input-token divergence and the
# runner grew fields for them. They are not rewritten: they are committed and no figure in them
# is affected. Every fact those fields carry is re-derived from the result records instead, for
# every tier, and the extended fields are asserted where they exist.
TIERS_WITH_EXTENDED_BATCH_FIELDS = ("sonnet5",)
EXTENDED_FIELDS = (
    "input_token_divergence",
    "rows_with_thinking_above_zero",
    "thinking_tokens_total",
    "rows_by_stop_reason",
)

# The one refused response in the committed runs, and what it contains.
REFUSAL = {
    "custom_id": "test__no_context__sonnet5__test_37",
    "category": "bio",
    "content_blocks": 0,
    "output_tokens": 0,
}


def _records(tier: str, condition: str) -> list[dict]:
    path = RUNS / f"{QUERY_SET}.{condition}.{tier}.jsonl"
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _batch_record(tier: str, condition: str) -> dict:
    path = RUNS / f"{QUERY_SET}.{condition}.{tier}.batch.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _bodies(tier: str, condition: str) -> dict[str, dict]:
    """Re-derive every request body from committed files. No key, no network."""
    store = load_chunk_store()
    rows = load_rows(QUERY_SET)
    config = TIERS[tier]
    if condition == "raw":
        requests = [build_raw(QUERY_SET, row, store) for row in rows]
    else:
        requests = [build_no_context(QUERY_SET, row) for row in rows]
    bodies = [build_body(request, config) for request in requests]
    return {body["custom_id"]: body for body in bodies}


def _answer_text(record: dict) -> str:
    blocks = record["response"]["message"]["content"]
    return "".join(b.get("text", "") for b in blocks if b["type"] == "text")


@pytest.mark.parametrize("tier,condition", CASES)
def test_fifty_records_keyed_and_sorted_by_custom_id(tier, condition):
    records = _records(tier, condition)
    assert len(records) == EXPECTED_ROWS
    ids = [r["custom_id"] for r in records]
    assert len(set(ids)) == EXPECTED_ROWS
    assert ids == sorted(ids), "records are not in custom_id order"
    assert all(i.startswith(f"{QUERY_SET}__{condition}__{tier}__") for i in ids)


@pytest.mark.parametrize("tier,condition", CASES)
def test_every_record_names_the_body_that_produced_it(tier, condition):
    """The provenance check. Re-derives all fifty digests from committed files."""
    records = _records(tier, condition)
    bodies = _bodies(tier, condition)
    assert len(bodies) == EXPECTED_ROWS
    checked = 0
    for record in records:
        expected = request_body_digest(bodies[record["custom_id"]])
        assert len(expected) == 64
        assert len(record["body_sha256"]) == 64
        assert record["body_sha256"] == expected, record["custom_id"]
        checked += 1
    assert checked == EXPECTED_ROWS, "the loop compared fewer rows than the file holds"


@pytest.mark.parametrize("tier,condition", CASES)
def test_the_provenance_check_is_capable_of_failing(tier, condition):
    """V20. A body whose parameters moved must not match the committed digest."""
    bodies = _bodies(tier, condition)
    key = sorted(bodies)[0]
    committed = {r["custom_id"]: r["body_sha256"] for r in _records(tier, condition)}
    mutated = json.loads(json.dumps(bodies[key]))
    mutated["params"]["max_tokens"] = MAX_TOKENS + 1
    assert request_body_digest(mutated) != committed[key]
    mutated_text = json.loads(json.dumps(bodies[key]))
    mutated_text["params"]["messages"][0]["content"] += " "
    assert request_body_digest(mutated_text) != committed[key]


@pytest.mark.parametrize("tier,condition", CASES)
def test_the_bodies_differ_by_tier_and_the_rendered_content_does_not(tier, condition):
    """The assembler's claim, checked rather than described.

    Rendered content does not depend on the model, so two tiers hash the same content and
    different bodies. A body digest that stopped varying by tier would mean the model string or
    the decoding stopped reaching the request.
    """
    other = [t for t in TIERS_UNDER_TEST if t != tier][0]
    mine = _batch_record(tier, condition)["request_body_digest"]
    theirs = _batch_record(other, condition)["request_body_digest"]
    assert mine["content"] == theirs["content"]
    assert mine["set"] != theirs["set"]


@pytest.mark.parametrize("tier,condition", CASES)
def test_no_answer_was_truncated(tier, condition):
    records = _records(tier, condition)
    assert max_tokens_stops(records) == []
    assert _batch_record(tier, condition)["max_tokens_stops"] == []
    reasons = sorted({r["response"]["message"]["stop_reason"] for r in records})
    assert reasons == EXPECTED_STOP_REASONS[(tier, condition)]
    assert _batch_record(tier, condition)["stop_reasons"] == reasons


@pytest.mark.parametrize("tier,condition", CASES)
def test_every_request_succeeded_on_the_requested_model(tier, condition):
    records = _records(tier, condition)
    assert {r["result_type"] for r in records} == {"succeeded"}
    assert {r["response"]["message"]["model"] for r in records} == {TIERS[tier].model}
    counts = _batch_record(tier, condition)["request_counts"]
    assert counts["succeeded"] == EXPECTED_ROWS
    for failure in ("errored", "expired", "canceled", "processing"):
        assert counts[failure] == 0, failure


@pytest.mark.parametrize("tier,condition", CASES)
def test_usage_totals_reconcile_with_the_records(tier, condition):
    """V21. The batch record's totals are re-derived from the file beside it, not trusted."""
    records = _records(tier, condition)
    derived_in = sum(r["response"]["message"]["usage"]["input_tokens"] for r in records)
    derived_out = sum(r["response"]["message"]["usage"]["output_tokens"] for r in records)
    batch = _batch_record(tier, condition)
    assert batch["usage_totals"]["input_tokens"] == derived_in
    assert batch["usage_totals"]["output_tokens"] == derived_out
    assert derived_in == EXPECTED_USAGE_INPUT[(tier, condition)]
    assert batch["count_tokens_total"]["measured"] == COUNT_TOKENS_FIGURE[(tier, condition)]
    assert batch["count_tokens_total"]["committed_figure"] == COUNT_TOKENS_FIGURE[(tier, condition)]


@pytest.mark.parametrize("tier,condition", CASES)
def test_input_token_divergence_reconciles_from_the_records(tier, condition):
    """Where usage exceeds count_tokens, the excess reconciles against the committed figure.

    Re-derived from the result records on every tier, so a run whose batch record predates the
    per-row divergence field is checked to the same standard as one that carries it.
    """
    records = _records(tier, condition)
    derived_in = sum(r["response"]["message"]["usage"]["input_tokens"] for r in records)
    expected = EXPECTED_DIVERGENCE[(tier, condition)]
    assert derived_in - COUNT_TOKENS_FIGURE[(tier, condition)] == sum(expected.values())
    batch = _batch_record(tier, condition)
    assert batch["count_tokens_total"]["measured"] == COUNT_TOKENS_FIGURE[(tier, condition)]


@pytest.mark.parametrize("tier,condition", CASES)
def test_the_extended_batch_fields_are_present_exactly_where_expected(tier, condition):
    """The presence gate is asserted, so a later check cannot skip silently on a missing key."""
    batch = _batch_record(tier, condition)
    carried = tier in TIERS_WITH_EXTENDED_BATCH_FIELDS
    for field in EXTENDED_FIELDS:
        assert (field in batch) is carried, (tier, condition, field)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_the_per_row_divergence_is_named_with_its_excess_where_the_record_carries_it(condition):
    """An aggregate difference with no row list cannot be told apart from a systematic offset.

    The two have different causes, so the run that diverged names the row and the excess.
    """
    tier = "sonnet5"
    recorded = _batch_record(tier, condition)["input_token_divergence"]
    expected = EXPECTED_DIVERGENCE[(tier, condition)]
    assert set(recorded["rows"]) == set(expected)
    for row, excess in expected.items():
        entry = recorded["rows"][row]
        assert entry["difference"] == excess
        assert entry["usage_input_tokens"] - entry["count_tokens"] == excess
    assert recorded["total"] == sum(expected.values())


@pytest.mark.parametrize("tier,condition", CASES)
def test_the_decoding_block_is_the_committed_manifest_setting(tier, condition):
    config = TIERS[tier]
    expected = EXPECTED_DECODING[tier]
    decoding = _batch_record(tier, condition)["decoding"]
    assert decoding["temperature"] == config.temperature == expected["temperature"]
    assert decoding["thinking"] == config.thinking == expected["thinking"]
    assert decoding["effort"] == config.effort == expected["effort"]
    assert decoding["max_tokens"] == MAX_TOKENS == 16000
    assert _batch_record(tier, condition)["model_requested"] == config.model


@pytest.mark.parametrize("tier,condition", CASES)
def test_the_thinking_detail_field_is_recorded_as_measured(tier, condition):
    """Counted rather than described, because the two tiers differ in the field's shape.

    A committed development note beside these runs calls this field absent on the Haiku tier.
    It is not absent there; it is present and null. Counts leave no room for that reading.
    """
    records = _records(tier, condition)
    expected = EXPECTED_THINKING[(tier, condition)]
    usages = [r["response"]["message"]["usage"] for r in records]
    present = [u for u in usages if "output_tokens_details" in u]
    non_null = [u for u in present if u["output_tokens_details"] is not None]
    above_zero = [u for u in non_null if u["output_tokens_details"].get("thinking_tokens")]
    assert len(present) == expected["present"]
    assert len(non_null) == expected["non_null"]
    assert len(above_zero) == expected["rows_above_zero"]
    total = sum(u["output_tokens_details"]["thinking_tokens"] for u in non_null)
    assert total == expected["total"]

    batch = _batch_record(tier, condition)
    assert batch["output_tokens_details"]["records_carrying_the_key"] == len(present)
    assert batch["output_tokens_details"]["records_whose_value_is_not_null"] == len(non_null)
    assert batch["output_tokens_details"]["of"] == EXPECTED_ROWS
    if tier in TIERS_WITH_EXTENDED_BATCH_FIELDS:
        assert len(batch["rows_with_thinking_above_zero"]) == expected["rows_above_zero"]
        assert batch["thinking_tokens_total"] == expected["total"]


def test_the_one_refused_response_is_recorded_whole_and_is_not_an_abstention():
    """The Sonnet no-context refusal, pinned with the consequence it carries.

    The model returned no content on this row. `classify_response` compares a whole response
    against the marker, so an empty response classifies as answered, which is a substantive
    misclassification of a row that produced no answer at all. It is pinned here rather than
    repaired: the predicate is committed, the grading of record happens at its own commit, and
    a silent fix would change a sealed predicate on the strength of one row. What this test
    guarantees is that the row cannot be lost and the misclassification cannot be inherited
    unnoticed.
    """
    records = {r["custom_id"]: r for r in _records("sonnet5", "no_context")}
    record = records[REFUSAL["custom_id"]]
    message = record["response"]["message"]
    assert record["result_type"] == "succeeded"
    assert message["stop_reason"] == "refusal"
    assert message["stop_details"]["type"] == "refusal"
    assert message["stop_details"]["category"] == REFUSAL["category"]
    assert len(message["content"]) == REFUSAL["content_blocks"]
    assert message["usage"]["output_tokens"] == REFUSAL["output_tokens"]
    assert _answer_text(record) == ""
    assert classify_response(_answer_text(record)) == ANSWERED

    others = [r for cid, r in records.items() if cid != REFUSAL["custom_id"]]
    assert len(others) == EXPECTED_ROWS - 1
    assert all(r["response"]["message"]["stop_reason"] == "end_turn" for r in others)
    assert _batch_record("sonnet5", "no_context")["rows_by_stop_reason"]["refusal"] == ["test_37"]


def test_the_same_row_was_answered_on_every_other_committed_run():
    """The refusal is a property of that row without context, not of the row.

    Its raw-condition counterpart on the same tier and its no-context counterpart on the other
    tier both returned an end_turn answer, so the refusal cannot be attributed to the query
    alone. Recorded because the honest reading of one refusal depends on what the same question
    did elsewhere.
    """
    row = "test_37"
    for tier, condition in CASES:
        if (tier, condition) == ("sonnet5", "no_context"):
            continue
        record = next(r for r in _records(tier, condition) if r["custom_id"].endswith(f"__{row}"))
        assert record["response"]["message"]["stop_reason"] == "end_turn", (tier, condition)
        assert _answer_text(record) != "", (tier, condition)
