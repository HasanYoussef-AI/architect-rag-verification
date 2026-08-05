"""Check, not an edit. Re-derive each committed duplication_scan block and diff against it.

The committed blocks compared the two endpoint units of a clean multi-hop pair against each other
at sentence granularity, floor 0.60. This runs the FINAL shipped segmenter, comparable_segments,
in that same pairwise mode so the comparison is like for like, and additionally under a
period-only segmentation so any divergence is attributable to segmentation rather than left
ambiguous.

Nothing is written. eval/test_query_verification.jsonl is opened read-only.

Run:  python -m src.goldset.check_committed_duplication_scans
"""

from __future__ import annotations

import difflib
import json
import re
from src.ingest.corpus_integrity import REPO_ROOT
from src.goldset.attributability import (
    LEXICAL_FLOOR,
    Corpus,
    exclusion_report,
    normalise_for_lexical,
)

EVAL = REPO_ROOT / "eval"
PERIOD_ONLY = re.compile(r"(?<=[.!?])\s+")


def cross_pairs(left, right, floor=LEXICAL_FLOOR):
    out = []
    for ls in left:
        ln = normalise_for_lexical(ls)
        if not ln:
            continue
        m = difflib.SequenceMatcher(None, ln, "")
        for rs in right:
            rn = normalise_for_lexical(rs)
            if not rn:
                continue
            m.set_seq2(rn)
            if m.real_quick_ratio() < floor or m.quick_ratio() < floor:
                continue
            r = m.ratio()
            if r >= floor:
                out.append({"ratio": round(r, 3), "source": ls, "target": rs})
    out.sort(key=lambda p: -p["ratio"])
    return out


def main() -> int:
    corpus = Corpus.load()
    print("SEGMENTER: comparable_segments, the one both arms share")
    print(f"  fingerprint: {corpus.segmentation_fingerprint()}")
    print(f"  funnel: {json.dumps(exclusion_report(corpus))}")
    print()
    rows = [
        json.loads(line)
        for line in (EVAL / "test_query_verification.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    multi = [r for r in rows if r.get("multi_hop")]
    print(f"committed verification rows: {len(rows)}; with a multi_hop block: {len(multi)}")
    print()
    head = f"{'row':<8} {'edge':<26} {'committed':>10} {'shipped':>9} {'period-only':>12}  verdict"
    print(head)
    print("-" * len(head))

    reproduced, diverged = 0, []
    for r in multi:
        mh = r["multi_hop"]
        su, tu = mh["source_unit"], mh["target_unit"]
        c = mh["duplication_scan"]
        ct, cn = c.get("top_ratio"), len(c.get("pairs_at_or_above_floor", []))

        ls = corpus.unit_segments[su]
        rs = corpus.unit_segments[tu]
        shipped = cross_pairs(ls, rs)
        po = cross_pairs(
            [s.strip() for s in PERIOD_ONLY.split(corpus.unit_text[su]) if s.strip()],
            [s.strip() for s in PERIOD_ONLY.split(corpus.unit_text[tu]) if s.strip()],
        )
        st = shipped[0]["ratio"] if shipped else None
        pt = po[0]["ratio"] if po else None

        same = (ct is None and st is None) or (
            ct is not None and st is not None and abs(ct - st) < 0.0005
        )
        if same and cn == len(shipped):
            reproduced += 1
            verdict = "reproduces"
        else:
            verdict = f"DIVERGES ({cn} committed, {len(shipped)} shipped)"
            diverged.append((r["id"], su, tu, c, shipped))
        edge = f"{su.split(':')[1]} -> {tu.split(':')[1]}"
        print(f"{r['id']:<8} {edge:<26} {str(ct):>10} {str(st):>9} {str(pt):>12}  {verdict}")

    print()
    print(f"rows reproducing committed top_ratio AND pair count: {reproduced} of {len(multi)}")
    print(f"rows diverging: {len(diverged)}")
    for rid, su, tu, c, shipped in diverged:
        print("=" * 78)
        print(f"{rid}: {su} -> {tu}")
        print(f"  committed: top_ratio {c.get('top_ratio')}, {len(c.get('pairs_at_or_above_floor', []))} pair(s)")
        for p in c.get("pairs_at_or_above_floor", []):
            print(f"    committed {p['ratio']}: {p['source_sentence'][:90]}")
        for p in shipped:
            print(f"    shipped   {p['ratio']}: {p['source'][:90]}")
            print(f"                     vs {p['target'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
