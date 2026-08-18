"""The four sealed retrieval metrics, against literal fixtures with their arithmetic written out.

Every fixture is a literal, so a reader checks the number by hand rather than by running anything,
and nothing here touches the sealed set's rankings. The four shapes are the ones the pre-registered
definitions actually turn on: a unit spanning several chunks, one slot with several carriers,
several disjoint slots, and the adversarial exclusion.

NOTHING IN THIS FILE RUNS RETRIEVAL. PREREGISTRATION.md orders the queries and their embeddings
before retrieval runs on them, and the runner is not executed against the sealed set until the
results commit.
"""

from __future__ import annotations

import math

import pytest

from src.score.retrieval_metrics import (
    NOT_COMPUTED,
    aggregate,
    mrr,
    ndcg_at_10,
    precision_at_10,
    recall_at_10,
    score_query,
)
from src.score.slots import assert_slots_are_disjoint

FILLER = [f"other:unit_{i}" for i in range(1, 11)]


def _ranking(*placed: tuple[int, str]) -> list[str]:
    """A ten-chunk ranking with the named chunks at the given 1-based ranks."""
    out = list(FILLER)
    for rank, chunk in placed:
        out[rank - 1] = chunk
    return out


# ---------------------------------------------------------------------------- fixture 1
def test_a_multi_chunk_unit_satisfies_its_slot_from_any_of_its_chunks():
    """One slot, one unit, two of its chunks retrieved at ranks 3 and 7.

    Arithmetic. Two of ten chunks belong to the gold unit, so precision is 0.2 on a carrier count
    of 1. One slot of one is satisfied, so recall is 1.0. The first satisfying chunk is at rank 3,
    so MRR is 1/3. NDCG is one gain at rank 3 over an ideal of one gain at rank 1, that is
    (1/log2 4) / (1/log2 2) = 0.5.

    97 of 1150 corpus units span more than one chunk, up to 12 for nist_ai_600_1:app_B, so this is
    the shape the unit-to-chunk collapse exists for rather than a constructed edge case.
    """
    top = _ranking((3, "eu_ai_act:art_10#p2"), (7, "eu_ai_act:art_10#p1"))
    gold = [["eu_ai_act:art_10"]]

    p = precision_at_10(top, gold)
    assert p["precision_at_10"] == 0.2
    assert p["matching_chunks"] == 2
    assert p["carrier_count"] == 1
    assert p["carriers_in_top10"] == ["eu_ai_act:art_10"]

    assert recall_at_10(top, gold) == {"recall_at_10": 1.0, "slots_satisfied": 1, "slots_total": 1}

    m = mrr(top, gold)
    assert m["mrr"] == pytest.approx(1 / 3)
    assert m["first_satisfying_rank"] == 3
    assert m["first_satisfying_chunk"] == "eu_ai_act:art_10#p2"

    n = ndcg_at_10(top, gold)
    assert n["ndcg_at_10"] == pytest.approx((1 / math.log2(4)) / (1 / math.log2(2)))
    assert n["ideal_ranks"] == [1]


def test_the_bare_unit_id_also_belongs_to_its_unit():
    """A single-chunk unit's chunk id IS the unit id, with no separator.

    1053 of 1150 units are single-chunk. A predicate requiring the separator would report every
    one of them as absent, which is the bare-membership failure inverted.
    """
    top = _ranking((1, "nist_ai_100_1:sub_MANAGE_2.2"))
    gold = [["nist_ai_100_1:sub_MANAGE_2.2"]]
    assert recall_at_10(top, gold)["slots_satisfied"] == 1
    assert mrr(top, gold)["first_satisfying_rank"] == 1


def test_a_prefix_that_is_not_a_chunk_of_the_unit_does_not_satisfy():
    """art_1 must not satisfy a slot naming art_11, which a bare startswith would allow."""
    top = _ranking((1, "eu_ai_act:art_1"), (2, "eu_ai_act:art_110"))
    gold = [["eu_ai_act:art_11"]]
    assert recall_at_10(top, gold)["slots_satisfied"] == 0
    assert precision_at_10(top, gold)["matching_chunks"] == 0


# ---------------------------------------------------------------------------- fixture 2
def test_duplicated_carriers_within_one_slot_raise_precision_and_not_recall():
    """One slot naming three carriers of one statement, all three retrieved.

    Arithmetic. Three of ten chunks are gold, so precision is 0.3 on a carrier count of 3, which
    is the property the sealed file states: precision is raised by a retrieval returning several
    verbatim carriers, so the count is reported alongside. Recall is 1.0 and NDCG is 1.0, both
    unchanged from a single carrier, because a slot contributes once however many of its
    acceptable units appear. This is the MANAGE 2.2 shape, a real three-member slot on test_39.
    """
    top = _ranking((1, "nist_ai_600_1:sub_MANAGE_2.2"),
                   (2, "nist_ai_100_1:sub_MANAGE_2.2"),
                   (3, "nist_playbook:sub_MANAGE_2.2"))
    gold = [["nist_ai_600_1:sub_MANAGE_2.2",
             "nist_ai_100_1:sub_MANAGE_2.2",
             "nist_playbook:sub_MANAGE_2.2"]]

    p = precision_at_10(top, gold)
    assert p["precision_at_10"] == 0.3
    assert p["carrier_count"] == 3
    assert len(p["carriers_in_top10"]) == 3

    assert recall_at_10(top, gold)["recall_at_10"] == 1.0
    assert ndcg_at_10(top, gold)["ndcg_at_10"] == pytest.approx(1.0)

    # One carrier alone scores the same on recall and NDCG, and lower on precision.
    one = _ranking((1, "nist_ai_100_1:sub_MANAGE_2.2"))
    assert recall_at_10(one, gold)["recall_at_10"] == 1.0
    assert ndcg_at_10(one, gold)["ndcg_at_10"] == pytest.approx(1.0)
    assert precision_at_10(one, gold)["precision_at_10"] == 0.1


def test_the_precision_denominator_is_ten_and_not_the_ranking_length():
    """The denominator is fixed at K, which a ten-long fixture cannot demonstrate.

    Every other fixture here hands in ten chunks, so len(matching)/K and
    len(matching)/len(top_chunks) agree and a mutation between them is invisible. Found by the
    mutation run rather than by reading. This drives a short ranking straight into the metric,
    where the two differ: one matching chunk out of five is 0.2 by the wrong denominator and 0.1
    by the right one.

    The metric does not enforce depth; the runner does, raising on any ranking that is not ten
    long. That division of labour is deliberate. If the metric rescaled instead, a short ranking
    would silently produce a HIGHER precision than the same hits in a full one, which is the
    direction that flatters a result.
    """
    short = ["eu_ai_act:art_43", "x:1", "x:2", "x:3", "x:4"]
    gold = [["eu_ai_act:art_43"]]
    p = precision_at_10(short, gold)
    assert p["k"] == 10
    assert p["matching_chunks"] == 1
    assert p["precision_at_10"] == 0.1, (
        f"precision is {p['precision_at_10']} on a five-chunk ranking; the denominator followed "
        "the ranking length instead of staying at ten"
    )
    assert p["precision_at_10"] != 0.2


def test_mrr_takes_the_first_satisfying_rank_across_slots_and_not_the_last():
    """Two slots satisfied at different ranks, so the first and last rank differ.

    Every single-slot fixture makes min and max over the satisfied ranks identical, so a mutation
    between them passes. Found by the mutation run. Here slot 0 is satisfied at rank 6 and slot 1
    at rank 2, so MRR is 1/2 by the definition and would be 1/6 if the last were taken.
    """
    top = _ranking((6, "eu_ai_act:art_43"), (2, "eu_ai_act:art_97"))
    gold = [["eu_ai_act:art_43"], ["eu_ai_act:art_97"]]
    m = mrr(top, gold)
    assert m["first_satisfying_rank"] == 2
    assert m["first_satisfying_chunk"] == "eu_ai_act:art_97"
    assert m["mrr"] == pytest.approx(0.5), (
        f"MRR is {m['mrr']}; 1/6 would mean the last satisfying rank was taken"
    )
    assert m["mrr"] != pytest.approx(1 / 6)


def test_mrr_takes_the_earliest_chunk_within_one_slot():
    """The same distinction inside a single slot with two carriers at different ranks."""
    top = _ranking((4, "nist_ai_100_1:sub_MANAGE_2.2"), (9, "nist_ai_600_1:sub_MANAGE_2.2"))
    gold = [["nist_ai_100_1:sub_MANAGE_2.2", "nist_ai_600_1:sub_MANAGE_2.2"]]
    m = mrr(top, gold)
    assert m["first_satisfying_rank"] == 4
    assert m["mrr"] == pytest.approx(0.25)


def test_no_precision_figure_can_be_obtained_without_its_carrier_count():
    """The sealed requirement, held by the return type rather than by a caller's discipline.

    There is no function returning the fraction alone, so a caller cannot quote the number
    without the count arriving with it. Loosening the return to a float would fail here.
    """
    p = precision_at_10(_ranking((1, "a:b")), [["a:b"]])
    assert isinstance(p, dict)
    assert "precision_at_10" in p and "carrier_count" in p
    assert set(p) >= {"precision_at_10", "matching_chunks", "k", "carrier_count",
                      "carriers_in_top10"}


# ---------------------------------------------------------------------------- fixture 3
def test_multiple_disjoint_slots_score_each_part_separately():
    """Two slots, the first satisfied at rank 2 and the second not at all.

    Arithmetic. One of ten chunks is gold, so precision is 0.1 on a carrier count of 2. One slot
    of two is satisfied, so recall is 0.5. The first satisfying chunk is at rank 2, so MRR is 0.5.
    NDCG is one gain at rank 2 over an ideal of gains at ranks 1 and 2, that is
    (1/log2 3) / (1/log2 2 + 1/log2 3).
    """
    top = _ranking((2, "eu_ai_act:art_43"))
    gold = [["eu_ai_act:art_43"], ["eu_ai_act:art_97"]]

    assert precision_at_10(top, gold)["precision_at_10"] == 0.1
    assert precision_at_10(top, gold)["carrier_count"] == 2
    assert recall_at_10(top, gold) == {"recall_at_10": 0.5, "slots_satisfied": 1, "slots_total": 2}
    assert mrr(top, gold)["mrr"] == 0.5

    n = ndcg_at_10(top, gold)
    expected = (1 / math.log2(3)) / (1 / math.log2(2) + 1 / math.log2(3))
    assert n["ndcg_at_10"] == pytest.approx(expected)
    assert n["ideal_ranks"] == [1, 2]
    assert n["ndcg_at_10"] <= 1.0


def test_ndcg_raises_on_overlapping_slots_rather_than_returning_above_one():
    """Disjointness is a precondition of the definition, not an assumption about the data."""
    overlapping = [["a:b"], ["a:b", "c:d"]]
    with pytest.raises(ValueError, match="disjoint"):
        ndcg_at_10(_ranking((1, "a:b")), overlapping)
    with pytest.raises(ValueError, match="disjoint"):
        assert_slots_are_disjoint(overlapping)
    with pytest.raises(ValueError, match="disjoint"):
        score_query(_ranking((1, "a:b")), overlapping)


def test_a_total_miss_scores_zero_on_every_metric():
    """No chunk satisfies any slot. MRR is 0.0 by convention, which keeps a mean well defined."""
    top = list(FILLER)
    gold = [["eu_ai_act:art_43"], ["eu_ai_act:art_97"]]
    assert precision_at_10(top, gold)["precision_at_10"] == 0.0
    assert recall_at_10(top, gold)["recall_at_10"] == 0.0
    assert mrr(top, gold) == {"mrr": 0.0, "first_satisfying_rank": None,
                              "first_satisfying_chunk": None}
    assert ndcg_at_10(top, gold)["ndcg_at_10"] == 0.0


# ---------------------------------------------------------------------------- fixture 4
def test_an_adversarial_row_is_carried_and_marked_rather_than_dropped():
    """Empty gold, non-empty ranking. Every metric is absent and the marker says why."""
    metrics, note = score_query(_ranking((1, "eu_ai_act:art_43")), [])
    assert metrics is None
    assert note == NOT_COMPUTED
    assert "gold is empty" in note


def test_aggregates_exclude_on_the_marker_and_not_on_a_stratum_name():
    """A later gold-empty stratum is excluded by the same rule with no edit to the aggregator."""
    scored = [
        {"id": "a", "carrier_count": 1,
         "metrics": {"precision_at_10": 0.2, "recall_at_10": 1.0, "mrr": 0.5, "ndcg_at_10": 1.0}},
        {"id": "b", "carrier_count": 3,
         "metrics": {"precision_at_10": 0.4, "recall_at_10": 0.0, "mrr": 0.0, "ndcg_at_10": 0.0}},
        {"id": "adv", "carrier_count": 0, "metrics": None, "metrics_note": NOT_COMPUTED},
    ]
    agg = aggregate(scored)
    assert agg["n_queries"] == 2, "the marked row entered the denominator"
    assert agg["precision_at_10"] == pytest.approx(0.3)
    assert agg["recall_at_10"] == pytest.approx(0.5)
    assert agg["carrier_count_min"] == 1 and agg["carrier_count_max"] == 3

    assert aggregate([scored[2]]) == {"n_queries": 0}


def test_the_aggregate_is_a_macro_average_over_queries():
    """Macro over queries, ruled. A micro-average over slots is a different number and is not
    computed anywhere, so the two cannot be confused in the artifact."""
    scored = [
        {"id": "one_slot", "carrier_count": 1,
         "metrics": {"precision_at_10": 0.0, "recall_at_10": 1.0, "mrr": 1.0, "ndcg_at_10": 1.0}},
        {"id": "ten_slots", "carrier_count": 1,
         "metrics": {"precision_at_10": 0.0, "recall_at_10": 0.0, "mrr": 0.0, "ndcg_at_10": 0.0}},
    ]
    # Macro: each query weighs one, so recall is 0.5. A micro-average over 1 and 10 slots would
    # be 1/11, and that number appears nowhere.
    assert aggregate(scored)["recall_at_10"] == pytest.approx(0.5)
    assert aggregate(scored)["recall_at_10"] != pytest.approx(1 / 11)


def test_score_query_returns_all_four_metrics_in_one_record():
    """A caller cannot obtain a partial score, so no artifact row can carry three of the four."""
    metrics, note = score_query(_ranking((1, "a:b")), [["a:b"]])
    assert note is None
    for key in ("precision_at_10", "recall_at_10", "mrr", "ndcg_at_10",
                "carrier_count", "slots_total", "matching_chunks"):
        assert key in metrics, f"score_query omitted {key}"
