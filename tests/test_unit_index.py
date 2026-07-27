"""The corpus unit index is a pure, byte-stable derivation of the chunk artifacts.

A unit is a parent_id. The index groups every committed chunk by parent_id, and these
tests pin four properties: it re-derives byte-for-byte (so it cannot be hand edited),
it covers every chunk exactly once, it has the expected unit count, and every unit_id
referenced by the pool, the relations, the cross-references and the duplication map
resolves to an index unit. That last one is the real test of the parent_id / unit_id
bridge: the artifacts key units on unit_id, the chunks key them on parent_id, and if the
two ever diverged a reference would dangle here.
"""

from __future__ import annotations

import json

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.unit_index import DOC_ORDER, OUTPUT, _chunk_path, derive, to_bytes

DATA = REPO_ROOT / "data"
EVAL = REPO_ROOT / "eval"


def _index() -> dict:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def test_index_is_byte_identical_on_rederivation():
    assert OUTPUT.read_bytes() == to_bytes(derive())


def test_unit_count_is_1150():
    index = _index()
    assert index["n_units"] == 1150
    assert len(index["units"]) == 1150


def test_chunk_union_is_every_chunk_exactly_once():
    index = _index()
    listed = [cid for unit in index["units"] for cid in unit["chunks"]]
    assert len(listed) == 1294
    assert len(set(listed)) == 1294
    actual = set()
    for doc in DOC_ORDER:
        for line in _chunk_path(doc).read_text(encoding="utf-8").splitlines():
            if line.strip():
                actual.add(json.loads(line)["chunk_id"])
    assert set(listed) == actual


def _is_corpus_unit_id(value) -> bool:
    return isinstance(value, str) and ":" in value and value.split(":", 1)[0] in DOC_ORDER


def test_every_referenced_unit_id_resolves_to_an_index_unit():
    index_units = {unit["unit_id"] for unit in _index()["units"]}
    referenced: dict[str, set[str]] = {}

    pool = json.loads((EVAL / "dev_unit_pool.json").read_text(encoding="utf-8"))
    referenced["dev_unit_pool"] = {u["unit_id"] for u in pool["units"]}

    rel: set[str] = set()
    for doc in ("nist_ai_100_1", "nist_ai_600_1", "nist_playbook"):
        for line in (DATA / "chunks" / f"{doc}.relations.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            rel.add(record["unit_id"])
            for edge in record.get("prose_xrefs", []):
                if _is_corpus_unit_id(edge.get("target")):
                    rel.add(edge["target"])
            for edge in record.get("action_subcategory", []):
                if _is_corpus_unit_id(edge.get("unit_id")):
                    rel.add(edge["unit_id"])
            for edge in record.get("structural_join", []):
                if _is_corpus_unit_id(edge.get("unit_id")):
                    rel.add(edge["unit_id"])
    referenced["relations"] = rel

    xref: set[str] = set()
    for line in (DATA / "chunks" / "eu_ai_act.xrefs.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        xref.add(record["unit_id"])
        xref.update(t for t in record.get("refs_internal", []) if _is_corpus_unit_id(t))
    referenced["xrefs"] = xref

    dup: set[str] = set()
    for record in json.loads(
        (DATA / "chunks" / "nist_ai_100_1.duplication_map.json").read_text(encoding="utf-8")
    ):
        dup.add(record["source_unit_id"])
        dup.update(d["unit_id"] for d in record.get("duplicated_in", []))
    referenced["duplication_map"] = dup

    dangling = {src: sorted(ids - index_units) for src, ids in referenced.items() if ids - index_units}
    assert not dangling, f"unit_ids not resolving to an index unit: {dangling}"
