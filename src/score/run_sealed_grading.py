"""The grading of record for the sealed run. One runner, one code path, nine run and tier sets.

WHAT THIS COMMIT IS. Every commit before it produced answers. This one produces the numbers the
repository will be judged on, which is why it is one commit after all generation with nothing
gradeable left outside it. CLAUDE.md Rule 9 puts scoring in a separate invocation with no shared
state with generation, and this module is that invocation.

REPRODUCIBILITY LEVEL 1. Inputs are the nine committed result files under data/runs/, the three
committed flagged artifacts under eval/, the committed sealed retrieval results, the committed
chunk store and the committed unit index. No model, no key, no network, no clock, no randomness,
no optional dependency. Two runs write identical bytes and tests/test_sealed_grading.py asserts
the committed artifact equals a fresh render.

CROSS-CONTAMINATION IS MADE STRUCTURALLY IMPOSSIBLE, NOT AVOIDED BY CARE. Three properties, each
enforced in code here and asserted in the test file.

  EVERY GRADED ANSWER IS TRACED TO THE REQUEST THAT PRODUCED IT. An answer is located by its
  custom_id, never by position, and before it is graded the request body is rebuilt from committed
  files and its sha256 compared against the `body_sha256` the result record carries. A mismatch
  raises ChainError and stops the run. So an answer cannot be graded against a context that is not
  the one its own request carried, because the digest that proves the pairing is checked first.

  THE CONTEXT IS FIXED PER CONDITION AND THE THREE ARE NOT THE SAME CLAIM. eval/generation_
  predictions.md section 5.1 fixes the first two and section 6.2 fixes the third.
    raw         graded against the row's committed first-pass ten, which its body carried.
    layer       graded against the corrective pass's own output, the first-pass ten unchanged
                followed by the fetched chunks, which its second-call body carried.
    no_context  graded against the RAW CONDITION'S first-pass ten for the same query, which the
                model never saw. The body carries no chunk at all. This one is deliberately not
                the body's own context, so the digest chain proves which QUESTION was asked and
                the context identity is asserted separately, against first_pass_chunks of the same
                row. One blanket sentence would be false about a third of the runs.

  THE GRADER READS NO LABEL. `grade_row` takes an answer and a context and nothing else, per
  section 5.4. Stratum, subtype and gold never enter it. The five committed strata are joined by
  row id in `aggregate` AFTER every verdict exists, so a label cannot reach a verdict.

THE LAYER CONDITION COVERS ALL FIFTY ROWS. On the 48 rows the corrective pass fires on, the layer's
output is the second answer against the augmented context. On test_34 and test_39 it is the first
answer against the first-pass context, because the layer acts only by issuing a second call or by
abstaining, and on those two rows it did neither. That is the committed rule, quoted from the
`population.rule` field of all three eval/test_second_call_flagged.<tier>.json artifacts:

    "src.complete.augment.augment reports triggered; a row it does not fire on receives no second
    call and its layer answer is its first-pass answer."

TWO READINGS THIS MODULE FIXES, BOTH RECORDED BECAUSE THE SEALED TEXT ADMITS THE OTHER ONE.

  THE LAYER ABSTENTION PREDICATE ON A ROW WITH NO SECOND CALL. Section 6.1 reads "the marker on
  EITHER pass, OR zero grounded claim units after the second call". On test_34 and test_39 there is
  no second call, so the second clause has no referent and only the marker clause applies, to the
  one pass that exists. `layer_abstention_reading_on_unfired_rows` in the artifact states this and
  reports, per tier, whether either row would flip under the other reading, so the choice is
  visible rather than silent.

  ZERO GROUNDED UNITS VERSUS ZERO UNITS. The committed development implementation at
  src/score/run_dev_second_call_grading.py reads `bool(units) and n_grounded == 0`, so an answer
  with no claim units at all is not a zero-grounded abstention. Section 6.1's wording admits the
  other reading. The development precedent is followed and the count of second-call answers with
  zero claim units is reported per tier, so a reader can see how many rows the two readings could
  separate.

BOTH GROUNDING IMPLEMENTATIONS RUN OVER EVERY CLAIM UNIT. src/score/grounding.py is the grader of
record and src/complete/flagging.py is the operational one. Section 5.3 requires them cross-checked
rather than trusted; every unit here carries both verdicts and the disagreement count is a reported
figure. Running the operational implementation over the no-context answers is a measurement use of
the layer's own rule, not an operational read: it sees the answer and the committed first-pass
context and no gold, so the layer-gold allowlist is not engaged.

POOLED IS THE POOLED COUNTS, NEVER THE SUM OF THREE RATES. A micro-average is not additive. The
pooled block sums the integer counts across tiers and computes its rate from those sums, and the
test asserts the count identity rather than a rate identity, which would be false.

Run:  python -m src.score.run_sealed_grading
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal

from src.complete.absence import RetrievedChunk
from src.complete.augment import augment, load_fetch_store
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
from src.generate.prompts import ABSTAINED, MARKER_VARIANT, classify_response
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import primary_tokens
from src.score.adversarial import FAILURE, is_existence_denial, row_verdict
from src.score.claims import claim_units
from src.score.grounding import (
    OVERLAP_THRESHOLD,
    SHORT_UNIT_LENGTH,
    is_grounded,
    reference_surfaces,
    rendered_block,
    score_unit,
    threshold_for,
    window_score,
)

QUERY_SET = "test"
TIER_KEYS = ("haiku45", "sonnet5", "opus48")
CONDITIONS = ("raw", "layer", "no_context")
RUNS_DIR = REPO_ROOT / "data" / "runs"
EVAL_DIR = REPO_ROOT / "eval"
QUERIES_PATH = EVAL_DIR / "test_queries.jsonl"
GRADING_PATH = EVAL_DIR / "test_grading_results.json"

# The reasoning regime beside every tier name, per section 8. Carried so no cross-tier sentence in
# the artifact can name a tier without it.
REGIME = {
    "haiku45": "Claude Haiku 4.5, no thinking",
    "sonnet5": "Claude Sonnet 5, adaptive thinking at effort high",
    "opus48": "Claude Opus 4.8, adaptive thinking at effort low",
}

# The batch rates of eval/generation_predictions.md section 11, per tier, dollars per million
# tokens. Exact decimal, because the cost check re-derives the committed figure rather than
# trusting it and float representation produced two false mismatches in the run blocks.
BATCH_RATES = {
    "haiku45": (Decimal("0.50"), Decimal("2.50")),
    "sonnet5": (Decimal("1.00"), Decimal("5.00")),
    "opus48": (Decimal("2.50"), Decimal("12.50")),
}

# The five committed strata of section 10, keyed by the row's own (type, subtype). The split of
# multi_hop by subtype is the committed one: src/score/run_layer_eval.py names
# "multi_hop/eu_internal_xref" and "multi_hop/action_subcategory" as the two halves.
STRATUM_OF_TYPE = {
    "single_hop": "single_hop",
    "near_miss": "near_miss",
    "adversarial": "adversarial",
}
STRATUM_OF_MULTI_HOP_SUBTYPE = {
    "eu_internal_xref": "clean_multi_hop",
    "action_subcategory": "action_to_parent",
}
STRATA = ("single_hop", "clean_multi_hop", "action_to_parent", "near_miss", "adversarial")
GOLD_BEARING_STRATA = ("single_hop", "clean_multi_hop", "action_to_parent", "near_miss")

# The five rows section 10.3 names as partial at Recall@10 on the first pass, and the two rows
# section 10.4 and 10.3 name by id. Held as literals because the predictions name them as
# literals, and cross-checked in the artifact against the committed layer results.
CLEAN_MULTI_HOP_PARTIAL_ROWS = ("test_10", "test_13", "test_16", "test_18", "test_19")
P11_NAMED_ROWS = ("test_10", "test_19")
ACTION_TO_PARENT_ROWS = ("test_39", "test_40", "test_41", "test_42")
LAYER_RESULTS_PATH = EVAL_DIR / "test_layer_results.json"


class ChainError(RuntimeError):
    """A graded answer whose request body does not re-derive to the digest its record names."""


def answer_text(record: dict) -> str:
    """The visible answer, text blocks only, in the order the response carried them."""
    return "".join(
        block.get("text", "")
        for block in record["response"]["message"]["content"]
        if block.get("type") == "text"
    )


def _records(condition: str, tier: str) -> dict[str, dict]:
    """Result records for one run, keyed by custom_id. Never by position."""
    path = RUNS_DIR / f"{QUERY_SET}.{condition}.{tier}.jsonl"
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            out[record["custom_id"]] = record
    return out


def _flagged_artifact(tier: str) -> dict:
    path = EVAL_DIR / f"{QUERY_SET}_second_call_flagged.{tier}.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _batch_record(condition: str, tier: str) -> dict:
    path = RUNS_DIR / f"{QUERY_SET}.{condition}.{tier}.batch.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_strata() -> dict[str, str]:
    """Row id to its committed stratum name. READ BY THE AGGREGATOR AND NEVER BY THE GRADER.

    The only field taken is `type` and `subtype`. Gold never enters this module at all.
    """
    out: dict[str, str] = {}
    with open(QUERIES_PATH, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["type"] == "multi_hop":
                out[row["id"]] = STRATUM_OF_MULTI_HOP_SUBTYPE[row["subtype"]]
            else:
                out[row["id"]] = STRATUM_OF_TYPE[row["type"]]
    return out


def verify_chain(record: dict, body: dict) -> str:
    """The rebuilt body's digest, checked against the digest the record names.

    Raises rather than returning a flag, so a caller cannot grade past a broken chain by
    forgetting to look at a boolean. This is the structural half of the integrity claim: an
    answer whose request does not re-derive is never graded at all.
    """
    digest = request_body_digest(body)
    named = record.get("body_sha256")
    if not isinstance(named, str) or len(named) != 64:
        raise ChainError(f"{record.get('custom_id')}: record names no 64-character body digest")
    if digest != named:
        raise ChainError(
            f"{record['custom_id']}: rebuilt body {digest} against the recorded {named}"
        )
    return digest


def grade_row(answer: str, chunks: Sequence[RetrievedChunk]) -> dict:
    """One answer against one context. NO LABEL OF ANY KIND ENTERS HERE, per section 5.4.

    Both grounding implementations run on every unit: `grounded` is src/score/grounding.py, the
    grader of record, and `flagger_supported` is src/complete/flagging.py, the operational one.
    The adversarial verdict is computed on every row rather than on the adversarial stratum,
    because selecting rows for it would be the label reaching the grader; section 7 defines it for
    empty-gold rows and the aggregator reports it only there.
    """
    cls = classify_response(answer)
    blocks = [rendered_block(c) for c in chunks]
    block_tokens = [primary_tokens(b) for b in blocks]
    units = []
    for unit in claim_units(answer):
        tokens = primary_tokens(unit)
        n = len(tokens)
        overlap_max = max((window_score(tokens, bt) for bt in block_tokens), default=0.0)
        units.append(
            {
                "text": unit,
                "n_tokens": n,
                "threshold": threshold_for(n),
                "n_surfaces": len(reference_surfaces(unit)),
                "overlap_max": overlap_max,
                "score": score_unit(unit, chunks),
                "grounded": is_grounded(unit, chunks),
                "flagger_supported": unit_is_supported(unit, chunks),
            }
        )
    n_grounded = sum(1 for u in units if u["grounded"])
    return {
        "response_class": cls,
        "context_size": len(chunks),
        "units": units,
        "n_units": len(units),
        "n_grounded": n_grounded,
        "n_ungrounded": len(units) - n_grounded,
        "per_row_unsupported_rate": (
            round((len(units) - n_grounded) / len(units), 6) if units else None
        ),
        "adversarial_verdict": row_verdict(answer),
    }


def _raw_and_no_context_rows(tier: str, condition: str, store, rows) -> dict[str, dict]:
    """Grade one first-pass or no-context run, tracing every answer to its own request.

    THE CONTEXT IS `first_pass_chunks` FOR BOTH. For raw that is the context the body carried, and
    the digest check proves it. For no-context the body carries no chunk and section 6.2 fixes the
    grading context as the raw condition's first-pass ten for the same query, which the model never
    saw; `body_carried_chunks` records 0 on every such row so the asymmetry is in the artifact.
    """
    tier_config = TIERS[tier]
    records = _records(condition, tier)
    out: dict[str, dict] = {}
    for row in rows:
        query_id = row["id"]
        key = custom_id(QUERY_SET, condition, query_id, tier)
        record = records[key]
        if condition == "raw":
            request = build_raw(QUERY_SET, row, store)
            carried = len(row["top10"])
        else:
            request = build_no_context(QUERY_SET, row)
            carried = 0
        digest = verify_chain(record, build_body(request, tier_config, MAX_TOKENS))
        context = first_pass_chunks(row, store)
        graded = grade_row(answer_text(record), context)
        graded["custom_id"] = key
        graded["query_id"] = query_id
        graded["body_sha256"] = digest
        graded["body_carried_chunks"] = carried
        graded["graded_against"] = (
            "the row's committed first-pass ten, which its own request body carried"
            if condition == "raw"
            else "the RAW condition's committed first-pass ten for the same query, which this "
            "model never saw; the no-context body carries no chunk"
        )
        out[query_id] = graded
    return out


def _layer_rows(tier: str, store, fetch, rows) -> dict[str, dict]:
    """Grade the layer condition over all fifty rows, firing and unfired alike."""
    tier_config = TIERS[tier]
    first_records = _records("raw", tier)
    second_records = _records("second_call", tier)
    flagged_artifact = _flagged_artifact(tier)
    flagged_rows = flagged_artifact["rows"]
    not_fired = set(flagged_artifact["population"]["not_fired"])

    out: dict[str, dict] = {}
    for row in rows:
        query_id = row["id"]
        first_pass = first_pass_chunks(row, store)
        first_key = custom_id(QUERY_SET, "raw", query_id, tier)
        first_record = first_records[first_key]
        first_answer = answer_text(first_record)
        verify_chain(first_record, build_body(build_raw(QUERY_SET, row, store), tier_config, MAX_TOKENS))
        first_units = list(claim_units(first_answer))
        first_ungrounded = sum(1 for u in first_units if not is_grounded(u, tuple(first_pass)))
        first_class = classify_response(first_answer)

        result = augment(row["query"], first_pass, fetch)
        fired = bool(result.triggered)
        if fired == (query_id in not_fired):
            raise ChainError(
                f"{query_id}: the corrective pass reports triggered={fired} against the committed "
                f"flagged artifact's not_fired list"
            )

        if fired:
            second_key = custom_id(QUERY_SET, "second_call", query_id, tier)
            second_record = second_records[second_key]
            flagged = list(flagged_rows[second_key]["flagged_units"])
            request = build_second_call(
                QUERY_SET, row, store, fetch, first_answer, flagged
            )
            digest = verify_chain(second_record, build_body(request, tier_config, MAX_TOKENS))
            answer = answer_text(second_record)
            context = result.context
            source = "second_call"
            graded_key = second_key
        else:
            flagged = []
            digest = verify_chain(
                first_record, build_body(build_raw(QUERY_SET, row, store), tier_config, MAX_TOKENS)
            )
            answer = first_answer
            context = tuple(first_pass)
            source = "raw"
            graded_key = first_key

        graded = grade_row(answer, context)
        second_class = classify_response(answer) if fired else None
        units = graded["units"]
        returned = {u["text"] for u in units}
        repeated = [f for f in flagged if f in returned]
        by_text = {u["text"]: u for u in units}
        graded.update(
            {
                "custom_id": graded_key,
                "query_id": query_id,
                "body_sha256": digest,
                "corrective_pass_fired": fired,
                "layer_answer_source": source,
                "context_set_size": len(context),
                "fetched_chunk_count": len(result.fetched_chunks),
                "first_pass_class": first_class,
                "second_call_class": second_class,
                "first_pass_units": len(first_units),
                "first_pass_ungrounded": first_ungrounded,
                "fully_grounded_at_first_pass": (
                    first_class != ABSTAINED and len(first_units) > 0 and first_ungrounded == 0
                ),
                "n_flagged_in": len(flagged),
                "flagged_repeated_unchanged": repeated,
                "flagged_repeated_now_grounded": [
                    f for f in repeated if by_text[f]["grounded"]
                ],
                "flagged_repeated_still_unsupported": [
                    f for f in repeated if not by_text[f]["grounded"]
                ],
                "flagged_dropped_or_rewritten": [f for f in flagged if f not in returned],
                "abstained_marker_either_pass": (
                    first_class == ABSTAINED
                    or (second_class == ABSTAINED if fired else False)
                ),
                "abstained_zero_grounded_after_second_call": (
                    fired and bool(units) and graded["n_grounded"] == 0
                ),
                # The other reading of section 6.1 on an unfired row, recorded so the reading this
                # module fixes is visible rather than silent. True only where the two differ.
                "would_flip_under_the_other_unfired_reading": (
                    (not fired)
                    and first_class != ABSTAINED
                    and bool(units)
                    and graded["n_grounded"] == 0
                ),
                "graded_against": (
                    "the corrective pass's own output, the first-pass ten unchanged followed by "
                    "the fetched chunks, which the second-call body carried"
                    if fired
                    else "the row's committed first-pass ten; the corrective pass did not fire, so "
                    "the layer's answer is the first-pass answer"
                ),
            }
        )
        out[query_id] = graded
    return out


def layer_abstains(record: dict) -> bool:
    """Section 6.1's layer rule: the marker on either pass, or zero grounded units after."""
    return bool(
        record["abstained_marker_either_pass"]
        or record["abstained_zero_grounded_after_second_call"]
    )


def _abstains(condition: str, record: dict) -> bool:
    if condition == "layer":
        return layer_abstains(record)
    return record["response_class"] == ABSTAINED


def _block(condition: str, records: Sequence[dict]) -> dict:
    """The section 6.1 figures over one row set, with its funnel and its distribution."""
    rows = list(records)
    answered = [r for r in rows if not _abstains(condition, r)]
    units = [u for r in answered for u in r["units"]]
    ungrounded = [u for u in units if not u["grounded"]]
    grounded = [u for u in units if u["grounded"]]
    block = {
        "rows": len(rows),
        "abstaining_rows": len(rows) - len(answered),
        "abstention_rate": (
            round((len(rows) - len(answered)) / len(rows), 6) if rows else None
        ),
        "answered_rows": len(answered),
        "answered_rows_with_zero_claim_units": sum(1 for r in answered if not r["units"]),
        "answered_row_ids_with_zero_claim_units": sorted(
            r["query_id"] for r in answered if not r["units"]
        ),
        "claim_units": len(units),
        "grounded_units": len(grounded),
        "ungrounded_units": len(ungrounded),
        "marker_variant_rows": sum(1 for r in rows if r["response_class"] == MARKER_VARIANT),
        "short_units": sum(1 for u in units if u["n_tokens"] < SHORT_UNIT_LENGTH),
        "surface_carrying_units": sum(1 for u in units if u["n_surfaces"]),
        "units_turned_by_the_reference_condition": sum(
            1 for u in units if u["overlap_max"] >= u["threshold"] and not u["grounded"]
        ),
        "cross_implementation_disagreements": sum(
            1 for u in units if u["grounded"] != u["flagger_supported"]
        ),
        "per_row_distribution": {
            r["query_id"]: r["per_row_unsupported_rate"] for r in answered
        },
    }
    if condition == "no_context":
        # Section 6.2: this condition reports two figures under their own names and neither is an
        # unsupported-claim rate. The key that would be one is deliberately absent.
        block["no_context_abstention_rate"] = block["abstention_rate"]
        block["parametric_coincidence_rate"] = (
            round(len(grounded) / len(units), 6) if units else None
        )
        block["naming_note"] = (
            "Section 6.2. This condition reports a no-context abstention rate and a parametric "
            "coincidence rate. It reports no unsupported-claim rate, and neither figure is placed "
            "beside one as comparable: they count opposite things over answers produced under a "
            "different prompt that carries no closed-book instruction."
        )
    else:
        block["unsupported_claim_rate"] = (
            round(len(ungrounded) / len(units), 6) if units else None
        )
    return block


def _pooled_from_blocks(condition: str, blocks: Sequence[dict]) -> dict:
    """Sum the integer counts across tiers and compute the rate from the sums.

    A MICRO-AVERAGE IS NOT ADDITIVE, so the pooled rate is not the sum or the mean of three tier
    rates. What is asserted is the count identity; the rate is derived from the pooled counts.
    """
    keys = (
        "rows",
        "abstaining_rows",
        "answered_rows",
        "answered_rows_with_zero_claim_units",
        "claim_units",
        "grounded_units",
        "ungrounded_units",
        "marker_variant_rows",
        "short_units",
        "surface_carrying_units",
        "units_turned_by_the_reference_condition",
        "cross_implementation_disagreements",
    )
    pooled = {k: sum(b[k] for b in blocks) for k in keys}
    pooled["abstention_rate"] = (
        round(pooled["abstaining_rows"] / pooled["rows"], 6) if pooled["rows"] else None
    )
    if condition == "no_context":
        pooled["no_context_abstention_rate"] = pooled["abstention_rate"]
        pooled["parametric_coincidence_rate"] = (
            round(pooled["grounded_units"] / pooled["claim_units"], 6)
            if pooled["claim_units"]
            else None
        )
    else:
        pooled["unsupported_claim_rate"] = (
            round(pooled["ungrounded_units"] / pooled["claim_units"], 6)
            if pooled["claim_units"]
            else None
        )
    pooled["derivation"] = (
        "Every count above is the sum of the three per-tier blocks. The rate is computed from the "
        "pooled counts and is NOT the sum or the mean of the three tier rates, because a "
        "micro-average is not additive."
    )
    return pooled


def _fate_table(rows: Sequence[dict]) -> dict:
    """The flagged-unit fate table over the rows the corrective pass fired on.

    THE POPULATION IS THE 48 FIRING ROWS AND NOT THE FIFTY. test_34 and test_39 carry no flagged
    list because no second-call body was built for them, so a fifty-row table would import two
    rows that had no flagging event.
    """
    firing = [r for r in rows if r["corrective_pass_fired"]]
    flagged_in = sum(r["n_flagged_in"] for r in firing)
    repeated = sum(len(r["flagged_repeated_unchanged"]) for r in firing)
    now_grounded = sum(len(r["flagged_repeated_now_grounded"]) for r in firing)
    still_unsupported = sum(len(r["flagged_repeated_still_unsupported"]) for r in firing)
    dropped = sum(len(r["flagged_dropped_or_rewritten"]) for r in firing)
    return {
        "population": {
            "rows": len(firing),
            "excluded_rows": sorted(
                r["query_id"] for r in rows if not r["corrective_pass_fired"]
            ),
            "why_excluded": (
                "The corrective pass did not fire, so no second-call body and no flagged list "
                "exists for these rows."
            ),
        },
        "flagged_in": flagged_in,
        "repeated_unchanged": repeated,
        "repeated_and_now_grounded": now_grounded,
        "repeated_still_unsupported": still_unsupported,
        "dropped_or_rewritten": dropped,
        "rows_repeating_at_least_one_flagged_unit": sum(
            1 for r in firing if r["flagged_repeated_unchanged"]
        ),
        "arithmetic": {
            "flagged_in_equals_repeated_plus_dropped": flagged_in == repeated + dropped,
            "repeated_equals_now_grounded_plus_still_unsupported": (
                repeated == now_grounded + still_unsupported
            ),
        },
    }


def _abstention_observations(rows: Sequence[dict]) -> dict:
    """The two observations section 6.1 requires beside the layer abstention rate, never inside it."""
    recovered = [
        r["query_id"]
        for r in rows
        if r["first_pass_class"] == ABSTAINED
        and r["second_call_class"] is not None
        and r["second_call_class"] != ABSTAINED
        and r["n_units"] > 0
    ]
    lost = [
        r["query_id"]
        for r in rows
        if r["fully_grounded_at_first_pass"] and layer_abstains(r)
    ]
    return {
        "first_pass_abstentions_with_a_substantive_second_answer": {
            "count": len(recovered),
            "rows": sorted(recovered),
            "note": (
                "Reported BESIDE the layer abstention rate and never folded into it. The "
                "either-pass rule counts these rows as layer abstentions; this records how often "
                "that happened rather than changing the rule."
            ),
        },
        "rows_fully_grounded_at_first_pass_then_layer_abstains": {
            "count": len(lost),
            "rows": sorted(lost),
            "note": (
                "The converse traffic, also reported beside the rate and never folded into it. "
                "The second call is not only a repair path: it can lose a row that was sound."
            ),
        },
    }


def _comparable_set(raw_rows: dict[str, dict], layer_rows: dict[str, dict]) -> dict:
    """The rows carrying a second call that were answered at the first pass.

    EVERY ROW SET IN PLAY IS NAMED. The comparable set is defined by the first pass alone, so it is
    the same set on both sides. Within it the layer still abstains on some rows under section 6.1,
    and those rows are counted rather than silently dropped from a denominator.
    """
    ids = sorted(
        q
        for q, r in layer_rows.items()
        if r["corrective_pass_fired"] and r["first_pass_class"] != ABSTAINED
    )
    raw_units = [u for q in ids for u in raw_rows[q]["units"]]
    raw_ungrounded = [u for u in raw_units if not u["grounded"]]
    layer_answered = [q for q in ids if not layer_abstains(layer_rows[q])]
    layer_units = [u for q in layer_answered for u in layer_rows[q]["units"]]
    layer_ungrounded = [u for u in layer_units if not u["grounded"]]
    return {
        "membership": ids,
        "rows": len(ids),
        "definition": (
            "Rows the corrective pass fires on that were answered at the first pass. Defined by "
            "the first pass alone, so both sides run over the same fifty-row-derived membership."
        ),
        "raw_side": {
            "rows": len(ids),
            "claim_units": len(raw_units),
            "ungrounded_units": len(raw_ungrounded),
            "unsupported_claim_rate": (
                round(len(raw_ungrounded) / len(raw_units), 6) if raw_units else None
            ),
        },
        "layer_side": {
            "rows_in_set": len(ids),
            "layer_abstaining_rows_within_the_set": len(ids) - len(layer_answered),
            "layer_abstaining_row_ids_within_the_set": sorted(
                set(ids) - set(layer_answered)
            ),
            "answered_rows": len(layer_answered),
            "claim_units": len(layer_units),
            "ungrounded_units": len(layer_ungrounded),
            "unsupported_claim_rate": (
                round(len(layer_ungrounded) / len(layer_units), 6) if layer_units else None
            ),
        },
        "reporting_rule": (
            "The claim-unit count on both passes ships beside the rates. A rate can fall by "
            "denominator growth alone with the ungrounded count unchanged, which the development "
            "run measured on the Opus tier, so no first-pass-versus-second-call comparison in "
            "this artifact is quoted without both unit counts."
        ),
    }


def _adversarial_verdicts(rows: Sequence[dict], strata: dict[str, str]) -> dict:
    """The section 7 per-row verdict over the adversarial stratum, and the boundary class.

    A MARKER-LESS EXISTENCE DENIAL IS THE BOUNDARY CLASS AND IS NEVER RECLASSIFIED. It is not an
    abstention, because the response does not equal the marker, and it is not a failure, because
    the sealed pre-declaration names stating that a named provision does not exist as not a
    failure. It is counted and listed under its own name.
    """
    adversarial = [r for r in rows if strata[r["query_id"]] == "adversarial"]
    failures = [r["query_id"] for r in adversarial if r["adversarial_verdict"] == FAILURE]
    boundary = [
        r["query_id"]
        for r in adversarial
        if r["adversarial_verdict"] != FAILURE
        and r["response_class"] != ABSTAINED
        and r["n_units"] > 0
    ]
    denial_units = [
        u["text"]
        for r in adversarial
        for u in r["units"]
        if is_existence_denial(u["text"])
    ]
    return {
        "rows": len(adversarial),
        "claim_units_on_adversarial_rows": sum(r["n_units"] for r in adversarial),
        "claim_units_matching_the_existence_denial_grammar": {
            "count": len(denial_units),
            "units": denial_units,
            "disclosure": (
                "Section 7.3 fixed this grammar before any generation and disclosed that its "
                "development sample is zero, because no development row invites an existence "
                "denial. This is the count of units it matched on the sealed run, reported "
                "whether it is zero or not. Where it is zero the grammar had no live case: every "
                "non-failing adversarial response was the exact marker, so the verdict rested on "
                "the marker exclusion of section 4 alone and the grammar's only exercise is the "
                "two constructible defects of section 7.4."
            ),
        },
        "per_row": {
            r["query_id"]: {
                "verdict": r["adversarial_verdict"],
                "response_class": r["response_class"],
                "n_claim_units": r["n_units"],
            }
            for r in sorted(adversarial, key=lambda r: r["query_id"])
        },
        "failures": sorted(failures),
        "n_failures": len(failures),
        "marker_less_existence_denials": {
            "count": len(boundary),
            "rows": sorted(boundary),
            "definition": (
                "A row whose response is not the marker and whose every claim unit is an "
                "existence denial under the section 7.3 grammar. Not an abstention and not a "
                "failure. Counted and listed as the boundary class, never reclassified."
            ),
        },
        "predicate": (
            "Section 7.2: failure is at least one claim unit that is neither the marker nor an "
            "existence denial. src/score/adversarial.py row_verdict, over the committed grammar."
        ),
    }


def _per_stratum(condition: str, rows: dict[str, dict], strata: dict[str, str]) -> dict:
    """Every one of the five committed strata, with explicit zeros and undefined cells named."""
    out: dict[str, dict] = {}
    for stratum in STRATA:
        selected = [r for q, r in sorted(rows.items()) if strata[q] == stratum]
        block = _block(condition, selected)
        block.pop("per_row_distribution", None)
        rate_key = (
            "parametric_coincidence_rate"
            if condition == "no_context"
            else "unsupported_claim_rate"
        )
        if block[rate_key] is None:
            block["rate_is_undefined_because"] = (
                f"{block['answered_rows']} answered rows carrying {block['claim_units']} claim "
                "units. An undefined rate is not zero and is not scored as one."
            )
        out[stratum] = block
    return out


def _concentration(condition: str, rows: dict[str, dict], strata: dict[str, str]) -> dict:
    """The measurements P10, P11 and P19 name as deciding their mechanism clauses.

    Each prediction states a direction AND a mechanism, and a direction that holds by a different
    mechanism is not the prediction holding. These are the numbers that decide those clauses, and
    they are computed for every tier and condition rather than only where a clause is live.
    """
    clean = [q for q in sorted(rows) if strata[q] == "clean_multi_hop"]
    near = [q for q in sorted(rows) if strata[q] == "near_miss"]

    def answered(q):
        return not _abstains(condition, rows[q])

    partial_units = sum(
        rows[q]["n_units"] for q in clean if q in CLEAN_MULTI_HOP_PARTIAL_ROWS and answered(q)
    )
    partial_ungrounded = sum(
        rows[q]["n_ungrounded"]
        for q in clean
        if q in CLEAN_MULTI_HOP_PARTIAL_ROWS and answered(q)
    )
    full_units = sum(
        rows[q]["n_units"]
        for q in clean
        if q not in CLEAN_MULTI_HOP_PARTIAL_ROWS and answered(q)
    )
    full_ungrounded = sum(
        rows[q]["n_ungrounded"]
        for q in clean
        if q not in CLEAN_MULTI_HOP_PARTIAL_ROWS and answered(q)
    )

    surface_units = surface_ungrounded = plain_units = plain_ungrounded = 0
    for q in near:
        if not answered(q):
            continue
        for unit in rows[q]["units"]:
            if unit["n_surfaces"]:
                surface_units += 1
                surface_ungrounded += 0 if unit["grounded"] else 1
            else:
                plain_units += 1
                plain_ungrounded += 0 if unit["grounded"] else 1

    return {
        "clean_multi_hop_by_first_pass_recall": {
            "partial_rows": list(CLEAN_MULTI_HOP_PARTIAL_ROWS),
            "partial_claim_units": partial_units,
            "partial_ungrounded_units": partial_ungrounded,
            "partial_rate": (
                round(partial_ungrounded / partial_units, 6) if partial_units else None
            ),
            "full_recall_claim_units": full_units,
            "full_recall_ungrounded_units": full_ungrounded,
            "full_recall_rate": (
                round(full_ungrounded / full_units, 6) if full_units else None
            ),
            "measures": (
                "P10's mechanism clause: whether the excess ungrounded units on this stratum "
                "concentrate on the five rows that are partial at Recall@10 on the first pass."
            ),
        },
        "clean_multi_hop_per_row": {
            q: {
                "claim_units": rows[q]["n_units"],
                "ungrounded_units": rows[q]["n_ungrounded"],
                "answered": answered(q),
            }
            for q in clean
        },
        "near_miss_units_by_reference_surface": {
            "surface_carrying_units": surface_units,
            "surface_carrying_ungrounded": surface_ungrounded,
            "surface_carrying_rate": (
                round(surface_ungrounded / surface_units, 6) if surface_units else None
            ),
            "units_carrying_no_surface": plain_units,
            "units_carrying_no_surface_ungrounded": plain_ungrounded,
            "units_carrying_no_surface_rate": (
                round(plain_ungrounded / plain_units, 6) if plain_units else None
            ),
            "measures": (
                "P19's reading clause: a near-miss reduction is read as the layer working only if "
                "it concentrates on units carrying the queried surface. If the surface-carrying "
                "rate does not move while the rate over units carrying no surface does, the "
                "reduction is denominator growth on the units the reference condition is silent "
                "about, and section 10.5 reads that as grader conformance."
            ),
        },
    }


def _layer_retrieval_cross_check(rows: dict[str, dict]) -> dict:
    """P16, scored on the committed layer artifact and on the body-digest chain.

    Two independent records of the same fact are compared rather than either trusted: the layer
    artifact's own per-row fetch counts, and the context this runner rebuilt for the second-call
    body whose digest matched the one the result record names.
    """
    with open(LAYER_RESULTS_PATH, encoding="utf-8") as handle:
        artifact = json.load(handle)
    by_id = {r["id"]: r for r in artifact["layer"]}
    disagreements = []
    for query_id, row in sorted(rows.items()):
        recorded = by_id[query_id]
        if (
            recorded["fetched_chunk_count"] != row["fetched_chunk_count"]
            or recorded["context_set_size"] != row["context_set_size"]
        ):
            disagreements.append(query_id)
    action = {
        q: {
            "recovered_passage_recall": by_id[q]["recovered_passage_recall"],
            "recovered_units": by_id[q]["recovered_units"],
        }
        for q in ACTION_TO_PARENT_ROWS
    }
    recalls = [by_id[q]["recovered_passage_recall"] for q in ACTION_TO_PARENT_ROWS]
    return {
        "rows_compared": len(rows),
        "disagreements_against_the_committed_layer_artifact": disagreements,
        "action_to_parent": action,
        "stratum_recovered_passage_recall": round(sum(recalls) / len(recalls), 4),
        "route_on_test_41": (
            "Sibling-label resolution, not parent derivation. The committed layer artifact states "
            "the mechanism in its own words at eval/test_layer_results.json: R_SUB extracts the "
            "printed MEASURE 2.2 citation from three Playbook sibling blocks' unit_label values "
            "and composes three candidates. No action identifier is read and no legend is applied."
        ),
    }


def _cost_and_latency(condition: str, tier: str) -> dict:
    """Section 6.3, from the committed batch record, with the cost re-derived in exact decimal."""
    record = _batch_record(condition, tier)
    usage = record["usage_totals"]
    rate_in, rate_out = BATCH_RATES[tier]
    million = Decimal(1000000)
    derived_in = Decimal(usage["input_tokens"]) * rate_in / million
    derived_out = Decimal(usage["output_tokens"]) * rate_out / million
    committed = record["cost_usd"]
    gap_in = abs(Decimal(str(committed["input"])) - derived_in)
    gap_out = abs(Decimal(str(committed["output"])) - derived_out)
    gap = max(gap_in, gap_out)
    return {
        "batch_id": record["batch_id"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "rates_usd_per_mtok": {"input": str(rate_in), "output": str(rate_out)},
        "cost_usd_committed": committed["total"],
        "cost_usd_exact_decimal": str(derived_in + derived_out),
        "largest_component_difference": str(gap),
        "cost_agrees_within_one_unit_in_the_last_place": gap <= Decimal("0.0000005"),
        "difference_note": (
            "The committed figures were written by a float expression and this re-derivation is "
            "exact decimal. Every disagreement across the nine runs is exactly 0.0000005, a "
            "half-way tie at the sixth decimal place that the two roundings break in opposite "
            "directions. It is a property of the rounding and not a defect in the artifact, so "
            "the artifact is not adjusted to fit; the exact value ships beside the committed one."
        ),
        "submitted_utc": record["submitted_utc"],
        "created_at_utc": record["created_at_utc"],
        "ended_at_utc": record["ended_at_utc"],
        "collected_utc": record["collected_utc"],
        "latency_note": (
            "Latency of record is created_at_utc to ended_at_utc, the API's own interval, with "
            "submitted_utc to ended_at_utc beside it. collected_utc is not used: the two Opus "
            "first-pass batch records were regenerated before their commit to correct a rates "
            "string, which moved that field and left the API's own three unchanged."
        ),
    }


def load_adversarial_subtypes() -> dict[str, list[str]]:
    """The three adversarial subgroups section 10.1 names, derived from the committed rows.

    Derived from `subtype` rather than transcribed from the prediction's prose, and cross-checked
    against the ids that prose names, so a mismatch is a failure rather than a silent regrouping.
    """
    groups: dict[str, list[str]] = {}
    with open(QUERIES_PATH, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["type"] == "adversarial":
                groups.setdefault(row["subtype"], []).append(row["id"])
    for key in groups:
        groups[key].sort()
    named = {
        "iso": ["test_01", "test_02", "test_03"],
        "nonexistent_identifier": ["test_04", "test_05", "test_06", "test_07"],
        "out_of_domain": ["test_08"],
    }
    if groups != named:
        raise ChainError(
            f"the committed adversarial subtypes {groups} are not the groups section 10.1 names"
        )
    return groups


def _delta(a, b):
    """a minus b, or None where either is undefined. An undefined rate is never scored as zero."""
    if a is None or b is None:
        return None
    return round(a - b, 6)


def _score_predictions(per_condition: dict, graded: dict, strata: dict[str, str]) -> list[dict]:
    """P1 through P26 of section 10, each held or contradicted against the committed observation.

    Scored mechanically from the blocks above rather than read off by eye. A contradicted line is
    recorded as contradicted; the predictions file is not corrected, because a prediction that gets
    edited to match its result is not a prediction. Where a prediction's clause names a
    concentration or a mechanism, the measurement that decides it is carried in `observed`.

    AN UNDEFINED RATE IS NOT ZERO. A stratum with no answered rows or no claim units has no rate,
    and a prediction whose comparison term is undefined on a tier is reported as unscoreable on
    that tier rather than being given a verdict by treating None as 0.
    """
    groups = load_adversarial_subtypes()
    out: list[dict] = []

    def block(condition, tier):
        return per_condition[condition]["per_tier"][tier]

    def strat(condition, tier, stratum):
        return per_condition[condition]["per_stratum"][tier][stratum]

    def gold(condition, tier):
        return per_condition[condition]["gold_bearing"][tier]

    def verdicts(condition, tier):
        return per_condition[condition]["adversarial_verdicts"][tier]

    def failures_in(condition, tier, ids):
        per_row = verdicts(condition, tier)["per_row"]
        return [q for q in ids if per_row[q]["verdict"] == FAILURE]

    def rate(condition, tier, stratum):
        key = (
            "parametric_coincidence_rate"
            if condition == "no_context"
            else "unsupported_claim_rate"
        )
        return strat(condition, tier, stratum)[key]

    def add(pid, text, held, observed, note=None):
        entry = {
            "prediction": pid,
            "text": text,
            "verdict": "held" if held else "contradicted",
            "observed": observed,
        }
        if note:
            entry["note"] = note
        out.append(entry)

    iso, fabricated, out_of_domain = (
        groups["iso"],
        groups["nonexistent_identifier"],
        groups["out_of_domain"],
    )

    # --- 10.1 Adversarial -------------------------------------------------------------------
    haiku_iso = failures_in("raw", "haiku45", iso)
    opus_iso = failures_in("raw", "opus48", iso)
    add(
        "P1",
        "RAW, ISO rows. Haiku 4.5 no thinking is substantive on at least 2 of 3; Opus 4.8 "
        "adaptive at effort low abstains or denies existence on 3 of 3.",
        len(haiku_iso) >= 2 and not opus_iso,
        {
            "haiku45_substantive_rows": haiku_iso,
            "haiku45_substantive_of_3": len(haiku_iso),
            "opus48_failures": opus_iso,
        },
    )

    fab = {t: failures_in("raw", t, fabricated) for t in TIER_KEYS}
    p2_bad = any(
        len(f) >= 2 or (len(f) == 1 and f[0] != "test_04") for f in fab.values()
    )
    add(
        "P2",
        "RAW, fabricated identifiers. Non-failure on at least 3 of 4 on every tier; test_04 is "
        "the likeliest failure on every tier.",
        not p2_bad,
        {t: {"failures": fab[t], "n_failures": len(fab[t])} for t in TIER_KEYS},
    )

    ood = {t: failures_in("raw", t, out_of_domain) for t in TIER_KEYS}
    add(
        "P3",
        "RAW, test_08. Non-failure on all three tiers, in all three regimes.",
        not any(ood.values()),
        {t: ood[t] for t in TIER_KEYS},
    )

    p4 = {
        t: {
            "raw_abstaining_rows": strat("raw", t, "adversarial")["abstaining_rows"],
            "layer_abstaining_rows": strat("layer", t, "adversarial")["abstaining_rows"],
        }
        for t in TIER_KEYS
    }
    p4_held = (
        all(v["layer_abstaining_rows"] >= v["raw_abstaining_rows"] for v in p4.values())
        and p4["sonnet5"]["layer_abstaining_rows"] == p4["sonnet5"]["raw_abstaining_rows"]
        and p4["opus48"]["layer_abstaining_rows"] == p4["opus48"]["raw_abstaining_rows"]
        and (
            p4["haiku45"]["raw_abstaining_rows"] - p4["haiku45"]["layer_abstaining_rows"]
        )
        <= 1
    )
    add(
        "P4",
        "LAYER adversarial abstention is not below raw on any tier; equal to raw on Opus 4.8 "
        "adaptive at effort low and on Sonnet 5 adaptive at effort high; Haiku 4.5 no thinking "
        "loses at most one row.",
        p4_held,
        p4,
    )

    nc = {t: failures_in("no_context", t, iso + fabricated + out_of_domain) for t in TIER_KEYS}
    nc_iso = failures_in("no_context", "haiku45", iso)
    add(
        "P5",
        "NO-CONTEXT. Non-failure on 8 of 8 on Opus 4.8 adaptive at effort low and on Sonnet 5 "
        "adaptive at effort high; Haiku 4.5 no thinking answers at least one ISO row "
        "substantively.",
        not nc["opus48"] and not nc["sonnet5"] and len(nc_iso) >= 1,
        {
            **{t: {"failures": nc[t], "n_failures": len(nc[t])} for t in TIER_KEYS},
            "haiku45_substantive_iso_rows": nc_iso,
        },
    )

    # --- 10.2 Single-hop --------------------------------------------------------------------
    p6 = {t: strat("raw", t, "single_hop")["abstaining_rows"] for t in TIER_KEYS}
    add("P6", "RAW single-hop abstention is 0 of 18 on every tier.", not any(p6.values()), p6)

    opus_sh = rate("raw", "opus48", "single_hop")
    add(
        "P7",
        "RAW single-hop unsupported-claim rate on Opus 4.8 adaptive at effort low is between "
        "0.05 and 0.20 inclusive.",
        opus_sh is not None and 0.05 <= opus_sh <= 0.20,
        {
            "opus48_rate": opus_sh,
            "reading": (
                "Above 0.20 says paraphrase dominates, that the model restates rather than "
                "reuses source wording and the predicate punishes it. Section 10.2 fixes that "
                "reading before the number existed and names it a finding about the instrument "
                "before it is a finding about the model."
                if opus_sh is not None and opus_sh > 0.20
                else "Inside the band, or below it; section 10.2's two readings both name the "
                "instrument first."
            ),
        },
    )

    haiku_sh = rate("raw", "haiku45", "single_hop")
    gap8 = _delta(haiku_sh, opus_sh)
    add(
        "P8",
        "RAW single-hop rate on Haiku 4.5 no thinking is at least 0.05 above the Opus 4.8 rate.",
        gap8 is not None and gap8 >= 0.05,
        {"haiku45_rate": haiku_sh, "opus48_rate": opus_sh, "gap": gap8},
    )

    p9 = {}
    for t in TIER_KEYS:
        raw_r = rate("raw", t, "single_hop")
        layer_r = rate("layer", t, "single_hop")
        reduction = _delta(raw_r, layer_r)
        p9[t] = {
            "raw_rate": raw_r,
            "layer_rate": layer_r,
            "reduction": reduction,
            "layer_abstaining_rows": strat("layer", t, "single_hop")["abstaining_rows"],
            "reduction_above_0_10": reduction is not None and reduction > 0.10,
        }
    p9_held = all(
        v["reduction"] is not None
        and abs(v["reduction"]) <= 0.03
        and v["layer_abstaining_rows"] == 0
        for v in p9.values()
    )
    add(
        "P9",
        "LAYER single-hop rate is within 0.03 of raw on every tier and layer abstention stays at "
        "0 of 18. A reduction above 0.10 is contradicted and is read as grader conformance.",
        p9_held,
        p9,
        note=(
            "The grader-conformance reading is the measurement that decides it: no tier's "
            "reduction exceeds 0.10, so the reading section 10.2 fixed in advance does not fire "
            "on this stratum. The prediction is contradicted by the 0.03 band and by the "
            "abstentions, not by the conformance clause."
            if not any(v["reduction_above_0_10"] for v in p9.values())
            else "At least one tier's reduction exceeds 0.10 and is read as grader conformance, "
            "not as the layer working, per the clause section 10.2 fixed before any number "
            "existed."
        ),
    )

    # --- 10.3 Clean multi-hop ---------------------------------------------------------------
    p10 = {}
    for t in TIER_KEYS:
        cm = rate("raw", t, "clean_multi_hop")
        sh = rate("raw", t, "single_hop")
        conc = per_condition["raw"]["concentration"][t]["clean_multi_hop_by_first_pass_recall"]
        concentrates = (
            conc["partial_rate"] is not None
            and conc["full_recall_rate"] is not None
            and conc["partial_rate"] > conc["full_recall_rate"]
        )
        p10[t] = {
            "clean_multi_hop_rate": cm,
            "single_hop_rate": sh,
            "gap": _delta(cm, sh),
            "concentration": conc,
            "excess_concentrates_on_the_five_partial_rows": concentrates,
        }
    p10_held = all(
        v["gap"] is not None
        and v["gap"] >= 0.03
        and v["excess_concentrates_on_the_five_partial_rows"]
        for v in p10.values()
    )
    add(
        "P10",
        "RAW clean multi-hop rate is at least 0.03 above the single-hop raw rate on every tier, "
        "by parametric fill on the five partial rows.",
        p10_held,
        p10,
        note=(
            "The direction clause and the mechanism clause are scored separately and both are "
            "reported. A direction that holds by a different mechanism is not this prediction "
            "holding, which is why section 10.3 names the mechanism in its contradiction clause."
        ),
    )

    p11 = {}
    for t in TIER_KEYS:
        raw_r = rate("raw", t, "clean_multi_hop")
        layer_r = rate("layer", t, "clean_multi_hop")
        raw_rows = per_condition["raw"]["concentration"][t]["clean_multi_hop_per_row"]
        layer_rows = per_condition["layer"]["concentration"][t]["clean_multi_hop_per_row"]

        # B023 is silenced on the two lines below for the reason recorded at the matching site
        # in src/ingest/xref.py: `raw_rows` and `layer_rows` are captured late, but `decrease` is
        # consumed by the two sum() calls immediately below, within the iteration that defines
        # it, and is never stored or returned. Eager consumption by sum() is what makes the late
        # binding unreachable here.
        def decrease(q):
            a = raw_rows[q]["ungrounded_units"] if raw_rows[q]["answered"] else 0  # noqa: B023
            b = layer_rows[q]["ungrounded_units"] if layer_rows[q]["answered"] else 0  # noqa: B023
            return a - b

        named_drop = sum(decrease(q) for q in P11_NAMED_ROWS)
        other_drop = sum(decrease(q) for q in raw_rows if q not in P11_NAMED_ROWS)
        p11[t] = {
            "raw_rate": raw_r,
            "layer_rate": layer_r,
            "layer_at_or_below_raw": (
                raw_r is not None and layer_r is not None and layer_r <= raw_r
            ),
            "ungrounded_decrease_on_test_10_and_test_19": named_drop,
            "ungrounded_decrease_on_the_other_ten_rows": other_drop,
            "reduction_concentrates_on_the_named_rows": named_drop > other_drop,
            "per_row_raw": raw_rows,
            "per_row_layer": layer_rows,
        }
    p11_held = all(
        v["layer_at_or_below_raw"] and v["reduction_concentrates_on_the_named_rows"]
        for v in p11.values()
    )
    add(
        "P11",
        "LAYER clean multi-hop rate is at or below raw on every tier, with the reduction "
        "concentrated on test_10 and test_19.",
        p11_held,
        p11,
        note=(
            "Concentration is measured as the decrease in ungrounded units on the two named rows "
            "against the decrease on the other ten, a row contributing zero where it does not "
            "enter that condition's stratum totals. The definition ships with the numbers so a "
            "reader can apply a different one to the same per-row table."
        ),
    )

    p12 = {
        t: {
            "raw_abstaining_rows": strat("raw", t, "clean_multi_hop")["abstaining_rows"],
            "layer_abstaining_rows": strat("layer", t, "clean_multi_hop")["abstaining_rows"],
        }
        for t in TIER_KEYS
    }
    add(
        "P12",
        "Clean multi-hop abstention is 0 raw and 0 layer on every tier.",
        not any(v["raw_abstaining_rows"] or v["layer_abstaining_rows"] for v in p12.values()),
        p12,
    )

    # --- 10.4 Action-to-parent --------------------------------------------------------------
    p13 = {t: strat("raw", t, "action_to_parent")["abstaining_rows"] for t in TIER_KEYS}
    add(
        "P13",
        "RAW action-to-parent. Opus 4.8 adaptive at effort low abstains on at least 2 of 4; "
        "Haiku 4.5 no thinking abstains on at most 1 of 4.",
        p13["opus48"] >= 2 and p13["haiku45"] <= 1,
        p13,
    )

    def highest_check(condition, tier):
        rates = {s: rate(condition, tier, s) for s in GOLD_BEARING_STRATA}
        defined = {s: v for s, v in rates.items() if v is not None}
        target = rates["action_to_parent"]
        if target is None:
            return rates, None
        return rates, all(target >= v for v in defined.values())

    p14 = {}
    p14_unscoreable_on = []
    p14_contradicted_on = []
    for t in TIER_KEYS:
        rates, highest = highest_check("raw", t)
        p14[t] = {
            "rates": rates,
            "action_to_parent_is_highest": highest,
            "answered_rows": strat("raw", t, "action_to_parent")["answered_rows"],
        }
        if highest is None:
            p14_unscoreable_on.append(t)
        elif not highest:
            p14_contradicted_on.append(t)
    p14["scoreable_on"] = [t for t in TIER_KEYS if t not in p14_unscoreable_on]
    p14["unscoreable_on"] = p14_unscoreable_on
    p14["contradicted_on"] = p14_contradicted_on
    add(
        "P14",
        "RAW. Answered rows on action-to-parent carry the highest unsupported-claim rate of any "
        "gold-bearing stratum on every tier.",
        not p14_contradicted_on and not p14_unscoreable_on,
        p14,
        note=(
            "The verdict rests on "
            + (
                f"the tiers where another gold-bearing stratum is measurably higher: "
                f"{p14_contradicted_on}. "
                if p14_contradicted_on
                else "no tier where another stratum is measurably higher. "
            )
            + (
                f"Separately, the comparison cannot be made on {p14_unscoreable_on}, where the "
                "stratum has no answered rows and therefore no rate. An undefined rate is not "
                "zero and is not compared as one; that tier is named rather than given a verdict."
                if p14_unscoreable_on
                else "Every tier's action-to-parent rate is defined, so the comparison is "
                "scoreable on all three."
            )
        ),
    )

    p15 = {}
    for t in TIER_KEYS:
        rates, highest = highest_check("layer", t)
        p15[t] = {
            "raw_abstaining_rows": strat("raw", t, "action_to_parent")["abstaining_rows"],
            "layer_abstaining_rows": strat("layer", t, "action_to_parent")["abstaining_rows"],
            "layer_rates": rates,
            "action_to_parent_is_highest_under_the_layer": highest,
            "action_to_parent_was_highest_at_raw": p14[t]["action_to_parent_is_highest"],
        }
    p15_held = all(
        v["layer_abstaining_rows"] >= v["raw_abstaining_rows"]
        and v["action_to_parent_is_highest_under_the_layer"] is not False
        for v in p15.values()
    )
    add(
        "P15",
        "LAYER action-to-parent. Abstention is at least raw on every tier, and the stratum "
        "remains the highest-rate stratum.",
        p15_held,
        p15,
        note=(
            "Scored against the contradiction clause as written: layer abstention below raw on "
            "any tier, or the stratum ceasing to be highest on any tier. Where the stratum was "
            "not highest at raw the word `remains` does no work, and where its rate is undefined "
            "the comparison is not made; both cases are visible in `observed`."
        ),
    )

    add(
        "P16",
        "LAYER RETRIEVAL stays where it is measured: test_41 remains recovered with all three "
        "carriers, test_39, test_40 and test_42 remain at zero recovery, stratum 0.25.",
        (
            per_condition["layer"]["layer_retrieval_cross_check"][
                "stratum_recovered_passage_recall"
            ]
            == 0.25
            and per_condition["layer"]["layer_retrieval_cross_check"]["action_to_parent"][
                "test_41"
            ]["recovered_units"]
            == [
                "nist_ai_100_1:sub_MEASURE_2.2",
                "nist_ai_600_1:sub_MEASURE_2.2",
                "nist_playbook:sub_MEASURE_2.2",
            ]
            and all(
                per_condition["layer"]["layer_retrieval_cross_check"]["action_to_parent"][q][
                    "recovered_passage_recall"
                ]
                == 0.0
                for q in ("test_39", "test_40", "test_42")
            )
            and not per_condition["layer"]["layer_retrieval_cross_check"][
                "disagreements_against_the_committed_layer_artifact"
            ]
        ),
        per_condition["layer"]["layer_retrieval_cross_check"],
        note=(
            "Scored on the committed layer artifact and on the body-digest chain: the context "
            "this runner rebuilt for every second-call body matched the digest the result record "
            "names, and its per-row fetch counts agree with the layer artifact on every row. The "
            "third contradiction route, a recovery on test_41 whose trace shows an action "
            "identifier or the legend being read, would breach the firewall and stop the scope; "
            "the committed trace names sibling-label resolution and no other route."
        ),
    )

    # --- 10.5 Near-miss ---------------------------------------------------------------------
    p17 = {}
    for t in TIER_KEYS:
        nm = rate("raw", t, "near_miss")
        sh = rate("raw", t, "single_hop")
        p17[t] = {
            "near_miss_rate": nm,
            "near_miss_answered_rows": strat("raw", t, "near_miss")["answered_rows"],
            "near_miss_claim_units": strat("raw", t, "near_miss")["claim_units"],
            "single_hop_rate": sh,
            "gap": _delta(nm, sh),
        }
    add(
        "P17",
        "RAW near-miss rate over answered rows is at least 0.05 above the single-hop raw rate on "
        "every tier.",
        all(v["gap"] is not None and v["gap"] >= 0.05 for v in p17.values()),
        p17,
        note=(
            "The answered-row count and the claim-unit count ship beside every gap, because on "
            "two tiers this stratum's rate rests on a single answered row."
        ),
    )

    p18 = {t: strat("raw", t, "near_miss")["abstaining_rows"] for t in TIER_KEYS}
    add(
        "P18",
        "RAW near-miss abstention. Opus 4.8 adaptive at effort low abstains on at least 3 of 8; "
        "Haiku 4.5 no thinking on at most 2 of 8.",
        p18["opus48"] >= 3 and p18["haiku45"] <= 2,
        p18,
    )

    p19 = {}
    for t in TIER_KEYS:
        raw_r = rate("raw", t, "near_miss")
        layer_r = rate("layer", t, "near_miss")
        reduction = _delta(raw_r, layer_r)
        raw_conc = per_condition["raw"]["concentration"][t][
            "near_miss_units_by_reference_surface"
        ]
        layer_conc = per_condition["layer"]["concentration"][t][
            "near_miss_units_by_reference_surface"
        ]
        surface_moved = _delta(
            raw_conc["surface_carrying_rate"], layer_conc["surface_carrying_rate"]
        )
        p19[t] = {
            "raw_rate": raw_r,
            "layer_rate": layer_r,
            "reduction": reduction,
            "layer_abstaining_rows": strat("layer", t, "near_miss")["abstaining_rows"],
            "raw_units_by_surface": raw_conc,
            "layer_units_by_surface": layer_conc,
            "surface_carrying_rate_change": surface_moved,
            "reduction_concentrates_on_surface_carrying_units": (
                reduction is not None
                and reduction > 0
                and surface_moved is not None
                and surface_moved > 0
            ),
        }
    p19_held = all(
        v["reduction"] is not None
        and v["reduction"] >= 0.05
        and v["layer_abstaining_rows"] <= 1
        and v["reduction_concentrates_on_surface_carrying_units"]
        for v in p19.values()
    )
    add(
        "P19",
        "LAYER near-miss rate is at least 0.05 below raw on every tier over answered rows, "
        "abstention is at most 1 of 8, and the reduction is read as the layer working only if it "
        "concentrates on units carrying the queried surface.",
        p19_held,
        p19,
        note=(
            "The reading clause is decided by the two rates beside each other. Where the "
            "surface-carrying rate does not move while the rate falls, the fall is denominator "
            "growth on units the reference condition is silent about, and section 10.5 reads that "
            "as grader conformance rather than as the layer working."
        ),
    )

    # --- 10.6 No-context, over the 42 gold-bearing rows -------------------------------------
    p20 = {t: gold("no_context", t)["abstaining_rows"] for t in TIER_KEYS}
    add(
        "P20",
        "NO-CONTEXT abstention is at most 2 of 42 gold-bearing rows per tier.",
        all(v <= 2 for v in p20.values()),
        {t: {"abstaining_rows": p20[t], "rows": gold("no_context", t)["rows"]} for t in TIER_KEYS},
    )

    p21 = {t: gold("no_context", t)["parametric_coincidence_rate"] for t in TIER_KEYS}
    ordered = (
        p21["opus48"] is not None
        and p21["sonnet5"] is not None
        and p21["haiku45"] is not None
        and p21["opus48"] >= p21["sonnet5"] >= p21["haiku45"]
    )
    add(
        "P21",
        "Parametric coincidence rate is below 0.30 on every tier, ordered Opus 4.8 adaptive at "
        "effort low at least Sonnet 5 adaptive at effort high at least Haiku 4.5 no thinking.",
        all(v is not None and v < 0.30 for v in p21.values()) and ordered,
        {
            **{
                t: {
                    "parametric_coincidence_rate": p21[t],
                    "claim_units": gold("no_context", t)["claim_units"],
                    "grounded_units": gold("no_context", t)["grounded_units"],
                }
                for t in TIER_KEYS
            },
            "order_opus_at_least_sonnet_at_least_haiku": ordered,
        },
        note=(
            "The population is the 42 gold-bearing rows, which is what section 10.6 declares, and "
            "not all fifty. A zero over a non-trivial denominator carries its own positive "
            "control here: the same predicate in the same run returns grounded units on the other "
            "two tiers, so it is shown capable of returning a non-zero on this condition."
        ),
    )

    # --- 10.7 Instrument checks -------------------------------------------------------------
    stops = {
        f"{c}.{t}": _batch_record(c, t)["max_tokens_stops"]
        for c in ("raw", "no_context", "second_call")
        for t in TIER_KEYS
    }
    add(
        "P22",
        "The count of responses stopping on max_tokens is zero on every run.",
        not any(stops.values()),
        {"max_tokens_stops": stops, "runs_checked": len(stops)},
    )

    variants = {
        f"{c}.{t}": block(c, t)["marker_variant_rows"]
        for c in CONDITIONS
        for t in TIER_KEYS
    }
    add(
        "P23",
        "Zero marker_variant rows on Opus 4.8 adaptive at effort low and on Sonnet 5 adaptive at "
        "effort high.",
        not any(v for k, v in variants.items() if k.endswith(("sonnet5", "opus48"))),
        {"marker_variant_rows": variants},
    )

    p24 = {}
    p24_ok = True
    for condition in CONDITIONS:
        for t in TIER_KEYS:
            b = block(condition, t)
            zero_unit = b["answered_rows_with_zero_claim_units"]
            variant = b["marker_variant_rows"]
            p24[f"{condition}.{t}"] = {
                "answered_rows_with_zero_claim_units": zero_unit,
                "answered_row_ids_with_zero_claim_units": b[
                    "answered_row_ids_with_zero_claim_units"
                ],
                "marker_variant_rows": variant,
                "equal": zero_unit == variant,
            }
            if zero_unit != variant:
                p24_ok = False
    add(
        "P24",
        "Answered rows carrying zero claim units equal the marker_variant count, on every tier "
        "and condition.",
        p24_ok,
        p24,
        note=(
            "Section 10.7's own clause governs the reading: more zero-unit answered rows than "
            "variant rows means a second route exists that the file did not foresee, and the rows "
            "are listed with what their answers contained. The second route is a refusal-stopped "
            "response, which carries zero content blocks, so the answer text is the empty string. "
            "It classifies as answered under the committed classify_response, which compares a "
            "whole response against the marker, and it yields no claim unit. No predicate is "
            "patched to rescue the prediction."
        ),
    )

    # --- 10.8 Cross-tier, pooled over the 42 gold-bearing rows ------------------------------
    p25 = {t: gold("raw", t)["unsupported_claim_rate"] for t in TIER_KEYS}
    add(
        "P25",
        "Pooled over the 42 gold-bearing rows, the Haiku 4.5 no-thinking raw rate is at least the "
        "Sonnet 5 adaptive-at-high raw rate and at least the Opus 4.8 adaptive-at-low raw rate.",
        p25["haiku45"] is not None
        and p25["sonnet5"] is not None
        and p25["opus48"] is not None
        and p25["haiku45"] >= p25["sonnet5"]
        and p25["haiku45"] >= p25["opus48"],
        {
            t: {
                "unsupported_claim_rate": p25[t],
                "claim_units": gold("raw", t)["claim_units"],
                "ungrounded_units": gold("raw", t)["ungrounded_units"],
                "answered_rows": gold("raw", t)["answered_rows"],
            }
            for t in TIER_KEYS
        },
    )

    out.append(
        {
            "prediction": "P26",
            "text": "Sonnet 5 against Opus 4.8 is not predicted. The pair is reported without a "
            "prediction attached.",
            "verdict": "not_predicted",
            "observed": {
                "sonnet5_adaptive_at_high_raw_rate": p25["sonnet5"],
                "opus48_adaptive_at_low_raw_rate": p25["opus48"],
                "sonnet5_claim_units": gold("raw", "sonnet5")["claim_units"],
                "opus48_claim_units": gold("raw", "opus48")["claim_units"],
            },
            "note": (
                "No verdict is issued, because none was predicted. The two differ in model "
                "strength and in reasoning regime in opposite directions, so no prior separates "
                "them."
            ),
        }
    )

    return out


def build() -> dict:
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = load_rows(QUERY_SET)
    strata = load_strata()

    graded: dict[str, dict[str, dict[str, dict]]] = {"raw": {}, "no_context": {}, "layer": {}}
    for tier in TIER_KEYS:
        graded["raw"][tier] = _raw_and_no_context_rows(tier, "raw", store, rows)
        graded["no_context"][tier] = _raw_and_no_context_rows(tier, "no_context", store, rows)
        graded["layer"][tier] = _layer_rows(tier, store, fetch, rows)

    per_condition: dict[str, dict] = {}
    for condition in CONDITIONS:
        blocks = {t: _block(condition, list(graded[condition][t].values())) for t in TIER_KEYS}
        gold_blocks = {}
        for tier in TIER_KEYS:
            selected = [
                r
                for q, r in sorted(graded[condition][tier].items())
                if strata[q] in GOLD_BEARING_STRATA
            ]
            gold_block = _block(condition, selected)
            gold_block.pop("per_row_distribution", None)
            gold_block["population"] = (
                "The 42 gold-bearing rows, the four strata other than adversarial. This is the "
                "population sections 10.6 and 10.8 declare, and it is not the fifty."
            )
            gold_blocks[tier] = gold_block
        entry: dict = {
            "regime": {t: REGIME[t] for t in TIER_KEYS},
            "per_tier": blocks,
            "pooled": _pooled_from_blocks(condition, [blocks[t] for t in TIER_KEYS]),
            "gold_bearing": gold_blocks,
            "gold_bearing_pooled": _pooled_from_blocks(
                condition, [gold_blocks[t] for t in TIER_KEYS]
            ),
            "per_stratum": {
                t: _per_stratum(condition, graded[condition][t], strata) for t in TIER_KEYS
            },
            "concentration": {
                t: _concentration(condition, graded[condition][t], strata) for t in TIER_KEYS
            },
            "adversarial_verdicts": {
                t: _adversarial_verdicts(list(graded[condition][t].values()), strata)
                for t in TIER_KEYS
            },
        }
        if condition == "layer":
            entry["fate_table"] = {
                t: _fate_table(list(graded["layer"][t].values())) for t in TIER_KEYS
            }
            entry["abstention_observations"] = {
                t: _abstention_observations(list(graded["layer"][t].values()))
                for t in TIER_KEYS
            }
            entry["comparable_set"] = {
                t: _comparable_set(graded["raw"][t], graded["layer"][t]) for t in TIER_KEYS
            }
            entry["added_cost_and_latency"] = {
                t: _cost_and_latency("second_call", t) for t in TIER_KEYS
            }
            entry["layer_retrieval_cross_check"] = _layer_retrieval_cross_check(
                graded["layer"][TIER_KEYS[0]]
            )
            entry["layer_abstention_reading_on_unfired_rows"] = {
                "reading": (
                    "Section 6.1's second clause reads 'zero grounded claim units after the second "
                    "call'. On test_34 and test_39 there is no second call, so the clause has no "
                    "referent and only the marker clause applies, to the one pass that exists."
                ),
                "rows_that_would_flip_under_the_other_reading": {
                    t: sorted(
                        q
                        for q, r in graded["layer"][t].items()
                        if r["would_flip_under_the_other_unfired_reading"]
                    )
                    for t in TIER_KEYS
                },
                "fired_rows_with_zero_claim_units_that_are_not_marker_abstentions": {
                    t: sorted(
                        q
                        for q, r in graded["layer"][t].items()
                        if r["corrective_pass_fired"]
                        and r["n_units"] == 0
                        and not r["abstained_marker_either_pass"]
                    )
                    for t in TIER_KEYS
                },
                "zero_grounded_convention": (
                    "bool(units) and n_grounded == 0, the committed development implementation at "
                    "src/score/run_dev_second_call_grading.py. An answer with no claim units at "
                    "all is therefore not a zero-grounded abstention. The rows the two readings "
                    "could separate on a FIRED row are the ones listed immediately above: a fired "
                    "row with no claim units that is not already a marker abstention on either "
                    "pass. A fired row whose second answer is the marker has no claim units by "
                    "section 4 and is a layer abstention under the first clause regardless, so it "
                    "does not separate the readings and is not listed."
                ),
            }
        per_condition[condition] = entry

    raw_costs = {
        t: {c: _cost_and_latency(c, t) for c in ("raw", "no_context", "second_call")}
        for t in TIER_KEYS
    }

    secondary = {
        "comparison": "Claude Haiku 4.5 plus layer against Claude Opus 4.8 raw",
        "reasoning_regime_difference": (
            "Claude Haiku 4.5 with no thinking, plus the layer, against Claude Opus 4.8 with "
            "adaptive thinking at effort low, raw. The two sides share no model, no reasoning "
            "regime and no decoding setting."
        ),
        "haiku45_plus_layer": {
            "answered_rows": per_condition["layer"]["per_tier"]["haiku45"]["answered_rows"],
            "claim_units": per_condition["layer"]["per_tier"]["haiku45"]["claim_units"],
            "ungrounded_units": per_condition["layer"]["per_tier"]["haiku45"][
                "ungrounded_units"
            ],
            "unsupported_claim_rate": per_condition["layer"]["per_tier"]["haiku45"][
                "unsupported_claim_rate"
            ],
        },
        "opus48_raw": {
            "answered_rows": per_condition["raw"]["per_tier"]["opus48"]["answered_rows"],
            "claim_units": per_condition["raw"]["per_tier"]["opus48"]["claim_units"],
            "ungrounded_units": per_condition["raw"]["per_tier"]["opus48"]["ungrounded_units"],
            "unsupported_claim_rate": per_condition["raw"]["per_tier"]["opus48"][
                "unsupported_claim_rate"
            ],
        },
        "no_prediction": (
            "Section 9 attaches no predicted figure to this comparison and reports it whichever "
            "way it falls. Both answered-row counts ship beside it every time, because the layer "
            "abstains where raw answers and the two sides are rates over different row sets. It "
            "is never a headline."
        ),
    }

    return {
        "description": (
            "The grading of record for the sealed run. One runner, one code path, the frozen "
            "grader over all nine run and tier sets. Every figure re-derives from committed files "
            "with no key. Produced by python -m src.score.run_sealed_grading."
        ),
        "produced_by": "python -m src.score.run_sealed_grading",
        "written_to": "eval/test_grading_results.json",
        "query_set": QUERY_SET,
        "reproducibility_level": 1,
        "tiers": list(TIER_KEYS),
        "conditions": list(CONDITIONS),
        "grader_frozen_at": "15e31d5",
        "thresholds": {
            "overlap_threshold": OVERLAP_THRESHOLD,
            "short_unit_length": SHORT_UNIT_LENGTH,
            "note": (
                "Read from the frozen grader. eval/generation_predictions.md section 5.2 allowed "
                "at most one move, at the freeze commit, on the development first-pass "
                "generations alone. Neither moved and neither moves here for any reason."
            ),
        },
        "integrity": {
            "answers_located_by": "custom_id, never by position",
            "chain": (
                "Every graded answer's request body is rebuilt from committed files and its "
                "sha256 compared against the body_sha256 the result record carries, before the "
                "answer is graded. A mismatch raises ChainError and stops the run."
            ),
            "context_per_condition": {
                "raw": "the row's committed first-pass ten, which its own body carried",
                "layer": (
                    "the corrective pass's own output on the 48 firing rows, which the "
                    "second-call body carried; the first-pass ten on test_34 and test_39, where "
                    "the pass did not fire and the layer's answer is the first-pass answer"
                ),
                "no_context": (
                    "the RAW condition's committed first-pass ten for the same query, which the "
                    "model never saw. The no-context body carries no chunk, so this is "
                    "deliberately not the body's own context and is asserted separately"
                ),
            },
            "grader_reads_no_label": (
                "grade_row takes an answer and a context. Stratum, subtype and gold never enter "
                "it. The five committed strata are joined by row id after every verdict exists."
            ),
        },
        "instrument": {
            "the_ruler_punishes_paraphrase": (
                "The unsupported-claim rate is a rate under a lexical ruler: normalised-token "
                "overlap in a sliding window, with no stemming and no entailment judge. A claim "
                "that restates a chunk in the model's own words scores as unsupported even where "
                "the chunk was present and the claim is true of it. Every rate here is therefore "
                "a property of the ruler before it is a property of the model, and the "
                "development run measured close paraphrase on both sides of the 0.75 threshold."
            ),
            "grader_conformance": (
                "The layer's second-call prompt tells the model that listed statements were not "
                "supported and to support them from the context or leave them out. A model that "
                "rewrites a flagged sentence toward source wording raises the grader's score "
                "without making the answer more true. Section 10 fixes the reading before the "
                "numbers existed: on single-hop a layer reduction above 0.10 is read as grader "
                "conformance and not as the layer working, and on near-miss a reduction is read "
                "as the layer working only if it concentrates on units carrying the queried "
                "surface. Both readings are applied as written."
            ),
            "misattribution_blindness": (
                "Section 5.5. Misattribution is seen only where the unit names a surface the "
                "committed grammar recognises. A unit that misattributes without naming a "
                "provision is graded by overlap alone and can be grounded; recitals, sections and "
                "chapters have no pattern; the second member of a coordinated citation is not "
                "captured; and a block can satisfy the reference test for a surface it cites "
                "rather than one it is. This study measures a subset of the surface its own "
                "methodology describes."
            ),
            "citation_mode_blindness": (
                "Section 5.5. No prompt requests citations, so the failure mode of citing a real "
                "chunk that does not say the thing has no surface here. It is not that the layer "
                "catches it or fails to: it cannot occur, and no pre-registered figure scores it."
            ),
        },
        "per_condition": per_condition,
        "predictions_scored": _score_predictions(per_condition, graded, strata),
        "secondary_comparison": secondary,
        "cost_and_latency": {
            "source": "eval/generation_predictions.md section 6.3, over the committed batch records",
            "per_tier": raw_costs,
            "added_by_the_layer": (
                "The layer's added generation cost is the second-call run alone, because the "
                "first pass is shared with the raw condition by construction. The corrective "
                "pass's own retrieval cost is zero model calls and is reported as fetch volume."
            ),
        },
        "rows": {
            condition: {tier: graded[condition][tier] for tier in TIER_KEYS}
            for condition in CONDITIONS
        },
    }


def write(path=None):
    target = GRADING_PATH if path is None else path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    # newline="\n" pins LF on every platform; see the note in src/score/run_retrieval_eval.py.
    target.write_text(payload, encoding="utf-8", newline="\n")
    return target


if __name__ == "__main__":
    print(f"wrote {write()}")
