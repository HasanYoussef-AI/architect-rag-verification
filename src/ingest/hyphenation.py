"""Resolving the U+FFFE line-break hyphen, with evidence rather than a default.

Two defects are corrected here. Both are recorded because the repository's value
depends on them being visible rather than tidied away.

DEFECT 1, the unsafe default. The original rule said: delete U+FFFE, validating
only that a letter sits on both sides. That precondition looked like a safety
check but was not one, because a REAL hyphen in a compound such as
"third-party" also has letters on both sides. PDFium encodes any hyphen falling
at a line break as U+FFFE, so deleting produced "thirdparty". The
exact-substring assertion could not catch it: the corrupted text was faithfully
carried into the chunk. Only cross-document evidence exposed it.

DEFECT 2, an ordering bug between discard removal and character normalisation.
Hyphen resolution originally ran on the RAW text, before discard lines were
removed. A word split across a PAGE boundary has its continuation after the page
footer and the running header:

    "...for exam<U+FFFE>Page 15 \f NIST AI 100-1 AI RMF 1.0 ple, how a human..."

Reading the neighbour from raw text yields "exam" and "Page" rather than "exam"
and "ple". Constraining neighbours to one physical line would NOT fix this,
because the continuation legitimately lives on the next page. The fix is
ordering: resolution runs on text already assembled from content lines, with
discards removed, and skips the line break between the fragments.

The corrected decision procedure, per occurrence, with NO silent default:

  1. Non-letter neighbour -> real hyphen. Structurally decisive, since a
     discretionary hyphen only ever appears between letters inside one word.
     Corroborated against poppler and pdfminer.
  2. Letters both sides -> look for positive evidence in BOTH directions across
     the WHOLE corpus, with every line-break hyphen masked so no occurrence can
     be evidence about itself.
  3. Exactly one direction attested -> take it, record the evidence.
  4. Both attested -> an explicitly recorded TIE-BREAK, not evidence. Prefer the
     hyphenated form (the Group A rule), because the discretionary hyphen renders
     as a hyphen on the published page, so this reproduces the source's visible
     text rather than a joined form that never appears. The failure mode is a
     spurious hyphen inside a word, which is far less damaging to lexical and
     semantic retrieval than silently welding two words together.
  5. Neither attested -> the vendored English wordlist decides, evidence source
     four (src/ingest/wordlist.py), by the fragment test in _resolve_by_wordlist.
     A syllable break always leaves at least one fragment that is not a word,
     "cooper" + "ation", "nonethe" + "less", so the joined form being a dictionary
     word is necessary but not sufficient to delete: at least one fragment must
     also fail the lookup, which is the signature of a typesetting break rather
     than a real hyphen. Three outcomes, the third labelled distinctly as a
     tie-break rather than evidence:
       joined form not a word              -> real hyphen, keep;
       joined a word, a fragment is not    -> syllable break, delete;
       joined a word, both fragments words -> ambiguous compound, keep (TIE-BREAK).
     This is a mechanical lookup in a committed, checksummed artifact, not a
     judgment about English, which is why it does not violate the
     no-reconstruction rule the way morphological judgment would. Known
     limitation, stated rather than discovered: a syllable break whose two
     fragments both happen to be words, "the" + "rapist" for "therapist", is
     wrongly kept by the tie-break. That fails in the safe direction, a spurious
     hyphen inside a word rather than two welded words, and corpus attestation
     catches an ambiguous compound whenever it appears elsewhere in the corpus.

This is reproduction with a recorded tie-break and a last-resort wordlist lookup,
not normalisation. Corpus frequency is evidence about which character the PDF
encoded at a position, never licence to standardise the corpus toward a majority
form.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from src.ingest.pdf_extract import SOFT_HYPHEN_BREAK, extract_pages
from src.ingest.wordlist import load_wordlist

REPO_ROOT = Path(__file__).resolve().parents[2]

CORPUS_PDFS = (
    Path("corpus/nist_ai_rmf/raw/NIST.AI.100-1.pdf"),
    Path("corpus/nist_ai_rmf/raw/NIST.AI.600-1.pdf"),
    Path("corpus/nist_ai_rmf/raw/AI_RMF_Playbook.pdf"),
)

RULE_NON_LETTER = "non-letter neighbour, real hyphen, structurally decisive"
RULE_HYPHEN_ATTESTED = "hyphenated form attested elsewhere in corpus, real hyphen"
RULE_JOINED_ATTESTED = "joined form attested elsewhere in corpus, discretionary hyphen"
TIE_BREAK_BOTH = "TIE-BREAK, both forms attested, no position-specific evidence"
# Superseded by the wordlist tier below: the neither-attested case is now decided
# by the vendored wordlist, so this sentinel is retained only for reference.
TIE_BREAK_NEITHER = "TIE-BREAK, neither form attested, no evidence available"
RULE_WORDLIST_JOINED = "joined form a word and a fragment is not, syllable break, delete"
RULE_WORDLIST_HYPHEN = "joined form absent from vendored wordlist, real hyphen"
TIE_BREAK_WORDLIST_BOTH = "TIE-BREAK, joined form and both fragments are words, ambiguous compound"

HYPHEN = "-"
DELETE = ""

# Rules backed by corpus attestation or structure. The wordlist rules are a
# distinct, weaker evidence tier and are deliberately not folded in here.
_EVIDENCE_RULES = frozenset({RULE_NON_LETTER, RULE_HYPHEN_ATTESTED, RULE_JOINED_ATTESTED})
_WORDLIST_RULES = frozenset({RULE_WORDLIST_JOINED, RULE_WORDLIST_HYPHEN, TIE_BREAK_WORDLIST_BOTH})


@dataclass(frozen=True)
class Decision:
    doc_id: str
    left: str
    right: str
    hyphenated: str
    joined: str
    hyphen_evidence: int
    joined_evidence: int
    rule: str
    outcome: str
    evidence_based: bool
    sentence: str


@lru_cache(maxsize=1)
def evidence_text() -> str:
    """All corpus text with every line-break hyphen masked.

    Masking is essential: an occurrence at a line break must never count as
    evidence about itself or about any other occurrence.
    """
    parts = []
    for pdf in CORPUS_PDFS:
        raw = "\n".join(extract_pages(REPO_ROOT / pdf))
        parts.append(re.sub(r"\s+", " ", raw.replace(SOFT_HYPHEN_BREAK, "\x00")))
    return " ".join(parts)


def _count(pattern: str) -> int:
    return len(re.findall(rf"(?<![A-Za-z]){re.escape(pattern)}(?![A-Za-z])", evidence_text(), re.I))


# The continuation of a word split at a line break may sit after a newline, once
# discard lines have been removed. Whitespace between the fragments is consumed.
_RIGHT = re.compile(r"\s*([A-Za-z]+)")


def _resolve_by_wordlist(left: str, right: str) -> tuple[str, str]:
    """Evidence source four, for the residue with no corpus attestation.

    A syllable break always leaves at least one fragment that is not a word:
    "cooper" + "ation", "nonethe" + "less", "quanti" + "ties". A genuine compound
    has both fragments as words: "round" + "trip", "non" + "inclusive". So the
    joined form being a dictionary word is necessary but not sufficient to delete;
    at least one fragment must also fail the lookup, which is the signature of a
    typesetting break rather than a real hyphen.

    Three outcomes:
      joined form not a word              -> real hyphen, keep (evidence);
      joined a word, a fragment is not    -> syllable break, delete (evidence);
      joined a word, both fragments words -> ambiguous compound, keep (TIE-BREAK).

    Known limitation, recorded rather than discovered: a syllable break whose two
    fragments both happen to be words, "the" + "rapist" for "therapist", is
    wrongly kept by the tie-break. That fails in the safe direction, a spurious
    hyphen inside a word rather than two welded words.
    """
    words = load_wordlist()
    if f"{left}{right}".lower() not in words:
        return RULE_WORDLIST_HYPHEN, HYPHEN
    if left.lower() in words and right.lower() in words:
        return TIE_BREAK_WORDLIST_BOTH, HYPHEN
    return RULE_WORDLIST_JOINED, DELETE


def resolve(text: str, doc_id: str) -> tuple[str, list[Decision]]:
    """Resolve every U+FFFE in text already assembled from CONTENT lines.

    Must not be called on raw text: see DEFECT 2 in the module docstring.
    """
    decisions: list[Decision] = []
    out: list[str] = []
    cursor = 0
    for match in re.finditer(re.escape(SOFT_HYPHEN_BREAK), text):
        left_match = re.search(r"[A-Za-z]+$", text[: match.start()])
        left = left_match.group(0) if left_match else ""
        right_match = _RIGHT.match(text[match.end() :])
        right = right_match.group(1) if right_match else ""
        consumed = right_match.end() if right_match else 0

        before = text[match.start() - 1] if match.start() else ""
        sentence = re.sub(r"\s+", " ", text[max(0, match.start() - 70) : match.end() + 70])

        if not (before.isalpha() and right):
            rule, outcome, hyp_n, join_n = RULE_NON_LETTER, HYPHEN, 0, 0
            consumed = 0
        else:
            hyp_n = _count(f"{left}-{right}")
            join_n = _count(f"{left}{right}")
            if hyp_n and not join_n:
                rule, outcome = RULE_HYPHEN_ATTESTED, HYPHEN
            elif join_n and not hyp_n:
                rule, outcome = RULE_JOINED_ATTESTED, DELETE
            elif hyp_n and join_n:
                rule, outcome = TIE_BREAK_BOTH, HYPHEN
            else:
                rule, outcome = _resolve_by_wordlist(left, right)
            consumed = right_match.start(1)

        decisions.append(
            Decision(
                doc_id=doc_id,
                left=left,
                right=right,
                hyphenated=f"{left}-{right}",
                joined=f"{left}{right}",
                hyphen_evidence=hyp_n,
                joined_evidence=join_n,
                rule=rule,
                outcome=outcome,
                evidence_based=rule in _EVIDENCE_RULES,
                sentence=sentence,
            )
        )
        out.append(text[cursor : match.start()])
        out.append(outcome)
        cursor = match.end() + consumed
    out.append(text[cursor:])
    return "".join(out), decisions


def decisions_as_dicts(decisions: list[Decision]) -> list[dict]:
    return [asdict(d) for d in decisions]
