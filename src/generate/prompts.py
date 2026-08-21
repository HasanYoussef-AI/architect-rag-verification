"""The three prompt literals and the context renderer, component H1 part two.

THE PROMPTS ARE LITERALS HERE AND NOWHERE ELSE. eval/generation_predictions.md quotes
them from this module rather than transcribing them, so there is one source and the
predictions file cannot drift from what the assembler emits. A test asserts the digests
of these literals against pinned values, so a prompt edit after the predictions file
commits is a failing test rather than a silent change.

THE MARKER IS ONE LITERAL SHARED BY ALL THREE PROMPTS. Detection is exact string
comparison against a normalised claim unit, never a pattern, because a fuzzy marker
detector is a detector that matches on shape while the claim lives in content. One
literal means one detector rather than three.

The marker is worded without reference to context so that the same sentence is true and
usable in all three conditions. A marker phrased as "the retrieved context does not
support an answer" reads as false in the no-context condition, which receives no context
at all, and would have forced either a second literal or a marker the model could
reasonably decline to emit.

WHY THE NO-CONTEXT PROMPT CARRIES NO CLOSED-BOOK INSTRUCTION. CLAUDE.md Rule 1 governs
the operational pipeline, the raw and layer conditions. The no-context condition is a
contamination probe: PREREGISTRATION.md states it "Measures how much of the raw score is
carried by parametric knowledge of a public corpus rather than by retrieval". Under the
closed-book instruction with an empty context the only compliant output is abstention on
every row, so the condition would measure nothing. The departure is recorded here, in the
run manifest, and in the predictions file rather than left implicit.

WHY NO CITATIONS ARE REQUESTED. docs/METHODOLOGY.md names citing a real chunk that does
not say the thing as part of the faithfulness surface, but PREREGISTRATION.md pre-registers
no citation metric, and the grounding predicate aligns a claim against the whole committed
context rather than against a cited chunk. Asking for citations would add text that is not
a claim, would enlarge every answer, and would create a surface no pre-registered figure
scores. Recorded as a decision rather than an omission.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from src.complete.absence import RetrievedChunk

# The one marker literal. Emitted by the model, detected by exact comparison.
MARKER = "I do not have enough information to answer this question."

# Response classes. The detector lives beside its literal so the two cannot drift apart.
ABSTAINED = "abstained"
ANSWERED = "answered"
MARKER_VARIANT = "marker_variant"

_WHITESPACE = re.compile(r"\s+")


def normalize_response(text: str) -> str:
    """The normalisation abstention detection runs against.

    Two operations and no more: strip the outer whitespace, then collapse every internal
    whitespace run to one space. Nothing is case-folded and no punctuation is removed, so
    the comparison stays exact. Anything looser is handled by the variant class below
    rather than by widening this function, because a detector that quietly accepts near
    misses is a detector matching on shape while the claim lives in content.
    """
    return _WHITESPACE.sub(" ", text.strip())


def classify_response(text: str) -> str:
    """ABSTAINED, MARKER_VARIANT or ANSWERED.

    ABSTENTION IS WHOLE-RESPONSE EQUALITY, NEVER CONTAINMENT. A response carrying the
    marker followed by substantive content is not an abstention; its content is claim units
    and is graded. Containment would score a marker-plus-parametric answer as a clean
    abstention on exactly the adversarial rows this study cares most about, which is the
    false pass the sealed pre-declaration's own sentence constructs.

    MARKER_VARIANT is a response that equals the marker only after case folding or after
    dropping a trailing period. It is counted and listed rather than silently bucketed, and
    it is treated as ANSWERED everywhere a binary is needed. That is the direction that
    costs us: on the adversarial stratum it lowers the abstention rate rather than raising
    it, and the study should not be flattered by a near miss.
    """
    normalized = normalize_response(text)
    if normalized == MARKER:
        return ABSTAINED
    if normalized.casefold().rstrip(".") == MARKER.casefold().rstrip("."):
        return MARKER_VARIANT
    return ANSWERED


def is_abstention(text: str) -> bool:
    """The binary form. A variant is not an abstention."""
    return classify_response(text) == ABSTAINED

RAW_SYSTEM = """You answer questions about AI governance frameworks using only the context provided in the user message.

Rules:
- Use only the provided context. Do not use anything you know from training. If the context does not contain the answer, do not supply it from memory.
- If the provided context does not support an answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
- Be brief. Answer the question and stop."""

SECOND_CALL_SYSTEM = """You are revising an answer about AI governance frameworks using only the context provided in the user message.

The context provided below may have been expanded since the first answer was written, and it may now contain passages the first answer did not have.

Rules:
- Use only the provided context. Do not use anything you know from training. If the context does not contain the answer, do not supply it from memory.
- Statements listed as unsupported were not supported by the context. Either support each one from the context provided below or leave it out. Do not repeat one unchanged.
- Write the answer the provided context supports.
- If the provided context does not support an answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
- Be brief. Answer the question and stop."""

NO_CONTEXT_SYSTEM = """You answer questions about AI governance frameworks.

Rules:
- Answer the question directly.
- If you do not know the answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
- Be brief. Answer the question and stop."""

PROMPTS = {
    "raw": RAW_SYSTEM,
    "second_call": SECOND_CALL_SYSTEM,
    "no_context": NO_CONTEXT_SYSTEM,
}


def render_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Render retrieved context as text, using the three admitted fields and no others.

    One block per chunk, in the order given, which for the layer condition is the
    committed corrective pass's order: the first-pass ten unchanged, then the fetched
    chunks. A `RetrievedChunk` carries only `chunk_id`, `text` and `unit_label`, so the
    fourteen remaining `Chunk` fields are unreachable here by type rather than declined.
    """
    return "\n\n".join(
        f"[{c.chunk_id}] {c.unit_label}\n{c.text}" for c in chunks
    )


def render_raw_user(query: str, chunks: Sequence[RetrievedChunk]) -> str:
    return f"Context:\n\n{render_context(chunks)}\n\nQuestion: {query}"


def render_no_context_user(query: str) -> str:
    return f"Question: {query}"


def render_second_call_user(
    query: str,
    chunks: Sequence[RetrievedChunk],
    first_answer: str,
    flagged_claims: Sequence[str],
) -> str:
    """The second call is a single user turn, never a prefilled assistant turn.

    Assistant message prefills return a 400 on Claude Opus 4.8 and Claude Sonnet 5, so the
    first answer enters as quoted text inside the user turn. A two-turn conversation would
    also work and is rejected for a different reason: it would carry the first-pass ten in
    the earlier turn and the augmented set in the later one, sending the first-pass chunks
    twice, since augmentation appends rather than replaces.
    """
    if flagged_claims:
        flagged = "\n".join(f"- {c}" for c in flagged_claims)
    else:
        flagged = "(none)"
    return (
        f"Context:\n\n{render_context(chunks)}\n\n"
        f"Question: {query}\n\n"
        f"First answer:\n{first_answer}\n\n"
        f"Statements from the first answer that the context did not support:\n{flagged}"
    )
