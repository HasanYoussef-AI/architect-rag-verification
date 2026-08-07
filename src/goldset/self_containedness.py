"""Outward-reference candidate generation over a corpus unit, for screening self-containedness.

An authoring-time screening instrument. It runs before any query text exists, takes a unit id,
and reports every phrase in that unit's text that may point outside the unit. It decides nothing.
Two arms report; a human verifies what they surface and records the verdict on the row. That is
the division src/goldset/attributability.py already uses and argues for.

WHY THIS EXISTS, AND WHAT IT IS FOR. The screening record requires, on every single-hop pick, an
enumeration of the phrases pointing outside the unit, each quoted with its chunk id and verdicted
a signpost or a dependency, with a funnel. On several picks that funnel is expected to terminate
at zero. A human enumeration has no starting population, so a zero funnel is indistinguishable
from an unlooked-at funnel. The product of this module is therefore the DENOMINATOR, not a
verdict: the candidate population that makes a zero a measured zero rather than an asserted one.
V10 is the argument, not V7. Optimising this module's judgment would be optimising something it
does not have.

RECALL, NOT PRECISION, AND THE ASYMMETRY THAT SETS IT. A false positive costs one line of prose
verdicting a candidate a signpost. A false negative silently passes an inadmissible pick, and no
downstream check would catch it. Every pattern here is therefore deliberately over-matching. A
reference to a paragraph of the unit's own article is emitted, because narrowing that would
require deciding what is internal, and deciding is what this module does not do.

CHUNK RECORDS, READ PER RECORD, NEVER CONCATENATED. data/chunks/<doc>.chunks.jsonl is the
artifact of record. It is already the target of record for the one absence check this repository
has: attributability.HEADING_PREDICATE names it verbatim. Its records carry chunk_id, which the
screening record requires on every quoted phrase, and char_end - char_start equals len(text) on
all 397 committed eu_ai_act records, so an offset re-derives exactly.

This module deliberately does NOT reuse attributability.Corpus. That class builds unit text by
concatenating chunk text with no separator. Across the 64 multi-chunk eu_ai_act units outside the
eleven single-hop picks, 90 adjacent chunk pairs join with no whitespace on either side,
fabricating tokens that exist in no chunk: "this Regulation.For example", "AI models.They should".
A candidate matched across such a join could not be attributed to a chunk_id and would quote text
that appears in no committed record. Every match here is found inside one chunk record's text and
carries that record's chunk_id and offsets. test_no_candidate_spans_a_chunk_boundary pins it.

This module also does not read data/chunks/eu_ai_act.xrefs.jsonl. That relation is precision
tuned and drops matches by design, which is backwards for a recall-tuned generator, and keeping
this module's input to unit text alone means no question arises about a screening instrument
reading a relation that defines gold for another stratum.

ARM 1, NAMED REFERENCES. Three surface classes, reported separately and funnelled together.

  article_or_annex     "Article 72", "Annex IV". The ordinary internal pointer.
  deference_locution   "referred to in", "pursuant to", "within the meaning of", and the
                       structural nouns Chapter, Section, Title, paragraph, point.
  external_instrument  A named instrument the corpus does not contain: "Regulation (EU) No
                       182/2011", "Regulation (EC) No 300/2008", "Regulation (EU) 2019/2144",
                       "Directive 2013/36/EU", and the acronyms TEU, TFEU, GDPR, ECHR, TRIPS.

The external_instrument class is named explicitly rather than reached incidentally through a
locution. The admissibility ruling makes a unit inadmissible where its relevant text defers to an
instrument the corpus does not contain, and the three committed target_defers_out_of_corpus
positives carry exactly this surface: art_98 names Regulation (EU) No 182/2011, art_102 names
Regulation (EC) No 300/2008, art_109 names Regulation (EU) 2019/2144. Catching that class only
through an adjacent locution would leave a recital naming Regulation (EU) 2016/679 with no
locution invisible.

ARM 2, DEFINED-TERM DEFERENCE. A unit can defer for substance without pointing anywhere, by using
a term the corpus defines elsewhere. Article 3 of the EU AI Act is headed "Definitions" and states
each definition as a quoted term followed by "means", so the inventory is derived from the corpus
rather than supplied from model knowledge.

This arm fires very widely and that is not a defect. Measured over the 295 eu_ai_act units outside
the eleven picks, for terms that are in the inventory: "AI system" occurs in 202 of them,
"provider" in 143, "deployer" in 57. As a generator that decides nothing this is correct
behaviour, and as anything read as a finding it would be noise. It is therefore a separate arm
with its own funnel, so the human verdicts a bounded and attributed list rather than a wall.

THE INVENTORY IS ARTICLE 3 AND NOTHING ELSE, AND THAT BOUNDS THE ARM. "high-risk AI system" is
one of the Act's most load-bearing terms and is NOT an Article 3 definition; classification lives
in Article 6. It occurs in 120 of those same 295 units and this arm does not reach it on that
ground. test_arm2_does_not_reach_high_risk_ai_system_and_that_limit_is_pinned holds the limit
visible, because an arm whose scope is assumed to be the whole vocabulary is the failure this
module's third arm exists to avoid repeating.

ARM 3, UNNAMED SUBSTANTIVE DEFERENCE. NO COMMITTED METHOD COVERS THIS, AND THE BLOCK SAYS SO.
A unit can state a purpose whose operative content is enacted elsewhere. That is marked only by
ordinary modal and purposive prose, "in order to ensure", "should", "it is appropriate that",
which is the default register of every recital in the Act. A predicate over it has no
discriminating power: it fires on substantially all recitals, or it is fitted to the ones already
looked at, which V15 bars. This arm carries a human verdict and an explicit statement that no
committed method reaches it.

THE ROLL-UP IS NOT THE CONJUNCTION. Two empty funnels plus an unverdicted third part is not a
verified property. self_containedness_verdict is a separate human field, and the emitted block
states in its own text that it does not follow from the arms, so a reader cannot mistake two
zeros for a finding.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from src.ingest.corpus_integrity import REPO_ROOT

DATA = REPO_ROOT / "data"
CHUNKS = DATA / "chunks"

DOCUMENTS = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")

# The unit whose text defines the corpus's own vocabulary. Exact id: "eu_ai_act:art_3" and not a
# prefix test, because startswith("eu_ai_act:art_3") also matches art_30 through art_39.
DEFINITIONS_UNIT = "eu_ai_act:art_3"

# This Act, by its own number. Naming the corpus is not deferring outside it.
_SELF_BY_NUMBER = re.compile(r"Regulation\s*\(EU\)\s*2024/1689")

_ARTICLE_OR_ANNEX = re.compile(r"\b(?:Articles?|Annexe?s?)\s+(?:\d+|[IVXLC]+)\b")

_DEFERENCE_LOCUTION = re.compile(
    r"\b(?:"
    r"referred\s+to\s+in|pursuant\s+to|laid\s+down\s+in|within\s+the\s+meaning\s+of"
    r"|as\s+defined\s+in|in\s+accordance\s+with|provided\s+for\s+in|set\s+out\s+in"
    r"|specified\s+in|established\s+(?:by|in|under)|without\s+prejudice\s+to|subject\s+to"
    r"|listed\s+in|described\s+in|meets?\s+the\s+conditions\s+(?:of|in)|in\s+line\s+with"
    r"|Chapters?\s+[IVXLC0-9]+|Sections?\s+[A-Z0-9]+|Titles?\s+[IVXLC]+"
    r"|paragraphs?\s+\d+|points?\s+\(?[a-z0-9]{1,4}\)?|subparagraph"
    r")\b",
    re.IGNORECASE,
)

# EU instrument citation takes two shapes: the noun then a parenthesised jurisdiction then the
# number, "Regulation (EU) No 182/2011"; and the noun then the number then the jurisdiction,
# "Directive 2013/36/EU", "Decision No 768/2008/EC".
_INSTRUMENT_NUMBERED = re.compile(
    r"\b(?:Regulations?|Directives?|Decisions?|Recommendations?)\s*"
    r"(?:\((?:EU|EC|EEC|Euratom)\)\s*)?"
    r"(?:No\s*)?\d{1,4}/\d{2,4}"
    r"(?:/(?:EU|EC|EEC|Euratom))?",
)

# Instruments the Act cites by acronym, with no noun and no number for a pattern to key on.
_INSTRUMENT_ACRONYM = re.compile(r"\b(?:TEU|TFEU|GDPR|ECHR|TRIPS)\b")

# A capitalised instrument noun not introduced by "this". Deliberately case-sensitive: EU drafting
# capitalises the noun when it names an instrument and leaves the ordinary English word lowercase,
# so a case-insensitive form fires on "deployers that make decisions".
_INSTRUMENT_NOUN = re.compile(
    r"(?<!this\s)(?<!This\s)\b(?:Charter|Treaty|Treaties|Protocol)\b",
)

CLASS_ARTICLE_OR_ANNEX = "article_or_annex"
CLASS_DEFERENCE_LOCUTION = "deference_locution"
CLASS_EXTERNAL_INSTRUMENT = "external_instrument"

_ARM1_PATTERNS = (
    (CLASS_ARTICLE_OR_ANNEX, _ARTICLE_OR_ANNEX),
    (CLASS_DEFERENCE_LOCUTION, _DEFERENCE_LOCUTION),
    (CLASS_EXTERNAL_INSTRUMENT, _INSTRUMENT_NUMBERED),
    (CLASS_EXTERNAL_INSTRUMENT, _INSTRUMENT_ACRONYM),
    (CLASS_EXTERNAL_INSTRUMENT, _INSTRUMENT_NOUN),
)

SELF_REFERENCE_PREDICATE = (
    "the matched surface lies inside an occurrence of this Regulation's own number, "
    "Regulation (EU) 2024/1689. Naming the corpus is not deferring outside it. This is the only "
    "exclusion in arm 1, and it is a well-formedness condition rather than a judgment: it cannot "
    "remove a reference to any other instrument"
)

NAMED_REFERENCES_PREDICATE = (
    "every match of the arm 1 surface patterns inside a single chunk record's text, in the "
    "committed data/chunks/<doc>.chunks.jsonl records for the unit, taken per record and never "
    "over concatenated unit text. Three classes are reported: article_or_annex, "
    "deference_locution and external_instrument. Deliberately over-matching: a reference to the "
    "unit's own paragraph is emitted, because narrowing it would require deciding what is "
    "internal. Every match is reported with its chunk_id, its character offsets within that "
    "chunk, its surface text and its surrounding sentence. Nothing is excluded by score, and the "
    "only exclusion is the self-reference well-formedness condition"
)

DEFINED_TERM_PREDICATE = (
    "every term in the Article 3 inventory that occurs, case-insensitively, in a chunk record's "
    "text for the unit. The inventory is derived from the corpus: the quoted term preceding the "
    "word 'means' in eu_ai_act:art_3, which is headed 'Definitions'. One candidate per "
    "(term, chunk_id) pair, carrying the offset of the term's first occurrence in that chunk and "
    "the number of occurrences, so attribution is preserved without emitting a row per "
    "occurrence. A unit's use of its own definition is excluded when the unit IS the definitions "
    "unit, and that exclusion is reported in the funnel"
)

INVENTORY_PREDICATE = (
    "a term enclosed in the typographic single quotes the Official Journal text uses, immediately "
    "followed by whitespace and the word 'means', inside the text of eu_ai_act:art_3. Derived "
    "from the corpus, not supplied from model knowledge. The pattern is deliberately narrow and "
    "will miss a definition written in any other form; "
    "test_inventory_pattern_is_capable_of_missing shows it failing on a definition phrased "
    "'shall mean', so its recall is bounded and stated rather than assumed"
)

UNNAMED_DEFERENCE_STATEMENT = (
    "NO COMMITTED METHOD COVERS THIS PART. A unit can defer for substance without naming "
    "anything, by stating a purpose whose operative content is enacted elsewhere. That is marked "
    "only by ordinary modal and purposive prose, which is the default register of every recital "
    "in the Act, so a mechanical predicate over it either fires on substantially all recitals or "
    "is fitted to the observations it would judge. This part is a human verdict. It is recorded "
    "here as an explicit gap so that a reader of two empty arms above cannot mistake them for a "
    "finding about this part."
)

ROLLUP_STATEMENT = (
    "This verdict is NOT the conjunction of the three parts above and does not follow from them. "
    "named_references and defined_term_deference may both be empty while the unit is not "
    "self-contained, because unnamed_substantive_deference has no committed method and is the "
    "part most likely to carry a recital's dependency. An empty arm 1 funnel means no NAMED "
    "outward reference was found; it does not mean the unit is self-contained. This field is set "
    "by a human who has read the unit, and it is null until they do."
)

_ARM_COMMAND = (
    'python -c "from src.goldset.self_containedness import ChunkCorpus, screen; '
    'print(screen(UNIT_ID, ChunkCorpus.load()))"'
)
_INVENTORY_COMMAND = (
    'python -c "from src.goldset.self_containedness import ChunkCorpus, article_3_inventory; '
    'print(article_3_inventory(ChunkCorpus.load()))"'
)

_INVENTORY_RE = re.compile(r"‘([^’]{1,80})’\s+means\b")

_SENTENCE_END = re.compile(r"[.!?;]\s")


def _sentence_around(text: str, start: int, end: int) -> str:
    """The sentence containing a match, bounded by this chunk record. Never crosses a chunk.

    Bounding by the record is the whole point: a sentence taken from concatenated unit text could
    span a fabricated join and quote a string that appears in no committed record.
    """
    left = 0
    for match in _SENTENCE_END.finditer(text, 0, start):
        left = match.end()
    right_match = _SENTENCE_END.search(text, end)
    right = right_match.end() if right_match else len(text)
    return re.sub(r"\s+", " ", text[left:right]).strip()


@dataclass(frozen=True)
class ChunkCorpus:
    """Committed chunk records, grouped by unit, never concatenated."""

    records: dict[str, list[dict]]

    @classmethod
    def load(cls, documents: tuple[str, ...] = DOCUMENTS) -> ChunkCorpus:
        records: dict[str, list[dict]] = {}
        for doc in documents:
            path = CHUNKS / f"{doc}.chunks.jsonl"
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                unit = row["chunk_id"].split("#", 1)[0]
                records.setdefault(unit, []).append(row)
        for unit in records:
            records[unit].sort(key=lambda r: r["seq"])
        return cls(records=records)

    def unit_ids(self) -> list[str]:
        return sorted(self.records)

    def chunks_for(self, unit_id: str) -> list[dict]:
        if unit_id not in self.records:
            raise KeyError(f"no committed chunk records for unit {unit_id!r}")
        return self.records[unit_id]


def article_3_inventory(corpus: ChunkCorpus) -> list[str]:
    """The defined-term inventory, derived from eu_ai_act:art_3 and nowhere else."""
    terms: list[str] = []
    for record in corpus.chunks_for(DEFINITIONS_UNIT):
        terms.extend(match.group(1).strip() for match in _INVENTORY_RE.finditer(record["text"]))
    return sorted(set(terms))


def inventory_fingerprint(terms: list[str]) -> str:
    """sha256 over the exact ordered inventory, so a pattern change invalidates a recorded run."""
    payload = json.dumps(sorted(terms), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _self_reference_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _SELF_BY_NUMBER.finditer(text)]


def named_references(unit_id: str, corpus: ChunkCorpus) -> dict:
    """Arm 1. Every named outward-reference surface in the unit, with its funnel."""
    raw: list[dict] = []
    removed: list[dict] = []
    for record in corpus.chunks_for(unit_id):
        text = record["text"]
        masked = _self_reference_spans(text)
        for klass, pattern in _ARM1_PATTERNS:
            for match in pattern.finditer(text):
                candidate = {
                    "chunk_id": record["chunk_id"],
                    "char_start_in_chunk": match.start(),
                    "char_end_in_chunk": match.end(),
                    "surface": match.group(0),
                    "class": klass,
                    "sentence": _sentence_around(text, match.start(), match.end()),
                }
                if any(a <= match.start() and match.end() <= b for a, b in masked):
                    removed.append(candidate)
                else:
                    raw.append(candidate)
    raw.sort(key=lambda c: (c["chunk_id"], c["char_start_in_chunk"], c["class"]))
    removed.sort(key=lambda c: (c["chunk_id"], c["char_start_in_chunk"], c["class"]))
    by_class = {
        klass: sum(1 for c in raw if c["class"] == klass)
        for klass in (
            CLASS_ARTICLE_OR_ANNEX,
            CLASS_DEFERENCE_LOCUTION,
            CLASS_EXTERNAL_INSTRUMENT,
        )
    }
    return {
        "predicate": NAMED_REFERENCES_PREDICATE,
        "command": _ARM_COMMAND,
        "reproducibility_level": 1,
        "over_matching": (
            "Tuned for recall. A false positive costs one line of prose verdicting it a signpost; "
            "a false negative silently passes an inadmissible pick and no downstream check would "
            "catch it."
        ),
        "funnel": {
            "starting_population": len(raw) + len(removed),
            "removed_self_reference": {
                "count": len(removed),
                "predicate": SELF_REFERENCE_PREDICATE,
                "removed_items": removed,
            },
            "candidates": len(raw),
        },
        "candidates_by_class": by_class,
        "candidates": raw,
    }


def defined_term_deference(
    unit_id: str, corpus: ChunkCorpus, inventory: list[str] | None = None
) -> dict:
    """Arm 2. Every Article 3 defined term the unit uses, with its funnel."""
    terms = inventory if inventory is not None else article_3_inventory(corpus)
    is_definitions_unit = unit_id == DEFINITIONS_UNIT
    candidates: list[dict] = []
    present: set[str] = set()
    for record in corpus.chunks_for(unit_id):
        lowered = record["text"].lower()
        for term in terms:
            needle = term.lower()
            first = lowered.find(needle)
            if first < 0:
                continue
            present.add(term)
            if is_definitions_unit:
                continue
            candidates.append(
                {
                    "chunk_id": record["chunk_id"],
                    "term": term,
                    "char_start_in_chunk": first,
                    "char_end_in_chunk": first + len(needle),
                    "occurrences_in_chunk": lowered.count(needle),
                    "sentence": _sentence_around(record["text"], first, first + len(needle)),
                }
            )
    candidates.sort(key=lambda c: (c["chunk_id"], c["char_start_in_chunk"], c["term"]))
    own = len(present) if is_definitions_unit else 0
    return {
        "predicate": DEFINED_TERM_PREDICATE,
        "command": _ARM_COMMAND,
        "reproducibility_level": 1,
        "inventory": {
            "source_unit": DEFINITIONS_UNIT,
            "n_terms": len(terms),
            "fingerprint": inventory_fingerprint(terms),
            "predicate": INVENTORY_PREDICATE,
            "command": _INVENTORY_COMMAND,
        },
        "fires_widely": (
            "This arm fires very widely and that is not a defect. It is a generator that decides "
            "nothing, reported as its own arm with its own funnel so a human verdicts a bounded "
            "attributed list. A wide arm 2 is not evidence about self-containedness by itself."
        ),
        "funnel": {
            "starting_population": len(terms),
            "removed_term_absent_from_unit": {
                "count": len(terms) - len(present),
                "predicate": "the inventory term does not occur in any chunk record for the unit",
            },
            "removed_units_own_definitions": {
                "count": own,
                "predicate": (
                    "the unit IS eu_ai_act:art_3, so its use of a term it itself defines is not "
                    "deference to another unit. Applies to that one unit and to no other"
                ),
            },
            "candidates": len(candidates),
        },
        "distinct_terms_used": sorted(present) if not is_definitions_unit else [],
        "candidates": candidates,
    }


def unnamed_substantive_deference() -> dict:
    """Arm 3. No committed method. A human verdict, recorded as an explicit gap."""
    return {
        "covered_by_committed_method": False,
        "statement": UNNAMED_DEFERENCE_STATEMENT,
        "human_verdict": None,
        "reasoning": None,
        "quoted_text": None,
    }


def self_containedness_verdict() -> dict:
    """The roll-up. Not the conjunction of the arms, and it says so."""
    return {
        "verdict": None,
        "set_by": "human",
        "is_not_the_conjunction_of_the_parts": ROLLUP_STATEMENT,
        "reasoning": None,
    }


def screen(unit_id: str, corpus: ChunkCorpus | None = None,
           inventory: list[str] | None = None) -> dict:
    """The four named parts of the self-containedness evidence for one unit."""
    corpus = corpus if corpus is not None else ChunkCorpus.load()
    return {
        "unit_id": unit_id,
        "chunk_ids": [r["chunk_id"] for r in corpus.chunks_for(unit_id)],
        "named_references": named_references(unit_id, corpus),
        "defined_term_deference": defined_term_deference(unit_id, corpus, inventory),
        "unnamed_substantive_deference": unnamed_substantive_deference(),
        "self_containedness_verdict": self_containedness_verdict(),
    }
