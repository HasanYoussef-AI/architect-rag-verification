"""Tests for the U+FFFE hyphen resolver, its wordlist tier, and the decision log.

The resolver's fourth evidence tier decides the residue that has no corpus
attestation, using the vendored wordlist. Its refinement, that a delete requires
the joined form to be a word AND at least one fragment to not be a word, is the
part that separates a syllable break ("cooper" + "ation") from a genuine compound
("round" + "trip"), so it is pinned directly. The whole-corpus decision log is
pinned by byte-identity, the same discipline as the ingestion reruns.
"""

from __future__ import annotations

import json

from src.ingest.hyphenation import (
    DELETE,
    HYPHEN,
    RULE_WORDLIST_HYPHEN,
    RULE_WORDLIST_JOINED,
    TIE_BREAK_WORDLIST_BOTH,
    _resolve_by_wordlist,
    resolve,
)
from src.ingest.hyphenation_report import (
    OUTPUT_DIR,
    all_decisions,
    build_jsonl,
    build_summary,
)
from src.ingest.pdf_extract import SOFT_HYPHEN_BREAK

# The eight AI 100-1 syllable breaks: each has at least one non-word fragment.
SYLLABLE_BREAKS = [
    ("Nonethe", "less"),
    ("cooper", "ation"),
    ("devel", "opments"),
    ("em", "phasize"),
    ("formal", "ized"),
    ("illus", "trated"),
    ("man", "agers"),
    ("quanti", "ties"),
]

# The two ambiguous compounds: joined form is a word and BOTH fragments are words.
AMBIGUOUS_COMPOUNDS = [("round", "trip"), ("non", "inclusive")]


def test_wordlist_keeps_when_joined_form_is_not_a_word():
    """cost + effective -> costeffective is not a word -> real hyphen, keep."""
    rule, outcome = _resolve_by_wordlist("cost", "effective")
    assert (rule, outcome) == (RULE_WORDLIST_HYPHEN, HYPHEN)


def test_wordlist_deletes_a_syllable_break():
    """cooper + ation -> cooperation is a word and 'ation' is not -> delete."""
    rule, outcome = _resolve_by_wordlist("cooper", "ation")
    assert (rule, outcome) == (RULE_WORDLIST_JOINED, DELETE)


def test_wordlist_keeps_an_ambiguous_compound_by_tie_break():
    """round + trip -> both are words -> keep, labelled as a tie-break."""
    rule, outcome = _resolve_by_wordlist("round", "trip")
    assert (rule, outcome) == (TIE_BREAK_WORDLIST_BOTH, HYPHEN)


def test_documented_failure_mode_the_rapist_is_wrongly_kept():
    """A syllable break whose fragments are both words is wrongly kept, fails safe."""
    rule, outcome = _resolve_by_wordlist("the", "rapist")
    assert (rule, outcome) == (TIE_BREAK_WORDLIST_BOTH, HYPHEN)


def test_all_eight_syllable_breaks_delete():
    for left, right in SYLLABLE_BREAKS:
        rule, outcome = _resolve_by_wordlist(left, right)
        assert outcome == DELETE, f"{left}-{right} should delete"
        assert rule == RULE_WORDLIST_JOINED


def test_both_ambiguous_compounds_keep_by_tie_break():
    for left, right in AMBIGUOUS_COMPOUNDS:
        rule, outcome = _resolve_by_wordlist(left, right)
        assert (rule, outcome) == (TIE_BREAK_WORDLIST_BOTH, HYPHEN), f"{left}-{right}"


def test_resolve_joins_a_syllable_break_end_to_end():
    """A neither-attested residue word is joined through the wordlist tier."""
    out, decisions = resolve(f"encouraged to test tools in cooper{SOFT_HYPHEN_BREAK}ation with", "t")
    assert "cooperation" in out
    assert decisions[0].rule == RULE_WORDLIST_JOINED
    assert decisions[0].outcome == DELETE


def test_resolve_keeps_an_ambiguous_compound_end_to_end():
    out, decisions = resolve(f"as much carbon as 300 round{SOFT_HYPHEN_BREAK}trip flights", "t")
    assert "round-trip" in out
    assert decisions[0].rule == TIE_BREAK_WORDLIST_BOTH
    assert decisions[0].outcome == HYPHEN


def test_decision_log_is_byte_identical_to_the_committed_artifact():
    """Re-running the resolver across the corpus must reproduce the committed log."""
    committed = (OUTPUT_DIR / "decision_log.jsonl").read_bytes()
    assert build_jsonl(all_decisions()) == committed


def test_decision_log_summary_is_pinned():
    """The tier breakdown and wordlist split are pinned across all 337 occurrences."""
    summary = build_summary(all_decisions())
    assert summary["total_occurrences"] == 337
    assert summary["by_tier"] == {
        "1_non_letter_neighbour": 2,
        "2_corpus_attestation_one_direction": 273,
        "3_both_attested_group_A": 7,
        "4_wordlist": 55,
    }
    assert "5_unresolved" not in summary["by_tier"]
    assert summary["wordlist_tier"] == {
        "total": 55,
        "delete_syllable_break": 8,
        "keep_joined_not_a_word": 45,
        "keep_ambiguous_compound_tie_break": 2,
    }
    on_disk = json.loads((OUTPUT_DIR / "decision_log.summary.json").read_text(encoding="utf-8"))
    assert on_disk == summary
