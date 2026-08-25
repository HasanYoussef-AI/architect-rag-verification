"""Assert that the suite produced exactly the result docs/REPRODUCE.md documents.

WHY THIS IS NOT A HARDCODED TRIPLE. The expected figures are read out of `docs/REPRODUCE.md`
rather than written here, so the workflow and the walkthrough check each other. A tree that gains
a test and a walkthrough that is not updated with it disagree, and the disagreement is what fails.
Hardcoding the numbers here would let the walkthrough go stale silently, which is the exact defect
this repository has already corrected twice in that file.

WHAT IT COMPARES. The `a fresh clone` row of the environment table against a real run in an
environment built the way that table's own row says: the default `uv sync`, no `embed` group, no
segment embedding cache. That is why continuous integration is worth having here at all. It does
not run some convenient subset; it runs the documented stranger's path.

EVERY PARSE IS ASSERTED BEFORE IT IS USED. A regex that matches nothing yields no numbers, and a
comparison against no numbers is the kind of check that reports a pass because it found nothing to
judge. Each parse below raises with the text it failed on rather than returning a default.

Usage:  python .github/assert_documented_result.py <collect-output> <run-output>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPRODUCE = Path("docs/REPRODUCE.md")

# The row of the environment table that describes a default `uv sync` clone, and the three counts
# in it. The leading cell is matched on "fresh clone" so that reordering the table does not silently
# select a different environment.
FRESH_ROW = re.compile(
    r"^\|[^|]*fresh clone[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", re.M
)
COLLECTED = re.compile(r"(\d+)\s+tests?\s+collected")
PASSED = re.compile(r"(\d+)\s+passed")
SKIPPED = re.compile(r"(\d+)\s+skipped")


def _one(pattern: re.Pattern[str], text: str, what: str, source: str) -> int:
    match = pattern.search(text)
    if match is None:
        raise SystemExit(
            f"could not read {what} from {source}. The check is not able to report a pass "
            f"without it, so this is a failure rather than a default.\n"
            f"--- last 40 lines of {source} ---\n" + "\n".join(text.splitlines()[-40:])
        )
    return int(match.group(1))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    collect_text = Path(argv[0]).read_text(encoding="utf-8", errors="replace")
    run_text = Path(argv[1]).read_text(encoding="utf-8", errors="replace")

    if not REPRODUCE.exists():
        raise SystemExit(f"{REPRODUCE} is missing, so there is nothing to check the run against")
    row = FRESH_ROW.search(REPRODUCE.read_text(encoding="utf-8"))
    if row is None:
        raise SystemExit(
            f"no fresh-clone row found in {REPRODUCE}. The documented figures are what this check "
            "compares against, so their absence is a failure and not a skip."
        )
    want = {
        "collected": int(row.group(1)),
        "passed": int(row.group(2)),
        "skipped": int(row.group(3)),
    }

    got = {
        "collected": _one(COLLECTED, collect_text, "the collected count", argv[0]),
        "passed": _one(PASSED, run_text, "the passed count", argv[1]),
        "skipped": _one(SKIPPED, run_text, "the skipped count", argv[1]),
    }

    width = max(len(k) for k in want)
    print(f"{'':<{width}}  {'documented':>10}  {'measured':>9}")
    for key in ("collected", "passed", "skipped"):
        mark = "ok" if want[key] == got[key] else "DIFFERS"
        print(f"{key:<{width}}  {want[key]:>10}  {got[key]:>9}  {mark}")

    bad = [k for k in want if want[k] != got[k]]
    if bad:
        raise SystemExit(
            "\nThe suite result and docs/REPRODUCE.md disagree on: "
            + ", ".join(sorted(bad))
            + ".\nOne of the two is wrong. If the tree gained or lost tests deliberately, the "
            "walkthrough's environment table moves in the same commit; if it did not, this is a "
            "real regression."
        )
    print("\nThe run matches the documented fresh-clone result on all three figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
