"""Geometry of emitted SVG markup, so a figure's bounds can be asserted rather than eyeballed.

WHY THIS EXISTS. The figures were guarded by three byte-level checks from the commit that placed
them: a digest pin, a rebuild against the committed artifacts, and a two-build determinism check.
All three were green while four of the six figures emitted text below the bottom edge of their own
viewBox, because none of them ever asked where a glyph lands. A byte guard answers "did this file
change"; it cannot answer "does this file render". This module supplies the second question, and
`tests/test_figures.py` asserts it.

THE EXTENT OF A STRING IS ESTIMATED, NOT MEASURED, and every threshold here exists to absorb that.
There is no font engine in this repository by deliberate choice, recorded in `svg.py`, so the width
of a rendered string is approximated from per-character classes. The estimate is used here to bound
a region rather than to place one, so it is inflated by an explicit multiplier before it is judged,
and the vertical extent is taken from the font size with ascent and descent allowances well above
what a typical sans-serif face occupies. A check built on an approximation is only honest if the
approximation is padded in the direction that makes the check stricter, which is what these do.

The parser reads the emitted markup rather than the generator's variables, for the reason the
two-ruler check already records: a figure can satisfy every rule in its source and still emit
something else. What ships is the markup, so the markup is what is measured.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import unescape

from src.figures.svg import text_width

# --------------------------------------------------------------------------------------------
# Defaults. tests/test_figures.py states the values it judges with explicitly rather than
# inheriting them silently, so a threshold change is visible in the test that depends on it.
# --------------------------------------------------------------------------------------------

# Multiplier applied to the estimated width of every string before it is judged. text_width sorts
# characters into four coarse classes, so a real face can exceed the estimate on a string that is
# unluckily distributed. Padding the estimate makes a pass mean "inside even if the estimate is
# wrong by this much" rather than "inside if the estimate happens to be right".
WIDTH_MULTIPLIER = 1.15

# Fraction of the font size a glyph occupies above its baseline, and below it. A typical sans-serif
# ascender sits near 0.75em and a descender near 0.21em; these are set above both so that a face
# with unusually tall capitals or deep descenders is still bounded.
ASCENT = 0.85
DESCENT = 0.30

# Minimum clear distance from every drawn element to each of the four viewBox edges.
MARGIN = 12.0

# Minimum clear vertical distance between the bottom of the plot area and the top of the legend
# block, so the legend reads as a separate band rather than as part of the chart.
LEGEND_GAP = 24.0

_SVG_RE = re.compile(r'<svg\b[^>]*\bviewBox="([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"')
_TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.DOTALL)
_RECT_RE = re.compile(r"<rect\b([^>]*)/>")
_LINE_RE = re.compile(r"<line\b([^>]*)/>")


def _attr(attrs: str, name: str, default: float | None = None) -> float | None:
    m = re.search(rf'\b{name}="([-\d.]+)"', attrs)
    if m:
        return float(m.group(1))
    return default


def _str_attr(attrs: str, name: str, default: str) -> str:
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return m.group(1) if m else default


def view_box(markup: str) -> tuple[float, float, float, float]:
    """The viewBox as (min_x, min_y, width, height). Raises if the document has none."""
    m = _SVG_RE.search(markup)
    if not m:
        raise ValueError("no viewBox on the svg root")
    return tuple(float(g) for g in m.groups())  # type: ignore[return-value]


def elements(
    markup: str,
    *,
    width_multiplier: float = WIDTH_MULTIPLIER,
    ascent: float = ASCENT,
    descent: float = DESCENT,
) -> list[dict]:
    """Every drawn element as {kind, label, x0, y0, x1, y1}.

    The full-canvas background rect is excluded: it is the ground the figure is painted on and is
    exactly the viewBox by construction, so judging it against a margin would fail every figure for
    the one element that is supposed to reach the edge.
    """
    _, _, vw, vh = view_box(markup)
    out: list[dict] = []

    for attrs, raw in _TEXT_RE.findall(markup):
        s = unescape(raw)
        size = _attr(attrs, "font-size", 12.0) or 12.0
        x = _attr(attrs, "x", 0.0) or 0.0
        y = _attr(attrs, "y", 0.0) or 0.0
        anchor = _str_attr(attrs, "text-anchor", "start")
        w = text_width(s, size) * width_multiplier
        if anchor == "middle":
            x0, x1 = x - w / 2, x + w / 2
        elif anchor == "end":
            x0, x1 = x - w, x
        else:
            x0, x1 = x, x + w
        out.append({
            "kind": "text",
            "label": s,
            "x0": x0, "y0": y - ascent * size,
            "x1": x1, "y1": y + descent * size,
        })

    for attrs in _RECT_RE.findall(markup):
        x = _attr(attrs, "x", 0.0) or 0.0
        y = _attr(attrs, "y", 0.0) or 0.0
        w = _attr(attrs, "width", 0.0) or 0.0
        h = _attr(attrs, "height", 0.0) or 0.0
        if x == 0 and y == 0 and w == vw and h == vh:
            continue
        out.append({
            "kind": "rect", "label": f"rect {w}x{h}",
            "x0": x, "y0": y, "x1": x + w, "y1": y + h,
        })

    for attrs in _LINE_RE.findall(markup):
        x1v = _attr(attrs, "x1", 0.0) or 0.0
        y1v = _attr(attrs, "y1", 0.0) or 0.0
        x2v = _attr(attrs, "x2", 0.0) or 0.0
        y2v = _attr(attrs, "y2", 0.0) or 0.0
        out.append({
            "kind": "line", "label": "line",
            "x0": min(x1v, x2v), "y0": min(y1v, y2v),
            "x1": max(x1v, x2v), "y1": max(y1v, y2v),
        })

    return out


def violations(
    markup: str,
    *,
    margin: float = MARGIN,
    width_multiplier: float = WIDTH_MULTIPLIER,
    ascent: float = ASCENT,
    descent: float = DESCENT,
) -> list[str]:
    """Every element whose extent leaves the margin box, worst first, as readable lines."""
    _, _, vw, vh = view_box(markup)
    found: list[tuple[float, str]] = []
    for el in elements(
        markup, width_multiplier=width_multiplier, ascent=ascent, descent=descent
    ):
        over = {
            "left": margin - el["x0"],
            "right": el["x1"] - (vw - margin),
            "top": margin - el["y0"],
            "bottom": el["y1"] - (vh - margin),
        }
        worst = max(over.values())
        if worst > 0:
            sides = ", ".join(f"{k} by {v:.1f}" for k, v in over.items() if v > 0)
            found.append((
                worst,
                f"{el['kind']} {el['label']!r} at "
                f"({el['x0']:.1f},{el['y0']:.1f})-({el['x1']:.1f},{el['y1']:.1f}) "
                f"leaves the {margin:g}px margin of the {vw:g}x{vh:g} viewBox: {sides}",
            ))
    found.sort(key=lambda pair: -pair[0])
    return [line for _, line in found]


def clearance(
    markup: str,
    *,
    width_multiplier: float = WIDTH_MULTIPLIER,
    ascent: float = ASCENT,
    descent: float = DESCENT,
) -> dict[str, float]:
    """Smallest distance from any drawn element to each edge. Negative means it crosses the edge.

    This is the measurement the bounds check reduces to a verdict, reported separately so a figure
    can be described by how much room it actually has rather than only by whether it passed.
    """
    _, _, vw, vh = view_box(markup)
    els = elements(markup, width_multiplier=width_multiplier, ascent=ascent, descent=descent)
    if not els:
        raise ValueError("no drawn elements")
    return {
        "left": min(e["x0"] for e in els),
        "right": min(vw - e["x1"] for e in els),
        "top": min(e["y0"] for e in els),
        "bottom": min(vh - e["y1"] for e in els),
        "worst": min(
            min(e["x0"] for e in els),
            min(vw - e["x1"] for e in els),
            min(e["y0"] for e in els),
            min(vh - e["y1"] for e in els),
        ),
    }
