"""The offline reproducibility set opens no network connection.

WHAT THIS PINS. `docs/REPRODUCE.md` opens by saying "Nothing here needs an API key, a network
connection, or money." That has to be true by mechanism and not because an attempt fails, so the
dense arm's model lookup must decide absence from the local cache without opening a socket.

WHY THIS RUNS IN A SUBPROCESS, WHICH IS THE PART WORTH READING. The first version of this check ran
in-process and its zero was not a measurement. `huggingface_hub` caches its agent registry after the
first load, so any earlier test in the same process that touched the library left the registry
loaded and this check then saw no fetch and reported clean. Run on its own it failed, and run after
`tests/test_attributability.py` it passed, on the same code and the same machine.

That made the guard pass precisely when a network was available to populate the cache early, which
is the opposite of what it exists to detect. It is why continuous integration stayed green while an
outside reviewer running the documented path on Linux hit the failure.

A fresh interpreter has no such state, so the property is asked of a fresh interpreter. It also
costs nothing in accuracy: the question a reviewer asks is what a clean run does, and this is that
question.

AND A FRESH INTERPRETER WAS STILL NOT ENOUGH, which is the second thing worth reading. The first
subprocess version moved only `HF_HUB_CACHE` and passed against the very code it was written to
catch, because the agent registry caches on disk under `HF_HOME`, which it had left alone. Both are
redirected now, and set in the environment before the interpreter starts rather than patched after
import. That was found by running the corrected guard against the old mechanism and getting a green
it had no right to.

THE CONTROL IS NOT OPTIONAL. A harness that counts connection attempts and reports zero has two
explanations and only one is good news. The second check drives a real connection attempt through
the same harness in the same kind of subprocess and requires the count to move.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from src.ingest.corpus_integrity import REPO_ROOT

# Runs in a fresh interpreter. Stubs the socket layer, counts every attempt, and points the model
# cache at an empty directory so absence is the condition under test. Prints one line the parent
# parses; anything unparseable is a failure rather than a default, for the reason the docstring of
# .github/assert_documented_result.py gives.
_PROBE = r"""
import socket, sys

attempts = []

class _Blocked(socket.socket):
    def __init__(self, *args, **kwargs):
        attempts.append("socket()")
        raise OSError("the offline reproducibility set must not open a connection")

def _block(*args, **kwargs):
    attempts.append(args[:1])
    raise OSError("the offline reproducibility set must not open a connection")

socket.socket = _Blocked
socket.create_connection = _block
socket.getaddrinfo = _block

mode = sys.argv[1]
outcome = ""
if mode == "offline":
    from src.goldset.attributability import onnx_session
    outcome = repr(onnx_session())
elif mode == "control":
    try:
        socket.create_connection(("127.0.0.1", 9))
    except OSError:
        pass
    outcome = "control"

print(f"ATTEMPTS={len(attempts)} OUTCOME={outcome} DETAIL={attempts}")
"""


def _run(mode: str) -> tuple[int, str]:
    """Run the probe in a fresh interpreter and return (attempt count, its whole output)."""
    # HF_HOME as well as HF_HUB_CACHE, and set in the environment before the interpreter starts
    # rather than patched after import. Redirecting the model cache alone is not enough: the agent
    # registry that turned out to be doing the fetching caches on disk under HF_HOME, so a probe
    # that moved only HF_HUB_CACHE read that registry, never fetched, and reported a clean zero
    # against the very code it was supposed to catch. Measured, not reasoned: it did exactly that.
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ)
        env["HF_HOME"] = str(Path(home) / "hf")
        env["HF_HUB_CACHE"] = str(Path(home) / "hf" / "hub")
        done = subprocess.run(
            [sys.executable, "-c", _PROBE, mode],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=300, env=env,
        )
        blob = done.stdout + done.stderr
        for line in done.stdout.splitlines():
            if line.startswith("ATTEMPTS="):
                return int(line.split("=", 1)[1].split()[0]), blob
    raise AssertionError(
        f"the probe printed no ATTEMPTS line, so nothing was measured. Output:\n{blob}"
    )


def test_the_offline_set_opens_no_connection_when_the_model_is_absent():
    """The claim in docs/REPRODUCE.md, asserted on the path that broke it, in a clean process.

    Returning None is not enough on its own: the code this replaced also returned None, after
    opening a socket and failing. The attempt count is what separates true in mechanism from true
    in outcome.
    """
    attempts, output = _run("offline")

    assert "OUTCOME=None" in output, (
        f"the model cache was pointed at an empty directory, so the session must be absent. "
        f"Output:\n{output}"
    )
    assert attempts == 0, (
        f"the offline path opened {attempts} connection(s) with the model absent. "
        "docs/REPRODUCE.md says a network connection is not needed, and that has to be true by "
        f"mechanism rather than because the attempt fails. Output:\n{output}"
    )


def test_the_session_guard_records_and_attributes_a_connection(monkeypatch):
    """The control for the session-wide guard in conftest.py, and it ships rather than being run once.

    That guard reports zero for the whole suite. A counter reporting zero has two explanations and
    only one is good news, so its recording code is exercised here on every run.

    It uses the same factory conftest.py installs, over a private sink of its own. That matters: a
    control that opened a connection into the session's sink would trip the very check it exists to
    verify, and the only way out of that would be an exemption for itself. There is no exemption
    list in this guard and this is how it stays that way.
    """
    from tests._netguard import install

    sink: list = []
    install(monkeypatch, sink)

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 9))

    assert sink == [("127.0.0.1", 9)], (
        f"the recording stubs did not capture the attempt they intercepted, so the session guard's "
        f"zero would prove nothing. Recorded: {sink!r}"
    )


def test_the_harness_counts_a_connection_that_is_actually_attempted():
    """V20. The zero above means nothing unless this counter is shown able to move.

    Nothing in the repository is exercised here on purpose. The subject is the instrument: if the
    stubs stopped intercepting, this fails and the check above becomes a detector reporting a pass
    because it can no longer see anything.
    """
    attempts, output = _run("control")

    assert attempts == 1, (
        f"the harness recorded {attempts} attempts for a connection it was asked to make, so a "
        f"zero elsewhere in this file would prove nothing. Output:\n{output}"
    )
