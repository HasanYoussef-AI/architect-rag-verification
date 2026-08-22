"""The two implementations of the grounding predicate, asserted identical.

eval/generation_predictions.md section 5.3 requires the rule implemented twice, one operational
and one the grader of record, and requires that neither import the other. A disagreement between
them stops the scope and is resolved by finding which is wrong, never by making one call the
other. This file is where a disagreement surfaces.

The cases below are constructed and fixed before any answer exists. The same comparison runs over
every committed answer when answers exist; the function that does it is here and takes the rows,
so the later run is a call rather than a new test.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.complete.absence import RetrievedChunk
from src.complete.flagging import (
    FLAG_OVERLAP_THRESHOLD,
    FLAG_SHORT_UNIT_LENGTH,
    FLAG_SHORT_UNIT_THRESHOLD,
    block_admits,
    flag_rendered_block,
    flag_surfaces,
    flag_threshold_for,
    flagged_units,
    unit_is_supported,
)
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.claims import claim_units
from src.score.grounding import (
    OVERLAP_THRESHOLD,
    SHORT_UNIT_LENGTH,
    SHORT_UNIT_THRESHOLD,
    block_admits_unit,
    is_grounded,
    reference_surfaces,
    rendered_block,
    threshold_for,
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
PLAYBOOK_TEXT = (
    "AI Transparency Resources . WEF Companion to the Model AI Governance Framework- 2020."
)
GOLD_BLOCK = RetrievedChunk(
    chunk_id="nist_playbook:sub_GOVERN_2.3.ai_transparency_resources",
    unit_label="GOVERN 2.3 AI Transparency Resources",
    text=PLAYBOOK_TEXT,
)
SIBLING_BLOCK = RetrievedChunk(
    chunk_id="nist_playbook:sub_MAP_3.3.ai_transparency_resources",
    unit_label="MAP 3.3 AI Transparency Resources",
    text=PLAYBOOK_TEXT,
)
# The unit a model would write answering test_43: it restates the queried subcategory and its
# content is the sibling's content verbatim, which is the near-miss trap in one sentence.
#
# THE CASE IS CHOSEN SO THE OVERLAP TERM ALONE WOULD GROUND IT AGAINST BOTH BLOCKS. Measured, it
# scores 0.8571 against the sibling block and 0.8571 against the gold block, both above the 0.75
# threshold, so the reference condition is the only thing separating them. An earlier form of this
# case scored 0.7333 against the sibling, below the threshold, and would have passed even with the
# condition removed from both implementations: it asserted the right verdict for the wrong reason.
# The two-file mutation in the report 16 record is what exposed that, and this comment records it
# so the case cannot drift back into a shape that proves nothing.
WRONG_LABEL_UNIT = (
    "GOVERN 2.3 AI Transparency Resources WEF Companion to the Model AI Governance Framework 2020"
)

SHORT = RetrievedChunk(chunk_id="c", unit_label="l", text="risk management")
IDENT = RetrievedChunk(chunk_id="c", unit_label="l", text="GOVERN 1.3 requires documentation")
CURLY = RetrievedChunk(
    chunk_id="c", unit_label="l", text="the provider's duty to keep records is set out here"
)

# Every constructed case of tests/test_grounding.py, as (unit, context) pairs.
CASES: tuple[tuple[str, tuple[RetrievedChunk, ...]], ...] = (
    ("Providers of high-risk AI systems shall establish, implement, document and maintain "
     "a risk management system.", (CHUNK_A, CHUNK_B)),
    ("providers of high-risk ai systems shall lifecycle of a high-risk ai system",
     (CHUNK_A, CHUNK_B)),
    ("documentation for ten years Market surveillance authorities may", (CHUNK_X, CHUNK_Y)),
    ("risk management plan", (CHUNK_A, CHUNK_B)),
    ("risk management system", (CHUNK_A, CHUNK_B)),
    ("the provider’s duty to keep records", (CURLY,)),
    ("GOVERN 1.3", (IDENT,)),
    ("GOVERN 1.4", (IDENT,)),
    ("GOVERN 1.4 requires documentation", (IDENT,)),
    ("providers shall establish a risk management system", (SHORT,)),
    ("...", (CHUNK_A,)),
    ("Providers shall appoint a data protection officer.", (CHUNK_A, CHUNK_B)),
    ("The risk management system shall be understood as a continuous iterative process",
     (CHUNK_A, CHUNK_B)),
    ("a", (CHUNK_A,)),
    ("high-risk ai systems", (CHUNK_A,)),
    (WRONG_LABEL_UNIT, (SIBLING_BLOCK,)),
    (WRONG_LABEL_UNIT, (GOLD_BLOCK,)),
    (WRONG_LABEL_UNIT, (SIBLING_BLOCK, GOLD_BLOCK)),
    ("Article 9 and Article 10 both apply", (CHUNK_A, CHUNK_B)),
    ("the map 3.3 revision was adopted", (SIBLING_BLOCK,)),
)


def disagreements(
    cases: Sequence[tuple[str, Sequence[RetrievedChunk]]],
) -> list[tuple[str, bool, bool]]:
    """Every case where the grader and the flagging pass differ, as (unit, grader, flagger).

    Takes the cases so the same function runs over the committed answers when they exist.
    """
    out = []
    for unit, context in cases:
        grader = is_grounded(unit, context)
        flagger = unit_is_supported(unit, context)
        if grader != flagger:
            out.append((unit, grader, flagger))
    return out


def test_the_two_implementations_agree_on_every_constructed_case():
    assert CASES, "an empty case list would make this test pass by having nothing to check"
    found = disagreements(CASES)
    assert found == [], f"the two implementations disagree on {found}"


def test_the_case_list_exercises_both_verdicts():
    """V20: an agreement test over cases that are all True would pass on two broken predicates."""
    verdicts = {is_grounded(u, c) for u, c in CASES}
    assert verdicts == {True, False}, "the cases do not exercise both outcomes"


def test_both_implementations_carry_the_section_5_2_values_and_agree():
    """The constants are duplicated on purpose. This is what keeps the duplication honest."""
    assert (OVERLAP_THRESHOLD, SHORT_UNIT_LENGTH, SHORT_UNIT_THRESHOLD) == (0.75, 4, 1.0)
    assert (FLAG_OVERLAP_THRESHOLD, FLAG_SHORT_UNIT_LENGTH, FLAG_SHORT_UNIT_THRESHOLD) == (
        0.75, 4, 1.0,
    )
    assert OVERLAP_THRESHOLD == FLAG_OVERLAP_THRESHOLD
    assert SHORT_UNIT_LENGTH == FLAG_SHORT_UNIT_LENGTH
    assert SHORT_UNIT_THRESHOLD == FLAG_SHORT_UNIT_THRESHOLD
    for n in range(0, 12):
        assert threshold_for(n) == flag_threshold_for(n)


def test_neither_module_imports_the_other():
    """Section 5.3, asserted by reading both sources rather than by trusting the design."""
    grader = (REPO_ROOT / "src" / "score" / "grounding.py").read_text(encoding="utf-8")
    flagger = (REPO_ROOT / "src" / "complete" / "flagging.py").read_text(encoding="utf-8")
    assert "src.complete.flagging" not in grader
    assert "src.score.grounding" not in flagger
    # The control: both DO reference the two modules section 5.1 names as shared inputs.
    assert "src.retrieve.tokenize" in grader and "src.retrieve.tokenize" in flagger


def test_the_wrong_label_case_in_the_shape_of_test_43():
    """The case the reference condition exists for, asserted on both implementations.

    The same content sits in both blocks. Only the rendered label differs, and the label is where
    the identifier lives: measured over the committed store, all eight near-miss gold blocks carry
    their subcategory identifier in unit_label and none carries it in text.
    """
    # The overlap term alone would ground it against BOTH blocks, so the reference condition is
    # the only discriminator. Asserted first, or the case below proves nothing.
    from src.score.grounding import window_score
    from src.retrieve.tokenize import primary_tokens

    unit_tokens = primary_tokens(WRONG_LABEL_UNIT)
    assert window_score(unit_tokens, primary_tokens(rendered_block(SIBLING_BLOCK))) >= 0.75
    assert window_score(unit_tokens, primary_tokens(rendered_block(GOLD_BLOCK))) >= 0.75

    # Against the sibling alone the unit names a provision the block does not carry.
    assert not is_grounded(WRONG_LABEL_UNIT, (SIBLING_BLOCK,))
    assert not unit_is_supported(WRONG_LABEL_UNIT, (SIBLING_BLOCK,))
    # Against the gold block the same sentence is grounded, so the condition is not simply strict.
    assert is_grounded(WRONG_LABEL_UNIT, (GOLD_BLOCK,))
    assert unit_is_supported(WRONG_LABEL_UNIT, (GOLD_BLOCK,))
    # And with both present, the gold block is the one that admits it.
    assert is_grounded(WRONG_LABEL_UNIT, (SIBLING_BLOCK, GOLD_BLOCK))
    assert unit_is_supported(WRONG_LABEL_UNIT, (SIBLING_BLOCK, GOLD_BLOCK))


def test_both_implementations_render_the_same_block_and_read_the_same_surfaces():
    """Section 5.1 bars an asymmetry between the two sides, so it is asserted rather than assumed."""
    for chunk in (CHUNK_A, GOLD_BLOCK, SIBLING_BLOCK, SHORT, IDENT):
        assert rendered_block(chunk) == flag_rendered_block(chunk)
        block = rendered_block(chunk)
        assert reference_surfaces(block) == frozenset(flag_surfaces(block))
    for unit, _ in CASES:
        assert reference_surfaces(unit) == frozenset(flag_surfaces(unit))
        for chunk in (GOLD_BLOCK, SIBLING_BLOCK):
            assert block_admits_unit(reference_surfaces(unit), rendered_block(chunk)) == (
                block_admits(flag_surfaces(unit), flag_rendered_block(chunk))
            )


def test_flagged_units_are_exactly_the_grader_s_unsupported_units():
    """The operational output and the headline grading must name the same sentences."""
    answer = (
        "Providers of high-risk AI systems shall establish, implement, document and maintain "
        "a risk management system. Providers shall appoint a data protection officer."
    )
    context = (CHUNK_A, CHUNK_B)
    flagged = flagged_units(answer, context)
    ungrounded = tuple(u for u in claim_units(answer) if not is_grounded(u, context))
    assert flagged == ungrounded
    assert flagged == ("Providers shall appoint a data protection officer.",)
