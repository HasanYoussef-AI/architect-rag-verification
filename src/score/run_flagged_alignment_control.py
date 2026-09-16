"""The alignment control over the flagged units, and the grounding predicate's own null.

WHAT THIS MEASURES. For every claim unit the operational flagging pass marked unsupported on the
sealed set, two things: the best alignment the grader of record found for it against the first-pass
context it was actually flagged in, and the best alignment the same function finds for it against
every other sealed row's first-pass context. The second is a null. It says what this predicate
returns for a unit whose supporting source is, on the whole, not in the context being scored.

WHY IT EXISTS, AND IT IS NOT A CLASSIFIER. `docs/RESULTS.md` section 5 reported that zero flagged
units were rescued by the fetched context and explained it by asserting the flagged units were
paraphrase of blocks already present. That explanation had no measurement behind it. This artifact
is the measurement, and the first thing it establishes is that the obvious reading of the raw
figures is wrong: no flagged unit scores near zero against its own context, and neither does a
flagged unit scored against a context drawn from a different row. Multiset containment over a
window of the unit's own length picks up function words and shared domain vocabulary, so some
overlap is guaranteed between any claim about these frameworks and any passage from them. Without
the null beside it, a low absolute alignment reads as evidence of an absent source and is not.

Nothing here separates an absent source from a restatement of present text, nothing here is a
threshold, and nothing here decides anything. A threshold chosen on these observations would be
fitted under CLAUDE.md V15, and the distribution carries no natural cut to choose one at: the
figures under `continuity` are what say so.

WHAT IT CONSUMES, AND WHAT IT DOES NOT TOUCH. The committed flagged lists, the committed grading
results, the committed sealed queries with their first-pass top tens, and the committed chunk
store. The scoring function is `src.score.grounding.window_score`, imported and called, which is
the grader of record's own window comparison frozen at 15e31d5. No frozen module is modified and
no grading verdict is recomputed: the own-context figures are read out of the committed grading
artifact rather than re-derived, so this file cannot disagree with it about the measured side, and
tests/test_flagged_alignment_control.py asserts that read is exact.

THE REFERENCE CONDITION IS DELIBERATELY NOT APPLIED to the foreign side. `window_score` is the
overlap term alone, which is what `overlap_max` records on the measured side, so the two sides are
the same quantity. Applying the condition to a foreign context would ask whether a unit's
identifiers appear in an unrelated row's blocks, which is a question about identifier collision and
not about alignment.

REPRODUCIBILITY LEVEL 1 over committed inputs only. No model, no key, no network, no clock, no
randomness, no optional dependency. Two runs write identical bytes.

Run:  python -m src.score.run_flagged_alignment_control
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from src.generate.assemble import first_pass_chunks, load_chunk_store, load_rows
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import primary_tokens
from src.score.grounding import rendered_block, window_score

QUERY_SET = "test"
TIER_KEYS = ("haiku45", "sonnet5", "opus48")
EVAL_DIR = REPO_ROOT / "eval"
GRADING_PATH = EVAL_DIR / "test_grading_results.json"
CONTROL_PATH = EVAL_DIR / "test_flagged_alignment_control.json"

# Histogram bins over the unit interval. Fixed width rather than chosen on the data, because the
# measured distribution carries no natural cut and an uneven band drawn on a continuous
# distribution manufactures structure the data does not hold.
BIN_WIDTH = 0.05
N_BINS = 20


def flagged_path(tier: str):
    return EVAL_DIR / f"{QUERY_SET}_second_call_flagged.{tier}.json"


def quantile(values: Sequence[float], p: float) -> float:
    """Linear interpolation between order statistics, stated rather than inherited.

    Sorted ascending, index p*(n-1), interpolating between the two neighbouring values. Written
    out here rather than taken from a library so the artifact's quantiles have a definition a
    reviewer can check against the committed vectors without installing anything.
    """
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile over an empty sequence")
    if len(ordered) == 1:
        return ordered[0]
    position = p * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def summary(values: Sequence[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": round(ordered[0], 6),
        "q25": round(quantile(ordered, 0.25), 6),
        "median": round(quantile(ordered, 0.50), 6),
        "q75": round(quantile(ordered, 0.75), 6),
        "q95": round(quantile(ordered, 0.95), 6),
        "max": round(ordered[-1], 6),
        "mean": round(sum(ordered) / len(ordered), 6),
        "exact_zeros": sum(1 for v in ordered if v == 0.0),
    }


def histogram(values: Sequence[float]) -> dict[str, int]:
    """Counts in fixed 0.05 bins, keyed by the bin's lower edge. Empty bins are kept."""
    counts = [0] * N_BINS
    for value in values:
        index = min(int(value / BIN_WIDTH), N_BINS - 1)
        counts[index] += 1
    return {f"{index * BIN_WIDTH:.2f}": counts[index] for index in range(N_BINS)}


def largest_gaps(values: Sequence[float], take: int = 5) -> list[dict]:
    """The widest adjacent gaps in the sorted sequence, with what each would split.

    This is what answers whether a cut exists to read off the data. It is reported rather than
    acted on: a gap is evidence about the shape, not a threshold.
    """
    ordered = sorted(values)
    gaps = []
    for index in range(len(ordered) - 1):
        gaps.append(
            {
                "gap": round(ordered[index + 1] - ordered[index], 6),
                "below": round(ordered[index], 6),
                "above": round(ordered[index + 1], 6),
                "splits_below": index + 1,
                "splits_above": len(ordered) - index - 1,
            }
        )
    gaps.sort(key=lambda entry: (-entry["gap"], entry["below"]))
    return gaps[:take]


def load_flagged() -> tuple[list[dict], dict]:
    """The flagged population, in a fixed order, with the funnel that produced it.

    Ordered by tier in the committed tier order, then by query id, then by the unit's position in
    its row's committed flagged list, so the artifact's row order is a property of the inputs and
    not of dictionary iteration.
    """
    grading = json.loads(GRADING_PATH.read_text(encoding="utf-8"))
    units: list[dict] = []
    funnel = {
        "starting_row_tier_pairs": 0,
        "removed_corrective_pass_did_not_fire": 0,
        "fired_row_tier_pairs": 0,
        "fired_pairs_flagging_nothing": 0,
        "fired_pairs_contributing_at_least_one_unit": 0,
        "flagged_units": 0,
        "not_fired_rows_by_tier": {},
    }

    for tier in TIER_KEYS:
        artifact = json.loads(flagged_path(tier).read_text(encoding="utf-8"))
        population = artifact["population"]
        funnel["starting_row_tier_pairs"] += population["starting_rows"]
        funnel["removed_corrective_pass_did_not_fire"] += (
            population["starting_rows"] - population["fired"]
        )
        funnel["fired_row_tier_pairs"] += population["fired"]
        funnel["not_fired_rows_by_tier"][tier] = list(population["not_fired"])

        rows = sorted(artifact["rows"].values(), key=lambda row: row["query_id"])
        for row in rows:
            if row["n_flagged"] == 0:
                funnel["fired_pairs_flagging_nothing"] += 1
                continue
            funnel["fired_pairs_contributing_at_least_one_unit"] += 1
            graded = grading["rows"]["raw"][tier][row["query_id"]]
            by_text: dict[str, list[dict]] = {}
            for unit in graded["units"]:
                by_text.setdefault(unit["text"], []).append(unit)
            for position, text in enumerate(row["flagged_units"]):
                matches = by_text.get(text)
                if matches is None:
                    raise KeyError(
                        f"{tier}/{row['query_id']}: a flagged unit is absent from the committed "
                        "grading artifact's raw units for the same row"
                    )
                if len(matches) > 1:
                    raise ValueError(
                        f"{tier}/{row['query_id']}: a flagged unit's text occurs more than once in "
                        "the row's claim units, so the join is ambiguous"
                    )
                graded_unit = matches[0]
                units.append(
                    {
                        "tier": tier,
                        "query_id": row["query_id"],
                        "position_in_flagged_list": position,
                        "text": text,
                        "n_tokens": graded_unit["n_tokens"],
                        "n_surfaces": graded_unit["n_surfaces"],
                        "threshold": graded_unit["threshold"],
                        "own_overlap_max": graded_unit["overlap_max"],
                        "own_score": graded_unit["score"],
                        "own_grounded": graded_unit["grounded"],
                        "flagger_supported": graded_unit["flagger_supported"],
                    }
                )
    funnel["flagged_units"] = len(units)
    return units, funnel


def load_foreign_blocks() -> tuple[dict[str, tuple[str, ...]], dict[str, list[str]]]:
    """The sealed rows' first-pass blocks, tokenised once, keyed by chunk id.

    SEPARATE FROM THE SCORING ON PURPOSE. Every file this module opens is opened here or in
    load_flagged, and window_score opens nothing, so a test that patches open around these two
    functions covers the producer's whole file surface rather than a sample of it. That is why the
    read-guard test in tests/test_flagged_alignment_control.py is both cheap and total.
    """
    store = load_chunk_store()
    rows = {row["id"]: row for row in load_rows(QUERY_SET)}

    row_block_ids: dict[str, tuple[str, ...]] = {}
    block_tokens: dict[str, list[str]] = {}
    for query_id in sorted(rows):
        chunks = first_pass_chunks(rows[query_id], store)
        row_block_ids[query_id] = tuple(chunk.chunk_id for chunk in chunks)
        for chunk in chunks:
            if chunk.chunk_id not in block_tokens:
                block_tokens[chunk.chunk_id] = primary_tokens(rendered_block(chunk))
    return row_block_ids, block_tokens


def foreign_alignments(
    units: list[dict],
    row_block_ids: dict[str, tuple[str, ...]],
    block_tokens: dict[str, list[str]],
) -> dict:
    """Every unit against every other sealed row's first-pass context. No sample.

    Each unit is scored once against each DISTINCT rendered block in the sealed set, and a row's
    figure is the maximum over that row's blocks. The sealed rows' first-pass tens overlap, so the
    distinct block count is well below fifty times ten, and the shortcut is a memoisation rather
    than an approximation: the maximum over a row's blocks is the same number whichever order the
    blocks were scored in. tests/test_flagged_alignment_control.py recomputes a fixed sample of
    units naively, block by block with no cache and from its own reading of the chunk store, and
    asserts the same values.
    """
    row_ids = sorted(row_block_ids)

    for unit in units:
        unit_tokens = primary_tokens(unit["text"])
        cache: dict[str, float] = {}
        per_row: dict[str, float] = {}
        for query_id in row_ids:
            if query_id == unit["query_id"]:
                continue
            best = 0.0
            for chunk_id in row_block_ids[query_id]:
                score = cache.get(chunk_id)
                if score is None:
                    score = window_score(unit_tokens, block_tokens[chunk_id])
                    cache[chunk_id] = score
                if score > best:
                    best = score
            per_row[query_id] = best
        values = [per_row[key] for key in sorted(per_row)]
        unit["foreign_rows"] = len(values)
        unit["foreign_overlap_max_by_row"] = {key: per_row[key] for key in sorted(per_row)}
        unit["foreign_max"] = max(values)
        unit["foreign_median"] = round(quantile(values, 0.50), 6)
        unit["foreign_mean"] = round(sum(values) / len(values), 6)
        unit["beats_every_foreign_row"] = unit["own_overlap_max"] > unit["foreign_max"]
        unit["beats_its_foreign_mean"] = unit["own_overlap_max"] > unit["foreign_mean"]

    return {
        "sealed_rows": len(row_ids),
        "distinct_rendered_blocks_across_the_sealed_first_passes": len(block_tokens),
        "chunk_slots_across_the_sealed_first_passes": sum(
            len(value) for value in row_block_ids.values()
        ),
    }


def build() -> dict:
    units, funnel = load_flagged()
    row_block_ids, block_tokens = load_foreign_blocks()
    coverage = foreign_alignments(units, row_block_ids, block_tokens)

    own = [unit["own_overlap_max"] for unit in units]
    own_score = [unit["own_score"] for unit in units]
    null = [
        value
        for unit in units
        for value in unit["foreign_overlap_max_by_row"].values()
    ]

    null_q95 = quantile(null, 0.95)
    beats = [unit for unit in units if unit["beats_every_foreign_row"]]

    per_tier: dict[str, dict] = {}
    for tier in TIER_KEYS:
        subset = [unit for unit in units if unit["tier"] == tier]
        per_tier[tier] = {
            "flagged_units": len(subset),
            "own_overlap_max": summary([unit["own_overlap_max"] for unit in subset]),
            "own_score": summary([unit["own_score"] for unit in subset]),
            "beats_every_foreign_row": sum(1 for unit in subset if unit["beats_every_foreign_row"]),
            "does_not_beat_every_foreign_row": sum(
                1 for unit in subset if not unit["beats_every_foreign_row"]
            ),
            "at_or_below_the_pooled_null_q95": sum(
                1 for unit in subset if unit["own_overlap_max"] <= null_q95
            ),
            "above_the_pooled_null_q95": sum(
                1 for unit in subset if unit["own_overlap_max"] > null_q95
            ),
        }

    zeros = [unit for unit in units if unit["own_score"] == 0.0]
    condition_bit = [unit for unit in units if unit["own_score"] != unit["own_overlap_max"]]

    return {
        "description": (
            "The best alignment the grader of record finds for every flagged claim unit of the "
            "sealed run, against the first-pass context it was flagged in and against every other "
            "sealed row's first-pass context. The second is the null this predicate returns when "
            "the supporting source is, on the whole, not in the context being scored."
        ),
        "produced_by": "python -m src.score.run_flagged_alignment_control",
        "written_to": str(CONTROL_PATH.relative_to(REPO_ROOT)),
        "query_set": QUERY_SET,
        "reproducibility_level": 1,
        "artifact_class": (
            "Instrument measurement, not a condition result. eval/test_retrieval_results.json, "
            "eval/test_layer_results.json and eval/test_grading_results.json are the outputs of "
            "the three measured conditions. This file is a property of the grading predicate, "
            "measured over a population one of them defines, and it is pinned separately for that "
            "reason rather than folded into the three."
        ),
        "decides_nothing": (
            "No threshold is chosen here and none is available. A threshold chosen after seeing "
            "these observations is fitted under CLAUDE.md V15, and the figures under `continuity` "
            "record that the measured distribution carries no natural cut to read one off. "
            "Nothing in this file separates a claim whose source is absent from a claim that "
            "restates present text in different words; see `what_this_cannot_settle`."
        ),
        "the_instrument": (
            "src.score.grounding.window_score, the grader of record's own window comparison, "
            "frozen at 15e31d5 and imported rather than reimplemented. It is best multiset "
            "containment of the unit's primary tokens in any window of the unit's own length over "
            "one rendered block. The reference condition is not applied on either side, so both "
            "sides are the same quantity that the grading artifact records as overlap_max."
        ),
        "own_side_is_read_not_recomputed": (
            "own_overlap_max, own_score, own_grounded, n_tokens, n_surfaces and threshold are read "
            "out of eval/test_grading_results.json under rows.raw.<tier>.<query_id>.units[], "
            "joined on the unit's exact text. This file therefore cannot disagree with the grading "
            "artifact about the measured side. The join is total at the flagged population and the "
            "unit texts within a row are unique, both asserted in the test file."
        ),
        "sampling_decision": {
            "decision": "enumerated, not sampled",
            "what_was_enumerated": (
                "every flagged unit against every sealed row other than its own, 49 foreign rows "
                "per unit, with no draw and no seed."
            ),
            "reason": (
                "CLAUDE.md V5 prefers an exhaustive audit to a sample where the population can be "
                "enumerated, and this one can. The sealed first-pass tens hold "
                f"{coverage['distinct_rendered_blocks_across_the_sealed_first_passes']} distinct "
                f"rendered blocks across {coverage['chunk_slots_across_the_sealed_first_passes']} "
                "chunk slots, so the whole enumeration is one pass over each unit against each "
                "distinct block."
            ),
            "supersedes": (
                "An uncommitted earlier form of this measurement drew five foreign rows per unit. "
                "A sampled maximum is an underestimate of the enumerated maximum, so the sampled "
                "count of units beating every foreign row was an upper bound on the enumerated "
                "one. The enumerated figure below is the measurement of record and the sampled "
                "figure is not carried, because a number with a committed producer and a number "
                "without one do not belong beside each other."
            ),
        },
        "foreign_context_caveat": (
            "A foreign context is not guaranteed to be free of support for the unit scored against "
            "it. The corpus is bounded and the sealed rows are drawn from it, so some foreign row "
            "will occasionally hold a block that does support a given claim. The null is therefore "
            "an upper bound on chance alignment rather than a clean null, and the separation "
            "between the measured side and the null is at least as large as this file reports and "
            "not smaller. A reader of any figure under `null_distribution` meets this sentence "
            "first by design."
        ),
        "what_this_cannot_settle": (
            "Three limits, each of which could be over-read. First, the predicate is lexical and "
            "punishes paraphrase, which the freeze commit already recorded, so a low alignment is "
            "consistent with an absent source and with a faithful paraphrase alike and this file "
            "cannot part them. Second, a high alignment says a unit shares a large fraction of its "
            "tokens with some window of some present block; it does not say that block states the "
            "proposition the unit asserts. Third, the null answers what this predicate returns "
            "when the source is elsewhere; it says nothing about whether the corpus holds support "
            "for any particular unit."
        ),
        "inputs": {
            "flagged_lists": [
                str(flagged_path(tier).relative_to(REPO_ROOT)) for tier in TIER_KEYS
            ],
            "grading_results": str(GRADING_PATH.relative_to(REPO_ROOT)),
            "sealed_queries": f"eval/{QUERY_SET}_queries.jsonl",
            "chunk_store": "data/chunks/*.chunks.jsonl",
            "no_model_no_key_no_network": True,
        },
        "population": funnel,
        "coverage": coverage,
        "own_distribution": {
            "note": (
                "overlap_max and score of the flagged units against their own first-pass context, "
                "read from the grading artifact. score is the grader of record's value with the "
                "reference condition applied; overlap_max is the overlap term alone."
            ),
            "pooled_overlap_max": summary(own),
            "pooled_score": summary(own_score),
            "pooled_overlap_max_histogram": histogram(own),
            "pooled_score_histogram": histogram(own_score),
        },
        "null_distribution": {
            "caveat": (
                "An upper bound on chance alignment, not a clean null. See foreign_context_caveat."
            ),
            "pairs": len(null),
            "pairs_note": (
                "one per (flagged unit, foreign sealed row) pair, each the maximum over that row's "
                "ten first-pass blocks."
            ),
            "summary": summary(null),
            "histogram": histogram(null),
            "reading": (
                "The predicate returns no value near zero for in-domain text. That no flagged unit "
                "scores near zero against its own context is therefore a property of this ruler "
                "and not a fact about the units, and any reading of the measured figures has to "
                "carry this distribution beside them."
            ),
        },
        "paired_result": {
            "test": (
                "per unit, the unit's own overlap_max against the maximum over all 49 foreign "
                "rows. A per-unit comparison, not a unit judged against a pooled quantile "
                "assembled partly from other units' scores."
            ),
            "beats_every_foreign_row": len(beats),
            "does_not_beat_every_foreign_row": len(units) - len(beats),
            "beats_its_own_foreign_mean": sum(1 for unit in units if unit["beats_its_foreign_mean"]),
            "of": len(units),
            "reading": (
                "For the units that beat every foreign row the measurement is consistent with "
                "paraphrase of blocks already present. For those that do not it gives no reason to "
                "prefer that reading over an absent source. Neither group is settled by it."
            ),
        },
        "pooled_quantile_cut": {
            "note": (
                "A second cut, reported beside the paired test and weaker than it, because a unit "
                "is judged here against a quantile assembled partly from other units' scores. It "
                "is a descriptive ruler mark and not a threshold."
            ),
            "null_q95": round(null_q95, 6),
            "above": sum(1 for unit in units if unit["own_overlap_max"] > null_q95),
            "at_or_below": sum(1 for unit in units if unit["own_overlap_max"] <= null_q95),
            "of": len(units),
        },
        "continuity": {
            "note": (
                "Whether a cut can be read off the measured distribution rather than invented. "
                "Reported, not acted on."
            ),
            "overlap_max_range": round(max(own) - min(own), 6),
            "overlap_max_min": round(min(own), 6),
            "overlap_max_max": round(max(own), 6),
            "overlap_max_largest_gaps": largest_gaps(own),
            "score_largest_gaps_excluding_the_exact_zeros": largest_gaps(
                [unit["own_score"] for unit in units if unit["own_score"] > 0.0]
            ),
            "reading": (
                "overlap_max is continuous: its largest adjacent gap is a small fraction of its "
                "range, so any absent-versus-restated band would have to be invented rather than "
                "read off. score is bimodal, and score_bimodality below records that the low mode "
                "is the reference condition rather than a fact about sources."
            ),
        },
        "score_bimodality": {
            "note": (
                "score falls below overlap_max only where the reference condition rejected blocks "
                "the overlap term would have scored. A classifier thresholding on score would read "
                "a signal about identifiers as a signal about sources."
            ),
            "units_with_score_exactly_zero": len(zeros),
            "all_of_them_carry_a_reference_surface": all(unit["n_surfaces"] > 0 for unit in zeros),
            "their_overlap_max_min": round(min(unit["own_overlap_max"] for unit in zeros), 6),
            "their_overlap_max_max": round(max(unit["own_overlap_max"] for unit in zeros), 6),
            "their_overlap_max_sorted": sorted(
                round(unit["own_overlap_max"], 6) for unit in zeros
            ),
            "units_where_score_is_below_overlap_max": len(condition_bit),
            "of_those_score_is_exactly_zero": sum(1 for unit in condition_bit if unit["own_score"] == 0.0),
            "all_of_those_carry_a_reference_surface": all(
                unit["n_surfaces"] > 0 for unit in condition_bit
            ),
            "units_carrying_no_reference_surface": sum(1 for unit in units if unit["n_surfaces"] == 0),
            "and_for_every_one_of_those_score_equals_overlap_max": all(
                unit["own_score"] == unit["own_overlap_max"]
                for unit in units
                if unit["n_surfaces"] == 0
            ),
        },
        "tier_heterogeneity": {
            "note": (
                "The tiers do not behave alike and the pooled figures describe no tier. Every "
                "pooled number in this file should be read with this block beside it."
            ),
            "per_tier": per_tier,
            "share_of_the_population_from_the_largest_tier": round(
                max(per_tier[tier]["flagged_units"] for tier in TIER_KEYS) / len(units), 6
            ),
        },
        "units": units,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="replace an existing control artifact. Overwriting a committed measurement is a "
             "correction and is logged; without this the runner refuses.",
    )
    parser.add_argument("--stdout", action="store_true", help="write to stdout and not to disk")
    args = parser.parse_args(argv)

    artifact = build()
    payload = json.dumps(artifact, indent=1, ensure_ascii=False) + "\n"

    if args.stdout:
        sys.stdout.write(payload)
        return 0

    if CONTROL_PATH.exists() and not args.overwrite:
        print(
            f"{CONTROL_PATH} already exists. A committed measurement is not silently replaced; "
            "re-running over one takes --overwrite, whose use is logged in the commit message and "
            "the session log.",
            file=sys.stderr,
        )
        return 1

    # newline="\n" pins LF on every platform; see the note in src/score/run_retrieval_eval.py.
    CONTROL_PATH.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {CONTROL_PATH}")
    print(json.dumps(artifact["paired_result"], indent=1))
    print(json.dumps(artifact["null_distribution"]["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
