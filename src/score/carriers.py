"""Gold-carrier equivalence classes, as one definition the tests and the scorer share.

PREREGISTRATION.md scores Precision@10 over chunks, so a retrieval returning several verbatim
carriers of one statement raises it, and the sealed file requires each query's carrier count to be
reported alongside the figure. That count is a property of the gold rather than of the run: it is
how many units carry the slot's statement, computable before retrieval.

WHY THIS MOVED OUT OF A TEST MODULE. tests/test_gold_carrier_counts.py defined this union-find and
was the only thing that could use it. The scorer needs the same composition, and two
implementations of gold-carrier identity in one repository is the defect V4's cross-check exists
to catch, stated the other way round. It moves here, the test imports it, and a regression there
asserts the moved function still reproduces the manifest's committed duplicated_gold_carrier_counts
figures. Those numbers were derived before the move, so they are an oracle rather than a
restatement.

BOTH RELATIONS, COMPOSED. The AI 100-1 duplication map carries semantic restatement structure and
is exact-substring and NIST-only; verbatim_groups.json's normalised-identity groups carry
byte-level identity after comparison normalisation. Neither contains the other. The single-hop slot
ruling composes them for a measured reason: two of the closure's ten expansion units are reachable
only through verbatim_groups.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.ingest.corpus_integrity import REPO_ROOT

DUPLICATION_MAP = REPO_ROOT / "data" / "chunks" / "nist_ai_100_1.duplication_map.json"
VERBATIM_GROUPS = REPO_ROOT / "data" / "retrieval" / "verbatim_groups.json"


def unit_of(chunk_id: str) -> str:
    """The unit a chunk id belongs to. Chunk ids are `unit#suffix` or the bare unit id."""
    return chunk_id.split("#", 1)[0]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def carrier_classes() -> dict[str, str]:
    """Union-find over both duplication relations. Returns unit id -> class representative.

    A unit named by neither relation has no entry here at all, which is the common case: both
    relations are NIST-side, so every EU unit is absent. Callers treat absence as a class of one,
    and must do so explicitly rather than by reading membership off this dict, since a unit with
    no entry reports a class of zero if counted that way.
    """
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

    for row in _load(DUPLICATION_MAP):
        members = [row["source_unit_id"], *[d["unit_id"] for d in row["duplicated_in"]]]
        for member in members[1:]:
            union(members[0], member)
    for group in _load(VERBATIM_GROUPS)["bases"]["normalised_identity"]["groups"]:
        members = [unit_of(m) for m in group["members"]]
        for member in members[1:]:
            union(members[0], member)
    return {unit: find(unit) for unit in parent}


def class_of(unit: str, classes: dict[str, str]) -> str:
    """This unit's class representative, itself when no relation names it."""
    return classes.get(unit, unit)


def carrier_count(gold_slots: list[list[str]], classes: dict[str, str] | None = None) -> int:
    """How many units carry the statements this query's gold names.

    The count reported beside every Precision@10 figure. It is the size of the union of the slots,
    which is the number of distinct units any of which satisfies some slot; a duplicated statement
    contributes one per carrier, which is exactly the property that raises precision.
    """
    if classes is None:
        classes = carrier_classes()
    return len({unit for slot in gold_slots for unit in slot})


def carriers_in(chunks: list[str], gold_slots: list[list[str]]) -> list[str]:
    """The gold units present among these chunks, in first-appearance order.

    Reported beside the count so a precision figure can be read against the units that produced
    it rather than against a bare number.
    """
    gold = {unit for slot in gold_slots for unit in slot}
    seen: list[str] = []
    for chunk in chunks:
        unit = unit_of(chunk)
        if unit in gold and unit not in seen:
            seen.append(unit)
    return seen
