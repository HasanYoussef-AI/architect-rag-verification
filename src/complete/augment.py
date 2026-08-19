"""The corrective pass, component C3 of the verification layer.

Given a query and its fused top 10, C2 reports which resolved units the context set does
not hold. This module fetches those units' committed chunks and assembles the final
context set the layer hands to the model.

AUGMENTATION ONLY, which is the whole policy. The first-pass ten are never removed, never
reordered and never truncated; fetched chunks are appended after them. That invariant is
what makes the single-hop prediction exact rather than approximate: eighteen rows are
already at recall 1 on the first pass, so if no committed gold chunk can leave a context
set, the completeness delta on that stratum is zero by construction and any non-zero value
is a defect in this module rather than a result.

NO BOUND IS APPLIED. Every absent resolved unit is fetched. eval/layer_predictions.md
section 5 records the absence of a bound as a named condition and states why one is not
chosen: the ranks carrying each recovery were known when that file was written, so a bound
set here would be fitted to the observations it would be judged against. If a bound is
adopted later it is a cost decision, set from the cost budget, shipping with the
recoveries it removes reported by row.

THE TRIGGER IS THE BROAD PREDICATE, per the round-13 ruling and on measured grounds. The
narrow query-reference predicate is silent on three of the ten rows where the layer
recovers a missing gold unit, because those recoveries come from references printed in
retrieved text or in a unit_label rather than in the query, so a trigger confined to it
would not fetch on them at all.

WHAT THIS MODULE OPENS. The committed unit index, for the chunks composing each unit, and
the committed chunk store, for their text and labels. Both sit inside the layer's readable
surface. The unit index records which chunks compose a unit and never which unit relates
to another, which is why the firewall admits it; the chunk-to-unit grouping it carries is
cross-checked against the lexical chunk-id rule over the whole corpus in
tests/test_augmentation.py rather than trusted.

Fetched chunks enter as RetrievedChunk, the same type the first pass arrives in, so
`structural_path` and `parent_id` are unreachable on a fetched chunk exactly as they are
on a retrieved one. Loading is where the three admitted fields are chosen out of the
committed record, and it is the only place in this package that ever sees a full one.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.complete.absence import (
    CompletenessReport,
    RetrievedChunk,
    assess,
    context_absence_fires,
)
from src.complete.references import UNIT_INDEX_PATH
from src.ingest.corpus_integrity import REPO_ROOT

CHUNKS_DIR = REPO_ROOT / "data" / "chunks"

# The canonical corpus order, matching src/retrieve/retriever.py so a fetched chunk and a
# retrieved one are drawn from files read in the same order.
CANONICAL_DOC_ORDER = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")


@dataclass(frozen=True)
class FetchStore:
    """Everything the corrective pass may read, loaded once.

    `unit_chunks` is the unit index's own grouping, in its committed order, which fixes
    the order chunks of one fetched unit appear in. `chunks` holds only the three admitted
    values per chunk, so no caller of this module can reach a barred field through it.
    """

    unit_ids: frozenset[str]
    unit_chunks: Mapping[str, tuple[str, ...]]
    chunks: Mapping[str, RetrievedChunk]


@dataclass(frozen=True)
class AugmentationResult:
    """The corrective pass over one row."""

    first_pass: tuple[RetrievedChunk, ...]
    fetched_units: tuple[str, ...]
    fetched_chunks: tuple[RetrievedChunk, ...]
    context: tuple[RetrievedChunk, ...]
    triggered: bool
    report: CompletenessReport

    @property
    def size(self) -> int:
        """The final context set size, which is what a recovered-passage recall figure is
        read against. It is not 10, which is why the layer condition reports no metric at
        a fixed k."""
        return len(self.context)


def load_fetch_store(
    unit_index_path=None, chunks_dir=None
) -> FetchStore:
    """Load the unit index and the chunk store, keeping only the admitted chunk fields."""
    index_path = UNIT_INDEX_PATH if unit_index_path is None else unit_index_path
    directory = CHUNKS_DIR if chunks_dir is None else chunks_dir

    with open(index_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    unit_chunks = {unit["unit_id"]: tuple(unit["chunks"]) for unit in payload["units"]}

    chunks: dict[str, RetrievedChunk] = {}
    for doc in CANONICAL_DOC_ORDER:
        path = directory / f"{doc}.chunks.jsonl"
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                chunks[record["chunk_id"]] = RetrievedChunk(
                    chunk_id=record["chunk_id"],
                    text=record["text"],
                    unit_label=record["unit_label"],
                )
    return FetchStore(
        unit_ids=frozenset(unit_chunks),
        unit_chunks=unit_chunks,
        chunks=chunks,
    )


def fetch_unit(unit_id: str, store: FetchStore) -> tuple[RetrievedChunk, ...]:
    """A unit's committed chunks, in the unit index's recorded order.

    Raises on a unit the index does not carry rather than returning empty, because an
    empty fetch and an unknown unit are different facts and a silent empty would make a
    missing unit look like a unit with nothing in it.
    """
    if unit_id not in store.unit_chunks:
        raise KeyError(f"unit is not in the committed unit index: {unit_id}")
    return tuple(store.chunks[chunk_id] for chunk_id in store.unit_chunks[unit_id])


def augment(
    query_text: str, first_pass: Sequence[RetrievedChunk], store: FetchStore
) -> AugmentationResult:
    """Assess the first pass, fetch every absent resolved unit, and assemble the context.

    The returned context is the first-pass sequence unchanged, followed by the fetched
    chunks. No first-pass chunk is dropped, moved or replaced, and no fetched chunk can
    collide with one: a unit is fetched only when no first-pass chunk belongs to it.
    """
    report = assess(query_text, first_pass, store.unit_ids)
    triggered = context_absence_fires(report)

    fetched_units: list[str] = []
    fetched_chunks: list[RetrievedChunk] = []
    if triggered:
        for unit_id in report.absent_units:
            fetched_units.append(unit_id)
            fetched_chunks.extend(fetch_unit(unit_id, store))

    return AugmentationResult(
        first_pass=tuple(first_pass),
        fetched_units=tuple(fetched_units),
        fetched_chunks=tuple(fetched_chunks),
        context=tuple(first_pass) + tuple(fetched_chunks),
        triggered=triggered,
        report=report,
    )
