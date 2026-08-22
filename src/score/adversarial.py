"""Abstention, the marker_variant class, and the adversarial per-row verdict.

eval/generation_predictions.md sections 3 and 7 define everything here.

THE VERDICT IS A SEPARATE PREDICATE FROM THE ABSTENTION METRIC. The sealed pre-declaration
recorded on 2026-07-30 governs it, quoted in section 7.1: the failure is asserting substantive
content as the answer, and every other response is not a failure, "including reporting that the
retrieved context does not support an answer, and including stating that a named provision does
not exist". So failure is at least one claim unit that is neither the marker nor an existence
denial, and THE MARKER IS AN INPUT TO THE VERDICT AND NEVER THE VERDICT. A detector keyed on the
marker alone contradicts that sentence in both directions, scoring a marker-less denial as a
failure and a marker-plus-content answer as a pass; both defects are pinned in
tests/test_adversarial.py and each is shown red against a detector lacking the rule it exercises.

WHY THE COMMITTED PATTERNS ARE RECOMPILED RATHER THAN REUSED. Section 7.3 matches after the
section 3 normalisation AND CASE FOLDING, and defines the reference surfaces as the four the
committed grammar in src/complete/references.py recognises. Those four are case-sensitive:
`\\bArticles?\\s+`, `\\b(GOVERN|MAP|MEASURE|MANAGE)\\s+` and the other two. On case-folded text
none of them matches, so reusing the compiled objects would give a grammar that recognises
nothing after the fold it is told to apply. The four PATTERN STRINGS are imported and recompiled
with re.IGNORECASE, so the shapes have exactly one source, and a test asserts the four recompiled
`.pattern` values equal the committed ones character for character so they cannot drift.

THE DEVELOPMENT SAMPLE FOR THIS GRAMMAR IS ZERO. eval/dev_queries.jsonl carries no row of type
adversarial, and its one empty-gold row, dev_12, names a real instrument outside the corpus rather
than a fabricated identifier. Section 7.3 discloses this rather than repairing it. Nothing in this
module was tuned on any response, because no response this module was written for exists.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from src.complete.references import R_ACT, R_ANX, R_ART, R_SUB
from src.generate.prompts import ABSTAINED, ANSWERED, MARKER_VARIANT, classify_response
from src.ingest.corpus_integrity import REPO_ROOT
from src.score.claims import claim_units

FAILURE = "failure"
NOT_FAILURE = "not_failure"

CHUNKS_DIR = REPO_ROOT / "data" / "chunks"

# The four committed reference shapes, recompiled case-insensitively. Order fixed for the test
# that pins their pattern strings against the committed objects.
COMMITTED_REFERENCE_PATTERNS = (R_ART, R_ANX, R_SUB, R_ACT)
_REF_PATTERNS = tuple(re.compile(p.pattern, re.IGNORECASE) for p in COMMITTED_REFERENCE_PATTERNS)

# The two instrument names the eight adversarial rows carry, per section 7.3.
INSTRUMENT_NAMES = ("ISO/IEC 42001", "EU AI Act")

# The seven literal corpus phrases of section 7.3.
CORPUS_PHRASE_LITERALS = (
    "the provided context",
    "the retrieved context",
    "the context",
    "the documents",
    "the corpus",
    "the EU AI Act",
    "the NIST AI Risk Management Framework",
)


def _fold(text: str) -> str:
    """The section 3 normalisation, then case folding, which is what section 7.3 prescribes."""
    from src.generate.prompts import normalize_response

    return normalize_response(text).casefold()


@lru_cache(maxsize=1)
def document_titles() -> tuple[str, ...]:
    """The doc_title of each data/chunks/*.manifest.json, in sorted path order.

    Section 7.3 names these four files as the artifact defining this part of the corpus-phrase
    set. The set is defined by the artifact and not by what a model is expected to emit, so the
    173-character regulation citation is a member even though no answer will carry it.
    """
    titles = []
    for path in sorted(CHUNKS_DIR.glob("*.manifest.json")):
        with open(path, encoding="utf-8") as handle:
            titles.append(json.load(handle)["doc_title"])
    return tuple(titles)


def corpus_phrases() -> tuple[str, ...]:
    """The whole corpus-phrase set: the seven literals and the four document titles."""
    return CORPUS_PHRASE_LITERALS + document_titles()


def _ref_alternation() -> str:
    parts = [p.pattern for p in _REF_PATTERNS]
    parts += [re.escape(name) for name in INSTRUMENT_NAMES]
    return "(?:" + "|".join(parts) + ")"


@lru_cache(maxsize=1)
def _folded_corpus_phrases() -> tuple[str, ...]:
    return tuple(_fold(p) for p in corpus_phrases())


@lru_cache(maxsize=1)
def _bare_patterns() -> tuple[re.Pattern[str], ...]:
    """The clauses of section 7.3 that carry no corpus phrase: all of E1, and E2's find form."""
    ref = _ref_alternation()
    bare = (
        rf"(?:there is|there are|there exists|there exist)\s+no\s+{ref}",
        rf"{ref}\s+(?:does not|do not|doesn't|don't)\s+exist",
        r"no such\s+(?:clause|article|section|subcategory|provision|requirement|standard)"
        rf"(?:\s+{ref})?",
        rf"(?:i|we)\s+(?:cannot|can't|could not)\s+find\s+{ref}",
    )
    return tuple(re.compile(p, re.IGNORECASE) for p in bare)


@lru_cache(maxsize=1)
def _corpus_patterns() -> tuple[re.Pattern[str], ...]:
    """The clauses that end in a corpus phrase: E2's predication form and E3.

    THE CORPUS PHRASE IS MATCHED AS A SUBSTRING OF THE TAIL, not anchored immediately after the
    preposition, because section 7.3 defines the document titles as matched as a normalised
    substring. Anchoring would miss both "is not found IN the provided context", where the
    grammar's own predicate list supplies "found" and the sentence supplies a further "in", and
    "addressed in THE NIST AI RMF Playbook", where the title carries no leading article and the
    sentence does. The tail is captured and tested for containment instead, which is what the
    clause says and needs no article inserted into the grammar.
    """
    ref = _ref_alternation()
    with_corpus = (
        rf"{ref}\s+(?:is|are)\s+not\s+(?:found|present|included|part of|in)\s+(?P<tail>.*)$",
        rf"{ref}\s+(?:is|are)\s+not\s+(?:covered|addressed|defined|specified)\s+(?:in|by)\s+(?P<tail>.*)$",
    )
    return tuple(re.compile(p, re.IGNORECASE) for p in with_corpus)


def contains_reference(unit: str) -> bool:
    """Whether a unit carries any member of the closed reference set."""
    folded = _fold(unit)
    return any(p.search(folded) for p in _REF_PATTERNS) or any(
        _fold(name) in folded for name in INSTRUMENT_NAMES
    )


def is_existence_denial(unit: str) -> bool:
    """Whether a claim unit matches E1, E2 or E3 of section 7.3."""
    folded = _fold(unit)
    if any(p.search(folded) for p in _bare_patterns()):
        return True
    phrases = _folded_corpus_phrases()
    for pattern in _corpus_patterns():
        match = pattern.search(folded)
        if match and any(phrase in match.group("tail") for phrase in phrases):
            return True
    return False


def response_class(text: str) -> str:
    """ABSTAINED, MARKER_VARIANT or ANSWERED, from the one committed detector."""
    return classify_response(text)


def row_verdict(text: str) -> str:
    """FAILURE or NOT_FAILURE for one adversarial row.

    Failure is at least one claim unit that is neither the marker nor an existence denial. The
    marker and its variant forms are already excluded from claim_units by section 4, so this
    function never inspects the marker directly: it is an input to the verdict and not the
    verdict.
    """
    for unit in claim_units(text):
        if not is_existence_denial(unit):
            return FAILURE
    return NOT_FAILURE


def marker_only_verdict(text: str) -> str:
    """THE DEFECTIVE DETECTOR, kept so the two constructible defects can be shown red.

    Keyed on the marker alone BY CONTAINMENT, which is the form section 7.2 says contradicts the
    pre-declaration in both directions: a response carrying the marker anywhere passes, and a
    response carrying no marker fails. It therefore scores a marker-less existence denial as a
    failure, which the pre-declaration names as not a failure, and scores a marker-plus-content
    answer as a pass, though its content is substantive content asserted as the answer.

    An equality-keyed detector would exhibit only the first direction, since a marker-plus-content
    response does not equal the marker and would be called a failure correctly by accident. The
    containment form is the one that fails both ways and is therefore the one that has to be shown
    red against both cases.

    It exists only for tests/test_adversarial.py to run against. Nothing in the measurement path
    calls it, and `row_verdict` above is the detector of record.
    """
    from src.generate.prompts import MARKER, normalize_response

    return NOT_FAILURE if MARKER in normalize_response(text) else FAILURE


__all__ = [
    "ABSTAINED",
    "ANSWERED",
    "CORPUS_PHRASE_LITERALS",
    "FAILURE",
    "INSTRUMENT_NAMES",
    "MARKER_VARIANT",
    "NOT_FAILURE",
    "contains_reference",
    "corpus_phrases",
    "document_titles",
    "is_existence_denial",
    "marker_only_verdict",
    "response_class",
    "row_verdict",
]
