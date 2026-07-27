"""Corpus-wide unit index, derived from the committed chunk artifacts.

A unit is a ``parent_id``: the structural element (article, recital, subcategory,
section, appendix, and so on) that one or more chunks belong to. This module groups
every chunk in ``data/chunks/*.chunks.jsonl`` by ``parent_id`` and records, per unit,
its document, ``unit_type``, and the ordered list of chunk ids. Chunks key units on
``parent_id`` while the relation, cross-reference, duplication and pool artifacts key
them on ``unit_id``; the two are the same identifier, and this index is where the join
is made once, so nothing downstream has to bridge it again.

The index is the universe the sealed test-set frame draws from, so it is committed and
frozen like the corpus. It carries no query text, no gold, no rank and no result. It is
derivable, not authored: ``tests/test_unit_index.py`` re-derives it from the chunk
artifacts and asserts byte-equality, so a hand edit fails loudly.
"""

from __future__ import annotations

import json

from src.ingest.corpus_integrity import REPO_ROOT

CHUNK_DIR = REPO_ROOT / "data" / "chunks"
OUTPUT = REPO_ROOT / "eval" / "corpus_unit_index.json"

# Canonical document order, matching the ingestion order used elsewhere.
DOC_ORDER = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")


def _chunk_path(doc: str):
    return CHUNK_DIR / f"{doc}.chunks.jsonl"


def derive() -> dict:
    """Group all committed chunks into units. Pure function of the chunk artifacts."""
    units: dict[str, dict] = {}
    for doc in DOC_ORDER:
        for line in _chunk_path(doc).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            chunk = json.loads(line)
            uid = chunk["parent_id"]
            rec = units.get(uid)
            if rec is None:
                rec = units[uid] = {
                    "unit_id": uid,
                    "doc": chunk["doc_id"],
                    "unit_type": chunk["unit_type"],
                    "_chunks": [],
                }
            elif rec["doc"] != chunk["doc_id"] or rec["unit_type"] != chunk["unit_type"]:
                raise ValueError(
                    f"unit {uid} spans inconsistent doc/unit_type: "
                    f"{rec['doc']}/{rec['unit_type']} vs {chunk['doc_id']}/{chunk['unit_type']}"
                )
            rec["_chunks"].append((chunk["seq"], chunk["chunk_id"]))

    doc_rank = {doc: i for i, doc in enumerate(DOC_ORDER)}
    ordered = []
    for uid in sorted(units, key=lambda u: (doc_rank[units[u]["doc"]], u)):
        rec = units[uid]
        ordered.append(
            {
                "unit_id": uid,
                "doc": rec["doc"],
                "unit_type": rec["unit_type"],
                "chunks": [cid for _, cid in sorted(rec["_chunks"])],
            }
        )

    by_document = {doc: 0 for doc in DOC_ORDER}
    for unit in ordered:
        by_document[unit["doc"]] += 1

    return {
        "description": (
            "Corpus-wide unit index, derived from data/chunks/*.chunks.jsonl by grouping "
            "chunks on parent_id. A unit is a parent_id; each record carries its document, "
            "unit_type, and ordered chunk ids. Committed and frozen as the universe the sealed "
            "test-set frame draws from; tests/test_unit_index.py re-derives it and asserts "
            "byte-equality, so it cannot be hand edited without the test failing."
        ),
        "n_units": len(ordered),
        "n_chunks": sum(len(u["chunks"]) for u in ordered),
        "by_document": by_document,
        "units": ordered,
    }


def to_bytes(index: dict) -> bytes:
    """Canonical serialization. The committed file is exactly these bytes."""
    return (json.dumps(index, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build() -> dict:
    index = derive()
    OUTPUT.write_bytes(to_bytes(index))
    return index


def main() -> int:
    index = build()
    print(
        f"wrote {OUTPUT.relative_to(REPO_ROOT)}: {index['n_units']} units, "
        f"{index['n_chunks']} chunks, by document {index['by_document']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
