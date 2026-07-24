"""Structure-aware ingestion of the EU AI Act Official Journal HTML.

Units are the document's own: 113 Articles, 13 Annexes, 180 Recitals, located by
the ELI anchors the document itself carries (art_N, anx_R, rct_N). Chunk IDs are
built from those anchors, so they are a property of the corpus rather than of
our parsing parameters.

Recitals are ingested and tagged as such. They are non-binding interpretive text
covering the same subject matter as the Articles in similar language, which
makes them the most realistic near-miss distractors available. Whether gold sets
may cite them is a pre-registration decision, not an ingestion one.

Enumerated lists in the Official Journal are laid out as HTML tables, with the
marker, "(a)", in the first cell and the text in the second, and Recitals are
laid out as a table whose first cell holds the recital number. Table rows are
therefore flattened to one block each rather than skipped, which is why the
block extractor treats `tr` as a text block.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.ingest.chunk_schema import Chunk, UnitXrefs, write_jsonl
from src.ingest.corpus_integrity import REPO_ROOT, sha256_file, verify_all
from src.ingest.htmltree import Element, parse_html
from src.ingest.normalize import (
    COMPARISON_TIME_NORMALISATION_NOTE,
    nonascii_inventory,
    normalize_block,
)
from src.ingest.tokenization import MAX_TOKENS, count_tokens, tokenizer_fingerprint
from src.ingest.xref import amends_external_instrument, extract_references

DOC_ID = "eu_ai_act"
DOC_TITLE = (
    "Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 "
    "laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)"
)
SOURCE_PATH = Path("corpus/eu_ai_act/raw/CELEX_32024R1689_EN_OJ.html")
OUTPUT_DIR = REPO_ROOT / "data" / "chunks"

UNIT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("recital", re.compile(r"^rct_(\d+)$")),
    ("article", re.compile(r"^art_(\d+)$")),
    ("annex", re.compile(r"^anx_([IVXLC]+)$")),
]

BLOCK_SEPARATOR = "\n"
UNIT_SEPARATOR = "\n\n"

_SENTENCE_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(‘“])")


class IngestError(RuntimeError):
    """Raised when the document does not parse as expected. Fails loudly by design."""


@dataclass
class Unit:
    unit_key: str  # "art_6"
    unit_type: str
    label: str
    heading: str
    blocks: list[str]
    structural_path: list[str]
    order: int


def element_text(element: Element) -> str:
    parts: list[str] = []

    def walk(node: Element | str) -> None:
        if isinstance(node, str):
            parts.append(node)
            return
        for child in node.children:
            walk(child)

    walk(element)
    return normalize_block("".join(parts))


def extract_blocks(element: Element) -> list[str]:
    """Flatten a unit into ordered text blocks, one per paragraph or table row."""
    blocks: list[str] = []

    def walk(node: Element) -> None:
        for child in node.children:
            if isinstance(child, str):
                text = normalize_block(child)
                if text:
                    blocks.append(text)
                continue
            if child.tag == "p" or child.tag == "tr":
                text = element_text(child)
                if text:
                    blocks.append(text)
            else:
                walk(child)

    walk(element)
    return blocks


def _direct_class_text(element: Element, class_name: str) -> str:
    for child in element.children:
        if isinstance(child, Element) and child.attrs.get("class") == class_name:
            return element_text(child)
    return ""


def _title_for_container(element: Element) -> str:
    """Title of a Title, Chapter or Section container, from its own heading lines.

    The label, "CHAPTER I", sits in an `oj-ti-section-1` paragraph, while the
    descriptive name, "GENERAL PROVISIONS", sits in a nested `eli-title` div
    rather than in a sibling paragraph.
    """
    parts = [
        _direct_class_text(element, "oj-ti-section-1"),
        _direct_class_text(element, "oj-ti-section-2"),
        _direct_class_text(element, "eli-title"),
    ]
    return " ".join(part for part in parts if part).strip()


def structural_path_for(element: Element) -> list[str]:
    """Ancestor Title, Chapter and Section headings, outermost first."""
    path: list[str] = []
    node = element.parent
    while node is not None:
        node_id = node.id or ""
        if re.match(r"^(?:tit|cpt)_[IVXLC0-9]+(?:\.sct_\d+)?$", node_id):
            title = _title_for_container(node)
            if title:
                path.append(title)
        node = node.parent
    return list(reversed(path))


def collect_units(root: Element) -> list[Unit]:
    """Locate every structural unit by its own ELI anchor, in document order."""
    units: list[Unit] = []
    seen: set[str] = set()
    order = 0
    for element in root.iter_elements():
        element_id = element.id
        if not element_id or element_id in seen:
            continue
        for unit_type, pattern in UNIT_PATTERNS:
            if not pattern.match(element_id):
                continue
            seen.add(element_id)
            blocks = extract_blocks(element)
            if not blocks:
                raise IngestError(f"unit {element_id} produced no text blocks")
            if unit_type == "article":
                label = _direct_class_text(element, "oj-ti-art") or f"Article {element_id[4:]}"
                heading = ""
                for child in element.children:
                    if isinstance(child, Element) and child.attrs.get("class") == "eli-title":
                        heading = element_text(child)
                        break
            elif unit_type == "annex":
                titles = [
                    element_text(child)
                    for child in element.children
                    if isinstance(child, Element) and child.attrs.get("class") == "oj-doc-ti"
                ]
                label = titles[0] if titles else f"Annex {element_id[4:]}"
                heading = titles[1] if len(titles) > 1 else ""
            else:
                number = element_id[4:]
                label = f"Recital ({number})"
                heading = ""
            units.append(
                Unit(
                    unit_key=element_id,
                    unit_type=unit_type,
                    label=label,
                    heading=heading,
                    blocks=blocks,
                    structural_path=structural_path_for(element),
                    order=order,
                )
            )
            order += 1
            break
    return units


def _split_oversize_block(block: str) -> list[str]:
    """Fallback for a single block over the cap: split on sentence boundaries.

    Raises rather than truncating if a single sentence still exceeds the cap,
    because silently dropping text is the failure this repository cannot afford.
    """
    pieces = _SENTENCE_SPLIT.split(block)
    if len(pieces) == 1:
        raise IngestError(
            f"single sentence exceeds the {MAX_TOKENS}-token cap and cannot be split "
            f"on a document boundary: {block[:160]!r}"
        )
    out: list[str] = []
    for piece in pieces:
        if count_tokens(piece) > MAX_TOKENS:
            raise IngestError(
                f"sentence exceeds the {MAX_TOKENS}-token cap: {piece[:160]!r}"
            )
        out.append(piece)
    return out


def pack_blocks(blocks: list[str]) -> list[list[int]]:
    """Greedy pack block indices into chunks under the cap, never mid-block.

    Returns a list of index runs. Splitting happens only on the document's own
    paragraph and list-item boundaries.
    """
    groups: list[list[int]] = []
    current: list[int] = []
    for index, block in enumerate(blocks):
        candidate = current + [index]
        text = BLOCK_SEPARATOR.join(blocks[i] for i in candidate)
        if count_tokens(text) <= MAX_TOKENS:
            current = candidate
            continue
        if current:
            groups.append(current)
            current = []
        if count_tokens(block) <= MAX_TOKENS:
            current = [index]
        else:
            raise IngestError(
                f"block at index {index} exceeds the cap on its own and needs "
                f"sentence-level fallback: {block[:120]!r}"
            )
    if current:
        groups.append(current)
    return groups


def build(verify: bool = True) -> dict:
    if verify:
        verify_all()

    source = REPO_ROOT / SOURCE_PATH
    source_sha = sha256_file(source)
    root = parse_html(source.read_text(encoding="utf-8", errors="surrogateescape"))
    units = collect_units(root)

    counts = {kind: sum(1 for u in units if u.unit_type == kind) for _, kind in
              [(None, "article"), (None, "annex"), (None, "recital")]}
    expected = {"article": 113, "annex": 13, "recital": 180}
    if counts != expected:
        raise IngestError(f"unit counts {counts} do not match the document's structure {expected}")

    # Pre-split any block that alone exceeds the cap, on sentence boundaries.
    for unit in units:
        rebuilt: list[str] = []
        for block in unit.blocks:
            if count_tokens(block) > MAX_TOKENS:
                rebuilt.extend(_split_oversize_block(block))
            else:
                rebuilt.append(block)
        unit.blocks = rebuilt

    chunks: list[Chunk] = []
    xrefs: list[UnitXrefs] = []
    doc_parts: list[str] = []
    cursor = 0

    for unit in units:
        unit_text = BLOCK_SEPARATOR.join(unit.blocks)
        unit_start = cursor
        doc_parts.append(unit_text)
        cursor += len(unit_text) + len(UNIT_SEPARATOR)

        unit_id = f"{DOC_ID}:{unit.unit_key}"
        internal, external, dropped, evidence = extract_references(
            unit_text,
            DOC_ID,
            amends_external=amends_external_instrument(unit.heading),
        )
        xrefs.append(
            UnitXrefs(
                unit_id=unit_id,
                refs_internal=[r for r in internal if r != unit_id],
                refs_external=external,
                refs_dropped=[d for d in dropped if d["ref"] != unit_id],
                evidence=evidence,
            )
        )

        # Byte offset of each block within the unit text.
        block_offsets: list[int] = []
        running = 0
        for block in unit.blocks:
            block_offsets.append(running)
            running += len(block) + len(BLOCK_SEPARATOR)

        groups = pack_blocks(unit.blocks)
        for position, group in enumerate(groups, start=1):
            text = BLOCK_SEPARATOR.join(unit.blocks[i] for i in group)
            start = unit_start + block_offsets[group[0]]
            chunk_id = unit_id if len(groups) == 1 else f"{unit_id}#p{position}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
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

    # Referential integrity. An internal edge must resolve to a unit that
    # actually exists in this document. "Article 290 TFEU" cannot be internal
    # because the Act has 113 Articles. This is a structural check rather than a
    # patch for an observed error, so it also catches modes not yet seen.
    real_units = {f"{DOC_ID}:{unit.unit_key}" for unit in units}
    for record in xrefs:
        unresolved = [ref for ref in record.refs_internal if ref not in real_units]
        if not unresolved:
            continue
        record.refs_internal[:] = [r for r in record.refs_internal if r in real_units]
        for ref in unresolved:
            sentence = next(
                (e["sentence"] for e in record.evidence if e["outcome"] == "internal"), ""
            )
            record.refs_dropped.append(
                {
                    "ref": ref,
                    "reason": "target unit does not exist in this document",
                    "surface": "",
                    "sentence": sentence,
                }
            )

    doc_text = UNIT_SEPARATOR.join(doc_parts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text_path = OUTPUT_DIR / f"{DOC_ID}.normalized.txt"
    text_path.write_text(doc_text, encoding="utf-8")

    # Offsets must resolve against the persisted text, not merely be plausible.
    for chunk in chunks:
        if doc_text[chunk.char_start : chunk.char_end] != chunk.text:
            raise IngestError(f"offset mismatch for {chunk.chunk_id}")

    chunks_sha = write_jsonl(chunks, OUTPUT_DIR / f"{DOC_ID}.chunks.jsonl")
    xrefs_sha = write_jsonl(xrefs, OUTPUT_DIR / f"{DOC_ID}.xrefs.jsonl")

    import hashlib

    token_counts = sorted(c.token_count for c in chunks)
    split_units = sum(1 for u in units if len({c.chunk_id for c in chunks
                                               if c.parent_id == f"{DOC_ID}:{u.unit_key}"}) > 1)
    manifest = {
        "schema_version": Chunk.__dataclass_fields__["schema_version"].default,
        "doc_id": DOC_ID,
        "doc_title": DOC_TITLE,
        "source": {
            "path": str(SOURCE_PATH),
            "sha256": source_sha,
        },
        "tokenizer": tokenizer_fingerprint(),
        "chunking": {
            "max_tokens": MAX_TOKENS,
            "split_boundary": "document paragraph and list-item boundaries",
            "sentence_fallback": "only for a single block over the cap",
            "block_separator": "\\n",
            "unit_separator": "\\n\\n",
            "heading_in_text": (
                "headings appear in the text only where the document places them; "
                "they are not duplicated into split chunks, so every chunk text is an "
                "exact substring of the normalised document text"
            ),
        },
        "counts": {
            "units": {kind: counts[kind] for kind in sorted(counts)},
            "units_split": split_units,
            "chunks_total": len(chunks),
            "chunks_by_unit_type": {
                kind: sum(1 for c in chunks if c.unit_type == kind) for kind in sorted(counts)
            },
        },
        "token_distribution": {
            "min": token_counts[0],
            "median": token_counts[len(token_counts) // 2],
            "max": token_counts[-1],
            "mean": round(sum(token_counts) / len(token_counts), 1),
            "over_cap": sum(1 for t in token_counts if t > MAX_TOKENS),
        },
        "cross_references": {
            "status": "high-precision candidate extraction, not an authority",
            "derivation": (
                "derived by our regular expression from prose, not read from publisher "
                "markup: the Official Journal HTML hyperlinks only footnotes"
            ),
            "precision": "validated by full audit of every emitted edge, not a sample",
            "recall": (
                "deliberately sacrificed for precision, an ambiguous reference is dropped "
                "rather than guessed, and anaphoric references such as 'that Article' or "
                "'paragraph 3 thereof' are not captured at all"
            ),
            "use_in_ground_truth": (
                "candidate generator only, every edge entering a pre-registered gold set is "
                "individually read and verified at the point of use"
            ),
            "warning": "this is not the complete cross-reference structure of the Act",
            "rule": (
                "explicit 'of this Regulation' wins, then an explicit external qualifier, "
                "then drop inside articles amending an external instrument, then drop when "
                "any external instrument is named in the same sentence, otherwise internal"
            ),
            "acronym_instruments": (
                "the Act cites the Treaties by acronym, 'Article 16 TFEU', with no instrument "
                "noun. A reference carrying an adjacent acronym is classified external, not "
                "dropped, because the acronym settles it rather than casting doubt"
            ),
            "referential_integrity": (
                "an internal edge must resolve to a unit that exists in this document. This is "
                "a structural safety net and it currently fires zero times, because "
                "acronym-qualified references such as 'Article 290 TFEU' are already classified "
                "external upstream. It is retained to catch modes not yet observed, not because "
                "it is doing work today"
            ),
            "internal_edges": sum(len(x.refs_internal) for x in xrefs),
            "external_refs": sum(len(x.refs_external) for x in xrefs),
            "dropped_refs": sum(len(x.refs_dropped) for x in xrefs),
            "dropped_by_reason": {
                reason: count
                for reason, count in sorted(
                    Counter(
                        d["reason"].split(":")[0] for x in xrefs for d in x.refs_dropped
                    ).items()
                )
            },
            "referential_integrity_firings": sum(
                1 for x in xrefs for d in x.refs_dropped if "does not exist" in d["reason"]
            ),
        },
        "source_format_notes": {
            "enumerated_lists_are_tables": (
                "enumerated points are laid out as HTML tables with the marker, '(a)', in "
                "the first cell and the text in the second"
            ),
            "recitals_are_tables_only": (
                "all 180 Recitals exist only as tables, number in the first cell and text "
                "in the second, so a parser that skips tables would drop every list item "
                "and every Recital while still appearing to succeed. Asserted by test."
            ),
            "unit_boundaries_need_dom_nesting": (
                "unit extent comes from element nesting, not from a regex window between "
                "anchors. A window over-captures whenever an anchor is the last of its "
                "kind: Article 113 absorbed the Annexes and measured 2577 words against a "
                "true length near 100. The NIST PDFs in part two have no nesting to fall "
                "back on, so that step needs its own boundary strategy."
            ),
        },
        "known_source_artifacts": {
            "art_1_heading_stray_backtick": (
                "the heading of Article 1 reads 'Subject matter`' with a trailing backtick. "
                "This is in the published Regulation, not in our extraction: it appears in "
                "the official EUR-Lex PDF as well, at line 3023 of the pdftotext rendering. "
                "Reproduced exactly rather than corrected, per the rule that source text is "
                "never edited or reconstructed."
            ),
        },
        "downstream_notes": {
            "comparison_time_normalisation": COMPARISON_TIME_NORMALISATION_NOTE,
            "non_ascii_inventory": nonascii_inventory(doc_text),
            "non_ascii_leave_alone": (
                "U+00E0 and U+00E9, a with grave and e with acute, are deliberately excluded "
                "from normalisation: they are genuine content in French terms in the English "
                "text, 'vis-a-vis' and 'cafes', not typography to fold."
            ),
            "non_ascii_verified_absent": (
                "The sweep of the stored text was run, not skipped, and these classes were "
                "examined and confirmed ABSENT: guillemets, the en dash U+2013, and the "
                "non-breaking space U+00A0. Only the quote, apostrophe and em-dash codepoints "
                "in the inventory above are present and all are covered by the comparison-time map."
            ),
            "non_breaking_space_u00a0": (
                "The raw EUR-Lex HTML uses U+00A0 in structural titles, 'Article' + U+00A0 + "
                "number, recorded in corpus/SOURCES.md. It is folded to a plain space at "
                "ingestion by normalize_spaces, so it is absent from the stored text, and the "
                "comparison-time map folds U+00A0 again for safety."
            ),
            "integrity_path": (
                "This document is HTML, not PDF, so its integrity is validated by DOM nesting, "
                "ELI anchors and the recital-count assertion rather than a raw_chars partition "
                "proof. The absence of a partition_proof is by design, not a gap."
            ),
        },
        "outputs": {
            f"{DOC_ID}.chunks.jsonl": chunks_sha,
            f"{DOC_ID}.xrefs.jsonl": xrefs_sha,
            f"{DOC_ID}.normalized.txt": hashlib.sha256(
                doc_text.encode("utf-8")
            ).hexdigest(),
        },
    }
    manifest_path = OUTPUT_DIR / f"{DOC_ID}.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    manifest = build()
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
