"""Where each committed carrier relation stands on a slot member, for a given pick.

A gold slot for a duplicated statement is the union of two committed relations, the AI 100-1
duplication map's `duplicated_in` list and `verbatim_groups.json`'s normalised-identity group
members, plus any carrier added by individual verification. Deciding whether a candidate member
belongs needs to know what each relation SAYS about it, and there are three answers, not two: a
relation can hold a record covering the pick and list the member, hold a record covering the pick
and leave the member out, or hold nothing about the pick at all.

Measured exclusion and silence are different facts and only this form separates them. A relation
that compared a unit and left it out is evidence about the unit; a relation that never compared
it is evidence about nothing. A membership test over the member alone collapses the two, because
a unit excluded from a group it was compared against and a unit no group ever compared both fail
`member in group`. That collapse is pinned by tests/test_relation_positions.py, which reproduces
the superseded implementation and asserts it returns the wrong answer where this one returns the
right one.

Relation membership is read from the relation's own structure, the group's member list or the
map's `duplicated_in` list, never by whole-file containment. Three containment-shaped false
results occurred before the class was pinned.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.ingest.corpus_integrity import REPO_ROOT

GROUPS_PATH = Path("data/retrieval/verbatim_groups.json")
DUPLICATION_MAP_PATH = Path("data/chunks/nist_ai_100_1.duplication_map.json")

SILENT = "SILENT"
INCLUDES = "MEASURED AND INCLUDES"
EXCLUDES = "MEASURED AND EXCLUDES"


def load_relations(repo_root: Path | None = None) -> tuple[list, list]:
    """The two committed carrier relations, in the form this module reads them."""
    root = repo_root or REPO_ROOT
    groups = json.loads((root / GROUPS_PATH).read_text(encoding="utf-8"))
    return (
        groups["bases"]["normalised_identity"]["groups"],
        json.loads((root / DUPLICATION_MAP_PATH).read_text(encoding="utf-8")),
    )


def relation_positions(pick: str, member: str, groups: list, duplication_map: list) -> dict:
    """Each relation's position on this member, for this pick, as a sentence naming its basis.

    The sentence carries the covered set rather than only the verdict, so a reader can check the
    verdict against the relation's own contents without opening the relation.
    """
    held = next((g["members"] for g in groups if pick in g["members"]), None)
    if held is None:
        verbatim = "%s: no normalised_identity group holds this pick" % SILENT
    elif member in held:
        verbatim = "%s: the normalised_identity group members are %s" % (
            INCLUDES, json.dumps(held))
    else:
        verbatim = ("%s: the normalised_identity group holds exactly %s and this unit is not "
                    "one of them") % (EXCLUDES, json.dumps(held))

    row = next((r for r in duplication_map
                if r["source_unit_id"] == pick
                or any(d["unit_id"] == pick for d in r["duplicated_in"])), None)
    if row is None:
        duplication = "%s: carries no row for this pick" % SILENT
    else:
        covered = sorted({row["source_unit_id"]} | {d["unit_id"] for d in row["duplicated_in"]})
        if member in covered:
            duplication = "%s: the row for this pick covers %s" % (INCLUDES, json.dumps(covered))
        else:
            duplication = ("%s: the row for this pick covers %s and this unit is not among "
                           "them") % (EXCLUDES, json.dumps(covered))
    return {"duplication_map": duplication, "verbatim_groups": verbatim}


def verdicts(positions: dict) -> dict:
    """The bare verdict per relation, for asserting on without matching prose."""
    return {k: v.split(":", 1)[0] for k, v in positions.items()}


def document_of(unit_id: str) -> str:
    """The document a unit id belongs to. Every unit id in this corpus is `<doc_id>:<local>`."""
    return unit_id.split(":", 1)[0]


def nominated_for_testing(pick: str, groups: list, duplication_map: list) -> dict[str, list[str]]:
    """Every unit either committed relation records alongside `pick`, mapped to the relations
    naming it. Document-blind, deliberately.

    Nomination is not admission. The locked rule is that the union decides which units get TESTED
    and never which units skip the test, so a same-document identity twin is nominated here, put
    to the carrier standard, and recorded on the row with its verdict and its ground. Narrowing
    this set would remove evidence rather than add rigour: a twin that never appears on the row is
    a twin nobody can see was considered.

    Membership is read from each relation's own structure, the group's member list and the map
    row's source_unit_id plus duplicated_in, never by whole-file containment. Matching is exact
    string equality against the member list, the same rule relation_positions uses, so the two
    cannot disagree about what a relation says.
    """
    found: dict[str, list[str]] = {}
    held = next((g["members"] for g in groups if pick in g["members"]), None)
    if held is not None:
        for unit in held:
            if unit != pick:
                found.setdefault(unit, []).append("verbatim_groups")
    row = next((r for r in duplication_map
                if r["source_unit_id"] == pick
                or any(d["unit_id"] == pick for d in r["duplicated_in"])), None)
    if row is not None:
        covered = {row["source_unit_id"]} | {d["unit_id"] for d in row["duplicated_in"]}
        for unit in covered:
            if unit != pick:
                found.setdefault(unit, []).append("duplication_map")
    return {unit: sorted(rels) for unit, rels in sorted(found.items())}


def relation_derived_carriers(pick: str, groups: list,
                              duplication_map: list) -> dict[str, list[str]]:
    """The nominated units a committed relation may ADMIT to `pick`'s gold slot.

    Cross-document only. PREREGISTRATION.md scopes the any-carrier clause in its own words to a
    statement "duplicated verbatim across documents", so a relation cannot admit a unit sharing
    `pick`'s document. Measured over this corpus the restriction narrows 49 units, every one of
    them nist_playbook, which is the same-document block duplication the near-miss stratum draws
    its distractors from: those twins are the legitimate competitors and admitting them would put
    the competitor inside the slot it is supposed to be discriminated from.

    Individual verification is the other route into a slot and is unrestricted by document. It is
    a recorded human verdict under the carrier standard, not a derivation, so it is deliberately
    outside this function: this is the mechanical arm alone.
    """
    return {unit: rels
            for unit, rels in nominated_for_testing(pick, groups, duplication_map).items()
            if document_of(unit) != document_of(pick)}
