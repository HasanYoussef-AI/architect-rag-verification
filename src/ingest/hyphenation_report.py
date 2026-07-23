"""Decision log for the U+FFFE hyphen resolver across the whole corpus.

Runs hyphenation.resolve over all three NIST documents and records, for every
occurrence, the fragments, the corpus evidence counts, the rule that fired, the
outcome, and the evidence tier. This is an analysis artifact for audit and
review, not part of document ingestion: it produces no chunks, no manifest and no
normalised text, and it changes no document output. It exists so the weakest
evidence tier, the wordlist, can be reviewed in full.

Faithful assembly. resolve must see text with discards removed between a marker
and its continuation (DEFECT 2 in hyphenation.py). Across the whole corpus that
happens only twice, both in AI 100-1, where PDFium appends a page footer to the
end of a content line and the running header then follows on the next page. Those
two interruptions are collapsed here from the committed constants, so all 239
AI 100-1 markers keep correct fragments. AI 600-1 and the Playbook have no such
case, so their raw extracted text already gives correct fragments for every
occurrence, which is why running on raw text is faithful for them and covers all
337 occurrences corpus-wide.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.hyphenation import (
    RULE_HYPHEN_ATTESTED,
    RULE_JOINED_ATTESTED,
    RULE_NON_LETTER,
    RULE_WORDLIST_HYPHEN,
    RULE_WORDLIST_JOINED,
    TIE_BREAK_BOTH,
    TIE_BREAK_WORDLIST_BOTH,
    Decision,
    resolve,
)
from src.ingest.nist_ai_100_1 import RUNNING_HEADER
from src.ingest.pdf_extract import PAGE_SEPARATOR, SOFT_HYPHEN_BREAK, extract_pages

OUTPUT_DIR = REPO_ROOT / "data" / "hyphenation"

DOCS = (
    ("nist_ai_100_1", Path("corpus/nist_ai_rmf/raw/NIST.AI.100-1.pdf")),
    ("nist_ai_600_1", Path("corpus/nist_ai_rmf/raw/NIST.AI.600-1.pdf")),
    ("nist_playbook", Path("corpus/nist_ai_rmf/raw/AI_RMF_Playbook.pdf")),
)

# The two AI 100-1 page-boundary interruptions: a marker, then an appended page
# footer, the page separator, the running header, and the newline before the
# continuation. Collapsing this to the bare marker rejoins the fragments, the same
# net effect as the ingester's strip_footer_tails plus running-header discard.
_AI100_INTERRUPTION = re.compile(
    re.escape(SOFT_HYPHEN_BREAK) + r"Page\s+\d+.*?" + re.escape(RUNNING_HEADER) + r"\s*\n",
    re.DOTALL,
)

# Rule to evidence tier, for the by-tier breakdown.
_TIER = {
    RULE_NON_LETTER: "1_non_letter_neighbour",
    RULE_HYPHEN_ATTESTED: "2_corpus_attestation_one_direction",
    RULE_JOINED_ATTESTED: "2_corpus_attestation_one_direction",
    TIE_BREAK_BOTH: "3_both_attested_group_A",
    RULE_WORDLIST_JOINED: "4_wordlist",
    RULE_WORDLIST_HYPHEN: "4_wordlist",
    TIE_BREAK_WORDLIST_BOTH: "4_wordlist",
}

_WORDLIST_RULES = (RULE_WORDLIST_JOINED, RULE_WORDLIST_HYPHEN, TIE_BREAK_WORDLIST_BOTH)


def tier(rule: str) -> str:
    return _TIER.get(rule, "5_unresolved")


def resolvable_text(doc_id: str, path: Path) -> str:
    """Text for resolve: raw extraction, with the two AI 100-1 interruptions collapsed."""
    raw = PAGE_SEPARATOR.join(extract_pages(REPO_ROOT / path))
    if doc_id == "nist_ai_100_1":
        raw = _AI100_INTERRUPTION.sub(SOFT_HYPHEN_BREAK, raw)
    return raw


def all_decisions() -> list[Decision]:
    """Every U+FFFE decision across the corpus, in document then text order."""
    decisions: list[Decision] = []
    for doc_id, path in DOCS:
        _, doc_decisions = resolve(resolvable_text(doc_id, path), doc_id)
        decisions.extend(doc_decisions)
    return decisions


def build_jsonl(decisions: list[Decision]) -> bytes:
    """One row per occurrence, deterministic order, each tagged with its tier."""
    rows = []
    for decision in decisions:
        row = asdict(decision)
        row["tier"] = tier(decision.rule)
        rows.append(row)
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for row in rows
    ).encode("utf-8")


def build_summary(decisions: list[Decision]) -> dict:
    by_doc = {}
    for doc_id, _ in DOCS:
        doc_dec = [d for d in decisions if d.doc_id == doc_id]
        by_doc[doc_id] = {
            "occurrences": len(doc_dec),
            "by_tier": dict(sorted(Counter(tier(d.rule) for d in doc_dec).items())),
        }
    wordlist = [d for d in decisions if d.rule in _WORDLIST_RULES]
    return {
        "total_occurrences": len(decisions),
        "by_tier": dict(sorted(Counter(tier(d.rule) for d in decisions).items())),
        "by_document": by_doc,
        "wordlist_tier": {
            "total": len(wordlist),
            "delete_syllable_break": sum(1 for d in wordlist if d.rule == RULE_WORDLIST_JOINED),
            "keep_joined_not_a_word": sum(1 for d in wordlist if d.rule == RULE_WORDLIST_HYPHEN),
            "keep_ambiguous_compound_tie_break": sum(
                1 for d in wordlist if d.rule == TIE_BREAK_WORDLIST_BOTH
            ),
        },
    }


def write_artifacts() -> dict:
    decisions = all_decisions()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "decision_log.jsonl").write_bytes(build_jsonl(decisions))
    summary = build_summary(decisions)
    (OUTPUT_DIR / "decision_log.summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    print(json.dumps(write_artifacts(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
