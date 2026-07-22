"""Corpus integrity verification.

Recomputes the SHA-256 of every file under `corpus/*/raw/` and checks it against
the provenance table in `corpus/SOURCES.md`. Ingestion calls this first and
refuses to proceed on any failure, so a corrupted or swapped corpus cannot be
ingested silently.

The EUR-Lex HTML gets an extra check. EUR-Lex injects a per-request analytics
script, so the raw SHA-256 of a fresh download differs from the committed one
even when the legal text is identical. `SOURCES.md` therefore also records a
stable content hash computed after stripping that script, and this module
verifies both: the raw hash pins the committed bytes, the stable hash pins the
text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_MD = REPO_ROOT / "corpus" / "SOURCES.md"
CORPUS_DIR = REPO_ROOT / "corpus"

# The analytics element EUR-Lex injects per request. Documented in SOURCES.md
# under "Reproducing the HTML checksum".
RUXIT_SCRIPT_RE = re.compile(r"<script[^>]*ruxitagentjs.*?</script>", re.DOTALL)

# Table rows in SOURCES.md pair a backticked path with a backticked hex digest.
_ROW_RE = re.compile(r"\|\s*`([^`]+)`\s*\|.*?`([0-9a-f]{64})`", re.MULTILINE)
_STABLE_RE = re.compile(r"stable content SHA-256:\s*([0-9a-f]{64})")

# SOURCES.md also records vendored third-party files, which are not corpus and
# do not live under corpus/*/raw/. Only rows naming a corpus raw path are
# checksum rows for this verifier.
_CORPUS_PATH_RE = re.compile(r"^[A-Za-z0-9_.-]+/raw/[^/]+$")


class IntegrityError(RuntimeError):
    """Raised when the corpus on disk does not match the recorded provenance."""


@dataclass(frozen=True)
class FileCheck:
    path: str
    expected: str
    actual: str
    kind: str  # "raw" or "stable-content"

    @property
    def ok(self) -> bool:
        return self.expected == self.actual


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_content_sha256(path: Path) -> str:
    """SHA-256 after removing the injected EUR-Lex analytics element.

    The rule is stated in `corpus/SOURCES.md` so a reviewer can reproduce it:
    decode as UTF-8, delete every match of the analytics script element with
    dot-matches-newline, re-encode as UTF-8, hash.
    """
    text = path.read_bytes().decode("utf-8", errors="surrogateescape")
    stripped = RUXIT_SCRIPT_RE.sub("", text)
    return hashlib.sha256(stripped.encode("utf-8", errors="surrogateescape")).hexdigest()


def parse_sources(sources_md: Path = SOURCES_MD) -> tuple[dict[str, str], str | None]:
    """Return (relative corpus path -> expected raw sha256, stable content sha256)."""
    text = sources_md.read_text(encoding="utf-8")
    expected = {
        path: digest
        for path, digest in _ROW_RE.findall(text)
        if _CORPUS_PATH_RE.match(path)
    }
    if not expected:
        raise IntegrityError(f"no corpus checksum rows found in {sources_md}")
    stable_match = _STABLE_RE.search(text)
    return expected, (stable_match.group(1) if stable_match else None)


def discover_raw_files(corpus_dir: Path = CORPUS_DIR) -> list[Path]:
    """Every file under corpus/*/raw/, sorted for determinism."""
    return sorted(p for p in corpus_dir.glob("*/raw/*") if p.is_file())


def verify_corpus(
    corpus_dir: Path = CORPUS_DIR, sources_md: Path = SOURCES_MD
) -> list[FileCheck]:
    """Check every raw corpus file against SOURCES.md.

    Raises IntegrityError on any mismatch, any file present on disk but absent
    from SOURCES.md, or any file recorded in SOURCES.md but missing on disk.
    """
    expected, stable_expected = parse_sources(sources_md)
    found = discover_raw_files(corpus_dir)
    checks: list[FileCheck] = []
    problems: list[str] = []

    found_rel = {str(p.relative_to(corpus_dir)) for p in found}
    for recorded in sorted(expected):
        if recorded not in found_rel:
            problems.append(f"recorded in SOURCES.md but missing on disk: {recorded}")

    for path in found:
        rel = str(path.relative_to(corpus_dir))
        if rel not in expected:
            problems.append(f"present on disk but not recorded in SOURCES.md: {rel}")
            continue
        check = FileCheck(rel, expected[rel], sha256_file(path), "raw")
        checks.append(check)
        if not check.ok:
            problems.append(
                f"raw checksum mismatch: {rel}\n"
                f"    expected {check.expected}\n"
                f"    actual   {check.actual}"
            )
        if path.suffix == ".html" and stable_expected is not None:
            stable = FileCheck(rel, stable_expected, stable_content_sha256(path), "stable-content")
            checks.append(stable)
            if not stable.ok:
                problems.append(
                    f"stable content checksum mismatch: {rel}\n"
                    f"    expected {stable.expected}\n"
                    f"    actual   {stable.actual}"
                )

    if problems:
        raise IntegrityError(
            "corpus integrity check failed, refusing to ingest:\n  " + "\n  ".join(problems)
        )
    return checks


def main() -> int:
    try:
        checks = verify_corpus()
    except IntegrityError as exc:
        print(exc)
        return 1
    for check in checks:
        print(f"OK  {check.kind:<15} {check.path}")
    print(f"\n{len(checks)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
