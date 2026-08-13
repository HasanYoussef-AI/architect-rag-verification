"""Calibration of the self-containedness instrument against held-out units.

Writes eval/self_containedness_calibration.json. Runs before any single-hop pick is screened, and
never touches one: the eleven eu_ai_act single-hop picks are removed as the FIRST filter of every
enumeration here, so no arm is evaluated against a unit it will later judge.

Three arms, and each states its claim narrowly rather than borrowing authority from the others.

POSITIVE ARM. The twelve units the committed rejection record independently establishes as
carrying an outward reference: the six source_points_only sources, and from the four
target_defers_out_of_corpus rows both the three distinct citing sources and the three distinct
deferring targets. Every one must produce at least one arm 1 candidate. This is the arm that can
fail.

NEGATIVE ARM, AND ITS CLAIM IS NARROW. The six source_points_only targets. It does NOT control the
instrument. Arm 1 fires on all six, on references unrelated to the rejection, because these are
long articles that cite other provisions for other reasons. What it controls is the VERDICT step
that runs after the instrument: the rejection record independently characterises each of these six
as answering without reference back, so a verdict protocol that reads every named reference as a
dependency would flag all six and is visibly wrong. The claim is bounded to that and must not be
read as evidence about arm 1's precision.

REGISTER ARM. Arm 2 over the full held-out population of eu_ai_act recitals carrying no named
Article or Annex reference, that population being defined by arm 1's own article_or_annex class
and fixed before the distribution was observed. The claim is CAPABILITY: the batch to be screened
is majority recital, and if arm 2 fires on essentially none of this population then it has no
coverage of that register and screening stops. rct_40 and rct_41 are kept as a floor check on
arm 1, and the record states why that pair cannot carry the register claim: both are in the
committed cross-reference relation precisely because they name Article 26, so selecting them
selects on the property under test.
"""

from __future__ import annotations

import json

from src.goldset.self_containedness import (
    CLASS_ARTICLE_OR_ANNEX,
    CLASS_EXTERNAL_INSTRUMENT,
    ChunkCorpus,
    article_3_inventory,
    defined_term_deference,
    inventory_fingerprint,
    named_references,
)
from src.ingest.corpus_integrity import REPO_ROOT

EVAL = REPO_ROOT / "eval"
TEST_FRAME = EVAL / "test_frame.json"
REJECTIONS = EVAL / "test_frame_rejections.jsonl"
OUTPUT = EVAL / "self_containedness_calibration.json"

POSITIVE_REASON_CODES = ("source_points_only", "target_defers_out_of_corpus")

RECORDED_PREDICTION = (
    "Recorded before the register arm was run, so the result can contradict it. Arm 2 fires on a "
    "large majority of the held-out recitals carrying no named reference, because Article 3 "
    "defines terms such as AI system, provider and deployer that recital prose uses constantly. "
    "If it fires on few, the prediction is wrong about where recital deference lives and the "
    "design changes before anything is screened."
)

PICKS_DISCLOSURE = (
    "Four of the six recitals among the eleven eu_ai_act single-hop picks carry no named Article "
    "or Annex reference. This was surfaced during the design round as arithmetic over the "
    "committed data/chunks/eu_ai_act.xrefs.jsonl evidence field, which records 149 of 180 "
    "recitals as carrying no such surface form against 145 of those held out from the picks. It "
    "is recorded here rather than buried, and it is an observation about a pre-existing committed "
    "artifact and NOT a run of this instrument, which has never been evaluated against a pick. "
    "The design was frozen against criteria that do not depend on it: the register population is "
    "defined by arm 1's own class over non-pick recitals, and the capability threshold was fixed "
    "before the distribution was observed."
)

FLOOR_CHECK_LIMIT = (
    "rct_40 and rct_41 are retained as a floor check on arm 1 because they cost nothing. They "
    "cannot carry the register claim. Both are the only two recitals appearing in the committed "
    "internal cross-reference relation, and they appear in it precisely because their text names "
    "Article 26, so selecting them selects on the property under test. A pointer pattern fires on "
    "them trivially, and passing this check is no evidence that arm 1 or arm 2 reaches the 149 "
    "recitals of 180 that name no Article at all."
)


# The calibration's population is the clean_multi_hop draw-order rejections, whose `rejected`
# entry is an ordered [citing source, cited target] pair and whose reason codes are the ones the
# role split reads. eval/test_frame_rejections.jsonl holds every drawing stratum's rejections, so
# the stratum is named here rather than left implicit. Without it the funnel's starting_population
# counts rows of other strata that the reason-code filter then removes, which moves a committed
# calibration figure whenever an unrelated stratum lands. The role split itself was already
# scoped in effect, since no other stratum uses these reason codes, but "in effect" is not a
# filter; it also unpacks `rejected` as a pair, which a bare unit id would not survive.
CALIBRATION_STRATUM = "clean_multi_hop"


def _load_rejection_rows() -> list[dict]:
    return [
        row
        for row in (
            json.loads(line)
            for line in REJECTIONS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if row.get("stratum") == CALIBRATION_STRATUM
    ]


def positive_and_negative_units() -> tuple[list[str], list[str], dict]:
    """Derive both arms from the committed rejection record rather than naming units."""
    rows = _load_rejection_rows()
    kept = [r for r in rows if r.get("reason_code") in POSITIVE_REASON_CODES]
    positive: list[str] = []
    negative: list[str] = []
    for row in kept:
        source, target = row["rejected"]
        if row["reason_code"] == "source_points_only":
            positive.append(source)
            negative.append(target)
        else:
            positive.append(source)
            positive.append(target)
    positive_set = sorted(set(positive))
    negative_set = sorted(set(negative) - set(positive_set))
    removed: dict[str, int] = {}
    for row in rows:
        code = row.get("reason_code")
        if code not in POSITIVE_REASON_CODES:
            removed[code] = removed.get(code, 0) + 1
    funnel = {
        "starting_population": len(rows),
        "removed_reason_code_not_in_scope": {
            "count": len(rows) - len(kept),
            "predicate": (
                "reason_code is not one of source_points_only or target_defers_out_of_corpus"
            ),
            "removed_by_reason_code": removed,
        },
        "rows_kept": len(kept),
        "role_split_predicate": (
            "rejected is ordered [citing source, cited target]. On a source_points_only row the "
            "record characterises the target as answering without reference back, so the target "
            "is a negative and only the source is a positive. On a target_defers_out_of_corpus "
            "row both endpoints are positives: the source cites, and the target is what defers"
        ),
        "positive_units": len(positive_set),
        "negative_units": len(negative_set),
    }
    return positive_set, negative_set, funnel


def _unit_summary(unit_id: str, corpus: ChunkCorpus, inventory: list[str]) -> dict:
    arm1 = named_references(unit_id, corpus)
    arm2 = defined_term_deference(unit_id, corpus, inventory)
    surfaces = sorted(
        {
            c["surface"]
            for c in arm1["candidates"]
            if c["class"] in (CLASS_ARTICLE_OR_ANNEX, CLASS_EXTERNAL_INSTRUMENT)
        }
    )
    return {
        "unit_id": unit_id,
        "arm1_starting_population": arm1["funnel"]["starting_population"],
        "arm1_removed_self_reference": arm1["funnel"]["removed_self_reference"]["count"],
        "arm1_candidates": arm1["funnel"]["candidates"],
        "arm1_by_class": arm1["candidates_by_class"],
        "arm1_named_surfaces": surfaces,
        "arm2_candidates": arm2["funnel"]["candidates"],
        "arm2_distinct_terms": len(arm2["distinct_terms_used"]),
    }


def build(corpus: ChunkCorpus | None = None) -> dict:
    corpus = corpus if corpus is not None else ChunkCorpus.load()
    inventory = article_3_inventory(corpus)

    frame = json.loads(TEST_FRAME.read_text(encoding="utf-8"))
    eu = frame["strata"]["single_hop"]["sources"]["eu_ai_act"]
    draw_order = eu["draw_order"]
    allocation = eu["allocation"]
    picks = set(draw_order[:allocation])
    index_of = {unit: i for i, unit in enumerate(draw_order)}

    positive, negative, role_funnel = positive_and_negative_units()

    contaminating = sorted((set(positive) | set(negative)) & picks)
    if contaminating:
        raise ValueError(f"calibration unit is also a pick: {contaminating}")

    positive_rows = [_unit_summary(u, corpus, inventory) for u in
                     sorted(positive, key=lambda u: index_of.get(u, 10**6))]
    for row in positive_rows:
        row["single_hop_draw_index"] = index_of.get(row["unit_id"])
    negative_rows = [_unit_summary(u, corpus, inventory) for u in
                     sorted(negative, key=lambda u: index_of.get(u, 10**6))]
    for row in negative_rows:
        row["single_hop_draw_index"] = index_of.get(row["unit_id"])

    positive_zero = [r["unit_id"] for r in positive_rows if r["arm1_candidates"] == 0]

    # Register arm. The pick filter runs FIRST, so no arm is ever evaluated against a pick.
    all_recitals = sorted(u for u in corpus.unit_ids() if u.startswith("eu_ai_act:rct_"))
    non_pick = [u for u in all_recitals if u not in picks]
    named: list[str] = []
    unnamed: list[str] = []
    for unit in non_pick:
        arm1 = named_references(unit, corpus)
        if arm1["candidates_by_class"][CLASS_ARTICLE_OR_ANNEX] > 0:
            named.append(unit)
        else:
            unnamed.append(unit)

    register_hits = 0
    distribution: dict[str, int] = {}
    term_counts: list[int] = []
    for unit in unnamed:
        arm2 = defined_term_deference(unit, corpus, inventory)
        n = len(arm2["distinct_terms_used"])
        term_counts.append(n)
        if n > 0:
            register_hits += 1
        bucket = "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 else "6-10" if n <= 10 \
            else "11+"
        distribution[bucket] = distribution.get(bucket, 0) + 1

    floor_rows = [_unit_summary(u, corpus, inventory)
                  for u in ("eu_ai_act:rct_40", "eu_ai_act:rct_41")]
    for row in floor_rows:
        row["single_hop_draw_index"] = index_of.get(row["unit_id"])

    return {
        "description": (
            "Calibration of src/goldset/self_containedness.py against held-out units, run before "
            "any single-hop pick is screened. The eleven eu_ai_act single-hop picks are removed "
            "as the first filter of every enumeration, so no arm here is evaluated against a unit "
            "it will later judge."
        ),
        "command": "python -m src.goldset.calibrate_self_containedness",
        "reproducibility_level": 1,
        "inventory": {
            "source_unit": "eu_ai_act:art_3",
            "n_terms": len(inventory),
            "fingerprint": inventory_fingerprint(inventory),
        },
        "recorded_prediction": RECORDED_PREDICTION,
        "picks_disclosure": PICKS_DISCLOSURE,
        "role_split_funnel": role_funnel,
        "positive_arm": {
            "claim": (
                "Every unit the committed rejection record independently establishes as carrying "
                "an outward reference must produce at least one arm 1 candidate. This is the arm "
                "that can fail."
            ),
            "n_units": len(positive_rows),
            "units_producing_no_candidate": positive_zero,
            "passed": not positive_zero,
            "units": positive_rows,
        },
        "negative_arm": {
            "claim": (
                "The six source_points_only targets. This arm does NOT control the instrument. "
                "Arm 1 fires on all six, on references unrelated to the rejection. What it "
                "controls is the verdict step downstream of the instrument: the record "
                "independently characterises each of these six as answering without reference "
                "back, so a verdict protocol that reads every named reference as a dependency "
                "flags all six and is visibly wrong. The claim is bounded to the verdict step."
            ),
            "controls_the_instrument": False,
            "controls_the_verdict_step": True,
            "n_units": len(negative_rows),
            "units_where_arm1_fires": [
                r["unit_id"] for r in negative_rows if r["arm1_candidates"] > 0
            ],
            "units": negative_rows,
        },
        "register_arm": {
            "claim": (
                "Capability. The batch to be screened is majority recital. If arm 2 fires on "
                "essentially none of the held-out recitals carrying no named reference, it has no "
                "coverage of that register and screening stops."
            ),
            "population_rule": (
                "eu_ai_act recital units, minus the eleven single-hop picks, minus those where "
                "arm 1 emits at least one candidate of class article_or_annex. Fixed before the "
                "distribution was observed."
            ),
            "funnel": {
                "starting_population": len(all_recitals),
                "removed_is_a_single_hop_pick": {
                    "count": len(all_recitals) - len(non_pick),
                    "predicate": (
                        "the unit is one of the eleven eu_ai_act single-hop picks. Applied FIRST, "
                        "so no arm is evaluated against a pick"
                    ),
                },
                "removed_carries_a_named_article_or_annex_reference": {
                    "count": len(named),
                    "predicate": (
                        "arm 1 emits at least one candidate of class article_or_annex for the unit"
                    ),
                    "removed_items": named,
                },
                "population": len(unnamed),
            },
            "arm2_fired_on": register_hits,
            "arm2_fired_on_fraction": (
                round(register_hits / len(unnamed), 4) if unnamed else None
            ),
            "distinct_terms_distribution": distribution,
            "distinct_terms_min": min(term_counts) if term_counts else None,
            "distinct_terms_median": (
                sorted(term_counts)[len(term_counts) // 2] if term_counts else None
            ),
            "distinct_terms_max": max(term_counts) if term_counts else None,
            "floor_check": {
                "limit": FLOOR_CHECK_LIMIT,
                "units": floor_rows,
            },
        },
    }


def main() -> None:
    record = build()
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
