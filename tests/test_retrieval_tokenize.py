"""Tokenisation: identifiers kept whole, index-side-only expansion, primary-token dl.

The four direction checks confirm expansion is index-side only and that document
length counts primary tokens, so expansion parts add postings without being
charged against length. No stopword removal, no stemming, both explicit.
"""

from __future__ import annotations

from src.retrieve.tokenize import (
    document_length,
    primary_tokens,
    tokenize_document,
    tokenize_query,
)


def test_identifiers_are_kept_whole():
    assert primary_tokens("GOVERN 1.1") == ["govern", "1.1"]
    assert primary_tokens("GV-1.1-001") == ["gv-1.1-001"]
    assert primary_tokens("art_6") == ["art_6"]
    assert primary_tokens("third-party") == ["third-party"]


def test_query_side_has_no_expansion():
    assert tokenize_query("third-party") == ["third-party"]


def test_index_side_expands_but_keeps_the_whole_token():
    doc = tokenize_document("third-party")
    assert doc[0] == "third-party"
    assert "third" in doc and "party" in doc


def test_dotted_numeric_groups_are_not_split():
    assert tokenize_document("gv-1.1-001") == ["gv-1.1-001", "gv", "1.1", "001"]


def test_document_length_counts_primary_tokens_only():
    # two primary tokens; expansion parts of "third-party" are not charged
    assert document_length("third-party foo") == 2
    assert len(tokenize_document("third-party foo")) == 4


def test_query_reaches_document_through_expansion():
    doc = set(tokenize_document("the third-party auditor"))
    assert set(tokenize_query("third party")) <= doc  # split query reaches it
    assert set(tokenize_query("third-party")) <= doc  # whole token reaches it


def test_normalisation_shared_by_both_sides():
    # curly apostrophe and en dash fold to ASCII, so the two spellings tokenise alike
    assert tokenize_query("system’s") == tokenize_query("system's")
    assert tokenize_document("pre–deployment") == tokenize_document("pre-deployment")
