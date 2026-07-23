"""Structure-aware ingestion of NIST AI 600-1, the Generative AI Profile.

Three kinds of printed identifier carry the structure, and all three are used
as-is rather than replaced by anything invented:

  numbered sections   1, 2, 2.1 to 2.12, 3
  subcategory headings   "GOVERN 1.1: <Core statement, verbatim>"
  action identifiers  "GV-1.1-001", 212 of them

The action identifier encodes its own subcategory, GV-1.1-001 belonging to
GOVERN 1.1, which the document states explicitly. That is a third structural
relation, exact and identifier-based, recorded in its own field. It is not
merged into structural_join, which joins on shared subcategory identifiers across
documents, nor into prose_xrefs, which is a regex over running text.

This document references only 49 of the 72 subcategories, because it is a profile
over a subset. Any assumption that the three NIST documents share one subcategory
set is wrong.

ONE DOCUMENTED EXCEPTION to the rule that a chunk identifier derives verbatim
from the extracted surface. The document's first GOVERN 4.3 action prints its ID
garbled in the PDF's own text layer as "GV4.3--001", the separators damaged where
the correct printed form is "GV-4.3-001". All three extraction engines, pypdfium2,
poppler and pdfminer.six, render it identically, so the defect is in the source
PDF, not our extractor. The row is a genuine 212th action: it carries action text
and a GAI-risk tag. Every component of the identifier survives in the string,
prefix GV, subcategory 4.3, number 001, only the separators are damaged, and the
subcategory is independently confirmed by the GOVERN 4.3 heading directly above it
and the sequence position by GV-4.3-002 directly below. The action anchor is
therefore recognised by a tolerant pattern that tolerates damaged separators but
validates all three components, the stored text keeps "GV4.3--001" verbatim so the
exact-substring assertion holds, and only the derived key is normalised to
GV-4.3-001. The manifest records this as a single exception, not a general
licence, and downstream_notes records the resulting lexical-mismatch case.
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
from src.ingest.normalize import (
    COMPARISON_TIME_NORMALISATION_NOTE,
    nonascii_inventory,
)
from src.ingest.pdf_extract import (
    extract_pages,
    extractor_fingerprint,
    sha256_text,
)
from src.ingest.tokenization import MAX_TOKENS, count_tokens, tokenizer_fingerprint

DOC_ID = "nist_ai_600_1"
DOC_TITLE = (
    "Artificial Intelligence Risk Management Framework: Generative Artificial "
    "Intelligence Profile, NIST AI 600-1"
)
SOURCE_PATH = Path("corpus/nist_ai_rmf/raw/NIST.AI.600-1.pdf")
OUTPUT_DIR = REPO_ROOT / "data" / "chunks"

_SECTION = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(?P<title>[A-Z].{2,80})$")
_APPENDIX = re.compile(r"^Appendix\s+(?P<letter>[A-Z])\.\s+(?P<title>[A-Z].{2,80})$")
_APPENDIX_SECTION = re.compile(r"^(?P<id>[A-Z]\.\d+(?:\.\d+)*)\.\s+(?P<title>[A-Z].{2,80})$")
_SUBCATEGORY = re.compile(r"^(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+\.\d+):\s*(?P<stmt>.*)$")
# Strict form, the correct printed shape. Tolerant form allows damaged separators,
# see the module docstring; both validate the three components below.
_ACTION_STRICT = re.compile(r"^(?:GV|MP|MS|MG)-\d+\.\d+-\d{3}\b")
_ACTION_TOLERANT = re.compile(r"^(?P<prefix>GV|MP|MS|MG)-?(?P<sub>\d+\.\d+)-+(?P<num>\d{3})\b")
_TABLE_HEADER = re.compile(r"^Action ID\s+Suggested Action\s+GAI Risks$")
_TOC_LINE = re.compile(r"\.{6,}\s*\d+$")

_FUNCTION_OF_PREFIX = {"GV": "GOVERN", "MP": "MAP", "MS": "MEASURE", "MG": "MANAGE"}


def classify_lines(lines: list[Line], first_anchor: int) -> None:
    for index, line in enumerate(lines):
        if index < first_anchor:
            line.kind = "front_matter"
        elif _TABLE_HEADER.match(line.text):
            line.kind = "table_header"
        elif _TOC_LINE.search(line.text):
            line.kind = "table_of_contents"
        else:
            line.kind = "content"


def subcategory_headings(lines: list[Line]) -> set[tuple[str, str]]:
    """The (function, number) pairs that print a real subcategory heading here."""
    found: set[tuple[str, str]] = set()
    for line in lines:
        if line.kind == "content":
            match = _SUBCATEGORY.match(line.text)
            if match:
                found.add((match.group(1), match.group(2)))
    return found


def find_anchors(lines: list[Line], valid_subs: set[tuple[str, str]]):
    """(line index, kind, key, label, surface) for every printed identifier.

    surface is the raw matched text; for the one garbled action it differs from
    the derived label. Every action's subcategory is validated against a real
    heading; an action whose components do not validate is reported, not recognised.
    """
    anchors = []
    for index, line in enumerate(lines):
        if line.kind != "content":
            continue
        action = _ACTION_TOLERANT.match(line.text)
        if action:
            prefix, sub, num = action.group("prefix"), action.group("sub"), action.group("num")
            function = _FUNCTION_OF_PREFIX[prefix]
            if (function, sub) not in valid_subs:
                raise IngestError(
                    f"action {prefix}-{sub}-{num} has no matching subcategory heading, "
                    f"refusing to recognise it: {line.text[:80]!r}"
                )
            aid = f"{prefix}-{sub}-{num}"
            anchors.append((index, "action", f"act_{aid}", aid, action.group(0)))
            continue
        sub = _SUBCATEGORY.match(line.text)
        if sub:
            key = f"sub_{sub.group(1)}_{sub.group(2)}"
            anchors.append((index, "subcategory", key, f"{sub.group(1)} {sub.group(2)}", line.text))
            continue
        appendix = _APPENDIX.match(line.text)
        if appendix:
            letter = appendix.group("letter")
            anchors.append((index, "appendix", f"app_{letter}", f"Appendix {letter}", line.text))
            continue
        appendix_section = _APPENDIX_SECTION.match(line.text)
        if appendix_section:
            aid = appendix_section.group("id")
            anchors.append((index, "appendix_section", f"sec_{aid}", aid, line.text))
            continue
        section = _SECTION.match(line.text)
        if section:
            anchors.append((index, "section", f"sec_{section.group(1)}", section.group(1), line.text))
    return anchors


def build_units(lines: list[Line], anchors) -> list[Unit]:
    units: list[Unit] = []
    context_path: list[str] = []
    current_sub = ""
    for position, (index, kind, key, label, _surface) in enumerate(anchors):
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        body = [line for line in lines[index:end] if line.kind == "content"]
        if kind == "section":
            context_path, current_sub = [label], ""
            unit_type, path = "section", []
        elif kind == "appendix":
            context_path, current_sub = [label], ""
            # Appendix B is the References bibliography, chunked and tagged, not excluded.
            unit_type = "references" if key == "app_B" else "appendix"
            path = []
        elif kind == "appendix_section":
            unit_type, path = "appendix_section", list(context_path)
        elif kind == "subcategory":
            current_sub = label
            unit_type, path = "subcategory_statement", list(context_path)
        else:
            unit_type = "action"
            path = list(context_path) + ([current_sub] if current_sub else [])
        units.append(
            Unit(
                unit_key=key,
                unit_type=unit_type,
                label=label,
                heading="",
                structural_path=path,
                lines=body,
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

    first = next(
        (i for i, line in enumerate(lines) if _SECTION.match(line.text) and line.text.startswith("1.")),
        None,
    )
    if first is None:
        raise IngestError("could not locate the first numbered section")
    classify_lines(lines, first)
    valid_subs = subcategory_headings(lines)
    anchors = find_anchors(lines, valid_subs)
    units = build_units(lines, anchors)

    actions = [a for a in anchors if a[1] == "action"]
    subcats = [u for u in units if u.unit_type == "subcategory_statement"]
    if len(subcats) != 49:
        raise IngestError(f"expected 49 subcategory headings, found {len(subcats)}")

    # Action-count and garble accounting, pinned so the recovery cannot drift.
    strict_n = sum(1 for line in lines if line.kind == "content" and _ACTION_STRICT.match(line.text))
    garbled = [(key, surface) for (_i, kind, key, label, surface) in actions if surface != label]
    action_keys = [a[2] for a in actions]
    if len(actions) != 212:
        raise IngestError(f"expected 212 action rows, found {len(actions)}")
    if len(set(action_keys)) != 212:
        raise IngestError("duplicate action identifiers after recovery")
    if len(garbled) != 1 or garbled[0][0] != "act_GV-4.3-001" or garbled[0][1] != "GV4.3--001":
        raise IngestError(f"unexpected garble set: strict={strict_n} garbled={garbled}")

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
                    heading="",
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

    unit_ids = {f"{DOC_ID}:{u.unit_key}" for u in units}
    relations = []
    audit: list[dict] = []
    for unit in units:
        unit_id = f"{DOC_ID}:{unit.unit_key}"
        body = unit_bodies.get(unit_id, "")

        action_relation = []
        if unit.unit_type == "action":
            prefix, sub = unit.label.split("-")[0], unit.label.split("-")[1]
            function = _FUNCTION_OF_PREFIX[prefix]
            action_relation.append(
                {
                    "subcategory": f"{function} {sub}",
                    "unit_id": f"{DOC_ID}:sub_{function}_{sub}",
                    "basis": "the action identifier encodes its own subcategory",
                }
            )
        joins = []
        if unit.unit_type == "subcategory_statement":
            function, number = unit.label.split()
            for other in ("nist_ai_100_1", "nist_playbook"):
                joins.append(
                    {
                        "doc_id": other,
                        "unit_id": f"{other}:sub_{function}_{number}",
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
            if klass == INTERNAL:
                if kind == "Section":
                    target = f"{DOC_ID}:sec_{ident}"
                elif kind == "Appendix":
                    target = f"{DOC_ID}:app_{ident}"
                else:
                    target = None
                if target and target in unit_ids and target != unit_id:
                    entry["target"] = target
                    refs.append(entry)
                else:
                    entry["reason"] = "no resolvable unit for this printed identifier"
                    dropped.append(entry)
            elif klass == CROSS_DOCUMENT:
                target = f"nist_ai_100_1:app_{ident}" if kind == "Appendix" else None
                if target:
                    entry["target"] = target
                    refs.append(entry)
                else:
                    entry["reason"] = "cross-document target is not a resolvable unit id"
                    dropped.append(entry)
            else:
                entry["reason"] = f"points outside the corpus: {detail}"
                dropped.append(entry)
            audit.append({"unit_id": unit_id, **entry})
        if action_relation or joins or refs or dropped:
            relations.append(
                {
                    "unit_id": unit_id,
                    "action_subcategory": action_relation,
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
        "garbled_identifier_exception": {
            "stored_surface": "GV4.3--001",
            "derived_unit_id": f"{DOC_ID}:act_GV-4.3-001",
            "note": (
                "The single documented exception to deriving a chunk id verbatim from the "
                "extracted surface. The PDF's own text layer prints this action id garbled, "
                "confirmed identical across pypdfium2, poppler and pdfminer.six, so the defect "
                "is in the source, not the extractor. The three components survive intact "
                "(GV, 4.3, 001) and are independently corroborated by the GOVERN 4.3 heading "
                "above and GV-4.3-002 below, so the derivation is component-based rather than "
                "externally corroborated. Stored text keeps GV4.3--001 verbatim; only the "
                "derived key is normalised. This is one exception, not a general licence."
            ),
        },
        "partition_proof": proof,
        "structure": {
            "units": len(units),
            "units_by_type": dict(sorted(Counter(u.unit_type for u in units).items())),
            "action_identifiers": len(actions),
            "action_identifiers_strict": strict_n,
            "action_identifiers_recovered": len(garbled),
            "subcategories_referenced": len(subcats),
            "subcategory_coverage_note": (
                "this profile references a SUBSET of the 72 AI RMF subcategories, 49 of them. "
                "Any assumption that the three NIST documents share one subcategory set is wrong"
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
        "relations": {
            "action_subcategory": (
                "exact, the action identifier encodes its subcategory. Its own field, merged "
                "into neither structural_join nor prose_xrefs"
            ),
            "structural_join": "same printed subcategory identifier in another corpus document",
            "prose_xrefs_classes": (
                "three classes. internal resolves within this document, cross_document "
                "resolves to a unit in another corpus document with its real unit id, external "
                "points outside the corpus and emits no edge. Every reference audited in full"
            ),
            "action_subcategory_edges": sum(len(r["action_subcategory"]) for r in relations),
            "structural_join_edges": sum(len(r["structural_join"]) for r in relations),
            "prose_xrefs_by_class": dict(sorted(klass_counts.items())),
            "prose_xrefs_audited_in_full": len(audit),
        },
        "downstream_notes": {
            "comparison_time_normalisation": COMPARISON_TIME_NORMALISATION_NOTE,
            "non_ascii_inventory": nonascii_inventory(raw),
            "garbled_action_id_lexical_mismatch": (
                "A query containing GV-4.3-001 will not lexically match the chunk carrying the "
                "garbled surface GV4.3--001. This is a retrieval consequence of an extraction "
                "artifact in our pipeline, not a property of the document, so it must not be "
                "used as a designed trap in the query set. The retrieval step inherits it as a "
                "known case."
            ),
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
    first = next(
        (i for i, line in enumerate(lines) if _SECTION.match(line.text) and line.text.startswith("1.")),
        None,
    )
    classify_lines(lines, first)
    valid_subs = subcategory_headings(lines)
    decisions: list = []
    for unit in build_units(lines, find_anchors(lines, valid_subs)):
        _, unit_decisions = resolve_unit_blocks(unit, DOC_ID)
        decisions.extend(unit_decisions)
    return decisions


def main() -> int:
    print(json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
