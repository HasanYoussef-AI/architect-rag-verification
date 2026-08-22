"""Produce the development first-pass grading artifact, the freeze commit's basis.

WHAT THIS IS FOR. eval/generation_predictions.md section 5.4 requires the grounding predicate to be
built at one commit and frozen at another, and requires the freeze to record what the reference
condition turned, whether that is zero or not. This module produces the figures that record it,
from the committed grader over the committed development first-pass answers, so the judgment rests
on an artifact a reviewer re-derives rather than on prose.

REPRODUCIBILITY LEVEL 1. Inputs are the three committed answer files under data/runs/, the
committed development retrieval results and the committed chunk store. No model, no key, no
network, no clock, no randomness, no optional dependency. Two runs write identical bytes and
tests/test_dev_grading.py asserts the committed artifact equals a fresh render.

WHAT IT READS, AND WHAT IT DOES NOT. Per section 5.4 the grader sees the committed answer and the
committed context of the request that produced it, and never gold. This module passes exactly that:
the answer text from the result record, and the rendered blocks of that row's fused top 10. It
reads the tier only to key the output, never to grade; every figure per tier is the same computation
run over a different set of answers.

THE CONTEXT IS THE RENDERED BLOCK. src/score/grounding.py's rendered_block reproduces the exact
per-chunk string src/generate/prompts.py put in the request, which is what section 5.1 names as the
context. The bodies are unchanged since they were sent: the content digest over the twelve
development raw requests is pinned in tests/test_generate_assembly.py and is green.

Run:  python -m src.score.run_dev_grading
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from src.complete.absence import RetrievedChunk
from src.complete.flagging import unit_is_supported
from src.generate.assemble import first_pass_chunks, load_chunk_store, load_rows
from src.generate.prompts import ABSTAINED, MARKER_VARIANT, classify_response
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import primary_tokens
from src.score.adversarial import row_verdict
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

TIERS = ("haiku45", "sonnet5", "opus48")
RUNS_DIR = REPO_ROOT / "data" / "runs"
GRADING_PATH = REPO_ROOT / "eval" / "dev_first_pass_grading.json"


def answer_text(record: dict) -> str:
    """The visible answer, text blocks only, in the order the response carried them."""
    return "".join(
        b.get("text", "")
        for b in record["response"]["message"]["content"]
        if b.get("type") == "text"
    )


def grade_row(answer: str, chunks: Sequence[RetrievedChunk]) -> dict:
    """One answer graded against its own context. No label of any kind enters here."""
    cls = classify_response(answer)
    row: dict = {"response_class": cls, "units": []}
    if cls == ABSTAINED:
        return row
    blocks = [rendered_block(c) for c in chunks]
    block_tokens = [primary_tokens(b) for b in blocks]
    for unit in claim_units(answer):
        tokens = primary_tokens(unit)
        n = len(tokens)
        surfaces = sorted(tuple(s) for s in reference_surfaces(unit))
        overlap_max = max((window_score(tokens, bt) for bt in block_tokens), default=0.0)
        row["units"].append(
            {
                "text": unit,
                "n_tokens": n,
                "threshold": threshold_for(n),
                "n_surfaces": len(surfaces),
                "overlap_max": overlap_max,
                "score": score_unit(unit, chunks),
                "grounded": is_grounded(unit, chunks),
                "flagger_supported": unit_is_supported(unit, chunks),
            }
        )
    row["adversarial_verdict"] = row_verdict(answer)
    return row


def build() -> dict:
    store = load_chunk_store()
    contexts = {r["id"]: first_pass_chunks(r, store) for r in load_rows("dev")}
    per_row: dict[str, dict] = {}
    for tier in TIERS:
        path = RUNS_DIR / f"dev.raw.{tier}.jsonl"
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                custom_id = record["custom_id"]
                query_id = custom_id.split("__")[-1]
                per_row[custom_id] = grade_row(answer_text(record), contexts[query_id])

    def totals(ids: Sequence[str]) -> dict:
        rows = [per_row[i] for i in ids]
        answered = [r for r in rows if r["response_class"] != ABSTAINED]
        units = [u for r in answered for u in r["units"]]
        ungrounded = [u for u in units if not u["grounded"]]
        return {
            "rows": len(rows),
            "abstained": sum(1 for r in rows if r["response_class"] == ABSTAINED),
            "marker_variant": sum(1 for r in rows if r["response_class"] == MARKER_VARIANT),
            "answered_rows": len(answered),
            "answered_rows_with_zero_units": sum(1 for r in answered if not r["units"]),
            "claim_units": len(units),
            "ungrounded_units": len(ungrounded),
            "unsupported_claim_rate": round(len(ungrounded) / len(units), 6) if units else None,
            "short_units": sum(1 for u in units if u["n_tokens"] < SHORT_UNIT_LENGTH),
            "surface_carrying_units": sum(1 for u in units if u["n_surfaces"]),
            "units_turned_by_the_reference_condition": sum(
                1 for u in units if u["overlap_max"] >= u["threshold"] and not u["grounded"]
            ),
            "cross_implementation_disagreements": sum(
                1 for u in units if u["grounded"] != u["flagger_supported"]
            ),
        }

    all_ids = sorted(per_row)
    return {
        "description": (
            "The development first-pass grading, the freeze commit's basis. The committed grader "
            "run over the three committed development first-pass answer files and the committed "
            "context of each request. Reproducibility level 1: no model, no key, no network, no "
            "clock. Produced by python -m src.score.run_dev_grading."
        ),
        "produced_by": "python -m src.score.run_dev_grading",
        "written_to": "eval/dev_first_pass_grading.json",
        "thresholds": {
            "overlap_threshold": OVERLAP_THRESHOLD,
            "short_unit_length": SHORT_UNIT_LENGTH,
            "frozen": (
                "Frozen at this commit against the development first-pass generations. Neither "
                "moved. eval/generation_predictions.md section 5.2 allows at most one move, at "
                "this commit, on these generations alone, and only with its cause recorded."
            ),
        },
        "inputs": [
            "data/runs/dev.raw.haiku45.jsonl",
            "data/runs/dev.raw.sonnet5.jsonl",
            "data/runs/dev.raw.opus48.jsonl",
            "eval/dev_retrieval_results.json",
            "data/chunks/*.chunks.jsonl",
        ],
        "pooled": totals(all_ids),
        "per_tier": {
            tier: totals([i for i in all_ids if f"__{tier}__" in i]) for tier in TIERS
        },
        "rows": {i: per_row[i] for i in all_ids},
    }


def write(path=None):
    target = GRADING_PATH if path is None else path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    target.write_text(payload, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(f"wrote {write()}")
