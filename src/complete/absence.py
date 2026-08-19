"""The completeness predicate, component C2 of the verification layer.

Given the query text, the fused top 10 and C1's grammar, this module reports what the
first pass referred to and did not return. It emits the two signals the layer acts on
and it emits them nowhere else:

  CONTEXT ABSENCE. A reference that resolves to a real unit which no retrieved chunk
  belongs to. The completeness surface: the first pass named a passage and did not
  return it.

  NON RESOLUTION. A well-formed reference naming no unit in the corpus at all. The
  fabricated-provision signal, reached from the query text and the committed unit index
  with no annotation of any kind.

THE FIREWALL IS HELD BY TYPE, NOT BY DISCIPLINE. This module opens nothing. It never
receives a chunk record, so `structural_path` and `parent_id` are not fields it declines
to read, they are fields it cannot reach: a retrieved chunk enters as RetrievedChunk,
which carries the three values CLAUDE.md admits as retrieved context and has no other
attribute. Likewise the query enters as a string, so `type`, `subtype`, `note`,
`gold_slots`, `expected_units`, `id` and `split` never exist in this module's world.
tests/test_context_absence.py asserts both properties rather than trusting this
paragraph.

MEMBERSHIP IS LEXICAL ON THE CHUNK ID. Deciding whether a resolved unit is in the
context set needs a chunk-to-unit map, and the obvious one, the chunk record's own
parent_id, is outside retrieved context. The chunk id carries the same information
already: a chunk belongs to a unit when its id is that unit id or that unit id followed
by the '#' separator. Measured against parent_id, the two agree on all 1294 committed
chunks and produce identical absent sets on all fifty committed rows. The predicate is
re-implemented here rather than imported from src/score/slots.py, because the grader
must stay a separate invocation with no shared state, and a test cross-checks the two
implementations over the whole corpus.

The '#' separator matters. Bare containment would let the Playbook's sibling blocks
collapse into their subcategory statement, and a prefix rule without the separator would
let art_11 swallow art_113.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.complete.references import DroppedReference, Reference, extract, resolve


@dataclass(frozen=True)
class RetrievedChunk:
    """One chunk of the fused top 10, carrying retrieved context and nothing else.

    The three fields are exactly what the layer-gold firewall admits per retrieved
    chunk. Constructing one is where a caller chooses those three out of the chunk
    record, so the choice is visible at every call site rather than buried here.
    """

    chunk_id: str
    text: str
    unit_label: str


@dataclass(frozen=True)
class CompletenessReport:
    """What the first pass referred to, and what it did not return.

    TWO ABSENCE SETS, NOT ONE, because they are different signals and conflating them
    reads a strong result off a weak one. `absent_units` is every resolved unit no
    retrieved chunk belongs to, most of which are incidental citations inside retrieved
    text. `query_absent_units` is the subset composed from a reference the QUERY itself
    made, which is the query naming a passage the first pass did not return.

    Measured over the sealed fifty, the broad set is non-empty on 48 rows and the query
    set on 11. Neither separates the near-miss stratum: both are non-empty on all eight of
    its rows, including test_45, whose anchor block was retrieved at rank 7 while three
    other units its query names were not. What does separate them is not a flag at all but
    which unit is absent, which is what corrective re-retrieval acts on.
    """

    references: tuple[Reference, ...]
    resolved_units: tuple[str, ...]
    absent_units: tuple[str, ...]
    query_absent_units: tuple[str, ...]
    unresolved_references: tuple[Reference, ...]
    dropped_references: tuple[DroppedReference, ...]


def chunk_belongs_to_unit(chunk_id: str, unit_id: str) -> bool:
    """Exact match, or the unit id followed by the '#' separator. See the module docstring."""
    return chunk_id == unit_id or chunk_id.startswith(unit_id + "#")


def unit_is_in_context(unit_id: str, context: Iterable[RetrievedChunk]) -> bool:
    return any(chunk_belongs_to_unit(chunk.chunk_id, unit_id) for chunk in context)


def _sources(query_text: str, context: Sequence[RetrievedChunk]):
    """The query text with block composition on, then the three permitted fields per chunk.

    Block composition is enabled for the query alone because the block type is part of
    the information need, which the query states. The reason is recorded in
    eval/layer_predictions.md with the measurement that it changes no recovery.
    """
    yield query_text, True
    for chunk in context:
        yield chunk.text, False
        yield chunk.unit_label, False
        yield chunk.chunk_id, False


def assess(
    query_text: str, context: Sequence[RetrievedChunk], unit_index: frozenset[str]
) -> CompletenessReport:
    """The completeness predicate over one query and its fused top 10.

    Pure. No artifact is opened; the unit index arrives already loaded, from
    src.complete.references.load_unit_index, which is the layer's one permitted read.
    """
    references: list[Reference] = []
    dropped: list[DroppedReference] = []
    from_query: set[str] = set()
    for index, (source, allow_blocks) in enumerate(_sources(query_text, context)):
        found, removed = extract(source, allow_block_composition=allow_blocks)
        references.extend(found)
        dropped.extend(removed)
        if index == 0:
            for reference in found:
                from_query.update(reference.candidates)

    seen: dict[str, None] = {}
    for reference in references:
        for candidate in reference.candidates:
            seen.setdefault(candidate, None)

    resolved_units = tuple(unit for unit in seen if unit in unit_index)
    absent_units = tuple(
        unit for unit in resolved_units if not unit_is_in_context(unit, context)
    )
    query_absent_units = tuple(unit for unit in absent_units if unit in from_query)
    unresolved = tuple(
        reference for reference in references if not resolve(reference, unit_index)
    )
    return CompletenessReport(
        references=tuple(references),
        resolved_units=resolved_units,
        absent_units=absent_units,
        query_absent_units=query_absent_units,
        unresolved_references=unresolved,
        dropped_references=tuple(dropped),
    )


def context_absence_fires(report: CompletenessReport) -> bool:
    """Signal one, broad form. Any resolved unit the context set does not hold.

    Fires on almost every row of the sealed fifty, because legal and standards text
    cites itself densely. It is the augmentation trigger, not a completeness verdict.
    """
    return bool(report.absent_units)


def query_reference_absent(report: CompletenessReport) -> bool:
    """Signal one, narrow form. The QUERY named a real unit the context set does not hold.

    A per-row diagnostic, not the augmentation trigger. Measured, it is silent on three of
    the ten rows where the layer recovers a missing gold unit, test_10, test_19 and
    test_41, whose recoveries come from references printed in retrieved text or in a
    unit_label rather than in the query, so a trigger confined to this predicate would not
    fetch on them at all.

    eval/layer_predictions.md section 6.3 predicts a context-absence flag firing on exactly
    seven near-miss rows and not on test_45. That prediction is contradicted: this
    predicate and the broad one both fire on all eight. The predictions file is left
    uncorrected, because a contradicted prediction is recorded rather than edited.
    """
    return bool(report.query_absent_units)


def non_resolution_fires(report: CompletenessReport) -> bool:
    """Signal two. A well-formed reference names no unit in the corpus.

    True is a finding about the corpus and not an error: on the sealed set every row
    that fires this carries a fabricated identifier in its own query text.
    """
    return bool(report.unresolved_references)
