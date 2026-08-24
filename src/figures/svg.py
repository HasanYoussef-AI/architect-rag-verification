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

COLOUR. Figures paint an explicit ground rather than inheriting the page's. GitHub renders an
embedded SVG over the reader's theme background, so a figure with a transparent ground renders
against two different colours for two different readers and one of them will be unreadable. The
ground is stated here, which makes a figure look the same to both.

The ground is now the dark canvas of the palette the diagrams use, and the palette is the one the
owner's public architect-worldcup repository carries in its committed diagrams: canvas #0A1A1F,
text #E8EAEC, cyan #00D4FF for the raw condition and gold #C9A84C for the layer condition, matching
the diagrams where cyan is data and gold is the processed path. Earlier revisions of this module
painted a light ground and argued for it on the same reasoning; what changed is which explicit
ground is used, not whether one is stated.

The palette does not rely on the red-green axis. It does not separate cyan from gold by lightness
either: those two sit at a 1.29 to 1 luminance ratio, which is a property of the two brand colours
rather than a choice made here, so they are not distinguishable in greyscale. Every series is
additionally labelled, which is why colour is never the only channel and why that ratio is
survivable. The third series is set apart in lightness from both, and the values and their
measurements are in `figures.py` beside the constants.

CONTRAST IS ASSERTED, NOT ASSUMED. Every text element is measured against the colour actually
behind it, which is the canvas for text on open ground and the bar fill for a label drawn on top of
a bar, and required to reach 4.5 to 1. Measuring in-bar labels against the canvas instead would
pass light text sitting on a light bar, which is the one case the check exists to catch.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

# --------------------------------------------------------------------------------------------
# The palette. Canvas, ink and the two condition colours are taken verbatim from the diagrams;
# the rest are derived from them and each derivation states what it is for and what it measures.
# Luminance is the WCAG relative luminance and every ratio below is against the canvas unless
# stated otherwise. The measurements live in tests/test_figures.py, which recomputes them.
# --------------------------------------------------------------------------------------------
CANVAS = "#0A1A1F"        # the ground, from the diagram palette
INK = "#E8EAEC"           # primary text and axes, from the diagram palette. 14.75:1 on canvas
MUTED = "#9AA5AD"         # secondary text. Canvas lightened toward ink. 7.08:1 on canvas
GRID = "#22353D"          # gridlines. Canvas lightened slightly. 1.39:1, deliberately low
SERIES_RAW = "#00D4FF"    # raw condition, cyan, from the diagram palette where cyan is data
SERIES_LAYER = "#C9A84C"  # layer condition, gold, from the diagram palette, the processed path
SERIES_THIRD = "#2E9BB5"  # third series. Cyan darkened toward canvas, set apart in lightness
ON_SERIES = "#0A1A1F"     # a label drawn on top of a series fill, which is light, so this is dark

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


def text(x, y, s, *, size=12, fill=INK, anchor="start", weight=None, family=None):
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
        rect(0, 0, width, height, CANVAS),
    ]
    return "\n".join(head + body + ["</svg>", ""])
