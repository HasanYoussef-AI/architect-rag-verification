"""The two id spaces, and the NDCG bound over the sealed set's real gold.

Gold is unit-level and retrieval returns chunks, so the collapse between them is the one place a
definitional error changes every metric silently. Both predicates are exercised in both
directions, and the bound is checked against the committed gold rather than against a fixture,
because the disjointness precondition it rests on is a property of that gold.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.score.retrieval_metrics import ndcg_at_10
from src.score.slots import (
    assert_slots_are_disjoint,
    chunk_belongs_to_unit,
    slot_satisfaction,
    unit_satisfies_slot,
)

QUERIES = REPO_ROOT / "eval" / "test_queries.jsonl"


def _rows():
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_the_chunk_id_predicate_is_the_prefix_rule_and_not_bare_membership():
    """Exact match, or the unit id followed by the separator. Both directions asserted.

    Bare membership is the wrong implementation of the same requirement and reports 97 of 1150
    real unit ids as absent, so its empty results are evidence of nothing. The separator matters:
    without it art_1 would claim art_11's chunks.
    """
    assert chunk_belongs_to_unit("eu_ai_act:art_10", "eu_ai_act:art_10")
    assert chunk_belongs_to_unit("eu_ai_act:art_10#p1", "eu_ai_act:art_10")
    assert chunk_belongs_to_unit("eu_ai_act:art_10#p12", "eu_ai_act:art_10")

    assert not chunk_belongs_to_unit("eu_ai_act:art_100", "eu_ai_act:art_10")
    assert not chunk_belongs_to_unit("eu_ai_act:art_1", "eu_ai_act:art_10")
    assert not chunk_belongs_to_unit("nist_ai_100_1:art_10", "eu_ai_act:art_10")


def test_the_unit_id_predicate_is_exact_membership():
    """Deliberately not a prefix rule: the slot names units, and art_1 is not art_11."""
    slot = ["eu_ai_act:art_11", "eu_ai_act:art_97"]
    assert unit_satisfies_slot("eu_ai_act:art_11", slot)
    assert unit_satisfies_slot("eu_ai_act:art_97", slot)
    assert not unit_satisfies_slot("eu_ai_act:art_1", slot)
    assert not unit_satisfies_slot("eu_ai_act:art_110", slot)
    assert not unit_satisfies_slot("eu_ai_act:art_11#p1", slot), (
        "a chunk id satisfied a slot; slots name units and the two spaces are not interchangeable"
    )


def test_slot_satisfaction_reports_the_first_rank_and_every_carrier():
    """The rank is the first one; the carriers are all of them, because precision needs them."""
    top = ["x:1", "eu_ai_act:art_10#p2", "y:1", "eu_ai_act:art_10#p1", "nist:sub_A"]
    hits = slot_satisfaction(top, [["eu_ai_act:art_10", "nist:sub_A"]])
    assert len(hits) == 1
    assert hits[0].satisfied
    assert hits[0].first_satisfying_rank == 2
    assert hits[0].first_satisfying_chunk == "eu_ai_act:art_10#p2"
    assert set(hits[0].satisfying_units) == {"eu_ai_act:art_10", "nist:sub_A"}

    missed = slot_satisfaction(["a:1", "b:2"], [["c:3"]])
    assert missed[0].satisfied is False
    assert missed[0].first_satisfying_rank is None
    assert missed[0].satisfying_units == ()


def test_the_disjointness_precondition_holds_on_every_committed_row():
    """The sealed gold satisfies the precondition NDCG rests on, checked through the raiser."""
    for row in _rows():
        assert_slots_are_disjoint(row["gold_slots"])


def test_the_disjointness_raiser_can_fail():
    """V20, through the same function the precondition uses."""
    with pytest.raises(ValueError, match="slots 0 and 1 both admit"):
        assert_slots_are_disjoint([["a:1"], ["a:1", "b:2"]])
    with pytest.raises(ValueError, match="disjoint"):
        assert_slots_are_disjoint([["a:1"], ["b:2"], ["c:3", "a:1"]])


def test_ndcg_is_at_or_below_one_on_every_committed_gold_set():
    """The bound, over the real gold rather than over a fixture.

    Gold-only: the ranking handed in is fabricated, so no retrieval runs and nothing here depends
    on the sealed set's results, which do not exist. What is being checked is that the ideal is
    built correctly for each row's slot count, which is what keeps the metric bounded.
    """
    for row in _rows():
        gold = row["gold_slots"]
        if not gold:
            continue
        # A ranking that satisfies every slot as early as possible, the best case for the bound.
        best = [slot[0] for slot in gold]
        best += [f"filler:{i}" for i in range(10 - len(best))]
        result = ndcg_at_10(best[:10], gold)
        assert result["ndcg_at_10"] <= 1.0 + 1e-12, (
            f"{row['id']}: NDCG is {result['ndcg_at_10']}, above one"
        )
        assert result["ndcg_at_10"] == pytest.approx(1.0), (
            f"{row['id']}: a ranking satisfying every slot in order should score exactly one, "
            f"got {result['ndcg_at_10']}"
        )
        assert result["ideal_ranks"] == list(range(1, min(10, len(gold)) + 1))


def test_no_retrieval_runs_anywhere_in_the_scoring_tests():
    """The ordering constraint, asserted over this module's own sources.

    PREREGISTRATION.md orders retrieval after the queries and their embeddings. The metrics
    modules are pure and their tests are literal-driven, and this asserts that stays true: a
    scoring test that imported the retriever would run retrieval against the sealed set at
    collection time, which is exactly what the gate exists to prevent.

    Asserted over the parsed import graph rather than over the file's text. A substring check
    matched its own assertion string and reported this file as importing the retriever, which is
    a detector that cannot distinguish a mention from a use. The claim here is structural, so the
    instrument is structural.
    """
    import ast
    import pathlib

    for name in ("test_score_slots.py", "test_retrieval_metrics.py"):
        path = pathlib.Path(__file__).parent / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        offending = sorted(m for m in imported if "retrieve" in m or "retriever" in m)
        assert not offending, f"{name} imports {offending}, which would run retrieval"

    # The detector is shown capable of failing, on a module that really does import the retriever.
    tree = ast.parse("from src.retrieve.retriever import load_retriever")
    found = {f"{n.module}.{a.name}" for n in ast.walk(tree)
             if isinstance(n, ast.ImportFrom) and n.module for a in n.names}
    assert any("retriever" in m for m in found), "the import detector cannot see a real import"
