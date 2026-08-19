"""C1, the reference grammar and resolver, tested exhaustively rather than by sample.

THE POPULATION IS ENUMERABLE, so it is enumerated. The audit below runs the grammar over
the query text and the committed text, chunk id and unit_label of every chunk in all
fifty committed top 10 lists, 1550 source strings, and asserts the resulting per-row
figures against the hand derivations in eval/layer_predictions.md. That file was
committed before this module existed, so the assertion is a cross-implementation check
in the sense of V4 and not a restatement of the code.

WHAT THE TEST MAY READ AND THE MODULE MAY NOT. This file opens
eval/test_retrieval_results.json and data/chunks/*.chunks.jsonl. Both are outside the
layer's readable surface as CLAUDE.md defines it, and that is correct: the firewall
binds the operational layer's runtime inputs, not the measurement. The two firewall
tests at the bottom are what hold the module to the narrower surface, by reading its
source and by patching open().
"""

from __future__ import annotations

import ast
import builtins
import json
import re
from pathlib import Path

import pytest

from src.complete import references
from src.complete.references import (
    BLOCK_PHRASES,
    Reference,
    extract,
    load_unit_index,
    resolve,
    resolves,
)
from src.ingest.corpus_integrity import REPO_ROOT

EVAL_DIR = REPO_ROOT / "eval"
CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
COMPLETE_DIR = REPO_ROOT / "src" / "complete"

# Artifacts the firewall bars the layer from opening, by artifact name, mirroring the
# complement of the allowlist as CLAUDE.md states it.
BARRED_ARTIFACTS = (
    "data/chunks/nist_ai_600_1.relations.jsonl",
    "data/chunks/nist_ai_100_1.relations.jsonl",
    "data/chunks/nist_playbook.relations.jsonl",
    "data/chunks/eu_ai_act.xrefs.jsonl",
    "data/chunks/nist_ai_100_1.duplication_map.json",
    "data/retrieval/verbatim_groups.json",
    "data/retrieval/near_duplicate_exceptions.json",
    "eval/test_query_verification.jsonl",
    "eval/test_frame.json",
    "eval/pass_one_designations.jsonl",
    "eval/test_retrieval_results.json",
    "eval/test_queries.jsonl",
)


@pytest.fixture(scope="module")
def unit_index():
    return load_unit_index()


@pytest.fixture(scope="module")
def chunk_store():
    chunks = {}
    for doc in ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook"):
        path = CHUNKS_DIR / f"{doc}.chunks.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            chunks[record["chunk_id"]] = record
    return chunks


@pytest.fixture(scope="module")
def retrieval_rows():
    payload = json.loads((EVAL_DIR / "test_retrieval_results.json").read_text(encoding="utf-8"))
    return payload["retrieval"]


def _row_sources(row, chunk_store):
    """The query text with block composition on, then three fields per retrieved chunk with it off."""
    yield row["query"], True
    for chunk_id in row["top10"]:
        record = chunk_store[chunk_id]
        yield record["text"], False
        yield record["unit_label"], False
        yield chunk_id, False


def _audit_row(row, chunk_store, unit_index):
    retrieved_units = {chunk_store[c]["parent_id"] for c in row["top10"]}
    candidates, drops = [], []
    for source, allow_blocks in _row_sources(row, chunk_store):
        found, dropped = extract(source, allow_block_composition=allow_blocks)
        for reference in found:
            candidates.extend(reference.candidates)
        drops.extend(dropped)
    candidates = list(dict.fromkeys(candidates))
    resolved = [u for u in candidates if u in unit_index]
    absent = [u for u in resolved if u not in retrieved_units]
    missing_gold = set()
    for index, slot in enumerate(row["gold_slots"]):
        if not row["slot_satisfaction"][index]["satisfied"]:
            missing_gold |= set(slot)
    return {
        "absent": absent,
        "recovered": sorted(set(absent) & missing_gold),
        "drop_events": len(drops),
    }


# The committed hand derivations from eval/layer_predictions.md section 6.4, in row order.
SINGLE_HOP_ABSENT = {
    "test_21": 9, "test_22": 17, "test_23": 9, "test_24": 24, "test_25": 1, "test_26": 3,
    "test_27": 7, "test_28": 12, "test_29": 14, "test_30": 2, "test_31": 9,
    "test_32": 5, "test_33": 5, "test_34": 0, "test_35": 21, "test_36": 2,
    "test_37": 5, "test_38": 3,
}
# Sections 6.1, 6.2 and 6.3. Every other row recovers nothing.
EXPECTED_RECOVERY = {
    "test_10": ["eu_ai_act:art_49"],
    "test_19": ["eu_ai_act:art_16"],
    "test_41": ["nist_ai_100_1:sub_MEASURE_2.2", "nist_ai_600_1:sub_MEASURE_2.2",
                "nist_playbook:sub_MEASURE_2.2"],
    "test_43": ["nist_playbook:sub_GOVERN_2.3.ai_transparency_resources"],
    "test_44": ["nist_playbook:sub_MANAGE_3.1.ai_transparency_resources"],
    "test_46": ["nist_playbook:sub_MAP_3.4.ai_transparency_resources"],
    "test_47": ["nist_playbook:sub_MEASURE_2.5.ai_transparency_resources"],
    "test_48": ["nist_playbook:sub_MANAGE_4.2.ai_transparency_resources"],
    "test_49": ["nist_playbook:sub_MANAGE_1.3.ai_transparency_resources"],
    "test_50": ["nist_playbook:sub_MANAGE_4.3.ai_transparency_resources"],
}


def test_the_exhaustive_audit_reproduces_every_committed_recovery(
    retrieval_rows, chunk_store, unit_index
):
    """Row by row rather than by count, so a compensating pair of errors cannot pass."""
    observed = {}
    for row in retrieval_rows:
        result = _audit_row(row, chunk_store, unit_index)
        if result["recovered"]:
            observed[row["id"]] = result["recovered"]
    assert observed == EXPECTED_RECOVERY


def test_the_exhaustive_audit_reproduces_the_single_hop_absent_counts(
    retrieval_rows, chunk_store, unit_index
):
    """The per-row counts, where a grammar regression shows first."""
    rows = {r["id"]: r for r in retrieval_rows}
    observed = {
        row_id: len(_audit_row(rows[row_id], chunk_store, unit_index)["absent"])
        for row_id in SINGLE_HOP_ABSENT
    }
    assert observed == SINGLE_HOP_ABSENT


def test_the_external_filter_drop_events_and_rows_are_stable(
    retrieval_rows, chunk_store, unit_index
):
    """Event count, which needs no dedupe key, and the count of rows carrying a drop.

    A deduped figure needs its key stated to mean anything, so the invariant pinned here
    is the key-free one.
    """
    events, rows_with_drops = 0, 0
    for row in retrieval_rows:
        result = _audit_row(row, chunk_store, unit_index)
        events += result["drop_events"]
        rows_with_drops += 1 if result["drop_events"] else 0
    assert (events, rows_with_drops) == (44, 13)


def test_article_113_resolves_to_the_last_article_of_the_act(unit_index):
    """The V22 mutation target. Narrowing R_ART to two digits must turn this red."""
    found, dropped = extract("From what date does Article 113 apply?")
    assert dropped == []
    assert [r.candidates for r in found] == [("eu_ai_act:art_113",)]
    assert resolve(found[0], unit_index) == ("eu_ai_act:art_113",)


def test_the_external_filter_drops_the_test_18_directive_reference(unit_index):
    """The one occurrence the filter exists to catch, shown red before it is trusted."""
    sentence = (
        "For high-risk AI systems used for law enforcement purposes Article 13 of "
        "Directive (EU) 2016/680 shall apply."
    )
    found, dropped = extract(sentence)
    assert found == []
    assert [(d.surface, d.qualifier) for d in dropped] == [("Article 13", "of Directive")]


def test_the_external_filter_keeps_a_reference_to_this_regulation(unit_index):
    """The companion. A filter that drops everything would pass the test above."""
    sentence = (
        "deployers of high-risk AI systems shall use the information provided under "
        "Article 13 of this Regulation to comply with their obligation"
    )
    found, dropped = extract(sentence)
    assert dropped == []
    assert [r.candidates for r in found] == [("eu_ai_act:art_13",)]


def test_the_external_filter_sees_through_a_parenthesised_subdivision():
    found, dropped = extract("under Article 34(4) of Regulation (EU) 2019/1020, the market")
    assert found == []
    assert [d.qualifier for d in dropped] == ["(4) of Regulation"]


@pytest.mark.parametrize("surface", ["GV-4.3-001", "GV4.3--001"])
def test_both_printed_surfaces_of_the_garbled_action_normalise_to_one_unit(surface, unit_index):
    """The documented PDF defect. The correct form and the damaged one name one unit."""
    found, _ = extract(f"What does {surface} require?")
    assert [r.candidates for r in found] == [("nist_ai_600_1:act_GV-4.3-001",)]
    assert resolves(found[0], unit_index)


def test_a_neighbouring_action_identifier_does_not_collapse_onto_the_garbled_one(unit_index):
    """The negative control on the tolerance. Without it, an over-tolerant pattern passes."""
    found, _ = extract("What does GV-4.3-002 require?")
    assert [r.candidates for r in found] == [("nist_ai_600_1:act_GV-4.3-002",)]
    assert resolve(found[0], unit_index) == ("nist_ai_600_1:act_GV-4.3-002",)


def test_a_subcategory_surface_composes_three_candidates():
    found, _ = extract("What does MEASURE 2.2 require?")
    assert [r.candidates for r in found] == [
        ("nist_ai_100_1:sub_MEASURE_2.2", "nist_ai_600_1:sub_MEASURE_2.2",
         "nist_playbook:sub_MEASURE_2.2")
    ]


def test_a_subcategory_present_in_two_documents_still_resolves(unit_index):
    """AI 600-1 is a profile over a subset, so two of three is normal and is not absence."""
    found, _ = extract("What does GOVERN 2.3 require?")
    hits = resolve(found[0], unit_index)
    assert hits == ("nist_ai_100_1:sub_GOVERN_2.3", "nist_playbook:sub_GOVERN_2.3")
    assert resolves(found[0], unit_index)


@pytest.mark.parametrize(
    "query",
    [
        "Under the EU AI Act, what does Article 114 require?",
        "Under the EU AI Act, what does Article 181 require?",
        "What does GOVERN 1.8 require?",
        "What does GOVERN 7.1 require?",
    ],
)
def test_the_fabricated_identifiers_resolve_to_nothing(query, unit_index):
    """Well formed under the grammar, naming no unit. The abstention signal."""
    found, _ = extract(query)
    assert found, "the fabricated identifier must still be a well-formed surface"
    assert all(resolve(r, unit_index) == () for r in found)
    assert all(not resolves(r, unit_index) for r in found)


def test_block_composition_is_off_by_default():
    found, _ = extract("Which AI transparency resources does the Playbook list under MAP 5.1?")
    kinds = [r.kind for r in found]
    assert "playbook_block" not in kinds


def test_block_composition_on_query_text_reaches_the_block_unit(unit_index):
    found, _ = extract(
        "Which AI transparency resources does the Playbook list under MAP 5.1?",
        allow_block_composition=True,
    )
    blocks = [r for r in found if r.kind == "playbook_block"]
    assert [r.candidates for r in blocks] == [
        ("nist_playbook:sub_MAP_5.1.ai_transparency_resources",)
    ]
    assert resolves(blocks[0], unit_index)


def test_block_phrase_matching_is_longest_phrase_first():
    """'ai transparency resources' contains 'references' nowhere, but 'transparency &
    documentation' and 'about' both appear in ordinary prose, so order must be fixed."""
    assert BLOCK_PHRASES[0][0] == "transparency & documentation"
    found, _ = extract(
        "About the transparency & documentation for MAP 5.1", allow_block_composition=True
    )
    blocks = [r for r in found if r.kind == "playbook_block"]
    assert [r.candidates for r in blocks] == [
        ("nist_playbook:sub_MAP_5.1.transparency_documentation",)
    ]


def test_a_block_phrase_without_a_subcategory_composes_nothing():
    found, _ = extract("Which AI transparency resources exist?", allow_block_composition=True)
    assert found == []


def test_the_playbook_block_vocabulary_covers_every_subcategory(unit_index):
    """Five slugs over seventy-two subcategories, beside the bare statement units."""
    slugs = sorted({slug for _phrase, slug in BLOCK_PHRASES})
    assert slugs == ["about", "ai_transparency_resources", "references",
                     "suggested_actions", "transparency_documentation"]
    for slug in slugs:
        matching = [u for u in unit_index
                    if u.startswith("nist_playbook:sub_") and u.endswith("." + slug)]
        assert len(matching) == 72, slug
    bare = [u for u in unit_index
            if re.fullmatch(r"nist_playbook:sub_[A-Z]+_\d+\.\d+", u)]
    assert len(bare) == 72


# ---------------------------------------------------------------- firewall tests

_PREFIX_MAP = re.compile(
    r"[\"']\s*(GV|MP|MS|MG)\s*[\"']\s*:\s*[\"']\s*(GOVERN|MAP|MEASURE|MANAGE)\s*[\"']"
)


def _prefix_map_hits(source: str) -> list[tuple[str, str]]:
    """Every action-prefix to function-name pair written as a dict entry in source."""
    return [(m.group(1), m.group(2)) for m in _PREFIX_MAP.finditer(source)]


def test_no_prefix_to_function_map_exists_anywhere_under_src_complete():
    """The barred route in code form. Deriving MANAGE 2.2 from MG-2.2-003 is the
    action_subcategory relation in string form, so the map that would do it must not
    exist in this package at all. Asserted by reading source, not by trusting a docstring."""
    modules = sorted(COMPLETE_DIR.rglob("*.py"))
    assert modules, "the package must contain modules for this check to mean anything"
    offenders = {}
    for module in modules:
        hits = _prefix_map_hits(module.read_text(encoding="utf-8"))
        if hits:
            offenders[module.name] = hits
    assert offenders == {}


def test_the_prefix_map_detector_fires_on_the_map_it_exists_to_find():
    """The red companion. A detector that never matches would pass the test above on an
    empty package and on a violating one alike."""
    violating = '_FUNCTION_OF_PREFIX = {"GV": "GOVERN", "MP": "MAP", "MS": "MEASURE", "MG": "MANAGE"}'
    assert _prefix_map_hits(violating) == [
        ("GV", "GOVERN"), ("MP", "MAP"), ("MS", "MEASURE"), ("MG", "MANAGE")
    ]
    assert _prefix_map_hits("nothing to see here") == []


class _BarredPath(AssertionError):
    pass


def _guarded_open(monkeypatch):
    """Patch open() so any barred artifact raises instead of returning a handle."""
    real_open = builtins.open

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for barred in BARRED_ARTIFACTS:
            if text.endswith(barred):
                raise _BarredPath(f"the layer opened a barred artifact: {barred}")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guard)


def test_the_module_opens_no_barred_artifact(monkeypatch):
    """Every public entry point, exercised under the guard."""
    _guarded_open(monkeypatch)
    index = load_unit_index()
    assert len(index) == 1150
    found, dropped = extract(
        "Which AI transparency resources does the Playbook list under MAP 5.1? "
        "See Article 13 of this Regulation and Annex IX and GV-4.3-001.",
        allow_block_composition=True,
    )
    assert found and dropped == []
    for reference in found:
        resolve(reference, index)
        resolves(reference, index)


def test_the_barred_path_guard_raises_when_a_barred_artifact_is_opened(monkeypatch):
    """The red companion. Without it the guard could be a no-op and the test above would
    pass by blindness, which is the V20 failure mode this repository has already paid for."""
    _guarded_open(monkeypatch)
    with pytest.raises(_BarredPath):
        with open(EVAL_DIR / "test_retrieval_results.json", encoding="utf-8"):
            pass
    with pytest.raises(_BarredPath):
        with open(CHUNKS_DIR / "eu_ai_act.xrefs.jsonl", encoding="utf-8"):
            pass


def _code_string_literals(source: str) -> list[str]:
    """Every string constant in the module's CODE, docstrings and comments excluded.

    Comments never reach the AST. Docstrings do, as the first statement of a module,
    class or function, and are excluded here by identity. The distinction is the point:
    naming a barred artifact in prose to explain that it is barred is not opening it,
    and an earlier form of this check read the raw source and failed on exactly that.
    """
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_the_module_names_only_the_unit_index_as_an_artifact_in_code():
    """A second, independent hold on the same property: no barred path is reachable as a
    string the code could hand to open()."""
    source = (COMPLETE_DIR / "references.py").read_text(encoding="utf-8")
    literals = _code_string_literals(source)
    assert "corpus_unit_index.json" in literals
    joined = " ".join(literals)
    for barred in BARRED_ARTIFACTS:
        assert Path(barred).name not in joined, barred


def test_the_literal_scanner_ignores_prose_and_catches_code():
    """The red companion. Without it the scanner could return nothing and pass by blindness."""
    prose_only = '"""Mentions eval/test_frame.json in a docstring."""\nX = 1\n'
    assert _code_string_literals(prose_only) == []
    in_code = 'PATH = "eval/test_frame.json"\n'
    assert _code_string_literals(in_code) == ["eval/test_frame.json"]
    commented = "# eval/test_frame.json in a comment\nX = 1\n"
    assert _code_string_literals(commented) == []


def test_the_reference_dataclass_is_frozen():
    """Frozen so a caller cannot rewrite a resolved candidate after the fact."""
    reference = Reference("eu_article", "Article 6", 0, 9, ("eu_ai_act:art_6",))
    with pytest.raises(Exception):
        reference.kind = "mutated"
    assert references.Reference is Reference
