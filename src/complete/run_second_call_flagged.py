"""The sealed second-call flagged lists, per tier, and nothing else.

WHY THIS IS NOT src/score/run_dev_second_call_grading.py. That module builds a flagged list and
grades the answers in one run, which suited the development split where both happened at one
commit. On the sealed set they do not: the grading of record is a single separate commit, and a
producer that graded here would put a faithfulness figure in the tree ahead of it. This module
therefore stops at the flagged list. It imports nothing from src/score/ except the claim-unit
segmenter that src/complete/flagging.py already depends on.

WHY IT LIVES UNDER src/complete/. src/complete/flagging.py's own docstring states that it "lives
under src/complete/ rather than under src/score/ because its output is layer machinery and not
measurement". The producer of that output belongs beside it for the same reason.

WHAT A FLAGGED LIST IS COMPUTED AGAINST. The FIRST-PASS context, not the augmented one, because
it records what the context the model then had did not support. The body the list goes into
carries the augmented context. eval/generation_predictions.md section 5.1 fixes both halves and
src/score/run_dev_second_call_grading.py states the same division for the development split.

THE POPULATION IS THE ROWS THE CORRECTIVE PASS FIRES ON, derived here from
src.complete.augment.augment rather than read from a list, and cross-checked against the
committed layer artifact by tests/test_second_call_flagged.py rather than trusted.

A ROW WHOSE FIRST PASS ABSTAINED STILL GETS A SECOND CALL. That is the case where augmentation
can rescue a miss, and it is what the development split did: dev_11 and dev_12 abstained on the
Haiku tier and both carry a second call with an empty flagged list. The first answer such a body
carries is the marker itself.

REPRODUCIBILITY LEVEL 1 over committed inputs: the committed first-pass answers, the committed
retrieval results, the committed chunk store and the committed unit index. No model, no key, no
clock, no randomness.

Run:  python -m src.complete.run_second_call_flagged <tier>
"""

from __future__ import annotations

import json
import sys

from src.complete.augment import augment, load_fetch_store
from src.complete.flagging import flagged_units
from src.generate.assemble import custom_id, first_pass_chunks, load_chunk_store, load_rows
from src.generate.prompts import classify_response
from src.ingest.corpus_integrity import REPO_ROOT

QUERY_SET = "test"
RUNS_DIR = REPO_ROOT / "data" / "runs"
EVAL_DIR = REPO_ROOT / "eval"


def output_path(tier: str):
    """One file per tier, so each tier's commit adds a file and extends none.

    The development artifact pools all three tiers in one file, which was right when they landed
    in one scope. Here each tier lands in its own commit, and a pooled file would mean the second
    and third tiers rewriting an artifact the first committed.
    """
    return EVAL_DIR / f"{QUERY_SET}_second_call_flagged.{tier}.json"


def first_answers(tier: str) -> dict[str, str]:
    """The committed first-pass answers for a tier, by query id."""
    out: dict[str, str] = {}
    with open(RUNS_DIR / f"{QUERY_SET}.raw.{tier}.jsonl", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            out[record["custom_id"].split("__")[-1]] = "".join(
                block.get("text", "")
                for block in record["response"]["message"]["content"]
                if block.get("type") == "text"
            )
    return out


def build(tier: str) -> dict:
    store = load_chunk_store()
    fetch = load_fetch_store()
    rows = load_rows(QUERY_SET)
    answers = first_answers(tier)

    fired: dict[str, dict] = {}
    silent: list[str] = []
    for row in rows:
        query_id = row["id"]
        first_pass = first_pass_chunks(row, store)
        result = augment(row["query"], first_pass, fetch)
        if not result.triggered:
            silent.append(query_id)
            continue
        flagged = list(flagged_units(answers[query_id], first_pass))
        fired[custom_id(QUERY_SET, "second_call", query_id, tier)] = {
            "query_id": query_id,
            "flagged_units": flagged,
            "n_flagged": len(flagged),
            "first_pass_class": classify_response(answers[query_id]),
            "context_set_size": result.size,
            "fetched_chunk_count": len(result.fetched_chunks),
        }

    return {
        "description": (
            "The flagged lists the sealed second-call bodies carry, per row, for one tier. Each "
            "is the first answer's ungrounded units under src/complete/flagging.py, the frozen "
            "operational implementation, computed against the FIRST-PASS context. The bodies "
            "themselves carry the augmented context. Committed so a reviewer can rebuild every "
            "body exactly from committed files with no key."
        ),
        "produced_by": f"python -m src.complete.run_second_call_flagged {tier}",
        "written_to": str(output_path(tier).relative_to(REPO_ROOT)),
        "query_set": QUERY_SET,
        "tier": tier,
        "first_pass_source": f"data/runs/{QUERY_SET}.raw.{tier}.jsonl",
        "population": {
            "starting_rows": len(rows),
            "fired": len(fired),
            "not_fired": sorted(silent),
            "rule": (
                "src.complete.augment.augment reports triggered; a row it does not fire on "
                "receives no second call and its layer answer is its first-pass answer."
            ),
        },
        "grading_note": (
            "Nothing here is graded. No claim unit is scored and no rate is computed. The "
            "grading of record is a separate commit over committed files, per CLAUDE.md Rule 9."
        ),
        "rows": fired,
    }


def write(tier: str):
    payload = build(tier)
    path = output_path(tier)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    written = write(sys.argv[1])
    print(f"wrote {written}")
