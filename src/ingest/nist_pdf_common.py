"""Shared machinery for NIST PDF ingestion.

Used by the AI 600-1 and Playbook ingesters. AI 100-1 keeps its own copies of
the equivalent helpers deliberately: its output is already committed and cited,
and refactoring it to import from here would risk changing bytes for no gain.

The three guarantees carried over from AI 100-1 are the reason this module
exists at all: a partition proof over the full raw extraction, structure-derived
identifiers, and an exact-substring assertion that makes text reconstruction
detectable rather than merely discouraged.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.ingest.hyphenation import resolve
from src.ingest.normalize import normalize_block
from src.ingest.pdf_extract import PAGE_SEPARATOR, extract_pages
from src.ingest.tokenization import MAX_TOKENS, count_tokens

BLOCK_SEPARATOR = "\n"
UNIT_SEPARATOR = "\n\n"


class IngestError(RuntimeError):
    """Raised when a document does not parse as declared. Fails loudly by design."""


@dataclass
class Line:
    page: int
    text: str
    kind: str = "content"


@dataclass
class Unit:
    unit_key: str
    unit_type: str
    label: str
    heading: str
    structural_path: list[str]
    lines: list[Line] = field(default_factory=list)


def build_lines(pages: list[str]) -> tuple[str, list[Line]]:
    """Raw text plus a line inventory of the non-blank, stripped lines."""
    raw = PAGE_SEPARATOR.join(pages)
    lines = [
        Line(page_number, piece.strip())
        for page_number, page in enumerate(pages, start=1)
        for piece in page.split("\n")
        if piece.strip()
    ]
    return raw, lines


def structural_whitespace(pages: list[str]) -> Counter:
    """Characters between the raw text and the stripped line inventory.

    Kept as an explicit class so the partition proof covers raw_chars rather
    than a derived intermediate, and nothing can hide in the difference.
    """
    counts: Counter = Counter()
    for page in pages:
        parts = page.split("\n")
        counts["intra_page_newlines"] += len(parts) - 1
        for piece in parts:
            if piece.strip():
                counts["stripped_line_whitespace"] += len(piece) - len(piece.strip())
            else:
                counts["blank_line_chars"] += len(piece)
    counts["page_separators"] = len(PAGE_SEPARATOR) * (len(pages) - 1)
    return counts


def partition_proof(raw: str, pages: list[str], lines: list[Line], units: list[Unit]) -> dict:
    """Assert every raw character is content in one unit, a named discard, or whitespace."""
    assigned = {id(line) for unit in units for line in unit.lines}
    content = [line for line in lines if line.kind == "content"]
    unassigned = [line for line in content if id(line) not in assigned]
    duplicated = len([line for unit in units for line in unit.lines]) - len(assigned)

    discards: Counter = Counter()
    for line in lines:
        if line.kind != "content":
            discards[line.kind] += len(line.text)
    content_chars = sum(len(line.text) for line in content)
    ws = structural_whitespace(pages)
    ws_total = sum(ws.values())
    accounted = content_chars + sum(discards.values()) + ws_total

    if unassigned:
        raise IngestError(
            f"partition incomplete, {len(unassigned)} content lines assigned to no unit, "
            f"first: {unassigned[0].text[:110]!r}"
        )
    if duplicated:
        raise IngestError(f"partition overlaps, {duplicated} lines assigned more than once")
    if accounted != len(raw):
        raise IngestError(
            f"partition does not account for the full raw extraction: {accounted} of {len(raw)}"
        )

    line_chars = sum(len(line.text) for line in lines)
    return {
        "raw_chars": len(raw),
        "raw_chars_accounted": accounted,
        "raw_fully_accounted": True,
        "line_chars": line_chars,
        "content_chars": content_chars,
        "assigned_to_units_chars": sum(len(line.text) for unit in units for line in unit.lines),
        "unassigned_content_lines": 0,
        "lines_assigned_more_than_once": 0,
        "discarded_chars_by_class": dict(sorted(discards.items())),
        "discarded_chars_total": sum(discards.values()),
        "discarded_fraction_of_lines": round(sum(discards.values()) / line_chars, 4),
        "structural_whitespace_by_class": dict(sorted(ws.items())),
        "structural_whitespace_total": ws_total,
        "complete": True,
    }


def resolved_document_text(abs_path, doc_id: str) -> str:
    """Whole-document text with U+FFFE resolved, for cross-document identifier match.

    Used to derive structural_join edges by the same printed-identifier search
    another document uses, so the relation is symmetric and derived by one rule
    rather than special-cased per document.
    """
    resolved, _ = resolve("\n".join(extract_pages(abs_path)), doc_id)
    return resolved


def resolve_unit_blocks(unit: Unit, doc_id: str) -> tuple[list[str], list]:
    """Resolve U+FFFE across the whole unit, then split back into normalised blocks.

    Resolving per unit rather than per line lets a word split at a line break
    rejoin across the discarded lines between its fragments. The resolver reads
    neighbours within the text it is given, but its corpus attestation is always
    corpus-wide (src.ingest.hyphenation.evidence_text over all three PDFs), so the
    decisions match the committed corpus-wide decision log regardless of scope.
    Returns the non-empty normalised blocks and the resolver's decisions.
    """
    resolved, decisions = resolve(BLOCK_SEPARATOR.join(line.text for line in unit.lines), doc_id)
    blocks = [normalize_block(block) for block in resolved.split(BLOCK_SEPARATOR)]
    return [block for block in blocks if block], decisions


def pack(blocks: list[str]) -> list[list[int]]:
    """Greedy pack block indices under the token cap, never splitting mid-block."""
    groups: list[list[int]] = []
    current: list[int] = []
    for index, block in enumerate(blocks):
        candidate = current + [index]
        if count_tokens(BLOCK_SEPARATOR.join(blocks[i] for i in candidate)) <= MAX_TOKENS:
            current = candidate
            continue
        if current:
            groups.append(current)
        if count_tokens(block) > MAX_TOKENS:
            raise IngestError(f"block exceeds the cap on its own: {block[:110]!r}")
        current = [index]
    if current:
        groups.append(current)
    return groups


def write_jsonl_dicts(records: list[dict], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for r in records
    ).encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Prose cross-reference classification, three classes.
#
# Two classes are not enough for these documents. "See Appendix A of the AI RMF"
# points at AI 100-1's Appendix A, which is a real unit in this corpus: it is
# neither internal to the citing document nor external to the corpus, and
# collapsing it into either bucket loses a genuine cross-document pointer.
# ---------------------------------------------------------------------------

INTERNAL = "internal"
CROSS_DOCUMENT = "cross_document"
EXTERNAL = "external"

_PROSE_REF = re.compile(r"\b(?P<kind>Section|Appendix|Table|Figure)\s+(?P<id>[A-Z]|\d+(?:\.\d+)*)\b")

# Instrument names. External is outside the corpus; corpus is the AI RMF Core,
# whose appendices resolve into AI 100-1. A qualifier only counts when it is
# CONNECTED to the reference: "of the AI RMF" following it, or the instrument
# named immediately before it, "AI Risk Management Framework, Appendix A" or
# "ISO/IEC CD 5339. See Section 6". A mere nearby mention in a separate clause,
# "(see Appendix A), AI RMF subcategories not addressed", does not qualify, so
# that Appendix A stays internal.
_INSTR_EXTERNAL = (
    r"(EO\s*\d+|Executive\s+Order(?:\s*\d+)?|ISO(?:/IEC)?(?:\s+[A-Z]{1,3})?\s*\d+|OECD|"
    r"NIST\s+SP\s*[\d\-.]+)"
)
_INSTR_CORPUS = (
    r"((?:Artificial\s+Intelligence|AI)\s+Risk\s+Management\s+Framework|AI\s+RMF(?:\s+1\.0)?|"
    r"NIST\s+AI\s+100-1)"
)
_EXTERNAL_AFTER = re.compile(r"[\s\w().,'-]{0,20}\bof\s+(?:the\s+)?" + _INSTR_EXTERNAL, re.IGNORECASE)
_CORPUS_AFTER = re.compile(r"[\s\w().,'-]{0,20}\bof\s+(?:the\s+)?" + _INSTR_CORPUS, re.IGNORECASE)
_EXTERNAL_BEFORE = re.compile(_INSTR_EXTERNAL + r"[\s,.]{1,6}(?:See\s+)?$", re.IGNORECASE)
_CORPUS_BEFORE = re.compile(_INSTR_CORPUS + r"[\s,.]{1,6}(?:See\s+)?$", re.IGNORECASE)


def classify_prose_reference(sentence: str, start: int, end: int) -> tuple[str, str]:
    """Return (class, detail) by the instrument connected to the reference.

    The qualifier must follow via "of (the) X" or immediately precede the
    reference; a nearby mention in a separate clause does not qualify. External
    takes precedence over a corpus-document mention. Neither present means internal.
    """
    before = sentence[max(0, start - 60) : start]
    after = sentence[end : end + 40]
    external = _EXTERNAL_AFTER.match(after) or _EXTERNAL_BEFORE.search(before)
    if external:
        return EXTERNAL, re.sub(r"\s+", " ", external.group(1)).strip()
    corpus_doc = _CORPUS_AFTER.match(after) or _CORPUS_BEFORE.search(before)
    if corpus_doc:
        return CROSS_DOCUMENT, re.sub(r"\s+", " ", corpus_doc.group(1)).strip()
    return INTERNAL, ""


def find_prose_references(text: str):
    """Yield (match, kind, identifier) for every prose reference expression."""
    for match in _PROSE_REF.finditer(text):
        yield match, match.group("kind"), match.group("id")
