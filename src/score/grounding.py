"""The grounding predicate, the grader of record.

eval/generation_predictions.md section 5.1 defines the property and section 5.2 fixes the two
constants. This module implements them and nothing else.

WHAT IT READS. The committed answer and the committed context of the request that produced it,
arriving as RetrievedChunk values, the three-field type src/complete/ and src/generate/ already
use. THE UNIT OF THAT CONTEXT IS THE RENDERED BLOCK, the exact per-chunk string the request
carries, bracketed chunk id then unit label then text, and not the chunk text alone. An earlier
form of this module aligned against chunk.text; that was a narrower surface than section 5.1
states, and measured over the committed chunk store 390 of 1294 chunks carry a reference surface
in unit_label and not in text, eight of eight on the near-miss gold blocks, so the identifier the
model was shown would have been invisible to the grader. It never reads gold, never reads a stratum label, never reads a row id, AND IT OPENS NO FILE
AT ALL: every input arrives as an argument. tests/test_grounding.py asserts that by instrumenting
open and showing the recorded list non-empty on a control call first, so the guard is proved
capable of recording before its empty result is trusted.

THE WINDOW NEVER CROSSES A CHUNK BOUNDARY. Each chunk is tokenised separately and no
concatenation of chunk text is formed anywhere in this module. A window straddling two chunks
would score a claim assembled from the end of one and the start of the next as grounded, which is
the whole-context defect the windowed form exists to remove, reintroduced at a smaller scale.

TWO CASES SECTION 5.1 DOES NOT DEFINE, AND THE CONVENTION EACH TAKES. A chunk holding fewer
tokens than the unit contains no window of the unit's length, and a maximum over an empty set is
undefined; that chunk contributes nothing, and a unit no chunk is long enough to hold scores 0.0.
A unit with no primary tokens at all would divide by zero; it scores 0.0. Both are unsupported,
which is the direction section 5.1 already commits to, costing a true positive rather than
admitting a false one.

THIS IS ONE OF TWO IMPLEMENTATIONS. src/complete/flagging.py is the other, on the layer's side,
and section 5.3 requires that neither import the other. They share src.ingest.normalize and
src.retrieve.tokenize, which section 5.1 names as the inputs of the predicate itself, and nothing
else. Their constants are defined separately on purpose: a shared constant cannot be changed in
one implementation only, and that mutation is what tests/test_grounding_crosscheck.py exists to
catch.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from src.complete.absence import RetrievedChunk
from src.complete.references import R_ACT, R_ANX, R_ART, R_SUB
from src.retrieve.tokenize import primary_tokens

# The four committed reference shapes, used as compiled and therefore case-sensitively, on the
# unit side and the block side alike. Section 5.1 states the case decision and its reason: a
# case-insensitive R_SUB would extract a surface from the ordinary English word "map".
REFERENCE_PATTERNS = (R_ART, R_ANX, R_SUB, R_ACT)

# The section 5.2 candidates, named at one site in this module and nowhere else in it.
OVERLAP_THRESHOLD = 0.75
SHORT_UNIT_LENGTH = 4
SHORT_UNIT_THRESHOLD = 1.0


@dataclass(frozen=True)
class UnitVerdict:
    """One claim unit's verdict, with the score and the threshold it was judged against."""

    unit: str
    n_tokens: int
    score: float
    threshold: float
    grounded: bool


@dataclass(frozen=True)
class AnswerGrading:
    """One answer's units and the counts section 6.1 reports over them."""

    verdicts: tuple[UnitVerdict, ...]

    @property
    def n_units(self) -> int:
        return len(self.verdicts)

    @property
    def n_grounded(self) -> int:
        return sum(1 for v in self.verdicts if v.grounded)

    @property
    def n_unsupported(self) -> int:
        return self.n_units - self.n_grounded

    @property
    def unsupported_units(self) -> tuple[str, ...]:
        return tuple(v.unit for v in self.verdicts if not v.grounded)


def rendered_block(chunk: RetrievedChunk) -> str:
    """The exact per-chunk string the request carries, which is what the model saw.

    Mirrors the join body of src/generate/prompts.py render_context. It is written out here
    rather than imported because render_context returns the whole context joined, not one block,
    and this module must tokenise each block separately. tests/test_grounding.py asserts that
    joining these with a blank line reproduces render_context exactly, so the two cannot drift.
    """
    return f"[{chunk.chunk_id}] {chunk.unit_label}\n{chunk.text}"


def reference_surfaces(text: str) -> frozenset[tuple[str, ...]]:
    """Every reference surface in text, as its pattern's captured groups.

    Compared by captured groups rather than by matched text so that "Article 9" and "Articles 9"
    are the same surface, which is what the grammar's own groups already express.
    """
    out: set[tuple[str, ...]] = set()
    for index, pattern in enumerate(REFERENCE_PATTERNS):
        for match in pattern.finditer(text):
            groups = match.groups()
            out.add((str(index),) + tuple(groups))
    return frozenset(out)


def block_admits_unit(unit_surfaces: frozenset[tuple[str, ...]], block: str) -> bool:
    """Whether a block may be a candidate for a unit, per the section 5.1 reference condition.

    Scoped to the BLOCK and never to the window. Measured over the 148 EU AI Act article chunks
    whose text carries an Article surface, the median chunk is 307 tokens and the median position
    of the first Article token is 0, so a sentence-sized window aligning to later material could
    not contain it and every correct claim about a later paragraph would be unsupported. The
    residual block scope admits is disclosed in section 5.1: on 35 of those 148 the first surface
    names a different article.
    """
    if not unit_surfaces:
        return True
    return unit_surfaces <= reference_surfaces(block)


def threshold_for(n_tokens: int) -> float:
    """The threshold a unit of this length is judged against, per section 5.2."""
    return SHORT_UNIT_THRESHOLD if n_tokens < SHORT_UNIT_LENGTH else OVERLAP_THRESHOLD


def window_score(unit_tokens: Sequence[str], chunk_tokens: Sequence[str]) -> float:
    """Best multiset containment of the unit in any window of one chunk.

    Windows are of the unit's own length and slide by one token. Returns 0.0 when the unit is
    empty or the chunk is shorter than the unit, which are the two undefined cases named above.
    """
    n = len(unit_tokens)
    if n == 0 or len(chunk_tokens) < n:
        return 0.0
    need = Counter(unit_tokens)
    best = 0
    for start in range(len(chunk_tokens) - n + 1):
        window = Counter(chunk_tokens[start : start + n])
        overlap = sum(min(count, window[token]) for token, count in need.items())
        if overlap > best:
            best = overlap
            if best == n:
                break
    return best / n


def score_unit(unit: str, chunks: Sequence[RetrievedChunk]) -> float:
    """The maximum window score over the rendered blocks a unit's references admit.

    A block failing the reference condition is not a candidate and contributes no window, so the
    two conditions fold into one maximum and the question of which window is the aligning one
    never arises. THE EARLY EXIT SITS BEHIND THE REFERENCE TEST: a block scoring 1.0 that the
    unit's references do not admit is not a reason to stop, and before the condition existed it
    would have been.
    """
    unit_tokens = primary_tokens(unit)
    if not unit_tokens:
        return 0.0
    surfaces = reference_surfaces(unit)
    best = 0.0
    for chunk in chunks:
        block = rendered_block(chunk)
        if not block_admits_unit(surfaces, block):
            continue
        score = window_score(unit_tokens, primary_tokens(block))
        if score > best:
            best = score
            if best == 1.0:
                break
    return best


def is_grounded(unit: str, chunks: Sequence[RetrievedChunk]) -> bool:
    """Whether one claim unit is grounded in the context of its own request."""
    n = len(primary_tokens(unit))
    if n == 0:
        return False
    return score_unit(unit, chunks) >= threshold_for(n)


def grade_answer(answer: str, chunks: Sequence[RetrievedChunk]) -> AnswerGrading:
    """Every claim unit of an answer, judged against that answer's own context."""
    from src.score.claims import claim_units

    verdicts = []
    for unit in claim_units(answer):
        n = len(primary_tokens(unit))
        score = score_unit(unit, chunks)
        threshold = threshold_for(n)
        verdicts.append(
            UnitVerdict(
                unit=unit,
                n_tokens=n,
                score=score,
                threshold=threshold,
                grounded=bool(n) and score >= threshold,
            )
        )
    return AnswerGrading(verdicts=tuple(verdicts))


__all__ = [
    "OVERLAP_THRESHOLD",
    "REFERENCE_PATTERNS",
    "block_admits_unit",
    "reference_surfaces",
    "rendered_block",
    "SHORT_UNIT_LENGTH",
    "SHORT_UNIT_THRESHOLD",
    "AnswerGrading",
    "UnitVerdict",
    "grade_answer",
    "is_grounded",
    "score_unit",
    "threshold_for",
    "window_score",
]
