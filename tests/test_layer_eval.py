"""The layer measurement runner and the artifact it produces.

THE RUNNER IS HARNESS SIDE AND READS GOLD. That is not a firewall breach: the firewall binds the
operational layer's runtime inputs, not the measurement. What has to be true, and is asserted here
rather than argued, is that the layer is reached only through its committed surface and is handed
only a query string and RetrievedChunk values. A spy over the call proves it.

REPRODUCIBILITY IS ASSERTED AS A PROPERTY OF THE READS, not as a claim in prose. Building the
artifact is shown to open no embedding array, no query-embedding array and nothing under vendor/,
so the level-1 claim rests on which files the code touches rather than on which packages happen to
be absent from the machine running the suite.
"""

from __future__ import annotations

import builtins
import hashlib
import json

import pytest

from src.complete.absence import RetrievedChunk
from src.complete.augment import FetchStore
from src.ingest.corpus_integrity import REPO_ROOT
from src.score import run_layer_eval
from tests.test_augmentation import EXPECTED_RECOVERY, EXPECTED_SIZE

EVAL_DIR = REPO_ROOT / "eval"
LAYER_RESULTS = EVAL_DIR / "test_layer_results.json"
FIRST_PASS_RESULTS = EVAL_DIR / "test_retrieval_results.json"

# Files the layer measurement must never need. The first three are the retrieval arm's inputs and
# the fourth is the vendored model tree; touching any of them would put the layer condition above
# reproducibility level 1.
MODEL_PATH_MARKERS = (
    "data/retrieval/embeddings.npy",
    "eval/test_query_embeddings.npy",
    "eval/dev_query_embeddings.npy",
    "/vendor/",
)


@pytest.fixture(scope="module")
def committed():
    return json.loads(LAYER_RESULTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rebuilt():
    return run_layer_eval.build()


def test_the_layer_artifact_exists_and_ships():
    assert LAYER_RESULTS.exists(), (
        "eval/test_layer_results.json is the layer condition's results artifact and is missing"
    )


def test_rebuilding_reproduces_the_committed_artifact_byte_for_byte(committed, rebuilt):
    """The strongest form of the level-1 claim: the generator re-run over committed inputs
    reproduces the committed bytes, not merely the committed numbers."""
    payload = json.dumps(rebuilt, indent=1, ensure_ascii=False) + "\n"
    assert payload == LAYER_RESULTS.read_text(encoding="utf-8")
    assert rebuilt == committed


def test_building_the_artifact_opens_no_embedding_array_and_no_model(monkeypatch):
    """The corrective pass is resolution and fetch. It re-embeds nothing and re-ranks nothing, so
    it reads no embedding array and nothing from the vendored model tree. Asserted over the reads
    rather than over which packages the machine happens to lack."""
    real_open = builtins.open
    touched = []

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for marker in MODEL_PATH_MARKERS:
            if marker in text:
                touched.append(text)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guard)
    run_layer_eval.build()
    assert touched == []


def test_the_model_path_guard_can_fail(monkeypatch):
    """V20 companion. A guard that matches nothing would pass the test above on any code at all."""
    real_open = builtins.open
    touched = []

    def guard(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        for marker in MODEL_PATH_MARKERS:
            if marker in text:
                touched.append(text)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guard)
    with open(REPO_ROOT / "eval" / "test_query_embeddings.npy", "rb"):
        pass
    assert len(touched) == 1


def test_the_layer_is_called_only_with_a_query_string_and_retrieved_context(monkeypatch):
    """The spy that proves the call surface. If a gold slot, a stratum label or a row id were ever
    passed into the layer, it would have to arrive as one of these arguments."""
    calls = []
    real_augment = run_layer_eval.augment

    def spy(query_text, first_pass, store):
        calls.append((query_text, first_pass, store))
        return real_augment(query_text, first_pass, store)

    monkeypatch.setattr(run_layer_eval, "augment", spy)
    store = run_layer_eval.load_fetch_store()
    source = json.loads(FIRST_PASS_RESULTS.read_text(encoding="utf-8"))
    run_layer_eval.score_row(source["retrieval"][0], store)

    assert len(calls) == 1
    query_text, first_pass, passed_store = calls[0]
    assert isinstance(query_text, str)
    assert query_text == source["retrieval"][0]["query"]
    assert isinstance(first_pass, list) and len(first_pass) == 10
    assert all(isinstance(chunk, RetrievedChunk) for chunk in first_pass)
    assert isinstance(passed_store, FetchStore)


def test_the_artifact_carries_fifty_rows_and_the_forty_two_denominator(committed):
    assert len(committed["layer"]) == 50
    assert committed["aggregates"]["overall"]["n_queries"] == 42
    assert committed["aggregates"]["overall"]["n_rows_including_gold_empty"] == 50
    gold_empty = [row for row in committed["layer"] if row["recovered_passage_recall"] is None]
    assert len(gold_empty) == 8
    assert all(row["metrics_note"] for row in gold_empty)


def test_no_rank_metric_appears_anywhere_in_the_layer_condition(committed):
    """The round-five convention. The layer condition reports recovered-passage recall and the
    context set size, and never a figure at a fixed k."""
    blob = json.dumps({
        "aggregates": committed["aggregates"],
        "rows": [
            {k: v for k, v in row.items() if k != "first_pass_slot_satisfaction"}
            for row in committed["layer"]
        ],
    })
    for banned in ("precision_at_10", "ndcg_at_10", "\"mrr\""):
        assert banned not in blob, banned
    assert "recovered_passage_recall" in blob


def test_the_two_conditions_never_share_a_metric_label(committed):
    """First pass and layer carry different keys everywhere they appear together."""
    for row in committed["layer"]:
        assert "first_pass_recall_at_10" in row
        assert "recovered_passage_recall" in row
        assert "recall_at_10" not in row
    for agg in [committed["aggregates"]["overall"], *committed["aggregates"]["by_stratum"].values()]:
        assert "recall_at_10" not in agg
        if agg["n_queries"]:
            assert "recall_at_10_first_pass" in agg
            assert "recovered_passage_recall_layer" in agg


def test_the_first_pass_is_quoted_unchanged_and_never_recomputed(committed):
    source = {row["id"]: row for row in
              json.loads(FIRST_PASS_RESULTS.read_text(encoding="utf-8"))["retrieval"]}
    for row in committed["layer"]:
        original = source[row["id"]]
        assert row["first_pass_slot_satisfaction"] == original["slot_satisfaction"]
        expected = None if original["metrics"] is None else original["metrics"]["recall_at_10"]
        assert row["first_pass_recall_at_10"] == expected


def test_the_artifact_binds_the_first_pass_source_by_digest(committed):
    """So a reader can tell which first pass these layer figures were computed against."""
    recorded = committed["first_pass_source"]["sha256"]
    assert recorded == hashlib.sha256(FIRST_PASS_RESULTS.read_bytes()).hexdigest()
    assert committed["first_pass_source"]["path"] == "eval/test_retrieval_results.json"


def test_the_context_set_size_is_reported_per_row_and_matches_the_component_tests(committed):
    assert {row["id"]: row["context_set_size"] for row in committed["layer"]} == EXPECTED_SIZE


def test_the_recovery_set_matches_the_component_tests(committed):
    observed = {row["id"]: row["recovered_units"] for row in committed["layer"]
                if row["recovered_units"]}
    assert observed == {k: sorted(v) for k, v in EXPECTED_RECOVERY.items()}


def test_every_prediction_is_scored_and_only_section_six_three_is_contradicted(committed):
    scored = {entry["section"]: entry["verdict"] for entry in committed["predictions_scored"]}
    assert scored == {
        "6.1": "held", "6.2": "held", "6.3": "contradicted",
        "6.4": "held", "6.5": "held", "6.6": "held",
    }


def test_the_contradicted_prediction_carries_its_contradiction_and_reporting_form(committed):
    """A verdict of contradicted with no statement of what was contradicted would be a bare label."""
    entry = next(e for e in committed["predictions_scored"] if e["section"] == "6.3")
    assert entry["verdict"] == "contradicted"
    assert "contradiction" in entry
    assert "all eight" in entry["contradiction"]
    assert "left" in entry["contradiction"] and "uncorrected" in entry["contradiction"]
    assert entry["observed"]["flag_fired_on"] == [
        "test_43", "test_44", "test_45", "test_46", "test_47", "test_48", "test_49", "test_50"
    ]
    assert entry["observed"]["recovered_on"] == [
        "test_43", "test_44", "test_46", "test_47", "test_48", "test_49", "test_50"
    ]
    assert "crowding" in entry["required_reporting_form"]


def test_the_action_stratum_carries_the_split_reporting_form(committed):
    entry = next(e for e in committed["predictions_scored"] if e["section"] == "6.2")
    form = entry["required_reporting_form"]
    assert "Zero of four by any parent-derivation route" in form
    assert "sibling-label resolution" in form
    assert "No action identifier is read and no legend is applied" in form


def test_the_artifact_records_the_augmentation_policy_and_the_no_bound_condition(committed):
    policy = committed["augmentation_policy"]
    assert "augmentation only" in policy["policy"]
    assert "never removed" in policy["policy"]
    assert "No bound" in policy["no_bound"]
    assert "Applied identically to all fifty rows" in policy["uniform"]
    assert policy["trigger"].startswith("predicate a")


def test_the_artifact_records_the_adversarial_augmentation_volumes(committed):
    """Two quantities under two names. The absent-unit mean is what the predictions file
    tabulates; the fetched-chunk mean is what reaches the model and is larger wherever a fetched
    unit is split. An earlier draft reported the chunk figure under a units name, which is the
    one-field-one-quantity defect this assertion exists to prevent recurring."""
    adversarial = committed["adversarial_augmentation"]
    assert adversarial["n_rows"] == 8
    assert adversarial["absent_units_mean"] == pytest.approx(15.375)
    assert adversarial["fetched_chunks_mean"] == pytest.approx(21.625)
    assert adversarial["absent_units_mean"] < adversarial["fetched_chunks_mean"]
    assert "harder direction" in adversarial["consequence"]


def test_the_drops_funnel_is_key_free_and_states_the_keys_for_deduplicated_figures(committed):
    funnel = committed["external_filter_funnel"]
    assert funnel["drop_events"] == 44
    assert funnel["rows_with_at_least_one_drop"] == 13
    assert "36" in funnel["key_note"] and "42" in funnel["key_note"]
    assert "xrefs" in funnel["source_note"]


def test_the_reproducibility_claim_is_recorded_in_the_artifact(committed):
    assert committed["reproducibility_level"] == 1
    claim = committed["reproducibility_claim"]
    assert "no model" in claim and "no key" in claim
    assert "embed group absent" in claim
    assert committed["produced_by"] == "python -m src.score.run_layer_eval"
    assert committed["layer_components"] == [
        "src/complete/references.py",
        "src/complete/absence.py",
        "src/complete/augment.py",
    ]


def test_the_runner_refuses_to_overwrite_a_committed_result(capsys):
    """A committed result is not silently replaced; re-running over one is a Rule 4 correction."""
    assert run_layer_eval.main([]) == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert "--overwrite" in captured.err


def test_the_aggregate_delta_is_the_difference_of_the_two_conditions(committed):
    for agg in [committed["aggregates"]["overall"], *committed["aggregates"]["by_stratum"].values()]:
        if agg["n_queries"]:
            assert agg["delta"] == pytest.approx(
                agg["recovered_passage_recall_layer"] - agg["recall_at_10_first_pass"]
            )


def test_the_headline_pair(committed):
    overall = committed["aggregates"]["overall"]
    assert overall["recall_at_10_first_pass"] == pytest.approx(0.6785714285714286)
    assert overall["recovered_passage_recall_layer"] == pytest.approx(0.8928571428571429)
    assert overall["context_set_size_min"] == 10
    assert overall["context_set_size_max"] == 57
    assert overall["context_set_size_mean"] == pytest.approx(28.6)
