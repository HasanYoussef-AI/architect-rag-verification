"""Every `python -m` invocation a module's own text names must resolve to a runnable module.

THIS PINS A DEFECT CLASS, NOT ONE FILE. src/generate/manifest.py once recorded
"produced_by": "python -m src.generate.manifest" and gave the same command in its docstring while
carrying no __main__ block at all; running it exited 0, wrote nothing, and created no file. That
was fixed forward at 50bd34a by giving the module the entry point its own text claimed.
src/generate/batch.py carried the same defect in its docstring, naming
`python -m src.generate.batch submit ...` when no such entry point existed and the three committed
development batches were in fact submitted by calling `submit` and `collect` directly.

A file that names a command which does nothing is worse than a file that names no command: the
reader has no way to tell the difference without running it, and running it succeeds. So the rule
is mechanical rather than editorial, and it covers the whole tree so the defect cannot reappear in
a module nobody thought to check.
"""

from __future__ import annotations

import re

from src.ingest.corpus_integrity import REPO_ROOT

# A `python -m` invocation and the dotted module it names. The trailing character class stops the
# match at a sentence-ending period, so "run python -m src.foo.bar." names src.foo.bar and not
# src.foo.bar. with a trailing dot, which is not a module and never was.
INVOCATION = re.compile(r"python -m ([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)")

SOURCE_ROOT = REPO_ROOT / "src"


def _named_invocations() -> list[tuple[str, str]]:
    """Every (file, module) pair any file under src/ names as a `python -m` target."""
    out: list[tuple[str, str]] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        for match in INVOCATION.finditer(text):
            out.append((str(path.relative_to(REPO_ROOT)), match.group(1)))
    return out


def _has_entry_point(module: str) -> bool:
    target = REPO_ROOT / (module.replace(".", "/") + ".py")
    if not target.exists():
        return False
    return "__main__" in target.read_text(encoding="utf-8")


def test_every_named_python_m_invocation_resolves_to_a_module_with_an_entry_point():
    named = _named_invocations()
    assert named, "the scan found no invocations at all, so it proves nothing"
    broken = [(f, m) for f, m in named if not _has_entry_point(m)]
    assert broken == [], (
        "these files name a `python -m` command that does nothing, which is the defect class "
        f"fixed forward at 50bd34a: {broken}"
    )


def test_the_scan_finds_the_invocations_that_are_there():
    """The positive control. An empty scan would make the test above pass on nothing."""
    named = _named_invocations()
    modules = {m for _, m in named}
    assert "src.generate.manifest" in modules, "the known-good entry point was not found"
    assert len(named) >= 8, f"the scan found only {len(named)} invocations, which is too few"


def test_the_detector_is_capable_of_failing():
    """V20. The predicate is shown red against a module that certainly has no entry point."""
    assert not _has_entry_point("src.generate.assemble"), (
        "src/generate/assemble.py has gained a __main__; pick another module for this control"
    )
    assert not _has_entry_point("src.definitely.not.a.module")
    assert _has_entry_point("src.generate.manifest")


def test_the_trailing_period_is_not_taken_as_part_of_the_module_name():
    """A sentence ending in an invocation is prose, not a module named `foo.bar.`."""
    found = INVOCATION.findall("Build it with python -m src.goldset.build_segment_embeddings.")
    assert found == ["src.goldset.build_segment_embeddings"]
