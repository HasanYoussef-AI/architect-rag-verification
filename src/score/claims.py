"""The claim-unit segmenter, the grader's first stage.

eval/generation_predictions.md section 4 defines the object this module produces. A claim unit
is a sentence, with each list item its own unit, and the segmentation is deterministic: no
model, no randomness, no dependency outside the committed tree. PREREGISTRATION.md's term for
the same object is an atomic claim, and the two denote the same thing.

EACH LIST ITEM IS ONE UNIT, WHOLE, even when it carries more than one sentence. Section 4 gives
two rules, a unit is a sentence and each list item is its own unit, and the second is read as
governing the first inside a list. The alternative reading, splitting a multi-sentence list item
into sentences, is rejected for a reason rather than by preference: list items in answers about
this corpus routinely lack terminal punctuation, so a sentence split inside a list would merge
adjacent items whenever one of them ended without a period, which is the failure the list rule
exists to prevent. The reading is recorded here because the sentence admits the other one.

THE EXCLUSION IS THE MARKER AND NOTHING ELSE, exactly as section 4 bounds it. A segment is not a
claim unit when it equals the marker after normalisation, or when it equals it after case folding
or after dropping a trailing period, which is the marker_variant form. The marker literal and the
normalisation are imported from src/generate/prompts.py rather than restated, so there is one
marker in this repository and one detector, and no wider exclusion can be added here without
changing a literal a test pins.

WHY THE ABBREVIATION LIST IS CLOSED AND FIXED NOW. It is fixed in this module before any answer
exists, and it is short. A list grown after seeing answers is a lever: every addition merges two
units into one and changes the denominator of every rate in the study.

THE SENTENCE FLOOR IS AN INSTRUMENT LIMIT. A sentence asserting two things is one unit, so an
answer right about one half and wrong about the other scores wholly one way. Finer decomposition
is not deterministic without a model and CLAUDE.md Rule 2 admits none into the grader of record.
"""

from __future__ import annotations

import re

from src.generate.prompts import MARKER, normalize_response

# A list item, at the start of a line: a dash or asterisk bullet, an arabic numeral with a dot or
# a close paren, or a single letter with a close paren or a dot. Parenthesised letters, "(a)", are
# included because the EU AI Act's own enumerated points are printed that way and answers copy the
# form.
LIST_MARKER = re.compile(r"^\s*(?:[-*]|\(?[0-9]{1,2}[.)]|\(?[a-zA-Z][.)])\s+")

# Sentence terminators. A candidate terminates only under the guards in _terminates below.
_TERMINATOR = frozenset(".?!")

# Fixed and closed, before any answer exists. Stored without their trailing period.
ABBREVIATIONS = frozenset(
    {
        "e.g", "i.e", "cf", "etc", "vs", "approx", "no", "nos",
        "art", "arts", "sec", "secs", "fig", "figs", "para", "paras", "pp",
    }
)

# The alphabetic run, dots included, immediately preceding a candidate terminator.
_PRECEDING_WORD = re.compile(r"[A-Za-z.]+$")


def _is_marker_form(segment: str) -> bool:
    """True for the marker and for its two variant forms, and for nothing else."""
    normalized = normalize_response(segment)
    if normalized == MARKER:
        return True
    return normalized.casefold().rstrip(".") == MARKER.casefold().rstrip(".")


def _terminates(text: str, index: int) -> bool:
    """Whether the terminator character at `index` ends a sentence.

    Three conditions, all of them necessary.

    FOLLOWED BY WHITESPACE OR END OF TEXT. This is the load-bearing guard for identifiers with
    internal periods: in "GOVERN 1.3" and "Article 9.3" the inner period is followed by a digit,
    so it is not a candidate at all.

    NOT A PERIOD BETWEEN TWO DIGITS. Defensive, and DELIBERATELY REDUNDANT against the condition
    above: a period between two digits is never followed by whitespace, so this guard cannot be
    the only thing standing between an identifier and a split. It is kept because it states the
    intent at the site rather than leaving it to be inferred from the whitespace rule, and
    tests/test_claims.py records that removing it alone reddens nothing.

    NOT CLOSING A FIXED ABBREVIATION. The preceding alphabetic run, dots included, is looked up
    in ABBREVIATIONS with its outer dots stripped, so both "e.g." and "Art." are caught.
    """
    char = text[index]
    if char not in _TERMINATOR:
        return False
    if index + 1 < len(text) and not text[index + 1].isspace():
        return False
    if (
        char == "."
        and 0 < index < len(text) - 1
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    ):
        return False
    if char == ".":
        match = _PRECEDING_WORD.search(text[:index])
        if match and match.group(0).strip(".").casefold() in ABBREVIATIONS:
            return False
    return True


def split_sentences(block: str) -> list[str]:
    """Split one prose block into sentences. Terminators are kept on the sentence."""
    out: list[str] = []
    start = 0
    for index in range(len(block)):
        if _terminates(block, index):
            piece = block[start : index + 1].strip()
            if piece:
                out.append(piece)
            start = index + 1
    tail = block[start:].strip()
    if tail:
        out.append(tail)
    return out


def segment(answer: str) -> list[str]:
    """Every segment of an answer, in order, marker segments included.

    Lines are classified first. A list-item line is one segment with its marker stripped; runs of
    non-list lines are joined with a single space and split into sentences.
    """
    segments: list[str] = []
    prose: list[str] = []

    def flush() -> None:
        if prose:
            segments.extend(split_sentences(" ".join(prose).strip()))
            prose.clear()

    for line in answer.splitlines():
        if not line.strip():
            flush()
            continue
        marker = LIST_MARKER.match(line)
        if marker:
            flush()
            item = line[marker.end() :].strip()
            if item:
                segments.append(item)
        else:
            prose.append(line.strip())
    flush()
    return segments


def claim_units(answer: str) -> list[str]:
    """The graded units of an answer: every segment that is not the marker or a variant of it."""
    return [s for s in segment(answer) if not _is_marker_form(s)]


__all__ = ["ABBREVIATIONS", "LIST_MARKER", "claim_units", "segment", "split_sentences"]
