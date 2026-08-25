"""Cross-reference candidate extraction for the EU AI Act.

What this is, stated in full because the limits matter more than the feature.

HIGH-PRECISION CANDIDATE EXTRACTION. Derived by regular expression from the
document's prose, not read from publisher markup: the Official Journal HTML
hyperlinks only footnotes, so Article and Annex cross-references exist purely as
text. Precision is validated by a full audit of every emitted edge. Recall is
deliberately sacrificed for precision. Every edge that enters a pre-registered
gold set is individually read and verified at the point of use.

This is NOT the complete cross-reference structure of the Act and must never be
described as such.

Why the rule is conservative rather than clever
-----------------------------------------------
The graph is a candidate generator for roughly 16 multi-hop query pairs, drawn
from several hundred true internal edges. Recall is in large surplus; precision
is the scarce resource. A conservative rule that discards a sixth of the edges
still leaves hundreds of candidates, while a single false edge inside a gold set
corrupts the ground-truth claim the repository is built on. So the rule is
structural rather than fitted to the specific errors observed during
development, which would leave every unobserved failure mode live.

Decision procedure, in precedence order, for each reference found:

  1. Explicitly qualified "of this Regulation"  -> internal.
     Unambiguous positive evidence, and it outranks rule 4 because the doubt
     that rule 4 exists to resolve is already settled by the text itself.
  2. Explicitly qualified with a named external instrument -> external.
  3. Inside an Article whose heading declares it amends an external instrument
     -> dropped. Such articles carry bare references to the amended instrument
     with no in-sentence qualifier, so no sentence-level rule can catch them.
     Articles amending this Act, "Amendments to Annex III", are unaffected.
  4. Any external instrument named anywhere in the same sentence -> dropped.
     Covers anaphora such as "that Regulation" and qualifiers distributed
     across an enumeration.
  5. Otherwise -> internal. The Act refers to its own provisions without
     qualification, so an unqualified reference in a sentence that names no
     other instrument is the ordinary internal case.

Every drop is recorded with its sentence and reason so the conservatism is
auditable and the recall cost is visible rather than taken on faith.

Ranges are expanded: "Articles 102 to 109" yields 102 through 109 inclusive.
That is what the text denotes, not an inference added to it.
"""

from __future__ import annotations

import re

# Enumeration modifiers that may trail a number without ending the reference.
_MOD = r"""(?:
      \s*\(\d+\)
    | \s*\([a-z]{1,3}\)
    | \s*\([ivxlc]+\)
    | \s*,\s*points?
    | \s*,\s*paragraphs?\s*\d*
    | \s*,\s*(?:first|second|third|fourth)\s+subparagraph
    | \s*,\s*Sections?\s+[A-Z0-9]+
    | \s+to\s+\(\d+\)
)*"""

_ARTICLE_RE = re.compile(
    r"\bArticles?\s+(?P<num>\d+)" + _MOD
    + r"(?P<more>(?:\s*(?:,|and|or|to)\s*\d+" + _MOD + r")*)",
    re.VERBOSE,
)
_ANNEX_RE = re.compile(
    r"\bAnnexe?s?\s+(?P<num>[IVXLC]+)" + _MOD
    + r"(?P<more>(?:\s*(?:,|and|or|to)\s*[IVXLC]+" + _MOD + r")*)",
    re.VERBOSE,
)

# This Act, by its own number. Not an external instrument.
_SELF_BY_NUMBER = re.compile(r"Regulation\s*\(EU\)\s*2024/1689")

# Instrument nouns. An occurrence not preceded by "this" is an external
# instrument mention, which includes anaphora such as "that Regulation".
# Deliberately case-sensitive. EU drafting capitalises an instrument noun when
# it names an instrument, "Decision No 768/2008/EC", and leaves the ordinary
# English word lowercase, "deployers that make decisions". Matching case
# insensitively fired on the common noun and discarded plainly internal edges
# such as art_86 -> anx_III, which is over-conservative for no safety gain.
_INSTRUMENT_NOUN = re.compile(
    r"\b(?P<lead>[Tt]his|[Tt]hat|[Tt]he\s+said|[Tt]he\s+same|[Tt]hose|[Tt]hese)?\s*"
    r"(?P<noun>Regulations?|Directives?|Decisions?|Treaty|Treaties|Charter|Protocol)\b"
)

# Instruments named by acronym rather than by noun. The Act cites the Treaties
# this way constantly, "Article 16 TFEU", "Article 4(2) TEU", with no "of" and
# no instrument noun, so the noun pattern above cannot see them.
_INSTRUMENT_ACRONYM = re.compile(r"\b(?:TEU|TFEU|GDPR|ECHR|TRIPS)\b")

# The same acronyms appearing immediately after a reference, which makes the
# reference itself external rather than merely doubtful.
_ACRONYM_QUALIFIER = re.compile(r"^\s*,?\s*(?P<acronym>TEU|TFEU|GDPR|ECHR|TRIPS)\b")

# Adjacent qualifier immediately following a reference expression.
_SELF_QUALIFIER = re.compile(r"^\s*(?:,\s*)?(?:of|in|to|under)\s+this\s+Regulation\b", re.IGNORECASE)
_EXTERNAL_QUALIFIER = re.compile(
    r"^\s*(?:,\s*)?(?:of|to|in|under)\s+(?:the\s+)?"
    r"(?P<instrument>(?:that|the\s+said|the\s+same)\s+)?"
    r"(?P<noun>Regulations?|Directives?|Decisions?|Treaty|Treaties|Charter|Protocol)\b",
    re.IGNORECASE,
)

# A following reference expression bounds the adjacent-qualifier lookahead.
_NEXT_REF = re.compile(r"\b(?:Articles?|Annexe?s?)\s+(?:\d|[IVXLC])")
_LOOKAHEAD = 90

# Heading forms that declare an article amends another instrument.
_AMENDS_EXTERNAL = re.compile(
    r"^\s*Amendments?\s+to\s+(?:Regulation|Directive|Decision|Council|Commission)\b", re.IGNORECASE
)

# Sentence boundaries. Erring towards longer sentences makes the rule more
# conservative, which is the safe direction here.
_SENTENCE_SPLIT = re.compile(r"(?<=[.;])\s+(?=[A-Z(‘“])")

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

DROP_AMENDING_SCOPE = "inside an article amending an external instrument"
DROP_SENTENCE_INSTRUMENT = "external instrument named in the same sentence"


def amends_external_instrument(heading: str) -> bool:
    """True when an Article's own heading declares it amends another instrument.

    "Amendments to Regulation (EU) 2018/1139" is True.
    "Amendments to Annex III", which amends this Act, is False.
    """
    return bool(_AMENDS_EXTERNAL.match(heading or ""))


def _roman_to_int(value: str) -> int:
    total, previous = 0, 0
    for char in reversed(value.upper()):
        current = _ROMAN[char]
        total = total - current if current < previous else total + current
        previous = max(previous, current)
    return total


def _int_to_roman(value: int) -> str:
    table = [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
             (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for amount, symbol in table:
        while value >= amount:
            out.append(symbol)
            value -= amount
    return "".join(out)


def external_instruments_in(sentence: str) -> list[str]:
    """Instrument mentions in a sentence that are not this Regulation."""
    masked = _SELF_BY_NUMBER.sub(" ", sentence)
    found: list[str] = []
    for match in _INSTRUMENT_NOUN.finditer(masked):
        lead = (match.group("lead") or "").strip().lower()
        if lead == "this":
            continue
        found.append(re.sub(r"\s+", " ", match.group(0)).strip())
    found.extend(match.group(0) for match in _INSTRUMENT_ACRONYM.finditer(masked))
    return found


def split_sentences(text: str) -> list[tuple[int, str]]:
    """Split into (offset, sentence), respecting block boundaries first."""
    out: list[tuple[int, str]] = []
    cursor = 0
    for block in text.split("\n"):
        start = cursor
        for piece in _SENTENCE_SPLIT.split(block):
            index = text.find(piece, start)
            if index < 0:
                index = start
            out.append((index, piece))
            start = index + len(piece)
        cursor += len(block) + 1
    return out


def _expand(first: str, more: str, to_int, to_str) -> list[str]:
    values = [first]
    previous = first
    for connector, value in re.findall(r"(,|and|or|to)\s*(\d+|[IVXLC]+)", more, re.IGNORECASE):
        if connector.lower() == "to":
            values.extend(to_str(n) for n in range(to_int(previous) + 1, to_int(value) + 1))
        else:
            values.append(value)
        previous = value
    return values


def _adjacent_qualifier(sentence: str, end: int) -> tuple[str, str]:
    """Classify by the qualifier immediately following the reference."""
    window = sentence[end : end + _LOOKAHEAD]
    following = _NEXT_REF.search(window)
    if following:
        window = window[: following.start()]
    if _SELF_QUALIFIER.match(window):
        return "self", "this Regulation"
    acronym = _ACRONYM_QUALIFIER.match(window)
    if acronym:
        return "external", acronym.group("acronym")
    external = _EXTERNAL_QUALIFIER.match(window)
    if external:
        return "external", re.sub(r"\s+", " ", external.group(0)).strip(" ,")
    return "none", ""


def extract_references(
    text: str, doc_id: str = "eu_ai_act", amends_external: bool = False
) -> tuple[list[str], list[str], list[dict], list[dict]]:
    """Return (refs_internal, refs_external, refs_dropped, evidence)."""
    internal: set[str] = set()
    external: set[str] = set()
    dropped: list[dict] = []
    evidence: list[dict] = []

    for _, sentence in split_sentences(text):
        instruments = external_instruments_in(sentence)

        # B023 is silenced on the four lines below rather than the rule being dropped. This
        # closure captures `sentence` and `instruments` late, which is a real bug class, but it
        # is called only at the two finditer loops at the end of this iteration and is never
        # stored, returned or passed on, so the capture always resolves against the iteration
        # that created it. Verified by enumerating every call site.
        def handle(match, kind: str, to_int, to_str, prefix: str) -> None:
            verdict, qualifier = _adjacent_qualifier(sentence, match.end())  # noqa: B023
            members = _expand(match.group("num"), match.group("more") or "", to_int, to_str)
            ids = [f"{doc_id}:{prefix}{m}" for m in members]
            surface = re.sub(r"\s+", " ", match.group(0)).strip()
            context = re.sub(r"\s+", " ", sentence).strip()  # noqa: B023

            if verdict == "self":
                outcome, reason = "internal", "explicit 'of this Regulation'"
                internal.update(ids)
            elif verdict == "external":
                outcome, reason = "external", f"explicit qualifier: {qualifier}"
                external.update(f"{qualifier}: {kind} {m}" for m in members)
            elif amends_external:
                outcome, reason = "dropped", DROP_AMENDING_SCOPE
                dropped.extend(
                    {"ref": i, "reason": reason, "surface": surface, "sentence": context}
                    for i in ids
                )
            elif instruments:  # noqa: B023
                outcome = "dropped"
                reason = f"{DROP_SENTENCE_INSTRUMENT}: {instruments[0]}"  # noqa: B023
                dropped.extend(
                    {"ref": i, "reason": reason, "surface": surface, "sentence": context}
                    for i in ids
                )
            else:
                outcome, reason = "internal", "no competing instrument in sentence"
                internal.update(ids)

            evidence.append(
                {
                    "surface": surface,
                    "kind": kind,
                    "outcome": outcome,
                    "reason": reason,
                    "sentence": context,
                }
            )

        for match in _ARTICLE_RE.finditer(sentence):
            handle(match, "Article", int, str, "art_")
        for match in _ANNEX_RE.finditer(sentence):
            handle(match, "Annex", _roman_to_int, _int_to_roman, "anx_")

    return sorted(internal), sorted(external), dropped, evidence
