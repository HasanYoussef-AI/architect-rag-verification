"""Tests for the corpus integrity verifier.

The verifier is what makes it impossible to ingest a corrupted or swapped
corpus silently, so its failure path matters more than its success path.
"""

from __future__ import annotations

import hashlib

import pytest

from src.ingest.corpus_integrity import (
    IntegrityError,
    parse_sources,
    sha256_file,
    stable_content_sha256,
    verify_all,
    verify_corpus,
    verify_vendor,
)


def _make_corpus(tmp_path, html_body: str = "<html>legal text</html>"):
    """Build a miniature corpus plus a SOURCES.md that matches it."""
    corpus = tmp_path / "corpus"
    raw = corpus / "doc_a" / "raw"
    raw.mkdir(parents=True)
    pdf = raw / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7 pretend")
    html = raw / "doc.html"
    html.write_text(html_body, encoding="utf-8")

    sources = corpus / "SOURCES.md"
    sources.write_text(
        "| File | SHA-256 |\n| --- | --- |\n"
        f"| `doc_a/raw/doc.pdf` | `{sha256_file(pdf)}` |\n"
        f"| `doc_a/raw/doc.html` | `{sha256_file(html)}` |\n\n"
        f"stable content SHA-256: {stable_content_sha256(html)}\n",
        encoding="utf-8",
    )
    return corpus, sources, pdf, html


def test_verify_passes_on_an_intact_corpus(tmp_path):
    corpus, sources, _, _ = _make_corpus(tmp_path)
    checks = verify_corpus(corpus, sources)
    assert all(check.ok for check in checks)
    assert {c.kind for c in checks} == {"raw", "stable-content"}


def test_verify_catches_a_tampered_file(tmp_path):
    """The core guarantee: one flipped byte must stop ingestion."""
    corpus, sources, pdf, _ = _make_corpus(tmp_path)
    pdf.write_bytes(b"%PDF-1.7 tampered")
    with pytest.raises(IntegrityError) as excinfo:
        verify_corpus(corpus, sources)
    assert "raw checksum mismatch" in str(excinfo.value)
    assert "doc_a/raw/doc.pdf" in str(excinfo.value)


def test_verify_catches_a_swapped_file_of_identical_length(tmp_path):
    """A same-size substitution must not slip through a length-only check."""
    corpus, sources, pdf, _ = _make_corpus(tmp_path)
    original = pdf.read_bytes()
    pdf.write_bytes(b"X" * len(original))
    with pytest.raises(IntegrityError):
        verify_corpus(corpus, sources)


def test_verify_catches_an_undeclared_extra_file(tmp_path):
    corpus, sources, _, _ = _make_corpus(tmp_path)
    (corpus / "doc_a" / "raw" / "sneaked_in.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(IntegrityError) as excinfo:
        verify_corpus(corpus, sources)
    assert "not recorded in SOURCES.md" in str(excinfo.value)


def test_verify_catches_a_missing_file(tmp_path):
    corpus, sources, pdf, _ = _make_corpus(tmp_path)
    pdf.unlink()
    with pytest.raises(IntegrityError) as excinfo:
        verify_corpus(corpus, sources)
    assert "missing on disk" in str(excinfo.value)


def test_stable_content_hash_ignores_the_injected_analytics_script(tmp_path):
    """EUR-Lex varies analytics IDs per request; the legal text must still match."""
    body = '<html><head><script src="/x/ruxitagentjs_A" data-dtconfig="rid=RID_1"></script></head><body>text</body></html>'
    other = '<html><head><script src="/x/ruxitagentjs_A" data-dtconfig="rid=RID_9999"></script></head><body>text</body></html>'
    first = tmp_path / "a.html"
    second = tmp_path / "b.html"
    first.write_text(body, encoding="utf-8")
    second.write_text(other, encoding="utf-8")

    assert sha256_file(first) != sha256_file(second)
    assert stable_content_sha256(first) == stable_content_sha256(second)


def test_stable_content_hash_still_detects_a_change_to_the_legal_text(tmp_path):
    body = '<html><head><script src="/x/ruxitagentjs_A" data-dtconfig="rid=RID_1"></script></head><body>text</body></html>'
    edited = body.replace("text", "edited text")
    first, second = tmp_path / "a.html", tmp_path / "b.html"
    first.write_text(body, encoding="utf-8")
    second.write_text(edited, encoding="utf-8")
    assert stable_content_sha256(first) != stable_content_sha256(second)


def test_parse_sources_rejects_a_file_with_no_checksums(tmp_path):
    empty = tmp_path / "SOURCES.md"
    empty.write_text("# no table here\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        parse_sources(empty)


def test_the_real_corpus_verifies():
    """The committed corpus must match its recorded provenance."""
    checks = verify_corpus()
    assert checks
    assert all(check.ok for check in checks)


def test_stable_hash_recipe_matches_the_value_recorded_in_sources_md():
    """The documented strip rule must reproduce the published number."""
    expected, stable = parse_sources()
    assert stable is not None
    from src.ingest.corpus_integrity import CORPUS_DIR

    html = CORPUS_DIR / "eu_ai_act" / "raw" / "CELEX_32024R1689_EN_OJ.html"
    assert stable_content_sha256(html) == stable
    assert hashlib.sha256(html.read_bytes()).hexdigest() == expected[
        "eu_ai_act/raw/CELEX_32024R1689_EN_OJ.html"
    ]


def test_vendored_dependency_rows_are_not_treated_as_corpus_files():
    """SOURCES.md also records vendored third-party files under vendor/.

    Those are not corpus and do not live under corpus/*/raw/, so the verifier
    must ignore their rows rather than demand them on disk.
    """
    expected, _ = parse_sources()
    assert expected
    assert all("/raw/" in path for path in expected)
    assert not any(path.startswith("vendor/") for path in expected)


def test_vendor_verification_passes_on_the_committed_files():
    checks = verify_vendor()
    assert checks
    assert all(check.ok for check in checks)
    assert all(check.kind == "vendor" for check in checks)


def test_vendor_verification_catches_a_swapped_tokenizer(tmp_path, monkeypatch):
    """A swapped tokenizer moves chunk IDs and would void the pre-registration."""
    from src.ingest.corpus_integrity import REPO_ROOT

    vendor = tmp_path / "vendor" / "bge-base-en-v1.5"
    vendor.mkdir(parents=True)
    tokenizer = vendor / "tokenizer.json"
    tokenizer.write_text('{"real": true}', encoding="utf-8")
    sources = tmp_path / "SOURCES.md"
    sources.write_text(
        "| File | SHA-256 |\n| --- | --- |\n"
        f"| `vendor/bge-base-en-v1.5/tokenizer.json` | `{sha256_file(tokenizer)}` |\n",
        encoding="utf-8",
    )
    assert verify_vendor(tmp_path, sources)

    tokenizer.write_text('{"swapped": true}', encoding="utf-8")
    with pytest.raises(IntegrityError) as excinfo:
        verify_vendor(tmp_path, sources)
    assert "vendor checksum mismatch" in str(excinfo.value)
    assert REPO_ROOT.exists()


def test_verify_all_covers_corpus_and_vendor():
    kinds = {check.kind for check in verify_all()}
    assert kinds == {"raw", "stable-content", "vendor"}
