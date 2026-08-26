"""The socket stubs the offline guard is built from, shared by the session hook and its control.

ONE FACTORY, TWO SINKS, WHICH IS WHAT LETS THE CONTROL SHIP. The session-wide guard in conftest.py
installs these stubs with a session sink and fails the run if anything lands in it. Its control has
to prove the counter moves, and a control that opened a connection into the session sink would trip
the very check it exists to verify, which would then need an exemption for itself. Exemptions are the
shape this repository has declined twice, for the lint selection and the line length, so there is
none here.

Instead the control installs stubs built by this same factory over a private sink. Its connection is
intercepted by its own stub and never reaches the session's, and what is proven is this code, which
is the code the session guard runs. The control ships and runs on every suite, so the session's zero
is shown to be a measurement every time rather than on the day it was written.
"""

from __future__ import annotations

import socket


def recording_stubs(sink: list):
    """Return (socket_class, blocking_callable) that append to `sink` and refuse the connection.

    Three entry points are covered because a caller can reach the network through any of them: the
    socket constructor, the connection helper, and name resolution, which is where a request usually
    starts. The refusal is what makes an attempt visible as a failure rather than as traffic.
    """

    class _Blocked(socket.socket):
        def __init__(self, *args, **kwargs):
            sink.append("socket()")
            raise OSError("the offline reproducibility set must not open a connection")

    def _block(*args, **kwargs):
        sink.append(args[0] if args else "()")
        raise OSError("the offline reproducibility set must not open a connection")

    return _Blocked, _block


def install(monkeypatch, sink: list) -> list:
    """Point the three socket entry points at stubs recording into `sink`. Returns `sink`."""
    blocked, block = recording_stubs(sink)
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", block)
    monkeypatch.setattr(socket, "getaddrinfo", block)
    return sink
