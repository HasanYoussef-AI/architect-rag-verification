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
    load_relations,
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
