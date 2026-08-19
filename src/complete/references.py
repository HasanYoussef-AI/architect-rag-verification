"""The reference grammar and the resolver, component C1 of the verification layer.

Pure functions over strings, plus one artifact: the committed unit index at
eval/corpus_unit_index.json. Nothing else is opened here. The layer-gold firewall in
CLAUDE.md defines the readable surface and this module is the narrowest part of it: it
never sees retrieved context, never sees a query file field, and never sees a relation
artifact. tests/test_reference_grammar.py enforces both properties mechanically, by
reading this file's source and by patching open().

WHAT THIS IS NOT. It is not relation traversal. Every pattern below composes a printed
name into the unit id of the unit BEARING that name, which the firewall calls identity
resolution and permits. No pattern maps one unit's identifier to a different unit that
a relation asserts is related to it. In particular there is no map from an action
prefix to a function name anywhere in this package: deriving MANAGE 2.2 from MG-2.2-003
is the action_subcategory relation in string form and is barred, and a test asserts the
absence of such a map by reading source rather than by trusting this paragraph.

The grammar is fixed in eval/layer_predictions.md before any of this executed, and the
per-row figures there are hand derivations this module must reproduce exactly. A
disagreement is information about one side or the other, not a reason to adjust either.

R_ACT is deliberately shaped like _ACTION_TOLERANT in src/ingest/nist_ai_600_1.py, the
pattern the corpus was ingested under, so the one garbled printed surface GV4.3--001 and
the correct GV-4.3-001 normalise to a single resolvable unit id. The manifest records
that a lexical query for the correct identifier does not retrieve that unit at all,
which is why this component resolves and fetches rather than re-querying.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.ingest.corpus_integrity import REPO_ROOT

UNIT_INDEX_PATH = REPO_ROOT / "eval" / "corpus_unit_index.json"

# The three NIST documents a printed subcategory identifier can name. AI 600-1 is a
# profile over a subset of the subcategories, so a reference resolving in two documents
# rather than three is normal and is not evidence that the subcategory does not exist.
NIST_DOCS = ("nist_ai_100_1", "nist_ai_600_1", "nist_playbook")

R_ART = re.compile(r"\bArticles?\s+(\d{1,3})\b")
R_ANX = re.compile(r"\bAnnexe?s?\s+([IVXLC]{1,6})\b")
R_SUB = re.compile(r"\b(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+\.\d+)\b")
R_ACT = re.compile(r"\b(GV|MP|MS|MG)-?(\d+\.\d+)-+(\d{3})\b")

# An Article surface naming a different instrument. Applied to the text immediately
# following the surface, allowing one parenthesised subdivision such as "(4)". This is
# the layer's own filter over text it reads: data/chunks/eu_ai_act.xrefs.jsonl records
# the same distinction and is a gold source for the clean multi-hop stratum, so it is
# barred here and the filter is re-derived rather than looked up.
EXTERNAL_QUALIFIER = re.compile(
    r"^\s*(?:\([^)]*\)\s*)?of\s+(?:the\s+)?"
    r"(Directive|Regulation|Treaty|Charter|Decision|Convention)\b",
    re.IGNORECASE,
)
EXTERNAL_LOOKAHEAD = 40

# The Playbook block vocabulary, ordered longest phrase first so the match is
# deterministic rather than dependent on iteration order. Every subcategory carries all
# five, which is what makes composition total rather than partial.
BLOCK_PHRASES = (
    ("transparency & documentation", "transparency_documentation"),
    ("transparency and documentation", "transparency_documentation"),
    ("ai transparency resources", "ai_transparency_resources"),
    ("suggested actions", "suggested_actions"),
    ("references", "references"),
    ("about", "about"),
)


@dataclass(frozen=True)
class Reference:
    """One citation-formed surface and the unit ids it composes to.

    `candidates` is ordered and may hold more than one id: a printed subcategory
    identifier names a unit in up to three documents and the grammar does not choose
    between them. Resolution decides which of them exist.
    """

    kind: str
    surface: str
    start: int
    end: int
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class DroppedReference:
    """A surface removed by the external-instrument filter, with the text that removed it."""

    kind: str
    surface: str
    start: int
    end: int
    qualifier: str


def _block_slug(text: str) -> str | None:
    """The Playbook block slug named in text, longest phrase first, or None."""
    lowered = text.lower()
    for phrase, slug in BLOCK_PHRASES:
        if phrase in lowered:
            return slug
    return None


def extract(text: str, *, allow_block_composition: bool = False) -> tuple[
    list[Reference], list[DroppedReference]
]:
    """Every citation-formed surface in text, and the surfaces the external filter removed.

    Block composition is off by default and is enabled only for query text. The block
    type is part of the information need, which the query states; a retrieved chunk
    containing the ordinary word "references" or "about" is not asking for that block.
    Enabling it everywhere changes no recovery on the sealed fifty and only widens the
    false-positive surface, measured and recorded in eval/layer_predictions.md.
    """
    references: list[Reference] = []
    dropped: list[DroppedReference] = []

    for match in R_ART.finditer(text):
        tail = text[match.end() : match.end() + EXTERNAL_LOOKAHEAD]
        qualifier = EXTERNAL_QUALIFIER.match(tail)
        if qualifier is not None:
            dropped.append(
                DroppedReference(
                    "eu_article", match.group(0), match.start(), match.end(),
                    qualifier.group(0).strip(),
                )
            )
            continue
        references.append(
            Reference("eu_article", match.group(0), match.start(), match.end(),
                      ("eu_ai_act:art_" + match.group(1),))
        )

    for match in R_ANX.finditer(text):
        references.append(
            Reference("eu_annex", match.group(0), match.start(), match.end(),
                      ("eu_ai_act:anx_" + match.group(1),))
        )

    for match in R_ACT.finditer(text):
        unit = "nist_ai_600_1:act_{}-{}-{}".format(
            match.group(1), match.group(2), match.group(3)
        )
        references.append(
            Reference("nist_action", match.group(0), match.start(), match.end(), (unit,))
        )

    slug = _block_slug(text) if allow_block_composition else None
    for match in R_SUB.finditer(text):
        stem = "sub_{}_{}".format(match.group(1), match.group(2))
        candidates = tuple("{}:{}".format(doc, stem) for doc in NIST_DOCS)
        references.append(
            Reference("nist_subcategory", match.group(0), match.start(), match.end(),
                      candidates)
        )
        if slug is not None:
            references.append(
                Reference(
                    "playbook_block", match.group(0), match.start(), match.end(),
                    ("nist_playbook:{}.{}".format(stem, slug),),
                )
            )

    return references, dropped


def load_unit_index(path=None) -> frozenset[str]:
    """The committed unit ids. The only artifact this module opens.

    The index is the set of unit ids and the chunks composing each, derived by grouping
    chunks on parent_id. It records which chunks compose a unit and never which unit
    relates to another, which is why the firewall admits it.
    """
    target = UNIT_INDEX_PATH if path is None else path
    with open(target, encoding="utf-8") as handle:
        payload = json.load(handle)
    return frozenset(unit["unit_id"] for unit in payload["units"])


def resolve(reference: Reference, unit_index: frozenset[str]) -> tuple[str, ...]:
    """The reference's candidates that are members of the committed unit index.

    Empty when the surface is well formed and names nothing, which is the deterministic
    signal a fabricated provision produces. Non-resolution is a finding about the
    corpus, not an error.
    """
    return tuple(candidate for candidate in reference.candidates if candidate in unit_index)


def resolves(reference: Reference, unit_index: frozenset[str]) -> bool:
    """Whether any candidate resolves. A subcategory naming two of three documents resolves."""
    return bool(resolve(reference, unit_index))
