"""Tests for src/generate/, component H1 part five. No network, no key.

The digest checks follow the V20 shape rather than the naive one. A comparison that passes
when both sides are absent has produced a false green in this repository before, so each
side's shape is asserted before the two are compared, and the expected counts are derived
independently from the committed query files rather than read off the object under test.

Every emptiness or equality claim here has a companion showing the check capable of failing.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.complete.absence import RetrievedChunk
from src.complete.augment import augment, load_fetch_store
from src.generate.assemble import (
    AssembledRequest,
    assemble_all,
    body_digest,
    build_body,
    build_raw,
    content_digest,
    custom_id,
    first_pass_chunks,
    layer_context,
    load_chunk_store,
    load_rows,
)
from src.generate.batch import collect, max_tokens_stops, write_records
from src.generate.manifest import (
    MAX_TOKENS,
    PENDING,
    RUN_MANIFEST_PATH,
    RUN_MANIFEST_RELATIVE,
    TEMPERATURE_PROBES,
    TIERS,
    RunManifest,
    TierConfig,
    prompt_digest,
)
from src.generate.prompts import (
    ABSTAINED,
    ANSWERED,
    MARKER,
    MARKER_VARIANT,
    PROMPTS,
    classify_response,
    is_abstention,
    normalize_response,
    render_context,
)
from src.ingest.corpus_integrity import REPO_ROOT

FIXTURE_ANSWER = "FIXTURE ANSWER. This sentence stands in for a first-pass answer."
FIXTURE_FLAGGED = ("FIXTURE FLAGGED CLAIM ONE.", "FIXTURE FLAGGED CLAIM TWO.")

# Pinned prompt digests. A prompt edit after eval/generation_predictions.md commits is a
# failing test here rather than a silent drift between the file and the assembler.
PROMPT_DIGESTS = {
    "raw": "dcbafba1f627dca881b3f7d5ab35aefb259ad25eba11524cb0b4bf71cb46bb5f",
    "second_call": "e60ad2ae1fea8e2be4f99d17c2df0b0f79238b567372434f0216bd8de8c3c975",
    "no_context": "8b4e2a278c9219602018d09a073b20373791234de41e45730325e92e0f068777",
}

# Pinned content digests, per query set and condition, over the rendered system and user
# text. Tier independent by construction: the assembled text is a function of the corpus,
# the committed retrieval and the prompt literals, and not of the model.
CONTENT_DIGESTS = {
    ("test", "raw"): "3215884024ff1cb87ebe5af9e9da4b490876ffdb2103d9eaaf1b4a8f386b6587",
    ("test", "second_call"): "5ea4cf19883e5ae76e53015ad3ba3e794fe8452fb45f8beffe8e852fa77e617f",
    ("test", "no_context"): "bd3483e8f19109002f79b212838f30ddbb50a3e9ecde1a98f3b5fbb08c64d66a",
    ("dev", "raw"): "38912a19b232563ab1082460326a47474d3e12eb230b3ab8de021a3ca895aabd",
    ("dev", "second_call"): "a5c4b7951f54b790816f537379c63dec30f4d1cf13410441eff5624f94c082a2",
    ("dev", "no_context"): "3d3c82bec8201662d11a975e42eb6c9686fcf6dc6663f7f182e42957e915e513",
}

EXPECTED_ROWS = {"test": 50, "dev": 12}


def _derived_row_count(query_set: str) -> int:
    """Row count derived from the committed query file, not from the object under test.

    V20's second form: an equality that reads both sides from the same place proves
    nothing. This reads the count from a different file than the assembler reads.
    """
    name = "test_queries.jsonl" if query_set == "test" else "dev_queries.jsonl"
    path = REPO_ROOT / "eval" / name
    with open(path, encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


# --------------------------------------------------------------------------------------
# Prompts and the marker
# --------------------------------------------------------------------------------------


def test_prompt_literals_match_their_pinned_digests():
    for name, expected in PROMPT_DIGESTS.items():
        text = PROMPTS[name]
        assert isinstance(text, str) and text, f"{name} prompt is empty"
        actual = prompt_digest(text)
        assert len(actual) == 64, "digest is not a sha256 hex string"
        assert actual == expected, f"{name} prompt changed; update the predictions file too"


def test_prompt_digest_companion_is_capable_of_failing():
    """The pin above is trusted only once the same check is shown red."""
    mutated = PROMPTS["raw"] + " "
    assert prompt_digest(mutated) != PROMPT_DIGESTS["raw"]


def test_one_marker_literal_appears_in_all_three_prompts():
    assert MARKER == "I do not have enough information to answer this question."
    for name, text in PROMPTS.items():
        assert MARKER in text, f"{name} prompt does not carry the marker"


def test_the_second_call_prompt_does_not_instruct_the_model_to_differ():
    """Removed deliberately. The flagged-statement rule already covers the case that
    matters, and on the unflagged majority an instruction to differ is variance the layer
    did not need."""
    assert "Do not copy the first answer" not in PROMPTS["second_call"]
    assert "Do not repeat one unchanged." in PROMPTS["second_call"]


def test_the_second_call_prompt_instructs_the_model_to_write_what_the_context_supports():
    """The positive instruction, pinned as its own bullet.

    The two sentences above and this one shared a bullet once. Dropping the first took the
    second with it, and with it the prompt's only instruction to produce the answer from the
    context: the survivors named the question without naming the context, or named the
    context while scoped to the flagged statements, or bounded the source without directing
    an answer. Pinned separately from the removal above so neither decision can be reversed
    by an edit that looks like the other one.
    """
    second_call = PROMPTS["second_call"]
    assert "- Write the answer the provided context supports.\n" in second_call, (
        "the positive instruction is not present as its own bullet"
    )
    lines = second_call.split("\n")
    assert lines.index("- Write the answer the provided context supports.") == 7, (
        "the bullet is not where the removed bullet stood"
    )


# --------------------------------------------------------------------------------------
# Abstention detection. The two defects the sealed pre-declaration's own sentence
# constructs are pinned here, so reversing either decision means deleting a failing test.
# --------------------------------------------------------------------------------------


def test_marker_alone_is_an_abstention():
    assert classify_response(MARKER) == ABSTAINED
    assert is_abstention(MARKER)


def test_marker_followed_by_substantive_content_is_answered_not_abstained():
    """Defect one from the pre-declaration: a marker-plus-parametric answer.

    Containment would score this a clean abstention on exactly the adversarial rows the
    study cares most about. Whole-response equality is what closes it.
    """
    response = (
        f"{MARKER} However, ISO/IEC 42001 requires an organization to document the scope "
        "of its AI management system."
    )
    assert classify_response(response) == ANSWERED
    assert not is_abstention(response)


def test_marker_less_existence_denial_is_answered_not_abstained():
    """Defect two: the sealed pre-declaration names this as not a failure, which is a
    separate question from whether it is an abstention. It is not one, and its content is
    graded."""
    response = "Article 999 does not appear in the EU AI Act."
    assert classify_response(response) == ANSWERED
    assert not is_abstention(response)


def test_whitespace_only_differences_still_abstain():
    assert classify_response(f"  {MARKER}  ") == ABSTAINED
    assert classify_response(MARKER.replace(" ", "  ")) == ABSTAINED
    assert classify_response(f"\n{MARKER}\n") == ABSTAINED


def test_case_and_trailing_period_differences_are_a_counted_variant_not_an_abstention():
    assert classify_response(MARKER.upper()) == MARKER_VARIANT
    assert classify_response(MARKER.rstrip(".")) == MARKER_VARIANT
    assert not is_abstention(MARKER.upper())
    assert not is_abstention(MARKER.rstrip("."))


def test_normalisation_does_exactly_two_things():
    assert normalize_response("  a   b \n c  ") == "a b c"
    assert normalize_response("A.") == "A."  # no case folding, no punctuation removal


def test_abstention_companion_is_capable_of_failing():
    """A classifier that returned ABSTAINED for everything would pass the marker test."""
    assert classify_response("") != ABSTAINED
    assert classify_response("The EU AI Act sets out obligations.") != ABSTAINED


def test_only_the_no_context_prompt_omits_the_closed_book_instruction():
    """The O2 ruling, asserted rather than described in a comment."""
    closed_book = "Do not use anything you know from training"
    assert closed_book in PROMPTS["raw"]
    assert closed_book in PROMPTS["second_call"]
    assert closed_book not in PROMPTS["no_context"]


# --------------------------------------------------------------------------------------
# The firewall, held by type
# --------------------------------------------------------------------------------------


def test_retrieved_chunk_carries_only_the_three_admitted_fields():
    store = load_chunk_store()
    chunk = next(iter(store.values()))
    assert set(chunk.__dataclass_fields__) == {"chunk_id", "text", "unit_label"}
    for barred in ("parent_id", "structural_path", "doc_id", "unit_type", "heading"):
        assert not hasattr(chunk, barred), f"{barred} reachable on a retrieved chunk"


def test_loaded_rows_carry_only_id_query_and_top10():
    for query_set in ("test", "dev"):
        for row in load_rows(query_set):
            assert set(row) == {"id", "query", "top10"}


def test_assembled_request_carries_no_barred_field():
    store = load_chunk_store()
    row = load_rows("test")[0]
    request = build_raw("test", row, store)
    assert set(request.__dataclass_fields__) == {
        "custom_id",
        "query_set",
        "condition",
        "query_id",
        "system",
        "user",
    }


# --------------------------------------------------------------------------------------
# Assembly, shape asserted before any comparison
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("query_set", ["test", "dev"])
def test_row_counts_are_derived_independently_and_agree(query_set):
    derived = _derived_row_count(query_set)
    assert derived == EXPECTED_ROWS[query_set], "committed query file changed"
    built = assemble_all(
        query_set, fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED
    )
    for condition in ("raw", "second_call", "no_context"):
        assert len(built[condition]) == derived


@pytest.mark.parametrize("query_set", ["test", "dev"])
def test_content_digests_match_their_pins(query_set):
    built = assemble_all(
        query_set, fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED
    )
    for condition, requests in built.items():
        assert requests, f"{query_set}/{condition} assembled nothing"
        actual = content_digest(requests)
        assert len(actual) == 64
        assert actual == CONTENT_DIGESTS[(query_set, condition)]


def test_digest_is_stable_across_two_in_process_builds_and_a_fresh_process():
    """The triple check. Two builds here, one in a subprocess, all against the pin."""
    first = content_digest(
        assemble_all("test", fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED)["raw"]
    )
    second = content_digest(
        assemble_all("test", fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED)["raw"]
    )
    script = (
        "import sys; sys.path.insert(0, '.');"
        "from src.generate.assemble import assemble_all, content_digest;"
        "print(content_digest(assemble_all('test')['raw']))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    third = completed.stdout.strip()
    for value in (first, second, third):
        assert len(value) == 64, f"not a sha256 hex string: {value!r}"
    assert first == second == third == CONTENT_DIGESTS[("test", "raw")]


def test_digest_companion_fires_on_a_mutated_chunk_text():
    """A digest check that cannot notice a changed chunk is not a check."""
    store = load_chunk_store()
    rows = load_rows("test")
    clean = content_digest([build_raw("test", r, store) for r in rows])
    assert clean == CONTENT_DIGESTS[("test", "raw")]

    target = rows[0]["top10"][0]
    original = store[target]
    store[target] = RetrievedChunk(
        chunk_id=original.chunk_id,
        text=original.text + " MUTATED",
        unit_label=original.unit_label,
    )
    mutated = content_digest([build_raw("test", r, store) for r in rows])
    assert mutated != clean


def test_custom_ids_are_unique_and_deterministic():
    for query_set in ("test", "dev"):
        built = assemble_all(
            query_set, fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED
        )
        ids = [r.custom_id for condition in built for r in built[condition]]
        assert len(ids) == len(set(ids)), "custom_id collision"
    assert custom_id("test", "raw", "test_01") == "test__raw__test_01"
    assert custom_id("test", "raw", "test_01", "opus48") == "test__raw__opus48__test_01"


def test_custom_id_rejects_an_unknown_condition_or_query_set():
    with pytest.raises(ValueError):
        custom_id("test", "not_a_condition", "test_01")
    with pytest.raises(ValueError):
        custom_id("not_a_set", "raw", "test_01")


def test_no_context_body_carries_the_query_and_no_chunk():
    built = assemble_all("test")
    store = load_chunk_store()
    any_chunk_id = next(iter(store))
    for request in built["no_context"]:
        assert request.user.startswith("Question: ")
        assert "Context:" not in request.user
        assert any_chunk_id not in request.user


def test_second_call_context_equals_the_committed_corrective_pass():
    """One implementation of the augmentation order, not two."""
    store = load_chunk_store()
    fetch_store = load_fetch_store()
    for row in load_rows("test"):
        expected = augment(row["query"], first_pass_chunks(row, store), fetch_store).context
        assert expected, "an empty context set would make the comparison vacuous"
        assert layer_context(row, store, fetch_store) == expected
        assert render_context(expected)


def test_second_call_renders_none_when_no_claim_was_flagged():
    built = assemble_all("test", fixture_answer=FIXTURE_ANSWER, fixture_flagged=())
    assert "the context did not support:\n(none)" in built["second_call"][0].user


# --------------------------------------------------------------------------------------
# The read guard
# --------------------------------------------------------------------------------------


ALLOWED_READ_SUFFIXES = (
    ".chunks.jsonl",
    "eval/corpus_unit_index.json",
    "eval/test_retrieval_results.json",
    "eval/dev_retrieval_results.json",
)


def _guarded_open(opened: list[str]):
    real_open = builtins.open

    def guarded(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    return guarded


def test_assembly_opens_only_allowlisted_paths(monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr(builtins, "open", _guarded_open(opened))
    assemble_all("test", fixture_answer=FIXTURE_ANSWER, fixture_flagged=FIXTURE_FLAGGED)
    monkeypatch.undo()

    assert opened, "the guard recorded nothing, so it proves nothing"
    for path in opened:
        assert any(path.endswith(s) or s in path for s in ALLOWED_READ_SUFFIXES), (
            f"assembly opened a path outside the allowlist: {path}"
        )
    barred = (
        "relations.jsonl",
        "xrefs.jsonl",
        "duplication_map.json",
        "verbatim_groups.json",
        "near_duplicate_exceptions.json",
        "test_query_verification.jsonl",
        "test_frame.json",
        "pass_one_designations.jsonl",
        "test_layer_results.json",
        "test_queries.jsonl",
        "dev_queries.jsonl",
    )
    for path in opened:
        for name in barred:
            assert name not in path, f"assembly opened a barred artifact: {path}"


def test_read_guard_companion_is_capable_of_firing(monkeypatch):
    """The guard is trusted only after it is shown catching a barred read."""
    opened: list[str] = []
    monkeypatch.setattr(builtins, "open", _guarded_open(opened))
    with open(REPO_ROOT / "data" / "chunks" / "nist_ai_600_1.relations.jsonl", encoding="utf-8"):
        pass
    monkeypatch.undo()
    assert any("relations.jsonl" in p for p in opened)
    caught = False
    for path in opened:
        if "relations.jsonl" in path:
            caught = True
    assert caught, "the guard failed to record a barred read"


# --------------------------------------------------------------------------------------
# Per-tier parameters and the gate
# --------------------------------------------------------------------------------------


def test_build_body_refuses_a_tier_with_unmeasured_parameters():
    """Stays. Its subject changed because every pre-registered tier is now measured.

    Before gate 1a this pointed at TIERS["opus48"], which carried the sentinel. It now
    constructs a pending tier explicitly, so the guard is still exercised on the shape a
    pending tier has rather than on whichever tier happens to be unmeasured.
    """
    store = load_chunk_store()
    request = build_raw("test", load_rows("test")[0], store)
    unmeasured = TierConfig(
        key="opus48", model="claude-opus-4-8", temperature=PENDING,
        thinking={"type": "adaptive"}, effort="low",
    )
    with pytest.raises(ValueError, match="gate 1a"):
        build_body(request, unmeasured)

    for _key, tier in TIERS.items():
        build_body(request, tier)  # every measured tier builds rather than raising


def test_build_body_emits_the_documented_parameter_shape():
    store = load_chunk_store()
    request = build_raw("test", load_rows("test")[0], store)

    rejects_temperature = TierConfig(
        key="opus48", model="claude-opus-4-8", temperature=None,
        thinking={"type": "adaptive"}, effort="low",
    )
    body = build_body(request, rejects_temperature)
    assert body["custom_id"] == "test__raw__opus48__test_01"
    assert "temperature" not in body["params"], "omitted where the tier rejects it"
    assert body["params"]["thinking"] == {"type": "adaptive"}
    assert body["params"]["output_config"] == {"effort": "low"}
    assert body["params"]["model"] == "claude-opus-4-8"
    assert body["params"]["max_tokens"] == MAX_TOKENS

    accepts_temperature = TierConfig(
        key="haiku45", model="claude-haiku-4-5-20251001", temperature=0,
    )
    body2 = build_body(request, accepts_temperature)
    assert body2["params"]["temperature"] == 0
    assert "thinking" not in body2["params"]
    assert "output_config" not in body2["params"]
    assert body2["params"]["max_tokens"] == MAX_TOKENS


def test_every_tier_carries_a_measured_setting_backed_by_its_probe_record():
    """Replaces the pending-state test, which gate 1a was designed to make fail.

    The predecessor asserted every tier carried the sentinel. Passing the gate is exactly
    what breaks that, so it is replaced rather than deleted: the property that matters after
    the gate is that no setting is asserted without the probe pair it rests on. A setting of
    0 must come from a 200 on the temperature request, a setting of None from a 400, and in
    both cases the control must be 200 or the pairing was never a measurement at all.
    """
    assert set(TIERS) == {"haiku45", "sonnet5", "opus48"}
    records = {r["probe"]: r for r in TEMPERATURE_PROBES["records"]}
    assert len(records) == 6, "two probe records per tier, one of them the control"

    for key, tier in TIERS.items():
        assert tier.temperature != PENDING, f"tier {key} still carries the gate sentinel"
        assert tier.temperature in (0, None), f"tier {key} has a setting the rule does not admit"
        assert tier.temperature_probe == f"{key}:temperature_0", (
            f"tier {key} does not name its own probe record"
        )

        probe = records[tier.temperature_probe]
        control = records[f"{key}:control_no_temperature"]
        assert probe["tier"] == key and probe["carries_temperature"] is True
        assert control["tier"] == key and control["carries_temperature"] is False
        assert control["http_status"] == 200, (
            f"tier {key}: the control did not return 200, so no 400 is attributable to the "
            "parameter and the setting is not a measurement"
        )
        expected_status = 200 if tier.temperature == 0 else 400
        assert probe["http_status"] == expected_status, (
            f"tier {key}: setting {tier.temperature!r} does not match probe outcome "
            f"{probe['http_status']}"
        )
        # The recorded body is the sent body, so the parameter's presence is checkable.
        sent = json.loads(probe["request_body_sent"])
        assert "temperature" in sent and sent["temperature"] == 0
        assert "temperature" not in json.loads(control["request_body_sent"])


def test_the_manifest_names_a_producer_that_exists_and_a_path_that_ships():
    """The 6.1 defect, pinned. produced_by named a command that did nothing.

    Asserting the string alone would pass on a module with no entry point, which is how the
    claim went untrue in the first place, so the artifact's existence and its agreement with
    a fresh render are asserted beside it.
    """
    payload = json.loads(RunManifest().to_json())
    assert payload["produced_by"] == "python -m src.generate.manifest"
    assert payload["written_to"] == RUN_MANIFEST_RELATIVE
    assert RUN_MANIFEST_PATH.exists(), "the manifest names a path that does not ship"
    assert RUN_MANIFEST_PATH.relative_to(REPO_ROOT).as_posix() == RUN_MANIFEST_RELATIVE


def test_committed_run_manifest_is_byte_identical_to_a_fresh_render():
    """Determinism asserted on shape first, then on equality.

    V20's first form: two absent sides compare equal. Both sides are asserted non-empty and
    well formed before they are compared, and the render is taken twice so a per-call
    nondeterminism cannot hide inside a single comparison.
    """
    committed = RUN_MANIFEST_PATH.read_text(encoding="utf-8")
    first = RunManifest().to_json()
    second = RunManifest().to_json()
    for side, name in ((committed, "committed"), (first, "render")):
        assert len(side) > 1000, f"{name} side is too small to be the manifest"
        assert json.loads(side)["produced_by"], f"{name} side is not the manifest"
    assert first == second, "two renders in one process disagree"
    assert committed == first, (
        "data/runs/run_manifest.json is stale; re-run python -m src.generate.manifest"
    )


def test_the_manifest_carries_every_probe_verbatim():
    payload = json.loads(RunManifest().to_json())
    probes = payload["temperature_probes"]
    assert probes["endpoint"] == "POST /v1/messages"
    assert probes["run_window"]["started_utc"] and probes["run_window"]["ended_utc"]
    assert len(probes["records"]) == 6
    for record in probes["records"]:
        assert record["request_body_sent"], "a probe record carries no request body"
        assert record["response_body"], "a probe record carries no response body"
        assert record["http_status"] in (200, 400)
        if record["http_status"] == 400:
            assert record["error_message"], "a 400 record carries no error message"
        else:
            assert record["error_message"] is None
    assert payload["probe_records"] == probes["records"]


def test_max_tokens_is_one_constant_and_is_not_a_per_tier_field():
    """A per-tier value would have made it a fourth cross-tier difference to disclose."""
    assert MAX_TOKENS == 16000
    for tier in TIERS.values():
        assert not hasattr(tier, "max_tokens"), (
            f"tier {tier.key} carries its own max_tokens, which reopens the asymmetry"
        )
    payload = json.loads(RunManifest().to_json())
    assert payload["max_tokens"]["value"] == MAX_TOKENS
    assert "one constant across all three tiers" in payload["max_tokens"]["scope"]
    for record in payload["tiers"].values():
        assert "max_tokens" not in record


def test_manifest_records_the_nine_run_accounting_and_both_asymmetries():
    payload = json.loads(RunManifest().to_json())
    assert payload["run_accounting"]["runs"] == 9
    assert payload["run_accounting"]["reported_conditions"] == 9
    assert payload["marker_phrase"] == MARKER
    assert set(payload["prompts"]) == {"raw", "second_call", "no_context"}
    for name, expected in PROMPT_DIGESTS.items():
        assert payload["prompts"][name]["sha256"] == expected
    assert "temperature" in payload["cross_tier_asymmetries"]
    assert "thinking" in payload["cross_tier_asymmetries"]
    rows = payload["cross_tier_asymmetries"]["thinking"]["table_rows_quoted"]
    assert "Extended only" in rows["claude-haiku-4-5"]
    assert "On" in rows["claude-sonnet-5"]
    assert "Off" in rows["claude-opus-4-8"]


def test_body_digest_orders_by_custom_id_not_by_arrival():
    tier = TierConfig(key="haiku45", model="m", temperature=0)
    store = load_chunk_store()
    rows = load_rows("dev")
    bodies = [build_body(build_raw("dev", r, store), tier) for r in rows]
    forward = body_digest(bodies)
    backward = body_digest(list(reversed(bodies)))
    assert len(forward) == 64
    assert forward == backward
    mutated = [dict(b) for b in bodies]
    mutated[0]["params"] = dict(mutated[0]["params"], max_tokens=99)
    assert body_digest(mutated) != forward


# --------------------------------------------------------------------------------------
# Batch collection
# --------------------------------------------------------------------------------------


class _FakeItem:
    def __init__(self, custom_id, stop_reason="end_turn"):
        self.custom_id = custom_id
        self.result = _Payload(stop_reason)


class _Payload:
    def __init__(self, stop_reason):
        self.type = "succeeded"
        self._stop_reason = stop_reason

    def to_dict(self):
        return {
            "type": "succeeded",
            "message": {
                "stop_reason": self._stop_reason,
                "content": [{"type": "text", "text": "x"}],
            },
        }


class _FakeClient:
    def __init__(self, items):
        self._items = items

    def create(self, requests):  # pragma: no cover, never called in a test
        raise AssertionError("a test must never submit a batch")

    def retrieve(self, batch_id):  # pragma: no cover
        raise AssertionError("not used")

    def results(self, batch_id):
        return list(self._items)


def test_collection_is_byte_identical_under_a_shuffled_arrival_order(tmp_path):
    ids = ["test__raw__haiku45__test_03", "test__raw__haiku45__test_01",
           "test__raw__haiku45__test_02"]
    forward = collect(_FakeClient([_FakeItem(i) for i in ids]), "batch_x")
    backward = collect(_FakeClient([_FakeItem(i) for i in reversed(ids)]), "batch_x")
    assert [r["custom_id"] for r in forward] == sorted(ids)
    assert forward == backward

    p1 = write_records(forward, "test", "raw", "haiku45", runs_dir=tmp_path / "a")
    p2 = write_records(backward, "test", "raw", "haiku45", runs_dir=tmp_path / "b")
    b1, b2 = p1.read_bytes(), p2.read_bytes()
    assert b1, "wrote nothing, so the comparison would pass on two absences"
    assert hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest()


def test_collection_companion_fires_when_a_record_differs(tmp_path):
    a = collect(_FakeClient([_FakeItem("x__1")]), "b")
    b = collect(_FakeClient([_FakeItem("x__1", stop_reason="max_tokens")]), "b")
    assert a != b


def test_duplicate_custom_id_in_results_raises():
    with pytest.raises(ValueError, match="duplicate custom_id"):
        collect(_FakeClient([_FakeItem("x__1"), _FakeItem("x__1")]), "b")


def test_max_tokens_stops_finds_a_truncated_response_and_is_empty_otherwise():
    clean = collect(_FakeClient([_FakeItem("a__1"), _FakeItem("a__2")]), "b")
    assert max_tokens_stops(clean) == []
    dirty = collect(
        _FakeClient([_FakeItem("a__1"), _FakeItem("a__2", stop_reason="max_tokens")]), "b"
    )
    assert max_tokens_stops(dirty) == ["a__2"]


def test_written_records_are_deterministic_jsonl(tmp_path):
    records = collect(_FakeClient([_FakeItem("a__2"), _FakeItem("a__1")]), "b")
    path = write_records(records, "dev", "raw", "haiku45", runs_dir=tmp_path)
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["custom_id"] == "a__1"
    assert json.loads(lines[1])["custom_id"] == "a__2"


def test_isolated_paths_exist(tmp_path: Path):
    """Guards the constants the runner writes through, so a rename fails loudly."""
    assert (REPO_ROOT / "data" / "runs").is_dir()
    assert (REPO_ROOT / "eval" / "test_retrieval_results.json").is_file()
    assert (REPO_ROOT / "eval" / "dev_retrieval_results.json").is_file()
    assert not (tmp_path / "nothing").exists()


def test_assembled_request_content_digest_is_per_request():
    store = load_chunk_store()
    rows = load_rows("dev")
    a = build_raw("dev", rows[0], store)
    b = build_raw("dev", rows[1], store)
    assert isinstance(a, AssembledRequest)
    assert len(a.content_sha256) == 64
    assert a.content_sha256 != b.content_sha256
