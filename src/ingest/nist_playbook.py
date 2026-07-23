"""Structure-aware ingestion of the NIST AI RMF Playbook.

Structure derived from the document, not assumed. Each of the 72 subcategory
sections prints the Core statement verbatim and then five blocks:

    GOVERN 1.1                                 <- subcategory identifier
    Legal and regulatory requirements ...      <- the Core statement, verbatim
    About
    Suggested Actions
    Transparency & Documentation
      Organizations can document the following <- a SUB-LABEL, not a sixth block
    AI Transparency Resources
    References

"Organizations can document the following" also occurs exactly 72 times, which is
why it initially looked like a sixth block. Reading the nesting shows it sits
inside Transparency & Documentation.

The Core statement is a separate unit from the blocks, with its own identifier.
That separation is what makes the gold rule work: retrieving either copy of a
duplicated Core statement satisfies a gold set naming the statement, while a query
about what the Playbook adds beyond the Core can only be satisfied by the block
that actually carries that content.

References blocks are chunked and tagged as unit_type playbook_references, never
excluded. They are bibliography, so they are not mined for prose cross-references,
but they are kept so retrieval can decide what to do with them deliberately.

The page footer prints as "N of 142" and appears MID-CONTENT, between bullets.
The discard is therefore positional, applied per line, and because units are
assembled from the surviving lines in order, removing a footer line never joins
the text on either side of it into one block.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from src.ingest.chunk_schema import Chunk, write_jsonl
from src.ingest.corpus_integrity import REPO_ROOT, sha256_file, verify_all
from src.ingest.nist_pdf_common import (
    BLOCK_SEPARATOR,
    CROSS_DOCUMENT,
    INTERNAL,
    UNIT_SEPARATOR,
    IngestError,
    Line,
    Unit,
    build_lines,
    classify_prose_reference,
    find_prose_references,
    pack,
    partition_proof,
    resolve_unit_blocks,
    write_jsonl_dicts,
)
from src.ingest.normalize import COMPARISON_TIME_NORMALISATION_NOTE, nonascii_inventory
from src.ingest.pdf_extract import extract_pages, extractor_fingerprint, sha256_text
from src.ingest.tokenization import MAX_TOKENS, count_tokens, tokenizer_fingerprint

DOC_ID = "nist_playbook"
DOC_TITLE = "NIST AI RMF Playbook"
SOURCE_PATH = Path("corpus/nist_ai_rmf/raw/AI_RMF_Playbook.pdf")
OUTPUT_DIR = REPO_ROOT / "data" / "chunks"

_FUNCTION_LINE = re.compile(r"^(GOVERN|MAP|MEASURE|MANAGE)$")
_SUBCATEGORY_LINE = re.compile(r"^(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+\.\d+)$")
_PAGE_FOOTER = re.compile(r"^\d+\s+of\s+\d+$")
_TOC_LINE = re.compile(r"\.{6,}\s*\d+$")

# The five block headings, derived from the document: each occurs exactly 72
# times, once per subcategory section.
BLOCK_HEADINGS = {
    "About": "about",
    "Suggested Actions": "suggested_actions",
    "Transparency & Documentation": "transparency_documentation",
    "AI Transparency Resources": "ai_transparency_resources",
    "References": "references",
}

_REFERENCES_TYPE = "playbook_references"


def classify_lines(lines: list[Line], first_anchor: int) -> None:
    for index, line in enumerate(lines):
        if index < first_anchor:
            line.kind = "front_matter"
        elif _PAGE_FOOTER.match(line.text):
            line.kind = "page_footer"
        elif _TOC_LINE.search(line.text):
            line.kind = "table_of_contents"
        else:
            line.kind = "content"


def build_units(lines: list[Line]) -> list[Unit]:
    """Function intros, Core statements, and the five blocks, as separate units."""
    anchors: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if line.kind != "content":
            continue
        if _FUNCTION_LINE.match(line.text):
            anchors.append((index, "function", line.text))
        elif _SUBCATEGORY_LINE.match(line.text):
            anchors.append((index, "subcategory", line.text))
    if not anchors:
        raise IngestError("no function or subcategory anchors found")

    units: list[Unit] = []
    current_function = ""
    for position, (index, kind, label) in enumerate(anchors):
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        body = [line for line in lines[index:end] if line.kind == "content"]
        if kind == "function":
            current_function = label
            units.append(
                Unit(
                    unit_key=f"fn_{label}",
                    unit_type="function_intro",
                    label=label,
                    heading="",
                    structural_path=[label],
                    lines=body,
                )
            )
            continue

        match = _SUBCATEGORY_LINE.match(label)
        function, number = match.group(1), match.group(2)
        path = [current_function or function]
        cuts: list[tuple[int, str, str]] = []
        for offset, line in enumerate(body):
            if line.text in BLOCK_HEADINGS:
                cuts.append((offset, BLOCK_HEADINGS[line.text], line.text))
        statement_end = cuts[0][0] if cuts else len(body)
        units.append(
            Unit(
                unit_key=f"sub_{function}_{number}",
                unit_type="subcategory_statement",
                label=f"{function} {number}",
                heading="",
                structural_path=path,
                lines=body[:statement_end],
            )
        )
        for order, (offset, slug, printed) in enumerate(cuts):
            stop = cuts[order + 1][0] if order + 1 < len(cuts) else len(body)
            unit_type = _REFERENCES_TYPE if slug == "references" else f"playbook_{slug}"
            units.append(
                Unit(
                    unit_key=f"sub_{function}_{number}.{slug}",
                    unit_type=unit_type,
                    label=f"{function} {number} {printed}",
                    heading=printed,
                    structural_path=path + [f"{function} {number}"],
                    lines=body[offset:stop],
                )
            )
    return units


def build(verify: bool = True) -> dict:
    if verify:
        verify_all()
    source = REPO_ROOT / SOURCE_PATH
    source_sha = sha256_file(source)
    pages = extract_pages(source)
    raw, lines = build_lines(pages)

    first_anchor = next(
        (i for i, line in enumerate(lines) if _FUNCTION_LINE.match(line.text)), None
    )
    if first_anchor is None:
        raise IngestError("no function divider found")
    classify_lines(lines, first_anchor)
    units = build_units(lines)

    subcats = [u for u in units if u.unit_type == "subcategory_statement"]
    if len(subcats) != 72:
        raise IngestError(f"expected 72 subcategory statements, found {len(subcats)}")

    proof = partition_proof(raw, pages, lines, units)

    chunks: list[Chunk] = []
    doc_parts: list[str] = []
    cursor = 0
    hyphen_decisions: list = []
    unit_bodies: dict[str, str] = {}
    for unit in units:
        blocks, decisions = resolve_unit_blocks(unit, DOC_ID)
        hyphen_decisions.extend(decisions)
        if not blocks:
            continue
        unit_id = f"{DOC_ID}:{unit.unit_key}"
        unit_bodies[unit_id] = " ".join(blocks)
        unit_text = BLOCK_SEPARATOR.join(blocks)
        unit_start = cursor
        doc_parts.append(unit_text)
        cursor += len(unit_text) + len(UNIT_SEPARATOR)
        offsets, running = [], 0
        for block in blocks:
            offsets.append(running)
            running += len(block) + len(BLOCK_SEPARATOR)
        groups = pack(blocks)
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

    relations = []
    audit: list[dict] = []
    for unit in units:
        unit_id = f"{DOC_ID}:{unit.unit_key}"
        body = unit_bodies.get(unit_id, "")

        joins = []
        if unit.unit_type == "subcategory_statement":
            function, number = unit.label.split()
            joins.append(
                {
                    "doc_id": "nist_ai_100_1",
                    "unit_id": f"nist_ai_100_1:sub_{function}_{number}",
                    "basis": "same printed subcategory identifier",
                }
            )

        refs, dropped = [], []
        for match, kind, ident in find_prose_references(body):
            klass, detail = classify_prose_reference(body, match.start(), match.end())
            sentence = re.sub(r"\s+", " ", body[max(0, match.start() - 80) : match.end() + 70])
            entry = {
                "surface": match.group(0),
                "kind": kind,
                "classification": klass,
                "detail": detail,
                "sentence": sentence,
            }
            if klass == CROSS_DOCUMENT:
                target = f"nist_ai_100_1:app_{ident}" if kind == "Appendix" else None
                if target:
                    entry["target"] = target
                    refs.append(entry)
                else:
                    entry["reason"] = "cross-document target is not a resolvable unit id"
                    dropped.append(entry)
            elif klass == INTERNAL:
                entry["reason"] = "the Playbook has no numbered internal units to resolve against"
                dropped.append(entry)
            else:
                entry["reason"] = f"points outside the corpus: {detail}"
                dropped.append(entry)
            audit.append({"unit_id": unit_id, **entry})

        if joins or refs or dropped:
            relations.append(
                {
                    "unit_id": unit_id,
                    "structural_join": joins,
                    "prose_xrefs": refs,
                    "prose_xrefs_dropped": dropped,
                }
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"{DOC_ID}.extracted.txt").write_text(raw, encoding="utf-8")
    (OUTPUT_DIR / f"{DOC_ID}.normalized.txt").write_text(doc_text, encoding="utf-8")
    chunks_sha = write_jsonl(chunks, OUTPUT_DIR / f"{DOC_ID}.chunks.jsonl")
    relations_sha = write_jsonl_dicts(relations, OUTPUT_DIR / f"{DOC_ID}.relations.jsonl")
    audit_sha = write_jsonl_dicts(audit, OUTPUT_DIR / f"{DOC_ID}.prose_xref_audit.jsonl")

    tokens = sorted(c.token_count for c in chunks)
    klass_counts = Counter(a["classification"] for a in audit)
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
                "U+FFFE line-break hyphens in content resolved by "
                "src.ingest.hyphenation.resolve, per unit, with corpus-wide attestation. "
                "See data/hyphenation/decision_log.jsonl for the corpus-wide log."
            ),
        },
        "partition_proof": proof,
        "structure": {
            "functions": len([u for u in units if u.unit_type == "function_intro"]),
            "subcategory_statements": len(subcats),
            "block_headings_derived": sorted(BLOCK_HEADINGS),
            "block_note": (
                "five top-level blocks per subcategory. 'Organizations can document the "
                "following' also occurs 72 times but is a sub-label inside Transparency and "
                "Documentation, not a sixth block"
            ),
            "units": len(units),
            "units_by_type": dict(sorted(Counter(u.unit_type for u in units).items())),
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
        "relations": {
            "structural_join": "same printed subcategory identifier in AI 100-1, all 72 resolve",
            "prose_xrefs_classes": (
                "three classes. internal resolves within this document, cross_document resolves "
                "to a unit in another corpus document with its real unit id, external points "
                "outside the corpus and emits no edge. Every reference audited in full"
            ),
            "structural_join_edges": sum(len(r["structural_join"]) for r in relations),
            "prose_xrefs_by_class": dict(sorted(klass_counts.items())),
            "prose_xrefs_audited_in_full": len(audit),
        },
        "downstream_notes": {
            "references_blocks_are_bibliography": (
                "the 72 References blocks are bibliography rather than substantive content and "
                "are chunked and tagged as unit_type playbook_references rather than excluded. "
                "Citation lists share vocabulary with everything, so they are expected to behave "
                "oddly under retrieval, a decision for pre-registration to make deliberately"
            ),
            "page_footer_is_positional": (
                "the 'N of 142' footer appears mid-content between bullets. It is discarded per "
                "line by position, and units are assembled from the surviving lines in order, so "
                "removing it never joins the text on either side into one block"
            ),
            "comparison_time_normalisation": COMPARISON_TIME_NORMALISATION_NOTE,
            "non_ascii_inventory": nonascii_inventory(raw),
        },
        "outputs": {
            f"{DOC_ID}.extracted.txt": sha256_text(raw),
            f"{DOC_ID}.normalized.txt": sha256_text(doc_text),
            f"{DOC_ID}.chunks.jsonl": chunks_sha,
            f"{DOC_ID}.relations.jsonl": relations_sha,
            f"{DOC_ID}.prose_xref_audit.jsonl": audit_sha,
        },
    }
    (OUTPUT_DIR / f"{DOC_ID}.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def applied_hyphen_decisions() -> list:
    """Hyphen decisions applied to this document's content, for the log agreement check."""
    pages = extract_pages(REPO_ROOT / SOURCE_PATH)
    _, lines = build_lines(pages)
    first_anchor = next(
        (i for i, line in enumerate(lines) if _FUNCTION_LINE.match(line.text)), None
    )
    classify_lines(lines, first_anchor)
    decisions: list = []
    for unit in build_units(lines):
        _, unit_decisions = resolve_unit_blocks(unit, DOC_ID)
        decisions.extend(unit_decisions)
    return decisions


def main() -> int:
    print(json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
