"""Slot ordering, the closure route, the recorded arm 1 gap, and the distinguishing-term test.

WHAT THE CLOSURE CONTROL DOES AND DOES NOT SHOW. slot_from below is defined in this file. It is
a re-implementation of a rule that is applied by hand during screening, not a call into any code
path under src/. So this control shows that the rule, as written here, bars a closure member and
does not bar a non-member. It does NOT show that the screening path fires the code, because there
is no committed slot-derivation function for it to exercise. Stated plainly rather than left to
be inferred from a passing test. Making the control real requires a slot-derivation module that
the screening harness calls.

The arm 1 gap is pinned because it must stay visible without being fixed. Extending the
external-instrument pattern after seeing which unit it missed would fit the detector to that
observation, the same shape as the Article 6 classification gap already parked in
tests/test_self_containedness.py.

No control is constructed for needs_two_slots. That is verdict vocabulary with no instrument
behind it, and manufacturing a rejection to demonstrate a code is worse than a funnel that
honestly reports the code did not fire.
"""

from __future__ import annotations

import json

import pytest

from src.goldset.self_containedness import (
    CLASS_EXTERNAL_INSTRUMENT,
    ChunkCorpus,
    named_references,
)
from src.ingest.corpus_integrity import REPO_ROOT

FRAME = json.loads((REPO_ROOT / "eval" / "test_frame.json").read_text(encoding="utf-8"))
CLOSURE = {u["unit_id"] for u in FRAME["closure"]["units"]}
VERIFICATION = REPO_ROOT / "eval" / "test_query_verification.jsonl"
QUERIES = REPO_ROOT / "eval" / "test_queries.jsonl"


def slot_from(carriers: set[str], closure: set[str]) -> tuple[set[str], set[str]]:
    """Re-implementation of the hand-applied rule. See the module docstring on what this shows.

    Returns (slot_members, barred). A non-empty barred set is the condition under which
    answer_attributable_outside_slot fires by the closure route.
    """
    barred = {c for c in carriers if c in closure}
    return carriers - barred, barred


def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _single_hop_gold(verification_rows, query_rows) -> list[tuple[str, list[list[str]]]]:
    """(row id, gold_slots) for every single_hop row in the pair of files handed in.

    THE DETECTOR IS THE BLOCK, NOT A TYPE FIELD. An earlier form of this filtered the
    verification file on `row.get("type") == "single_hop"`. Verification rows carry no `type`
    key at all, only `subtype`, so that filter matched nothing on every row and the checks below
    would have skipped permanently, including after the rows landed. It also read `gold_slots`
    from the verification file, where that key does not live. Both are the V20 blindness form: a
    detector matching on a field path while the claim lives somewhere else, which returns a pass
    on the one case it exists to check.

    Gold is read from eval/test_queries.jsonl, which is where gold_slots lives, joined by id to
    the verification row that carries the single_hop block. Takes its rows as arguments so the
    control below can drive this function rather than a copy of it.
    """
    single_hop_ids = {r["id"] for r in verification_rows if r.get("single_hop")}
    return [(r["id"], r["gold_slots"]) for r in query_rows if r["id"] in single_hop_ids]


def _committed_single_hop_gold() -> list[tuple[str, list[list[str]]]]:
    """The committed rows, empty before the stratum lands."""
    return _single_hop_gold(_jsonl(VERIFICATION), _jsonl(QUERIES))


def test_the_single_hop_detector_is_shown_capable_of_finding_rows():
    """V20: the detector these checks depend on, driven against a row shaped like the ones that
    are coming, alongside the superseded predicate asserted to miss it.

    Without this, every check below skips at this commit and the first evidence that the
    detector works at all would arrive with the data it is supposed to judge. A detector whose
    only exercise is the commit it was written for is trusted on a pass it has never been able
    to withhold. The rows here are shaped from the committed schema: the verification row
    carries `subtype` and no `type`, which is the exact property the superseded filter missed.
    """
    verification = [
        {"id": "test_21", "subtype": "eu_ai_act", "query": "q", "multi_hop": None,
         "single_hop": {"drawn_unit": "eu_ai_act:art_113"}},
        {"id": "test_09", "subtype": "eu_internal_xref", "query": "q",
         "multi_hop": {"source_unit": "eu_ai_act:art_43"}, "single_hop": None},
    ]
    queries = [
        {"id": "test_21", "type": "single_hop", "subtype": "eu_ai_act",
         "gold_slots": [["eu_ai_act:art_113", "eu_ai_act:rct_179"]]},
        {"id": "test_09", "type": "multi_hop", "subtype": "eu_internal_xref",
         "gold_slots": [["eu_ai_act:art_43"], ["eu_ai_act:art_97"]]},
    ]

    found = _single_hop_gold(verification, queries)
    assert [row_id for row_id, _ in found] == ["test_21"], (
        f"the detector found {found}, expected exactly the single_hop row"
    )
    assert found[0][1] == [["eu_ai_act:art_113", "eu_ai_act:rct_179"]], (
        "the detector found the row but did not carry its gold across from the query file"
    )

    # The superseded predicate, reproduced so what is shown to fail is the thing that failed.
    superseded = {r["id"] for r in verification if r.get("type") == "single_hop"}
    assert superseded == set(), (
        "the superseded filter matched something, so this control no longer reproduces the "
        "defect it exists to pin"
    )
    assert {row_id for row_id, _ in found} != superseded, (
        "the current and superseded predicates agree, so the fix changed nothing"
    )


def test_the_closure_is_fifty_units_and_is_the_bar():
    assert len(CLOSURE) == 50


def test_closure_route_bars_a_carrier_that_sits_in_the_closure():
    pick = "eu_ai_act:art_113"
    carrier_in_closure = sorted(CLOSURE)[0]
    assert pick not in CLOSURE and carrier_in_closure in CLOSURE
    slot, barred = slot_from({pick, carrier_in_closure}, CLOSURE)
    assert barred == {carrier_in_closure}
    assert slot == {pick}


def test_closure_route_does_not_bar_when_no_carrier_is_in_the_closure():
    """The negative half. A rule that always bars would prove nothing."""
    pick, carrier = "eu_ai_act:art_113", "eu_ai_act:rct_179"
    assert pick not in CLOSURE and carrier not in CLOSURE
    slot, barred = slot_from({pick, carrier}, CLOSURE)
    assert barred == set()
    assert slot == {pick, carrier}


def test_no_committed_single_hop_slot_member_sits_in_the_closure():
    """Derived from the committed rows, not from a hand-maintained snapshot.

    Skips until the stratum lands, so it cannot rot into a stale literal the way an inline list
    of unit ids would when a later batch is screened.
    """
    rows = _committed_single_hop_gold()
    if not rows:
        pytest.skip("no committed single_hop rows yet; the check turns on at that commit")
    members = {u for _, slots in rows for slot in slots for u in slot}
    assert members, "single_hop rows are committed and name no gold unit at all"
    offending = sorted(members & CLOSURE)
    assert not offending, f"single_hop gold touches the closure: {offending}"


def test_single_hop_slots_are_lexicographic_within_a_slot():
    """Within-slot order is lexicographic ascending, and between-slot order is not touched.

    The convention is load-bearing rather than cosmetic. The sealed gold rule makes any carrying
    unit sufficient, so naming the drawn unit first would privilege it in exactly the way that
    rule forbids, the first thing a consumer does with a list being to take element zero. Sorting
    within the slot removes the drawn unit's positional privilege, and the verification block's
    drawn_unit is what names it instead.

    Single-hop carries one slot per row by the single-slot determinacy rule, so between-slot
    order does not arise here and is deliberately not asserted; on multi-hop rows that order is
    semantic and sorting it would be wrong.
    """
    rows = _committed_single_hop_gold()
    if not rows:
        pytest.skip("no committed single_hop rows yet; the check turns on at that commit")
    for row_id, slots in rows:
        assert len(slots) == 1, (
            f"{row_id}: {len(slots)} gold slots on a single_hop row. Single-slot determinacy "
            "makes a pick needing two slots a multi-hop, rejected from this stratum"
        )
        for slot in slots:
            assert slot == sorted(slot), (
                f"{row_id}: slot members are not lexicographic ascending; {slot} against "
                f"{sorted(slot)}"
            )


def test_arm1_does_not_reach_a_described_body_of_law_and_the_gap_is_recorded():
    """A recorded gap, deliberately not fixed.

    eu_ai_act:rct_87 was rejected unit_defers_for_substance because the party bound by its
    obligation is "the product manufacturer defined in that legislation", where that legislation
    is Union harmonisation legislation based on the New Legislative Framework, which the corpus
    does not contain. Arm 1's external_instrument class matches numbered citations, acronyms and
    capitalised instrument nouns, so it does not reach a body of law named by description. The
    rejection was carried by arm 3, the part with no committed method.
    """
    corpus = ChunkCorpus.load()
    unit = "eu_ai_act:rct_87"
    text = "".join(r["text"] for r in corpus.chunks_for(unit))
    assert "Union harmonisation legislation based on the New Legislative Framework" in text
    assert "the product manufacturer defined in that legislation" in text

    block = named_references(unit, corpus)
    assert {c["surface"] for c in block["candidates"]
            if c["class"] == CLASS_EXTERNAL_INSTRUMENT} == set()
    assert block["funnel"]["candidates"] == 1

    covering = named_references("eu_ai_act:art_87", corpus)
    assert "Directive (EU) 2019/1937" in {
        c["surface"] for c in covering["candidates"] if c["class"] == CLASS_EXTERNAL_INSTRUMENT
    }


def _outside_span(corpus: ChunkCorpus, unit: str, span: str) -> str:
    text = "\n".join(r["text"] for r in corpus.chunks_for(unit))
    i = text.index(span)
    return text[:i] + text[i + len(span):]


def test_distinguishing_term_test_discriminates():
    """The pass-two rule, shown accepting and rejecting rather than only accepting.

    The term distinguishing the span from a verdicted non-carrier must occur in the unit's own
    text OUTSIDE the designated span. rct_74 is the rejecting case and is the reason the rule
    exists: its only distinguishing term occurs once, inside the span.
    """
    corpus = ChunkCorpus.load()

    passing_span = ("Non-compliance with the prohibition of the AI practices referred to in "
                    "Article 5 shall be subject to administrative fines of up to EUR 1 500 000.")
    outside = _outside_span(corpus, "eu_ai_act:art_100", passing_span)
    assert outside.count("Union institution") >= 1
    assert outside.count("administrative fine") >= 1

    failing_span = ("The expected level of performance metrics should be declared in the "
                    "accompanying instructions of use.")
    outside74 = _outside_span(corpus, "eu_ai_act:rct_74", failing_span)
    assert failing_span.count("performance metrics") == 1
    assert outside74.count("performance metrics") == 0
