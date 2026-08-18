"""The four sealed retrieval metrics, exactly as PREREGISTRATION.md defines them.

No I/O. Every function takes one query's ranking and gold and returns a record, so a fixture is a
literal and a metric can be argued about without a corpus in the room. The runner is the only
thing that reads files.

THE DEFINITIONS, quoted from the sealed file rather than paraphrased:

  Precision@10 "is the fraction of the ten retrieved chunks whose unit satisfies a slot, scored
  over chunks because the ten positions are chunks and each one occupies context the model
  receives. It is therefore raised by a retrieval returning several verbatim carriers of one
  statement, so each query's carrier count is reported alongside it and no precision figure is
  quoted without it."

  "Recall@10 is slots satisfied over total slots. MRR is the reciprocal of the rank of the first
  chunk whose unit satisfies any slot. Both are scored over units, because gold is defined at
  unit level."

  "NDCG@10 assigns gain 1 to each slot at the rank of the first chunk satisfying it, and a slot
  contributes once however many of its acceptable units, or their chunks, appear. The ideal is
  those gains at ranks 1 through min(10, the number of slots)."

  "Not computed for adversarial queries, whose gold is empty."

NO BARE PRECISION FLOAT EXISTS. precision_at_10 returns a record carrying the carrier count, and
there is no function that returns the fraction alone. That is the mechanism which makes "no
precision figure is quoted without it" a property of the code rather than a convention a caller
has to remember: a caller cannot obtain the number without the count coming with it.
"""

from __future__ import annotations

import math

from src.score.carriers import carrier_count, carriers_in, unit_of
from src.score.slots import assert_slots_are_disjoint, slot_satisfaction

K = 10


def precision_at_10(top_chunks: list[str], gold_slots: list[list[str]]) -> dict:
    """Fraction of the ten retrieved CHUNKS whose unit satisfies a slot, with its carrier count.

    The denominator is K, not len(top_chunks). A short ranking is a defect in the run rather than
    a reason to shrink the denominator, and shrinking it would quietly inflate the figure, so the
    caller is expected to have asserted the depth. Bounded above by the available gold chunk count
    over ten, which is a property of precision at a fixed k rather than of the retriever.
    """
    gold_units = {unit for slot in gold_slots for unit in slot}
    matching = [c for c in top_chunks if unit_of(c) in gold_units]
    return {
        "precision_at_10": len(matching) / K,
        "matching_chunks": len(matching),
        "k": K,
        "carrier_count": carrier_count(gold_slots),
        "carriers_in_top10": carriers_in(top_chunks, gold_slots),
    }


def recall_at_10(top_chunks: list[str], gold_slots: list[list[str]]) -> dict:
    """Slots satisfied over total slots. Scored over units, because gold is unit-level."""
    hits = slot_satisfaction(top_chunks, gold_slots)
    satisfied = sum(1 for h in hits if h.satisfied)
    return {
        "recall_at_10": satisfied / len(gold_slots),
        "slots_satisfied": satisfied,
        "slots_total": len(gold_slots),
    }


def mrr(top_chunks: list[str], gold_slots: list[list[str]]) -> dict:
    """Reciprocal of the rank of the first chunk whose unit satisfies ANY slot.

    Zero when no chunk satisfies any slot, which is the ordinary convention and is what makes a
    stratum-level mean well defined over queries that missed entirely.
    """
    hits = slot_satisfaction(top_chunks, gold_slots)
    ranks = [h.first_satisfying_rank for h in hits if h.first_satisfying_rank is not None]
    if not ranks:
        return {"mrr": 0.0, "first_satisfying_rank": None, "first_satisfying_chunk": None}
    best = min(ranks)
    chunk = next(h.first_satisfying_chunk for h in hits if h.first_satisfying_rank == best)
    return {"mrr": 1.0 / best, "first_satisfying_rank": best, "first_satisfying_chunk": chunk}


def ndcg_at_10(top_chunks: list[str], gold_slots: list[list[str]]) -> dict:
    """Gain 1 per slot at its first satisfaction; ideal at ranks 1..min(10, number of slots).

    A slot contributes once however many of its acceptable units or their chunks appear, which is
    what makes returning one carrier of a duplicated statement score the same as returning all of
    them, as the sealed rule requires.

    Raises on overlapping slots rather than returning a number above one. Disjointness is a
    precondition of the definition, so a set that violates it has no NDCG rather than a large one.
    """
    assert_slots_are_disjoint(gold_slots)
    hits = slot_satisfaction(top_chunks, gold_slots)
    dcg = sum(1.0 / math.log2(h.first_satisfying_rank + 1)
              for h in hits if h.first_satisfying_rank is not None)
    ideal_ranks = list(range(1, min(K, len(gold_slots)) + 1))
    idcg = sum(1.0 / math.log2(r + 1) for r in ideal_ranks)
    return {
        "ndcg_at_10": (dcg / idcg) if idcg else 0.0,
        "dcg": dcg,
        "idcg": idcg,
        "ideal_ranks": ideal_ranks,
    }


NOT_COMPUTED = "not computed; gold is empty per PREREGISTRATION.md"


def score_query(top_chunks: list[str], gold_slots: list[list[str]]) -> tuple[dict | None, str | None]:
    """All four metrics for one query, or (None, marker) when the gold is empty.

    The marker travels with the row rather than the row being dropped, so an adversarial query is
    visibly carried and excluded rather than quietly missing from the artifact. Aggregation
    excludes on this marker rather than on a stratum name, so a later gold-empty stratum is
    excluded by the same rule without anyone editing the aggregator.
    """
    if not gold_slots:
        return None, NOT_COMPUTED
    assert_slots_are_disjoint(gold_slots)
    return (
        {
            **precision_at_10(top_chunks, gold_slots),
            **recall_at_10(top_chunks, gold_slots),
            **mrr(top_chunks, gold_slots),
            **ndcg_at_10(top_chunks, gold_slots),
        },
        None,
    )


METRIC_KEYS = ("precision_at_10", "recall_at_10", "mrr", "ndcg_at_10")


def aggregate(scored: list[dict]) -> dict:
    """Macro-average over queries, excluding rows carrying the not-computed marker.

    Macro over queries rather than micro over slots, ruled because every headline in the sealed
    file is per-query. The two are different numbers and the choice is stated in the artifact's
    description rather than left to be inferred.
    """
    usable = [row for row in scored if row.get("metrics") is not None]
    if not usable:
        return {"n_queries": 0}
    out = {"n_queries": len(usable)}
    for key in METRIC_KEYS:
        out[key] = sum(row["metrics"][key] for row in usable) / len(usable)
    counts = sorted(row["carrier_count"] for row in usable)
    out["carrier_count_min"] = counts[0]
    out["carrier_count_max"] = counts[-1]
    out["carrier_count_median"] = counts[len(counts) // 2]
    return out
