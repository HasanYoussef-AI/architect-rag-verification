"""The gold model: slots, the two id spaces, and what it takes to satisfy a slot.

PREREGISTRATION.md defines gold as unit-level and slot-based. A gold set is a set of required
slots; each slot is satisfied by any unit in its acceptable-unit set; slots within a query are
disjoint. Retrieval returns a fused top 10 of CHUNKS, so collapsing chunks to units is where the
two levels meet and is the one place a definitional error would silently change every metric.

TWO ID SPACES, TWO PREDICATES, stated as artifact, field and accepted values rather than as a
property, because a filter described in prose becomes a silent misfilter when it becomes code.

  Chunk-id space. A chunk id c belongs to unit u when `c == u or c.startswith(u + "#")`. This is
  the prefix predicate the committed verification records already use. Bare membership is the
  wrong implementation of the same requirement: it reports 97 of 1150 real unit ids as absent,
  because a multi-chunk unit's chunks are `unit#p1`, `unit#p2` and never the bare unit id, so an
  empty result under bare membership is not evidence of anything.

  Unit-id space. Exact set membership. A unit satisfies a slot when it is an element of that
  slot's acceptable-unit list. No prefix rule and no normalisation: the slot names units, and a
  prefix rule here would let `art_1` satisfy a slot naming `art_11`.
"""

from __future__ import annotations

from dataclasses import dataclass


def chunk_belongs_to_unit(chunk_id: str, unit_id: str) -> bool:
    """The chunk-id space predicate. Exact match or the unit id followed by the # separator."""
    return chunk_id == unit_id or chunk_id.startswith(unit_id + "#")


def unit_satisfies_slot(unit_id: str, slot: list[str]) -> bool:
    """The unit-id space predicate. Exact membership, deliberately not a prefix rule."""
    return unit_id in slot


@dataclass(frozen=True)
class SlotHit:
    """Where a slot was first satisfied in a ranking, or that it was not."""

    slot_index: int
    satisfied: bool
    first_satisfying_rank: int | None
    first_satisfying_chunk: str | None
    satisfying_units: tuple[str, ...]


def slot_satisfaction(top_chunks: list[str], gold_slots: list[list[str]]) -> list[SlotHit]:
    """For each slot, the rank of the first chunk whose unit satisfies it.

    Ranks are 1-based, matching the pre-registration's language throughout. A slot contributes
    once however many of its acceptable units, or their chunks, appear; the extra carriers are
    still reported in satisfying_units, because the carrier count is what a precision figure has
    to be read against.
    """
    hits: list[SlotHit] = []
    for index, slot in enumerate(gold_slots):
        first_rank: int | None = None
        first_chunk: str | None = None
        units: list[str] = []
        for rank, chunk in enumerate(top_chunks, 1):
            for unit in slot:
                if not chunk_belongs_to_unit(chunk, unit):
                    continue
                if first_rank is None:
                    first_rank, first_chunk = rank, chunk
                if unit not in units:
                    units.append(unit)
                break
        hits.append(SlotHit(index, first_rank is not None, first_rank, first_chunk, tuple(units)))
    return hits


def assert_slots_are_disjoint(gold_slots: list[list[str]]) -> None:
    """Raise when two slots of one query share an acceptable unit.

    A precondition rather than an assumption. PREREGISTRATION.md requires disjointness so that
    Recall@10 counts distinct answered parts and NDCG@10 stays at or below one; a unit satisfying
    two slots would contribute two gains against an ideal built for one. Raising here is what
    keeps NDCG from quietly returning a number above one on a set that violates it.
    """
    for i in range(len(gold_slots)):
        for j in range(i + 1, len(gold_slots)):
            shared = sorted(set(gold_slots[i]) & set(gold_slots[j]))
            if shared:
                raise ValueError(
                    f"slots {i} and {j} both admit {shared}. PREREGISTRATION.md requires a "
                    "query's slots to be disjoint; scoring a set that violates it would return a "
                    "recall that double-counts and an NDCG above one"
                )
