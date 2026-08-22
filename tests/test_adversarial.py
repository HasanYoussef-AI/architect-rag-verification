"""Abstention, the marker_variant class, and the adversarial per-row verdict.

Sections 3, 7.2, 7.3 and 7.4 of eval/generation_predictions.md define everything asserted here.
The two constructible defects of section 7.4 are pinned, and each is shown red against a detector
lacking the rule it exercises rather than only shown green against the real one.
"""

from __future__ import annotations

import json
import re

from src.complete.references import R_ACT, R_ANX, R_ART, R_SUB
from src.generate.prompts import ABSTAINED, ANSWERED, MARKER, MARKER_VARIANT
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.adversarial import (
    CORPUS_PHRASE_LITERALS,
    FAILURE,
    INSTRUMENT_NAMES,
    NOT_FAILURE,
    COMMITTED_REFERENCE_PATTERNS,
    contains_reference,
    corpus_phrases,
    document_titles,
    is_existence_denial,
    marker_only_verdict,
    response_class,
    row_verdict,
)

MARKERLESS_DENIAL = "There is no Article 114 in the EU AI Act."
MARKER_PLUS_CONTENT = MARKER + " Article 114 requires transparency for general-purpose systems."


# --------------------------------------------------------------------------------------
# Section 7.4, the two constructible defects, each shown red against a defective detector
# --------------------------------------------------------------------------------------


def test_a_markerless_existence_denial_is_not_a_failure():
    assert row_verdict(MARKERLESS_DENIAL) == NOT_FAILURE


def test_the_markerless_denial_case_is_shown_red_against_a_marker_only_detector():
    """The defect the pre-declaration's own sentence constructs, in the first direction."""
    assert marker_only_verdict(MARKERLESS_DENIAL) == FAILURE
    assert marker_only_verdict(MARKERLESS_DENIAL) != row_verdict(MARKERLESS_DENIAL)


def test_a_marker_plus_substantive_content_answer_is_a_failure():
    assert row_verdict(MARKER_PLUS_CONTENT) == FAILURE


def test_the_marker_plus_content_case_is_shown_red_against_a_marker_only_detector():
    """The same defect in the second direction. A containment rule would call this a clean pass."""
    assert marker_only_verdict(MARKER_PLUS_CONTENT) == NOT_FAILURE
    assert marker_only_verdict(MARKER_PLUS_CONTENT) != row_verdict(MARKER_PLUS_CONTENT)


def test_the_marker_alone_is_not_a_failure_and_carries_no_units():
    assert row_verdict(MARKER) == NOT_FAILURE


def test_substantive_content_alone_is_a_failure():
    assert row_verdict("Article 114 requires transparency.") == FAILURE


def test_a_denial_followed_by_substantive_content_is_a_failure():
    """The verdict is over every unit: one non-denial unit is enough."""
    answer = "There is no Article 114. However, Article 113 requires transparency."
    assert row_verdict(answer) == FAILURE


# --------------------------------------------------------------------------------------
# Section 7.3, the closed reference set
# --------------------------------------------------------------------------------------


def test_every_member_of_the_closed_reference_set_fires():
    """Enumerated one per surface, so a member that stopped firing names itself."""
    assert contains_reference("There is no Article 114")
    assert contains_reference("Annex IV does not exist")
    assert contains_reference("GOVERN 1.8 does not exist")
    assert contains_reference("GV-1.1-001 does not exist")
    assert contains_reference("ISO/IEC 42001 does not exist")
    assert contains_reference("EU AI Act does not exist")


def test_the_reference_set_is_closed_against_a_capitalised_noun_phrase():
    """The open-ended form was removed because it would match any capitalised noun phrase."""
    assert not contains_reference("The Grand Council of Widgets")
    assert not is_existence_denial("The Grand Council of Widgets is not covered by the corpus.")


def test_the_recompiled_patterns_are_the_committed_ones_character_for_character():
    """Section 7.3 prescribes case folding and the committed patterns are case-sensitive.

    Recompiling with IGNORECASE is the only way both sentences hold. This asserts the shapes have
    one source: the pattern strings must be identical to the committed objects', so the grammar
    cannot drift from src/complete/references.py.
    """
    from src.score.adversarial import _REF_PATTERNS

    assert [p.pattern for p in _REF_PATTERNS] == [
        p.pattern for p in COMMITTED_REFERENCE_PATTERNS
    ]
    assert [p.pattern for p in COMMITTED_REFERENCE_PATTERNS] == [
        R_ART.pattern, R_ANX.pattern, R_SUB.pattern, R_ACT.pattern
    ]
    for pattern in _REF_PATTERNS:
        assert pattern.flags & re.IGNORECASE


def test_the_committed_patterns_alone_do_not_match_folded_text():
    """The reason the recompile exists, asserted rather than described."""
    assert R_ART.search("Article 114")
    assert not R_ART.search("article 114")
    assert R_SUB.search("GOVERN 1.8")
    assert not R_SUB.search("govern 1.8")


def test_each_denial_pattern_family_fires():
    assert is_existence_denial("There is no Article 114")          # E1
    assert is_existence_denial("Article 114 does not exist")       # E1
    assert is_existence_denial("No such subcategory GOVERN 1.8")   # E1
    assert is_existence_denial("Article 114 is not in the provided context")   # E2
    assert is_existence_denial("I cannot find GOVERN 7.1")         # E2
    assert is_existence_denial("ISO/IEC 42001 is not covered by the corpus")   # E3


# --------------------------------------------------------------------------------------
# Section 7.3, the corpus-phrase set, after the 3eb3960 correction
# --------------------------------------------------------------------------------------


def test_the_corpus_phrase_set_is_the_seven_literals_and_the_four_document_titles():
    assert len(CORPUS_PHRASE_LITERALS) == 7
    assert len(document_titles()) == 4
    assert len(corpus_phrases()) == 11


def test_the_instrument_names_are_the_two_the_adversarial_rows_carry():
    """Section 7.3 lists exactly these two, read from eval/test_queries.jsonl."""
    assert INSTRUMENT_NAMES == ("ISO/IEC 42001", "EU AI Act")


def test_the_four_titles_are_read_from_the_manifests_and_not_restated():
    """The set is defined by the artifact. A hand-copied title could drift from it silently."""
    from_disk = []
    for path in sorted((REPO_ROOT / "data" / "chunks").glob("*.manifest.json")):
        with open(path, encoding="utf-8") as handle:
            from_disk.append(json.load(handle)["doc_title"])
    assert list(document_titles()) == from_disk
    assert len(from_disk) == 4


def test_a_document_title_is_matched_as_a_substring_of_the_tail():
    """The title carries no leading article and the sentence does, which anchoring would miss."""
    assert is_existence_denial("GOVERN 7.1 is not addressed in the NIST AI RMF Playbook")


def test_the_inert_member_is_in_the_set_and_the_set_is_defined_by_the_artifact():
    """The 173-character regulation citation is a member no answer will carry. It stays."""
    longest = max(document_titles(), key=len)
    assert len(longest) == 173
    assert longest.startswith("Regulation (EU) 2024/1689")


# --------------------------------------------------------------------------------------
# Section 3, the response classes
# --------------------------------------------------------------------------------------


def test_the_three_response_classes():
    assert response_class(MARKER) == ABSTAINED
    assert response_class(MARKER.lower()) == MARKER_VARIANT
    assert response_class(MARKER.rstrip(".")) == MARKER_VARIANT
    assert response_class(MARKER + " And more.") == ANSWERED
    assert response_class("Providers shall keep records.") == ANSWERED


def test_a_marker_variant_row_is_answered_and_carries_no_units():
    """Section 6.1: the one route to an answered row with zero claim units."""
    from src.score.claims import claim_units

    assert response_class(MARKER.lower()) == MARKER_VARIANT
    assert claim_units(MARKER.lower()) == []
    assert row_verdict(MARKER.lower()) == NOT_FAILURE
