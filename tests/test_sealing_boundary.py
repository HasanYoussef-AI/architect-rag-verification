"""The sealing-boundary checklist, over the final fifty rather than over drawn candidates.

Three checks were to be run against the final selected set before the sealing commit. Each was
re-derived by hand at the RAG-12 open and each is asserted here, because a measurement taken once
and written into a report is not a measurement a later change has to survive.

WHY THESE READ THE QUERY FILE AND NOT THE FRAME. The frame fixes the draw order; authoring then
rejects picks, backfills replacements and widens slots. tests/test_test_frame.py's
test_no_selected_pick_is_in_the_closure walks the frame's own draw order, so a carrier admitted
into a slot at authoring was never in its filter. Every check here selects on the presence of
gold_slots on a committed row rather than on a stratum name, which is the same widening
tests/test_test_query_verification.py applied to its two block-scoped checks and for the same
reason: a later stratum shipping the same field gets the same judgement rather than passing
unseen.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.goldset.relation_positions import load_relations

QUERIES = REPO_ROOT / "eval" / "test_queries.jsonl"
FRAME = REPO_ROOT / "eval" / "test_frame.json"
POOL = REPO_ROOT / "eval" / "dev_unit_pool.json"


def _rows() -> list[dict]:
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _gold_bearing() -> list[dict]:
    return [r for r in _rows() if r.get("gold_slots")]


def _carrier_classes() -> dict[str, str]:
    """unit id -> class representative, union-find over both committed carrier relations.

    The same union the single-hop slot ruling names: the duplication map's duplicated_in and
    verbatim_groups.json's normalised_identity members, composed rather than either alone.
    """
    groups, dup_map = load_relations(REPO_ROOT)
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for row in dup_map:
        for dup in row["duplicated_in"]:
            union(row["source_unit_id"], dup["unit_id"])
    for group in groups:
        members = group["members"]
        for member in members[1:]:
            union(members[0], member)
    return {unit: find(unit) for unit in list(parent)}


def _classes_by_row() -> dict[str, set[str]]:
    classes = _carrier_classes()
    return {r["id"]: {classes.get(u, u) for u in r["expected_units"]} for r in _gold_bearing()}


def _collisions() -> dict[str, list[str]]:
    shared: dict[str, list[str]] = {}
    for rid, cls in _classes_by_row().items():
        for c in cls:
            shared.setdefault(c, []).append(rid)
    return {c: sorted(ids) for c, ids in shared.items() if len(ids) > 1}


# Measured at the RAG-12 open over the closed set of fifty. Five carrier classes are gold on more
# than one row: four cross-stratum, single-hop against clean multi-hop, and one within clean
# multi-hop. All five are singleton classes, so each is ONE unit that is gold on two rows rather
# than two carriers of one statement.
KNOWN_SHARED_CLASSES = {
    "eu_ai_act:art_113": ["test_13", "test_22"],
    "eu_ai_act:art_49": ["test_10", "test_29"],
    "eu_ai_act:art_74": ["test_15", "test_30"],
    "eu_ai_act:art_78": ["test_11", "test_13"],
    "eu_ai_act:art_99": ["test_17", "test_31"],
}


def test_the_shared_gold_classes_are_the_five_recorded_ones():
    """A disclosure, fixed so that a change to it has to be argued rather than absorbed.

    The frame already ruled on this shape. Its cross_stratum_gold_govern_1_3 finding records the
    same statement reached by an easy single-hop query and by a hard structural hop, with opposite
    pre-registered predictions, as a CONTROLLED PAIR rather than a confound, and it rejected a
    cross-stratum disjointness constraint on the ground that inventing a structural rejection
    criterion after seeing which picks it would remove is a threshold fitted to its own
    observations. That reasoning covers these five unchanged. What this test adds is that the set
    is fixed: a later change to any gold slot that creates or removes a shared class turns this
    red and needs a ruling.

    The split matters and is asserted separately. Four are cross-stratum, single_hop against
    multi_hop/eu_internal_xref, which is the shape the frame reasoned about. One, art_78, is
    within clean multi-hop, two rows of one stratum sharing an endpoint, which the edge
    admissibility rules already record as noted rather than rejected.
    """
    found = _collisions()
    assert found == KNOWN_SHARED_CLASSES, (
        "the shared gold classes moved.\n"
        f"  recorded: {json.dumps(KNOWN_SHARED_CLASSES, sort_keys=True)}\n"
        f"  found   : {json.dumps(found, sort_keys=True)}\n"
        "This set is a disclosure stated over fixed membership; a change here is a ruling, not a "
        "re-pin."
    )

    # Singleton is checked through the same fallback the detector uses. A unit named by neither
    # carrier relation has no entry in the union-find at all and is its own class of one, which
    # is every EU unit here: both committed relations are NIST-side, the duplication map being
    # AI 100-1's and the normalised-identity groups being over subcategory statements. Reading
    # membership off the union-find dict alone reports such a unit as a class of zero, which is a
    # fact about the relation's coverage rather than about the class.
    classes = _carrier_classes()
    gold_units = {u for r in _gold_bearing() for u in r["expected_units"]}
    for rep in found:
        members = {u for u in gold_units if classes.get(u, u) == rep}
        assert len(members) == 1, (
            f"{rep} is no longer a singleton class among gold: {sorted(members)}. A shared "
            "MULTI-member class is the duplicated-statement case and reads differently from a "
            "shared unit, so which one this is has to be stated rather than assumed"
        )
        assert rep not in classes, (
            f"{rep} is now named by a committed carrier relation, so it is no longer a class of "
            "one by absence and the reading above needs revisiting"
        )

    stratum = {r["id"]: (r["type"], r["subtype"]) for r in _rows()}
    cross = {c for c, ids in found.items() if len({stratum[i] for i in ids}) > 1}
    assert len(cross) == 4, f"{len(cross)} classes are cross-stratum, not 4"
    assert cross == {"eu_ai_act:art_113", "eu_ai_act:art_49",
                     "eu_ai_act:art_74", "eu_ai_act:art_99"}


def test_the_shared_class_detector_can_fail():
    """V20. The comparison is shown reporting a collision it was not given."""
    classes = _classes_by_row()
    victim, other = sorted(classes)[0], sorted(classes)[1]
    fabricated = dict(classes)
    fabricated[other] = set(fabricated[victim])
    shared: dict[str, list[str]] = {}
    for rid, cls in fabricated.items():
        for c in cls:
            shared.setdefault(c, []).append(rid)
    found = {c: sorted(ids) for c, ids in shared.items() if len(ids) > 1}
    assert found != KNOWN_SHARED_CLASSES, "a fabricated collision was not detected"
    assert any(victim in ids and other in ids for ids in found.values())


def test_govern_1_3_is_gold_on_no_row_of_the_fifty():
    """The frame's recorded finding is true of the draw and not of the selection.

    eval/test_frame.json records that single-hop draws nist_ai_100_1:sub_GOVERN_1.3 and
    action-to-parent draws the AI 600-1 carrier, so one slot would be satisfied by either. The
    single-hop pick was then rejected at authoring under answer_attributable_outside_slot, so no
    single-hop query exists on that statement and the controlled pair does not exist in the final
    selected set. The frame is not corrected; the divergence is recorded here against the closed
    set, and the frame's note stands as a statement about the draw.
    """
    rows = _rows()
    for named in ("nist_ai_100_1:sub_GOVERN_1.3", "nist_ai_600_1:sub_GOVERN_1.3"):
        holders = [r["id"] for r in rows if named in r["expected_units"]]
        assert holders == [], f"{named} is gold on {holders}; the frame's pair is back"

    # Control: the same predicate finds a unit that IS gold, so the empties above are real.
    probe = _gold_bearing()[0]["expected_units"][0]
    assert [r["id"] for r in rows if probe in r["expected_units"]], (
        f"the predicate found no holder for {probe}, which is gold by construction"
    )


def slot_overlaps(gold_slots: list[list[str]]) -> list[tuple[int, int, list[str]]]:
    """Every pair of slots sharing an acceptable unit, as (i, j, shared).

    Factored out so the companion below drives the SAME predicate the check runs. The first
    version of this file asserted disjointness inline, and the mutation that gutted the
    comparison passed: the committed data is disjoint, so weakening the check changes nothing a
    clean run can see. A check whose only demonstration is over data that satisfies it has not
    been shown capable of failing at all, which is the V20 breach in its purest form.
    """
    slots = [set(s) for s in gold_slots]
    out = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            shared = sorted(slots[i] & slots[j])
            if shared:
                out.append((i, j, shared))
    return out


def gold_in_closure(gold: set[str], closure: set[str]) -> list[str]:
    """The gold units that sit in the closure. Factored out for the same reason as above."""
    return sorted(gold & closure)


def test_slots_within_a_query_are_disjoint():
    """PREREGISTRATION.md's Gold set rule, over every authored row rather than drawn candidates.

    No two slots of the same query share an acceptable unit. This is not cosmetic: it is what
    keeps Recall@10 a count of distinct answered parts, and what keeps NDCG@10 at or below one,
    since a unit satisfying two slots would contribute two gains against an ideal built for one.

    Measured over the fifty: 8 rows carry no slot, 30 carry one, 12 carry two, so 12 slot pairs
    are compared and the check is live rather than vacuous.
    """
    rows = _rows()
    by_count: dict[int, list[str]] = {}
    for r in rows:
        by_count.setdefault(len(r["gold_slots"]), []).append(r["id"])
    assert sorted(by_count) == [0, 1, 2], f"slot counts are now {sorted(by_count)}"
    assert len(by_count[0]) == 8 and len(by_count[1]) == 30 and len(by_count[2]) == 12

    pairs = sum(len(r["gold_slots"]) * (len(r["gold_slots"]) - 1) // 2 for r in rows)
    assert pairs == 12, f"{pairs} slot pairs compared, not 12; this check is not vacuous"

    for r in rows:
        overlaps = slot_overlaps(r["gold_slots"])
        assert not overlaps, (
            f"{r['id']}: " + "; ".join(
                f"slots {i} and {j} both admit {shared}" for i, j, shared in overlaps
            ) + ". PREREGISTRATION.md requires a query's slots to be disjoint, which is what "
            "keeps Recall@10 a count of distinct answered parts and NDCG@10 at or below 1"
        )


def test_the_disjointness_check_can_fail():
    """V20, through the same predicate the check runs, on a row whose slots overlap.

    Driven through slot_overlaps rather than restating the set intersection, so gutting that
    function turns this red. Restating it here would leave the real check demonstrated only over
    data that already satisfies it, which demonstrates nothing.
    """
    overlapping = [["eu_ai_act:art_43"], ["eu_ai_act:art_43", "eu_ai_act:art_97"]]
    found = slot_overlaps(overlapping)
    assert found == [(0, 1, ["eu_ai_act:art_43"])], (
        f"the predicate did not detect an overlapping pair: {found}"
    )

    three = [["a"], ["b"], ["a", "c"]]
    assert slot_overlaps(three) == [(0, 2, ["a"])], "the predicate missed a non-adjacent pair"

    assert slot_overlaps([["a"], ["b"]]) == [], "the predicate reported a false overlap"
    assert slot_overlaps([["a"]]) == [], "a single slot cannot overlap itself"


def test_expected_units_is_the_in_place_flatten_of_gold_slots():
    """gold_slots is the authoritative structure and expected_units is its derived flattening.

    Recorded as pinned by a test since the row schema was set; no test pinned it. Measured 50 of
    50 today. In place rather than sorted, because order between slots is load-bearing: on one
    committed row the reversed pair is itself a separate draw-order entry, so the pair does not
    identify its candidate without its order.
    """
    for r in _rows():
        expected = [u for slot in r["gold_slots"] for u in slot]
        assert r["expected_units"] == expected, (
            f"{r['id']}: expected_units {r['expected_units']} against the in-place flatten "
            f"{expected}"
        )


def test_the_flatten_check_is_order_sensitive():
    """V20, and the companion is chosen to be the one a set comparison would pass.

    A sorted flattening has the same members as an in-place one, so a membership test cannot tell
    them apart. This drives the real comparison against exactly that case.
    """
    gold = [["eu_ai_act:art_97"], ["eu_ai_act:art_43"]]
    in_place = [u for slot in gold for u in slot]
    sorted_flat = sorted(in_place)
    assert set(in_place) == set(sorted_flat), "the two flattenings differ in membership"
    assert in_place != sorted_flat, "this fixture does not distinguish the two orders"


def test_no_gold_unit_of_the_fifty_sits_in_the_fifty_unit_closure():
    """Against the closure, not the 40-unit development pool, and over every stratum.

    The closure is the 40 pool units plus every unit carrying a statement verbatim-identical to a
    pool unit, measured at 50. A gold slot naming one either admits a pool unit into gold and
    breaks the development firewall, or omits it and scores a retrieval hit on byte-identical text
    as a miss.

    The committed single_hop check reaches 18 of the 42 gold-bearing rows and 26 of the 65 gold
    units, leaving clean multi-hop, action-to-parent and near-miss unreached. This one reads every
    row carrying gold.
    """
    frame = json.loads(FRAME.read_text(encoding="utf-8"))
    closure = {u["unit_id"] for u in frame["closure"]["units"]}
    assert len(closure) == 50, f"the closure is {len(closure)} units, not 50"

    gold = {u for r in _gold_bearing() for slot in r["gold_slots"] for u in slot}
    assert len(gold) == 65, f"{len(gold)} distinct gold units, not 65"

    offending = gold_in_closure(gold, closure)
    assert not offending, (
        f"gold touches the closure: {offending}. The closure is the development pool plus every "
        "unit carrying a verbatim-identical statement; a gold slot naming one either breaks the "
        "development firewall or scores identical text as a miss"
    )


def test_the_closure_is_the_bar_and_the_pool_alone_is_not():
    """Why the closure rather than the pool, measured rather than argued.

    Gold intersected with the 40-unit pool is also empty, so a pool-only check would report a
    pass while leaving the ten closure-only units unguarded. Asserting both is what stops a later
    simplification from weakening the bar without any test noticing.
    """
    frame = json.loads(FRAME.read_text(encoding="utf-8"))
    closure = {u["unit_id"] for u in frame["closure"]["units"]}
    pool_doc = json.loads(POOL.read_text(encoding="utf-8"))
    units = pool_doc["units"] if isinstance(pool_doc, dict) else pool_doc
    pool = {u["unit_id"] if isinstance(u, dict) else u for u in units}

    assert len(pool) == 40, f"the pool is {len(pool)} units, not 40"
    assert pool < closure, "the closure is no longer a strict superset of the pool"
    closure_only = closure - pool
    assert len(closure_only) == 10, f"{len(closure_only)} closure-only units, not 10"

    gold = {u for r in _gold_bearing() for slot in r["gold_slots"] for u in slot}
    assert not (gold & pool), "gold touches the pool"

    # The control that makes the distinction real: a closure-only unit IS caught by the closure
    # check and would NOT be caught by a pool-only one.
    probe = sorted(closure_only)[0]
    assert probe in closure and probe not in pool
    assert (gold | {probe}) & closure == {probe}
    assert not ((gold | {probe}) & pool), (
        "a pool-only check would have flagged this probe, so it does not demonstrate the gap"
    )


def test_the_closure_check_can_fail():
    """V20, through the same predicate the check runs, against gold that does touch the closure.

    The committed gold is disjoint from the closure, so no mutation of the real check can be seen
    on clean data. What is demonstrated instead is the predicate itself detecting a violation, on
    a gold set built by adding one real closure member.
    """
    frame = json.loads(FRAME.read_text(encoding="utf-8"))
    closure = {u["unit_id"] for u in frame["closure"]["units"]}
    gold = {u for r in _gold_bearing() for slot in r["gold_slots"] for u in slot}
    probe = sorted(closure)[0]

    assert gold_in_closure(gold, closure) == [], "the committed gold already touches the closure"
    assert gold_in_closure(gold | {probe}, closure) == [probe], (
        "the predicate did not detect a gold unit sitting in the closure"
    )
    assert gold_in_closure(set(), closure) == [], "the predicate reported a false hit on no gold"


def test_the_checklist_reaches_every_gold_bearing_row():
    """The coverage the superseded single_hop-scoped check did not have, asserted as a number.

    18 of 42 before, all 42 now. Stated as a count so a later re-scoping to one stratum shows up
    here rather than as a quiet loss of reach.
    """
    rows = _rows()
    gold_bearing = _gold_bearing()
    assert len(rows) == 50
    assert len(gold_bearing) == 42, f"{len(gold_bearing)} gold-bearing rows, not 42"
    strata = sorted({(r["type"], r["subtype"]) for r in gold_bearing})
    assert len(strata) == 7, f"the checks reach {len(strata)} type/subtype pairs, not 7: {strata}"
    empty = [r["id"] for r in rows if not r.get("gold_slots")]
    assert empty == [f"test_0{i}" for i in range(1, 9)], (
        f"the gold-empty rows are {empty}, not the eight adversarial rows"
    )


@pytest.mark.parametrize("relation", ["duplication_map", "verbatim_groups"])
def test_both_carrier_relations_contribute_to_the_classes(relation):
    """Neither relation alone reproduces the composition, so both are load-bearing here.

    The single-hop slot ruling composes them for a measured reason: two of the closure's ten
    expansion units are reachable only through verbatim_groups.json. If one relation could be
    dropped without changing the classes, this file would be resting on a union it does not need.
    """
    groups, dup_map = load_relations(REPO_ROOT)
    if relation == "duplication_map":
        assert dup_map, "the duplication map is empty"
        assert any(row["duplicated_in"] for row in dup_map)
    else:
        assert groups, "verbatim_groups holds no normalised_identity groups"
        assert any(len(g["members"]) > 1 for g in groups)
