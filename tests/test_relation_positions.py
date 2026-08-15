"""Regression test for the containment-shaped false result, with its negative control.

Three containment-shaped false results occurred while the single-hop slots were being measured.
The first two were a shell-globbed include pattern and a whole-file substring test over
verbatim_groups.json. The third was a relation-position function that asked whether either
relation named a member anywhere, which returns the same answer for a unit a relation compared
and excluded and for a unit no relation ever compared.

The position that must not be recoverable by a weaker test is nist_playbook:sub_GOVERN_1.3
against the pick nist_ai_100_1:sub_GOVERN_1.3. Both relations hold a record for that pick and
both leave that unit out, and that measured exclusion is the whole footing for calling the
Playbook unit a non-carrier. A function reporting silence there would dissolve the non-carrier
verdict without failing anything.

The pick itself was rejected at authoring under answer_attributable_outside_slot, so it carries
no query and ships no gold slot. That does not weaken this file. What is pinned here is a
property of the two committed relations, not of the selected set: the relations still hold those
records, the union rule that reads them still governs every slot in the stratum, and the two
relations still disagree on the Playbook member of MANAGE 3.1 and MEASURE 1.1, which are
accepted picks with three-member slots. The rejected pick is the sharpest case the relations
offer, which is why it is the one the control drives.
"""

from __future__ import annotations

import pytest

from src.goldset.relation_positions import (
    EXCLUDES,
    INCLUDES,
    SILENT,
    document_of,
    load_relations,
    nominated_for_testing,
    relation_derived_carriers,
    relation_positions,
    verdicts,
)

GOVERN_PICK = "nist_ai_100_1:sub_GOVERN_1.3"
PLAYBOOK_NON_CARRIER = "nist_playbook:sub_GOVERN_1.3"
AI_600_1_CARRIER = "nist_ai_600_1:sub_GOVERN_1.3"
UNRELATED_PICK = "eu_ai_act:rct_111"
UNRELATED_MEMBER = "eu_ai_act:art_3"


@pytest.fixture(scope="module")
def relations():
    return load_relations()


def test_the_playbook_unit_is_measured_and_excluded_on_govern_1_3(relations):
    """Both relations compared this unit against the pick and left it out. That is evidence."""
    groups, duplication_map = relations
    got = verdicts(relation_positions(GOVERN_PICK, PLAYBOOK_NON_CARRIER, groups, duplication_map))
    assert got == {"verbatim_groups": EXCLUDES, "duplication_map": EXCLUDES}


def test_a_unit_no_relation_compared_is_silent(relations):
    """No eu_ai_act unit is in any normalised_identity group and the duplication map is
    nist_ai_100_1 sourced, so both relations hold nothing for this pick. Silence, not
    exclusion."""
    groups, duplication_map = relations
    got = verdicts(relation_positions(UNRELATED_PICK, UNRELATED_MEMBER, groups, duplication_map))
    assert got == {"verbatim_groups": SILENT, "duplication_map": SILENT}


def test_exclusion_and_silence_are_not_the_same_answer(relations):
    """The property the defect violated, asserted directly rather than left to the two cases."""
    groups, duplication_map = relations
    excluded = relation_positions(GOVERN_PICK, PLAYBOOK_NON_CARRIER, groups, duplication_map)
    silent = relation_positions(UNRELATED_PICK, UNRELATED_MEMBER, groups, duplication_map)
    assert excluded["verbatim_groups"] != silent["verbatim_groups"]
    assert excluded["duplication_map"] != silent["duplication_map"]


def test_the_carrier_on_govern_1_3_is_measured_and_included(relations):
    """The third value has to be reachable too, or the two-way distinction is untested."""
    groups, duplication_map = relations
    got = verdicts(relation_positions(GOVERN_PICK, AI_600_1_CARRIER, groups, duplication_map))
    assert got == {"verbatim_groups": INCLUDES, "duplication_map": INCLUDES}


@pytest.mark.parametrize("pick,member", [
    ("nist_ai_100_1:sub_MANAGE_3.1", "nist_playbook:sub_MANAGE_3.1"),
    ("nist_ai_100_1:sub_MEASURE_1.1", "nist_playbook:sub_MEASURE_1.1"),
])
def test_the_two_relations_disagree_on_the_playbook_member(pick, member, relations):
    """The union rule's live case: the duplication map includes these units and verbatim_groups
    excludes them, which is why the slot is the union and not either relation alone. A function
    collapsing exclusion into silence would hide that the two relations disagree at all."""
    groups, duplication_map = relations
    got = verdicts(relation_positions(pick, member, groups, duplication_map))
    assert got == {"verbatim_groups": EXCLUDES, "duplication_map": INCLUDES}


def _containment_positions(pick: str, member: str, groups: list, duplication_map: list) -> dict:
    """The superseded implementation, reproduced so the test can be shown capable of failing.

    It asks whether either relation names the MEMBER anywhere and never looks at the pick.
    """
    in_group = any(member in g["members"] for g in groups)
    named = any(r["source_unit_id"] == member
                or any(d["unit_id"] == member for d in r["duplicated_in"])
                for r in duplication_map)
    return {"verbatim_groups": INCLUDES if in_group else SILENT,
            "duplication_map": INCLUDES if named else SILENT}


def test_the_superseded_implementation_fails_the_case_this_file_exists_to_pin(relations):
    """V20. The check is trusted only once it has been shown to fail on the known defect."""
    groups, duplication_map = relations
    wrong = _containment_positions(GOVERN_PICK, PLAYBOOK_NON_CARRIER, groups, duplication_map)
    right = verdicts(relation_positions(GOVERN_PICK, PLAYBOOK_NON_CARRIER, groups,
                                        duplication_map))
    assert wrong["verbatim_groups"] == SILENT, (
        "the superseded function reported silence where the group measured and excluded")
    assert right["verbatim_groups"] == EXCLUDES
    assert wrong["verbatim_groups"] != right["verbatim_groups"]


# ---------------------------------------------------------------------------------------------
# Nomination against admission. PREREGISTRATION.md scopes the any-carrier clause in its own words
# to a statement duplicated verbatim ACROSS DOCUMENTS, so a relation may admit only across
# documents, while nomination for testing stays the unscoped union on the locked rule that the
# union decides which units get tested and never which units skip the test.

SAME_DOCUMENT_TWIN_PICK = "nist_playbook:sub_MANAGE_3.1.ai_transparency_resources"
SAME_DOCUMENT_TWIN = "nist_playbook:sub_MANAGE_3.2.ai_transparency_resources"


def _every_unit_either_relation_mentions(groups, duplication_map) -> set[str]:
    units = {m.split("#", 1)[0] for g in groups for m in g["members"]}
    for row in duplication_map:
        units.add(row["source_unit_id"])
        units.update(d["unit_id"] for d in row["duplicated_in"])
    return units


def test_nomination_reaches_a_same_document_twin(relations):
    """The unscoped half. A same-document identity twin is nominated, so it is tested and lands on
    the row as a verdicted non-carrier rather than never appearing at all."""
    groups, duplication_map = relations
    nominated = nominated_for_testing(SAME_DOCUMENT_TWIN_PICK, groups, duplication_map)
    assert SAME_DOCUMENT_TWIN in nominated, (
        "the twin is not nominated, so nothing would put it to the carrier standard and the row "
        "would not record that it was considered")
    assert nominated[SAME_DOCUMENT_TWIN] == ["verbatim_groups"]


def test_admission_does_not_reach_that_same_document_twin(relations):
    """The scoped half, on the same pair, so nomination and admission are shown to differ on a
    real corpus case rather than in principle."""
    groups, duplication_map = relations
    admitted = relation_derived_carriers(SAME_DOCUMENT_TWIN_PICK, groups, duplication_map)
    assert SAME_DOCUMENT_TWIN not in admitted, (
        "a same-document twin was admitted to the slot by a relation. Admitting it would put the "
        "near-miss competitor inside the slot it exists to be discriminated from")
    assert admitted == {}


def test_admission_still_reaches_a_cross_document_carrier(relations):
    """The scoping must not be a blanket refusal. GOVERN 1.3's AI 600-1 carrier is cross-document
    and both relations include it, so it is admitted."""
    groups, duplication_map = relations
    admitted = relation_derived_carriers(GOVERN_PICK, groups, duplication_map)
    assert AI_600_1_CARRIER in admitted
    assert admitted[AI_600_1_CARRIER] == ["duplication_map", "verbatim_groups"]
    assert PLAYBOOK_NON_CARRIER not in admitted, (
        "the Playbook unit is measured and excluded by both relations, so nomination reaches it "
        "and admission does not")


# The three units the exact-match rule does not reach. Each is a two-chunk Playbook references
# unit whose chunks sit in two DIFFERENT normalised_identity groups, so no group's member list
# contains the bare unit id and exact string equality finds nothing. eval/test_frame.json names
# this case by name in the block_clusters basis: the population admits a unit through chunk-level
# membership normalised to its unit id, while the key requires the member string to equal the
# candidate string, and nist_playbook:sub_MEASURE_4.1.references is admitted by the one and
# carries no key under the other.
#
# The exact-match rule is the one that ships, because relation_positions uses it and the thirty
# nine committed slot entries carry its output. Recorded as a boundary rather than repaired: a
# unit-normalised rule here would disagree with what those rows already say.
EXACT_MATCH_DOES_NOT_REACH = (
    "nist_playbook:sub_MEASURE_4.1.references",
    "nist_playbook:sub_MEASURE_4.2.references",
    "nist_playbook:sub_MEASURE_4.3.references",
)


def test_the_two_functions_differ_by_exactly_the_same_document_set(relations):
    """The corpus-wide funnel, and the positive control that the scoping does something.

    A restriction that removed nothing would pass every assertion above while being decorative.
    Measured: the difference is 49 units, every one of them nist_playbook, which is the
    same-document block duplication the near-miss stratum draws its distractors from.
    """
    groups, duplication_map = relations
    units = _every_unit_either_relation_mentions(groups, duplication_map)
    narrowed = {
        u for u in units
        if nominated_for_testing(u, groups, duplication_map)
        != relation_derived_carriers(u, groups, duplication_map)
    }
    assert narrowed, (
        "the cross-document restriction removes nothing anywhere in the corpus, so it is "
        "decorative and no test below it means anything")
    assert len(narrowed) == 49, f"expected 49 narrowed units, measured {len(narrowed)}"
    assert {u.split(':', 1)[0] for u in narrowed} == {"nist_playbook"}, (
        "the narrowing reached a document other than nist_playbook, which would mean the "
        "same-document duplication is not confined to the Playbook blocks")

    for unit in units:
        admitted = relation_derived_carriers(unit, groups, duplication_map)
        assert all(document_of(u) != document_of(unit) for u in admitted), (
            f"{unit}: relation_derived_carriers returned a same-document unit")


def test_the_exact_match_boundary_is_pinned_rather_than_absorbed(relations):
    """The three units the shipped rule does not reach, asserted by name.

    Found by two implementations disagreeing, 49 against 52, while this file was being written.
    The looser unit-normalised rule reaches them and the shipped exact-match rule does not. Pinned
    here so the boundary is a recorded property with its three instances rather than a silent
    three-unit gap, and so a later change to either matching rule fails rather than passing.
    """
    groups, duplication_map = relations
    for unit in EXACT_MATCH_DOES_NOT_REACH:
        assert not [g for g in groups if unit in g["members"]], (
            f"{unit} is now an exact member of a group, so this boundary has moved")
        assert [g for g in groups if any(m.split("#", 1)[0] == unit for m in g["members"])], (
            f"{unit} is no longer reachable by the unit-normalised rule either, so the two rules "
            "no longer disagree here and this pin describes nothing")
        assert nominated_for_testing(unit, groups, duplication_map) == {}, (
            f"{unit}: the shipped rule now nominates something for it")


def test_the_cross_document_scoping_can_fail(relations):
    """V20. The scoping is trusted only once the unscoped form has been shown to admit the unit it
    is there to keep out, on the same pair, in the same run."""
    groups, duplication_map = relations
    unscoped = nominated_for_testing(SAME_DOCUMENT_TWIN_PICK, groups, duplication_map)
    scoped = relation_derived_carriers(SAME_DOCUMENT_TWIN_PICK, groups, duplication_map)
    assert SAME_DOCUMENT_TWIN in unscoped and SAME_DOCUMENT_TWIN not in scoped, (
        "the two functions agree on the pair the scoping exists for, so nothing here is pinned")
    assert document_of(SAME_DOCUMENT_TWIN) == document_of(SAME_DOCUMENT_TWIN_PICK)
