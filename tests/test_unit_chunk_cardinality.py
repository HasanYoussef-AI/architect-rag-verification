"""Unit-to-chunk cardinality, re-derived and pinned against the manifest.

Gold is unit-level and slot-based; first-pass retrieval returns a top 10 of chunks. The
collapse from chunks to units is therefore a definitional choice, and no retrieval metric
in this repository has made it yet. This module measures the population that choice acts
on, before the metric exists, so the measurement cannot be shaped by a metric written
around it.

Every number recorded under ``unit_chunk_cardinality`` in the retrieval manifest is
re-derived here from ``eval/corpus_unit_index.json`` and ``eval/test_frame.json`` and
compared. A hand edit to the manifest, or a change to either artifact, fails.
"""

from __future__ import annotations

import collections
import json

from src.ingest.corpus_integrity import REPO_ROOT

MANIFEST = REPO_ROOT / "data" / "retrieval" / "retrieval_manifest.json"
UNIT_INDEX = REPO_ROOT / "eval" / "corpus_unit_index.json"
TEST_FRAME = REPO_ROOT / "eval" / "test_frame.json"
DEV_RESULTS = REPO_ROOT / "eval" / "dev_retrieval_results.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _unit_of(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def derive() -> dict:
    """Every recorded number, derived from the committed artifacts."""
    index = _load(UNIT_INDEX)
    units = index["units"]
    size = {u["unit_id"]: len(u["chunks"]) for u in units}
    multi = [u for u in units if size[u["unit_id"]] > 1]

    dist = collections.Counter(size[u["unit_id"]] for u in units)
    corpus = {
        "n_units": index["n_units"],
        "n_chunks": index["n_chunks"],
        "units_by_chunk_count": {str(k): dist[k] for k in sorted(dist)},
        "multi_chunk_units": len(multi),
        "chunks_held_by_multi_chunk_units": sum(size[u["unit_id"]] for u in multi),
        "multi_chunk_units_by_document": {
            doc: sum(1 for u in multi if u["doc"] == doc) for doc in index["by_document"]
        },
        "multi_chunk_units_by_unit_type": dict(
            sorted(
                collections.Counter(u["unit_type"] for u in multi).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
        "largest_unit": max(units, key=lambda u: size[u["unit_id"]])["unit_id"],
        "largest_unit_chunks": max(size.values()),
    }

    # Gold-side candidate populations, per stratum source, as distinct units. Which element
    # of a pair carries gold differs by stratum, so each is named rather than inferred:
    # clean multi-hop needs both endpoints, action-to-parent's gold is the parent, and the
    # near-miss near_duplicate pairs carry gold on the query side.
    frame = _load(TEST_FRAME)
    st = frame["strata"]
    sh = st["single_hop"]["sources"]
    populations = {
        **{f"single_hop.{d}": list(sh[d]["draw_order"]) for d in sh},
        "clean_multi_hop.eu_internal_xref.source": [
            e[0] for e in st["clean_multi_hop"]["sources"]["eu_internal_xref"]["draw_order"]
        ],
        "clean_multi_hop.eu_internal_xref.target": [
            e[1] for e in st["clean_multi_hop"]["sources"]["eu_internal_xref"]["draw_order"]
        ],
        "action_to_parent.action_subcategory.parent": [
            e[1] for e in st["action_to_parent"]["sources"]["action_subcategory"]["draw_order"]
        ],
        "near_miss.block_clusters": list(
            st["near_miss"]["sources"]["block_clusters"]["draw_order"]
        ),
        "near_miss.near_duplicate.query": [
            _unit_of(e[0]) for e in st["near_miss"]["sources"]["near_duplicate"]["draw_order"]
        ],
    }
    strata = {}
    for name, members in populations.items():
        distinct = sorted(set(members))
        strata[name] = {
            "distinct_candidate_units": len(distinct),
            "multi_chunk": sum(1 for u in distinct if size.get(u, 1) > 1),
        }

    # What the corpus property does to a ten-slot top-k, on the only committed retrieval run.
    observed = {
        r["id"]: len({_unit_of(c) for c in r["top10"]}) for r in _load(DEV_RESULTS)["retrieval"]
    }
    return {"corpus": corpus, "sealed_frame_gold_side": strata, "development_top10": observed}


def test_manifest_records_the_derived_cardinality():
    recorded = _load(MANIFEST)["unit_chunk_cardinality"]
    derived = derive()
    for section in ("corpus", "sealed_frame_gold_side", "development_top10"):
        assert recorded[section] == derived[section], (
            f"{section} in the manifest does not match the artifacts it is derived from"
        )


def test_every_unit_holds_at_least_one_chunk():
    assert all(u["chunks"] for u in _load(UNIT_INDEX)["units"])


def test_chunk_counts_sum_to_the_index_total():
    index = _load(UNIT_INDEX)
    assert sum(len(u["chunks"]) for u in index["units"]) == index["n_chunks"]


def test_multi_chunk_units_are_a_minority_but_not_empty():
    """Pins the direction of the finding: the population is neither absent nor dominant."""
    d = derive()["corpus"]
    assert 0 < d["multi_chunk_units"] < d["n_units"] / 2


def test_a_multi_chunk_unit_consumes_more_than_one_top10_slot():
    """The asymmetry is observed, not hypothetical: at least one committed development
    top 10 collapses to fewer than ten distinct units."""
    assert any(n < 10 for n in derive()["development_top10"].values())
