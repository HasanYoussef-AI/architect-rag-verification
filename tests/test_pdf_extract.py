"""Tests for PDF extraction, including why the extractor of record was chosen.

The pdfminer regression below is deliberate. The reason pypdfium2 is the
extractor of record is a measured defect in an alternative, and a reason that
lives only in prose can be quietly reversed by a future refactor. Pinning it in
code means anyone proposing to switch back has to delete a failing test and
explain why.
"""

from __future__ import annotations

import re

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.pdf_extract import (
    SOFT_HYPHEN_BREAK,
    count_soft_hyphen_breaks,
    extract_pages,
    extract_raw_text,
    extractor_fingerprint,
    find_unjoinable_breaks,
    join_soft_hyphens,
)

AI_100_1 = REPO_ROOT / "corpus/nist_ai_rmf/raw/NIST.AI.100-1.pdf"


@pytest.fixture(scope="module")
def pages():
    return extract_pages(AI_100_1)


def test_page_count_matches_the_document(pages):
    assert len(pages) == 48


def test_no_page_extracts_empty(pages):
    """An empty page is the signature of content lost to a table or figure."""
    assert [i for i, p in enumerate(pages, 1) if not p.strip()] == []


def test_extractor_version_is_pinned():
    """Extractors change output across releases and chunk IDs freeze at ingestion."""
    fingerprint = extractor_fingerprint()
    assert fingerprint["engine"] == "pypdfium2"
    assert re.match(r"^\d+\.\d+", fingerprint["pypdfium2_version"])
    assert re.match(r"^\d+\.", fingerprint["pdfium_version"])


# --------------------------------------------------------------------------
# The U+FFFE join rule
# --------------------------------------------------------------------------

def test_soft_hyphen_break_marker_is_present_in_the_document(pages):
    raw = "\n".join(pages)
    assert count_soft_hyphen_breaks(raw) > 0


def test_join_rule_precondition_holds_everywhere(pages):
    """The rule is only safe with a letter on both sides. Anything else must fail loudly."""
    assert find_unjoinable_breaks("\n".join(pages)) == []


def test_join_rule_rejoins_a_split_word():
    assert join_soft_hyphens(f"inte{SOFT_HYPHEN_BREAK}grated") == "integrated"
    assert join_soft_hyphens(f"or{SOFT_HYPHEN_BREAK}ganizational") == "organizational"


def test_join_rule_removes_every_marker(pages):
    joined = join_soft_hyphens("\n".join(pages))
    assert SOFT_HYPHEN_BREAK not in joined


def test_find_unjoinable_breaks_flags_a_bad_case():
    assert find_unjoinable_breaks(f"word {SOFT_HYPHEN_BREAK} next")


def test_extraction_is_deterministic():
    assert extract_raw_text(AI_100_1) == extract_raw_text(AI_100_1)


# --------------------------------------------------------------------------
# Regression: why pdfminer.six is not the extractor of record
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pdfminer_text():
    pdfplumber = pytest.importorskip("pdfplumber")
    with pdfplumber.open(AI_100_1) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def test_pdfminer_drops_inter_word_spaces_on_this_document(pdfminer_text, pages):
    """pdfminer.six loses spaces on this pdfTeX document; PDFium does not.

    Measured as run-together tokens of 25 characters or more.
    """
    def run_together(texts):
        return [w for t in texts for w in t.split() if len(w) >= 25]

    assert len(run_together(pdfminer_text)) > 300
    assert len(run_together(pages)) < 20


def test_pdfminer_emits_reversed_text_on_page_16(pdfminer_text, pages):
    """pdfminer.six emits page 16 backwards. PDFium reads it correctly."""
    assert "AxidneppAeeS" in pdfminer_text[15].replace(" ", "")
    assert "See Appendix A for detailed descriptions" in re.sub(r"\s+", " ", pages[15])


def test_pdfium_output_is_the_readable_one(pages):
    """A positive statement of what correct extraction looks like here."""
    page_two = re.sub(r"\s+", " ", pages[1])
    assert "This publication is available free of charge from" in page_two
    assert "Thispublicationisavailablefreeofchargefrom" not in page_two.replace(" ", "x")
