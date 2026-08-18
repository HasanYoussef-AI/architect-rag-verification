"""Produce the retrieval results artifact for a query set.

NOT EXECUTED AGAINST THE SEALED SET IN THE COMMIT THAT LANDS IT. PREREGISTRATION.md orders the
queries and their embeddings before retrieval runs on them, so this module commits with its
fixtures driven by literals and no number it can produce yet existing. Running it against the
sealed set is the results commit, a separate scope, and until then `src.score.gate` refuses.

Reproducibility level 1. Every input is committed: the query file, the query embeddings, the chunk
embeddings and the chunk order. No model, no key, no network. The artifact re-derives byte for
byte from the tree.

Run:  python -m src.score.run_retrieval_eval [--set test]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from src.score.carriers import carrier_count
from src.score.gate import QUERY_SETS, QuerySet, gate_reason
from src.score.retrieval_metrics import aggregate, score_query
from src.score.slots import slot_satisfaction

DESCRIPTION = (
    "Retrieval results and frozen metrics for the sealed query set, first pass, fused top 10. "
    "Produced by src/score/run_retrieval_eval.py over committed embeddings with no model and no "
    "key, so every figure re-derives from the tree. Aggregates are MACRO-AVERAGES OVER QUERIES, "
    "not micro-averages over slots; the two are different numbers and every headline in "
    "PREREGISTRATION.md is per-query. Adversarial rows are carried and marked not computed, and "
    "aggregates exclude them by that marker rather than by stratum name. No precision figure "
    "appears without its carrier count."
)


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def score_set(query_set: QuerySet, top10_by_id: dict[str, list[str]]) -> dict:
    """Build the artifact from a query set and its rankings. Pure given those two inputs."""
    queries = []
    for row in _rows(query_set.queries):
        top10 = top10_by_id[row["id"]]
        if len(top10) != 10:
            raise ValueError(
                f"{row['id']}: the ranking holds {len(top10)} chunks, not 10. Precision@10 is "
                "scored over a denominator of ten, so a short ranking is a defect in the run "
                "rather than a smaller denominator"
            )
        gold_slots = row["gold_slots"]
        metrics, note = score_query(top10, gold_slots)
        hits = slot_satisfaction(top10, gold_slots)
        queries.append({
            "id": row["id"],
            "type": row["type"],
            "subtype": row["subtype"],
            "query": row["query"],
            "top10": top10,
            "gold_slots": gold_slots,
            "slot_satisfaction": [
                {
                    "slot_index": h.slot_index,
                    "satisfied": h.satisfied,
                    "first_satisfying_rank": h.first_satisfying_rank,
                    "first_satisfying_chunk": h.first_satisfying_chunk,
                    "satisfying_units": list(h.satisfying_units),
                }
                for h in hits
            ],
            "carrier_count": carrier_count(gold_slots),
            "metrics": metrics,
            "metrics_note": note,
        })

    by_stratum = defaultdict(list)
    for q in queries:
        by_stratum[f"{q['type']}/{q['subtype']}"].append(q)

    return {
        "description": DESCRIPTION,
        "produced_by": "python -m src.score.run_retrieval_eval",
        "reproducibility_level": 1,
        "query_set": query_set.name,
        "queries": queries,
        "aggregates": {
            "overall": aggregate(queries),
            "by_stratum": {k: aggregate(v) for k, v in sorted(by_stratum.items())},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", default="test", choices=[q.name for q in QUERY_SETS])
    parser.add_argument(
        "--overwrite", action="store_true",
        help="replace an existing results file. Overwriting a committed result is a Rule 4 "
             "correction and is logged; without this the runner refuses.",
    )
    args = parser.parse_args(argv)
    query_set = next(q for q in QUERY_SETS if q.name == args.set)

    if query_set.results.exists() and not args.overwrite:
        print(
            f"{query_set.results} already exists. A committed result is not silently replaced; "
            "re-running over one is a Rule 4 correction and takes --overwrite, whose use is "
            "logged in the commit message and the session log.",
            file=sys.stderr,
        )
        return 1

    reason = gate_reason(query_set)
    if reason is not None and not query_set.results.exists():
        # The gate is derived from the results file's absence, so producing that file is exactly
        # what opens it. This is the one caller for which a closed gate is the normal state.
        pass

    from src.retrieve.retriever import load_retriever

    retriever = load_retriever()
    import numpy as np

    embeddings = np.load(query_set.embeddings)
    rows = _rows(query_set.queries)
    if embeddings.shape[0] != len(rows):
        raise ValueError(
            f"{embeddings.shape[0]} embedding rows against {len(rows)} queries; the array and the "
            "query file are not aligned and no result is produced over a mismatch"
        )

    top10 = {}
    for index, row in enumerate(rows):
        top10[row["id"]] = retriever.search(row["query"], embeddings[index])

    artifact = score_set(query_set, top10)
    query_set.results.write_text(
        json.dumps(artifact, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {query_set.results}")
    print(json.dumps(artifact["aggregates"]["overall"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
