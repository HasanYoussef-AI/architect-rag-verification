"""The offline reproducibility set opens no network connection.

WHAT THIS PINS AND WHY IT IS A TEST RATHER THAN A NOTE. `docs/REPRODUCE.md` opens by saying
"Nothing here needs an API key, a network connection, or money." That was true in outcome and false
in mechanism: `onnx_session` resolved the pinned weight through `download_onnx`, which calls
`hf_hub_download` with no `local_files_only`, so a reader running offline got retry warnings and a
delay before the dense arm skipped. The arm skipped either way, which is why nothing failed and
nobody noticed.

The defect was found by putting a firing control beside a diagnostic, not by reading the code. It is
pinned here so that reversing it requires deleting a failing test.

THE COLD CACHE IS THE WHOLE POINT. On a machine that has already fetched the weight,
`hf_hub_download` returns from disk and opens nothing, so this check passes on a warm cache whether
the code is right or wrong. That warm cache is exactly what hid the defect during the first
measurement. Each check below moves `HF_HUB_CACHE` to an empty directory first, so the question
asked is the one a fresh clone asks.

THE CONTROL IS NOT OPTIONAL. A guard that counts connection attempts and reports zero has two
explanations, and only one of them is good news. The second check makes a real connection attempt
under the same guard and requires the counter to move, so a zero above is a measurement rather than
a detector that stopped working.
"""

from __future__ import annotations

import socket

import pytest

from src.goldset.attributability import onnx_session


def _guard(monkeypatch) -> list:
    """Replace the socket layer with stubs that count every attempt and refuse it.

    Returns the list attempts are recorded in. Three entry points are covered because a caller can
    reach the network through any of them: the socket constructor, the connection helper, and name
    resolution, which is where a request usually starts.
    """
    attempts: list = []

    class _Blocked(socket.socket):
        def __init__(self, *args, **kwargs):
            attempts.append("socket()")
            raise OSError("the offline reproducibility set must not open a connection")

    def _block(*args, **kwargs):
        attempts.append(args[:1])
        raise OSError("the offline reproducibility set must not open a connection")

    monkeypatch.setattr(socket, "socket", _Blocked)
    monkeypatch.setattr(socket, "create_connection", _block)
    monkeypatch.setattr(socket, "getaddrinfo", _block)
    return attempts


def _cold_model_cache(monkeypatch, tmp_path) -> None:
    """Point the model cache at an empty directory, so absence is the condition under test."""
    try:
        import huggingface_hub.constants as constants
    except ImportError:
        return
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path / "hub"))


def test_the_offline_set_opens_no_connection_when_the_model_is_absent(monkeypatch, tmp_path):
    """The claim in docs/REPRODUCE.md, asserted on the path that broke it.

    Absence has to be decided from the local cache. Returning None is not enough on its own: the
    previous code also returned None, after trying the network and failing. The attempt count is
    what separates true in mechanism from true in outcome.
    """
    _cold_model_cache(monkeypatch, tmp_path)
    attempts = _guard(monkeypatch)

    session = onnx_session()

    assert session is None, (
        "the model cache was pointed at an empty directory, so the session must be absent"
    )
    assert attempts == [], (
        f"onnx_session opened {len(attempts)} connection(s) with the model absent. "
        "docs/REPRODUCE.md says a network connection is not needed, and that has to be true by "
        f"mechanism rather than because the attempt fails. Attempts: {attempts}"
    )


def test_the_guard_counts_a_connection_that_is_actually_attempted(monkeypatch):
    """V20. The zero above means nothing unless this counter is shown able to move.

    Nothing in the repository is exercised here on purpose. The point is the instrument: if the
    stubs stopped intercepting, this fails and the check above becomes a detector reporting a pass
    because it can no longer see anything.
    """
    attempts = _guard(monkeypatch)

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 9))

    assert len(attempts) == 1, (
        "the socket guard did not record a connection it was asked to make, so a zero elsewhere "
        "in this file would prove nothing"
    )
