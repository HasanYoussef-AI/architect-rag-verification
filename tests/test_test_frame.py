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

The reconstruction property is asserted against the authored rows as well, per drawing source
rather than for one hard-coded source, so a stratum gains that coverage at the commit its rows
land rather than at a later one. The join is derived: row type inverts STRATUM_TO_FRAME and row
subtype is the frame's source key verbatim. What is tabulated is which element of a candidate a
row is keyed by, because that differs per source and cannot be inferred from the stratum name.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.build_test_frame import OUTPUT, _sha256, build_frame, compute_closure, to_bytes
from tests.test_test_queries import STRATUM_TO_FRAME

EVAL = REPO_ROOT / "eval"
REJECTIONS = EVAL / "test_frame_rejections.jsonl"
QUERIES = EVAL / "test_queries.jsonl"
VERIFICATION = EVAL / "test_query_verification.jsonl"


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


def _verification() -> dict[str, dict]:
    """The verification records by row id, or an empty map before the file exists."""
    if not VERIFICATION.exists():
        return {}
    return {
        record["id"]: record
        for record in (json.loads(line)
                       for line in VERIFICATION.read_text(encoding="utf-8").splitlines()
                       if line.strip())
    }


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


# The two matcher fields are clean_multi_hop artifacts. They record which revision of the
# citing-sentence matcher produced a rejection and what a re-derivation under the later revision
# returned, which is a question only that stratum's edge-drawing raises. Scoped rather than
# universal, on the precedent the adversarial grader pre-declaration already sets in
# tests/test_test_queries.py: required inside the stratum they belong to, asserted absent outside
# it, so a row given a fabricated value fails rather than passing unnoticed.
MATCHER_FIELDS = ("matcher_revision", "matcher_recheck")
MATCHER_STRATUM = "clean_multi_hop"


def _rejection_row_defects(record: dict) -> list[str]:
    """Every way a rejection row violates the recorded requirements, as a list of messages.

    One predicate, driven by the check below and by its V20 companion, so what is shown capable
    of failing is what actually runs rather than a second copy that can drift from it.

    matcher_recheck is required PRESENT and not required non-empty, and the asymmetry is
    measured rather than assumed: over the 19 committed rows matcher_revision is present on 19
    and non-empty on 19, while matcher_recheck is present on 19 and non-null on 6. A
    non-emptiness requirement would fail 13 committed rows, so presence is the requirement the
    file supports and null is a recorded state meaning the row was not re-derived.
    """
    where = f"{record.get('stratum')}/{record.get('source')} {record.get('rejected')}"
    defects: list[str] = []
    for field in ("stratum", "source", "rejected", "reason", "reason_code"):
        if field not in record:
            defects.append(f"{where}: rejection row missing {field}")
    for field in ("reason", "reason_code"):
        value = record.get(field)
        if field in record and not (isinstance(value, str) and value.strip()):
            defects.append(f"{where}: {field} is empty")

    if record.get("stratum") == MATCHER_STRATUM:
        revision = record.get("matcher_revision")
        if "matcher_revision" not in record:
            defects.append(f"{where}: rejection row missing matcher_revision")
        elif not (isinstance(revision, str) and revision.strip()):
            defects.append(f"{where}: matcher_revision is empty")
        if "matcher_recheck" not in record:
            defects.append(
                f"{where}: rejection row missing matcher_recheck. The key is required on every "
                "row of this stratum; null is the recorded value where the row was not re-derived"
            )
    else:
        for field in MATCHER_FIELDS:
            if field in record:
                defects.append(
                    f"{where}: carries {field}, which is a {MATCHER_STRATUM} artifact with "
                    "nothing to say outside that stratum. A value here is fabricated, not "
                    "recorded, so the field is asserted absent rather than left optional"
                )
    return defects


def test_every_rejection_carries_a_reason_and_a_reason_code():
    """The frame requires a rejected pick to carry a recorded reason, in
    clean_multi_hop.backfill_authoring_rule and near_miss.backfill_authoring_rule. The committed
    reconstruction test enforces stratum, source and rejected only, so without this a row with no
    reason at all passes."""
    for record in _rejections():
        defects = _rejection_row_defects(record)
        assert not defects, "; ".join(defects)


def test_matcher_fields_are_scoped_to_their_own_stratum():
    """The scoping, asserted over the committed file in both directions.

    The universal form this replaces had never met a row lacking matcher_revision, all 19
    committed rows being clean_multi_hop, so it could not have failed. The absence half is
    vacuous until a row of another stratum lands, which is why the companion below drives it on
    a fabricated row rather than waiting for the data to prove the check works.
    """
    rows = _rejections()
    assert rows, "eval/test_frame_rejections.jsonl is absent or empty"
    for record in rows:
        where = f"{record.get('stratum')}/{record.get('source')} {record.get('rejected')}"
        if record["stratum"] == MATCHER_STRATUM:
            assert all(f in record for f in MATCHER_FIELDS), f"{where}: missing a matcher field"
        else:
            assert not any(f in record for f in MATCHER_FIELDS), (
                f"{where}: a {record['stratum']} row carries a {MATCHER_STRATUM} matcher field"
            )


def test_rejection_reason_test_can_fail():
    """V20: the check above is shown capable of failing before it is trusted.

    Drives _rejection_row_defects, the predicate the check itself runs, over rows that violate
    each requirement, and asserts each is caught. An earlier form of this companion asserted
    properties of the dicts it constructed and never called the predicate, so it demonstrated
    that a key was missing from a literal rather than that the check would catch it.
    """
    good = {
        "stratum": "clean_multi_hop",
        "source": "eu_internal_xref",
        "rejected": ["a", "b"],
        "reason": "real",
        "reason_code": "x",
        "matcher_revision": "rev2",
        "matcher_recheck": None,
    }
    assert _rejection_row_defects(good) == [], "the companion's baseline row must itself pass"

    no_reason = {k: v for k, v in good.items() if k != "reason"}
    assert _rejection_row_defects(no_reason), "a row with no reason was not caught"
    assert _rejection_row_defects({**good, "reason": "   "}), "a blank reason was not caught"
    no_code = {k: v for k, v in good.items() if k != "reason_code"}
    assert _rejection_row_defects(no_code), "a row with no reason_code was not caught"

    # The scoping, both directions, on rows the committed file does not yet contain.
    no_revision = {k: v for k, v in good.items() if k != "matcher_revision"}
    assert _rejection_row_defects(no_revision), (
        f"a {MATCHER_STRATUM} row with no matcher_revision was not caught"
    )
    no_recheck = {k: v for k, v in good.items() if k != "matcher_recheck"}
    assert _rejection_row_defects(no_recheck), (
        f"a {MATCHER_STRATUM} row with no matcher_recheck was not caught"
    )
    single_hop = {**good, "stratum": "single_hop", "source": "eu_ai_act",
                  "rejected": "eu_ai_act:art_87"}
    assert _rejection_row_defects(single_hop), (
        "a single_hop row carrying a fabricated matcher_revision was not caught, which is the "
        "exact failure the scoping exists to prevent"
    )
    clean_single_hop = {k: v for k, v in single_hop.items() if k not in MATCHER_FIELDS}
    assert _rejection_row_defects(clean_single_hop) == [], (
        "a well-formed single_hop rejection row must pass, or the scoping bars the rows it was "
        "written to admit"
    )

    # A null matcher_recheck is a recorded state, not a defect. Asserted directly, because the
    # measured file has 13 of them and a presence-plus-non-emptiness reading would fail them all.
    assert _rejection_row_defects({**good, "matcher_recheck": None}) == []


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


# --------------------------------------------------------------------------------------------
# The authored set against the reconstruction, per stratum source.
#
# The reconstruction test above asserts the count and the not-rejected property, never the set,
# so a selected set that is the right size but the wrong members passes it. What follows asserts
# the members, for every drawing source rather than for one.
#
# It exists because a rejection can free a target and reopen an entry select_distinct_target had
# skipped: draw index 4 held art_72 and was a pass when the walk was screened, draw index 10 was
# skipped for that reason, and when draw 4 was later rejected draw 10 became eligible and entered
# the reconstruction while the query rows still named the older set.
# --------------------------------------------------------------------------------------------

# Frame stratum to query-row type, derived by inverting the committed map rather than restated.
# Row `type` names the pre-registered stratum and `subtype` names the frame's source key within
# it verbatim, which is why the twelve clean multi-hop rows carry multi_hop / eu_internal_xref.
FRAME_STRATUM_TO_ROW_TYPE = {
    frame_stratum: row_type
    for row_type, frame_strata in STRATUM_TO_FRAME.items()
    for frame_stratum in frame_strata
}


def _draw_order_key(candidate):
    """A draw-order entry as a hashable key. Pairs become tuples, bare units stay strings.

    Entry shape does not follow stratum: near_miss/block_clusters entries are bare strings while
    action_to_parent/action_subcategory entries are pairs, so this cannot be inferred from the
    stratum name. Applying tuple() blindly would turn a bare unit id into a tuple of characters.
    """
    return tuple(candidate) if isinstance(candidate, list) else candidate


def _recorded_drawn_unit(row_id: str) -> str | None:
    """The drawn unit as the verification record states it, or None where no record carries one.

    drawn_unit is recorded rather than derived, deliberately: the draw-order intersection below
    is a derivation, the field is a record, and two independent implementations beat one.
    """
    record = _verification().get(row_id)
    if not record:
        return None
    for block in ("single_hop",):
        if record.get(block):
            return record[block].get("drawn_unit")
    return None


def _bare_unit_key(row, spec):
    """The candidate a row was drawn from, for a source whose draw order holds bare unit ids.

    Not simply expected_units, because a gold slot is satisfied by any carrying unit and may name
    carriers outside this source. The frame's own cross_stratum_gold_govern_1_3 finding records
    that the statement single-hop draws at nist_ai_100_1:sub_GOVERN_1.3 is the same statement
    action-to-parent draws at nist_ai_600_1:sub_GOVERN_1.3, so one slot is satisfied by either
    carrier under the any-carrier gold rule, and the second is not a candidate of this source.
    That draw sits at index 2 of nist_ai_100_1's draw order, which stays true whether or not
    screening rejects it. The row's gold is intersected with the source's FULL candidate
    population, which is the eligibility list and not the selection, so this derives the key
    without consulting the answer it is about to check.

    THE INTERSECTION IS NOT ALWAYS A SINGLETON, and an earlier form of this function asserted
    that it was. A slot member can itself be an eligible candidate of the same source when both
    units come from the same document: eu_ai_act:art_113's slot carries eu_ai_act:rct_179 and
    eu_ai_act:rct_111's carries eu_ai_act:art_3, and all four are in eu_ai_act's 298-candidate
    eligibility list, so those two rows intersect at two. The disambiguator is the recorded
    drawn_unit, which the screening record carries for exactly this case. The derivation stays
    the sole authority where the intersection is a singleton, so the record cannot quietly
    redirect a row that the draw order already determines; where it is ambiguous the record
    decides and must name one of the candidates the derivation surfaced, which is what stops the
    field from pointing anywhere it likes.
    """
    hits = sorted(set(row["expected_units"]) & {str(c) for c in spec["draw_order"]})
    assert hits, (
        f"{row['id']}: gold names none of this source's candidates, so the row does not join to "
        f"the source its subtype names. Gold {sorted(row['expected_units'])}."
    )
    recorded = _recorded_drawn_unit(row["id"])
    if len(hits) == 1:
        # The derivation decides. A record that disagrees is a defect either way, so it fails
        # here rather than being ignored; silence on a disagreement is the blind-detector form
        # of V20 this repository has already paid for three times.
        assert recorded in (None, hits[0]), (
            f"{row['id']}: the draw order determines the drawn unit as {hits[0]} and the "
            f"verification record states {recorded}. Two implementations disagree; neither is "
            "assumed right."
        )
        return hits[0]
    assert recorded is not None, (
        f"{row['id']}: gold names {len(hits)} of this source's candidates, {hits}, so the drawn "
        "candidate is ambiguous from the row alone, and no verification record carries a "
        "drawn_unit to disambiguate it. Record one rather than narrowing the gold slot: the slot "
        "is what the any-carrier gold rule makes it, and it is not the place to encode a draw."
    )
    assert recorded in hits, (
        f"{row['id']}: the verification record states drawn_unit {recorded}, which is not among "
        f"this source's candidates named by the row's gold, {hits}."
    )
    return recorded


def _pair_key(row, spec):
    """A row drawn from a pair-shaped draw order. Order is load-bearing between slots: on one of
    the twelve committed clean multi-hop picks the reversed pair is itself a separate draw-order
    entry, so the pair is not order-free."""
    return tuple(row["expected_units"])


# Which element of a candidate a row is keyed by differs per source, so each is named rather than
# inferred, following the same practice as tests/test_unit_chunk_cardinality.py. Absent on
# purpose: action_to_parent/action_subcategory, near_miss/block_clusters and
# near_miss/near_duplicate have no authored rows and no settled row shape. They are not defaulted,
# so the first row authored against them fails here rather than being skipped silently.
KEY_EXTRACTORS = {
    ("single_hop", "eu_ai_act"): _bare_unit_key,
    ("single_hop", "nist_ai_100_1"): _bare_unit_key,
    ("single_hop", "nist_ai_600_1"): _bare_unit_key,
    ("clean_multi_hop", "eu_internal_xref"): _pair_key,
}


def _query_rows() -> list[dict]:
    if not QUERIES.exists():
        pytest.skip(f"{QUERIES.name} is not committed yet")
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _rejected_by_source() -> dict:
    out: dict[tuple[str, str], set[str]] = {}
    for record in _rejections():
        out.setdefault((record["stratum"], record["source"]), set()).add(
            json.dumps(record["rejected"])
        )
    return out


def _rows_of(rows, stratum, source):
    return [r for r in rows
            if r["type"] == FRAME_STRATUM_TO_ROW_TYPE[stratum] and r["subtype"] == source]


def _verdicts(frame, rejected_by_source, rows) -> dict:
    """Authored against reconstructed, per source, for every source that has authored rows.

    One function so the check and its companion drive the same comparison rather than two copies.
    """
    near_miss = _near_miss_selected(frame, rejected_by_source)
    out = {}
    for stratum, source, spec in _sources(frame):
        mine = _rows_of(rows, stratum, source)
        if not mine:
            continue
        extractor = KEY_EXTRACTORS.get((stratum, source))
        assert extractor is not None, (
            f"{stratum}/{source}: {len(mine)} rows are authored against this source and no key "
            "extractor is registered for it. Which element of a candidate carries gold differs "
            "per source, so add an entry to KEY_EXTRACTORS deliberately rather than defaulting."
        )
        picks = (near_miss[source] if stratum == "near_miss"
                 else _selected(spec, rejected_by_source.get((stratum, source), set())))
        out[(stratum, source)] = {
            "rows": len(mine),
            "allocation": spec["allocation"],
            "authored": {extractor(r, spec) for r in mine},
            "reconstructed": {_draw_order_key(c) for c in picks},
        }
    return out


def test_authored_rows_reconstruct_from_the_draw_order_per_source():
    """Every unit a source's rows were authored against is in that source's reconstruction, and
    once the source's row count reaches its allocation the two sets are equal.

    Bound at every commit, exactness at completion, the form
    tests/test_test_queries.py::test_row_count_per_stratum_matches_the_frame already uses: a
    stratum authored in batches is partial by construction until the last batch lands, and
    demanding equality at every commit could not survive incremental authoring. The subset half
    catches the reopened-skip cascade on the first commit after the reconstruction moves, without
    waiting for the stratum to seal.

    Per source, not per stratum: single_hop has three sources whose reconstructions are disjoint
    by document, so comparing a union would hide which source drifted.
    """
    frame = _frame()
    verdicts = _verdicts(frame, _rejected_by_source(), _query_rows())
    assert verdicts, "no committed query row joins to any frame drawing source"
    for (stratum, source), v in verdicts.items():
        where = f"{stratum}/{source}"
        assert v["rows"] <= v["allocation"], (
            f"{where}: {v['rows']} authored rows over the frame's allocation of {v['allocation']}"
        )
        assert len(v["authored"]) == v["rows"], (
            f"{where}: {v['rows']} rows collapse to {len(v['authored'])} distinct candidates, so "
            "two rows were authored against the same draw-order entry"
        )
        assert v["authored"] <= v["reconstructed"], (
            f"{where}: rows were authored against candidates the reconstruction does not select; "
            f"authored only {sorted(v['authored'] - v['reconstructed'])}"
        )
        if v["rows"] == v["allocation"]:
            assert v["authored"] == v["reconstructed"], (
                f"{where}: the source is full at {v['rows']} of {v['allocation']} and the two sets "
                f"differ; reconstructed only {sorted(v['reconstructed'] - v['authored'])}, "
                f"authored only {sorted(v['authored'] - v['reconstructed'])}"
            )


def test_authored_reconstruction_check_can_fail():
    """V20: the check above is shown capable of failing before it is trusted.

    Drops one rejection, which reopens an entry select_distinct_target had skipped and changes the
    reconstruction, and asserts the same comparison the check runs now reports a mismatch. Driven
    through _verdicts rather than a private copy, so what is shown to fail is what runs.

    Not vacuous at landing: clean_multi_hop is at twelve rows against an allocation of twelve, so
    the exactness branch is live and the control has real data to move.
    """
    frame = _frame()
    rows = _query_rows()
    key = ("clean_multi_hop", "eu_internal_xref")
    full = _rejected_by_source()
    baseline = _verdicts(frame, full, rows)
    assert key in baseline, "no clean_multi_hop rows committed, so this control has nothing to drive"
    assert baseline[key]["rows"] == baseline[key]["allocation"], (
        "the control assumes clean_multi_hop is full, so that the exactness branch is the one "
        f"being shown to fail; it is at {baseline[key]['rows']} of {baseline[key]['allocation']}"
    )
    assert baseline[key]["authored"] == baseline[key]["reconstructed"]

    dropped = json.dumps(["eu_ai_act:art_9", "eu_ai_act:art_72"])
    assert dropped in full[key], "the rejection this control drops is no longer in the log"
    perturbed_log = {k: (v - {dropped} if k == key else v) for k, v in full.items()}
    perturbed = _verdicts(frame, perturbed_log, rows)

    assert perturbed[key]["reconstructed"] != baseline[key]["reconstructed"], (
        "dropping a rejection did not change the reconstruction; the control moves nothing"
    )
    assert perturbed[key]["authored"] != perturbed[key]["reconstructed"], (
        "the reconstruction moved and the equality comparison did not detect it; check is blind"
    )
    assert not perturbed[key]["authored"] <= perturbed[key]["reconstructed"], (
        "the reconstruction moved and the subset comparison did not detect it; check is blind"
    )


def test_drop_a_rejection_control_holds_for_every_full_source():
    """V20 generalised: the same control, per source, on whatever data has landed.

    The companion above pins one cascade specifically and names its literals, which is what
    makes it evidence about the reopened-skip case. It covers one source. This runs the same
    comparison over EVERY source that is full and carries at least one rejection, so a stratum
    gains the control at the commit its rows land rather than at a later one, and so the
    control's coverage grows with the file instead of staying where it was written.

    Deliberately not driven by a synthetic rejection log. A fixture would exercise the
    reconstruction against rows nobody screened, which proves the code path runs and nothing
    about the artifact. Sources with no authored rows are skipped, so this is silent for a
    stratum until its data arrives and then binding, and the skip list is reported.

    single_hop's three sources carry no distinctness rule, so their walks are monotone: dropping
    a rejection lets the dropped candidate back in and pushes the marginal entry out. That the
    reconstruction MOVES is asserted rather than assumed, so a source where the drop changes
    nothing fails here instead of yielding a control that cannot fail.
    """
    frame = _frame()
    rows = _query_rows()
    full = _rejected_by_source()
    baseline = _verdicts(frame, full, rows)

    exercised, skipped = [], []
    for key, v in sorted(baseline.items()):
        where = f"{key[0]}/{key[1]}"
        if v["rows"] != v["allocation"]:
            skipped.append(f"{where}: {v['rows']} of {v['allocation']} rows, not full")
            continue
        if not full.get(key):
            skipped.append(f"{where}: full, but the log carries no rejection to drop")
            continue
        assert v["authored"] == v["reconstructed"], f"{where}: baseline is already mismatched"

        for dropped in sorted(full[key]):
            perturbed_log = {k: (val - {dropped} if k == key else val) for k, val in full.items()}
            perturbed = _verdicts(frame, perturbed_log, rows)
            assert perturbed[key]["reconstructed"] != v["reconstructed"], (
                f"{where}: dropping rejection {dropped} did not change the reconstruction, so "
                "the control moves nothing and would pass whatever the authored set held"
            )
            assert perturbed[key]["authored"] != perturbed[key]["reconstructed"], (
                f"{where}: the reconstruction moved when {dropped} was dropped and the equality "
                "comparison did not detect it; the check is blind"
            )
            assert not perturbed[key]["authored"] <= perturbed[key]["reconstructed"], (
                f"{where}: the reconstruction moved when {dropped} was dropped and the subset "
                "comparison did not detect it; the check is blind"
            )
        exercised.append(f"{where}: {len(full[key])} rejections each shown to move the walk")

    assert exercised, (
        "no source is both full and carrying a rejection, so this control exercised nothing. "
        f"Sources considered and why each was skipped: {skipped}"
    )


def test_every_authored_source_has_a_registered_key_extractor():
    """No silent default. A source that gains rows without a KEY_EXTRACTORS entry must fail rather
    than be skipped, and the table must not name a source the frame does not have."""
    frame = _frame()
    frame_sources = {(stratum, source) for stratum, source, _ in _sources(frame)}
    assert set(KEY_EXTRACTORS) <= frame_sources, (
        f"KEY_EXTRACTORS names sources the frame does not have: "
        f"{sorted(set(KEY_EXTRACTORS) - frame_sources)}"
    )
    rows = _query_rows()
    for stratum, source in sorted(frame_sources):
        if _rows_of(rows, stratum, source):
            assert (stratum, source) in KEY_EXTRACTORS, (
                f"{stratum}/{source} has authored rows and no registered key extractor"
            )
