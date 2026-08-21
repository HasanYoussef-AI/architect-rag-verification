"""Request assembly, component H1 part one.

A PURE FUNCTION FROM COMMITTED FILES TO REQUEST BODIES. No network, no key, no clock, no
randomness, no environment read. Every input is a committed artifact and the output is
determined by them, which is what makes the byte-reproducibility check meaningful rather
than decorative.

THE THREE CONDITIONS, AND WHAT EACH BODY CARRIES.

  raw, and the layer's first pass, which are the same request. The query and the fused
  top 10 read from the committed retrieval results. PREREGISTRATION.md gives one first
  pass per tier serving both raw and layer, so this assembler emits one body per row per
  tier and the layer condition reuses it rather than issuing its own.

  layer second call. The query, the layer's final context set, the first answer verbatim,
  and the claim units the grounding check flagged. The context set is the committed
  corrective pass's output, the first-pass ten unchanged followed by the fetched chunks,
  built by calling src/complete/augment.py rather than reassembled here, so there is one
  implementation of the augmentation order.

  no-context. The query and no chunk.

THE FIREWALL IS HELD BY TYPE. Retrieved context enters as `RetrievedChunk`, the same type
src/complete/ uses, carrying `chunk_id`, `text` and `unit_label` and no other attribute.
The remaining fourteen `Chunk` fields are unreachable rather than declined. Loading is the
only place a full committed record is seen, and it selects the three admitted values.

TWO DIGESTS, AND THEY ARE DIFFERENT CLAIMS.

  The content digest covers the rendered system and user text for every row and condition.
  It is a function of the corpus, the committed retrieval and the prompt literals, and it
  does not vary by tier, because the assembled text does not depend on the model. It is
  computable now and is pinned now.

  The body digest covers the full request bodies including the per-tier parameters. Those
  parameters are not known until the gate 1a probes measure which tiers accept temperature
  and until count_tokens sets max_tokens, so a body digest computed before then would pin
  placeholder values. `build_body` raises on an unresolved parameter rather than emitting
  one, so no request can be built ahead of the gate that fixes it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.complete.absence import RetrievedChunk
from src.complete.augment import FetchStore, augment, load_fetch_store
from src.generate.manifest import MAX_TOKENS, PENDING, TierConfig
from src.generate.prompts import (
    NO_CONTEXT_SYSTEM,
    RAW_SYSTEM,
    SECOND_CALL_SYSTEM,
    render_no_context_user,
    render_raw_user,
    render_second_call_user,
)
from src.ingest.corpus_integrity import REPO_ROOT

CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
CANONICAL_DOC_ORDER = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1", "nist_playbook")

TEST_RETRIEVAL_PATH = REPO_ROOT / "eval" / "test_retrieval_results.json"
DEV_RETRIEVAL_PATH = REPO_ROOT / "eval" / "dev_retrieval_results.json"

CONDITIONS = ("raw", "second_call", "no_context")
QUERY_SETS = ("test", "dev")


@dataclass(frozen=True)
class AssembledRequest:
    """One request, before per-tier parameters are attached.

    `system` and `user` are the full rendered text. `custom_id` is the Batch API key and
    is the only way a result is matched back to its row, because batch results arrive in
    any order and matching by position would be wrong.
    """

    custom_id: str
    query_set: str
    condition: str
    query_id: str
    system: str
    user: str

    @property
    def content_sha256(self) -> str:
        payload = json.dumps(
            {"custom_id": self.custom_id, "system": self.system, "user": self.user},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def custom_id(query_set: str, condition: str, query_id: str, tier: str | None = None) -> str:
    """The Batch API key. Deterministic, unique, and readable in a result file.

    The tier is optional because the rendered content does not vary by tier; a body
    carries the tier, a content record does not.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    if query_set not in QUERY_SETS:
        raise ValueError(f"unknown query set: {query_set}")
    parts = [query_set, condition, query_id]
    if tier is not None:
        parts.insert(2, tier)
    return "__".join(parts)


def load_chunk_store(chunks_dir: Path | None = None) -> dict[str, RetrievedChunk]:
    """chunk_id to the three admitted values, read in the canonical corpus order."""
    directory = CHUNKS_DIR if chunks_dir is None else chunks_dir
    out: dict[str, RetrievedChunk] = {}
    for doc in CANONICAL_DOC_ORDER:
        with open(directory / f"{doc}.chunks.jsonl", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                out[record["chunk_id"]] = RetrievedChunk(
                    chunk_id=record["chunk_id"],
                    text=record["text"],
                    unit_label=record["unit_label"],
                )
    return out


def load_rows(query_set: str, path: Path | None = None) -> list[dict]:
    """The committed first-pass rows for a query set: id, query and fused top 10.

    Only those three values are taken. The sealed rows also carry `gold_slots`,
    `slot_satisfaction`, `carrier_count`, `metrics`, `type` and `subtype`, and none of
    them reaches an assembled request.
    """
    if path is None:
        path = TEST_RETRIEVAL_PATH if query_set == "test" else DEV_RETRIEVAL_PATH
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return [
        {"id": r["id"], "query": r["query"], "top10": list(r["top10"])}
        for r in payload["retrieval"]
    ]


def first_pass_chunks(row: dict, store: dict[str, RetrievedChunk]) -> list[RetrievedChunk]:
    return [store[chunk_id] for chunk_id in row["top10"]]


def build_raw(query_set: str, row: dict, store: dict[str, RetrievedChunk]) -> AssembledRequest:
    chunks = first_pass_chunks(row, store)
    return AssembledRequest(
        custom_id=custom_id(query_set, "raw", row["id"]),
        query_set=query_set,
        condition="raw",
        query_id=row["id"],
        system=RAW_SYSTEM,
        user=render_raw_user(row["query"], chunks),
    )


def build_no_context(query_set: str, row: dict) -> AssembledRequest:
    return AssembledRequest(
        custom_id=custom_id(query_set, "no_context", row["id"]),
        query_set=query_set,
        condition="no_context",
        query_id=row["id"],
        system=NO_CONTEXT_SYSTEM,
        user=render_no_context_user(row["query"]),
    )


def build_second_call(
    query_set: str,
    row: dict,
    store: dict[str, RetrievedChunk],
    fetch_store: FetchStore,
    first_answer: str,
    flagged_claims: Sequence[str],
) -> AssembledRequest:
    """The layer's second call, over the committed corrective pass's context set.

    `first_answer` and `flagged_claims` do not exist until the first pass runs and the
    grounding check is frozen, so before then this is exercised against a fixture answer
    and fixture flagged units. The context half is fully determined by committed files
    now, which is why it is the half the content digest covers for this condition.
    """
    result = augment(row["query"], first_pass_chunks(row, store), fetch_store)
    return AssembledRequest(
        custom_id=custom_id(query_set, "second_call", row["id"]),
        query_set=query_set,
        condition="second_call",
        query_id=row["id"],
        system=SECOND_CALL_SYSTEM,
        user=render_second_call_user(
            row["query"], result.context, first_answer, flagged_claims
        ),
    )


def layer_context(
    row: dict, store: dict[str, RetrievedChunk], fetch_store: FetchStore
) -> tuple[RetrievedChunk, ...]:
    """The layer's final context set for a row, from the committed corrective pass."""
    return augment(row["query"], first_pass_chunks(row, store), fetch_store).context


def build_body(
    request: AssembledRequest, tier: TierConfig, max_tokens: int = MAX_TOKENS
) -> dict:
    """The full Batch API request for one row on one tier.

    Raises on a per-tier parameter still pending, so a body cannot be built before gate 1a
    fixes it. That is the gate expressed as a type error rather than as a note in a
    document.

    `max_tokens` is a single constant across all three tiers and is a parameter here only
    so a test can vary it. It is deliberately not a `TierConfig` field: a per-tier value
    would make it a fourth cross-tier difference to disclose, and no measurement at gate 1a
    could set it anyway, since count_tokens counts input tokens.
    """
    tier.assert_resolved()
    params: dict = {
        "model": tier.model,
        "max_tokens": max_tokens,
        "system": request.system,
        "messages": [{"role": "user", "content": request.user}],
    }
    if tier.temperature is not None:
        params["temperature"] = tier.temperature
    if tier.thinking is not None:
        params["thinking"] = tier.thinking
    if tier.effort is not None:
        params["output_config"] = {"effort": tier.effort}
    return {
        "custom_id": custom_id(request.query_set, request.condition, request.query_id, tier.key),
        "params": params,
    }


def assemble_all(
    query_set: str,
    *,
    fixture_answer: str = "",
    fixture_flagged: Sequence[str] = (),
    store: dict[str, RetrievedChunk] | None = None,
    fetch_store: FetchStore | None = None,
) -> dict[str, list[AssembledRequest]]:
    """Every request for one query set, by condition, in committed row order.

    The second-call requests use the fixture answer and fixture flagged units, because the
    real ones do not exist yet. The context half of each is real.
    """
    store = load_chunk_store() if store is None else store
    fetch_store = load_fetch_store() if fetch_store is None else fetch_store
    rows = load_rows(query_set)
    return {
        "raw": [build_raw(query_set, r, store) for r in rows],
        "no_context": [build_no_context(query_set, r) for r in rows],
        "second_call": [
            build_second_call(
                query_set, r, store, fetch_store, fixture_answer, fixture_flagged
            )
            for r in rows
        ],
    }


def content_digest(requests: Sequence[AssembledRequest]) -> str:
    """sha256 over the rendered content of a request sequence, in custom_id order.

    Sorted by custom_id rather than left in row order, so the digest is a property of the
    set and not of the order a caller happened to build it in.
    """
    payload = json.dumps(
        [
            {"custom_id": r.custom_id, "system": r.system, "user": r.user}
            for r in sorted(requests, key=lambda r: r.custom_id)
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def body_digest(bodies: Sequence[dict]) -> str:
    """sha256 over full request bodies, in custom_id order."""
    payload = json.dumps(
        sorted(bodies, key=lambda b: b["custom_id"]),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "PENDING",
    "AssembledRequest",
    "assemble_all",
    "body_digest",
    "build_body",
    "build_no_context",
    "build_raw",
    "build_second_call",
    "content_digest",
    "custom_id",
    "layer_context",
    "load_chunk_store",
    "load_rows",
]
