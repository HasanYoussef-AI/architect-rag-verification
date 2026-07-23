"""Cross-document forward-reference validation across the three NIST documents.

The identifiers are derived mechanically from each document's own printed
identifiers, with no adjustment to match another document's prediction. This
enforces that the prediction and the derivation agree: AI 100-1's structural_join
must decompose to exactly 72 Playbook targets and 49 AI 600-1 targets, and every
one of those targets, plus the reverse joins, the duplication-map targets, and
the action-to-subcategory edges, must resolve to a real unit. A mismatch here is
a finding about one of the ingestion steps, so it fails loudly.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.nist_ai_100_1 import build as build_ai_100_1
from src.ingest.nist_ai_600_1 import build as build_ai_600_1
from src.ingest.nist_playbook import OUTPUT_DIR
from src.ingest.nist_playbook import build as build_playbook


@pytest.fixture(scope="module")
def corpus():
    build_ai_100_1()
    build_ai_600_1()
    build_playbook()

    def rows(name):
        path = OUTPUT_DIR / name
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]

    units = {
        doc: {c["parent_id"] for c in rows(f"{doc}.chunks.jsonl")}
        for doc in ("nist_ai_100_1", "nist_ai_600_1", "nist_playbook")
    }
    relations = {doc: rows(f"{doc}.relations.jsonl") for doc in units}
    duplication = json.loads((OUTPUT_DIR / "nist_ai_100_1.duplication_map.json").read_text("utf-8"))
    return units, relations, duplication


def test_ai_100_1_join_decomposes_to_72_playbook_and_49_ai_600_1(corpus):
    units, relations, _ = corpus
    joins = [j for r in relations["nist_ai_100_1"] for j in r["structural_join"]]
    to_playbook = [j["unit_id"] for j in joins if j["doc_id"] == "nist_playbook"]
    to_ai_600_1 = [j["unit_id"] for j in joins if j["doc_id"] == "nist_ai_600_1"]
    assert len(to_playbook) == 72
    assert len(to_ai_600_1) == 49
    assert all(target in units["nist_playbook"] for target in to_playbook)
    assert all(target in units["nist_ai_600_1"] for target in to_ai_600_1)


def test_every_structural_join_edge_resolves(corpus):
    units, relations, _ = corpus
    all_units = set().union(*units.values())
    for doc, records in relations.items():
        for record in records:
            for join in record.get("structural_join", []):
                assert join["unit_id"] in all_units, f"{doc} join to missing {join['unit_id']}"


def test_every_duplication_target_resolves(corpus):
    units, _, duplication = corpus
    all_units = set().union(*units.values())
    targets = [entry["unit_id"] for row in duplication for entry in row["duplicated_in"]]
    assert targets
    assert all(target in all_units for target in targets)


def test_every_action_subcategory_edge_resolves_within_ai_600_1(corpus):
    units, relations, _ = corpus
    edges = [e for r in relations["nist_ai_600_1"] for e in r.get("action_subcategory", [])]
    assert len(edges) == 212
    assert all(edge["unit_id"] in units["nist_ai_600_1"] for edge in edges)


def test_every_resolved_prose_xref_target_resolves(corpus):
    units, relations, _ = corpus
    all_units = set().union(*units.values())
    for doc, records in relations.items():
        for record in records:
            for reference in record.get("prose_xrefs", []):
                assert reference["target"] in all_units, f"{doc}: {reference['target']}"
