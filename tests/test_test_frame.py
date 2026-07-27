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


def _selected(spec: dict, rejected_keys: set) -> list:
    """Reconstruct the selected set from the draw order and rejection log alone, applying the
    committed rule: forward-walk, skip rejected entries and, under select_distinct_target,
    entries whose target unit is already taken, until allocation entries are chosen."""
    out, taken = [], set()
    for candidate in spec["draw_order"]:
        if json.dumps(candidate) in rejected_keys:
            continue
        if spec.get("select_distinct_target"):
            if candidate[1] in taken:
                continue
            taken.add(candidate[1])
        out.append(candidate)
        if len(out) == spec["allocation"]:
            break
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
    for stratum, source, spec in _sources(frame):
        for candidate in _selected(spec, set()):
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
        if spec.get("select_distinct_target"):
            targets = [c[1] for c in selected]
            assert len(set(targets)) == len(targets), f"{stratum}/{source}: selected duplicate targets"


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
