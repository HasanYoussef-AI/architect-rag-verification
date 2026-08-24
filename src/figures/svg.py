"""Minimal deterministic SVG primitives.

WHY THIS EXISTS RATHER THAN A PLOTTING LIBRARY. Every figure in docs/figures/ is pinned by digest
and rebuilt byte-for-byte by a test, on the same regime the three result artifacts use. A plotting
library makes that hard for reasons that have nothing to do with the data: SVG back-ends embed a
creation timestamp, a library version string, per-element ids derived from object identity, and
font metrics resolved against whatever fonts the machine happens to have. Each of those is a source
of byte drift that would have to be stripped after the fact, and a determinism claim that rests on
stripping is weaker than one that rests on never emitting.

Emitting the markup directly makes determinism a property of construction. Nothing here reads a
clock, a random source, an environment variable or a font. The same inputs produce the same bytes.

It also keeps the figures inside the repository's reproducibility posture. Adding a plotting
dependency for a documentation artifact would mean a reviewer needs it installed to rebuild a
figure, when everything else in the offline set needs nothing but the standard library and numpy.

TEXT WIDTH IS ESTIMATED, NOT MEASURED, and that is a deliberate limitation. Without a font engine
there is no way to measure a rendered string, so `text_width` approximates from per-character
widths at a nominal size. It is used only for centring and for background boxes, never for a
number, so an approximation that is a few percent out shifts a label by a pixel and changes no
figure's meaning.

COLOUR. Figures paint an explicit light background rather than inheriting the page's. GitHub
renders an embedded SVG over the reader's theme background, and a figure with a transparent ground
and dark text is unreadable in dark mode. An explicit ground is bright in dark mode and correct in
both, which is the better failure. The series palette is distinguishable in greyscale and does not
rely on the red-green axis; every series is additionally distinguished by its label, so colour is
never the only channel.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

# Nominal per-character advance widths at font-size 1, by rough class. Estimation only.
_NARROW = set("iljItf1.,:;'|!")
_WIDE = set("mwMW@%")


def text_width(s: str, size: float) -> float:
    """Approximate rendered width of `s` at `size`. Centring only, never a reported value."""
    total = 0.0
    for ch in s:
        if ch in _NARROW:
            total += 0.30
        elif ch in _WIDE:
            total += 0.92
        elif ch.isupper():
            total += 0.66
        else:
            total += 0.53
    return total * size


def num(value: float) -> str:
    """Fixed formatting so a float never reaches the markup through repr.

    Three decimals, trailing zeros and a trailing point removed. Deterministic across platforms:
    the same float always renders to the same string.
    """
    s = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def rect(x, y, w, h, fill, *, opacity=None, rx=None):
    parts = [f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"']
    if rx is not None:
        parts.append(f' rx="{num(rx)}"')
    parts.append(f' fill="{fill}"')
    if opacity is not None:
        parts.append(f' opacity="{num(opacity)}"')
    parts.append("/>")
    return "".join(parts)


def line(x1, y1, x2, y2, stroke, *, width=1.0, dash=None):
    parts = [
        f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}"',
        f' stroke="{stroke}" stroke-width="{num(width)}"',
    ]
    if dash:
        parts.append(f' stroke-dasharray="{dash}"')
    parts.append("/>")
    return "".join(parts)


def text(x, y, s, *, size=12, fill="#1a1a1a", anchor="start", weight=None, family=None):
    fam = family or "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    parts = [
        f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}"',
        f' font-family="{fam}" fill="{fill}"',
    ]
    if anchor != "start":
        parts.append(f' text-anchor="{anchor}"')
    if weight:
        parts.append(f' font-weight="{weight}"')
    parts.append(f">{escape(s)}</text>")
    return "".join(parts)


def document(width: float, height: float, title: str, desc: str, body: list[str]) -> str:
    """Wrap `body` in an accessible SVG root.

    role="img" plus <title> and <desc> is what a screen reader reads. The embedding page carries
    its own alt text as well; both exist because a reader may meet the file directly.
    """
    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(width)}" height="{num(height)}"'
        f' viewBox="0 0 {num(width)} {num(height)}" role="img"'
        f' aria-labelledby="figure-title figure-desc">',
        f"<title id=\"figure-title\">{escape(title)}</title>",
        f"<desc id=\"figure-desc\">{escape(desc)}</desc>",
        rect(0, 0, width, height, "#ffffff"),
    ]
    return "\n".join(head + body + ["</svg>", ""])
