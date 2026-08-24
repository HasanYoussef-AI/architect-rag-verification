"""Write the results tables to results/tables/ as CSV.

Run:  python -m src.figures.build_tables [--check]

WHY CSV WHEN THE JSON ALREADY SHIPS. eval/test_grading_results.json is the artifact of record and
nothing here supersedes it. What it is not is convenient: it nests four levels deep, keys per
condition then per tier then per stratum, and interleaves prose derivation strings with the numbers
they describe, because it is written to be read alongside a claim rather than loaded into a frame.

These four files are the same numbers in tidy long form, one observation per row, so a reviewer who
wants to plot a series, diff two conditions or check an arithmetic identity can load them in one
line instead of writing a walker. They add a projection, not a fact. Every value is read from a
committed artifact and none is restated as a literal, and a rebuild test compares them byte for
byte, so the projection cannot drift from its source without turning a test red.

Reproducibility level 1. No model, no key, no network, no clock. LF is pinned in the writer for the
reason src/score/run_retrieval_eval.py records.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys

from src.ingest.corpus_integrity import REPO_ROOT

EVAL = REPO_ROOT / "eval"
TABLES_DIR = REPO_ROOT / "results" / "tables"

TIERS = ("haiku45", "sonnet5", "opus48")
CONDITIONS = ("raw", "layer", "no_context")
STRATA = ("single_hop", "clean_multi_hop", "action_to_parent", "near_miss", "adversarial")


def _load(name):
    return json.loads((EVAL / name).read_text(encoding="utf-8"))


def _fmt(v):
    """One formatting rule for every cell, so a float never reaches a file through repr."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return str(v)


def _quote(cell: str) -> str:
    """RFC 4180 quoting.

    Not decorative. The reasoning-regime values carry a comma, "Claude Haiku 4.5, no thinking",
    so an unquoted writer silently shifts every column after it by one and the file parses into
    the wrong shape rather than failing. Caught by reading the first emitted file.
    """
    if any(c in cell for c in (',', '"', "\n", "\r")):
        return '"' + cell.replace('"', '""') + '"'
    return cell


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    buf.write(",".join(_quote(h) for h in header) + "\n")
    for r in rows:
        buf.write(",".join(_quote(_fmt(c)) for c in r) + "\n")
    return buf.getvalue()


def table_unsupported_claim_rate(grading) -> str:
    """Long form: one row per condition, tier and scope. `stratum` is `all` for the tier total."""
    header = ["condition", "tier", "reasoning_regime", "stratum", "rows", "answered_rows",
              "claim_units", "ungrounded_units", "unsupported_claim_rate"]
    rows = []
    for cond in CONDITIONS:
        blk = grading["per_condition"][cond]
        regimes = blk["regime"]
        for tier in TIERS:
            t = blk["per_tier"][tier]
            rows.append([cond, tier, regimes[tier], "all", t["rows"], t["answered_rows"],
                         t["claim_units"], t["ungrounded_units"],
                         t.get("unsupported_claim_rate")])
            for stratum in STRATA:
                s = blk["per_stratum"][tier].get(stratum)
                if s is None:
                    continue
                rows.append([cond, tier, regimes[tier], stratum, s["rows"], s["answered_rows"],
                             s["claim_units"], s["ungrounded_units"],
                             s.get("unsupported_claim_rate")])
        p = blk["pooled"]
        rows.append([cond, "pooled", "", "all", p["rows"], p["answered_rows"], p["claim_units"],
                     p["ungrounded_units"], p.get("unsupported_claim_rate")])
    return _csv(header, rows)


def table_retrieval_by_stratum(retrieval, layer) -> str:
    """The two conditions side by side, under their own metric names and never a shared one."""
    header = ["stratum", "n_queries", "precision_at_10_first_pass", "recall_at_10_first_pass",
              "mrr_first_pass", "ndcg_at_10_first_pass", "recovered_passage_recall_layer",
              "context_set_size_mean_layer"]
    fp = retrieval["aggregates"]["by_stratum"]
    lay = layer["aggregates"]["by_stratum"]
    rows = []
    for key in sorted(fp):
        f = fp[key]
        lyr = lay.get(key, {})
        rows.append([key, f["n_queries"], f.get("precision_at_10"), f.get("recall_at_10"),
                     f.get("mrr"), f.get("ndcg_at_10"),
                     lyr.get("recovered_passage_recall_layer"),
                     lyr.get("context_set_size_mean")])
    f = retrieval["aggregates"]["overall"]
    lyr = layer["aggregates"]["overall"]
    rows.append(["overall", f["n_queries"], f["precision_at_10"], f["recall_at_10"], f["mrr"],
                 f["ndcg_at_10"], lyr["recovered_passage_recall_layer"],
                 lyr["context_set_size_mean"]])
    return _csv(header, rows)


def table_flagged_unit_fate(grading) -> str:
    header = ["tier", "flagged_in", "repeated_unchanged", "repeated_and_now_grounded",
              "repeated_still_unsupported", "dropped_or_rewritten",
              "rows_repeating_at_least_one"]
    fate = grading["per_condition"]["layer"]["fate_table"]
    rows = []
    for tier in TIERS:
        b = fate[tier]
        rows.append([tier, b["flagged_in"], b["repeated_unchanged"],
                     b["repeated_and_now_grounded"], b["repeated_still_unsupported"],
                     b["dropped_or_rewritten"], b["rows_repeating_at_least_one_flagged_unit"]])
    rows.append(["total",
                 sum(fate[t]["flagged_in"] for t in TIERS),
                 sum(fate[t]["repeated_unchanged"] for t in TIERS),
                 sum(fate[t]["repeated_and_now_grounded"] for t in TIERS),
                 sum(fate[t]["repeated_still_unsupported"] for t in TIERS),
                 sum(fate[t]["dropped_or_rewritten"] for t in TIERS), ""])
    return _csv(header, rows)


def table_cost_and_latency(grading) -> str:
    header = ["tier", "run", "input_tokens", "output_tokens", "cost_usd_committed",
              "cost_usd_exact_decimal", "latency_seconds_created_to_ended"]
    per_tier = grading["cost_and_latency"]["per_tier"]
    rows = []
    for tier in TIERS:
        for run in sorted(per_tier[tier]):
            b = per_tier[tier][run]
            latency = ""
            if "created_at_utc" in b and "ended_at_utc" in b:
                from datetime import datetime
                a = datetime.fromisoformat(b["created_at_utc"].replace("Z", "+00:00"))
                z = datetime.fromisoformat(b["ended_at_utc"].replace("Z", "+00:00"))
                latency = int((z - a).total_seconds())
            rows.append([tier, run, b["input_tokens"], b["output_tokens"],
                         b["cost_usd_committed"], b["cost_usd_exact_decimal"], latency])
    return _csv(header, rows)


def build_all() -> dict[str, str]:
    grading = _load("test_grading_results.json")
    retrieval = _load("test_retrieval_results.json")
    layer = _load("test_layer_results.json")
    return {
        "unsupported_claim_rate.csv": table_unsupported_claim_rate(grading),
        "retrieval_by_stratum.csv": table_retrieval_by_stratum(retrieval, layer),
        "flagged_unit_fate.csv": table_flagged_unit_fate(grading),
        "cost_and_latency.csv": table_cost_and_latency(grading),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="compare the committed tables against a fresh build, write nothing")
    args = parser.parse_args(argv)

    built = build_all()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    if args.check:
        bad = 0
        for name, text in sorted(built.items()):
            path = TABLES_DIR / name
            if not path.exists() or path.read_bytes() != text.encode("utf-8"):
                bad += 1
                print(f"DIFFERS  {name}", file=sys.stderr)
            else:
                print(f"OK       {name}  {hashlib.sha256(path.read_bytes()).hexdigest()[:16]}")
        print(f"\n{len(built) - bad} of {len(built)} match")
        return 1 if bad else 0

    for name, text in sorted(built.items()):
        path = TABLES_DIR / name
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(REPO_ROOT)}  "
              f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}  "
              f"{text.count(chr(10)) - 1} data rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
