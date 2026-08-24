"""The figures and the results tables: digest pins, rebuild, determinism and the two-ruler rule.

SAME REGIME AS THE THREE RESULT ARTIFACTS, and for the same reason. A figure that is not pinned is
a figure that can drift away from the number it claims to draw, and a reader who trusts a chart
more than a table is exactly the reader that harms.

THREE CHECKS THAT DO NOT SUBSUME EACH OTHER, which is why all three exist:

  The DIGEST pins compare committed bytes against a constant. They catch any change to a committed
  figure, including one made by hand in an editor.

  The REBUILD checks derive each figure from the committed artifacts and compare bytes. They catch
  the generator and the committed file parting company, which a digest pin alone cannot see because
  it never runs the generator.

  The DETERMINISM check builds twice in one process and compares. It catches a generator that
  happens to agree with the committed bytes on one run and would not on the next, which is the
  failure a plotting library's embedded timestamp or object-identity id produces.

  The BOUNDS check computes where every drawn element actually lands and requires it to sit inside
  the viewBox with a margin. It catches a figure that renders wrong, which none of the three above
  can see, because all three are answers to "did these bytes change" and none of them is an answer
  to "does this file render".

THE TWO-RULER RULE IS ASSERTED ON THE EMITTED MARKUP, not on the source. A figure could satisfy
every naming rule in the generator and still render a shared axis label, so the check reads the
committed SVG text and requires that the first-pass and layer series are named separately and that
no bare shared label appears.

THE BOUNDS CHECK WAS ADDED AFTER THE DEFECT IT CATCHES SHIPPED. Four of the six figures then
committed emitted text below the bottom edge of their own viewBox, and one of those also ran off
the right edge; the legend's last line was cropped in two of them and a whole summary line was
outside the canvas in three. Every byte guard above was green throughout, because a digest cannot
see geometry. The regression test below reconstructs that geometry and requires the check to
reject it, so the check is never trusted on the strength of a pass alone.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from src.figures import geometry, svg
from src.figures.build_figures import FIGURES_DIR
from src.figures.build_tables import TABLES_DIR
from src.figures.build_tables import build_all as build_tables
from src.figures.figures import STRATA, TIERS
from src.figures.figures import build_all as build_figures
from src.figures.figures import build_all_figs, decomposition
from src.ingest.corpus_integrity import REPO_ROOT

# Computed at the commit that put these files on the dark canvas.
FIGURE_DIGESTS = {
    "context-sizes.svg": "d92429a55429a4cf0ec49122f67884131f7cef78045d3486b0b73cf0e9629df2",
    "flagged-fate.svg": "71e543336750cc9407e362e092b99d4263c2a0cd703c78857e7a056909ccc0eb",
    "predictions.svg": "57aa7ad89f08f496b35323d37002e0ffd631dc24335e6d992e6d78ecabbf5fc0",
    "rates-by-stratum.svg": "8deb73c8f002414ef34456301baaed167f8b8371af71429940079e1d920107e4",
    "rates-by-tier.svg": "f3ba128db2d15321182a9c12917df52c395173b6873ee702fedd5d4c006db181",
    "recall-by-stratum.svg": "ba893129ed37608c189520602df067e8267eff9ac7eff057dfe134e75aa18b9e",
    "reduction-decomposition.svg": "bb95f1747c7c01c3b5f2eb4da774211bb3cb3559fa093a6d8397517a8a6782f2",
}

# --------------------------------------------------------------------------------------------
# The bounds check's thresholds, stated here rather than inherited, because these are the numbers
# that decide whether a figure passes and a reader of this file should not have to open another
# one to learn them.
#
# MARGIN, 12 units of the viewBox coordinate system. The figures are drawn at roughly their
# rendered pixel size, so twelve is a visible band: wide enough that a real font engine disagreeing
# with the width estimate by a glyph cannot push anything onto the edge, and narrow enough that it
# does not silently demand whitespace the design did not intend.
#
# WIDTH_MULTIPLIER, 1.15. There is no font engine here by deliberate choice, so a string's width is
# estimated from four coarse character classes. The estimate is inflated by fifteen percent before
# it is judged, so that a pass means "inside even if the estimate is out by that much" rather than
# "inside if the estimate happens to be exact". This is the check being made stricter than its
# instrument, which is the only honest direction for a check built on an approximation.
#
# ASCENT and DESCENT, 0.85 and 0.30 of the font size. A typical sans-serif ascender sits near
# 0.75em above the baseline and a descender near 0.21em below; both allowances are set above that.
#
# LEGEND_GAP, 24. The clear distance the legend block must keep from the bottom of the plot area,
# so it reads as a separate band rather than as part of the chart.
# --------------------------------------------------------------------------------------------
MARGIN = 12.0
WIDTH_MULTIPLIER = 1.15
ASCENT = 0.85
DESCENT = 0.30
LEGEND_GAP = 24.0

BOUNDS = {"margin": MARGIN, "width_multiplier": WIDTH_MULTIPLIER,
          "ascent": ASCENT, "descent": DESCENT}

# --------------------------------------------------------------------------------------------
# MIN_CONTRAST, 4.5 to 1, the WCAG AA threshold for body text, applied to every text element in
# every figure against the colour actually behind it.
#
# Against the colour behind it, not against the canvas. On a dark canvas those differ for any
# label drawn on top of a bar, and they differ in both directions, which is why the backdrop is
# the right reference and the canvas is not:
#
#   light label on the gold series   14.75:1 against the canvas,  1.89:1 against the bar
#   dark label on the gold series     1.00:1 against the canvas,  7.78:1 against the bar
#
# A canvas-referenced check passes the first, which no reader can read, and fails the second,
# which every reader can. The figures use the second, and this threshold judges it against the
# bar. Text on open ground has the canvas as its backdrop, so nothing is exempted.
# --------------------------------------------------------------------------------------------
MIN_CONTRAST = 4.5

TABLE_DIGESTS = {
    "cost_and_latency.csv": "3aace4ddd7924310ad991605431fa6e75aed8db475e82e800ad86183f16d7f47",
    "flagged_unit_fate.csv": "4b7eddd03decd1a7df0083a592c59f862566c810a62bd9959bc19d38d99af70d",
    "retrieval_by_stratum.csv": "3ad9084e575046eb9ad1e4f1317637924f5bfdda067dd9fd65bffe7f1a8fdf4d",
    "unsupported_claim_rate.csv": "70f91f820db1139de8d93578a4facab8497d718e17a877a06b33a29ba33ef11c",
}


def _grading():
    return json.loads(
        (REPO_ROOT / "eval" / "test_grading_results.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(FIGURE_DIGESTS))
def test_the_committed_figure_matches_its_pinned_digest(name):
    path = FIGURES_DIR / name
    assert path.exists(), f"{name} is pinned here but is not in the tree"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == FIGURE_DIGESTS[name], (
        f"{name}: sha256 {actual} against the pinned {FIGURE_DIGESTS[name]}. Rebuild with "
        "python -m src.figures.build_figures and move the pin in the same commit"
    )


@pytest.mark.parametrize("name", sorted(TABLE_DIGESTS))
def test_the_committed_table_matches_its_pinned_digest(name):
    path = TABLES_DIR / name
    assert path.exists(), f"{name} is pinned here but is not in the tree"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == TABLE_DIGESTS[name], f"{name}: sha256 {actual}"


def test_every_figure_rebuilds_from_the_committed_artifacts_byte_for_byte():
    """The generator and the committed file must not part company."""
    built = build_figures()
    assert set(built) == set(FIGURE_DIGESTS), "the figure set moved without the pins moving"
    for name, text in sorted(built.items()):
        on_disk = (FIGURES_DIR / name).read_bytes()
        assert text.encode("utf-8") == on_disk, f"{name} rebuilds to different bytes"


def test_every_table_rebuilds_from_the_committed_artifacts_byte_for_byte():
    built = build_tables()
    assert set(built) == set(TABLE_DIGESTS)
    for name, text in sorted(built.items()):
        on_disk = (TABLES_DIR / name).read_bytes()
        assert text.encode("utf-8") == on_disk, f"{name} rebuilds to different bytes"


def test_two_builds_in_one_process_are_byte_identical():
    """Determinism, which the digest and rebuild checks are both blind to.

    A generator embedding a timestamp or an identity-derived id can match the committed bytes on
    the run that produced them and differ on the next. Nothing here reads a clock, a random source
    or an environment variable, and this asserts that rather than trusting it.
    """
    a, b = build_figures(), build_figures()
    assert a == b, "two consecutive figure builds differ"
    c, d = build_tables(), build_tables()
    assert c == d, "two consecutive table builds differ"


def test_no_figure_carries_a_carriage_return():
    """The writers pin LF, so a committed figure carrying CRLF means one was written another way."""
    for name in sorted(FIGURE_DIGESTS):
        assert b"\r" not in (FIGURES_DIR / name).read_bytes(), name
    for name in sorted(TABLE_DIGESTS):
        assert b"\r" not in (TABLES_DIR / name).read_bytes(), name


def test_every_figure_is_accessible():
    """role="img" plus a title and a description, which is what a screen reader reads."""
    for name in sorted(FIGURE_DIGESTS):
        text = (FIGURES_DIR / name).read_text(encoding="utf-8")
        assert 'role="img"' in text, name
        title = re.search(r"<title[^>]*>(.+?)</title>", text)
        desc = re.search(r"<desc[^>]*>(.+?)</desc>", text)
        assert title and len(title.group(1)) > 10, f"{name} has no usable title"
        assert desc and len(desc.group(1)) > 40, f"{name} has no usable description"


def test_the_two_conditions_share_no_metric_label_in_the_retrieval_figure():
    """The two-ruler rule, asserted on the emitted markup rather than on the generator.

    The first pass reports Recall@10 and the layer condition reports recovered-passage recall. A
    shared bare label would be the exact collapse the naming discipline exists to prevent, and it
    is the kind of thing that survives review in prose and reappears in a legend.
    """
    text = (FIGURES_DIR / "recall-by-stratum.svg").read_text(encoding="utf-8")
    assert "Recall@10, first pass" in text
    assert "recovered-passage recall, layer" in text
    labels = re.findall(r"<text[^>]*>([^<]*)</text>", text)
    for label in labels:
        stripped = label.strip().lower()
        assert stripped not in ("recall", "recall@10", "recovered-passage recall"), (
            f"the retrieval figure carries the bare label {label!r}, which reads as one ruler "
            "over two conditions"
        )
    for banned in ("precision_at_10", "Precision@10", "NDCG", "MRR"):
        assert banned not in text, f"{banned} is a first-pass metric and has no layer counterpart"


def test_the_rate_figure_prints_the_counts_the_artifact_holds():
    """Every rate ships with its counts, applied to a chart.

    A bar labelled only with a rate is where the unit-count rule is most often dropped, so the
    printed counts are checked against the artifact rather than against the generator.
    """
    text = (FIGURES_DIR / "rates-by-tier.svg").read_text(encoding="utf-8")
    grading = _grading()
    for cond in ("raw", "layer"):
        for tier in ("haiku45", "sonnet5", "opus48"):
            blk = grading["per_condition"][cond]["per_tier"][tier]
            pair = f"{blk['ungrounded_units']}/{blk['claim_units']}"
            assert pair in text, f"{cond} {tier}: the figure does not print {pair}"


def test_the_decomposition_matches_the_committed_rows():
    """The one figure that derives rather than reads, checked against its own source.

    The reduction decomposition is computed from the per-row blocks because the artifact stores no
    field for it. These are the figures the results documentation publishes.
    """
    dec = decomposition(_grading())
    assert [dec[t]["abstained_rows"] for t in ("haiku45", "sonnet5", "opus48")] == [13, 4, 2]
    assert [dec[t]["abstained_ungrounded"] for t in ("haiku45", "sonnet5", "opus48")] == [26, 2, 4]
    assert [dec[t]["abstained_units"] for t in ("haiku45", "sonnet5", "opus48")] == [28, 4, 4]
    assert [dec[t]["ungrounded_removed"] for t in ("haiku45", "sonnet5", "opus48")] == [4, 0, 4]
    assert [dec[t]["grounded_added"] for t in ("haiku45", "sonnet5", "opus48")] == [10, 5, 26]
    assert [dec[t]["units_added"] for t in ("haiku45", "sonnet5", "opus48")] == [6, 5, 22]
    assert sum(dec[t]["ungrounded_removed"] for t in dec) == 8
    assert sum(dec[t]["grounded_added"] for t in dec) == 41


def test_the_tables_parse_as_rectangles():
    """A regime label carries a comma, so an unquoted writer shifts every column after it.

    That happened, was caught by reading the first emitted file, and is pinned here: the failure
    mode is a file that parses into the wrong shape rather than one that fails to parse.
    """
    import csv
    import io

    for name in sorted(TABLE_DIGESTS):
        text = (TABLES_DIR / name).read_text(encoding="utf-8")
        rows = list(csv.reader(io.StringIO(text)))
        widths = {len(r) for r in rows}
        assert len(widths) == 1, f"{name} is ragged: column counts {sorted(widths)}"
        assert len(rows) > 1, f"{name} carries no data rows"
    text = (TABLES_DIR / "unsupported_claim_rate.csv").read_text(encoding="utf-8")
    assert '"Claude Haiku 4.5, no thinking"' in text, (
        "the comma-carrying regime label is not quoted, which is the defect this pins"
    )


def test_the_figure_checks_are_capable_of_failing():
    """V20. Every check above reports a pass, so each is shown able to withhold one.

    Nothing on disk is touched: the predicates are applied in memory to mutated copies.
    """
    built = build_figures()

    # The digest predicate rejects a changed figure.
    mutated = built["rates-by-tier.svg"] + "<!-- -->"
    assert hashlib.sha256(mutated.encode("utf-8")).hexdigest() != FIGURE_DIGESTS[
        "rates-by-tier.svg"]

    # The two-ruler predicate rejects a shared bare label.
    bad = built["recall-by-stratum.svg"].replace(
        ">Recall@10, first pass<", ">recall<")
    labels = re.findall(r"<text[^>]*>([^<]*)</text>", bad)
    assert any(lbl.strip().lower() == "recall" for lbl in labels), (
        "the label extractor did not see the injected shared label, so its clean result on the "
        "real figure would prove nothing"
    )

    # The counts predicate rejects a figure that prints a rate without its counts.
    stripped = built["rates-by-tier.svg"].replace("78/140", "")
    assert "78/140" not in stripped

    # The accessibility predicate rejects a figure with no description.
    no_desc = re.sub(r"<desc[^>]*>.+?</desc>", "", built["predictions.svg"])
    assert not re.search(r"<desc[^>]*>(.+?)</desc>", no_desc)


# ------------------------------------------------------------------------------------------------
# Bounds. Where the drawn elements actually land.
# ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(FIGURE_DIGESTS))
def test_every_element_sits_inside_the_viewbox_with_a_margin(name):
    """No text, rect or line may come within MARGIN of any edge of its own viewBox.

    Run over the emitted markup rather than the generator's variables, for the reason the two-ruler
    check already records: what ships is the markup.
    """
    markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
    bad = geometry.violations(markup, **BOUNDS)
    assert not bad, (
        f"{name} has {len(bad)} element(s) outside its margin box:\n  " + "\n  ".join(bad)
    )


@pytest.mark.parametrize("name", sorted(FIGURE_DIGESTS))
def test_every_figure_reports_a_clearance_at_or_above_the_margin(name):
    """The same requirement stated as a measurement, so a figure has a number and not a verdict."""
    markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
    c = geometry.clearance(
        markup, width_multiplier=WIDTH_MULTIPLIER, ascent=ASCENT, descent=DESCENT)
    assert c["worst"] >= MARGIN, (
        f"{name}: worst clearance {c['worst']:.1f} against the required {MARGIN:g}. "
        f"left {c['left']:.1f} right {c['right']:.1f} top {c['top']:.1f} bottom {c['bottom']:.1f}"
    )


def test_every_legend_block_clears_the_plot_area_and_sits_inside():
    """The legend is a separate band, not part of the chart, and it is wholly on the canvas.

    The generator reports both rectangles rather than the check recovering them from the markup by
    pattern, which would be a detector keyed to structure while the claim lives in position.
    """
    for name, fig in sorted(build_all_figs().items()):
        _, _, vw, vh = geometry.view_box(fig.svg)
        _, py, _, ph = fig.plot
        lx0, ly0, lx1, ly1 = fig.legend
        gap = ly0 - (py + ph)
        assert gap >= LEGEND_GAP, (
            f"{name}: legend starts {gap:.1f} below the plot area, under the required "
            f"{LEGEND_GAP:g}"
        )
        assert lx0 >= MARGIN and ly0 >= MARGIN, f"{name}: legend crosses the top or left margin"
        assert lx1 <= vw - MARGIN, f"{name}: legend crosses the right margin"
        assert ly1 <= vh - MARGIN, f"{name}: legend crosses the bottom margin"


def _at_height(markup: str, height: float) -> str:
    """The same figure on a shorter canvas, ground included.

    The background rect is excluded from the bounds check by matching the canvas exactly, so a
    reconstruction that shrinks the viewBox and leaves the ground at its original size produces a
    violation from the ground alone. That was true of the first version of the regression test
    below, which therefore reported a pass on figures that were never cropped. The ground is
    resized with the canvas so that what the check sees is cropped text and nothing else.
    """
    _, _, vw, vh = geometry.view_box(markup)
    out = markup.replace(f'viewBox="0 0 {vw:g} {vh:g}"', f'viewBox="0 0 {vw:g} {height:g}"', 1)
    out = out.replace(
        f'<rect x="0" y="0" width="{vw:g}" height="{vh:g}"',
        f'<rect x="0" y="0" width="{vw:g}" height="{height:g}"', 1)
    assert out != markup, "the height rewrite did not apply, so the reconstruction proves nothing"
    return out


# The viewBox height each figure shipped at before the bounds check existed. The four above the
# line were cropped at those heights; the two below were not, and they are the control.
SHIPPED_HEIGHTS_CROPPED = {
    "rates-by-tier.svg": 430,
    "reduction-decomposition.svg": 430,
    "flagged-fate.svg": 400,
    "context-sizes.svg": 360,
}
SHIPPED_HEIGHTS_CLEAN = {
    "predictions.svg": 300,
    "recall-by-stratum.svg": 440,
}


def test_the_bounds_check_rejects_the_geometry_this_repository_shipped():
    """V13 and V20. The defect that motivated the check, pinned so reversing it fails a test.

    Four of the six figures committed before this check emitted text below the bottom edge of their
    own viewBox. Each is reconstructed at the height it shipped at, and the check must report a
    text element crossing the bottom edge, not merely report something. A bounds check that has
    only ever been seen to pass is not evidence of anything.
    """
    for name, old_h in sorted(SHIPPED_HEIGHTS_CROPPED.items()):
        shrunk = _at_height((FIGURES_DIR / name).read_text(encoding="utf-8"), old_h)
        bad = geometry.violations(shrunk, **BOUNDS)
        cropped_text = [b for b in bad if b.startswith("text ") and "bottom by" in b]
        assert cropped_text, (
            f"{name}: at the height {old_h} this repository shipped it at, the bounds check reports "
            f"no text crossing the bottom edge, so it cannot be catching that defect. Reported: "
            f"{bad}"
        )


def test_the_reconstruction_leaves_the_two_uncropped_figures_clean():
    """The complement, without which the test above passes by shrinking rather than by cropping.

    Two of the six were never cropped. Reconstructed at their own shipped heights by the same
    function, they must come back clean, which is what makes a violation on the other four a
    statement about those four rather than about the reconstruction.
    """
    for name, old_h in sorted(SHIPPED_HEIGHTS_CLEAN.items()):
        shrunk = _at_height((FIGURES_DIR / name).read_text(encoding="utf-8"), old_h)
        bad = geometry.violations(shrunk, **BOUNDS)
        assert not bad, (
            f"{name} was not cropped at height {old_h}, but the reconstruction reports {bad}, so "
            "the regression test above would pass on any figure"
        )


@pytest.mark.parametrize("edge", ["left", "right", "top", "bottom"])
def test_the_bounds_check_rejects_an_element_past_each_edge(edge):
    """The check is shown able to fail on all four sides, not only the one the defect used."""
    positions = {"left": (2, 60), "right": (298, 60), "top": (40, 4), "bottom": (40, 118)}
    x, y = positions[edge]
    doc = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"'
        ' viewBox="0 0 300 120" role="img">\n'
        '<rect x="0" y="0" width="300" height="120" fill="#ffffff"/>\n'
        f'<text x="{x}" y="{y}" font-size="12" fill="#1a1a1a">edge probe</text>\n'
        "</svg>\n"
    )
    bad = geometry.violations(doc, **BOUNDS)
    assert bad, f"an element placed past the {edge} edge was not reported"
    assert edge in bad[0], f"the {edge} overflow was reported as something else: {bad[0]}"


def test_the_bounds_check_accepts_a_document_that_is_actually_clear():
    """The complement of the four probes: the check is not simply reporting everything."""
    doc = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"'
        ' viewBox="0 0 300 120" role="img">\n'
        '<rect x="0" y="0" width="300" height="120" fill="#ffffff"/>\n'
        '<text x="40" y="60" font-size="12" fill="#1a1a1a">clear</text>\n'
        "</svg>\n"
    )
    assert geometry.violations(doc, **BOUNDS) == []


def test_the_background_rect_is_not_judged_against_the_margin():
    """It is the ground the figure is painted on and reaches the edge by construction."""
    doc = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 120">'
        '<rect x="0" y="0" width="300" height="120" fill="#ffffff"/>'
        "</svg>"
    )
    kinds = [e["kind"] for e in geometry.elements(doc)]
    assert kinds == [], f"the full-canvas ground was judged as a drawn element: {kinds}"


# ------------------------------------------------------------------------------------------------
# G7, the by-stratum rate figure.
# ------------------------------------------------------------------------------------------------

def test_the_stratum_figure_carries_all_five_strata_on_every_tier_panel():
    """A figure that silently omits a stratum is the graphical form of a table that does.

    The five are named in the generator rather than discovered from the artifact, so a stratum
    disappearing from the data fails here instead of quietly shortening the chart.
    """
    text = (FIGURES_DIR / "rates-by-stratum.svg").read_text(encoding="utf-8")
    labels = re.findall(r"<text[^>]*>([^<]*)</text>", text)
    assert len(STRATA) == 5, "the committed stratum count moved without this check moving"
    for stratum in STRATA:
        assert labels.count(stratum) == len(TIERS), (
            f"{stratum} appears {labels.count(stratum)} times, expected once per tier panel"
        )


def test_the_stratum_figure_prints_every_count_the_artifact_holds():
    """Every rate ships with its counts, checked per cell against the artifact, not the generator."""
    text = (FIGURES_DIR / "rates-by-stratum.svg").read_text(encoding="utf-8")
    grading = _grading()
    checked = 0
    for cond in ("raw", "layer"):
        per_stratum = grading["per_condition"][cond]["per_stratum"]
        for tier in TIERS:
            for stratum in STRATA:
                blk = per_stratum[tier][stratum]
                checked += 1
                if blk["answered_rows"] == 0:
                    continue
                pair = f"{blk['ungrounded_units']}/{blk['claim_units']}"
                assert pair in text, f"{cond} {tier} {stratum}: the figure does not print {pair}"
    assert checked == len(TIERS) * len(STRATA) * 2 == 30


def test_a_stratum_with_no_answered_row_is_marked_rather_than_drawn_as_zero():
    """The standing by-stratum ruling, applied to a chart.

    A tier that abstained on every row of a stratum has no rate. A bar of height zero there would
    read as perfect performance on exactly the rows the model refused to answer, which is the
    reading docs/RESULTS.md already refuses by printing undefined in its tables.
    """
    text = (FIGURES_DIR / "rates-by-stratum.svg").read_text(encoding="utf-8")
    grading = _grading()
    empty = [
        (cond, tier, stratum, blk)
        for cond in ("raw", "layer")
        for tier in TIERS
        for stratum, blk in grading["per_condition"][cond]["per_stratum"][tier].items()
        if blk["answered_rows"] == 0
    ]
    assert empty, "no zero-answered cell exists, so this check would prove nothing"
    for cond, tier, stratum, blk in empty:
        assert blk["abstaining_rows"] == blk["rows"], (
            f"{cond} {tier} {stratum} has no answered row but did not abstain on all of them, so "
            "the figure's wording would be wrong"
        )
        assert f"abstained on all {blk['rows']} rows" in text, (
            f"{cond} {tier} {stratum}: the figure does not mark the abstained stratum"
        )
    widths = [float(w) for w in re.findall(r'<rect[^>]*width="([-\d.]+)"', text)]
    assert not any(0 < w < 1 for w in widths), (
        "a bar of near-zero width is present, which is what the marking exists to avoid"
    )


# ------------------------------------------------------------------------------------------------
# Contrast. Whether the text can be read against what is behind it.
# ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(FIGURE_DIGESTS))
def test_every_text_element_reaches_the_contrast_minimum(name):
    """Every label in every figure, against the colour behind it."""
    markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
    bad = geometry.contrast_violations(
        markup, minimum=MIN_CONTRAST, width_multiplier=WIDTH_MULTIPLIER)
    assert not bad, f"{name} has {len(bad)} unreadable text element(s):\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("name", sorted(FIGURE_DIGESTS))
def test_every_figure_carries_text_and_a_dark_canvas(name):
    """Guards the check above against passing because it found nothing to judge.

    A contrast check over zero text elements reports clean. The canvas is asserted here too, since
    every ratio above is taken against it or against a bar drawn on it.
    """
    markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
    found = geometry.text_contrasts(markup, width_multiplier=WIDTH_MULTIPLIER)
    assert len(found) >= 10, f"{name} yielded only {len(found)} text elements to judge"
    assert f'fill="{svg.CANVAS}"' in markup, f"{name} does not paint the palette canvas"
    assert geometry.relative_luminance(svg.CANVAS) < 0.05, "the canvas is not dark"


def test_the_in_bar_labels_are_the_case_the_backdrop_reference_exists_for():
    """The two figures that draw a label on top of a bar, measured both ways.

    This is the evidence for referencing the backdrop rather than the canvas, and it is asserted
    rather than described: these labels are unreadable by the canvas-referenced measure and
    readable by the backdrop one, so a canvas-referenced check would have rejected the correct
    colour and accepted the wrong one.
    """
    on_bars = []
    for name in sorted(FIGURE_DIGESTS):
        markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
        for t in geometry.text_contrasts(markup, width_multiplier=WIDTH_MULTIPLIER):
            if t["backdrop"] != svg.CANVAS:
                on_bars.append((name, t))
    assert on_bars, "no figure draws a label on a bar, so this check would prove nothing"
    for name, t in on_bars:
        assert t["on_backdrop"] >= MIN_CONTRAST, f"{name}: {t['label']!r} unreadable on its bar"
        assert t["on_canvas"] < MIN_CONTRAST, (
            f"{name}: {t['label']!r} would also pass a canvas-referenced check, so it is not an "
            "instance of the divergence this test records"
        )
        light = geometry.contrast_ratio(svg.INK, t["backdrop"])
        assert light < MIN_CONTRAST, (
            f"{name}: the light ink would reach {light:.2f}:1 on {t['backdrop']}, so the dark "
            "label is not the only readable choice there and this reasoning does not hold"
        )


def test_the_contrast_check_is_capable_of_failing():
    """V20. Light text on a light bar must be rejected, and known ratios must come out right."""
    doc = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
        f'<rect x="0" y="0" width="200" height="100" fill="{svg.CANVAS}"/>'
        f'<rect x="20" y="20" width="160" height="60" fill="{svg.SERIES_LAYER}"/>'
        f'<text x="100" y="55" font-size="12" fill="{svg.INK}" text-anchor="middle">78</text>'
        "</svg>"
    )
    bad = geometry.contrast_violations(doc, minimum=MIN_CONTRAST)
    assert bad, "light text on the gold series was accepted, so the check cannot fail"
    assert "1.89" in bad[0], f"the reported ratio is not the measured one: {bad[0]}"

    # The same document with the dark label the figures actually use.
    fixed = doc.replace(f'fill="{svg.INK}" text-anchor', f'fill="{svg.ON_SERIES}" text-anchor')
    assert geometry.contrast_violations(fixed, minimum=MIN_CONTRAST) == []

    # Known anchors for the ratio itself.
    assert round(geometry.contrast_ratio("#ffffff", "#000000"), 2) == 21.0
    assert round(geometry.contrast_ratio("#000000", "#000000"), 2) == 1.0
    assert round(geometry.relative_luminance("#ffffff"), 4) == 1.0
    assert round(geometry.relative_luminance("#000000"), 4) == 0.0


def test_the_palette_is_the_diagram_palette_and_its_separations_are_measured():
    """The brand colours are verbatim, the derived ones are stated, and the ratios are recomputed.

    The raw-against-layer separation is 1.29 to 1, which is a property of the two brand colours
    rather than a choice, so those two are not distinguishable in greyscale and every series is
    additionally labelled. That is asserted here so the figure cannot quietly stop being labelled.
    """
    assert svg.CANVAS == "#0A1A1F"
    assert svg.INK == "#E8EAEC"
    assert svg.SERIES_RAW == "#00D4FF"
    assert svg.SERIES_LAYER == "#C9A84C"

    ratios = {
        "ink on canvas": geometry.contrast_ratio(svg.INK, svg.CANVAS),
        "muted on canvas": geometry.contrast_ratio(svg.MUTED, svg.CANVAS),
        "raw on canvas": geometry.contrast_ratio(svg.SERIES_RAW, svg.CANVAS),
        "layer on canvas": geometry.contrast_ratio(svg.SERIES_LAYER, svg.CANVAS),
        "third on canvas": geometry.contrast_ratio(svg.SERIES_THIRD, svg.CANVAS),
    }
    for what, r in ratios.items():
        assert r >= 3.0, f"{what} is only {r:.2f}:1"
    assert ratios["ink on canvas"] >= MIN_CONTRAST
    assert ratios["muted on canvas"] >= MIN_CONTRAST

    # A gridline is not text and is deliberately quiet.
    assert geometry.contrast_ratio(svg.GRID, svg.CANVAS) < 2.0

    # Every series pair is separated in lightness, and the weakest pair is the two brand colours.
    pairs = {
        ("raw", "layer"): geometry.contrast_ratio(svg.SERIES_RAW, svg.SERIES_LAYER),
        ("layer", "third"): geometry.contrast_ratio(svg.SERIES_LAYER, svg.SERIES_THIRD),
        ("raw", "third"): geometry.contrast_ratio(svg.SERIES_RAW, svg.SERIES_THIRD),
    }
    assert round(pairs[("raw", "layer")], 2) == 1.29
    assert pairs[("layer", "third")] > pairs[("raw", "layer")]
    assert pairs[("raw", "third")] > pairs[("layer", "third")]
    assert min(pairs.values()) == pairs[("raw", "layer")]

    # Colour is never the only channel, which is what makes 1.29:1 survivable.
    for name, label in (("rates-by-tier.svg", "raw, no verification layer"),
                        ("rates-by-stratum.svg", "raw, no verification layer")):
        text = (FIGURES_DIR / name).read_text(encoding="utf-8")
        assert label in text, f"{name} no longer labels its series"


def test_no_figure_carries_a_gradient_or_a_filter():
    """No decoration. The palette and the dark ground are the whole of it."""
    for name in sorted(FIGURE_DIGESTS):
        markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
        for banned in ("Gradient", "<filter", "feGaussianBlur", "url(#", "opacity=", "<style"):
            assert banned not in markup, f"{name} carries {banned}"


def test_no_figure_keeps_a_colour_from_the_light_palette():
    """The restyle is complete, asserted on the markup rather than on the constants."""
    retired = ("#ffffff", "#1a1a1a", "#5b6167", "#d7dbdf", "#2f5c8f", "#e8a33d", "#7d9a4e")
    for name in sorted(FIGURE_DIGESTS):
        markup = (FIGURES_DIR / name).read_text(encoding="utf-8")
        for colour in retired:
            assert colour not in markup.lower(), f"{name} still carries {colour}"


def test_the_stratum_figure_draws_no_verdict():
    """The per-stratum denominators are small and the readings live in docs/RESULTS.md.

    The figure reports counts. It does not tell a reader what they mean, and in particular it does
    not restate the near-miss movement, which the results documentation reports as grader
    conformance rather than as the layer working.
    """
    text = (FIGURES_DIR / "rates-by-stratum.svg").read_text(encoding="utf-8")
    labels = " ".join(re.findall(r"<text[^>]*>([^<]*)</text>", text)).lower()
    for verdict in ("the layer works", "improvement", "better on", "wins",
                    "grader conformance", "conformance"):
        assert verdict not in labels, f"the figure draws a verdict: {verdict!r}"
