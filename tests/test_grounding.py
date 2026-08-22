"""The grounding predicate, against constructed cases fixed before any answer exists.

Section 5.1 of eval/generation_predictions.md defines the property and section 5.2 the two
constants. Every case here was written from those sections. None was drawn from a model output.
"""

from __future__ import annotations

import builtins

from src.complete.absence import RetrievedChunk
from src.retrieve.tokenize import primary_tokens
from src.generate.prompts import render_context
from src.score.grounding import (
    OVERLAP_THRESHOLD,
    SHORT_UNIT_LENGTH,
    SHORT_UNIT_THRESHOLD,
    block_admits_unit,
    grade_answer,
    is_grounded,
    reference_surfaces,
    rendered_block,
    score_unit,
    threshold_for,
    window_score,
)

CHUNK_A = RetrievedChunk(
    chunk_id="eu_ai_act:art_9#p1",
    unit_label="Article 9",
    text=(
        "Providers of high-risk AI systems shall establish, implement, document and maintain "
        "a risk management system in relation to high-risk AI systems."
    ),
)
CHUNK_B = RetrievedChunk(
    chunk_id="eu_ai_act:art_9#p2",
    unit_label="Article 9",
    text=(
        "The risk management system shall be understood as a continuous iterative process "
        "planned and run throughout the entire lifecycle of a high-risk AI system."
    ),
)
CONTEXT = (CHUNK_A, CHUNK_B)


def test_the_two_constants_are_the_section_5_2_values():
    """A change to either is a failing test, which is what makes them candidates and not knobs."""
    assert OVERLAP_THRESHOLD == 0.75
    assert SHORT_UNIT_LENGTH == 4
    assert SHORT_UNIT_THRESHOLD == 1.0


def test_the_short_unit_threshold_applies_below_the_length_and_not_at_it():
    assert threshold_for(3) == SHORT_UNIT_THRESHOLD
    assert threshold_for(4) == OVERLAP_THRESHOLD


def test_a_unit_verbatim_from_a_chunk_is_grounded():
    unit = (
        "Providers of high-risk AI systems shall establish, implement, document and maintain "
        "a risk management system."
    )
    assert score_unit(unit, CONTEXT) == 1.0
    assert is_grounded(unit, CONTEXT)


def test_a_unit_assembled_from_two_chunks_is_not_grounded():
    """Six tokens from CHUNK_A's head and six from CHUNK_B's tail. Neither chunk holds it."""
    unit = "providers of high-risk ai systems shall lifecycle of a high-risk ai system"
    assert score_unit(unit, (CHUNK_A,)) < OVERLAP_THRESHOLD
    assert score_unit(unit, (CHUNK_B,)) < OVERLAP_THRESHOLD
    assert not is_grounded(unit, CONTEXT)


CHUNK_X = RetrievedChunk(
    chunk_id="eu_ai_act:art_11#p1",
    unit_label="Article 11",
    text="The provider shall keep the technical documentation for ten years",
)
CHUNK_Y = RetrievedChunk(
    chunk_id="eu_ai_act:art_74#p1",
    unit_label="Article 74",
    text="Market surveillance authorities may request access to training datasets",
)


def test_a_unit_spanning_the_boundary_between_adjacent_chunks_is_not_grounded():
    """The tail of one chunk and the head of the next, which a concatenating window accepts.

    The case is built on two chunks with disjoint vocabulary so the arithmetic is unambiguous:
    the unit scores 0.5 against each chunk alone and 1.0 against their concatenation. The second
    assertion is what makes the first mean something; without it the test would pass on a
    predicate that simply scored everything ungrounded.
    """
    boundary = (CHUNK_X, CHUNK_Y)
    unit = "documentation for ten years Market surveillance authorities may"
    assert score_unit(unit, (CHUNK_X,)) == 0.5
    assert score_unit(unit, (CHUNK_Y,)) == 0.5
    assert not is_grounded(unit, boundary)
    joined = primary_tokens(CHUNK_X.text) + primary_tokens(CHUNK_Y.text)
    assert window_score(primary_tokens(unit), joined) == 1.0, (
        "the case does not exercise the boundary: it must be grounded against a concatenation "
        "and ungrounded against the chunks, or it proves nothing"
    )


def test_a_short_unit_missing_one_token_is_not_grounded():
    """Below the short-unit length the threshold is exact containment."""
    unit = "risk management plan"
    assert len(primary_tokens(unit)) < SHORT_UNIT_LENGTH
    assert not is_grounded(unit, CONTEXT)
    assert is_grounded("risk management system", CONTEXT)


def test_typographic_characters_fold_to_ascii_on_both_sides():
    chunk = RetrievedChunk(
        chunk_id="c", unit_label="l", text="the provider's duty to keep records is set out here"
    )
    unit = "the provider’s duty to keep records"
    assert is_grounded(unit, (chunk,))


def test_a_short_unit_naming_the_wrong_identifier_is_not_grounded():
    chunk = RetrievedChunk(chunk_id="c", unit_label="l", text="GOVERN 1.3 requires documentation")
    assert is_grounded("GOVERN 1.3", (chunk,))
    assert not is_grounded("GOVERN 1.4", (chunk,))


def test_the_identifier_is_one_token_and_is_not_shredded():
    assert primary_tokens("GV-1.1-001") == ["gv-1.1-001"]
    assert primary_tokens("GOVERN 1.3") == ["govern", "1.3"]


def test_the_overlap_term_alone_tolerates_a_wrong_identifier_at_length():
    """THE OVERLAP TERM ON ITS OWN, which is what this test is about after the section 5.1 change.

    At OVERLAP_THRESHOLD a unit of n tokens differing from its best window in k tokens clears the
    term exactly when (n - k) / n is at or above the threshold, so k at or below n / 4. A wrong
    identifier is one token, so a four-token unit tolerates it. This is why keeping identifiers
    whole is necessary and not sufficient, and why the reference condition exists. It is asserted
    against window_score, the overlap term itself, because score_unit now folds the reference
    condition into its maximum and would return 0.0 here.
    """
    block_tokens = primary_tokens("GOVERN 1.3 requires documentation of the process")
    four = primary_tokens("GOVERN 1.4 requires documentation")
    assert len(four) == 4
    assert window_score(four, block_tokens) == 0.75
    assert 0.75 >= OVERLAP_THRESHOLD, "the overlap term alone would have called this grounded"


def test_the_reference_condition_catches_what_the_overlap_term_tolerates():
    """The companion to the test above, and the reason section 5.1 gained a third condition."""
    chunk = RetrievedChunk(
        chunk_id="c", unit_label="l", text="GOVERN 1.3 requires documentation of the process"
    )
    assert not is_grounded("GOVERN 1.4 requires documentation", (chunk,))
    assert is_grounded("GOVERN 1.3 requires documentation", (chunk,))


def test_the_rendered_block_is_what_the_request_carries():
    """The grader's block must be the assembler's block, asserted against the assembler itself.

    If src/generate/prompts.py ever changes how a chunk is rendered, this reddens rather than the
    grader silently grading against a surface the model never saw.
    """
    chunks = (CHUNK_A, CHUNK_B)
    assert "\n\n".join(rendered_block(c) for c in chunks) == render_context(chunks)
    assert rendered_block(CHUNK_A).startswith("[eu_ai_act:art_9#p1] Article 9\n")


def test_the_block_carries_the_label_identifier_the_text_does_not():
    """The near-miss shape: the identifier lives in the label and never in the text."""
    playbook = RetrievedChunk(
        chunk_id="nist_playbook:sub_GOVERN_2.3.ai_transparency_resources",
        unit_label="GOVERN 2.3 AI Transparency Resources",
        text="AI Transparency Resources . WEF Companion to the Model AI Governance Framework- 2020.",
    )
    assert reference_surfaces(playbook.text) == frozenset()
    assert ("2", "GOVERN", "2.3") in reference_surfaces(rendered_block(playbook))


def test_reference_surfaces_are_compared_by_captured_groups():
    assert reference_surfaces("Article 9") == reference_surfaces("Articles 9")
    assert reference_surfaces("Article 9") != reference_surfaces("Article 10")


def test_the_case_handling_is_the_committed_patterns_unchanged():
    """Section 5.1: a case-insensitive R_SUB would read a surface out of the English word map."""
    assert reference_surfaces("the map 3.3 revision") == frozenset()
    assert reference_surfaces("MAP 3.3") == frozenset({("2", "MAP", "3.3")})


def test_a_unit_with_no_surface_is_graded_by_overlap_alone():
    assert reference_surfaces("Providers shall keep records") == frozenset()
    assert block_admits_unit(frozenset(), "any block at all")


def test_the_reference_condition_is_block_scoped_not_window_scoped():
    """The measurement that decided it: the surface sits at token 0 of a long block."""
    long_text = "Article 6 " + " ".join(f"filler{i}" for i in range(300)) + " the annual report"
    chunk = RetrievedChunk(chunk_id="eu_ai_act:art_6", unit_label="Article 6", text=long_text)
    unit = "Article 6 requires the annual report"
    assert block_admits_unit(reference_surfaces(unit), rendered_block(chunk))
    # and the aligning material is hundreds of tokens from the surface
    assert primary_tokens(rendered_block(chunk)).index("article") < 5
    assert len(primary_tokens(rendered_block(chunk))) > 300


def test_a_chunk_shorter_than_the_unit_contributes_no_window():
    short = RetrievedChunk(chunk_id="c", unit_label="l", text="risk management")
    unit = "providers shall establish a risk management system"
    assert window_score(primary_tokens(unit), primary_tokens(short.text)) == 0.0
    assert score_unit(unit, (short,)) == 0.0
    assert not is_grounded(unit, (short,))


def test_a_unit_with_no_primary_tokens_scores_zero_and_is_unsupported():
    assert primary_tokens("...") == []
    assert score_unit("...", CONTEXT) == 0.0
    assert not is_grounded("...", CONTEXT)


def test_window_score_is_multiset_containment_not_set_overlap():
    """A repeated token in the unit must be matched as many times as it occurs."""
    assert window_score(["a", "a"], ["a", "b"]) == 0.5
    assert window_score(["a", "a"], ["a", "a"]) == 1.0


def test_grade_answer_counts_units_and_lists_the_unsupported_ones():
    answer = (
        "Providers of high-risk AI systems shall establish, implement, document and maintain "
        "a risk management system. Providers shall appoint a data protection officer."
    )
    grading = grade_answer(answer, CONTEXT)
    assert grading.n_units == 2
    assert grading.n_grounded == 1
    assert grading.n_unsupported == 1
    assert grading.unsupported_units == ("Providers shall appoint a data protection officer.",)


def test_grade_answer_excludes_the_marker_from_the_denominator():
    from src.generate.prompts import MARKER

    assert grade_answer(MARKER, CONTEXT).n_units == 0


def test_the_grader_opens_no_file(monkeypatch):
    """V20's first form: the guard is shown capable of recording before its empty result counts."""
    opened: list[str] = []
    real_open = builtins.open

    def guarded(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    import src.score.claims  # noqa: F401  imported before the guard so import machinery is out

    monkeypatch.setattr(builtins, "open", guarded)
    open(__file__, encoding="utf-8").close()  # the control read, through the guard
    control = len(opened)
    grade_answer("Providers shall establish a risk management system.", CONTEXT)
    after = len(opened)
    monkeypatch.undo()

    assert control == 1, "the guard recorded nothing on a known read, so it proves nothing"
    assert after == control, f"the grader opened {opened[control:]}"
