"""The claim-unit segmenter, against constructed cases fixed before any answer exists.

Every case here was written from eval/generation_predictions.md section 4 and from the forms this
corpus and these prompts make likely. None was drawn from a model output, because none exists.
"""

from __future__ import annotations

import subprocess
import sys

from src.generate.prompts import MARKER
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.claims import ABBREVIATIONS, claim_units, segment, split_sentences


def test_identifiers_with_internal_periods_are_not_split():
    """GOVERN 1.3 and Article 9.3 are the corpus's own identifier forms."""
    answer = "GOVERN 1.3 requires documentation. Article 9.3 requires risk management."
    units = claim_units(answer)
    assert units == [
        "GOVERN 1.3 requires documentation.",
        "Article 9.3 requires risk management.",
    ]


def test_a_dotted_identifier_alone_in_a_sentence_stays_whole():
    assert claim_units("The control is GV-1.1-001.") == ["The control is GV-1.1-001."]


def test_abbreviations_do_not_terminate_a_sentence():
    answer = "The Act, e.g. Art. 9, applies. It also applies elsewhere."
    assert claim_units(answer) == [
        "The Act, e.g. Art. 9, applies.",
        "It also applies elsewhere.",
    ]


def test_the_abbreviation_list_is_closed_and_fixed():
    """Growing it after seeing answers would merge units and change every denominator.

    The whole set is pinned rather than its size, so an addition is a failing test whatever it
    is, and the failure names the member that was added.
    """
    assert sorted(ABBREVIATIONS) == [
        "approx", "art", "arts", "cf", "e.g", "etc", "fig", "figs", "i.e",
        "no", "nos", "para", "paras", "pp", "sec", "secs", "vs",
    ]
    assert "framework" not in ABBREVIATIONS


def test_each_bulleted_item_is_its_own_unit():
    assert claim_units("- first item\n- second item") == ["first item", "second item"]


def test_each_numbered_item_is_its_own_unit():
    assert claim_units("1. first\n2. second") == ["first", "second"]


def test_parenthesised_letter_items_are_units():
    """The EU AI Act prints enumerated points as (a), (b), and answers copy the form."""
    assert claim_units("(a) first point\n(b) second point") == ["first point", "second point"]


def test_prose_followed_by_a_list_produces_both_forms():
    answer = "The obligations are as follows.\n- keep records\n- report incidents"
    assert claim_units(answer) == [
        "The obligations are as follows.",
        "keep records",
        "report incidents",
    ]


def test_a_multi_sentence_list_item_is_one_unit():
    """Section 4's list rule governs inside a list. Recorded because the sentence admits the
    other reading, and the other reading merges items whenever one lacks terminal punctuation."""
    assert claim_units("- first. second.") == ["first. second."]


def test_a_final_sentence_without_terminal_punctuation_is_still_a_unit():
    assert claim_units("This is a claim") == ["This is a claim"]


def test_the_marker_alone_produces_no_units():
    assert claim_units(MARKER) == []


def test_the_marker_followed_by_content_yields_the_content_only():
    """Section 3 rejects containment: the content is claim units and is graded."""
    answer = MARKER + " Article 114 requires transparency."
    assert claim_units(answer) == ["Article 114 requires transparency."]


def test_marker_variants_produce_no_units():
    assert claim_units(MARKER.lower()) == []
    assert claim_units(MARKER.rstrip(".")) == []


def test_a_sentence_about_the_context_is_a_unit_and_is_graded():
    """Section 4 names this sentence type explicitly as graded, not excluded."""
    answer = "The context does not specify the penalty amount."
    assert claim_units(answer) == ["The context does not specify the penalty amount."]


def test_the_exclusion_is_the_marker_and_nothing_else():
    """A wider exclusion could be widened again after seeing answers."""
    answer = "In summary, the following applies. Providers shall keep records."
    assert len(claim_units(answer)) == 2


def test_the_empty_answer_produces_no_units():
    assert claim_units("") == []
    assert claim_units("   \n\n  ") == []


def test_blank_lines_separate_prose_blocks():
    assert claim_units("First claim\n\nSecond claim") == ["First claim", "Second claim"]


def test_split_sentences_keeps_terminators():
    assert split_sentences("A. B? C!") == ["A.", "B?", "C!"]


def test_segmentation_is_deterministic_in_process_and_in_a_fresh_one():
    answer = "GOVERN 1.3 applies, e.g. Art. 9.\n- one\n- two\nA trailing claim"
    first = segment(answer)
    assert first == segment(answer)
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from src.score.claims import segment;"
        "print(repr(segment(%r)))" % (str(REPO_ROOT), answer)
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=REPO_ROOT
    )
    assert out.stdout.strip() == repr(first)


def test_segment_includes_the_marker_and_claim_units_removes_it():
    """The two functions differ by exactly the exclusion, which is what section 4 bounds."""
    answer = MARKER + " Something else."
    assert segment(answer) == [MARKER, "Something else."]
    assert claim_units(answer) == ["Something else."]
