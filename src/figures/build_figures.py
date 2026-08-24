"""Write the seven results figures to docs/figures/.

Run:  python -m src.figures.build_figures [--check]

--check writes nothing and reports whether the committed files match what this module produces,
which is what a reviewer runs to verify a figure without touching the tree.

Reproducibility level 1. Inputs are the three committed result artifacts; no model, no key, no
network and no clock. The writer pins LF for the reason src/score/run_retrieval_eval.py records.
"""

from __future__ import annotations

import argparse
import hashlib
import sys

from src.figures.figures import build_all
from src.ingest.corpus_integrity import REPO_ROOT

FIGURES_DIR = REPO_ROOT / "docs" / "figures"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="compare the committed figures against a fresh build and write nothing",
    )
    args = parser.parse_args(argv)

    built = build_all()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if args.check:
        bad = 0
        for name, text in sorted(built.items()):
            path = FIGURES_DIR / name
            if not path.exists():
                print(f"MISSING  {name}", file=sys.stderr)
                bad += 1
                continue
            on_disk = path.read_bytes()
            fresh = text.encode("utf-8")
            mark = "OK " if on_disk == fresh else "DIFFERS"
            if on_disk != fresh:
                bad += 1
            print(f"{mark:8} {name}  {hashlib.sha256(on_disk).hexdigest()[:16]}")
        print(f"\n{len(built) - bad} of {len(built)} match")
        return 1 if bad else 0

    for name, text in sorted(built.items()):
        path = FIGURES_DIR / name
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(REPO_ROOT)}  "
              f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}  {len(text)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
