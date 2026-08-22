"""The operational flagging pass, component of the layer and the SECOND implementation.

eval/generation_predictions.md section 5.3 requires the grounding rule implemented twice: one
operational, whose output becomes the flagged-statement list the second-call prompt carries, and
one the grader of record. This is the operational one. It lives under src/complete/ rather than
under src/score/ because its output is layer machinery and not measurement.

IT DOES NOT IMPORT THE GRADER AND THE GRADER DOES NOT IMPORT IT. Section 5.3 requires that, and a
test asserts it by reading both modules' imports. The two share src.ingest.normalize and
src.retrieve.tokenize, which section 5.1 names as the inputs of the predicate itself, and nothing
else. The claim-unit segmenter is shared for the same reason: it is the definition of the object
being judged rather than part of the judgement, so duplicating it would be duplicating section 4
and not section 5.

THE CONSTANTS ARE DEFINED HERE, SEPARATELY FROM THE GRADER'S. That duplication is deliberate. A
constant shared between the two implementations could not be changed in one of them only, and a
threshold changed in one implementation only is precisely the mutation
tests/test_grounding_crosscheck.py exists to catch. One test pins both sets to the section 5.2
values and asserts they are equal, so the duplication cannot drift silently.

THE ALGORITHM IS DELIBERATELY NOT THE GRADER'S. The grader rebuilds a counter per window. This
one carries a rolling multiset across the sliding window, adding the entering token and removing
the leaving one, and tracks the matched count incrementally. Two implementations reaching the
same numbers by the same steps would be one implementation written twice, and would agree even
where both are wrong.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from src.complete.absence import RetrievedChunk
from src.complete.references import R_ACT, R_ANX, R_ART, R_SUB
from src.retrieve.tokenize import primary_tokens

# This implementation's own handle on the four committed shapes, used as compiled and therefore
# case-sensitively, per section 5.1. Importing src/complete/references.py is not a breach of
# section 5.3: that section bars the two implementations from importing EACH OTHER, and this is a
# third module both may read, exactly as src.ingest.normalize and src.retrieve.tokenize are.
FLAG_REFERENCE_PATTERNS = (R_ART, R_ANX, R_SUB, R_ACT)

# The section 5.2 candidates, this implementation's own copy, named at one site.
FLAG_OVERLAP_THRESHOLD = 0.75
FLAG_SHORT_UNIT_LENGTH = 4
FLAG_SHORT_UNIT_THRESHOLD = 1.0


def flag_threshold_for(n_tokens: int) -> float:
    return FLAG_SHORT_UNIT_THRESHOLD if n_tokens < FLAG_SHORT_UNIT_LENGTH else FLAG_OVERLAP_THRESHOLD


def flag_rendered_block(chunk: RetrievedChunk) -> str:
    """The per-chunk string the request carries, which is the surface section 5.1 names.

    Written out here rather than imported from the assembler for the same reason the grader
    writes it out: render_context returns the whole context joined and this module must treat
    each block separately. A test asserts both copies against render_context itself.
    """
    return f"[{chunk.chunk_id}] {chunk.unit_label}\n{chunk.text}"


def flag_surfaces(text: str) -> list[tuple[str, ...]]:
    """Reference surfaces as captured groups, accumulated per pattern in a list.

    A list of tuples rather than the grader's frozenset, and compared below by an all() over
    membership rather than by a subset operator. The comparison is the same relation reached a
    different way, which is the point of there being two implementations at all.
    """
    out: list[tuple[str, ...]] = []
    for index, pattern in enumerate(FLAG_REFERENCE_PATTERNS):
        for match in pattern.finditer(text):
            key = (str(index),) + tuple(match.groups())
            if key not in out:
                out.append(key)
    return out


def block_admits(unit_surfaces: list[tuple[str, ...]], block: str) -> bool:
    """The section 5.1 reference condition, scoped to the block and never to the window."""
    if not unit_surfaces:
        return True
    present = flag_surfaces(block)
    return all(surface in present for surface in unit_surfaces)


def best_overlap(unit_tokens: Sequence[str], chunk_tokens: Sequence[str]) -> float:
    """Best containment of the unit in any window of one chunk, by a rolling multiset.

    `matched` is the size of the multiset intersection of the current window with the unit. A
    token entering the window increments it only while the window still holds fewer copies of
    that token than the unit needs; a token leaving decrements it under the mirror condition.
    """
    n = len(unit_tokens)
    if n == 0 or len(chunk_tokens) < n:
        return 0.0
    need = Counter(unit_tokens)
    have: Counter[str] = Counter()
    matched = 0
    best = 0
    for index, token in enumerate(chunk_tokens):
        if have[token] < need.get(token, 0):
            matched += 1
        have[token] += 1
        if index >= n:
            leaving = chunk_tokens[index - n]
            have[leaving] -= 1
            if have[leaving] < need.get(leaving, 0):
                matched -= 1
        if index >= n - 1 and matched > best:
            best = matched
            if best == n:
                break
    return best / n


def unit_is_supported(unit: str, chunks: Sequence[RetrievedChunk]) -> bool:
    """Whether the layer considers one claim unit supported by the context it was answered from.

    THE REFERENCE CONDITION IS A PRECHECK PER CHUNK, AHEAD OF THE ROLLING STRUCTURE. A block the
    unit's references do not admit is skipped before best_overlap is entered at all, so the
    rolling multiset is untouched by the condition: it still knows only `matched` and still never
    materialises a window. Putting the test inside the loop would have meant materialising each
    window to read surfaces out of it, which would have made this implementation a copy of the
    grader's and cost the independence section 5.3 requires.
    """
    unit_tokens = primary_tokens(unit)
    if not unit_tokens:
        return False
    surfaces = flag_surfaces(unit)
    threshold = flag_threshold_for(len(unit_tokens))
    for chunk in chunks:
        block = flag_rendered_block(chunk)
        if not block_admits(surfaces, block):
            continue
        if best_overlap(unit_tokens, primary_tokens(block)) >= threshold:
            return True
    return False


def flagged_units(answer: str, chunks: Sequence[RetrievedChunk]) -> tuple[str, ...]:
    """The claim units the layer flags as unsupported, in the answer's own order.

    This tuple is what src/generate/assemble.py renders into the second-call prompt as the
    statements the context did not support.
    """
    from src.score.claims import claim_units

    return tuple(u for u in claim_units(answer) if not unit_is_supported(u, chunks))


__all__ = [
    "FLAG_OVERLAP_THRESHOLD",
    "FLAG_REFERENCE_PATTERNS",
    "FLAG_SHORT_UNIT_LENGTH",
    "FLAG_SHORT_UNIT_THRESHOLD",
    "best_overlap",
    "block_admits",
    "flag_rendered_block",
    "flag_surfaces",
    "flag_threshold_for",
    "flagged_units",
    "unit_is_supported",
]
