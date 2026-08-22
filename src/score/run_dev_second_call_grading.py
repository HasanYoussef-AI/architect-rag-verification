"""The development second-call flagged lists and grading, per tier.

TWO ARTIFACTS FROM ONE PRODUCER, so neither is an artifact without a producer.

  eval/dev_second_call_flagged.json  the flagged lists the second-call bodies were built from,
  per row: the first answer's ungrounded units under the frozen operational implementation in
  src/complete/flagging.py. This is what the second-call prompt carried as the statements the
  context did not support, and it is committed so a reviewer can rebuild the bodies exactly.

  eval/dev_second_call_grading.json  the second answers graded by the frozen grader.

WHAT EACH ANSWER IS GRADED AGAINST. eval/generation_predictions.md section 5.1: a second-call
answer is graded against the corrective pass's output, the first-pass ten unchanged followed by
the fetched chunks, and never against the first-pass ten alone. The flagged list is the other way
round: it is computed against the FIRST-PASS context, because it records what the context the
model then had did not support. Both are what the run actually used.

ABSTENTION IS THE TWO-PREDICATE RULE of section 6.1: in the layer condition a row abstains when
the marker is returned on EITHER pass, or when the second call's answer carries zero grounded
claim units. Both halves are recorded per row so the figure can be read either way.

NOTHING HERE MOVES A THRESHOLD. The grader is frozen at 15e31d5 and section 5.4 forbids a move on
anything the second calls show. This module reads the frozen constants and never sets them.

REPRODUCIBILITY LEVEL 1 over committed inputs: the first-pass answers, the second-call answers,
the committed development retrieval and the committed chunk store. No model, no key, no clock.

Run:  python -m src.score.run_dev_second_call_grading
"""

from __future__ import annotations

import json

from src.complete.augment import augment, load_fetch_store
from src.complete.flagging import flagged_units
from src.generate.assemble import custom_id, first_pass_chunks, load_chunk_store, load_rows
from src.generate.prompts import ABSTAINED, classify_response
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.claims import claim_units
from src.score.grounding import OVERLAP_THRESHOLD, SHORT_UNIT_LENGTH, is_grounded, score_unit

# Every tier whose second calls have run. Extended as each lands, so there is one runner and one
# pair of artifacts rather than a parallel set per tier.
TIERS = ("haiku45", "sonnet5")
RUNS_DIR = REPO_ROOT / "data" / "runs"
FLAGGED_PATH = REPO_ROOT / "eval" / "dev_second_call_flagged.json"
GRADING_PATH = REPO_ROOT / "eval" / "dev_second_call_grading.json"


def _answers(condition: str, tier: str) -> dict[str, str]:
    out: dict[str, str] = {}
    with open(RUNS_DIR / f"dev.{condition}.{tier}.jsonl", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            out[record["custom_id"].split("__")[-1]] = "".join(
                b.get("text", "")
                for b in record["response"]["message"]["content"]
                if b.get("type") == "text"
            )
    return out


def _layer_abstains(record: dict) -> bool:
    """Section 6.1's layer rule: the marker on either pass, or zero grounded units after."""
    return (
        record["abstained_marker_either_pass"]
        or record["abstained_zero_grounded_after_second_call"]
    )


def build() -> tuple[dict, dict]:
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = {r["id"]: r for r in load_rows("dev")}

    flagged_payload: dict[str, dict] = {}
    graded: dict[str, dict] = {}
    for tier in TIERS:
        first = _answers("raw", tier)
        second = _answers("second_call", tier)
        for query_id in sorted(second):
            row = rows[query_id]
            first_pass = first_pass_chunks(row, store)
            result = augment(row["query"], first_pass, fetch)
            flagged = list(flagged_units(first[query_id], first_pass))
            key = custom_id("dev", "second_call", query_id, tier)
            flagged_payload[key] = {
                "flagged_units": flagged,
                "n_flagged": len(flagged),
                "first_pass_class": classify_response(first[query_id]),
            }

            answer = second[query_id]
            response_class = classify_response(answer)
            units = []
            for unit in claim_units(answer):
                units.append(
                    {
                        "text": unit,
                        "score": score_unit(unit, result.context),
                        "grounded": is_grounded(unit, result.context),
                        "was_flagged": unit in flagged,
                    }
                )
            n_grounded = sum(1 for u in units if u["grounded"])
            graded[key] = {
                "first_pass_class": classify_response(first[query_id]),
                "second_call_class": response_class,
                "context_set_size": result.size,
                "n_flagged_in": len(flagged),
                "units": units,
                "n_units": len(units),
                "n_grounded": n_grounded,
                "n_ungrounded": len(units) - n_grounded,
                "repeated_flagged_unchanged": [u["text"] for u in units if u["was_flagged"]],
                "repeated_flagged_now_grounded": [
                    u["text"] for u in units if u["was_flagged"] and u["grounded"]
                ],
                "flagged_not_returned": [f for f in flagged if all(u["text"] != f for u in units)],
                "abstained_marker_either_pass": (
                    classify_response(first[query_id]) == ABSTAINED
                    or response_class == ABSTAINED
                ),
                "abstained_zero_grounded_after_second_call": bool(units) and n_grounded == 0,
            }

    def totals(keys) -> dict:
        selected = [graded[k] for k in keys]
        answered = [r for r in selected if not _layer_abstains(r)]
        units_all = [u for r in answered for u in r["units"]]
        ungrounded = [u for u in units_all if not u["grounded"]]
        return {
            "rows": len(selected),
            "layer_abstaining_rows": len(selected) - len(answered),
            "answered_rows": len(answered),
            "claim_units": len(units_all),
            "ungrounded_units": len(ungrounded),
            "unsupported_claim_rate": (
                round(len(ungrounded) / len(units_all), 6) if units_all else None
            ),
            "rows_repeating_a_flagged_unit_unchanged": sum(
                1 for r in selected if r["repeated_flagged_unchanged"]
            ),
            "flagged_units_in": sum(r["n_flagged_in"] for r in selected),
            "flagged_units_repeated_unchanged": sum(
                len(r["repeated_flagged_unchanged"]) for r in selected
            ),
            "flagged_units_repeated_now_grounded": sum(
                len(r["repeated_flagged_now_grounded"]) for r in selected
            ),
            "flagged_units_not_returned": sum(len(r["flagged_not_returned"]) for r in selected),
            # DECLARED BEFORE ANY SEALED CALL, and reported BESIDE the layer abstention rate and
            # never folded into it. Section 6.1 abstains on the marker on either pass, so a row
            # that abstained first and then answered substantively still counts as a layer
            # abstention. This records how often that happened rather than changing the rule.
            "first_pass_abstentions_with_a_substantive_second_answer": sum(
                1
                for r in selected
                if r["first_pass_class"] == ABSTAINED
                and r["second_call_class"] != ABSTAINED
                and r["n_units"] > 0
            ),
        }

    keys_by_tier = {t: [k for k in sorted(graded) if f"__{t}__" in k] for t in TIERS}
    grading_payload = {
        "description": (
            "The development second-call grading, per tier. The frozen grader over the committed "
            "second answers, each against the corrective pass's own output. Reproducibility "
            "level 1. Produced by python -m src.score.run_dev_second_call_grading."
        ),
        "produced_by": "python -m src.score.run_dev_second_call_grading",
        "written_to": "eval/dev_second_call_grading.json",
        "tiers": list(TIERS),
        "grader_frozen_at": "15e31d5",
        "thresholds": {
            "overlap_threshold": OVERLAP_THRESHOLD,
            "short_unit_length": SHORT_UNIT_LENGTH,
            "note": "Read from the frozen grader. Section 5.4 forbids a move on what these show.",
        },
        "abstention_rule": (
            "Section 6.1, layer condition, two predicates: the marker on either pass, or zero "
            "grounded claim units after the second call."
        ),
        "per_tier": {t: totals(keys_by_tier[t]) for t in TIERS},
        "rows": graded,
    }
    flagged_full = {
        "description": (
            "The flagged lists the development second-call bodies carried, per row. Each is the "
            "first answer's ungrounded units under src/complete/flagging.py, the frozen "
            "operational implementation, computed against the FIRST-PASS context."
        ),
        "produced_by": "python -m src.score.run_dev_second_call_grading",
        "written_to": "eval/dev_second_call_flagged.json",
        "tiers": list(TIERS),
        "rows": flagged_payload,
    }
    return flagged_full, grading_payload


def write():
    flagged, grading = build()
    for path, payload in ((FLAGGED_PATH, flagged), (GRADING_PATH, grading)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    return FLAGGED_PATH, GRADING_PATH


if __name__ == "__main__":
    for p in write():
        print(f"wrote {p}")
