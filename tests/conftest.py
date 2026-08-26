"""The offline suite opens no network connection, asserted across the whole session.

WHAT THIS ASSERTS AND WHY IT IS NOT SCOPED TO ONE FUNCTION. `docs/REPRODUCE.md` opens by saying
"Nothing here needs an API key, a network connection, or money." That is a claim about everything a
reader runs, not about one call. A guard around a single function cannot see the next one, and this
repository has been bitten twice inside that set: once by a dependency's telemetry opening a socket
while building a user agent, which nothing here called deliberately, and once by a guard that passed
precisely when a network was available to warm a cache early. Neither would have been caught by a
check scoped to whichever function happened to be involved the first time.

So the property is asserted where the claim is made, across the session. Every socket attempt from
any test, any code path and any dependency is recorded, and the run fails if the total is not zero.

ATTRIBUTION IS PART OF THE CHECK. A failure names the tests that opened connections and what they
reached for. A bare total would send whoever sees it bisecting, which is worse than not having the
check, because it costs an afternoon to learn what one line could have said.

THE STANDING CONSTRAINT, ADOPTED DELIBERATELY. No test in this suite may open a socket. Nothing here
does today, measured across every environment the walkthrough documents, including the one where the
dense arm runs with the model and the segment cache present. The constraint is chosen rather than
discovered: it is the right one for a repository whose central promise is that every published number
re-derives offline from committed bytes.

IF A TEST GENUINELY NEEDS A CONNECTION, raise it rather than exempting it. There is no exemption list
here and adding one would hollow out the claim, which is the same reason the lint selection and the
line length were both resolved without one. A test that needs the network is either outside the
offline set, in which case the set's boundary has moved and that is a decision, or it is a defect.
Either way it is a conversation and not a line in a skip list.

A CONSEQUENCE, ALSO CHOSEN. This makes the checks sensitive to third-party behaviour: a dependency
that starts fetching something on import can turn the build red with nothing in this tree changing.
That is the correct sensitivity for a project whose central claim depends on how its dependencies
behave, and it has already happened here once.
"""

from __future__ import annotations

import socket

import pytest

from tests._netguard import recording_stubs

# Everything the stubs intercept, in order. Drained into _ATTEMPTS after each test so that a
# failure can name the test rather than only the total.
_LIVE: list = []
_ATTEMPTS: list[tuple[str, object]] = []

_ORIGINAL = (socket.socket, socket.create_connection, socket.getaddrinfo)


def pytest_configure(config):
    blocked, block = recording_stubs(_LIVE)
    socket.socket = blocked
    socket.create_connection = block
    socket.getaddrinfo = block


def pytest_unconfigure(config):
    socket.socket, socket.create_connection, socket.getaddrinfo = _ORIGINAL


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Attribute anything recorded while this test ran to this test."""
    yield
    for what in _LIVE:
        _ATTEMPTS.append((item.nodeid, what))
    _LIVE.clear()


def pytest_sessionfinish(session, exitstatus):
    """Fail the run if anything opened a connection, naming what did."""
    for what in _LIVE:  # anything outside a test, at collection or teardown
        _ATTEMPTS.append(("<outside a test>", what))
    _LIVE.clear()
    if not _ATTEMPTS:
        return

    by_test: dict[str, list] = {}
    for nodeid, what in _ATTEMPTS:
        by_test.setdefault(nodeid, []).append(what)

    lines = [
        "",
        "=" * 78,
        f"OFFLINE GUARD: {len(_ATTEMPTS)} network connection attempt(s) during the suite.",
        "docs/REPRODUCE.md states that reproduction needs no network connection, and that has to",
        "be true by mechanism. These opened one:",
        "",
    ]
    for nodeid, whats in sorted(by_test.items()):
        lines.append(f"  {len(whats):4}  {nodeid}")
        for what in whats[:5]:
            lines.append(f"        {what!r}")
    lines += [
        "",
        "There is no exemption list. If one of these genuinely needs a connection, that is a",
        "decision about where the offline set ends, not a line to add here.",
        "=" * 78,
    ]
    print("\n".join(lines))
    session.exitstatus = 1
