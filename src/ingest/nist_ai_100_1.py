"""Structure-aware ingestion of NIST AI 100-1, the AI RMF 1.0.

The EU AI Act declared its own structure through ELI anchors. A PDF declares
nothing, so this module builds three independent guarantees instead.

1. Anchors are validated against the document's own Table of Contents. The TOC
   is the document's declaration of its structure, so a heading is accepted only
   if the document itself declares it. This also discriminates real headings
   from the enumerated list items in Appendices C and D, which look identical to
   section headings, "3. Use clear and plain language...", but appear in no TOC.

2. A partition proof. Every character of the extracted text is assigned either
   to exactly one unit or to an explicitly named discard class. No gaps, no
   overlaps, and the discarded fraction is reported per class. A runaway final
   unit shows up as an oversized span, and dropped content shows up as
   unassigned characters. Neither can hide.

3. Every chunk's text must be an exact substring of the persisted extracted text
   at its recorded offsets. Any sentence originating from anywhere other than
   the PDF fails this assertion mechanically, which is what makes the
   no-reconstruction rule enforced rather than promised.

Front matter with no printed identifier, the two cover pages, the Table of
Contents, and the Lists of Figures and Tables, is excluded into the discard
class rather than given an invented identifier. It remains in the committed raw
extraction, so nothing is lost from the audit trail.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.ingest.chunk_schema import Chunk, write_jsonl
from src.ingest.corpus_integrity import REPO_ROOT, sha256_file, verify_all
from src.ingest.hyphenation import resolve
from src.ingest.normalize import normalize_block
from src.ingest.pdf_extract import (
    PAGE_SEPARATOR,
    extract_pages,
    extractor_fingerprint,
    find_unjoinable_breaks,
    sha256_text,
)
from src.ingest.tokenization import MAX_TOKENS, count_tokens, tokenizer_fingerprint

DOC_ID = "nist_ai_100_1"
DOC_TITLE = "Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1"
SOURCE_PATH = Path("corpus/nist_ai_rmf/raw/NIST.AI.100-1.pdf")
OUTPUT_DIR = REPO_ROOT / "data" / "chunks"

BLOCK_SEPARATOR = "\n"
UNIT_SEPARATOR = "\n\n"

# Pages holding the cover, the notices, the TOC and the lists of figures and
# tables. Content proper begins with the Executive Summary.
FRONT_MATTER_PAGES = 5

RUNNING_HEADER = "NIST AI 100-1 AI RMF 1.0"
_PAGE_FOOTER = re.compile(r"^Page\s+\d+$")
_TABLE_CONTINUATION = re.compile(
    r"^(Continued on next page|Categories\s+Subcategories|"
    r"Table\s+\d+:.*\(Continued\)\s*)$"
)

# Core anchors inside sections 5.1 to 5.4.
_CATEGORY = re.compile(r"^(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+):\s*(.*)$")
_SUBCATEGORY = re.compile(r"^(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+\.\d+):\s*(.*)$")

_TOC_ENTRY = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d{1,3})$")


class IngestError(RuntimeError):
    """Raised when the document does not parse as declared. Fails loudly by design."""


@dataclass
class Line:
    page: int
    text: str
    start: int
    end: int
    kind: str = "content"  # or a discard class name
    tail: str = ""  # boilerplate stripped from the end of a content line


@dataclass
class Unit:
    unit_key: str
    unit_type: str
    label: str
    heading: str
    structural_path: list[str]
    lines: list[Line] = field(default_factory=list)


def build_lines(pages: list[str]) -> tuple[str, list[Line]]:
    """Raw text plus a line inventory with exact offsets into that raw text."""
    raw = PAGE_SEPARATOR.join(pages)
    lines: list[Line] = []
    cursor = 0
    for page_number, page in enumerate(pages, start=1):
        for piece in page.split("\n"):
            start = cursor
            cursor += len(piece) + 1
            if piece.strip():
                lines.append(Line(page_number, piece.strip(), start, start + len(piece)))
        cursor = cursor - 1 + len(PAGE_SEPARATOR)
    return raw, lines


# The page footer is normally its own line, but twice in this document PDFium
# appends it to the end of a content line, splitting a word across the page
# boundary: "...for exam<U+FFFE>Page 15". Line-level discard cannot catch that,
# so a trailing footer is stripped positionally and its characters are still
# accounted to the page_footer discard class.
_FOOTER_TAIL = re.compile(r"\s*Page\s+\d+\s*$")


def strip_footer_tails(lines: list[Line]) -> None:
    for line in lines:
        if line.kind != "content" or _PAGE_FOOTER.match(line.text):
            continue
        match = _FOOTER_TAIL.search(line.text)
        if match:
            line.tail = line.text[match.start():]
            line.text = line.text[: match.start()]


def classify_lines(lines: list[Line]) -> None:
    """Mark each line as content or as a named discard class."""
    for line in lines:
        if line.page <= FRONT_MATTER_PAGES:
            line.kind = "front_matter"
        elif line.text == RUNNING_HEADER:
            line.kind = "running_header"
        elif _PAGE_FOOTER.match(line.text):
            line.kind = "page_footer"
        elif _TABLE_CONTINUATION.match(line.text):
            line.kind = "table_continuation"
        else:
            line.kind = "content"


def parse_toc(pages: list[str]) -> list[tuple[str, str]]:
    """The document's own declared structure, from its Table of Contents.

    Returns (identifier, title) pairs. Identifier is the printed numbering where
    the document prints one, otherwise the printed heading itself.
    """
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for page in pages[:FRONT_MATTER_PAGES]:
        for raw_line in page.split("\n"):
            line = raw_line.strip()
            match = _TOC_ENTRY.match(line)
            if not match:
                continue
            title = match.group("title").strip()
            if title.startswith(("Fig.", "Table ")):
                continue
            part = re.match(r"^(Part\s+\d+):\s*(.+)$", title)
            appendix = re.match(r"^(Appendix\s+[A-Z]):\s*(.+)$", title)
            numbered = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)$", title)
            if part:
                key, name = part.group(1), part.group(2)
            elif appendix:
                key, name = appendix.group(1), appendix.group(2)
            elif numbered:
                key, name = numbered.group(1), numbered.group(2)
            elif title == "Executive Summary":
                key, name = title, title
            else:
                continue
            if key not in seen:
                seen.add(key)
                entries.append((key, name))
    return entries


def _heading_matches(line: str, key: str, title: str) -> bool:
    """Does a body line announce this declared heading?"""
    flat = re.sub(r"\s+", " ", line).strip()
    if key.startswith(("Part ", "Appendix ")):
        return flat.startswith(key + ":")
    if key == "Executive Summary":
        return flat == "Executive Summary"
    # Numbered sections print as "1." or "1" then the title.
    pattern = rf"^{re.escape(key)}\.?\s+{re.escape(title[:40])}"
    return bool(re.match(pattern, flat))


def locate_anchors(lines: list[Line], toc: list[tuple[str, str]]) -> list[tuple[int, str, str]]:
    """Find each declared heading in the body. Returns (line index, key, title)."""
    anchors: list[tuple[int, str, str]] = []
    search_from = 0
    for key, title in toc:
        found = None
        for index in range(search_from, len(lines)):
            if lines[index].kind != "content":
                continue
            if _heading_matches(lines[index].text, key, title):
                found = index
                break
        if found is None:
            raise IngestError(
                f"declared in the Table of Contents but not found in the body: {key} {title!r}"
            )
        anchors.append((found, key, title))
        search_from = found + 1
    return anchors


def build_units(lines: list[Line], anchors: list[tuple[int, str, str]]) -> list[Unit]:
    """Units from TOC anchors, with Core sections split further by their tables."""
    units: list[Unit] = []
    path_stack: list[str] = []

    for position, (line_index, key, title) in enumerate(anchors):
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        body = [line for line in lines[line_index:end] if line.kind == "content"]

        if key.startswith("Part "):
            unit_type, path_stack = "part", [f"{key}: {title}"]
        elif key.startswith("Appendix "):
            unit_type, path_stack = "appendix", []
        elif key == "Executive Summary":
            unit_type, path_stack = "named_section", []
        else:
            unit_type = "section"

        ancestry = list(path_stack)
        core = _split_core_table(body, key, title, ancestry)
        if core:
            units.extend(core)
            continue
        units.append(
            Unit(
                unit_key=_unit_key(key),
                unit_type=unit_type,
                label=key if key != title else title,
                heading=title,
                structural_path=ancestry,
                lines=body,
            )
        )
    return units


def _unit_key(key: str) -> str:
    if key.startswith("Part "):
        return "part_" + key.split()[1]
    if key.startswith("Appendix "):
        return "app_" + key.split()[1]
    if key == "Executive Summary":
        return "exec_summary"
    return "sec_" + key


def _split_core_table(
    body: list[Line], key: str, title: str, ancestry: list[str]
) -> list[Unit]:
    """Split a Core section into its section prose, categories and subcategories."""
    positions = [
        (index, line)
        for index, line in enumerate(body)
        if _CATEGORY.match(line.text) or _SUBCATEGORY.match(line.text)
    ]
    if not positions:
        return []

    units: list[Unit] = []
    prose = body[: positions[0][0]]
    section_path = ancestry + [f"{key} {title}"]
    if prose:
        units.append(
            Unit(
                unit_key=_unit_key(key),
                unit_type="section",
                label=key,
                heading=title,
                structural_path=ancestry,
                lines=prose,
            )
        )
    for order, (index, line) in enumerate(positions):
        stop = positions[order + 1][0] if order + 1 < len(positions) else len(body)
        sub = _SUBCATEGORY.match(line.text)
        cat = _CATEGORY.match(line.text)
        if sub:
            function, number = sub.group(1), sub.group(2)
            unit_type, label = "subcategory", f"{function} {number}"
        else:
            function, number = cat.group(1), cat.group(2)
            unit_type, label = "category", f"{function} {number}"
        units.append(
            Unit(
                unit_key=f"{'sub' if sub else 'cat'}_{function}_{number}",
                unit_type=unit_type,
                label=label,
                heading="",
                structural_path=section_path,
                lines=body[index:stop],
            )
        )
    return units


PLAYBOOK_PATH = Path("corpus/nist_ai_rmf/raw/AI_RMF_Playbook.pdf")
GENAI_PATH = Path("corpus/nist_ai_rmf/raw/NIST.AI.600-1.pdf")

_MATCH_NORM = re.compile(r"[^a-z0-9]+")


def match_form(text: str) -> str:
    """Lowercase alphanumeric form used only for exact-substring duplication tests."""
    return " ".join(_MATCH_NORM.sub(" ", text.lower()).split())


def _resolved_text(path: Path, doc_id: str) -> str:
    """Full document text with U+FFFE resolved, for cross-document matching.

    The resolver uses corpus-wide attestation regardless of the text it is given.
    AI 600-1 and the Playbook have no page-boundary interruption between a marker
    and its continuation, so their raw joined text gives correct fragments; only
    AI 100-1 needs the content-line assembly that the main build performs.
    """
    resolved, _ = resolve("\n".join(extract_pages(REPO_ROOT / path)), doc_id)
    return resolved


def build_duplication_map(subcategories: dict[str, str]) -> list[dict]:
    """Mechanical exact-substring duplication test against the other two documents.

    Derived by exact matching, never by judgment. Records, for every Core
    subcategory statement, whether that statement appears verbatim in the
    Playbook and in AI 600-1, with the unit id on both sides.

    AI 600-1 is a profile and covers only a subset of the 72 subcategories, so
    absence there is expected and is not a defect.
    """
    others = {
        "nist_playbook": match_form(_resolved_text(PLAYBOOK_PATH, "nist_playbook")),
        "nist_ai_600_1": match_form(_resolved_text(GENAI_PATH, "nist_ai_600_1")),
    }
    rows: list[dict] = []
    for label, statement in sorted(subcategories.items()):
        probe = match_form(statement)
        function, number = label.split()
        row = {
            "subcategory": label,
            "source_unit_id": f"{DOC_ID}:sub_{function}_{number}",
            "statement_chars": len(statement),
            "duplicated_in": [],
        }
        if len(probe.split()) >= 8:
            for doc_id, haystack in others.items():
                if probe in haystack:
                    row["duplicated_in"].append(
                        {"doc_id": doc_id, "unit_id": f"{doc_id}:sub_{function}_{number}"}
                    )
        row["has_near_miss_twin"] = bool(row["duplicated_in"])
        rows.append(row)
    return rows


DUPLICATION_METHOD = (
    "For each Core subcategory, the statement is taken from the parsed unit, that is "
    "after discard classes are removed and after U+FFFE line-break hyphens are resolved "
    "by src.ingest.hyphenation.resolve on both the statement and the target document. "
    "Both the statement and the target document text are reduced to a match form: "
    "lowercased, every run of non-alphanumeric characters replaced by a single space, "
    "and whitespace collapsed. A duplicate is recorded when the ENTIRE match form of the "
    "statement occurs as a substring of the target document's match form. Statements of "
    "fewer than 8 words are not tested. This is a full-statement exact match, not a "
    "prefix match: a duplicate requires the entire statement to appear, not merely a "
    "leading window of it. A 12-word-prefix variant of the same method accepts more "
    "matches and is deliberately not the method used here. The committed counts are in "
    "duplicated_in_playbook and duplicated_in_ai_600_1 below."
)



# ---------------------------------------------------------------------------
# Cross-document and in-prose relations, kept in SEPARATE fields.
#
# structural_join is a property of the documents' organisation: the same
# subcategory identifier exists in another document. It is exact, derived from
# the shared printed identifier, and carries no regex precision risk.
#
# prose_xrefs is a regex over running text and carries the same precision risk
# the EU AI Act did. In this document the population is small, 38 references
# over a reference vocabulary (Section, Appendix, Table, Figure) that never
# collides with the external citation vocabulary (ISO, IEC, OECD), so every
# emitted reference is audited in full rather than sampled. Unresolvable
# targets, such as Figures, which are not chunked units, are dropped with a
# reason rather than pointed at something that does not exist.
# ---------------------------------------------------------------------------

_PROSE_REF = re.compile(r"\b(?P<kind>Section|Appendix|Table)\s+(?P<id>[A-D]|\d+(?:\.\d+)*)\b")
_UNRESOLVABLE = re.compile(r"\b(?P<kind>Figure|Fig\.)\s+(?P<id>\d+)\b")

# The Core tables are printed as Table 1 to Table 4 and correspond to the
# function sections 5.1 to 5.4. This mapping is stated by the document itself,
# in the TOC entries "Table 1 Categories and subcategories for the GOVERN
# function." and the section headings.
_TABLE_TO_SECTION = {"1": "sec_5.1", "2": "sec_5.2", "3": "sec_5.3", "4": "sec_5.4"}


def build_relations(units, unit_ids: set[str]) -> list[dict]:
    """structural_join and prose_xrefs per unit, as separate fields."""
    others = {
        "nist_playbook": _resolved_text(PLAYBOOK_PATH, "nist_playbook"),
        "nist_ai_600_1": _resolved_text(GENAI_PATH, "nist_ai_600_1"),
    }
    records = []
    for unit in units:
        unit_id = f"{DOC_ID}:{unit.unit_key}"
        joins = []
        if unit.unit_type == "subcategory":
            function, number = unit.label.split()
            for doc_id, text in others.items():
                if re.search(rf"\b{function}\s+{re.escape(number)}\b", text):
                    joins.append(
                        {
                            "doc_id": doc_id,
                            "unit_id": f"{doc_id}:sub_{function}_{number}",
                            "basis": "same printed subcategory identifier",
                        }
                    )
        resolved_body, _ = resolve(BLOCK_SEPARATOR.join(line.text for line in unit.lines), DOC_ID)
        body = normalize_block(resolved_body)
        refs, dropped = [], []
        for match in _PROSE_REF.finditer(body):
            kind, ident = match.group("kind"), match.group("id")
            if kind == "Appendix":
                target = f"{DOC_ID}:app_{ident}"
            elif kind == "Section":
                target = f"{DOC_ID}:sec_{ident}"
            else:
                mapped = _TABLE_TO_SECTION.get(ident)
                target = f"{DOC_ID}:{mapped}" if mapped else None
            sentence = re.sub(r"\s+", " ", body[max(0, match.start() - 70) : match.end() + 60])
            if target and target in unit_ids and target != unit_id:
                refs.append({"target": target, "surface": match.group(0), "sentence": sentence})
            else:
                if target == unit_id:
                    reason = "self-reference, the unit citing its own identifier"
                elif target is None:
                    reason = "no mapping from this printed identifier to a unit"
                else:
                    reason = "target is not a chunked unit in this document"
                dropped.append(
                    {"surface": match.group(0), "reason": reason, "sentence": sentence}
                )
        for match in _UNRESOLVABLE.finditer(body):
            dropped.append(
                {
                    "surface": match.group(0),
                    "reason": "figures are not chunked units, no resolvable target",
                    "sentence": re.sub(
                        r"\s+", " ", body[max(0, match.start() - 60) : match.end() + 50]
                    ),
                }
            )
        if joins or refs or dropped:
            records.append(
                {
                    "unit_id": unit_id,
                    "structural_join": joins,
                    "prose_xrefs": refs,
                    "prose_xrefs_dropped": dropped,
                }
            )
    return records



def write_jsonl_dicts(records: list[dict], path: Path) -> str:
    """Deterministic JSONL for plain dict records."""
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for r in records
    ).encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def build(verify: bool = True) -> dict:
    if verify:
        verify_all()

    source = REPO_ROOT / SOURCE_PATH
    source_sha = sha256_file(source)
    pages = extract_pages(source)
    raw, lines = build_lines(pages)

    unjoinable = find_unjoinable_breaks(raw)
    if unjoinable:
        raise IngestError(
            f"U+FFFE join rule precondition failed on {len(unjoinable)} occurrences: {unjoinable[:3]}"
        )

    classify_lines(lines)
    strip_footer_tails(lines)
    toc = parse_toc(pages)
    if not toc:
        raise IngestError("no Table of Contents entries parsed, cannot validate structure")
    anchors = locate_anchors(lines, toc)
    units = build_units(lines, anchors)

    # ---- partition proof over the raw extracted text -------------------------
    assigned = {id(line) for unit in units for line in unit.lines}
    content_lines = [line for line in lines if line.kind == "content"]
    unassigned = [line for line in content_lines if id(line) not in assigned]
    duplicated = len([line for unit in units for line in unit.lines]) - len(assigned)

    discard_chars = Counter()
    for line in lines:
        if line.kind != "content":
            discard_chars[line.kind] += len(line.text)
        elif line.tail:
            discard_chars["page_footer"] += len(line.tail)
    content_chars = sum(len(line.text) for line in content_lines)
    # Include stripped footer tails: they are counted in the discard classes, so
    # line_chars must be the pre-strip total for the accounting to balance.
    line_chars = sum(len(line.text) + len(line.tail) for line in lines)

    # Account for every character between the raw extraction and the line
    # inventory, so the proof covers the full raw text rather than a derived
    # intermediate. Nothing can hide in the difference.
    structural_ws = Counter()
    for page in pages:
        parts = page.split("\n")
        structural_ws["intra_page_newlines"] += len(parts) - 1
        for piece in parts:
            if piece.strip():
                structural_ws["stripped_line_whitespace"] += len(piece) - len(piece.strip())
            else:
                structural_ws["blank_line_chars"] += len(piece)
                structural_ws["blank_lines"] += 0
    structural_ws["page_separators"] = len(PAGE_SEPARATOR) * (len(pages) - 1)
    structural_total = (
        structural_ws["intra_page_newlines"]
        + structural_ws["stripped_line_whitespace"]
        + structural_ws["blank_line_chars"]
        + structural_ws["page_separators"]
    )
    accounted = content_chars + sum(discard_chars.values()) + structural_total
    if accounted != len(raw):
        raise IngestError(
            f"partition does not account for the full raw extraction: "
            f"{accounted} accounted, {len(raw)} raw, delta {len(raw) - accounted}"
        )

    partition = {
        "raw_chars": len(raw),
        "raw_chars_accounted": accounted,
        "raw_fully_accounted": accounted == len(raw),
        "structural_whitespace_by_class": dict(sorted(structural_ws.items())),
        "structural_whitespace_total": structural_total,
        "why_two_classes_are_equal": (
            "intra_page_newlines and stripped_line_whitespace are equal by construction, "
            "not by coincidence. PDFium emits exactly one trailing space on every line "
            "except the last line of each page, and never any leading space: the observed "
            "padding distribution is 1373 lines with one trailing space and 48 with none, "
            "the 48 being the page-final lines. Both counts therefore equal "
            "total_lines minus page_count."
        ),
        "line_chars": line_chars,
        "content_chars": content_chars,
        "assigned_to_units_chars": sum(len(line.text) for unit in units for line in unit.lines),
        "unassigned_content_lines": len(unassigned),
        "lines_assigned_more_than_once": duplicated,
        "discarded_chars_by_class": dict(sorted(discard_chars.items())),
        "discarded_chars_total": sum(discard_chars.values()),
        "discarded_fraction_of_lines": round(sum(discard_chars.values()) / line_chars, 4),
        "complete": not unassigned and duplicated == 0,
    }
    if unassigned:
        raise IngestError(
            f"partition incomplete, {len(unassigned)} content lines assigned to no unit, "
            f"first: {unassigned[0].text[:110]!r}"
        )
    if duplicated:
        raise IngestError(f"partition overlaps, {duplicated} lines assigned more than once")

    # ---- normalised text and chunks ------------------------------------------
    chunks: list[Chunk] = []
    doc_parts: list[str] = []
    cursor = 0
    subcategory_statements: dict[str, str] = {}
    hyphen_decisions: list = []

    for unit in units:
        # Resolve U+FFFE across the whole unit, not per line, so a word split at a
        # page boundary rejoins across the discarded footer and header. The
        # resolver consumes the newline between such fragments, which merges the
        # two lines into one block; every other line is returned unchanged.
        resolved_unit, unit_decisions = resolve(
            BLOCK_SEPARATOR.join(line.text for line in unit.lines), DOC_ID
        )
        hyphen_decisions.extend(unit_decisions)
        blocks = [normalize_block(block) for block in resolved_unit.split(BLOCK_SEPARATOR)]
        blocks = [b for b in blocks if b]
        if not blocks:
            continue
        unit_text = BLOCK_SEPARATOR.join(blocks)
        unit_start = cursor
        doc_parts.append(unit_text)
        cursor += len(unit_text) + len(UNIT_SEPARATOR)
        unit_id = f"{DOC_ID}:{unit.unit_key}"

        if unit.unit_type == "subcategory":
            head = blocks[0]
            statement = head.split(":", 1)[1].strip() if ":" in head else ""
            rest = " ".join(blocks[1:])
            subcategory_statements[unit.label] = (statement + " " + rest).strip()

        offsets, running = [], 0
        for block in blocks:
            offsets.append(running)
            running += len(block) + len(BLOCK_SEPARATOR)

        groups = _pack(blocks)
        for position, group in enumerate(groups, start=1):
            text = BLOCK_SEPARATOR.join(blocks[i] for i in group)
            start = unit_start + offsets[group[0]]
            chunks.append(
                Chunk(
                    chunk_id=unit_id if len(groups) == 1 else f"{unit_id}#p{position}",
                    parent_id=unit_id,
                    doc_id=DOC_ID,
                    doc_title=DOC_TITLE,
                    source_path=str(SOURCE_PATH),
                    source_sha256=source_sha,
                    unit_type=unit.unit_type,
                    unit_label=unit.label,
                    structural_path=unit.structural_path,
                    heading=unit.heading,
                    text=text,
                    token_count=count_tokens(text),
                    char_start=start,
                    char_end=start + len(text),
                    seq=position,
                    n_chunks_in_unit=len(groups),
                )
            )

    doc_text = UNIT_SEPARATOR.join(doc_parts)
    for chunk in chunks:
        if doc_text[chunk.char_start : chunk.char_end] != chunk.text:
            raise IngestError(f"exact-substring assertion failed for {chunk.chunk_id}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"{DOC_ID}.extracted.txt").write_text(raw, encoding="utf-8")
    (OUTPUT_DIR / f"{DOC_ID}.normalized.txt").write_text(doc_text, encoding="utf-8")
    chunks_sha = write_jsonl(chunks, OUTPUT_DIR / f"{DOC_ID}.chunks.jsonl")

    unit_ids = {f"{DOC_ID}:{u.unit_key}" for u in units}
    relations = build_relations(units, unit_ids)
    relations_sha = write_jsonl_dicts(relations, OUTPUT_DIR / f"{DOC_ID}.relations.jsonl")

    duplication = build_duplication_map(subcategory_statements)
    dup_path = OUTPUT_DIR / f"{DOC_ID}.duplication_map.json"
    dup_path.write_text(
        json.dumps(duplication, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    per_function = Counter(
        u.label.split()[0] for u in units if u.unit_type == "subcategory"
    )
    tokens = sorted(c.token_count for c in chunks)
    dup_counts = Counter(
        entry["doc_id"] for row in duplication for entry in row["duplicated_in"]
    )

    manifest = {
        "schema_version": Chunk.__dataclass_fields__["schema_version"].default,
        "doc_id": DOC_ID,
        "doc_title": DOC_TITLE,
        "source": {"path": str(SOURCE_PATH), "sha256": source_sha, "pages": len(pages)},
        "extractor": extractor_fingerprint(),
        "tokenizer": tokenizer_fingerprint(),
        "hyphenation": {
            "occurrences_resolved": len(hyphen_decisions),
            "deleted": sum(1 for d in hyphen_decisions if d.outcome == ""),
            "kept": sum(1 for d in hyphen_decisions if d.outcome == "-"),
            "by_rule": dict(sorted(Counter(d.rule for d in hyphen_decisions).items())),
            "note": (
                "U+FFFE line-break hyphens in content are resolved by "
                "src.ingest.hyphenation.resolve using corpus-wide attestation and then the "
                "vendored wordlist, per unit so a word split across a page boundary rejoins. "
                "This covers the content-line occurrences only; the corpus-wide log over all "
                "337 raw occurrences, including those in discarded regions, is "
                "data/hyphenation/decision_log.jsonl."
            ),
        },
        "partition_proof": partition,
        "structure": {
            "toc_entries_declared": len(toc),
            "anchors_located": len(anchors),
            "units": len(units),
            "units_by_type": dict(sorted(Counter(u.unit_type for u in units).items())),
            "subcategories": sum(1 for u in units if u.unit_type == "subcategory"),
            "subcategories_per_function": dict(sorted(per_function.items())),
            "validated_against": (
                "the document's own Table of Contents. A heading is accepted only if the "
                "document declares it, which also excludes the enumerated list items in "
                "Appendices C and D that look like section headings"
            ),
        },
        "counts": {
            "chunks_total": len(chunks),
            "chunks_by_unit_type": dict(sorted(Counter(c.unit_type for c in chunks).items())),
            "units_split": sum(1 for c in chunks if c.seq == 1 and c.n_chunks_in_unit > 1),
        },
        "token_distribution": {
            "min": tokens[0],
            "median": tokens[len(tokens) // 2],
            "max": tokens[-1],
            "mean": round(sum(tokens) / len(tokens), 1),
            "over_cap": sum(1 for t in tokens if t > MAX_TOKENS),
        },
        "duplication_map": {
            "method": "mechanical exact-substring match of each Core subcategory statement",
            "subcategories_tested": len(duplication),
            "method_detail": DUPLICATION_METHOD,
            "duplicated_in_playbook": dup_counts.get("nist_playbook", 0),
            "duplicated_in_ai_600_1": dup_counts.get("nist_ai_600_1", 0),
            "duplicated_in_both": sum(1 for r in duplication if len(r["duplicated_in"]) == 2),
            "no_near_miss_twin_count": sum(1 for r in duplication if not r["duplicated_in"]),
            "no_near_miss_twin": [
                r["subcategory"] for r in duplication if not r["duplicated_in"]
            ],
            "no_near_miss_twin_note": (
                "these subcategory statements appear verbatim in neither the Playbook nor "
                "AI 600-1, so they have no near-miss twin and will behave differently in the "
                "distractor bucket from the ones that do"
            ),
            "ai_600_1_coverage_warning": (
                "AI 600-1 is a profile and references only 49 of the 72 subcategories, so any "
                "assumption that all three documents share one subcategory set is wrong. "
                "Absence of a match there is expected, not a defect."
            ),
            "gold_rule_note": (
                "duplication is a near-miss trap to keep, not a problem to remove. Gold sets "
                "are defined at unit level and may name several acceptable units; where a "
                "statement is genuinely duplicated, retrieving any carrier satisfies the gold. "
                "Queries about what the Playbook adds beyond the Core statement are different "
                "questions and the Core unit does not satisfy them."
            ),
        },
        "relations": {
            "structural_join": (
                "same printed subcategory identifier present in another document. Exact, "
                "derived from the identifier, no regex precision risk"
            ),
            "prose_xrefs": (
                "regex over running text, every emitted reference audited in full rather "
                "than sampled, unresolvable targets dropped with a reason"
            ),
            "kept_separate": "structural_join and prose_xrefs are never merged into one field",
            "structural_join_edges": sum(len(r["structural_join"]) for r in relations),
            "prose_xrefs_emitted": sum(len(r["prose_xrefs"]) for r in relations),
            "prose_xrefs_dropped": sum(len(r["prose_xrefs_dropped"]) for r in relations),
        },
        "downstream_notes": {
            "comparison_time_whitespace_normalisation": (
                "Chunk text preserves the PDF's own line breaks, including mid-sentence, "
                "because reflowing into paragraphs requires guessing paragraph boundaries and "
                "can join text wrongly. Consequence to honour downstream: the deterministic "
                "grounding check string-matches claims from model answers against chunk text, "
                "and model answers contain clean sentences where these chunks carry newlines. "
                "ALL whitespace, including newlines, MUST be normalised on BOTH sides before "
                "any grounding comparison, and identically for BM25 tokenisation. Without it "
                "the layer would raise false unsupported-claim flags and corrupt the headline "
                "metric. This normalisation applies at comparison time ONLY and is never "
                "applied to the stored chunk text."
            ),
            "bimodal_chunk_length": (
                "This document is strongly bimodal by length: 72 of its 121 units are one or "
                "two line subcategory statements while narrative sections reach the 512-token "
                "cap, giving a median near 39 tokens against a maximum of 512. This is "
                "authentic to the document and is deliberately not altered. Very short chunks "
                "score differently from long ones under both lexical and dense retrieval, so "
                "length normalisation is to be examined deliberately at the retrieval step "
                "rather than discovered through a strange result."
            ),
        },
        "outputs": {
            f"{DOC_ID}.relations.jsonl": relations_sha,
            f"{DOC_ID}.extracted.txt": sha256_text(raw),
            f"{DOC_ID}.normalized.txt": sha256_text(doc_text),
            f"{DOC_ID}.chunks.jsonl": chunks_sha,
            f"{DOC_ID}.duplication_map.json": sha256_text(dup_path.read_text(encoding="utf-8")),
        },
    }
    (OUTPUT_DIR / f"{DOC_ID}.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _pack(blocks: list[str]) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    for index, block in enumerate(blocks):
        candidate = current + [index]
        if count_tokens(BLOCK_SEPARATOR.join(blocks[i] for i in candidate)) <= MAX_TOKENS:
            current = candidate
            continue
        if current:
            groups.append(current)
        if count_tokens(block) <= MAX_TOKENS:
            current = [index]
        else:
            raise IngestError(f"block exceeds the cap on its own: {block[:110]!r}")
    if current:
        groups.append(current)
    return groups


def applied_hyphen_decisions() -> list:
    """The hyphen decisions actually applied to this document's content.

    Reproduces the per-unit resolution the build performs, so a test can assert
    the applied result agrees with the committed corpus-wide decision log. This
    covers content-line occurrences only; markers in discarded front matter and
    headers never reach a unit and so are not applied anywhere.
    """
    pages = extract_pages(REPO_ROOT / SOURCE_PATH)
    _, lines = build_lines(pages)
    classify_lines(lines)
    strip_footer_tails(lines)
    anchors = locate_anchors(lines, parse_toc(pages))
    decisions: list = []
    for unit in build_units(lines, anchors):
        _, unit_decisions = resolve(
            BLOCK_SEPARATOR.join(line.text for line in unit.lines), DOC_ID
        )
        decisions.extend(unit_decisions)
    return decisions


def main() -> int:
    print(json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
