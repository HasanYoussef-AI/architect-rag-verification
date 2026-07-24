"""Derived retrieval artifacts match a fresh mechanical recomputation.

The verbatim group artifact and the reserved development pool are committed data.
These tests refuse a committed artifact that no longer matches what the frozen
corpus mechanically produces, so a stale artifact fails loudly.
"""

from __future__ import annotations

import json
from collections import defaultdict

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison
from src.retrieve.retriever import load_corpus_chunks

VERBATIM = REPO_ROOT / "data" / "retrieval" / "verbatim_groups.json"
POOL = REPO_ROOT / "eval" / "dev_unit_pool.json"


def _groups(key):
    groups = defaultdict(list)
    for chunk in load_corpus_chunks():
        groups[key(chunk)].append(chunk["chunk_id"])
    return sorted([sorted(v) for v in groups.values() if len(v) > 1], key=lambda g: g[0])


def test_normalised_verbatim_groups_match():
    art = json.loads(VERBATIM.read_text())["bases"]["normalised_identity"]
    recomputed = _groups(lambda c: normalise_for_comparison(c["text"]))
    assert [g["members"] for g in art["groups"]] == recomputed
    assert art["n_groups"] == len(recomputed) == 55


def test_raw_verbatim_groups_match():
    art = json.loads(VERBATIM.read_text())["bases"]["raw_identity"]
    recomputed = _groups(lambda c: c["text"])
    assert [g["members"] for g in art["groups"]] == recomputed
    assert art["n_groups"] == len(recomputed) == 23


def test_dev_pool_covers_every_stratum_with_forty_units():
    pool = json.loads(POOL.read_text())
    assert pool["n_units_selected"] == 40 == len(pool["units"])
    assert len(pool["strata"]) == 22


def test_dev_pool_units_are_real_and_unique():
    pool = json.loads(POOL.read_text())
    valid = {c["parent_id"] for c in load_corpus_chunks()}
    ids = [u["unit_id"] for u in pool["units"]]
    assert len(ids) == len(set(ids))
    assert all(u in valid for u in ids)


def test_dev_pool_member_chunks_belong_to_their_units():
    pool = json.loads(POOL.read_text())
    by_parent: dict[str, set[str]] = defaultdict(set)
    for chunk in load_corpus_chunks():
        by_parent[chunk["parent_id"]].add(chunk["chunk_id"])
    for unit in pool["units"]:
        assert set(unit["chunks"]) == by_parent[unit["unit_id"]]
