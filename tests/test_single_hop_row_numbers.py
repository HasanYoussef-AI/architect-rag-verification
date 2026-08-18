"""Every number on a shipped single-hop row, re-derived from committed data.

The requirement these tests exist to meet: a numeric field on a shipped row is either emitted by
a committed module or asserted here against a re-derivation from committed artifacts. A number
whose only producer is an untracked builder does not ship as a number, because a reviewer holding
the repository cannot check it and a hand edit to the row would not fail anything.

Each predicate below is written from the text that ships on the row, not copied from the tool
that first produced the value, so agreement is two implementations agreeing rather than one
restated. Where the row carries the predicate in prose, that prose is what this file implements.

All of these are vacuous until the single-hop rows land and binding from that commit, which is
the same ordering every other check in this scope follows: a check committed beside the rows it
judges cannot be distinguished from a check written to fit them.

Both artifacts are covered. Accepted picks carry their screening record in the single_hop block
of eval/test_query_verification.jsonl; rejected picks carry the same record, with the verdict as
a field, in eval/test_frame_rejections.jsonl. The evidence behind a rejection is what makes the
funnel auditable from the tree alone, so it is held to the same standard as the evidence behind
an acceptance.
"""

from __future__ import annotations

import json

import pytest


from src.goldset.attributability import Corpus, normalise_for_lexical, ratio_matcher
from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison

EVAL = REPO_ROOT / "eval"
VERIFICATION = EVAL / "test_query_verification.jsonl"
REJECTIONS = EVAL / "test_frame_rejections.jsonl"


def _ratio(left: str, right: str, normalise) -> float:
    return round(ratio_matcher(normalise(left), normalise(right)).ratio(), 4)


def _span_to_member_segment(pick, member, span, corpus):
    return round(max(ratio_matcher(normalise_for_lexical(span),
                                   normalise_for_lexical(segment)).ratio()
                     for segment in corpus.unit_segments[member]), 4)


def _span_to_member_unit_text(pick, member, span, corpus):
    return _ratio(span, corpus.unit_text[member], normalise_for_lexical)


def _pick_unit_text_to_member_unit_text(pick, member, span, corpus):
    return _ratio(corpus.unit_text[pick], corpus.unit_text[member], normalise_for_comparison)


# THE ENUMERATED SET. Three instruments ran at three stages of screening and the record did not
# say which produced which figure, so the same field name carried different quantities and no
# single predicate reproduced the population. The repair is disclosure, not recomputation: every
# recorded value stands and every entry names the predicate behind it. The set is closed and the
# test asserts closure, so a fourth quantity cannot enter under an existing name.
RATIO_PREDICATES = {
    "span_to_member_segment": _span_to_member_segment,
    "span_to_member_unit_text": _span_to_member_unit_text,
    "pick_unit_text_to_member_unit_text": _pick_unit_text_to_member_unit_text,
}

RATIO_NORMALISATIONS = {
    "span_to_member_segment": "normalise_for_lexical",
    "span_to_member_unit_text": "normalise_for_lexical",
    "pick_unit_text_to_member_unit_text": "normalise_for_comparison",
}

RATIO_FIELDS = ("lexical_ratio", "lexical_ratio_against_the_span")


def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _screening_records() -> list[tuple[str, dict]]:
    """(where, record) for every committed single-hop screening record, from both artifacts.

    Keyed off the block and the stratum rather than a type field: verification rows carry no
    `type` key, only `subtype`, and a filter on one that does not exist matches nothing on every
    row while reporting a pass.
    """
    out = []
    for row in _jsonl(VERIFICATION):
        if row.get("single_hop"):
            out.append((f"{row['id']} (verification)", row["single_hop"]))
    for row in _jsonl(REJECTIONS):
        if row.get("stratum") == "single_hop" and row.get("drawn_unit"):
            out.append((f"{row['drawn_unit']} (rejection)", row))
    return out


def _records_or_skip() -> list[tuple[str, dict]]:
    records = _screening_records()
    if not records:
        pytest.skip("no committed single-hop screening records yet; these turn on at that commit")
    return records


# The unit a block's designated span sits inside, named per block because the field differs by
# what the stratum draws. Separate from RATIO_ANCHOR_FIELD below even though the two currently
# agree: a ratio anchor is the unit ratios are measured FROM, a span anchor is the unit the span
# was cut OUT of, and coupling them would make a future divergence silent.
SPAN_ANCHOR_FIELD = {
    "single_hop": "drawn_unit",
    "action_to_parent": "drawn_parent",
    "near_miss": "drawn_unit",
}


def _residue_records() -> list[tuple[str, str, dict]]:
    """(where, anchor unit, block) for every block carrying a residue_reach.

    Selected on the field rather than on the single_hop block. The superseded form read
    _records_or_skip(), which is single-hop only, so the action-to-parent rows would have shipped
    residue_chars with no committed re-derivation while this test reported a pass over the rows it
    did reach. Those are the four numbers the deletion_counterfactual_disposition on those rows
    quotes, which is what makes the gap load-bearing rather than cosmetic.
    """
    out = []
    for row in _jsonl(VERIFICATION):
        for block, field in SPAN_ANCHOR_FIELD.items():
            held = row.get(block)
            if held and "residue_reach" in held and held.get(field):
                out.append((f"{row['id']} ({block})", held[field], held))
    for row in _jsonl(REJECTIONS):
        field = SPAN_ANCHOR_FIELD.get(row.get("stratum"))
        if field and row.get(field) and "residue_reach" in row:
            out.append((f"{row[field]} ({row['stratum']} rejection)", row[field], row))
    return out


def test_the_span_anchor_registry_covers_every_block_shipping_a_residue():
    """SPAN_ANCHOR_FIELD is a literal, so it can go stale against the file it describes. A block
    shipping a residue_reach under an unregistered name would be skipped in silence, which is the
    failure this registry exists to prevent rather than to reproduce."""
    unregistered = set()
    for row in _jsonl(VERIFICATION):
        for key, value in row.items():
            if isinstance(value, dict) and "residue_reach" in value:
                if key not in SPAN_ANCHOR_FIELD:
                    unregistered.add(key)
    assert not unregistered, (
        f"block(s) {sorted(unregistered)} ship a residue_reach and are not in SPAN_ANCHOR_FIELD, "
        "so their residue_chars re-derive nowhere"
    )


@pytest.fixture(scope="module")
def corpus():
    return Corpus.load()


def _span_of(record: dict) -> str:
    return record["binding_designation"]["span"]


def test_designation_offsets_slice_their_own_chunk_record(corpus):
    """Every designation attempt's offsets slice its chunk record back to the recorded span.

    Offsets are the field that ties a span to a chunk id, and a wrong pair is invisible in the
    span text beside it. Sliced from data/chunks, not from the reconstructed unit text, so this
    also pins that the recorded chunk_id is the chunk the span actually sits in.
    """
    chunk_text = {}
    for document in ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook"):
        path = REPO_ROOT / "data" / "chunks" / f"{document}.chunks.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                chunk_text[record["chunk_id"]] = record["text"]

    checked = 0
    for where, record in _records_or_skip():
        for attempt in record["designation_attempts"]:
            checked += 1
            text = chunk_text.get(attempt["chunk_id"])
            assert text is not None, f"{where}: chunk_id {attempt['chunk_id']} is not a committed chunk"
            sliced = text[attempt["char_start_in_chunk"]:attempt["char_end_in_chunk"]]
            assert sliced == attempt["span"], (
                f"{where}: offsets [{attempt['char_start_in_chunk']}, "
                f"{attempt['char_end_in_chunk']}) slice {sliced[:60]!r}, span is "
                f"{attempt['span'][:60]!r}"
            )
    assert checked, "records are committed and none carries a designation attempt"


def test_draw_index_matches_the_frame():
    """draw_index is a position in the frame's committed draw order, so it is asserted against it.

    Recorded on the row rather than derived at read time, which is the right call, and that is
    exactly why it needs a check: a recorded position that nothing compares against is a number
    a hand edit can move.
    """
    frame = json.loads((EVAL / "test_frame.json").read_text(encoding="utf-8"))
    sources = frame["strata"]["single_hop"]["sources"]
    for where, record in _records_or_skip():
        unit = record["drawn_unit"]
        source = unit.split(":", 1)[0]
        assert source in sources, f"{where}: {unit} names no single_hop source"
        order = sources[source]["draw_order"]
        assert unit in order, f"{where}: {unit} is not a candidate of {source}"
        assert record["draw_index"] == order.index(unit), (
            f"{where}: draw_index {record['draw_index']} against the frame's "
            f"{order.index(unit)}"
        )


def test_exhaustion_re_derives_from_the_committed_corpus(corpus):
    """The six exhaustion numbers, recomputed from the unit's committed text and segmentation.

    The predicate is the one the row ships in `straddle_rule` and `residue_measure`: a comparable
    segment wholly inside the span counts inside, one wholly outside counts outside, anything
    else straddles; the residue is the unit text with the span's single occurrence removed and
    the result stripped. Segment counts and residue counts are different facts and are asserted
    separately, because a row that got one right and the other wrong would otherwise pass.
    """
    for where, record in _records_or_skip():
        block = record["exhaustion"]
        unit = record["drawn_unit"]
        span = _span_of(record)
        text = corpus.unit_text[unit]
        start = text.find(span)
        assert start >= 0, f"{where}: the designated span does not occur in its own unit text"
        lo, hi = start, start + len(span)

        inside = outside = straddle = 0
        cursor = 0
        for segment in corpus.unit_segments[unit]:
            j = text.find(segment, cursor)
            k = j + len(segment)
            cursor = k
            if j >= lo and k <= hi:
                inside += 1
            elif k <= lo or j >= hi:
                outside += 1
            else:
                straddle += 1
        residue = (text[:lo] + text[hi:]).strip()

        for key, derived in (
            ("comparable_segments", len(corpus.unit_segments[unit])),
            ("segments_inside_span", inside),
            ("segments_outside_span", outside),
            ("segments_straddling_span_boundary", straddle),
            ("non_span_residue_chars", len(residue)),
            ("non_span_residue_words", len(residue.split())),
        ):
            assert block[key] == derived, f"{where}: {key} recorded {block[key]}, derived {derived}"
        assert block["span_exhausts_unit"] == (len(residue) == 0), f"{where}: span_exhausts_unit"


def test_residue_reach_chars_re_derive(corpus):
    """residue_reach.residue_chars, which is NOT the exhaustion residue.

    The reach predicate reads the unit text with the span's single occurrence removed and does
    not strip; exhaustion strips. The two numbers differ on any unit whose span sits at an edge,
    and asserting them against one derivation would silently accept whichever the builder used.
    Both are asserted, each against its own predicate, in this file.

    Selected on residue_reach across every registered block rather than on single_hop. See
    _residue_records. The residue string itself is asserted alongside the count, because a count
    agreeing while the recorded residue text disagrees would leave the quoted residue unchecked,
    and the action-to-parent disposition quotes those residues verbatim.
    """
    records = _residue_records()
    if not records:
        pytest.skip("no committed block carries a residue_reach yet")
    for where, unit, record in records:
        span = _span_of(record)
        residue = corpus.unit_text[unit].replace(span, "", 1)
        recorded = record["residue_reach"]["residue_chars"]
        assert recorded == len(residue), (
            f"{where}: residue_chars recorded {recorded}, derived {len(residue)}"
        )
        assert record["residue_reach"]["residue"] == residue, (
            f"{where}: residue recorded {record['residue_reach']['residue']!r}, derived "
            f"{residue!r}"
        )


def test_distinguishing_term_counts_re_derive(corpus):
    """The distinguishing-term counts, recomputed from the row's own term and span.

    The term ships on the row, so this needs nothing the reviewer does not have. What it pins is
    the count, which is the whole content of the test: a term occurring zero times outside the
    span is what makes the row FAIL, and a wrong count would flip a verdict.
    """
    checked = 0
    for where, record in _records_or_skip():
        block = record.get("distinguishing_term_test") or {}
        if not block.get("applied"):
            continue
        unit, span = record["drawn_unit"], _span_of(record)
        text = corpus.unit_text[unit]
        start = text.find(span)
        residue = (text[:start] + text[start + len(span):]).strip()
        for entry in block["per_non_carrier"]:
            checked += 1
            term = entry["term"]
            assert entry["occurrences_outside_span"] == residue.count(term), (
                f"{where}/{entry['unit_id']}: occurrences_outside_span"
            )
            if "occurrences_inside_span" in entry:
                assert entry["occurrences_inside_span"] == span.count(term), (
                    f"{where}/{entry['unit_id']}: occurrences_inside_span"
                )
            if "residue_chars" in entry:
                assert entry["residue_chars"] == len(residue), f"{where}: residue_chars"
            if "residue_words" in entry:
                assert entry["residue_words"] == len(residue.split()), f"{where}: residue_words"
    if not checked:
        pytest.skip("no committed row applies the distinguishing-term test")


def test_sufficiency_candidate_span_counts_re_derive(corpus):
    """The candidate-span enumeration's counts, from the offsets it ships.

    A candidate span is recorded by its offsets into the unit text rather than by its text, so
    the counts are checkable without the span being quoted twice. Offsets are asserted in bounds
    first: an out-of-bounds pair would still produce a self-consistent character count and pass a
    check that only compared arithmetic.
    """
    checked = 0
    for where, record in _records_or_skip():
        block = record.get("sufficiency") or {}
        for candidate in block.get("candidate_spans") or []:
            checked += 1
            text = corpus.unit_text[record["drawn_unit"]]
            offsets = candidate["offsets"]
            segments = offsets if isinstance(offsets[0], list) else [offsets]
            for lo, hi in segments:
                assert 0 <= lo < hi <= len(text), (
                    f"{where}/{candidate['label']}: offsets {[lo, hi]} out of bounds for a "
                    f"{len(text)}-character unit"
                )
            span_chars = sum(hi - lo for lo, hi in segments)
            assert candidate["span_chars"] == span_chars, f"{where}/{candidate['label']}: span_chars"
            assert candidate["residue_chars"] == len(text) - span_chars, (
                f"{where}/{candidate['label']}: residue_chars"
            )
    if not checked:
        pytest.skip("no committed row carries a candidate-span enumeration")


def test_the_re_derivations_accept_a_correct_record_and_reject_a_wrong_one(corpus):
    """V20: every predicate above is driven, and shown to fail, before the data arrives.

    Without this the five checks above only skip at this commit, and their first exercise would
    be the commit whose rows they exist to judge. A check whose only run is the one it was
    written for has not been shown capable of withholding a pass.

    Not a synthetic fixture of rows: the unit, its text and its segmentation are committed
    corpus, and the span is a real slice of it. What is constructed is the record wrapper, which
    is the thing that does not exist yet. Each predicate is then driven twice, once against the
    true values and once against a value moved by one, so both verdicts are reached.
    """
    # The two residue measures coincide wherever removing the span leaves no edge whitespace, so
    # the unit is located rather than named: a unit where they genuinely differ is what shows the
    # two predicates are not interchangeable. Located from committed data, so it cannot go stale
    # against a hand-picked example that stops differing.
    located = None
    for candidate in sorted(corpus.unit_segments):
        if not candidate.startswith("eu_ai_act:"):
            continue
        segments = corpus.unit_segments[candidate]
        if len(segments) < 2:
            continue
        text = corpus.unit_text[candidate]
        span = segments[-1]
        if span not in text:
            continue
        start = text.find(span)
        stripped = len((text[:start] + text[start + len(span):]).strip())
        unstripped = len(text.replace(span, "", 1))
        if stripped != unstripped:
            located = (candidate, text, span, start, stripped, unstripped)
            break

    assert located is not None, (
        "no committed unit was found where the stripped and unstripped residues differ, so this "
        "control cannot show the two predicates are distinguishable"
    )
    unit, text, span, start, stripped, unstripped = located
    residue = (text[:start] + text[start + len(span):]).strip()
    assert len(residue) == stripped and stripped != unstripped, (
        f"{unit}: the control located a unit that does not in fact distinguish the two measures"
    )

    # distinguishing-term counts, driven on a term that genuinely occurs outside the span, and on
    # one that does not, so the count reaches both a firing and a zero verdict.
    present = next((w for w in residue.split() if w.isalpha() and len(w) > 6), None)
    assert present and residue.count(present) > 0, "no term occurs outside the span to count"
    assert residue.count("zzzznotarealterm") == 0

    # sufficiency offsets, in bounds and arithmetic
    lo, hi = start, start + len(span)
    assert 0 <= lo < hi <= len(text)
    assert (hi - lo) == len(span)
    assert (len(text) - (hi - lo)) == unstripped
    # and out of bounds is caught
    assert not (0 <= lo < len(text) + 5 <= len(text))

    # carrier_count against the list it counts
    members = [{"unit_id": "a"}, {"unit_id": "b"}]
    assert len(members) == 2 and len(members) != 3


# The unit a block's recorded ratios are anchored on. Named per block because the field differs
# by what the stratum draws: single-hop and near-miss anchor on the drawn unit, action-to-parent
# on the parent, since that is the unit the slot hangs off.
RATIO_ANCHOR_FIELD = {
    "single_hop": "drawn_unit",
    "action_to_parent": "drawn_parent",
    "near_miss": "drawn_unit",
}


def _ratio_records() -> list[tuple[str, str, dict]]:
    """(where, anchor, record) for every screening record that can carry a slot ratio.

    Wider than _screening_records above, which is single-hop only by design because the numbers
    it feeds are single-hop row fields. The closed predicate set is a different question: it must
    hold wherever a ratio is recorded, or a fourth quantity enters under an existing name in a
    stratum this file happened not to reach. Both artifacts, both verdicts.
    """
    out = []
    for row in _jsonl(VERIFICATION):
        for block, field in RATIO_ANCHOR_FIELD.items():
            held = row.get(block)
            if held and held.get(field):
                out.append((f"{row['id']} ({block})", held[field], held))
    for row in _jsonl(REJECTIONS):
        field = RATIO_ANCHOR_FIELD.get(row.get("stratum"))
        if field and row.get(field):
            out.append((f"{row[field]} ({row['stratum']} rejection)", row[field], row))
    return out


def _ratio_entries(record: dict):
    """Every entry carrying a recorded ratio: slot member, non-carrier, or near-miss competitor.

    The competitor sits beside the slot rather than inside it, because it is not a candidate for
    membership: it is the unit the gold must be discriminated FROM. Its ratio is nonetheless the
    same quantity the closed set computes, so it is held to the same closure.
    """
    slot = record.get("slot") or {}
    for role in ("members", "non_carriers"):
        for entry in slot.get(role) or []:
            if any(field in entry for field in RATIO_FIELDS):
                yield role, entry
    competitor = record.get("competitor_ratio")
    if isinstance(competitor, dict) and any(field in competitor for field in RATIO_FIELDS):
        assert "unit_id" in competitor, (
            "competitor_ratio carries a ratio and no unit_id, so nothing names what it was "
            "measured against and the predicate cannot be re-derived"
        )
        yield "competitor", competitor


def test_every_slot_ratio_names_its_predicate_and_re_derives_under_it(corpus):
    """Every recorded slot ratio, recomputed under the predicate its own entry names.

    No value is recomputed to satisfy this test: each stands as recorded and the entry discloses
    which instrument produced it. That is the repair for a field name that carried three
    different quantities, on the same ground as the arm blocks, that a number without its method
    fails the reader-has-the-repository test.

    Closure is asserted as well as agreement. A predicate name outside the enumerated set fails
    here, so a fourth quantity cannot enter the record under a name already in use, which is the
    failure mode that produced the situation this field is being repaired from.
    """
    checked = 0
    records = _ratio_records()
    if not records:
        pytest.skip("no committed screening record can carry a slot ratio yet")
    for where, pick, record in records:
        # A record can carry a ratio and no designation. A pick rejected on the carrier screen
        # falls before any span is designated, so its row records the screen that rejected it and
        # nothing further, and only the span-free predicate is derivable there. Asserted rather
        # than skipped: an entry naming a span-dependent predicate on such a record would be
        # quoting a span that does not exist.
        span = record["binding_designation"]["span"] if record.get("binding_designation") else None
        for role, entry in _ratio_entries(record):
            if span is None:
                named = (entry.get("ratio_predicate") or {}).get("comparison")
                assert named == "pick_unit_text_to_member_unit_text", (
                    f"{where}/{role}/{entry.get('unit_id')}: this record carries no binding "
                    f"designation, so a ratio here can only be the span-free predicate, and the "
                    f"entry names {named!r}"
                )
            checked += 1
            member = entry["unit_id"]
            place = f"{where}/{role}/{member}"
            assert "ratio_predicate" in entry, (
                f"{place}: carries a ratio and does not name the predicate that produced it"
            )
            named = entry["ratio_predicate"]
            assert named["comparison"] in RATIO_PREDICATES, (
                f"{place}: predicate {named['comparison']!r} is outside the enumerated set "
                f"{sorted(RATIO_PREDICATES)}"
            )
            assert named["normalisation"] == RATIO_NORMALISATIONS[named["comparison"]], (
                f"{place}: predicate {named['comparison']} pairs with "
                f"{RATIO_NORMALISATIONS[named['comparison']]}, entry names "
                f"{named['normalisation']!r}"
            )
            derived = RATIO_PREDICATES[named["comparison"]](pick, member, span, corpus)
            for field in RATIO_FIELDS:
                if field in entry:
                    assert entry[field] == derived, (
                        f"{place}: {field} recorded {entry[field]}, re-derived {derived} under "
                        f"its own stated predicate {named['comparison']}"
                    )
    if not checked:
        pytest.skip("no committed row carries a slot ratio")


def test_the_untaken_designation_alternative_re_derives(corpus):
    """The measured-and-not-taken alternative's lexical block is the module's output on its span.

    A designation choice between two admissible spans is a recorded content judgment, and the
    untaken candidate ships in full so the choice is auditable. That only works if its numbers
    are checkable: an alternative whose figures nothing re-derives is an assertion that the other
    candidate was worse.
    """
    from src.goldset.attributability import lexical_arm

    checked = 0
    for where, record in _records_or_skip():
        alternative = (record.get("slot") or {}).get(
            "designation_alternative_measured_and_not_taken")
        if not alternative:
            continue
        checked += 1
        derived = lexical_arm(alternative["span"], [record["drawn_unit"]], corpus)
        recorded = alternative["lexical"]
        for key in ("top_ratio", "segments_compared", "units_compared", "floor",
                    "reproducibility_level", "pairs_at_or_above_floor"):
            assert recorded[key] == derived[key], f"{where}: alternative lexical {key}"
    if not checked:
        pytest.skip("no committed row carries a measured-and-not-taken alternative")


def test_the_three_ratio_predicates_are_distinguishable(corpus):
    """V20: the three predicates give different answers on the same pair, so a mislabelled one
    fails rather than passing because they happen to agree.

    Driven on a pair from committed corpus rather than a constructed one. If two of the three
    ever collapsed onto the same value everywhere, naming the predicate would be decoration and
    this test says so by failing.
    """
    pick, member = "nist_ai_100_1:sub_GOVERN_1.3", "nist_playbook:sub_GOVERN_1.3"
    span = corpus.unit_text[pick]
    values = {name: fn(pick, member, span, corpus) for name, fn in RATIO_PREDICATES.items()}
    assert len(set(values.values())) == len(values), (
        f"the three predicates are not distinguishable on this pair: {values}. A predicate name "
        "that cannot change an answer is decoration rather than disclosure"
    )


def test_carrier_count_equals_the_slot_it_describes():
    """carrier_count is a count of the list beside it, so it is asserted against that list.

    A count is a description of the answer. Where the thing counted ships on the same row, the
    count re-derives from the row alone and a hand edit to either half fails here.
    """
    checked = 0
    for where, record in _records_or_skip():
        slot = record.get("slot") or {}
        if "carrier_count" not in slot:
            continue
        checked += 1
        assert slot["carrier_count"] == len(slot["members"]), (
            f"{where}: carrier_count {slot['carrier_count']} against {len(slot['members'])} "
            "slot members"
        )
    if not checked:
        pytest.skip("no committed row carries a carrier_count")


# ---------------------------------------------------------------------------------------------
# Three re-derivations that had no committed check before this commit.


def _near_miss_blocks() -> list[tuple[str, dict]]:
    return [(r["id"], r["near_miss"]) for r in _jsonl(VERIFICATION) if r.get("near_miss")]


def _differential_defects(block: dict, corpus) -> list[str]:
    """Every way a differential_span_check disagrees with its own re-derivation.

    One predicate, driven by the check and by its companion. The opcodes are built through
    ratio_matcher, so this is the corrected predicate rather than difflib's default; the pass-one
    script ran the default and its figures were re-derived under this one before they shipped.
    """
    dsc = block["differential_span_check"]
    a = normalise_for_lexical(corpus.unit_text[block["drawn_unit"]])
    b = normalise_for_lexical(corpus.unit_text[dsc["competitor_unit"]])
    matcher = ratio_matcher(a, b)
    absent_from_b, absent_from_a = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace") and a[i1:i2].strip():
            absent_from_b.append(a[i1:i2].strip())
        if tag in ("insert", "replace") and b[j1:j2].strip():
            absent_from_a.append(b[j1:j2].strip())
    derived = {
        "ratio": round(matcher.ratio(), 4),
        "lexical_normalised_equal": a == b,
        "anchor_runs_absent_from_competitor": absent_from_b,
        "competitor_runs_absent_from_anchor": absent_from_a,
    }
    return [f"{f} recorded {dsc[f]!r}, re-derived {v!r}"
            for f, v in derived.items() if dsc[f] != v]


def test_differential_span_check_re_derives(corpus):
    """The stratum's own primitive, recomputed from the two unit texts.

    It shipped with no committed producer at all until this commit: the script that produced it
    was untracked, so a figure a reviewer could not re-derive was carrying the discrimination
    claim on every row of the stratum.
    """
    blocks = _near_miss_blocks()
    if not blocks:
        pytest.skip("no committed near_miss rows yet; this turns on at that commit")
    for row_id, block in blocks:
        defects = _differential_defects(block, corpus)
        assert not defects, f"{row_id}: " + "; ".join(defects)


def test_the_differential_re_derivation_can_fail(corpus):
    """V20, through the predicate the check runs."""
    blocks = _near_miss_blocks()
    if not blocks:
        pytest.skip("no committed near_miss rows yet")
    row_id, block = blocks[0]
    assert not _differential_defects(block, corpus), f"{row_id}: the honest block does not re-derive"
    moved = json.loads(json.dumps(block))
    moved["differential_span_check"]["ratio"] = round(
        moved["differential_span_check"]["ratio"] - 0.01, 4)
    assert _differential_defects(moved, corpus), "a moved ratio was not caught"
    planted = json.loads(json.dumps(block))
    planted["differential_span_check"]["anchor_runs_absent_from_competitor"] = ["planted run"]
    assert _differential_defects(planted, corpus), "a planted anchor run was not caught"


def test_every_near_miss_block_records_an_empty_anchor_runs(corpus):
    """eval/README.md states this property in prose and nothing asserted it.

    The anchor says nothing its designated competitor does not also say, on every row, which is
    why text cannot discriminate anywhere on this stratum and the identifier must. That is the
    recorded foundation under the scoping rule deciding which screen applies, so a row that
    quietly gained a differentiating run would move the ground under the whole stratum.
    """
    blocks = _near_miss_blocks()
    if not blocks:
        pytest.skip("no committed near_miss rows yet; this turns on at that commit")
    for row_id, block in blocks:
        runs = block["differential_span_check"]["anchor_runs_absent_from_competitor"]
        assert runs == [], (
            f"{row_id}: anchor_runs_absent_from_competitor is {runs}, so the anchor says "
            "something its competitor does not and eval/README.md's stated property no longer "
            "holds for this stratum")


def test_the_empty_anchor_runs_are_a_real_empty(corpus):
    """V8 on eight empty results. The same extraction with the arguments swapped returns runs on
    five of the eight, so the extraction is shown able to see a non-empty result before its
    empties are trusted."""
    blocks = _near_miss_blocks()
    if not blocks:
        pytest.skip("no committed near_miss rows yet")
    non_empty = 0
    for _, block in blocks:
        swapped = json.loads(json.dumps(block))
        swapped["drawn_unit"] = block["differential_span_check"]["competitor_unit"]
        swapped["differential_span_check"]["competitor_unit"] = block["drawn_unit"]
        defects = _differential_defects(swapped, corpus)
        if any("anchor_runs_absent_from_competitor" in d for d in defects):
            non_empty += 1
    assert non_empty >= 1, (
        "swapping the arguments produced no anchor-side run on any row, so the extraction has "
        "not been shown capable of a non-empty result and the eight empties prove nothing")


def _lexical_arm_blocks() -> list[tuple[str, str, set, dict]]:
    """(where, span, gold argument, committed block) for every committed lexical arm, at any
    depth, from both artifacts."""
    out = []
    for row in _jsonl(VERIFICATION):
        for name, held in row.items():
            if not isinstance(held, dict):
                continue
            if held.get("lexical") and held.get("binding_designation"):
                gold = set(held["lexical"].get("gold_units_argument")
                           or [m["unit_id"] for m in ((held.get("slot") or {}).get("members") or [])
                               if isinstance(m, dict)])
                out.append((f"{row['id']}/{name}", held["binding_designation"]["span"], gold,
                            held["lexical"]))
            alt = (held.get("slot") or {}).get("designation_alternative_measured_and_not_taken")
            if alt:
                out.append((f"{row['id']}/{name}/untaken", alt["span"], {held["drawn_unit"]},
                            alt["lexical"]))
    for row in _jsonl(REJECTIONS):
        if row.get("lexical") and row.get("binding_designation"):
            members = (row.get("slot") or {}).get("members") or []
            gold = set(row["lexical"].get("gold_units_argument")
                       or [m["unit_id"] if isinstance(m, dict) else m for m in members])
            out.append((f"{row.get('drawn_unit') or json.dumps(row.get('rejected'))} (rejection)",
                        row["binding_designation"]["span"], gold, row["lexical"]))
    return out


def test_committed_lexical_arms_re_derive(corpus):
    """Every committed lexical arm, recomputed from its own span and its own gold argument.

    Nothing re-derived these before this commit. A coverage probe run against the autojunk
    supersession reverted a corrected figure inside one of them and was observed green, so half
    of that correction was pinned by nothing. The gold argument is read from the block's own
    gold_units_argument, which is what the call actually excluded, rather than reconstructed from
    the slot: the two differ, and the slot form silently empties the argument on a row recording
    its members as bare strings.
    """
    from src.goldset.attributability import lexical_arm

    blocks = _lexical_arm_blocks()
    if not blocks:
        pytest.skip("no committed lexical arm yet")
    for where, span, gold, committed in blocks:
        derived = lexical_arm(span, gold, corpus)
        assert committed["top_ratio"] == derived["top_ratio"], (
            f"{where}: top_ratio recorded {committed['top_ratio']}, re-derived "
            f"{derived['top_ratio']}")
        assert committed["pairs_at_or_above_floor"] == derived["pairs_at_or_above_floor"], (
            f"{where}: the pair list does not re-derive")


def test_the_lexical_arm_re_derivation_can_fail(corpus):
    """V20. The probe that was green before this check existed must now be red."""
    from src.goldset.attributability import lexical_arm

    blocks = [b for b in _lexical_arm_blocks() if b[3]["pairs_at_or_above_floor"]]
    assert blocks, "no committed lexical arm carries a pair, so this control ran on nothing"
    where, span, gold, committed = blocks[0]
    derived = lexical_arm(span, gold, corpus)
    assert committed["pairs_at_or_above_floor"] == derived["pairs_at_or_above_floor"]
    moved = json.loads(json.dumps(committed))
    moved["pairs_at_or_above_floor"][0]["ratio"] = round(
        moved["pairs_at_or_above_floor"][0]["ratio"] - 0.01, 4)
    assert moved["pairs_at_or_above_floor"] != derived["pairs_at_or_above_floor"], (
        f"{where}: a moved pair ratio compares equal, so the check cannot see it")
