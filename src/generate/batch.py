"""Batch submission and collection, component H1 part four.

TWO SEPARATE INVOCATIONS, AND THE SEPARATION IS THE POINT. Submission writes a batch id and
stops. Collection reads a batch id and writes results. A collection can therefore be re-run
against a batch the API already holds without re-submitting and without spending again, which
is what makes a failed write or an interrupted download recoverable rather than expensive.

THE KEY IS NEVER READ HERE. Neither function constructs a client. The caller passes one in, and
the caller is what runs inside the Rule 8 subshell,

    (set -a; source .env; set +a; <the caller>)

so the key exists only inside that subshell, is never exported into the session, and is never
committed. Tests pass a fake client and run with no network.

THIS MODULE HAS NO COMMAND-LINE ENTRY POINT, AND IT IS CALLED AS A LIBRARY. The three committed
development first passes, at f027fe3, 08bb610 and 92a4294, each ran the same four steps from a
caller inside that subshell: build the bodies with src/generate/assemble.py, pass
`client.messages.batches` and those bodies to `submit` and keep the batch id it returns, poll
`retrieve` on the same client until the batch ends, then pass the id to `collect` and its records
to `write_records`. Nothing else in this module was called and no command was run.

CORRECTED, AND THE CORRECTION IS THE POINT OF THIS PARAGRAPH. This docstring previously gave the
subshell line as

    (set -a; source .env; set +a; python -m src.generate.batch submit ...)

which named a command that does not exist: this module has no `__main__` block, so that invocation
imports the module, does nothing, and exits 0. A reader could not tell that from reading it and
could not tell it from running it either. It is the same defect class fixed forward at 50bd34a,
where src/generate/manifest.py recorded a producer command it did not implement.
tests/test_module_entry_points.py now asserts mechanically that every `python -m` invocation named
anywhere under src/ resolves to a module that carries an entry point, so the defect cannot return
here or appear anywhere else silently.

RESULTS ARE KEYED BY custom_id AND NEVER BY POSITION. Anthropic's Message Batches
documentation states that results arrive in any order. Writing them in arrival order would
produce a file whose bytes depend on the order the API happened to return, which would break
the level-1 reproducibility claim every downstream number rests on. Collection sorts by
custom_id before writing and a test asserts that a shuffled arrival order produces identical
bytes.

THE RESPONSE IS STORED VERBATIM. CLAUDE.md Rule 6 requires the paid step to run once and its
outputs to be committed, so every downstream number reproduces with no key. A record that
stored only the answer text would lose stop_reason, usage and the model string, and
stop_reason is what the max_tokens check reads.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Protocol

from src.ingest.corpus_integrity import REPO_ROOT

RUNS_DIR = REPO_ROOT / "data" / "runs"


class BatchClient(Protocol):
    """The surface this module uses. The real Anthropic SDK client satisfies it."""

    def create(self, requests: Sequence[dict]) -> Any: ...

    def retrieve(self, batch_id: str) -> Any: ...

    def results(self, batch_id: str) -> Iterable[Any]: ...


def submit(client: BatchClient, bodies: Sequence[dict]) -> str:
    """Submit one batch and return its id. Spends money. Never called from a test."""
    if not bodies:
        raise ValueError("refusing to submit an empty batch")
    seen = [b["custom_id"] for b in bodies]
    if len(set(seen)) != len(seen):
        duplicates = sorted({c for c in seen if seen.count(c) > 1})
        raise ValueError(f"duplicate custom_id in batch: {duplicates}")
    batch = client.create(requests=list(bodies))
    return batch.id


def collect(client: BatchClient, batch_id: str) -> list[dict]:
    """Read one batch's results into records, sorted by custom_id.

    Sorting happens here rather than at write time so that the sort is a property of the
    collection rather than of whoever writes the file next.
    """
    records: list[dict] = []
    for item in client.results(batch_id):
        records.append(
            {
                "custom_id": item.custom_id,
                "result_type": item.result.type,
                "response": _to_plain(item.result),
            }
        )
    ids = [r["custom_id"] for r in records]
    if len(set(ids)) != len(ids):
        duplicates = sorted({c for c in ids if ids.count(c) > 1})
        raise ValueError(f"duplicate custom_id in batch results: {duplicates}")
    return sorted(records, key=lambda r: r["custom_id"])


def _to_plain(obj: Any) -> Any:
    """Convert an SDK object to plain JSON-serialisable data, verbatim.

    Nothing is selected out and nothing is renamed, so a field this repository does not
    read today is still on record for a reviewer who wants it.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def write_records(
    records: Sequence[dict],
    query_set: str,
    condition: str,
    tier: str,
    runs_dir: Path | None = None,
) -> Path:
    """Write collected records as deterministic JSONL and return the path.

    Fixed key order, no timestamp, LF line endings, UTF-8 without escaping, trailing
    newline, sorted by custom_id. The same conventions src/ingest/chunk_schema.py uses, for
    the same reason: two collections of one batch must produce identical bytes.
    """
    directory = RUNS_DIR if runs_dir is None else runs_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{query_set}.{condition}.{tier}.jsonl"
    ordered = sorted(records, key=lambda r: r["custom_id"])
    lines = [
        json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for r in ordered
    ]
    path.write_bytes("".join(lines).encode("utf-8"))
    return path


def max_tokens_stops(records: Sequence[dict]) -> list[str]:
    """The custom_ids whose response stopped on max_tokens.

    This must be empty. A non-empty list is a defect in the max_tokens parameter, not a
    finding about the model, and it invalidates the claim units of every listed row because
    a truncated answer ends mid-sentence.
    """
    out = []
    for r in records:
        message = (r.get("response") or {}).get("message") or {}
        if message.get("stop_reason") == "max_tokens":
            out.append(r["custom_id"])
    return sorted(out)
