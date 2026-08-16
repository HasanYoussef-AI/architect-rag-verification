"""The pass boundary, made checkable from git rather than asserted.

eval/pass_one_designations.jsonl is committed at the boundary between pass one and pass two: it
carries, for each accepted pick of the two remaining strata, what screening fixed and nothing
else. The commit that places it holds no query text, so a later commit carrying query text
postdates it, and the ordering a reviewer can check is the ordering git records.

Classes alone would prove only that the classes predate the query text. The binding designations
ride with them for a reason: on the sequence without them, the span and the query text it binds
would arrive in the same commit and nothing would order them. The single-hop stratum recorded
that gap and could not repair it, its evidence being file mtimes in an untracked tree. C2 and C3
below are what close it.

Two groups of checks. B1 to B9 are live the moment the artifact lands. C1 to C6 are vacuous until
the authored rows arrive and binding from the commit each one does, which is the same ordering
every other check in this scope follows: a check landing beside the rows it judges cannot be
distinguished from a check written to fit them.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from tests.test_test_frame import (
    KEY_EXTRACTORS,
    _draw_order_key,
    _frame,
    _rejected_by_source,
    _selected,
    _sources,
    _near_miss_selected,
)
from tests.test_test_queries import STRATUM_TO_FRAME

EVAL = REPO_ROOT / "eval"
DESIGNATIONS = EVAL / "pass_one_designations.jsonl"
QUERIES = EVAL / "test_queries.jsonl"
VERIFICATION = EVAL / "test_query_verification.jsonl"
CHUNKS = REPO_ROOT / "data" / "chunks"

# The whole key set, ordered, pinned as a literal. This is a whitelist and it is what enforces
# the must-not-contain list by construction: no prediction content, no arms, no slot, no verdict
# and no query can appear without editing this line, which is a deliberate act that shows in the
# diff. A blacklist of forbidden names would be a structural detector for a content claim, the
# failure this repository has already paid for three times.
FIELDS = ["id_predicted", "stratum", "source", "draw_index", "draw_entry",
          "binding_designation", "question_class", "question_class_fixed_at"]

FIXED_AT = "pass one screening, before any query text for this row existed"

# The sources these two strata draw from, in the order ids are assigned: action-to-parent first,
# then near-miss with block_clusters ahead of near_duplicate on canonical_offset_order.
SOURCE_ORDER = [("action_to_parent", "action_subcategory"),
                ("near_miss", "block_clusters"),
                ("near_miss", "near_duplicate")]

FIRST_ID = 39


def _rows() -> list[dict]:
    if not DESIGNATIONS.exists():
        pytest.skip(f"{DESIGNATIONS.name} is not committed yet")
    return [json.loads(line) for line in DESIGNATIONS.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _query_rows() -> list[dict]:
    if not QUERIES.exists():
        return []
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _verification() -> dict[str, dict]:
    if not VERIFICATION.exists():
        return {}
    return {r["id"]: r
            for r in (json.loads(line)
                      for line in VERIFICATION.read_text(encoding="utf-8").splitlines()
                      if line.strip())}


def _chunk_text() -> dict[str, str]:
    out = {}
    for path in sorted(CHUNKS.glob("*.chunks.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                out[c["chunk_id"]] = c["text"]
    return out


# ---------------------------------------------------------------------------------------------
# B, live from the commit that places the artifact.


# ---------------------------------------------------------------------------------------------
# B, live from the commit that places the artifact.
#
# ONE PREDICATE, driven by the checks and by their companion alike. An earlier form of this file
# had the companion drive a private reimplementation of the same logic, so weakening a check left
# its companion green and the companion proved nothing about the check it was written for. That
# is the second-copy failure the rejection-row predicate in tests/test_test_frame.py already
# exists to avoid, and it was caught here by mutating each check and observing the companion did
# not move. Defects are tagged so each check can assert on its own class while all of them run
# the same code.


def _context():
    return {"frame": _frame(), "text": _chunk_text(),
            "queries": [r["query"] for r in _query_rows()]}


def _row_defects(row: dict, ctx: dict) -> list[tuple[str, str]]:
    """Every way one artifact row violates the boundary requirements, tagged by check."""
    out: list[tuple[str, str]] = []
    frame, text, queries = ctx["frame"], ctx["text"], ctx["queries"]

    if list(row.keys()) != FIELDS:
        out.append(("b1", f"key set {list(row.keys())} against the pinned set {FIELDS}"))
        return out  # every check below reads keys this row may not have

    pair = (row["stratum"], row["source"])
    if pair not in {(s, n) for s, n, _ in _sources(frame)}:
        out.append(("b2", f"{pair} is not a frame drawing source"))
        return out
    if pair not in KEY_EXTRACTORS:
        out.append(("b2", f"{pair} has no registered key extractor"))

    spec = frame["strata"][row["stratum"]]["sources"][row["source"]]
    order = spec["draw_order"]
    if json.dumps(row["draw_entry"]) not in {json.dumps(c) for c in order}:
        out.append(("b3", "draw_entry is not a candidate of this source"))
    # SUBSUMED, and recorded as such rather than presented as an independent check. Under the
    # membership test above, which compares json.dumps, no value can have the wrong shape and
    # still be a member, so this branch cannot be the sole cause of a defect and a mutation
    # disabling it leaves every companion green. Measured, not assumed: disabling it was run and
    # observed green. It stays as a guard against a future membership test that stringifies both
    # sides, where shape would stop being implied, and it shares b3's tag because it is not
    # separately demonstrable today.
    expected = list if isinstance(order[0], list) else str
    if not isinstance(row["draw_entry"], expected):
        out.append(("b3", f"{row['source']} draws {expected.__name__} entries and this row "
                          f"carries {type(row['draw_entry']).__name__}"))
    if not (0 <= row["draw_index"] < len(order)):
        out.append(("b4", f"draw_index {row['draw_index']} out of range"))
    elif order[row["draw_index"]] != row["draw_entry"]:
        out.append(("b4", f"draw_index {row['draw_index']} holds a different entry"))

    d = row["binding_designation"]
    if set(d) != {"span", "chunk_id"}:
        out.append(("b5", f"binding_designation keys {sorted(d)}"))
    elif d["chunk_id"] not in text:
        out.append(("b5", f"no such chunk {d['chunk_id']}"))
    else:
        if d["span"] not in text[d["chunk_id"]]:
            out.append(("b5", f"the span does not occur in {d['chunk_id']}"))
        unit = d["chunk_id"].split("#", 1)[0]
        entry = row["draw_entry"]
        pick = (entry[1] if row["stratum"] == "action_to_parent"
                else entry[0] if isinstance(entry, list) else entry)
        if unit != pick:
            out.append(("b5", f"the span sits in {unit}, which is not the pick {pick}"))

    if not (isinstance(row["question_class"], str) and row["question_class"].strip()):
        out.append(("b7", "empty question_class"))
    if row["question_class_fixed_at"] != FIXED_AT:
        out.append(("b7", f"fixed-at marker {row['question_class_fixed_at']!r}"))

    blob = json.dumps(row, ensure_ascii=False)
    for q in queries:
        if q in blob:
            out.append(("b8", f"a committed query text appears in this row: {q!r}"))
        if row["question_class"] and row["question_class"] in q:
            out.append(("b8", "this row's class is contained in a committed query, so the "
                              "boundary between a class and a query has collapsed"))
    return out


def _defects(tag: str) -> list[str]:
    ctx = _context()
    return [f"{r.get('id_predicted')}: {m}"
            for r in _rows() for t, m in _row_defects(r, ctx) if t == tag]


def test_b1_one_ordered_key_set_over_every_row():
    """The whitelist. Ordered rather than set equality, the stronger form, and pinned rather than
    derived from the file: a literal is what makes an added field fail instead of being adopted.
    It is also what enforces the must-not-contain list, since no prediction content, arm, slot,
    verdict or query can appear without editing the literal, which shows in the diff."""
    assert _rows(), f"{DESIGNATIONS.name} is present but empty"
    assert not _defects("b1"), "; ".join(_defects("b1"))


def test_b2_every_row_names_a_registered_drawing_source():
    assert not _defects("b2"), "; ".join(_defects("b2"))


def test_b3_every_draw_entry_is_a_candidate_of_its_source_in_that_source_s_shape():
    """The entry verbatim, and its SHAPE per source: block_clusters draws bare unit ids while the
    other two draw pairs, so a pair where a string belongs would pass a membership test that
    stringifies both sides."""
    assert not _defects("b3"), "; ".join(_defects("b3"))


def test_b4_draw_index_indexes_that_entry():
    assert not _defects("b4"), "; ".join(_defects("b4"))


def test_b5_every_span_occurs_in_the_chunk_its_row_names():
    """Sliced from data/chunks rather than from a reconstructed unit text, so this pins that the
    recorded chunk is the one the span sits in and that the chunk belongs to the pick. A span with
    the right text against the wrong chunk id is invisible in the span alone."""
    assert not _defects("b5"), "; ".join(_defects("b5"))


def test_b7_every_row_carries_a_class_and_the_fixed_at_marker():
    assert not _defects("b7"), "; ".join(_defects("b7"))


def test_b8_no_value_in_the_artifact_carries_committed_query_text():
    """The content half of the must-not-contain list.

    B1's whitelist bars an added FIELD. It cannot bar a query smuggled into a value spelled as a
    class, which is a content claim and has to be checked against content. Compared in both
    directions, since a class containing a query and a query containing a class are the same
    defect seen from two sides.
    """
    if not _context()["queries"]:
        pytest.skip("no committed query rows to compare against")
    assert not _defects("b8"), "; ".join(_defects("b8"))


def test_b6_ids_are_contiguous_and_ordered_by_source_then_draw_index():
    """Ordering derived from canonical_offset_order rather than restated, so a frame change
    reports the move instead of leaving this asserting a stale sequence."""
    rows = _rows()
    ids = [r["id_predicted"] for r in rows]
    assert ids == [f"test_{FIRST_ID + i}" for i in range(len(rows))], ids
    assert len(set(ids)) == len(ids)

    canonical = [tuple(p) for p in _frame()["canonical_offset_order"]]
    for pair in SOURCE_ORDER:
        assert pair in canonical, f"{pair} is not in canonical_offset_order"
    near = [p for p in SOURCE_ORDER if p[0] == "near_miss"]
    assert near == [p for p in canonical if p[0] == "near_miss"], (
        "the near-miss source order here disagrees with canonical_offset_order")

    seen = [(r["stratum"], r["source"], r["draw_index"]) for r in rows]
    expected = sorted(seen, key=lambda t: (SOURCE_ORDER.index((t[0], t[1])), t[2]))
    assert seen == expected, f"rows are not ordered by source then draw index: {seen}"


def test_b9_the_twelve_picks_reconstruct_from_the_draw_order_and_the_rejection_log():
    """The selection justified at the boundary rather than three commits later.

    The rejection rows land with this artifact precisely so this can run here: an artifact naming
    a pick set that nothing can reconstruct would assert a selection on no evidence.
    """
    frame = _frame()
    rejected = _rejected_by_source()
    near_miss = _near_miss_selected(frame, rejected)
    rows = _rows()
    for stratum, source in SOURCE_ORDER:
        mine = [r for r in rows if (r["stratum"], r["source"]) == (stratum, source)]
        if not mine:
            continue
        spec = frame["strata"][stratum]["sources"][source]
        picks = (near_miss[source] if stratum == "near_miss"
                 else _selected(spec, rejected.get((stratum, source), set())))
        assert len(mine) == spec["allocation"], (
            f"{stratum}/{source}: {len(mine)} artifact rows against allocation "
            f"{spec['allocation']}")
        artifact = {_draw_order_key(r["draw_entry"]) for r in mine}
        reconstructed = {_draw_order_key(c) for c in picks}
        assert artifact == reconstructed, (
            f"{stratum}/{source}: the artifact's picks are not the reconstruction. "
            f"artifact only {sorted(artifact - reconstructed)}, "
            f"reconstruction only {sorted(reconstructed - artifact)}")


# ---------------------------------------------------------------------------------------------
# C, vacuous until the authored rows land and binding from the commit each one does.


def _landed():
    """(artifact row, query row, verification record) for every id that now exists."""
    queries = {r["id"]: r for r in _query_rows()}
    verification = _verification()
    out = []
    for row in _rows():
        q = queries.get(row["id_predicted"])
        if q is not None:
            out.append((row, q, verification.get(row["id_predicted"])))
    return out


def _block_of(record):
    for name in ("action_to_parent", "near_miss"):
        if record and record.get(name):
            return record[name]
    return None


def test_c1_landed_rows_map_to_the_artifact_s_stratum_and_source():
    landed = _landed()
    if not landed:
        pytest.skip("no artifact id has an authored row yet")
    invert = {fs: rt for rt, strata in STRATUM_TO_FRAME.items() for fs in strata}
    for row, q, _ in landed:
        assert q["type"] == invert[row["stratum"]], (
            f"{row['id_predicted']}: row type {q['type']}, artifact stratum {row['stratum']}")
        assert q["subtype"] == row["source"], (
            f"{row['id_predicted']}: row subtype {q['subtype']}, artifact source {row['source']}")


def test_c2_the_binding_designation_is_unchanged_from_the_boundary():
    """The pin that makes this commit worth landing. The span the row is authored against must be
    the span committed before the query existed, byte for byte, chunk id included."""
    landed = _landed()
    if not landed:
        pytest.skip("no artifact id has an authored row yet")
    checked = 0
    for row, _, record in landed:
        block = _block_of(record)
        assert block is not None, f"{row['id_predicted']}: no stratum block on its record"
        checked += 1
        assert block["binding_designation"] == row["binding_designation"], (
            f"{row['id_predicted']}: the designation moved between the boundary and the row.\n"
            f"  boundary: {row['binding_designation']}\n  row     : {block['binding_designation']}")
    assert checked, "no landed row carried a stratum block, so this compared nothing"


def test_c3_the_question_class_and_its_marker_are_unchanged_from_the_boundary():
    landed = _landed()
    if not landed:
        pytest.skip("no artifact id has an authored row yet")
    for row, _, record in landed:
        block = _block_of(record)
        assert block["question_class"] == row["question_class"], (
            f"{row['id_predicted']}: the class moved between the boundary and the row")
        assert block["question_class_fixed_at"] == row["question_class_fixed_at"], (
            f"{row['id_predicted']}: the fixed-at marker moved")


def test_c4_the_row_keys_back_to_the_artifact_s_draw_entry():
    """Through the source's registered extractor, so the join is the same one the reconstruction
    test uses rather than a second implementation of it."""
    landed = _landed()
    if not landed:
        pytest.skip("no artifact id has an authored row yet")
    frame = _frame()
    for row, q, _ in landed:
        spec = frame["strata"][row["stratum"]]["sources"][row["source"]]
        extractor = KEY_EXTRACTORS[(row["stratum"], row["source"])]
        assert extractor(q, spec) == _draw_order_key(row["draw_entry"]), (
            f"{row['id_predicted']}: the row keys to a different draw entry than the artifact")


def test_c5_every_artifact_row_either_has_its_id_or_a_rejection_at_authoring():
    """Scoped for the pass-two rejection contingency, which the single-hop scope hit four times.

    An authoring rejection appends its row to the log, and the replacement is screened after a
    reviewed boundary and appends its own designation and class in a correction commit. So the
    property that holds at every commit is not that every predicted id exists, but that a
    predicted id either exists or its draw entry is in the rejection log marked rejected at
    authoring. A pick that simply vanished satisfies neither.
    """
    rows = _rows()
    queries = {r["id"] for r in _query_rows()}
    if not queries & {r["id_predicted"] for r in rows}:
        pytest.skip("no artifact id has an authored row yet")
    if len(_query_rows()) != 50:
        pytest.skip("the query file has not reached its grand total")
    rejected_at_authoring = {
        json.dumps(r["rejected"])
        for r in (json.loads(line) for line in
                  (EVAL / "test_frame_rejections.jsonl").read_text(encoding="utf-8").splitlines()
                  if line.strip())
        if r.get("rejected_at") == "authoring"
    }
    for row in rows:
        if row["id_predicted"] in queries:
            continue
        assert json.dumps(row["draw_entry"]) in rejected_at_authoring, (
            f"{row['id_predicted']}: predicted at the boundary, absent from the query file, and "
            "not in the rejection log as rejected at authoring. A pick cannot simply vanish")


def test_c6_the_predicted_id_matches_the_row_that_carries_its_draw_entry():
    """Asserted apart from C4 on purpose. A pass-two rejection shifts every id after it, and that
    must report as an id prediction contradicted, not as a lost pick, so the two failure modes
    carry different messages."""
    landed = _landed()
    if not landed:
        pytest.skip("no artifact id has an authored row yet")
    frame = _frame()
    for row, _, _ in landed:
        spec = frame["strata"][row["stratum"]]["sources"][row["source"]]
        extractor = KEY_EXTRACTORS[(row["stratum"], row["source"])]
        matching = [q["id"] for q in _query_rows()
                    if q["subtype"] == row["source"]
                    and extractor(q, spec) == _draw_order_key(row["draw_entry"])]
        assert matching == [row["id_predicted"]], (
            f"{row['id_predicted']}: the id predicted at the boundary is contradicted. The row "
            f"carrying this draw entry is {matching}. If a pass-two rejection shifted the ids, "
            "correct the artifact and log it rather than loosening this")


# ---------------------------------------------------------------------------------------------
# V20. Each check driven against the defect it exists to catch, through _row_defects, the
# predicate the checks themselves run. Not a private copy: a private copy stays green when the
# check is weakened, which is how the earlier form of this section was found wanting.


def _a_good_row():
    return json.loads(json.dumps(_rows()[0]))


def _tags(row):
    return {t for t, _ in _row_defects(row, _context())}


def test_the_predicate_passes_a_well_formed_row():
    """The baseline, or every failure below proves nothing."""
    for row in _rows():
        assert _row_defects(row, _context()) == [], f"{row['id_predicted']}"


def test_b1_can_fail():
    good = _a_good_row()
    assert "b1" in _tags({**good, "retrieval_mechanism_prediction": {"prediction": "miss"}}), (
        "a prediction field was not caught, so the whitelist bars nothing")
    assert "b1" in _tags({**good, "query": "what does GOVERN 2.3 list?"}), (
        "a query field was not caught")
    assert "b1" in _tags({k: v for k, v in good.items() if k != "question_class"}), (
        "a missing class was not caught")
    assert "b1" in _tags(dict(reversed(list(good.items())))), (
        "a reordered key set was not caught, so the order is not pinned")


def test_b2_and_b3_and_b4_can_fail():
    good = _a_good_row()
    assert "b2" in _tags({**good, "source": "eu_internal_xref"}), (
        "a source this stratum does not draw from was not caught")
    assert "b3" in _tags({**good, "draw_entry": ["nowhere:unit_a", "nowhere:unit_b"]}), (
        "a draw entry the source does not hold was not caught")
    assert "b4" in _tags({**good, "draw_index": good["draw_index"] + 1}), (
        "a draw index pointing at a different entry was not caught")

    bare = next(r for r in _rows() if r["source"] == "block_clusters")
    paired = next(r for r in _rows() if r["source"] == "near_duplicate")
    assert "b3" in _tags({**bare, "draw_entry": [bare["draw_entry"], bare["draw_entry"]]}), (
        "a pair where block_clusters draws a bare unit id was not caught")
    assert "b3" in _tags({**paired, "draw_entry": paired["draw_entry"][0]}), (
        "a bare unit id where near_duplicate draws a pair was not caught")


def test_b5_can_fail_including_the_chunk_pairing():
    good = _a_good_row()
    other = next(r for r in _rows()
                 if r["binding_designation"]["chunk_id"] != good["binding_designation"]["chunk_id"])
    # Ownership isolated from the span-in-chunk half. Handing this row the OTHER pick's whole
    # designation, span and chunk together, leaves the span genuinely present in the chunk it
    # names, so only the ownership branch can fire. An earlier form swapped the chunk alone,
    # which the span-in-chunk branch also caught, and the two sharing a tag meant disabling
    # ownership left the companion green. That was found by mutating the branch and watching
    # this test not move.
    assert "b5" in _tags({**good, "binding_designation": other["binding_designation"]}), (
        "a designation belonging to another pick was not caught, which is the pairing defect a "
        "span read on its own cannot show")
    assert "b5" in _tags({**good, "binding_designation": {
        "span": good["binding_designation"]["span"] + " not in the chunk",
        "chunk_id": good["binding_designation"]["chunk_id"]}}), (
        "a span absent from its own chunk was not caught")


def test_b7_can_fail():
    good = _a_good_row()
    assert "b7" in _tags({**good, "question_class": "   "}), "a blank class was not caught"
    assert "b7" in _tags({**good, "question_class_fixed_at": "later"}), (
        "a reworded fixed-at marker was not caught")


def test_b8_can_fail_on_a_planted_query():
    queries = _context()["queries"]
    if not queries:
        pytest.skip("no committed query rows to drive this")
    assert "b8" in _tags({**_a_good_row(), "question_class": queries[0]}), (
        "a committed query planted as a class was not caught")


def test_b6_can_fail():
    rows = _rows()
    ids = [r["id_predicted"] for r in rows]
    gapped = ids[:-1] + [f"test_{FIRST_ID + len(rows)}"]
    assert gapped != [f"test_{FIRST_ID + i}" for i in range(len(rows))], (
        "a skipped id was not detected by the contiguity comparison")
    shuffled = [(r["stratum"], r["source"], r["draw_index"]) for r in reversed(rows)]
    expected = sorted(shuffled, key=lambda t: (SOURCE_ORDER.index((t[0], t[1])), t[2]))
    assert shuffled != expected, (
        "reversing the rows did not change the ordering comparison, so the order is not pinned")


def test_b9_can_fail():
    """Drop the action-to-parent rejection and the reconstruction moves off the artifact."""
    frame = _frame()
    full = _rejected_by_source()
    key = ("action_to_parent", "action_subcategory")
    assert full.get(key), "no action_to_parent rejection is committed, so this control is empty"
    spec = frame["strata"][key[0]]["sources"][key[1]]
    artifact = {_draw_order_key(r["draw_entry"]) for r in _rows()
                if (r["stratum"], r["source"]) == key}
    assert {_draw_order_key(c) for c in _selected(spec, full[key])} == artifact, (
        "the baseline reconstruction already disagrees with the artifact")
    assert {_draw_order_key(c) for c in _selected(spec, set())} != artifact, (
        "dropping the rejection did not move the reconstruction, so B9 would pass whatever the "
        "artifact held")
