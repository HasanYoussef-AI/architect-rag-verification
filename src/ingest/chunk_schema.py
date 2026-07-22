"""The chunk schema.

Format-agnostic on purpose: the same record type carries EU AI Act HTML chunks
and, in the next step, NIST PDF chunks.

Two properties are load-bearing and are enforced by tests.

Stable, structure-derived IDs. A chunk ID is built from the identifier the
document itself carries, the ELI anchor for the EU AI Act, never from a
positional index that would shift if parsing changed. Gold passages cite these
IDs and pre-registration is immutable once results exist.

Unit-level ground truth via parent_id. Units over the token cap are split, so if
gold passages could only cite leaf chunks then any later change to chunk size
would invalidate pre-registration. Every chunk therefore carries the ID of the
structural unit it came from, and a gold passage naming a unit is satisfied when
any chunk whose parent_id is that unit is retrieved. For an unsplit unit the
chunk ID and the parent ID are the same value, so the rule is uniform.

Chunk text is an exact substring of the persisted normalised document text at
[char_start:char_end]. Headings are carried as metadata rather than duplicated
into every split chunk, so that the substring property holds and a reviewer can
verify any chunk against the document text mechanically.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Chunk:
    # Identity
    chunk_id: str  # "eu_ai_act:art_6" or "eu_ai_act:art_6#p2"
    parent_id: str  # structural unit id, "eu_ai_act:art_6"
    doc_id: str  # "eu_ai_act"
    doc_title: str

    # Provenance of the bytes this came from
    source_path: str  # repo-relative path under corpus/*/raw/
    source_sha256: str

    # Structure
    unit_type: str  # "article" | "annex" | "recital"
    unit_label: str  # "Article 6"
    structural_path: list[str]  # ["Title III", "Chapter 1"], may be empty
    heading: str  # descriptive title, "" when the unit has none

    # Content
    text: str
    token_count: int
    char_start: int  # into the persisted normalised document text
    char_end: int

    # Position within the parent unit
    seq: int  # 1-based index among the parent's chunks
    n_chunks_in_unit: int

    schema_version: str = SCHEMA_VERSION

    @property
    def is_split(self) -> bool:
        return self.n_chunks_in_unit > 1


@dataclass(frozen=True)
class UnitXrefs:
    """Cross-reference candidates extracted from one structural unit.

    HIGH-PRECISION CANDIDATE EXTRACTION, not an authority. Derived by regular
    expression from prose, not read from publisher markup, because the Official
    Journal HTML hyperlinks only footnotes and leaves Article and Annex
    cross-references as plain text. Precision is validated by a full audit of
    every emitted edge. Recall is deliberately sacrificed for precision: an
    ambiguous reference is dropped rather than guessed. Anaphoric references
    such as "that Article" or "paragraph 3 thereof" are not captured at all.

    Every edge that enters a pre-registered gold set is individually read and
    verified at the point of use, and that verification is recorded there.

    This is not the complete cross-reference structure of the Act.

    refs_dropped records each discarded reference with its sentence and the
    reason, so the conservatism is auditable and the recall cost is visible.
    """

    unit_id: str
    refs_internal: list[str] = field(default_factory=list)
    refs_external: list[str] = field(default_factory=list)
    refs_dropped: list[dict[str, str]] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)


def write_jsonl(records: Iterable[object], path: Path) -> str:
    """Write dataclass records as JSONL and return the SHA-256 of the file.

    Deterministic: fixed key order from the dataclass, no timestamps, LF line
    endings, UTF-8 without escaping, trailing newline.
    """
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(asdict(record), ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    ]
    payload = "".join(lines).encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
