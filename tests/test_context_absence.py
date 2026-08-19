"""C2, the completeness predicate, tested against measured behaviour throughout.

A PREDICTION IN eval/layer_predictions.md IS CONTRADICTED HERE, and the tests assert what
the code does rather than what that file predicted. Section 6.3 predicts the
context-absence flag fires on exactly seven near-miss rows "and does not fire on
test_45", and lists "the flag firing on test_45" as a condition that would contradict it.
It fires on all eight. The prediction was written from the gold's point of view: test_45's
anchor block was retrieved at rank 7, so from the gold side there is nothing missing. From
the layer's side the same query names four real units and three of them are genuinely
absent from the context set, the AI 100-1, AI 600-1 and Playbook MAP 5.1 subcategory
statements, and no predicate confined to the readable surface can rule those out without
knowing which of the four is the answer, which is the gold.

Three candidate predicates were measured over all fifty rows before this file was written,
and all three fire on all eight near-miss rows: any resolved unit absent from the context
set; only units the query itself named; and only the most specific query referent. The
contradiction is recorded rather than repaired, per V14 and S6, and eval/layer_predictions.md
is left uncorrected, because a contradicted prediction that gets edited is not a prediction.

What the stratum delivers is unchanged and is recovery, not detection: seven of seven on
the missed rows, with the query-construction attribution locked beside it.

WHAT THIS FILE MAY READ AND THE MODULE MAY NOT. This file opens
eval/test_retrieval_results.json and data/chunks/*.chunks.jsonl. The firewall binds the
operational layer's runtime inputs, not the measurement. The module under test opens
nothing at all and cannot reach a chunk record: retrieved context enters as
RetrievedChunk, which carries the three admitted values and no others.
"""

from __future__ import annotations

import ast
import builtins
import json
from dataclasses import fields, is_dataclass

import pytest

from src.complete.absence import (
    CompletenessReport,
    RetrievedChunk,
    assess,
    chunk_belongs_to_unit,
    context_absence_fires,
    non_resolution_fires,
    query_reference_absent,
    unit_is_in_context,
)
from src.complete.references import load_unit_index
from src.ingest.corpus_integrity import REPO_ROOT
from tests.test_reference_grammar import BARRED_ARTIFACTS

EVAL_DIR = REPO_ROOT / "eval"
CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
ABSENCE_MODULE = REPO_ROOT / "src" / "complete" / "absence.py"

NEAR_MISS_GOLD = {
    "test_43": "nist_playbook:sub_GOVERN_2.3.ai_transparency_resources",
    "test_44": "nist_playbook:sub_MANAGE_3.1.ai_transparency_resources",
    "test_45": "nist_playbook:sub_MAP_5.1.ai_transparency_resources",
    "test_46": "nist_playbook:sub_MAP_3.4.ai_transparency_resources",
    "test_47": "nist_playbook:sub_MEASURE_2.5.ai_transparency_resources",
    "test_48": "nist_playbook:sub_MANAGE_4.2.ai_transparency_resources",
    "test_49": "nist_playbook:sub_MANAGE_1.3.ai_transparency_resources",
    "test_50": "nist_playbook:sub_MANAGE_4.3.ai_transparency_resources",
}
# test_45's anchor came back at rank 7. Every other row of the stratum missed its anchor.
NEAR_MISS_ANCHOR_RETRIEVED = {"test_45"}

SINGLE_HOP_ABSENT = {
    "test_21": 9, "test_22": 17, "test_23": 9, "test_24": 24, "test_25": 1, "test_26": 3,
    "test_27": 7, "test_28": 12, "test_29": 14, "test_30": 2, "test_31": 9,
    "test_32": 5, "test_33": 5, "test_34": 0, "test_35": 21, "test_36": 2,
    "test_37": 5, "test_38": 3,
}
# eval/layer_predictions.md section 4, as corrected at e87ef39.
ADVERSARIAL_ABSENT = {
    "test_01": 27, "test_02": 11, "test_03": 19, "test_04": 21,
    "test_05": 20, "test_06": 7, "test_07": 6, "test_08": 12,
}
FABRICATED = {
    "test_04": "Article 114", "test_05": "Article 181",
    "test_06": "GOVERN 1.8", "test_07": "GOVERN 7.1",
}
NO_CITATION_ROWS = ("test_01", "test_02", "test_03", "test_08")
# Predicate (a) is silent only where the row resolved no absent unit at all. Section 6.4
# names test_34 as the one row of the fifty at zero absent references; test_39 is the
# action row whose seven references were all already in the context set.
BROAD_SILENT_ROWS = {"test_34", "test_39"}
# Predicate (b), measured. It misses three of the ten recovery rows, which is why it is a
# diagnostic and not the augmentation trigger.
QUERY_ABSENT_ROWS = {
    "test_09", "test_11", "test_29",
    "test_43", "test_44", "test_45", "test_46", "test_47", "test_48", "test_49", "test_50",
}
RECOVERY_ROWS_MISSED_BY_PREDICATE_B = {"test_10", "test_19", "test_41"}


@pytest.fixture(scope="module")
def unit_index():
    return load_unit_index()


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
def reports(rows, chunk_records, unit_index):
    """assess() over every committed row. The three permitted fields are chosen here."""
    built = {}
    for row_id, row in rows.items():
        context = [
            RetrievedChunk(
                chunk_id=chunk_id,
                text=chunk_records[chunk_id]["text"],
                unit_label=chunk_records[chunk_id]["unit_label"],
            )
            for chunk_id in row["top10"]
        ]
        built[row_id] = assess(row["query"], context, unit_index)
    return built


# ------------------------------------------------------- the contradicted prediction


@pytest.mark.parametrize("row_id", sorted(NEAR_MISS_GOLD))
def test_context_absence_fires_on_all_eight_near_miss_rows(row_id, reports):
    """MEASURED, AND IT CONTRADICTS eval/layer_predictions.md SECTION 6.3.

    That section predicts the flag fires on exactly seven rows and "does not fire on
    test_45", naming "the flag firing on test_45" as a contradicting condition. It fires
    on all eight. test_45's query names four real units and three of them are absent from
    its context set even though its anchor block was retrieved at rank 7. The predictions
    file is deliberately not corrected; this assertion is the record of what the code does
    and the delta between the two documents is the finding.
    """
    report = reports[row_id]
    assert context_absence_fires(report) is True
    assert query_reference_absent(report) is True


@pytest.mark.parametrize("row_id", sorted(NEAR_MISS_GOLD))
def test_the_near_miss_gold_unit_is_absent_exactly_where_its_anchor_was_missed(row_id, reports):
    """The signal that does discriminate, and it is about the gold unit rather than the flag.

    On the seven missed rows the row's own gold block is among the absent units, which is
    what corrective re-retrieval acts on. On test_45 it is not, because it was retrieved.
    A flag firing on all eight and a recovery set covering seven are different facts and
    this test holds them apart.
    """
    expected_absent = row_id not in NEAR_MISS_ANCHOR_RETRIEVED
    assert (NEAR_MISS_GOLD[row_id] in reports[row_id].absent_units) is expected_absent


def test_exactly_seven_near_miss_rows_carry_their_gold_unit_as_absent(reports):
    recoverable = sorted(
        row_id for row_id, gold in NEAR_MISS_GOLD.items()
        if gold in reports[row_id].absent_units
    )
    assert recoverable == ["test_43", "test_44", "test_46", "test_47", "test_48",
                           "test_49", "test_50"]


# ------------------------------------------------------- non-resolution, signal two


@pytest.mark.parametrize("row_id,surface", sorted(FABRICATED.items()))
def test_each_fabricated_identifier_resolves_to_nothing(row_id, surface, reports, rows):
    """Asserted individually rather than by count, and the surface is checked to be present
    in the query text, so a row passing because the grammar missed it entirely cannot."""
    report = reports[row_id]
    assert surface in rows[row_id]["query"]
    assert non_resolution_fires(report) is True
    unresolved = [r.surface for r in report.unresolved_references]
    assert unresolved == [surface]


@pytest.mark.parametrize("row_id", NO_CITATION_ROWS)
def test_non_resolution_is_silent_where_no_identifier_is_named(row_id, reports):
    """The three ISO rows and the out-of-domain row. This component supplies no abstention
    signal on them at all, which is a stated limit rather than a gap."""
    report = reports[row_id]
    assert non_resolution_fires(report) is False
    assert report.unresolved_references == ()


# ------------------------------------------------------- the committed per-row figures


def test_single_hop_per_row_absent_counts_reproduce_the_predictions_file(reports):
    observed = {row_id: len(reports[row_id].absent_units) for row_id in SINGLE_HOP_ABSENT}
    assert observed == SINGLE_HOP_ABSENT


def test_adversarial_per_row_absent_counts_reproduce_the_corrected_table(reports):
    """Section 4 as corrected at e87ef39: test_08 at 12, the eight summing to 123."""
    observed = {row_id: len(reports[row_id].absent_units) for row_id in ADVERSARIAL_ABSENT}
    assert observed == ADVERSARIAL_ABSENT
    assert sum(observed.values()) == 123


def test_the_external_filter_drop_events_and_rows_are_stable(reports):
    events = sum(len(report.dropped_references) for report in reports.values())
    rows_with_drops = sum(1 for report in reports.values() if report.dropped_references)
    assert (events, rows_with_drops) == (44, 13)


def test_broad_absence_is_silent_on_exactly_two_rows(reports):
    """Predicate (a) over the fifty. Its silence lands on the two rows the predictions file
    records at zero absent units, and nowhere else."""
    silent = {row_id for row_id, report in reports.items() if not context_absence_fires(report)}
    assert silent == BROAD_SILENT_ROWS
    assert len(reports) - len(silent) == 48


def test_query_reference_absence_fires_on_eleven_rows(reports):
    """Predicate (b), enumerated rather than counted."""
    firing = {row_id for row_id, report in reports.items() if query_reference_absent(report)}
    assert firing == QUERY_ABSENT_ROWS


def test_predicate_b_misses_three_recovery_rows_and_so_cannot_be_the_trigger(reports):
    """The measurement that disqualifies (b) from triggering augmentation on its own.

    test_10, test_19 and test_41 recover from references printed in retrieved text or in a
    unit_label, never in the query, so a trigger confined to query references would not
    fetch on them at all.
    """
    for row_id in RECOVERY_ROWS_MISSED_BY_PREDICATE_B:
        assert query_reference_absent(reports[row_id]) is False
        assert context_absence_fires(reports[row_id]) is True


# ------------------------------------------------------- the membership predicate


def test_the_lexical_membership_rule_agrees_with_parent_id_on_every_committed_chunk(
    chunk_records,
):
    """The equivalence that lets C2 decide membership without reading parent_id, which the
    firewall bars. Every chunk belongs to its own parent under the lexical rule."""
    agreeing = sum(
        1 for record in chunk_records.values()
        if chunk_belongs_to_unit(record["chunk_id"], record["parent_id"])
    )
    assert agreeing == len(chunk_records) == 1294


def test_the_lexical_membership_rule_reproduces_parent_id_absent_sets_on_every_row(
    rows, chunk_records, reports
):
    """The same equivalence at row level: the absent set C2 computes from chunk ids alone
    equals the one computed from the barred parent_id field, on all fifty rows."""
    for row_id, row in rows.items():
        units_by_parent = {chunk_records[c]["parent_id"] for c in row["top10"]}
        by_parent = tuple(
            unit for unit in reports[row_id].resolved_units if unit not in units_by_parent
        )
        assert by_parent == reports[row_id].absent_units, row_id


def test_a_sibling_block_does_not_satisfy_its_subcategory_statement():
    """Without the '#' separator rule, bare containment would collapse these."""
    assert not chunk_belongs_to_unit(
        "nist_playbook:sub_MEASURE_2.2.about", "nist_playbook:sub_MEASURE_2.2"
    )
    assert not chunk_belongs_to_unit(
        "nist_playbook:sub_MEASURE_2.2.references#p1", "nist_playbook:sub_MEASURE_2.2"
    )
    assert chunk_belongs_to_unit(
        "nist_playbook:sub_MEASURE_2.2.references#p1", "nist_playbook:sub_MEASURE_2.2.references"
    )


def test_a_shorter_article_id_does_not_swallow_a_longer_one():
    """art_11 must not match art_113, the trap a prefix rule without a separator falls into."""
    assert not chunk_belongs_to_unit("eu_ai_act:art_113", "eu_ai_act:art_11")
    assert chunk_belongs_to_unit("eu_ai_act:art_60#p2", "eu_ai_act:art_60")
    assert chunk_belongs_to_unit("eu_ai_act:art_113", "eu_ai_act:art_113")


def test_unit_is_in_context_is_false_for_an_empty_context():
    assert unit_is_in_context("eu_ai_act:art_6", []) is False


# ------------------------------------------------------- firewall at the boundary


def test_retrieved_context_carries_the_three_admitted_values_and_no_others():
    """structural_path and parent_id are unreachable rather than declined: the type has no
    such attribute, so no future edit can read one without changing this contract."""
    assert is_dataclass(RetrievedChunk)
    assert [f.name for f in fields(RetrievedChunk)] == ["chunk_id", "text", "unit_label"]
    chunk = RetrievedChunk(chunk_id="eu_ai_act:art_6", text="x", unit_label="Article 6")
    assert not hasattr(chunk, "structural_path")
    assert not hasattr(chunk, "parent_id")
    with pytest.raises(Exception):
        chunk.text = "mutated"


def test_the_completeness_report_is_frozen():
    assert is_dataclass(CompletenessReport)
    report = assess("no references here", [], frozenset())
    with pytest.raises(Exception):
        report.absent_units = ()


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


def test_assess_opens_no_barred_artifact(monkeypatch, unit_index):
    """The whole predicate exercised under the guard, on a context carrying every
    reference kind the grammar knows."""
    context = [
        RetrievedChunk("nist_playbook:sub_MAP_5.1.about", "See Article 13 of this Regulation.",
                       "MAP 5.1 About"),
        RetrievedChunk("eu_ai_act:art_60#p2", "in accordance with Article 49(5); and Annex IX",
                       "Article 60"),
        RetrievedChunk("nist_ai_600_1:act_GV-4.3-001", "GV4.3--001 do the thing", "GV-4.3-001"),
    ]
    _guarded_open(monkeypatch)
    report = assess(
        "Which AI transparency resources does the Playbook list under MAP 5.1?",
        context,
        unit_index,
    )
    assert report.references
    assert report.absent_units
    assert context_absence_fires(report) is True


def test_the_barred_path_guard_raises_when_a_barred_artifact_is_opened(monkeypatch):
    """The red companion. Without it the guard could be a no-op and the test above would
    pass by blindness."""
    _guarded_open(monkeypatch)
    with pytest.raises(_BarredPath):
        with open(EVAL_DIR / "test_retrieval_results.json", encoding="utf-8"):
            pass
    with pytest.raises(_BarredPath):
        with open(CHUNKS_DIR / "nist_ai_600_1.relations.jsonl", encoding="utf-8"):
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


def test_the_absence_module_names_no_barred_artifact_and_no_barred_field_in_code():
    """No barred path is reachable as a string the code could hand to open(), and the two
    unit-structure fields appear nowhere in code either."""
    literals = " ".join(_code_string_literals(ABSENCE_MODULE.read_text(encoding="utf-8")))
    for barred in BARRED_ARTIFACTS:
        assert barred.rsplit("/", 1)[-1] not in literals, barred
    for field_name in ("structural_path", "parent_id"):
        assert field_name not in literals, field_name


def test_the_barred_artifact_list_matches_the_one_c1_is_held_to():
    """One firewall contract across the package rather than two lists drifting apart."""
    assert "eval/test_queries.jsonl" in BARRED_ARTIFACTS
    assert "data/chunks/nist_ai_600_1.relations.jsonl" in BARRED_ARTIFACTS
    assert "data/retrieval/verbatim_groups.json" in BARRED_ARTIFACTS
    assert len(BARRED_ARTIFACTS) == len(set(BARRED_ARTIFACTS)) == 12
