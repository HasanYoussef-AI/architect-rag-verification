"""Two-armed attributability scan over a designated answer span.

An authoring-time screening instrument. It runs before any query text exists, takes a span of
corpus text designated at screening, and reports where else in the frozen corpus that span's
content appears. It decides nothing. Both arms report; a human verifies what they surface and
records the verdict on the row.

This is not part of the operational layer and the layer-gold firewall does not reach it. The
firewall constrains what the layer may read while answering a query. This module runs before a
query exists, over the frozen corpus alone, and never sees a query, a stratum label, a row
identifier or any per-query annotation. It reads no file under data/retrieval/, so nothing it
does can reach the frozen retrieval parameters, which are frozen for retrieval.

ONE SEGMENTER, BOTH ARMS. comparable_segments is the only segmentation in this module and both
arms consume it. Two segmenters would let a pick pass one arm and fail the other for a
segmentation reason, and neither result would mean anything.

Lexical arm. difflib character-level similarity of the normalised span against every normalised
corpus segment, reporting every pair at or above a floor of 0.60. The floor matches the
convention already committed in eval/test_query_verification.jsonl and never moves. Exact and
reproducible from committed files with no model and no key: reproducibility level 1 in
data/retrieval/retrieval_manifest.json.

Dense arm. Cosine of the span's embedding against SEGMENT embeddings, reporting a fixed top 5 of
non-gold units with no floor. A fixed N fixed before any observation cannot be fitted to a
distribution; a floor chosen after seeing one can.

The dense arm embeds segments rather than chunks because a chunk-level arm is not an instrument.
Measured: on the published 0.940 pair, a chunk-level dense arm ranks the known partner
eu_ai_act:art_72 at 207 of 1149, cosine 0.5895, while the lexical arm ranks it first at 0.9397.
The span is 123 characters against art_72's 2318, so 5.3 percent of the text carries the match
and the remaining 94.7 percent sets the direction. Recital units in the corpus run 145 to 4,448
characters at a median of 1,030, against an answer that can occupy one sentence, so the same
dilution applies to the paraphrase case this arm was added to reach. Segment embeddings put both
arms on the same footing.

The segment embedding cache is not committed, on size. At 13316 segments by 768 float32 it is
40,906,752 bytes, 10.3 times the committed chunk embeddings at 3,975,296. Note this is NOT the
pattern the retrieval artifacts follow: data/retrieval/embeddings.npy IS committed, which is what
lets retrieval reproduce at level 2 without the model. Declining to commit this cache is a size
decision and its cost is precisely that the dense arm sits at level 3 instead. What commits is the
generator, the pinned model revision, and the per-pick output. The cache records a fingerprint of the exact segmentation it was built from
and load_segment_cache refuses a cache whose fingerprint does not match the current segmenter, so
a segmenter change cannot silently produce embeddings that no longer correspond to the segments
being compared. Level 3 in the manifest: regenerating from ONNX at the pinned revision reproduces
rankings, not bytes.

SEGMENTATION, AND WHY THE SEMICOLON IS CALIBRATION RATHER THAN FITTING.

A period-terminated segmenter is blind to the published 0.894 case. Annex IV point 3 of the EU AI
Act is one period-terminated block whose clauses are separated by semicolons, so a period-only
split leaves the matching clause buried in a 768-character span and the best reachable ratio
against Article 13(3)(d) is 0.3621, superseding 0.2968 under the autojunk correction, far below
the floor either way: the pick passes and the detector reports nothing. Segmenting on semicolons
as well reaches 0.8982 on the same pair, unmoved by that correction, so the comparison the
segmenter choice rests on is the same one.

Case A and case B are not observations this instrument will judge. Both are positives published
in eval/test_frame_rejections.jsonl before this instrument existed, on picks already rejected.
Selecting a segmenter that catches two pre-published positives is calibrating a detector against
held-out ground truth. Two conditions keep that true and are both met here: the reporting floor
never moves, and the segmenter is frozen and committed before any single-hop span is designated.

EXCLUSIONS ARE REPORTED, NOT PERFORMED SILENTLY. Two predicates remove segments that cannot carry
a claim, and every scan block ships the count each removed and the predicate that removed it, so
a reviewer sees the whole funnel and can disagree on the record.

Every block carries its own command and predicate. The duplication_scan blocks already committed
in eval/test_query_verification.jsonl carry neither, and their ratios cannot be re-derived from
the repository. That is a reproducibility gap in those blocks, not a defect in their verdicts,
which rest on individual verification rather than on a ratio.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison

DATA = REPO_ROOT / "data"
CHUNKS = DATA / "chunks"

# Deliberately outside data/retrieval/ and git-ignored via the embeddings_cache/ rule in
# .gitignore. Nothing this module writes can reach the frozen retrieval artifacts.
CACHE = REPO_ROOT / "embeddings_cache"
SEGMENT_VECTORS = CACHE / "segment_embeddings.npy"
SEGMENT_INDEX = CACHE / "segment_index.json"

# The manifest DOES ship. It is a few kilobytes and it is what keeps the dense arm checkable
# without the 40.6 MB cache: a reviewer regenerates and compares one hash rather than trusting
# the reported ranks.
MANIFEST = REPO_ROOT / "eval" / "segment_embedding_manifest.json"

SEGMENTER_ID = "comparable_segments/1"

# The text the chunker recorded between two chunks of the same unit. NOT a chosen separator:
# every one of the 144 inter-chunk gaps in the normalised files is exactly this string, and
# BLOCK_SEPARATOR in src/ingest/eu_ai_act.py, nist_ai_100_1.py and nist_pdf_common.py is the same
# value, because it is what ingest wrote. Joining on it reconstructs the unit's source text on
# 1150 of 1150 units; joining on "" reconstructs it on 1053 and fabricates a token on the other 97.
CHUNK_JOIN = "\n"

DOCUMENTS = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")

# Matches the floor already recorded in every committed duplication_scan block. Never moves.
LEXICAL_FLOOR = 0.60

# Fixed before any observation, so it cannot be fitted to a distribution the way a floor could.
DENSE_TOP_N = 5

# Sentence terminators plus the semicolon. The semicolon is load-bearing: see the module docstring
# and test_period_only_segmentation_is_blind_to_the_published_case.
_SEGMENT_BOUNDARY = re.compile(r"(?<=[.!?;])\s+|\n+")

# Hyphen folding is load-bearing: without it the published 0.940 case reproduces at 0.9310 rather
# than 0.940, because the pair differs by "law-enforcement" against "law enforcement".
_NON_ALNUM = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")

DETERMINISM_NOTE = (
    "Two full generations from a clean state on one machine produced byte-identical caches. The "
    "pinned ONNX session is single-threaded with a fixed graph optimisation level, which is what "
    "makes this hold, and the same property is what data/retrieval/retrieval_manifest.json "
    "records for the corpus embeddings. Verified before this digest was committed, because a "
    "digest that is silently not deterministic is worse than no digest."
)

ALPHABETIC_PREDICATE = "the segment carries at least one alphabetic word"
HEADING_PREDICATE = (
    "the segment is byte-identical, after stripping surrounding whitespace, to its own unit's "
    "unit_label as recorded in data/chunks/<doc>.chunks.jsonl. Own label only: a segment equal to "
    "some OTHER unit's label is kept, because that is a content match rather than a heading"
)

def ratio_matcher(a: str = "", b: str = "") -> difflib.SequenceMatcher:
    """The one constructor behind every committed ratio and every committed opcode set.

    autojunk is disabled. difflib's default treats a character appearing in more than one percent
    of the second sequence as junk once that sequence reaches 200 elements, a heuristic built for
    diffing source files and wrong for similarity between prose spans: it makes the score depend
    on the length of one side. Measured on the pair that exposed it,
    nist_playbook:sub_MANAGE_4.3.ai_transparency_resources against
    sub_MANAGE_4.2.ai_transparency_resources, a 133-character sequence against a 209-character
    one that is a near prefix of it, the default junks sixteen characters and returns 0.2865
    where autojunk=False returns 0.7719. A ratio field exists to record similarity, so a
    length-triggered artifact cannot be what it records.

    Every call site that feeds a committed number is routed here. The two deliberate exemptions
    are named in tests/test_test_query_verification.py, both short-string controls with no
    exposure.
    """
    return difflib.SequenceMatcher(None, a, b, autojunk=False)


LEXICAL_PREDICATE = (
    "difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() over character sequences, built "
    "through src.goldset.attributability.ratio_matcher, where a is the normalised designated span "
    "and b is a normalised corpus segment. Normalisation is normalise_for_comparison, then "
    "casefold, then every non-alphanumeric character to a space, then whitespace collapse. "
    "Segments come from comparable_segments. Every pair at or above the floor is reported. The "
    "floor decides nothing. autojunk is disabled because difflib's default makes the score depend "
    "on the length of the second sequence; see ratio_matcher for the measured case."
)

DENSE_PREDICATE = (
    "Cosine of the designated span's embedding against the SEGMENT embeddings in "
    "embeddings_cache/, over the same comparable_segments the lexical arm uses. The span and "
    "every segment pass through normalise_for_comparison and the pinned ONNX path, the same "
    "input normalisation and the same model the retriever uses, and both sides are L2-normalised "
    "so cosine is the dot product. Units are scored by the maximum cosine over their segments. "
    "The top N non-gold units are reported with no floor. Nothing is excluded by score."
)


def normalise_for_lexical(text: str) -> str:
    """Comparison form for the lexical arm."""
    folded = normalise_for_comparison(text).lower()
    return _WS.sub(" ", _NON_ALNUM.sub(" ", folded)).strip()


def carries_alphabetic_content(text: str) -> bool:
    """Well-formedness predicate: a comparable segment carries at least one alphabetic word.

    Added after a check against the twelve committed rows, where segmenting EU articles yields
    bare paragraph numbers and "1." against "1." scores 1.0. The module previously argued no
    length filter was needed because a short segment cannot reach the floor against a long span.
    That holds for a long designated span and is false for short against short, and it was
    written as a belief rather than measured.

    A well-formedness condition, not a score threshold. It removes segments carrying no
    alphabetic content whatever their score, and cannot change the ratio or the rank of any pair
    that does carry alphabetic content, so it could not have been tuned to any observation.
    """
    return any(token.isalpha() for token in normalise_for_lexical(text).split())


def is_own_heading(text: str, unit_label: str | None) -> bool:
    """The segment is its unit's own recorded heading, which segmentation dragged into content.

    Not a cut point. A length rule or a score cutoff would be fitted, because its threshold is
    chosen by looking at where the offenders fall. Byte identity against a label recorded in
    committed chunk metadata is a structural fact about the corpus, knowable without seeing a
    single pair.

    Own label only, and the narrowness is load-bearing. Enumerated over all 1150 units: 341 of
    14770 segments equal their own unit's label, none longer than two words or 17 characters, and
    a further 16 segments equal some OTHER unit's label. A broad any-label form would remove
    those 16. They are kept.
    """
    return unit_label is not None and text.strip() == unit_label.strip()


def segments(text: str) -> list[str]:
    """Raw segmentation: sentence terminators, semicolons and newlines. No length filter."""
    return [s.strip() for s in _SEGMENT_BOUNDARY.split(text) if s and s.strip()]


def comparable_segments(text: str, unit_label: str | None = None) -> list[str]:
    """The one segmentation both arms consume: raw segments minus what cannot carry a claim."""
    return [
        s
        for s in segments(text)
        if carries_alphabetic_content(s) and not is_own_heading(s, unit_label)
    ]


def segmentation_funnel(text: str, unit_label: str | None) -> dict:
    """The full funnel for one unit, so an exclusion is reported rather than performed silently."""
    raw = segments(text)
    no_alpha = [s for s in raw if not carries_alphabetic_content(s)]
    heading = [s for s in raw if carries_alphabetic_content(s) and is_own_heading(s, unit_label)]
    return {
        "raw_segments": len(raw),
        "removed_no_alphabetic_word": len(no_alpha),
        "removed_own_heading": len(heading),
        "comparable_segments": len(raw) - len(no_alpha) - len(heading),
    }


def unit_of(chunk_id: str) -> str:
    """The unit a chunk belongs to. A single-chunk unit's chunk id equals its unit id."""
    return chunk_id.split("#", 1)[0]


@dataclass(frozen=True)
class Corpus:
    """Frozen corpus text, loaded once and reused across spans."""

    unit_text: dict[str, str]
    unit_label: dict[str, str | None]
    unit_segments: dict[str, list[str]]
    funnel: dict[str, int]

    @classmethod
    def load(cls) -> Corpus:
        unit_text: dict[str, str] = {}
        unit_label: dict[str, str | None] = {}
        for doc in DOCUMENTS:
            for line in (CHUNKS / f"{doc}.chunks.jsonl").read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                unit = unit_of(row["chunk_id"])
                previous = unit_text.get(unit)
                unit_text[unit] = (
                    row["text"] if previous is None else previous + CHUNK_JOIN + row["text"]
                )
                unit_label.setdefault(unit, row.get("unit_label"))
        unit_segments = {
            u: comparable_segments(t, unit_label[u]) for u, t in sorted(unit_text.items())
        }
        totals = {
            "raw_segments": 0,
            "removed_no_alphabetic_word": 0,
            "removed_own_heading": 0,
            "comparable_segments": 0,
        }
        for u, t in unit_text.items():
            for k, v in segmentation_funnel(t, unit_label[u]).items():
                totals[k] += v
        return cls(
            unit_text=unit_text,
            unit_label=unit_label,
            unit_segments=unit_segments,
            funnel=totals,
        )

    def ordered_segments(self) -> list[tuple[str, str]]:
        """Every comparable segment as (unit, segment), in a fixed order the cache is built on."""
        return [(u, s) for u in sorted(self.unit_segments) for s in self.unit_segments[u]]

    def segmentation_fingerprint(self) -> str:
        """sha256 over the exact ordered segmentation, so a segmenter change invalidates a cache.

        Fingerprinting the output rather than the source is exact: any change to the boundary
        pattern or to either predicate changes this string, and no change to them can leave it
        unchanged.
        """
        payload = json.dumps(self.ordered_segments(), ensure_ascii=False, sort_keys=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def exclusion_report(corpus: Corpus) -> dict:
    """The corpus-wide funnel, shipped in every scan block."""
    return {
        "starting_population": corpus.funnel["raw_segments"],
        "removed_no_alphabetic_word": {
            "count": corpus.funnel["removed_no_alphabetic_word"],
            "predicate": ALPHABETIC_PREDICATE,
        },
        "removed_own_heading": {
            "count": corpus.funnel["removed_own_heading"],
            "predicate": HEADING_PREDICATE,
        },
        "comparable_segments": corpus.funnel["comparable_segments"],
    }


def lexical_arm(
    span: str,
    gold_units: set[str],
    corpus: Corpus,
    floor: float = LEXICAL_FLOOR,
) -> dict:
    """Every corpus segment outside the gold units whose ratio against the span reaches floor.

    quick_ratio and real_quick_ratio are documented upper bounds on ratio, so discarding a
    candidate whose upper bound is below the floor cannot discard a real hit.
    test_prefilter_does_not_change_the_result pins that against an unfiltered pass.
    """
    target = normalise_for_lexical(span)
    matcher = ratio_matcher(target, "")
    hits: list[dict] = []
    for unit, segs in sorted(corpus.unit_segments.items()):
        if unit in gold_units:
            continue
        for segment in segs:
            candidate = normalise_for_lexical(segment)
            if not candidate:
                continue
            matcher.set_seq2(candidate)
            if matcher.real_quick_ratio() < floor or matcher.quick_ratio() < floor:
                continue
            ratio = matcher.ratio()
            if ratio >= floor:
                hits.append({"unit": unit, "ratio": round(ratio, 4), "segment": segment})
    hits.sort(key=lambda h: (-h["ratio"], h["unit"], h["segment"]))
    return {
        "floor": floor,
        "floor_decides_nothing": (
            "The floor bounds what is reported, not what is admissible. Every pair at or above it "
            "ships so a reviewer can disagree in the open."
        ),
        "predicate": LEXICAL_PREDICATE,
        "command": (
            "python -c \"from src.goldset.attributability import Corpus, lexical_arm; "
            'print(lexical_arm(SPAN, GOLD_UNITS, Corpus.load()))"'
        ),
        "reproducibility_level": 1,
        "segments_compared": sum(
            len(s) for u, s in corpus.unit_segments.items() if u not in gold_units
        ),
        "units_compared": sum(1 for u in corpus.unit_segments if u not in gold_units),
        "top_ratio": hits[0]["ratio"] if hits else None,
        "pairs_at_or_above_floor": hits,
    }


def load_segment_cache(corpus: Corpus):
    """The cached segment embeddings, or None when absent. Refuses a stale cache.

    A cache built from a different segmentation would silently score the wrong text, which is the
    both-sides-absent failure V20 exists to catch, so the fingerprint mismatch raises rather than
    returning None. Absent is a skip; stale is an error.
    """
    if not (SEGMENT_VECTORS.exists() and SEGMENT_INDEX.exists()):
        return None
    index = json.loads(SEGMENT_INDEX.read_text(encoding="utf-8"))
    current = corpus.segmentation_fingerprint()
    if index.get("segmentation_fingerprint") != current:
        raise ValueError(
            "segment embedding cache is stale: it was built from segmentation "
            f"{index.get('segmentation_fingerprint')!r} and the current segmenter produces "
            f"{current!r}. Regenerate with src/goldset/build_segment_embeddings.py."
        )
    vectors = np.load(SEGMENT_VECTORS)
    if vectors.shape[0] != index["n_segments"]:
        raise ValueError(
            f"cache has {vectors.shape[0]} vectors against {index['n_segments']} indexed segments"
        )
    return vectors, index


def dense_arm(
    span: str,
    gold_units: set[str],
    corpus: Corpus,
    session,
    top_n: int = DENSE_TOP_N,
) -> dict:
    """Top N non-gold units by cosine of the span embedding against SEGMENT embeddings."""
    from src.retrieve.embed import embed_texts

    loaded = load_segment_cache(corpus)
    if loaded is None:
        raise FileNotFoundError(
            "no segment embedding cache. Build it with src/goldset/build_segment_embeddings.py; "
            "it is deliberately not committed."
        )
    vectors, index = loaded
    pairs = corpus.ordered_segments()
    vector = embed_texts([normalise_for_comparison(span)], session)[0]
    scores = vectors @ vector
    best: dict[str, tuple[float, str]] = {}
    for (unit, segment), score in zip(pairs, scores, strict=True):
        if unit in gold_units:
            continue
        if unit not in best or score > best[unit][0]:
            best[unit] = (float(score), segment)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))[:top_n]
    return {
        "top_n": top_n,
        "no_floor": (
            "Every non-gold unit is scored and a fixed N is reported. N was fixed before any "
            "observation, so it cannot be fitted to the distribution the way a floor could."
        ),
        "predicate": DENSE_PREDICATE,
        "command": (
            "python -c \"from src.goldset.attributability import Corpus, dense_arm, onnx_session; "
            'print(dense_arm(SPAN, GOLD_UNITS, Corpus.load(), onnx_session()))"'
        ),
        "reproducibility_level": 3,
        "reproducibility_note": (
            "Level 3 in data/retrieval/retrieval_manifest.json: regenerating an embedding from "
            "ONNX at the pinned revision reproduces rankings, not bytes. The pinned model is "
            "deliberately outside the offline reproducibility set, so a reviewer without it "
            "re-derives the lexical arm exactly and the dense arm not at all."
        ),
        "model_repo": index["model_repo"],
        "model_revision": index["model_revision"],
        "segments_scored": len(pairs),
        "units_scored": len(best),
        "top_units": [
            {"unit": u, "cosine": round(c, 6), "segment": seg} for u, (c, seg) in ranked
        ],
    }


def onnx_session():
    """The pinned ONNX session, or None when the model or its dependencies are absent.

    TWO OUTCOMES THAT MUST NOT LOOK ALIKE. Absence returns None, so the dense arm skips: the model
    is deliberately outside the offline reproducibility set and a fresh clone cannot reach it, which
    is a skip and not a failure. A weight that is present and fails its pinned SHA-256 raises,
    because that is not absence, it is an integrity failure, and a check whose failure is
    indistinguishable from "not installed" is not a check at all.

    This caught every exception and returned None until the two were separated, so a tampered weight
    reported as an uncached one and the dense arm skipped quietly. tests/test_attributability.py
    pins all three paths, the mismatch and both absences, so the swallow cannot return without a
    failing test.

    The two absence paths fail at different points and are both kept: `huggingface_hub` is missing
    in a default install, and `onnxruntime` can be missing after the weight has been fetched and
    verified.
    """
    from src.retrieve.embed import download_onnx, make_session

    try:
        path = download_onnx()
    except ValueError:
        # The pinned checksum did not match. Present and wrong, not absent.
        raise
    except Exception:
        return None

    try:
        return make_session(path)
    except Exception:
        return None


def scan(span: str, gold_units, corpus: Corpus | None = None, session=None) -> dict:
    """Both arms over one designated span, in a form that drops into a verification row."""
    corpus = corpus if corpus is not None else Corpus.load()
    gold = set(gold_units)
    block = {
        "designated_span": span,
        "gold_units_excluded": sorted(gold),
        "segmenter": {
            "boundary": "sentence terminators, semicolons and newlines",
            "fingerprint": corpus.segmentation_fingerprint(),
            "shared_by_both_arms": True,
        },
        "exclusion_funnel": exclusion_report(corpus),
        "lexical_arm": lexical_arm(span, gold, corpus),
    }
    if session is None:
        # A not-run block states what would have run. The reviewer who reaches it is precisely
        # the one without the model, so a bare reason string is a dead end for the reader who
        # most needs the predicate and the command.
        block["dense_arm"] = {
            "ran": False,
            "reason": (
                "No ONNX session was supplied, which is what onnx_session returns when the pinned "
                "model is not already cached. The model is deliberately outside the offline "
                "reproducibility set, so its absence is recorded rather than silently omitted."
            ),
            "predicate": DENSE_PREDICATE,
            "command": (
                "python -c \"from src.goldset.attributability import Corpus, dense_arm, "
                'onnx_session; print(dense_arm(SPAN, GOLD_UNITS, Corpus.load(), onnx_session()))"'
            ),
            "reproducibility_level": 3,
            "top_n": DENSE_TOP_N,
        }
    else:
        block["dense_arm"] = {"ran": True, **dense_arm(span, gold, corpus, session)}
    return block
