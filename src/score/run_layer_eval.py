"""Produce the layer retrieval results artifact, the companion to the first-pass results.

HARNESS SIDE, NOT LAYER SIDE. This module reads gold, and that is not a firewall breach: the
firewall binds the operational layer's runtime inputs, not the measurement. The separation is kept
by construction rather than by care. Everything under src/complete/ is called through its committed
surface and is handed only a query string and RetrievedChunk values; nothing in this file passes a
gold slot, a stratum label or a row identifier into the layer, and the layer has no parameter that
could receive one.

TWO INDEPENDENT MEMBERSHIP IMPLEMENTATIONS, DELIBERATELY. The layer decides whether a unit is in
its context set with src/complete/absence.py's lexical rule. This module scores what the final
context satisfies with src/score/slots.py, the grader of record, which is a separate implementation
of the same predicate reached through slot_satisfaction. A disagreement between them is a real
finding rather than a formatting difference, and scoring through the grader is what keeps Rule 9's
separation between the thing being measured and the thing measuring it.

Reproducibility level 1. Inputs are the committed first-pass results artifact, the committed chunk
store and the committed unit index. No model, no key, no network, no optional dependency: the
corrective pass is deterministic resolution and direct fetch, never re-embedding or re-ranking, so
the artifact re-derives byte for byte in a default environment with the build-only embed group
absent.

THE TWO CONDITIONS NEVER SHARE A METRIC LABEL. The first pass keeps Recall@10 against the fused top
10, exactly as frozen. The layer condition reports recovered-passage recall over the final context
set, with that set's size beside it, and reports no Precision@10, MRR or NDCG at all, because k is
not ten and the fetched units carry no rank order comparable to a fused ranking.

Run:  python -m src.score.run_layer_eval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict

from src.complete.absence import context_absence_fires, non_resolution_fires, query_reference_absent
from src.complete.augment import augment, load_fetch_store
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.slots import slot_satisfaction

EVAL = REPO_ROOT / "eval"
FIRST_PASS_RESULTS = EVAL / "test_retrieval_results.json"
LAYER_RESULTS = EVAL / "test_layer_results.json"

DESCRIPTION = (
    "Layer retrieval results for the sealed query set: the same first pass, followed by the "
    "deterministic corrective pass in src/complete/. Companion to eval/test_retrieval_results.json, "
    "which is quoted here unchanged and never recomputed. Produced with no model, no key and no "
    "optional dependency, so every figure re-derives from committed files. THE TWO CONDITIONS "
    "NEVER SHARE A METRIC LABEL: the first pass reports Recall@10 over the fused top 10, the layer "
    "condition reports recovered-passage recall over the final context set with that set's size "
    "beside it, and the layer condition reports no Precision@10, MRR or NDCG because k is not ten "
    "and the fetched units carry no comparable rank order. Aggregates are macro-averages over "
    "queries. Adversarial rows are carried and marked not computed, and aggregates exclude them by "
    "that marker rather than by stratum name."
)

MEASUREMENT_CONVENTION = {
    "first_pass": "Recall@10, Precision@10, MRR and NDCG@10 against the fused top 10 of chunks, "
                  "as defined in PREREGISTRATION.md and frozen in eval/test_retrieval_results.json. "
                  "Quoted unchanged.",
    "layer_condition": "recovered-passage recall over the final context set, with the final "
                       "context set size reported per row beside it.",
    "why_no_rank_metrics_for_the_layer": "Under augmentation the context set is not ten chunks, and "
                                         "the fetched units carry no rank order comparable to a "
                                         "fused ranking, so every rank-based figure would be about "
                                         "arithmetic rather than about the layer. A precision that "
                                         "fell purely because k grew would be the clearest case.",
    "term_provenance": "recovered-passage recall is PREREGISTRATION.md's own term, from the "
                       "null-interpretation clause written before any result existed.",
    "scored_by": "src/score/slots.py, the grader of record, a separate implementation from the "
                 "layer's own membership rule in src/complete/absence.py.",
}

AUGMENTATION_POLICY = {
    "trigger": "predicate a, context absence: any resolved unit no retrieved chunk belongs to.",
    "policy": "augmentation only. The first-pass ten are never removed, never reordered and never "
              "truncated; the chunks of every absent resolved unit are appended after them.",
    "uniform": "Applied identically to all fifty rows including the adversarial stratum. The layer "
               "cannot condition on stratum, because type and subtype are barred, so no "
               "stratum-varying policy is implementable without breaking the firewall.",
    "no_bound": "No bound on augmentation volume is applied. eval/layer_predictions.md section 5 "
                "records the absence of a bound as a named condition: the ranks carrying each "
                "recovery were known when that file was written, so a bound chosen after them "
                "would be fitted to its own observations. A future bound is a cost decision, set "
                "from the cost budget, shipping with the recoveries it removes reported by row.",
    "predicate_b_is_a_diagnostic": "The narrow query-reference predicate is reported per row and is "
                                   "not the trigger. Measured, it is silent on three of the ten "
                                   "rows where the layer recovers a missing gold unit, test_10, "
                                   "test_19 and test_41, whose recoveries come from references "
                                   "printed in retrieved text or in a unit_label rather than in the "
                                   "query.",
}


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_pass_recall(row: dict):
    metrics = row.get("metrics")
    return None if metrics is None else metrics["recall_at_10"]


def score_row(row: dict, store) -> dict:
    """One row through the layer. `row` is the committed first-pass record."""
    first_pass = [store.chunks[chunk_id] for chunk_id in row["top10"]]
    result = augment(row["query"], first_pass, store)

    context_ids = [chunk.chunk_id for chunk in result.context]
    gold_slots = row["gold_slots"]
    after = slot_satisfaction(context_ids, gold_slots)
    before = row["slot_satisfaction"]

    if gold_slots:
        recovered_recall = sum(1 for hit in after if hit.satisfied) / len(gold_slots)
        recovered_units = sorted(
            unit
            for index, slot in enumerate(gold_slots)
            if not before[index]["satisfied"]
            for unit in slot
            if any(chunk_id == unit or chunk_id.startswith(unit + "#") for chunk_id in context_ids)
        )
        note = None
    else:
        recovered_recall = None
        recovered_units = []
        note = "not computed; gold is empty per PREREGISTRATION.md"

    report = result.report
    return {
        "id": row["id"],
        "type": row["type"],
        "subtype": row["subtype"],
        "first_pass_slot_satisfaction": before,
        "first_pass_recall_at_10": _first_pass_recall(row),
        "context_set_size": result.size,
        "fetched_units": list(result.fetched_units),
        "fetched_chunk_count": len(result.fetched_chunks),
        "signals": {
            "context_absence": {
                "fired": context_absence_fires(report),
                "absent_units": list(report.absent_units),
            },
            "query_reference_absence": {
                "fired": query_reference_absent(report),
                "absent_units": list(report.query_absent_units),
            },
            "non_resolution": {
                "fired": non_resolution_fires(report),
                "surfaces": sorted({ref.surface for ref in report.unresolved_references}),
            },
        },
        "reference_counts": {
            "surfaces": len(report.references),
            "resolved_units": len(report.resolved_units),
            "dropped_external": len(report.dropped_references),
        },
        "recovered_passage_recall": recovered_recall,
        "recovered_units": recovered_units,
        "metrics_note": note,
    }


def aggregate(rows: list[dict]) -> dict:
    """Macro-average over queries, excluding gold-empty rows by their marker.

    Both conditions are averaged over the same denominator, so the pair is comparable even though
    the two figures are not the same metric and never carry the same label.
    """
    usable = [row for row in rows if row["recovered_passage_recall"] is not None]
    sizes = sorted(row["context_set_size"] for row in rows)
    out = {
        "n_queries": len(usable),
        "n_rows_including_gold_empty": len(rows),
        "context_set_size_min": sizes[0],
        "context_set_size_median": sizes[len(sizes) // 2],
        "context_set_size_max": sizes[-1],
        "context_set_size_mean": sum(sizes) / len(sizes),
    }
    if usable:
        out["recall_at_10_first_pass"] = sum(
            row["first_pass_recall_at_10"] for row in usable
        ) / len(usable)
        out["recovered_passage_recall_layer"] = sum(
            row["recovered_passage_recall"] for row in usable
        ) / len(usable)
        out["delta"] = out["recovered_passage_recall_layer"] - out["recall_at_10_first_pass"]
    return out


def score_predictions(scored: list[dict]) -> list[dict]:
    """Every prediction eval/layer_predictions.md makes about this measurement, held or contradicted.

    Scored mechanically from the rows above rather than read off by eye, and the one contradicted
    prediction is recorded as contradicted. The predictions file is not corrected: a contradicted
    prediction that gets edited is not a prediction.
    """
    by_id = {row["id"]: row for row in scored}
    by_stratum = defaultdict(list)
    for row in scored:
        by_stratum[f"{row['type']}/{row['subtype']}"].append(row)

    def recall(stratum, key):
        rows = [r for r in by_stratum[stratum] if r["recovered_passage_recall"] is not None]
        return sum(r[key] for r in rows) / len(rows)

    def recovered(row_id):
        return by_id[row_id]["recovered_units"]

    out = []

    clean = "multi_hop/eu_internal_xref"
    out.append({
        "section": "6.1",
        "prediction": "Clean multi-hop recovers exactly test_10 and test_19; zero on test_13, "
                      "test_16 and test_18; stratum 0.7917 to 0.8750.",
        "verdict": "held" if (
            recovered("test_10") == ["eu_ai_act:art_49"]
            and recovered("test_19") == ["eu_ai_act:art_16"]
            and not recovered("test_13") and not recovered("test_16") and not recovered("test_18")
            and round(recall(clean, "recovered_passage_recall"), 4) == 0.875
        ) else "contradicted",
        "observed": {
            "test_10": recovered("test_10"),
            "test_19": recovered("test_19"),
            "test_13": recovered("test_13"),
            "test_16": recovered("test_16"),
            "test_18": recovered("test_18"),
            "stratum_first_pass": round(recall(clean, "first_pass_recall_at_10"), 4),
            "stratum_layer": round(recall(clean, "recovered_passage_recall"), 4),
        },
        "note": "The three zero rows are a permanent limit of the design rather than a tuning "
                "shortfall. No pointer to the missing unit exists anywhere in their retrieved "
                "context, and the only route that could reach it is the inverse citation walk the "
                "firewall bars. It ships as a what-still-fails entry.",
    })

    action = "multi_hop/action_subcategory"
    out.append({
        "section": "6.2",
        "prediction": "Action-to-parent recovers nothing on test_39, test_40 and test_42, and "
                      "recovers all three carriers on test_41; stratum 0.0000 to 0.2500.",
        "verdict": "held" if (
            not recovered("test_39") and not recovered("test_40") and not recovered("test_42")
            and recovered("test_41") == ["nist_ai_100_1:sub_MEASURE_2.2",
                                         "nist_ai_600_1:sub_MEASURE_2.2",
                                         "nist_playbook:sub_MEASURE_2.2"]
            and round(recall(action, "recovered_passage_recall"), 4) == 0.25
        ) else "contradicted",
        "observed": {
            "test_41": recovered("test_41"),
            "stratum_first_pass": round(recall(action, "first_pass_recall_at_10"), 4),
            "stratum_layer": round(recall(action, "recovered_passage_recall"), 4),
        },
        "required_reporting_form": "Zero of four by any parent-derivation route, one of four by "
                                   "sibling-label resolution. The mechanism on test_41: the first "
                                   "pass returned three Playbook sibling blocks of the gold "
                                   "subcategory at ranks 2, 3 and 5, whose unit_label values begin "
                                   "MEASURE 2.2; R_SUB extracts that printed citation from the "
                                   "label and composes three candidates, all of which resolve and "
                                   "all of which are the slot's acceptable units. No action "
                                   "identifier is read and no legend is applied. The bare sentence "
                                   "that the layer recovers an action-to-parent row is false about "
                                   "the route that matters and is not used.",
    })

    near_miss_rows = [r for r in scored if r["type"] == "near_miss"]
    flag_fired = sorted(r["id"] for r in near_miss_rows if r["signals"]["context_absence"]["fired"])
    recovered_rows = sorted(r["id"] for r in near_miss_rows if r["recovered_units"])
    out.append({
        "section": "6.3",
        "prediction": "The context-absence flag fires on exactly seven near-miss rows and does not "
                      "fire on test_45.",
        "verdict": "contradicted",
        "observed": {
            "flag_fired_on": flag_fired,
            "recovered_on": recovered_rows,
            "block_clusters_first_pass": round(
                recall("near_miss/block_clusters", "first_pass_recall_at_10"), 4),
            "block_clusters_layer": round(
                recall("near_miss/block_clusters", "recovered_passage_recall"), 4),
            "near_duplicate_first_pass": round(
                recall("near_miss/near_duplicate", "first_pass_recall_at_10"), 4),
            "near_duplicate_layer": round(
                recall("near_miss/near_duplicate", "recovered_passage_recall"), 4),
        },
        "contradiction": "The flag fires on all eight. The prediction was written from the gold's "
                         "point of view, anchor retrieved therefore nothing missing; from the "
                         "layer's side test_45's query names four real units and three of them are "
                         "genuinely absent from its context set. Three candidate predicates were "
                         "measured over all fifty rows before any test was written, any resolved "
                         "unit absent, only units the query named, and only the most specific query "
                         "referent, and all three fire on all eight. No predicate confined to the "
                         "readable surface separates test_45 without knowing which of the four "
                         "units is the answer, which is the gold. eval/layer_predictions.md is left "
                         "uncorrected: a contradicted prediction is recorded as contradicted.",
        "required_reporting_form": "Not detection at seven of seven with no false positives. The "
                                   "flag fires on all eight rows and does not discriminate the "
                                   "crowded-out rows from the satisfied one, because carriers the "
                                   "query names are genuinely absent even where gold is satisfied. "
                                   "What the layer delivers on this stratum is recovery, seven of "
                                   "seven on the missed rows, and that recovery is a property of "
                                   "how the queries were written: each names the document, the "
                                   "block type and the subcategory identifier, so composing the "
                                   "three yields the row's gold unit id. The retrieval-path finding "
                                   "stands unchanged: on the seven missed rows neither the anchor "
                                   "nor its designated competitor is in the top 10, so the stratum "
                                   "measured crowding by other subcategories' blocks under the same "
                                   "generic heading rather than the pairwise displacement its rows "
                                   "predicted, and a recovery figure of seven of seven does not "
                                   "retire that finding.",
    })

    single_hop = [r for r in scored if r["type"] == "single_hop"]
    deltas = {
        r["id"]: r["recovered_passage_recall"] - r["first_pass_recall_at_10"] for r in single_hop
    }
    out.append({
        "section": "6.4",
        "prediction": "Single-hop completeness delta is exactly zero on 18 of 18 under "
                      "augmentation only.",
        "verdict": "held" if all(delta == 0 for delta in deltas.values()) and len(deltas) == 18
        else "contradicted",
        "observed": {"n_rows": len(deltas), "distinct_deltas": sorted(set(deltas.values()))},
        "note": "Exact rather than approximate, and the invariant is what makes it so: every row is "
                "already at recall 1, and no committed gold chunk can leave a context set under "
                "augmentation only. Any non-zero value would be a defect in the corrective pass "
                "rather than a result.",
    })

    fabricated = ["test_04", "test_05", "test_06", "test_07"]
    silent = ["test_01", "test_02", "test_03", "test_08"]
    out.append({
        "section": "6.5",
        "prediction": "All four fabricated identifiers resolve to nothing; the three ISO rows and "
                      "the one out-of-domain row carry no citation-formed reference at all.",
        "verdict": "held" if (
            all(by_id[r]["signals"]["non_resolution"]["fired"] for r in fabricated)
            and not any(by_id[r]["signals"]["non_resolution"]["fired"] for r in silent)
        ) else "contradicted",
        "observed": {
            r: by_id[r]["signals"]["non_resolution"]["surfaces"] for r in fabricated + silent
        },
        "note": "A deterministic abstention signal reached from the query text and the committed "
                "unit index alone, available on the fabricated-provision half of the stratum and "
                "contributing nothing to the other half. That asymmetry is a stated limit, "
                "predicted rather than discovered.",
    })

    overall = aggregate(scored)
    out.append({
        "section": "6.6",
        "prediction": "Overall 0.6786 first pass to 0.8929 layer condition over the 42 "
                      "gold-bearing rows.",
        "verdict": "held" if (
            round(overall["recall_at_10_first_pass"], 4) == 0.6786
            and round(overall["recovered_passage_recall_layer"], 4) == 0.8929
        ) else "contradicted",
        "observed": {
            "n_queries": overall["n_queries"],
            "recall_at_10_first_pass": round(overall["recall_at_10_first_pass"], 4),
            "recovered_passage_recall_layer": round(overall["recovered_passage_recall_layer"], 4),
        },
        "attribution": "The delta is dominated by the near-miss stratum, which contributes seven of "
                       "the ten recovered rows and whose recovery is a query-construction property. "
                       "Reported without that attribution the figure would overstate what the layer "
                       "does. The clean multi-hop delta on two rows recovered from printed forward "
                       "citations is the figure that reflects the completeness surface as "
                       "docs/METHODOLOGY.md describes it.",
    })
    return out


def build() -> dict:
    store = load_fetch_store()
    source = json.loads(FIRST_PASS_RESULTS.read_text(encoding="utf-8"))
    scored = [score_row(row, store) for row in source["retrieval"]]

    by_stratum = defaultdict(list)
    for row in scored:
        by_stratum[f"{row['type']}/{row['subtype']}"].append(row)

    drop_events = sum(row["reference_counts"]["dropped_external"] for row in scored)
    drop_rows = sum(1 for row in scored if row["reference_counts"]["dropped_external"])
    adversarial = [row for row in scored if row["type"] == "adversarial"]
    # Two quantities, two names. The absent-unit count is what eval/layer_predictions.md section 4
    # tabulates; the chunk count is what actually reaches the model, and it is larger wherever a
    # fetched unit is split. Reporting either under the other's name would be a field carrying a
    # quantity its name does not claim.
    adversarial_units = sorted(
        len(row["signals"]["context_absence"]["absent_units"]) for row in adversarial
    )
    adversarial_chunks = sorted(row["fetched_chunk_count"] for row in adversarial)

    return {
        "description": DESCRIPTION,
        "produced_by": "python -m src.score.run_layer_eval",
        "reproducibility_level": 1,
        "reproducibility_claim": (
            "The layer condition re-derives from committed files alone: no model, no key, no "
            "network and no optional dependency. The first pass is read from "
            "eval/test_retrieval_results.json rather than recomputed, and the corrective pass is "
            "deterministic reference resolution against eval/corpus_unit_index.json followed by "
            "direct fetch from data/chunks/*.chunks.jsonl. Verified by running this module in a "
            "default environment with the build-only embed group absent."
        ),
        "query_set": source["query_set"],
        "first_pass_source": {
            "path": "eval/test_retrieval_results.json",
            "sha256": _sha256(FIRST_PASS_RESULTS),
            "quoted_unchanged": "first_pass_slot_satisfaction and first_pass_recall_at_10 are "
                                "copied from that artifact and are never recomputed here.",
        },
        "layer_components": [
            "src/complete/references.py",
            "src/complete/absence.py",
            "src/complete/augment.py",
        ],
        "measurement_convention": MEASUREMENT_CONVENTION,
        "augmentation_policy": AUGMENTATION_POLICY,
        "layer": scored,
        "aggregates": {
            "overall": aggregate(scored),
            "by_stratum": {name: aggregate(rows) for name, rows in sorted(by_stratum.items())},
        },
        "predictions_scored": score_predictions(scored),
        "external_filter_funnel": {
            "predicate": "An Article surface is dropped where the text immediately following it, "
                         "within 40 characters and allowing one parenthesised subdivision, names a "
                         "Directive, Regulation, Treaty, Charter, Decision or Convention.",
            "drop_events": drop_events,
            "rows_with_at_least_one_drop": drop_rows,
            "key_note": "drop_events is a count of events and needs no deduplication key. Any "
                        "deduplicated figure ships with its key stated as artifact, field and "
                        "accepted values: deduplicating on the row, the surface and the matched "
                        "qualifier gives 36, and on the row, the surface and a 39-character "
                        "trailing context gives 42.",
            "source_note": "The filter is the layer's own over text it reads. It does not consult "
                           "data/chunks/eu_ai_act.xrefs.jsonl, which is a gold source for the clean "
                           "multi-hop stratum and is barred.",
        },
        "adversarial_augmentation": {
            "policy": "uniform, per augmentation_policy above",
            "n_rows": len(adversarial),
            "absent_units_min": adversarial_units[0],
            "absent_units_max": adversarial_units[-1],
            "absent_units_mean": sum(adversarial_units) / len(adversarial_units),
            "fetched_chunks_min": adversarial_chunks[0],
            "fetched_chunks_max": adversarial_chunks[-1],
            "fetched_chunks_mean": sum(adversarial_chunks) / len(adversarial_chunks),
            "two_quantities_note": "absent_units is the figure eval/layer_predictions.md section 4 "
                                   "tabulates. fetched_chunks is what reaches the model and is "
                                   "larger wherever a fetched unit is split into several chunks. "
                                   "Neither is reported under the other's name.",
            "consequence": "Abstention on this stratum will be evaluated against augmented context, "
                           "mean 15.375 absent units resolving to mean 21.625 fetched chunks. "
                           "The layer has no permitted way to decline, since conditioning on "
                           "stratum would require reading a barred field. This pushes the stratum in "
                           "the harder direction, because more plausible in-corpus text is a "
                           "stronger invitation to answer than less, so whatever abstention survives "
                           "is a stronger result. The generation predictions belong to the "
                           "generation scope and none is made here.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="replace an existing layer results file. Overwriting a committed result is a Rule 4 "
             "correction and is logged; without this the runner refuses.",
    )
    parser.add_argument("--stdout", action="store_true", help="write to stdout and not to disk")
    args = parser.parse_args(argv)

    artifact = build()
    payload = json.dumps(artifact, indent=1, ensure_ascii=False) + "\n"

    if args.stdout:
        sys.stdout.write(payload)
        return 0

    if LAYER_RESULTS.exists() and not args.overwrite:
        print(
            f"{LAYER_RESULTS} already exists. A committed result is not silently replaced; "
            "re-running over one is a Rule 4 correction and takes --overwrite, whose use is logged "
            "in the commit message and the session log.",
            file=sys.stderr,
        )
        return 1

    LAYER_RESULTS.write_text(payload, encoding="utf-8")
    print(f"wrote {LAYER_RESULTS}")
    print(json.dumps(artifact["aggregates"]["overall"], indent=1))
    for entry in artifact["predictions_scored"]:
        print(f"  section {entry['section']}: {entry['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
