"""PDF text extraction, pinned and auditable.

Extractor of record is pypdfium2, wrapping Google's PDFium. Chosen on evidence,
not habit, after comparing independent implementations against the actual files.

Why not the obvious alternatives:

  PyMuPDF is AGPL-3.0 or commercial, which is a poor fit for an Apache-2.0
  public repository, so it was rejected before testing.

  pdfminer.six, via pdfplumber, is materially WRONG on NIST AI 100-1, a
  pdfTeX-produced document. It emits some text reversed, "...AxidneppAeeS" for
  "See Appendix A...", and drops inter-word spaces across the document, giving
  548 run-together tokens of 25 characters or more against 4 from PDFium. It
  reported success on all 48 pages with no empty pages and no error, which is
  precisely the silent failure this project cannot tolerate. Poppler's pdftotext
  was used as an independent third engine to break the tie and agrees with
  PDFium. See `tests/test_pdf_extract.py` for the pinned regression.

The extractor version is pinned in the manifest for the same reason the
tokenizer is: PDF extractors change their output across releases, and chunk IDs
freeze at ingestion and are cited by pre-registered gold passages.

Extracted text is committed, so extraction is auditable without re-running and
a version bump shows up as a diff rather than a silent change.
"""

from __future__ import annotations

import hashlib
import re

import pypdfium2
import pypdfium2.version as pdfium_version

# PDFium encodes the discretionary hyphen at a line break as U+FFFE, a Unicode
# noncharacter that can never occur in valid text. Every occurrence across the
# three NIST documents has a letter on both sides, none is preceded by an ASCII
# hyphen, and none precedes a newline, so deleting it rejoins the word. This is
# a mechanical deletion of a noncharacter, not a repair from knowledge.
SOFT_HYPHEN_BREAK = "￾"

PAGE_SEPARATOR = "\n\f\n"


def extractor_fingerprint() -> dict[str, str]:
    """Identity recorded in the manifest and pinned like the tokenizer."""
    return {
        "engine": "pypdfium2",
        "pypdfium2_version": str(pypdfium2_version()),
        "pdfium_version": str(pdfium_version.PDFIUM_INFO),
        "soft_hyphen_rule": "delete U+FFFE, which rejoins a word split at a line break",
    }


def pypdfium2_version() -> str:
    return str(pdfium_version.PYPDFIUM_INFO)


def extract_pages(path) -> list[str]:
    """Per-page text exactly as PDFium reports it, with no cleanup applied."""
    document = pypdfium2.PdfDocument(str(path))
    try:
        return [
            document[index].get_textpage().get_text_range() or ""
            for index in range(len(document))
        ]
    finally:
        document.close()


def extract_raw_text(path) -> str:
    """Full document text, pages joined by a form feed, no cleanup applied.

    This is the artifact the partition proof is computed over and the artifact
    committed for audit. Nothing is removed here.
    """
    return PAGE_SEPARATOR.join(extract_pages(path))


def join_soft_hyphens(text: str) -> str:
    """Delete the U+FFFE line-break hyphen marker, rejoining split words."""
    return text.replace(SOFT_HYPHEN_BREAK, "")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_soft_hyphen_breaks(text: str) -> int:
    return text.count(SOFT_HYPHEN_BREAK)


def find_unjoinable_breaks(text: str) -> list[str]:
    """Occurrences where the join rule's precondition does not hold.

    The rule is only safe where a letter sits on both sides. Anything else is
    reported rather than silently joined.
    """
    bad: list[str] = []
    for match in re.finditer(re.escape(SOFT_HYPHEN_BREAK), text):
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if not (before.isalpha() and after.isalpha()):
            bad.append(text[max(0, match.start() - 20) : match.end() + 20])
    return bad
