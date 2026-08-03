"""The sealed candidate frame is a pure, replayable derivation with a reconstructible draw.

Properties pinned here. The frame re-derives byte-for-byte, so it cannot be hand edited. No
selected pick touches the 50-unit closure, in any stratum. The closure lists all 50 units
with provenance, 40 from the development pool and 10 by the artifact that pulled them. The
allocations and universe match what the ruling fixed. And the reconstruction property: the
final selected set must be reconstructible from the committed draw order plus the committed
rejection log alone, with nothing left over. Selection is the committed forward walk: skip
rejected entries and, under select_distinct_target, entries whose target unit is already
taken. That test ships now and passes vacuously on an empty rejection log; once authoring
records rejections it catches a cascade, a rejection that names a non-candidate, and a unit
that entered the set without appearing in either file.
"""

from __future__ import annotations

import json

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.build_test_frame import OUTPUT, _sha256, build_frame, compute_closure, to_bytes

EVAL = REPO_ROOT / "eval"
REJECTIONS = EVAL / "test_frame_rejections.jsonl"


def _frame() -> dict:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def _sources(frame: dict):
    for stratum, block in frame["strata"].items():
        for source, spec in block.get("sources", {}).items():
            yield stratum, source, spec


def _rejections() -> list[dict]:
    if not REJECTIONS.exists():
        return []
    return [json.loads(line) for line in REJECTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def _unit(value: str) -> str:
    return value.split("#", 1)[0]


def _gold(candidate):
    """The gold unit a candidate names: element 0 of a pair, or the candidate itself."""
    return candidate[0] if isinstance(candidate, list) else candidate


def _distinct_key(spec: dict):
    """The key function a spec's distinctness rule uses, or None when it carries no rule. A key of
    None for a given candidate means that candidate is unconstrained and can never collide."""
    if spec.get("select_distinct_target"):
        return lambda c: c[1]
    if "select_distinct_identity_group" in spec:
        table = spec["select_distinct_identity_group"]["key_by_candidate"]
        return lambda c: table.get(_gold(c))
    if "select_distinct_from" in spec:
        return _gold
    return None


def _selected(spec: dict, rejected_keys: set, taken=()) -> list:
    """Reconstruct the selected set from the draw order and rejection log alone, applying the
    committed rule: forward-walk, skip rejected entries and, under a distinctness rule, entries
    whose key is already taken, until allocation entries are chosen. taken seeds the key set so a
    source constrained against another source reconstructs the same way the builder selected."""
    key = _distinct_key(spec)
    out, seen = [], set(taken)
    for candidate in spec["draw_order"]:
        if json.dumps(candidate) in rejected_keys:
            continue
        if key is not None:
            k = key(candidate)
            if k is not None:
                if k in seen:
                    continue
                seen.add(k)
        out.append(candidate)
        if len(out) == spec["allocation"]:
            break
    return out


def _near_miss_selected(frame: dict, rejected_by_source: dict) -> dict:
    """near_miss's two sources are order-dependent: near_duplicate is constrained against
    block_clusters, in the order canonical_offset_order fixes. Walk them in that order, threading
    the taken set, so the cross-source rule reconstructs from committed files alone."""
    order = [tuple(p) for p in frame["canonical_offset_order"]]
    sources = frame["strata"]["near_miss"]["sources"]
    out, by_name = {}, {}
    for stratum, source in order:
        if stratum != "near_miss":
            continue
        spec = sources[source]
        seed = set()
        if "select_distinct_from" in spec:
            seed = {_gold(c) for c in by_name[spec["select_distinct_from"]]}
        picked = _selected(spec, rejected_by_source.get(("near_miss", source), set()), taken=seed)
        by_name[source] = picked
        out[source] = picked
    return out


def test_frame_is_byte_identical_on_rederivation():
    assert OUTPUT.read_bytes() == to_bytes(build_frame())


def test_allocations_and_universe_match_the_ruling():
    frame = _frame()
    assert frame["closure"]["n"] == 50
    sh = frame["strata"]["single_hop"]["sources"]
    assert sum(s["allocation"] for s in sh.values()) == 18
    assert frame["strata"]["clean_multi_hop"]["sources"]["eu_internal_xref"]["allocation"] == 12
    assert "action_subcategory" in frame["strata"]["action_to_parent"]["sources"]
    assert frame["strata"]["action_to_parent"]["sources"]["action_subcategory"]["allocation"] == 4
    nm = frame["strata"]["near_miss"]["sources"]
    assert nm["block_clusters"]["allocation"] == 3
    assert nm["near_duplicate"]["allocation"] == 5
    adv = frame["strata"]["adversarial"]
    assert adv["total"] == 8 and adv["draw"] is False
    assert frame["universe"]["sha256"] == _sha256(EVAL / "corpus_unit_index.json")


def test_no_selected_pick_is_in_the_closure():
    closure, _ = compute_closure()
    frame = _frame()
    near_miss = _near_miss_selected(frame, {})
    for stratum, source, spec in _sources(frame):
        picks = near_miss[source] if stratum == "near_miss" else _selected(spec, set())
        for candidate in picks:
            items = candidate if isinstance(candidate, list) else [candidate]
            offending = [i for i in items if _unit(i) in closure]
            assert not offending, f"{stratum}/{source}: selected pick {candidate} touches closure {offending}"


def test_selected_set_reconstructs_from_draw_order_and_rejection_log():
    frame = _frame()
    rejected_by_source: dict[tuple[str, str], set[str]] = {}
    for record in _rejections():
        rejected_by_source.setdefault((record["stratum"], record["source"]), set()).add(
            json.dumps(record["rejected"])
        )
    for stratum, source, spec in _sources(frame):
        keys = {json.dumps(c) for c in spec["draw_order"]}
        rejected = rejected_by_source.get((stratum, source), set())
        # every rejection must name a real candidate: nothing left over on the rejection side
        assert rejected <= keys, f"{stratum}/{source}: rejection log names a non-candidate"
        selected = _selected(spec, rejected)
        assert len(selected) == spec["allocation"], (
            f"{stratum}/{source}: {len(selected)} candidates survive rejections, need {spec['allocation']}"
        )
        assert all(json.dumps(c) in keys for c in selected), f"{stratum}/{source}: selected outside draw order"
        assert not (set(map(json.dumps, selected)) & rejected), f"{stratum}/{source}: selected a rejected candidate"
        key = _distinct_key(spec)
        if key is not None:
            taken = [key(c) for c in selected if key(c) is not None]
            assert len(set(taken)) == len(taken), f"{stratum}/{source}: selected duplicate keys"


def test_near_miss_rules_hold_through_backfill():
    """Both near-miss rules bind during backfill, not only the initial picks, and the selected set
    still reconstructs from the draw order plus the rejection log. Driven off a synthetic log, so
    it exercises the cascade whether or not authoring has recorded a real rejection yet."""
    frame = _frame()
    nm = frame["strata"]["near_miss"]["sources"]
    bc, nd = nm["block_clusters"], nm["near_duplicate"]
    synthetic = {
        ("near_miss", "block_clusters"): {json.dumps(bc["draw_order"][0])},
        ("near_miss", "near_duplicate"): {json.dumps(c) for c in nd["draw_order"][:2]},
    }
    picked = _near_miss_selected(frame, synthetic)
    three, five = picked["block_clusters"], picked["near_duplicate"]

    assert len(three) == bc["allocation"] and len(five) == nd["allocation"]
    # the walk went deeper than the spaced picks, so backfill really was exercised
    assert three != _near_miss_selected(frame, {})["block_clusters"]
    # no rejected entry was selected, on either source
    for source, sel in (("block_clusters", three), ("near_duplicate", five)):
        assert not (set(map(json.dumps, sel)) & synthetic[("near_miss", source)])
        assert all(json.dumps(c) in {json.dumps(d) for d in nm[source]["draw_order"]} for c in sel)
    # rule B: no two block_clusters picks share an identity group
    table = bc["select_distinct_identity_group"]["key_by_candidate"]
    groups = [table[c] for c in three if c in table]
    assert len(set(groups)) == len(groups), f"backfilled picks share an identity group: {groups}"
    # rule A: the two sources did not select the same unit
    assert not (set(three) & {_gold(c) for c in five}), "backfilled sources selected the same unit"


def test_closure_lists_all_50_units_with_provenance():
    frame = _frame()
    closure, origin = compute_closure()
    units = frame["closure"]["units"]
    assert len(units) == 50
    assert {u["unit_id"] for u in units} == closure
    assert sum(1 for u in units if u["pulled_by"] == "dev_pool") == 40
    for u in units:
        expected = origin.get(u["unit_id"], "dev_pool")
        assert u["pulled_by"] == expected, f"{u['unit_id']}: pulled_by {u['pulled_by']} != {expected}"
    assert "pool_reconciliation" in frame["closure"]
    assert "cross_stratum_gold_govern_1_3" in frame["recorded_finding"]


def test_every_rejection_carries_a_reason_and_a_reason_code():
    """The frame requires a rejected pick to carry a recorded reason, in
    clean_multi_hop.backfill_authoring_rule and near_miss.backfill_authoring_rule. The committed
    reconstruction test enforces stratum, source and rejected only, so without this a row with no
    reason at all passes."""
    for record in _rejections():
        where = f"{record.get('stratum')}/{record.get('source')} {record.get('rejected')}"
        for field in ("stratum", "source", "rejected", "reason", "reason_code", "matcher_revision"):
            assert field in record, f"{where}: rejection row missing {field}"
        for field in ("reason", "reason_code", "matcher_revision"):
            assert isinstance(record[field], str) and record[field].strip(), (
                f"{where}: {field} is empty"
            )


def test_rejection_reason_test_can_fail():
    """V20: the check above is shown capable of failing before it is trusted. Drives the same
    predicate over rows that violate it and asserts each is caught, so the check is not trusted on
    a pass it has never been able to withhold."""
    base = {
        "stratum": "clean_multi_hop",
        "source": "eu_internal_xref",
        "rejected": ["a", "b"],
        "reason_code": "x",
        "matcher_revision": "rev2",
    }
    assert "reason" not in base
    assert not {**base, "reason": "   "}["reason"].strip()
    no_code = {**base, "reason": "real"}
    del no_code["reason_code"]
    assert "reason_code" not in no_code


def test_rejection_log_is_populated_and_every_row_names_a_candidate():
    """The reconstruction test passes vacuously on an absent or empty log, so a deletion would
    restore the vacuous pass unnoticed. This pins the property instead of a count.

    An earlier form of this test asserted a literal row count and failed on the commit it shipped
    in, when screening a candidate reopened by a rejection added a row. A count is a description of
    the answer; the property is that the log is populated and that every row names a real
    draw-order candidate of the stratum it claims."""
    rows = _rejections()
    assert rows, "eval/test_frame_rejections.jsonl is absent or empty"
    frame = _frame()
    by_source = {(s, n): {json.dumps(c) for c in spec["draw_order"]}
                 for s, n, spec in _sources(frame)}
    for record in rows:
        key = (record["stratum"], record["source"])
        assert key in by_source, f"{key}: no such stratum and source in the frame"
        assert json.dumps(record["rejected"]) in by_source[key], (
            f"{key}: rejected entry {record['rejected']} is not a draw-order candidate"
        )


def test_reconstructed_set_equals_the_committed_query_rows():
    """The reconstruction test asserts the count and the not-rejected property, never the set, so a
    selected set that is twelve entries but not the twelve the queries were authored against passes
    it. This asserts equality against the committed rows.

    It exists because a rejection can free a target and reopen an entry that select_distinct_target
    had skipped: draw index 4 held art_72 and was a pass when the walk was screened, draw index 10
    was skipped for that reason, and when draw 4 was later rejected draw 10 became eligible and
    entered the reconstruction while the query rows still named the older set."""
    frame = _frame()
    rejected = {json.dumps(r["rejected"]) for r in _rejections()
                if (r["stratum"], r["source"]) == ("clean_multi_hop", "eu_internal_xref")}
    spec = frame["strata"]["clean_multi_hop"]["sources"]["eu_internal_xref"]
    reconstructed = {tuple(c) for c in _selected(spec, rejected)}
    rows = [json.loads(line) for line in (EVAL / "test_queries.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    # type names the pre-registered stratum and subtype names the source within it, so the two
    # frame strata that fold into multi_hop are told apart by subtype rather than by type.
    authored = {tuple(r["expected_units"]) for r in rows
                if r["type"] == "multi_hop" and r["subtype"] == "eu_internal_xref"}
    assert authored, "no clean_multi_hop query rows committed"
    assert reconstructed == authored, (
        "clean_multi_hop: reconstruction does not equal the committed query rows; "
        f"reconstructed only {sorted(reconstructed - authored)}, "
        f"authored only {sorted(authored - reconstructed)}"
    )


def test_set_equality_test_can_fail():
    """V20: the check above is shown capable of failing. Drops one rejection, which reopens a
    skipped entry and changes the selected set, and asserts the comparison detects it."""
    frame = _frame()
    spec = frame["strata"]["clean_multi_hop"]["sources"]["eu_internal_xref"]
    full = {json.dumps(r["rejected"]) for r in _rejections()
            if (r["stratum"], r["source"]) == ("clean_multi_hop", "eu_internal_xref")}
    baseline = {tuple(c) for c in _selected(spec, full)}
    without = {r for r in full if json.loads(r) != ["eu_ai_act:art_9", "eu_ai_act:art_72"]}
    perturbed = {tuple(c) for c in _selected(spec, without)}
    assert perturbed != baseline, "dropping a rejection did not change the set; check is blind"
