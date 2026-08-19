"""C3, the corrective pass, held to the augmentation-only invariant on every committed row.

THE INVARIANT IS WHAT MAKES ONE PREDICTION EXACT. eval/layer_predictions.md section 6.4
predicts a single-hop completeness delta of exactly zero on 18 of 18, and the reason it can
say "exactly" rather than "approximately" is that no committed gold chunk may leave a
context set. That is a property of this module and of nothing else, so the delta test and
the prefix test are two views of the same guarantee: if augmentation ever removed,
reordered or truncated the first pass, the delta would move and the prediction would have
been wrong for a reason having nothing to do with retrieval.

WHAT THIS FILE MAY READ AND THE MODULE MAY NOT. This file opens
eval/test_retrieval_results.json for the committed rankings and gold slots. Gold is barred
from the layer and is the whole point of the firewall; it is not barred from the
measurement. Scoring which gold slots an augmented context satisfies therefore lives here
and deliberately not in src/complete/, which carries no function whose only use is reading
gold.
"""

from __future__ import annotations

import ast
import builtins
import json
from dataclasses import fields, is_dataclass

import pytest

from src.complete.absence import RetrievedChunk, chunk_belongs_to_unit, unit_is_in_context
from src.complete.augment import (
    AugmentationResult,
    FetchStore,
    augment,
    fetch_unit,
    load_fetch_store,
)
from src.ingest.corpus_integrity import REPO_ROOT
from tests.test_reference_grammar import BARRED_ARTIFACTS

EVAL_DIR = REPO_ROOT / "eval"
CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
AUGMENT_MODULE = REPO_ROOT / "src" / "complete" / "augment.py"

SINGLE_HOP_ROWS = [f"test_{n}" for n in range(21, 39)]

# eval/layer_predictions.md sections 6.1, 6.2 and 6.3, by row and by unit.
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

# Final context set size per row: ten first-pass chunks plus the chunks of every absent
# resolved unit. Larger than the absent-unit count wherever a fetched unit is multi-chunk.
EXPECTED_SIZE = {
    "test_01": 37, "test_02": 21, "test_03": 29, "test_04": 57, "test_05": 53,
    "test_06": 17, "test_07": 16, "test_08": 23, "test_09": 53, "test_10": 33,
    "test_11": 44, "test_12": 36, "test_13": 17, "test_14": 19, "test_15": 30,
    "test_16": 26, "test_17": 44, "test_18": 20, "test_19": 26, "test_20": 32,
    "test_21": 34, "test_22": 50, "test_23": 25, "test_24": 41, "test_25": 12,
    "test_26": 15, "test_27": 23, "test_28": 37, "test_29": 46, "test_30": 17,
    "test_31": 27, "test_32": 15, "test_33": 15, "test_34": 10, "test_35": 31,
    "test_36": 12, "test_37": 15, "test_38": 13, "test_39": 10, "test_40": 21,
    "test_41": 13, "test_42": 27, "test_43": 37, "test_44": 32, "test_45": 31,
    "test_46": 35, "test_47": 39, "test_48": 38, "test_49": 38, "test_50": 38,
}
# The two rows with no absent resolved unit, so nothing to fetch. Section 6.4 names
# test_34 as the one row of the fifty at zero absent references; test_39's seven
# references were all already in its context set.
UNAUGMENTED_ROWS = {"test_34", "test_39"}


@pytest.fixture(scope="module")
def store():
    return load_fetch_store()


@pytest.fixture(scope="module")
def chunk_records():
    records = {}
    for doc in ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook"):
        for line in (CHUNKS_DIR / f"{doc}.chunks.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            record = json.loads(line)
            records[record["chunk_id"]] = record
    return records


@pytest.fixture(scope="module")
def rows():
    payload = json.loads((EVAL_DIR / "test_retrieval_results.json").read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload["retrieval"]}


@pytest.fixture(scope="module")
def results(rows, chunk_records, store):
    built = {}
    for row_id, row in rows.items():
        first_pass = [
            RetrievedChunk(
                chunk_id=chunk_id,
                text=chunk_records[chunk_id]["text"],
                unit_label=chunk_records[chunk_id]["unit_label"],
            )
            for chunk_id in row["top10"]
        ]
        built[row_id] = augment(row["query"], first_pass, store)
    return built


def _slots_satisfied_by(context, gold_slots):
    """Test-side gold scoring. The layer has no equivalent and must not."""
    return sum(1 for slot in gold_slots if any(unit_is_in_context(u, context) for u in slot))


# ------------------------------------------------------- the augmentation-only invariant


@pytest.mark.parametrize("row_id", [f"test_{n:02d}" for n in range(1, 51)])
def test_the_first_pass_is_an_unmodified_prefix_of_the_final_context(row_id, rows, results):
    """Never removed, never reordered, never truncated, on every committed row.

    Asserted as an ordered prefix rather than as set membership, because a set assertion
    passes on a reordering and reordering is one of the three things the policy forbids.
    """
    row = rows[row_id]
    result = results[row_id]
    assert [chunk.chunk_id for chunk in result.context[:10]] == row["top10"]
    assert [chunk.chunk_id for chunk in result.first_pass] == row["top10"]
    assert result.size >= 10


def test_no_chunk_appears_twice_in_any_final_context(results):
    """A fetched unit has no chunk in the first pass by construction, since it is fetched
    only when none of its chunks is there. This is that construction checked."""
    for row_id, result in results.items():
        ids = [chunk.chunk_id for chunk in result.context]
        assert len(ids) == len(set(ids)), row_id


def test_every_fetched_chunk_belongs_to_a_fetched_unit(results):
    for row_id, result in results.items():
        for chunk in result.fetched_chunks:
            assert any(
                chunk_belongs_to_unit(chunk.chunk_id, unit) for unit in result.fetched_units
            ), (row_id, chunk.chunk_id)


def test_no_bound_is_applied_every_absent_unit_is_fetched(results):
    """Section 5 records the absence of a bound as a named condition. This is the code
    matching it: the fetched-unit list is the absent-unit list, in the same order."""
    for row_id, result in results.items():
        assert result.fetched_units == result.report.absent_units, row_id


# ------------------------------------------------------- the exact single-hop prediction


@pytest.mark.parametrize("row_id", SINGLE_HOP_ROWS)
def test_single_hop_completeness_delta_is_exactly_zero(row_id, rows, results):
    """THE V22 MUTATION TARGET. Dropping the first pass from the assembled context turns
    this red on all eighteen rows, because every one is at recall 1 on the first pass and
    its gold chunk is never among the fetched ones: a satisfied unit is in the context set,
    so it is not absent, so it is not fetched.
    """
    row = rows[row_id]
    before = sum(1 for slot in row["slot_satisfaction"] if slot["satisfied"])
    after = _slots_satisfied_by(results[row_id].context, row["gold_slots"])
    assert before == len(row["gold_slots"])
    assert after - before == 0


# ------------------------------------------------------- recovery and size


def test_the_recovery_set_reproduces_the_predictions_file(rows, results):
    """Row by row and unit by unit, against the units P1 names."""
    observed = {}
    for row_id, row in rows.items():
        recovered = []
        for index, slot in enumerate(row["gold_slots"]):
            if row["slot_satisfaction"][index]["satisfied"]:
                continue
            recovered.extend(u for u in slot if unit_is_in_context(u, results[row_id].context))
        if recovered:
            observed[row_id] = sorted(recovered)
    assert observed == {row_id: sorted(units) for row_id, units in EXPECTED_RECOVERY.items()}


def test_recovery_happens_on_exactly_ten_rows(rows, results):
    recovered_rows = {
        row_id
        for row_id, row in rows.items()
        if any(
            not row["slot_satisfaction"][i]["satisfied"]
            and any(unit_is_in_context(u, results[row_id].context) for u in slot)
            for i, slot in enumerate(row["gold_slots"])
        )
    }
    assert recovered_rows == set(EXPECTED_RECOVERY)


def test_the_final_context_size_per_row(results):
    """Reported per row rather than as a distribution, because a recovered-passage recall
    figure is only readable beside the size of the set it was computed over."""
    assert {row_id: result.size for row_id, result in results.items()} == EXPECTED_SIZE


def test_the_size_is_ten_plus_the_fetched_chunk_count(results):
    for row_id, result in results.items():
        assert result.size == 10 + len(result.fetched_chunks), row_id


def test_exactly_two_rows_are_not_augmented(results):
    """Where nothing resolved absent, the trigger does not fire and the context is the
    first pass unchanged."""
    unaugmented = {row_id for row_id, result in results.items() if not result.triggered}
    assert unaugmented == UNAUGMENTED_ROWS
    for row_id in unaugmented:
        assert results[row_id].size == 10
        assert results[row_id].fetched_chunks == ()


def test_a_multi_chunk_unit_contributes_more_chunks_than_units(results):
    """The fetched chunk count exceeds the fetched unit count wherever a fetched unit is
    split, which is why size is not ten plus the absent-unit count."""
    inflated = {
        row_id
        for row_id, result in results.items()
        if len(result.fetched_chunks) > len(result.fetched_units)
    }
    assert "test_04" in inflated
    assert len(results["test_04"].fetched_units) == 21
    assert len(results["test_04"].fetched_chunks) == 47


# ------------------------------------------------------- fetch mechanics


def test_fetch_unit_returns_the_committed_chunk_order(store):
    fetched = fetch_unit("eu_ai_act:art_60", store)
    assert [chunk.chunk_id for chunk in fetched] == [
        "eu_ai_act:art_60#p1", "eu_ai_act:art_60#p2", "eu_ai_act:art_60#p3"
    ]


def test_fetch_unit_raises_on_a_unit_the_index_does_not_carry(store):
    """An empty fetch and an unknown unit are different facts, and a silent empty would
    make a missing unit look like a unit holding nothing."""
    with pytest.raises(KeyError):
        fetch_unit("eu_ai_act:art_999", store)


def test_the_unit_index_grouping_agrees_with_the_lexical_membership_rule(store, chunk_records):
    """The unit index is an artifact; the lexical rule is a function. Two implementations of
    the same grouping, cross-checked over all 1150 units rather than either trusted."""
    for unit_id, chunk_ids in store.unit_chunks.items():
        lexical = sorted(c for c in chunk_records if chunk_belongs_to_unit(c, unit_id))
        assert sorted(chunk_ids) == lexical, unit_id
    assert len(store.unit_chunks) == 1150
    assert sum(len(v) for v in store.unit_chunks.values()) == 1294


def test_the_store_holds_every_committed_chunk_as_retrieved_context(store, chunk_records):
    assert set(store.chunks) == set(chunk_records)
    assert len(store.chunks) == 1294
    for chunk in store.chunks.values():
        assert isinstance(chunk, RetrievedChunk)


def test_a_fetched_chunk_carries_the_committed_text_and_label(store, chunk_records):
    fetched = fetch_unit("nist_playbook:sub_MAP_5.1.ai_transparency_resources", store)
    assert len(fetched) == 1
    record = chunk_records[fetched[0].chunk_id]
    assert fetched[0].text == record["text"]
    assert fetched[0].unit_label == record["unit_label"]


# ------------------------------------------------------- firewall at the boundary


def test_fetched_chunks_are_the_same_type_the_first_pass_arrives_in():
    """So a barred field is unreachable on a fetched chunk exactly as on a retrieved one."""
    assert [f.name for f in fields(RetrievedChunk)] == ["chunk_id", "text", "unit_label"]
    assert is_dataclass(FetchStore)
    assert is_dataclass(AugmentationResult)


def test_the_augmentation_result_is_frozen(store):
    result = augment("no references here", [], store)
    with pytest.raises(Exception):
        result.context = ()


class _BarredPath(AssertionError):
    pass


def _guarded_open(monkeypatch):
    real_open = builtins.open

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for barred in BARRED_ARTIFACTS:
            if text.endswith(barred):
                raise _BarredPath(f"the layer opened a barred artifact: {barred}")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guard)


def test_loading_the_store_opens_no_barred_artifact(monkeypatch):
    """load_fetch_store reads the unit index and the four chunk stores, all permitted."""
    _guarded_open(monkeypatch)
    loaded = load_fetch_store()
    assert len(loaded.chunks) == 1294
    assert len(loaded.unit_chunks) == 1150


def test_the_corrective_pass_opens_no_barred_artifact(monkeypatch, store):
    _guarded_open(monkeypatch)
    context = [RetrievedChunk("eu_ai_act:art_60#p1", "in accordance with Article 49(5)",
                              "Article 60")]
    result = augment("Which Annex IX points must appear in the registration?", context, store)
    assert result.triggered is True
    assert result.fetched_chunks


def test_the_barred_path_guard_raises_when_a_barred_artifact_is_opened(monkeypatch):
    """The red companion. Without it the two tests above could pass on a no-op guard."""
    _guarded_open(monkeypatch)
    with pytest.raises(_BarredPath):
        with open(EVAL_DIR / "test_frame.json", encoding="utf-8"):
            pass
    with pytest.raises(_BarredPath):
        with open(CHUNKS_DIR / "eu_ai_act.xrefs.jsonl", encoding="utf-8"):
            pass


def _code_string_literals(source: str) -> list[str]:
    """Every string constant in the module's code, docstrings and comments excluded."""
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


def test_the_augment_module_names_no_barred_artifact_and_no_barred_field_in_code():
    literals = " ".join(_code_string_literals(AUGMENT_MODULE.read_text(encoding="utf-8")))
    for barred in BARRED_ARTIFACTS:
        assert barred.rsplit("/", 1)[-1] not in literals, barred
    for field_name in ("structural_path", "parent_id"):
        assert field_name not in literals, field_name


def test_the_package_carries_no_prefix_to_function_map():
    """The barred derivation route, re-asserted now that the package is complete. C1's own
    test scans the same directory; this one fails if a third module reintroduces it."""
    pattern = __import__("re").compile(
        r"[\"']\s*(GV|MP|MS|MG)\s*[\"']\s*:\s*[\"']\s*(GOVERN|MAP|MEASURE|MANAGE)\s*[\"']"
    )
    modules = sorted((REPO_ROOT / "src" / "complete").rglob("*.py"))
    assert len(modules) >= 4
    for module in modules:
        assert not pattern.search(module.read_text(encoding="utf-8")), module.name
