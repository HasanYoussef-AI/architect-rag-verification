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

WHY A ZERO SKIP COUNT IS INFERRED, AND WHY THAT IS NOT AN EXCEPTION TO THE LINE ABOVE. `pytest -q`
omits a category from its summary when the count is zero, so a run with no skips prints
"1065 passed in 227.62s" and the word "skipped" appears nowhere. Searching the whole file for a
skip count therefore found nothing and raised, which meant this check could only ever run in an
environment that happened to have a skip; the walkthrough documents three and only two of them do.

The fix is not to treat a missing phrase as zero. That would make truncated output, a crashed
interpreter and a genuinely clean run indistinguishable, which is one step from a script that reads
missing output as a pass. Instead the summary LINE is located first and asserted to exist, and the
counts are read only from inside it. A category absent from a line that has been positively
identified as a pytest summary means zero, because that is pytest's format. A file with no summary
line at all means nothing was measured, and that still raises. The two cases were previously
indistinguishable and are now separated, which is the same separation this repository already made
between a tampered model and an absent one.

Reading the counts from one identified line rather than from the whole file also tightens the
check: the previous form would have matched the word anywhere in the output, including inside this
repository's own offline-guard report block, which prints after the summary.

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

# A pytest summary line carries at least one outcome count and the wall clock, on one line. Both
# halves are required: "in 4.35s" alone appears in other output, and an outcome word alone appears
# in this repository's guard report.
_OUTCOME = re.compile(r"\b(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)\b")
_WALL_CLOCK = re.compile(r"\bin\s+\d[\d.]*s")


def _one(pattern: re.Pattern[str], text: str, what: str, source: str) -> int:
    match = pattern.search(text)
    if match is None:
        raise SystemExit(
            f"could not read {what} from {source}. The check is not able to report a pass "
            f"without it, so this is a failure rather than a default.\n"
            f"--- last 40 lines of {source} ---\n" + "\n".join(text.splitlines()[-40:])
        )
    return int(match.group(1))


def summary_line(text: str, source: str) -> str:
    """The last pytest summary line in `text`, or a failure. Never a default.

    Locating the line is what licenses reading an absent category as zero further down. If no line
    qualifies, nothing was measured and that is reported rather than absorbed.
    """
    lines = [
        line
        for line in text.splitlines()
        if _OUTCOME.search(line) and _WALL_CLOCK.search(line)
    ]
    if not lines:
        raise SystemExit(
            f"no pytest summary line found in {source}, so no run was measured. A summary line "
            "carries an outcome count and a wall clock together. Its absence is a failure and not "
            "a run with zero of everything.\n"
            f"--- last 40 lines of {source} ---\n" + "\n".join(text.splitlines()[-40:])
        )
    return lines[-1]


def outcome(line: str, category: str) -> int:
    """A category's count within an already-identified summary line, zero when pytest omitted it."""
    for count, name in _OUTCOME.findall(line):
        if name == category:
            return int(count)
    return 0


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

    line = summary_line(run_text, argv[1])
    got = {
        "collected": _one(COLLECTED, collect_text, "the collected count", argv[0]),
        "passed": outcome(line, "passed"),
        "skipped": outcome(line, "skipped"),
    }

    width = max(len(k) for k in want)
    print(f"summary line read: {line.strip()}")
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
