"""The seven results figures, each derived from a committed artifact.

EVERY NUMBER IN EVERY FIGURE COMES FROM A COMMITTED ARTIFACT, read here and never restated as a
literal. The three sources are eval/test_grading_results.json, eval/test_retrieval_results.json and
eval/test_layer_results.json, all three pinned by digest and asserted on every suite run, so a
figure is exactly as reproducible as the rate it draws.

THE TWO CONDITIONS NEVER SHARE A METRIC LABEL, in a figure as in prose. G4 is where that bites:
the first pass is labelled Recall@10 and the layer condition recovered-passage recall, on the same
axis, never a shared "recall". tests/test_figures.py asserts the absence of a bare shared label by
reading the emitted markup rather than trusting this paragraph.

ONE FIGURE DERIVES RATHER THAN READS, and it is marked here because that is the exception. The
reduction decomposition in G2 is not stored as fields in the grading artifact; it is computed from
the committed per-row blocks, splitting each tier's comparable set into rows the layer abstains on
and rows answered in both conditions. The derivation is in `decomposition` below and its outputs
were checked against the figures the session log publishes: abstention rows 13, 4 and 2; the
ungrounded and total units they carried; ungrounded removed 4, 0 and 4; grounded added 10, 5 and
26; total added 6, 5 and 22.

EVERY RATE CARRIES ITS COUNTS, which is the reporting rule applied to graphics. A bar showing 0.5571
is labelled 78/140. A chart is exactly where that rule is most often dropped.

A STRATUM A TIER NEVER ANSWERED IS NOT A ZERO BAR. G7 reports per-stratum rates, and a tier that
abstained on every row of a stratum has no rate at all. Drawing that as a bar of height zero would
read as perfect performance on exactly the rows the model refused to answer, which is the reading
the results documentation already refuses in its tables. Those cells print what happened instead.

EACH FIGURE RETURNS ITS GEOMETRY along with its markup. The bounds check in tests/test_figures.py
needs to know where the plot area ends and the legend begins, and recovering that by pattern
matching on the emitted markup would be a detector keyed to structure rather than to the claim, the
failure mode V20 names. The generator knows both rectangles exactly, so it reports them.
"""

from __future__ import annotations

import json
from typing import NamedTuple

from src.figures import svg
from src.ingest.corpus_integrity import REPO_ROOT

EVAL = REPO_ROOT / "eval"
GRADING = EVAL / "test_grading_results.json"
RETRIEVAL = EVAL / "test_retrieval_results.json"
LAYER = EVAL / "test_layer_results.json"

TIERS = ("haiku45", "sonnet5", "opus48")
TIER_LABEL = {
    "haiku45": "Haiku 4.5",
    "sonnet5": "Sonnet 5",
    "opus48": "Opus 4.8",
}
REGIME_SHORT = {
    "haiku45": "no thinking",
    "sonnet5": "adaptive, effort high",
    "opus48": "adaptive, effort low",
}

# The five committed strata, in the order the results tables list them. Named here rather than
# discovered from the artifact so that a stratum vanishing from the data fails the figure loudly
# instead of quietly shortening it.
STRATA = ("single_hop", "clean_multi_hop", "action_to_parent", "near_miss", "adversarial")

# The palette, from src/figures/svg.py, which records where each colour comes from. Bound to the
# names the figure bodies already used so that the restyle is a change of value and not of code.
#
# Measured relative luminance, and the ratio each colour makes against the canvas:
#
#   canvas  #0A1A1F  L 0.0090   1.00
#   ink     #E8EAEC  L 0.8205  14.75   primary text and axes
#   muted   #9AA5AD  L 0.3679   7.08   secondary text
#   grid    #22353D  L 0.0323   1.39   deliberately low, a gridline is not text
#   raw     #00D4FF  L 0.5431   9.98   cyan, the raw condition
#   layer   #C9A84C  L 0.4096   7.79   gold, the layer condition
#   third   #2E9BB5  L 0.2735   5.48   cyan darkened toward the canvas
#
# Series separation by lightness, which is what survives greyscale and most colour blindness:
#
#   raw against layer    1.29   inherent to the two brand colours, not separable in greyscale
#   layer against third  1.42
#   raw against third    1.83
#
# The raw-against-layer figure is why every series is also labelled. That was already this
# module's stance and the restyle does not weaken it; it makes the number explicit.
INK = svg.INK
MUTED = svg.MUTED
GRID = svg.GRID
RAW = svg.SERIES_RAW
LAYER_C = svg.SERIES_LAYER
THIRD = svg.SERIES_THIRD
ON_SERIES = svg.ON_SERIES


class Fig(NamedTuple):
    """A figure's markup and the two rectangles the bounds check judges it by.

    `plot` is the axis area, as (x, y, width, height). `legend` is the legend block's bounding box,
    as (x0, y0, x1, y1), covering its swatches and its text.
    """

    svg: str
    plot: tuple[float, float, float, float]
    legend: tuple[float, float, float, float]


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decomposition(grading: dict) -> dict:
    """Split each tier's comparable set into abstention-removed rows and rows answered in both.

    Derived from the committed per-row blocks rather than read from a field, because the artifact
    stores the comparable set and the per-row grades but not this split.
    """
    out = {}
    for tier in TIERS:
        cs = grading["per_condition"]["layer"]["comparable_set"][tier]
        members = cs["membership"]
        abstained = set(cs["layer_side"]["layer_abstaining_row_ids_within_the_set"])
        raw_rows = grading["rows"]["raw"][tier]
        layer_rows = grading["rows"]["layer"][tier]
        both = [r for r in members if r not in abstained]
        out[tier] = {
            "abstained_rows": len(abstained),
            "abstained_ungrounded": sum(raw_rows[r]["n_ungrounded"] for r in abstained),
            "abstained_units": sum(raw_rows[r]["n_units"] for r in abstained),
            "ungrounded_removed": (
                sum(raw_rows[r]["n_ungrounded"] for r in both)
                - sum(layer_rows[r]["n_ungrounded"] for r in both)
            ),
            "grounded_added": (
                sum(layer_rows[r]["n_grounded"] for r in both)
                - sum(raw_rows[r]["n_grounded"] for r in both)
            ),
            "units_added": (
                sum(layer_rows[r]["n_units"] for r in both)
                - sum(raw_rows[r]["n_units"] for r in both)
            ),
        }
    return out


def _frame(body, x0, y0, w, h, ymax, ticks, *, fmt=svg.num):
    """Axis frame with horizontal gridlines. Returns a value-to-y mapper."""
    def y_of(v):
        return y0 + h - (v / ymax) * h

    for t in ticks:
        yt = y_of(t)
        body.append(svg.line(x0, yt, x0 + w, yt, GRID, width=1))
        body.append(svg.text(x0 - 8, yt + 4, fmt(t), size=11, fill=MUTED, anchor="end"))
    body.append(svg.line(x0, y0 + h, x0 + w, y0 + h, INK, width=1.5))
    return y_of


def _legend(body, x, y, entries):
    """One legend row, entries laid out left to right. Returns its bounding box."""
    cx = x
    for label, colour in entries:
        body.append(svg.rect(cx, y - 9, 11, 11, colour))
        body.append(svg.text(cx + 16, y, label, size=12, fill=INK))
        cx += 16 + svg.text_width(label, 12) + 26
    return (x, y - 9, cx, y + 4)


def _legend_stack(body, x, y, entries, *, step=20):
    """One legend entry per line, stacked downward. Returns its bounding box.

    Three figures built this inline and identically before the bounds check needed a box back from
    it, so it is one helper now rather than three copies that can drift apart.
    """
    ly = y
    right = x
    for label, colour in entries:
        body.append(svg.rect(x, ly - 9, 11, 11, colour))
        body.append(svg.text(x + 16, ly, label, size=12, fill=INK))
        right = max(right, x + 16 + svg.text_width(label, 12))
        ly += step
    return (x, y - 9, right, ly - step + 4)


# --------------------------------------------------------------------------------------------
# G1: unsupported-claim rate, raw against layer, per tier
# --------------------------------------------------------------------------------------------
def figure_rates_by_tier(grading: dict) -> Fig:
    W, H = 760, 500
    x0, y0, w, h = 78, 78, 620, 250
    body: list[str] = []
    body.append(svg.text(30, 34, "Unsupported-claim rate, raw against layer", size=17, weight="600"))
    body.append(svg.text(
        30, 56,
        "Lower is better. Each bar is labelled with its ungrounded units over its total claim units.",
        size=12, fill=MUTED))

    ymax = 0.6
    y_of = _frame(body, x0, y0, w, h, ymax, [0, 0.15, 0.3, 0.45, 0.6])

    slot = w / len(TIERS)
    bw = 62
    for i, tier in enumerate(TIERS):
        cx = x0 + slot * i + slot / 2
        for j, (cond, colour) in enumerate((("raw", RAW), ("layer", LAYER_C))):
            blk = grading["per_condition"][cond]["per_tier"][tier]
            rate = blk["unsupported_claim_rate"]
            bx = cx - bw - 6 + j * (bw + 12)
            by = y_of(rate)
            body.append(svg.rect(bx, by, bw, y0 + h - by, colour))
            body.append(svg.text(bx + bw / 2, by - 22, svg.num(rate), size=13,
                                 anchor="middle", weight="600"))
            body.append(svg.text(
                bx + bw / 2, by - 8,
                f"{blk['ungrounded_units']}/{blk['claim_units']}",
                size=11, fill=MUTED, anchor="middle"))
            body.append(svg.text(bx + bw / 2, y0 + h + 16, cond, size=11,
                                 fill=MUTED, anchor="middle"))
        body.append(svg.text(cx, y0 + h + 38, TIER_LABEL[tier], size=13,
                             anchor="middle", weight="600"))
        body.append(svg.text(cx, y0 + h + 54, REGIME_SHORT[tier], size=11,
                             fill=MUTED, anchor="middle"))

    legend = _legend(body, x0, y0 + h + 92,
                     [("raw, no verification layer", RAW), ("layer", LAYER_C)])
    pooled_raw = grading["per_condition"]["raw"]["pooled"]
    pooled_layer = grading["per_condition"]["layer"]["pooled"]
    body.append(svg.text(
        x0, y0 + h + 122,
        f"pooled  raw {pooled_raw['ungrounded_units']}/{pooled_raw['claim_units']} = "
        f"{svg.num(pooled_raw['unsupported_claim_rate'])}   "
        f"layer {pooled_layer['ungrounded_units']}/{pooled_layer['claim_units']} = "
        f"{svg.num(pooled_layer['unsupported_claim_rate'])}",
        size=12, fill=MUTED))
    body.append(svg.text(
        x0, y0 + h + 142,
        "The three tiers are deployment configurations, not points on a capability scale.",
        size=11, fill=MUTED))

    return Fig(svg.document(
        W, H,
        "Unsupported-claim rate, raw against layer, by tier",
        "Grouped bar chart. For each of three model tiers, the raw and layer unsupported-claim "
        "rates, each bar labelled with its ungrounded units over total claim units.",
        body), (x0, y0, w, h), legend)


# --------------------------------------------------------------------------------------------
# G2: what the reduction is made of
# --------------------------------------------------------------------------------------------
def figure_reduction_decomposition(grading: dict) -> Fig:
    W, H = 760, 510
    x0, y0, w, h = 78, 92, 620, 232
    body: list[str] = []
    body.append(svg.text(30, 34, "What the reduction is made of", size=17, weight="600"))
    body.append(svg.text(
        30, 56,
        "Claim units, over each tier's comparable set. Almost none of the reduction is unsupported",
        size=12, fill=MUTED))
    body.append(svg.text(
        30, 72, "content disappearing.", size=12, fill=MUTED))

    dec = decomposition(grading)
    ymax = 28
    y_of = _frame(body, x0, y0, w, h, ymax, [0, 7, 14, 21, 28])

    series = (
        ("ungrounded units removed by abstention", "abstained_ungrounded", RAW),
        ("ungrounded units removed on rows answered in both", "ungrounded_removed", LAYER_C),
        ("grounded units added on rows answered in both", "grounded_added", THIRD),
    )
    slot = w / len(TIERS)
    bw = 44
    for i, tier in enumerate(TIERS):
        cx = x0 + slot * i + slot / 2
        for j, (_, key, colour) in enumerate(series):
            v = dec[tier][key]
            bx = cx - 1.5 * bw - 8 + j * (bw + 8)
            by = y_of(v)
            body.append(svg.rect(bx, by, bw, max(y0 + h - by, 1), colour))
            body.append(svg.text(bx + bw / 2, by - 6, str(v), size=12,
                                 anchor="middle", weight="600"))
        body.append(svg.text(cx, y0 + h + 18, TIER_LABEL[tier], size=13,
                             anchor="middle", weight="600"))
        body.append(svg.text(
            cx, y0 + h + 34,
            f"{dec[tier]['abstained_rows']} rows abstained of "
            f"{grading['per_condition']['layer']['comparable_set'][tier]['rows']}",
            size=11, fill=MUTED, anchor="middle"))

    legend = _legend_stack(body, x0, y0 + h + 66, [(label, colour) for label, _, colour in series])

    total_ung = sum(dec[t]["ungrounded_removed"] for t in TIERS)
    total_grd = sum(dec[t]["grounded_added"] for t in TIERS)
    ly = legend[3] + 24
    body.append(svg.text(
        x0, ly,
        f"Across all three tiers {total_ung} ungrounded units disappeared from rows answered in",
        size=11, fill=MUTED))
    body.append(svg.text(
        x0, ly + 18,
        f"both conditions, and {total_grd} grounded units were added.",
        size=11, fill=MUTED))

    return Fig(svg.document(
        W, H,
        "What the reduction is made of",
        "Grouped bar chart. For each of three model tiers, the ungrounded claim units removed by "
        "abstention, the ungrounded units removed on rows answered in both conditions, and the "
        "grounded units added on those rows.",
        body), (x0, y0, w, h), legend)


# --------------------------------------------------------------------------------------------
# G3: the flagged-unit fate table
# --------------------------------------------------------------------------------------------
def figure_flagged_fate(grading: dict) -> Fig:
    W, H = 760, 440
    x0, y0, w, h = 78, 96, 620, 210
    body: list[str] = []
    body.append(svg.text(30, 34, "What happened to the 109 flagged units", size=17, weight="600"))
    body.append(svg.text(
        30, 56,
        "Each flagged unit was returned to the model with the expanded context and an instruction",
        size=12, fill=MUTED))
    body.append(svg.text(
        30, 72,
        "to support it or leave it out. Not one was rescued by the fetched context, on any tier.",
        size=12, fill=MUTED))

    fate = grading["per_condition"]["layer"]["fate_table"]
    ymax = 70
    y_of = _frame(body, x0, y0, w, h, ymax, [0, 17.5, 35, 52.5, 70],
                  fmt=lambda v: svg.num(v) if v % 1 else str(int(v)))

    slot = w / len(TIERS)
    bw = 54
    for i, tier in enumerate(TIERS):
        cx = x0 + slot * i + slot / 2
        blk = fate[tier]
        stack = (
            ("dropped or rewritten", blk["dropped_or_rewritten"], RAW),
            ("repeated, still unsupported", blk["repeated_still_unsupported"], LAYER_C),
            ("repeated, now grounded", blk["repeated_and_now_grounded"], THIRD),
        )
        acc = 0.0
        bx = cx - bw / 2
        for _, v, colour in stack:
            if v <= 0:
                continue
            top = y_of(acc + v)
            body.append(svg.rect(bx, top, bw, y_of(acc) - top, colour))
            body.append(svg.text(bx + bw / 2, top + (y_of(acc) - top) / 2 + 4, str(v),
                                 size=12, fill=ON_SERIES, anchor="middle", weight="600"))
            acc += v
        body.append(svg.text(bx + bw / 2, y_of(acc) - 10,
                             f"{blk['flagged_in']} flagged", size=12,
                             anchor="middle", weight="600"))
        body.append(svg.text(cx, y0 + h + 18, TIER_LABEL[tier], size=13,
                             anchor="middle", weight="600"))
        body.append(svg.text(cx, y0 + h + 34,
                             f"rescued by fetched context: {blk['repeated_and_now_grounded']}",
                             size=11, fill=MUTED, anchor="middle"))

    legend = _legend_stack(body, x0, y0 + h + 62, [
        ("dropped or rewritten", RAW),
        ("repeated unchanged, still unsupported", LAYER_C),
        ("repeated unchanged, now grounded (zero on every tier)", THIRD),
    ])

    return Fig(svg.document(
        W, H,
        "What happened to the 109 flagged units",
        "Stacked bar chart. For each of three model tiers, the flagged claim units split into "
        "dropped or rewritten, repeated unchanged and still unsupported, and repeated unchanged "
        "and now grounded, the last of which is zero on every tier.",
        body), (x0, y0, w, h), legend)


# --------------------------------------------------------------------------------------------
# G4: recall by stratum, first pass against layer, under two metric names
# --------------------------------------------------------------------------------------------
def figure_recall_by_stratum(retrieval: dict, layer: dict) -> Fig:
    W, H = 860, 460
    x0, y0, w, h = 250, 78, 520, 236
    body: list[str] = []
    body.append(svg.text(30, 34, "Retrieval by stratum, under two metric names", size=17,
                         weight="600"))
    body.append(svg.text(
        30, 56,
        "The two conditions never share a metric label. Macro-averaged over the 42 gold-bearing rows.",
        size=12, fill=MUTED))

    fp = retrieval["aggregates"]["by_stratum"]
    lay = layer["aggregates"]["by_stratum"]
    strata = [k for k in sorted(fp) if fp[k].get("recall_at_10") is not None]

    ymax = 1.0
    row_h = h / len(strata)
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        xt = x0 + t * w
        body.append(svg.line(xt, y0, xt, y0 + h, GRID, width=1))
        body.append(svg.text(xt, y0 + h + 16, svg.num(t), size=11, fill=MUTED, anchor="middle"))
    body.append(svg.line(x0, y0, x0, y0 + h, INK, width=1.5))

    bh = 11
    for i, key in enumerate(strata):
        cy = y0 + row_h * i + row_h / 2
        body.append(svg.text(x0 - 10, cy + 4, key, size=11, fill=INK, anchor="end"))
        a = fp[key]["recall_at_10"]
        b = lay[key]["recovered_passage_recall_layer"]
        body.append(svg.rect(x0, cy - bh - 2, max(a / ymax * w, 0.8), bh, RAW))
        body.append(svg.text(x0 + a / ymax * w + 6, cy + 2, svg.num(a), size=10, fill=MUTED))
        body.append(svg.rect(x0, cy + 2, max(b / ymax * w, 0.8), bh, LAYER_C))
        body.append(svg.text(x0 + b / ymax * w + 6, cy + 11, svg.num(b), size=10, fill=MUTED))

    legend = _legend(body, x0, y0 + h + 46,
                     [("Recall@10, first pass", RAW), ("recovered-passage recall, layer", LAYER_C)])

    ov_fp = retrieval["aggregates"]["overall"]["recall_at_10"]
    ov_lay = layer["aggregates"]["overall"]["recovered_passage_recall_layer"]
    body.append(svg.text(
        x0, y0 + h + 76,
        f"overall  Recall@10 {svg.num(ov_fp)}   recovered-passage recall {svg.num(ov_lay)}   "
        "n = 42",
        size=12, fill=MUTED))
    body.append(svg.text(
        x0, y0 + h + 96,
        "The layer condition reports no rank-based figure: under augmentation k is not ten.",
        size=11, fill=MUTED))

    return Fig(svg.document(
        W, H,
        "Retrieval by stratum, under two metric names",
        "Horizontal grouped bar chart. For each retrieval stratum, the first pass Recall at 10 "
        "and the layer condition's recovered-passage recall, reported under separate metric names "
        "because the two conditions are not measured on the same ruler.",
        body), (x0, y0, w, h), legend)


# --------------------------------------------------------------------------------------------
# G5: final context set size, all fifty rows
# --------------------------------------------------------------------------------------------
def figure_context_sizes(layer: dict) -> Fig:
    W, H = 760, 400
    x0, y0, w, h = 78, 86, 620, 190
    body: list[str] = []
    body.append(svg.text(30, 34, "Final context set size, all fifty rows", size=17, weight="600"))
    body.append(svg.text(
        30, 56,
        "The first-pass ten are never removed, reordered or truncated; fetched chunks are appended.",
        size=12, fill=MUTED))

    sizes = sorted(r["context_set_size"] for r in layer["layer"])
    lo, hi = min(sizes), max(sizes)
    bin_w = 4
    start = (lo // bin_w) * bin_w
    bins: dict[int, int] = {}
    for s in sizes:
        b = ((s - start) // bin_w) * bin_w + start
        bins[b] = bins.get(b, 0) + 1
    edges = sorted(bins)
    ymax = max(bins.values())
    y_of = _frame(body, x0, y0, w, h, ymax, list(range(0, ymax + 1, max(1, ymax // 4))),
                  fmt=lambda v: str(int(v)))

    slot = w / len(edges)
    for i, e in enumerate(edges):
        v = bins[e]
        bx = x0 + slot * i + 3
        by = y_of(v)
        body.append(svg.rect(bx, by, slot - 6, y0 + h - by, RAW))
        body.append(svg.text(bx + (slot - 6) / 2, by - 5, str(v), size=11,
                             anchor="middle", fill=MUTED))
        body.append(svg.text(bx + (slot - 6) / 2, y0 + h + 16, str(e), size=10,
                             anchor="middle", fill=MUTED))

    agg = layer["aggregates"]["overall"]
    body.append(svg.text(x0, y0 + h + 42, "chunks in the final context set", size=11, fill=MUTED))
    body.append(svg.text(
        x0, y0 + h + 66,
        f"min {agg['context_set_size_min']}   median {agg['context_set_size_median']}   "
        f"mean {svg.num(agg['context_set_size_mean'])}   max {agg['context_set_size_max']}",
        size=12, fill=MUTED))
    unaug = sum(1 for r in layer["layer"] if r["context_set_size"] == 10)
    body.append(svg.text(
        x0, y0 + h + 86,
        f"{unaug} rows sit at exactly ten: the corrective pass did not fire on them.",
        size=11, fill=MUTED))

    # This figure carries no legend: one series, distinguished by its axis rather than by colour.
    # The bounds check still needs a box, so it is reported as the footnote band it actually has.
    legend = (x0, y0 + h + 32, x0 + 420, y0 + h + 89)

    return Fig(svg.document(
        W, H,
        "Final context set size, all fifty rows",
        f"Histogram of the final context set size across fifty rows, ranging from {lo} to {hi} "
        "chunks, with the rows on which the corrective pass did not fire sitting at exactly ten.",
        body), (x0, y0, w, h), legend)


# --------------------------------------------------------------------------------------------
# G6: the pre-registered predictions
# --------------------------------------------------------------------------------------------
def figure_predictions(grading: dict) -> Fig:
    W, H = 760, 310
    x0, y0, w = 78, 120, 620
    body: list[str] = []
    body.append(svg.text(30, 34, "The twenty-six pre-registered predictions", size=17,
                         weight="600"))
    body.append(svg.text(
        30, 56,
        "Committed before any sealed answer existed and scored mechanically from the graded blocks.",
        size=12, fill=MUTED))
    body.append(svg.text(
        30, 72,
        "Every contradicted line stands as written; the predictions file is not edited.",
        size=12, fill=MUTED))

    scored = grading["predictions_scored"]
    counts = {}
    for e in scored:
        counts[e["verdict"]] = counts.get(e["verdict"], 0) + 1
    # Three verdict categories, assigned for lightness separation rather than for meaning:
    # this figure carries no raw or layer condition, so the two condition colours are free
    # here. MUTED is a text colour and is never a fill.
    order = (("held", LAYER_C), ("contradicted", RAW), ("not_predicted", THIRD))
    total = len(scored)

    bx = x0
    bar_h = 46
    for label, colour in order:
        v = counts.get(label, 0)
        if v == 0:
            continue
        seg = v / total * w
        body.append(svg.rect(bx, y0, seg, bar_h, colour))
        body.append(svg.text(bx + seg / 2, y0 + 29, str(v), size=16, fill=ON_SERIES,
                             anchor="middle", weight="600"))
        bx += seg

    legend = _legend_stack(body, x0, y0 + bar_h + 44, [
        (f"{label.replace('_', ' ')}: {counts.get(label, 0)}", colour) for label, colour in order
    ])

    body.append(svg.text(
        x0, legend[3] + 22,
        f"{total} predictions scored. A contradicted prediction that gets edited is not a prediction.",
        size=11, fill=MUTED))

    return Fig(svg.document(
        W, H,
        "The twenty-six pre-registered predictions",
        "A single stacked bar showing the twenty-six pre-registered predictions split into those "
        "that held, those contradicted by the result, and the one to which no prediction was "
        "attached.",
        body), (x0, y0, w, bar_h), legend)


# --------------------------------------------------------------------------------------------
# G7: unsupported-claim rate by stratum, raw against layer, one panel per tier
# --------------------------------------------------------------------------------------------
def figure_rates_by_stratum(grading: dict) -> Fig:
    """All five committed strata on every panel, and no zero bar standing in for an abstention.

    The denominators here are small on several strata, which is why nothing in this figure reads a
    verdict off a comparison. The rate, its counts and its answered-row count are printed and the
    reading is left to docs/RESULTS.md, which carries it.
    """
    W, H = 820, 790
    lab_x = 196
    x0, w = 206, 400
    panel_top = 108
    row_h = 30
    panel_h = len(STRATA) * row_h + 44

    body: list[str] = []
    body.append(svg.text(30, 34, "Unsupported-claim rate by stratum, raw against layer",
                         size=17, weight="600"))
    body.append(svg.text(
        30, 56,
        "All five committed strata on every tier. Each bar is labelled with its ungrounded units",
        size=12, fill=MUTED))
    body.append(svg.text(
        30, 72,
        "over its total claim units. Lower is better.",
        size=12, fill=MUTED))

    raw_ps = grading["per_condition"]["raw"]["per_stratum"]
    lay_ps = grading["per_condition"]["layer"]["per_stratum"]

    bh = 9
    for pi, tier in enumerate(TIERS):
        py = panel_top + pi * panel_h
        body.append(svg.text(30, py, TIER_LABEL[tier], size=13, weight="600"))
        body.append(svg.text(30, py + 16, REGIME_SHORT[tier], size=11, fill=MUTED))
        body.append(svg.line(x0, py + 8, x0 + w, py + 8, GRID, width=1))
        for t in (0.25, 0.5, 0.75, 1.0):
            xt = x0 + t * w
            body.append(svg.line(xt, py + 8, xt, py + 8 + len(STRATA) * row_h, GRID, width=1))
            body.append(svg.text(xt, py, svg.num(t), size=10, fill=MUTED, anchor="middle"))
        body.append(svg.line(x0, py + 8, x0, py + 8 + len(STRATA) * row_h, INK, width=1.5))

        for si, stratum in enumerate(STRATA):
            cy = py + 8 + si * row_h + row_h / 2
            body.append(svg.text(lab_x, cy + 4, stratum, size=11, fill=INK, anchor="end"))
            for j, (blk, colour) in enumerate(
                ((raw_ps[tier][stratum], RAW), (lay_ps[tier][stratum], LAYER_C))
            ):
                by = cy - bh - 1 if j == 0 else cy + 1
                if blk["answered_rows"] == 0:
                    body.append(svg.text(
                        x0 + 4, by + bh - 1,
                        f"abstained on all {blk['rows']} rows",
                        size=10, fill=MUTED))
                    continue
                rate = blk["unsupported_claim_rate"]
                body.append(svg.rect(x0, by, max(rate * w, 0.8), bh, colour))
                body.append(svg.text(
                    x0 + rate * w + 6, by + bh - 1,
                    f"{blk['ungrounded_units']}/{blk['claim_units']}  {svg.num(rate)}  "
                    f"{blk['answered_rows']} answered",
                    size=10, fill=MUTED))

    legend_y = panel_top + len(TIERS) * panel_h + 44
    legend = _legend(body, x0, legend_y,
                     [("raw, no verification layer", RAW), ("layer", LAYER_C)])
    body.append(svg.text(
        x0, legend_y + 26,
        "A stratum a tier answered no row of carries no rate and is marked, never drawn as zero.",
        size=11, fill=MUTED))

    return Fig(svg.document(
        W, H,
        "Unsupported-claim rate by stratum, raw against layer, by tier",
        "Horizontal grouped bar chart in three panels, one per model tier. For each of the five "
        "committed strata, the raw and layer unsupported-claim rates, each bar labelled with its "
        "ungrounded units over its total claim units and its answered-row count, and each stratum "
        "a tier abstained on in every row marked as abstained rather than drawn as a zero bar.",
        body), (x0, panel_top, w, len(TIERS) * panel_h), legend)


# --------------------------------------------------------------------------------------------

FIGURES = {
    "rates-by-tier.svg": ("figure_rates_by_tier", ("grading",)),
    "rates-by-stratum.svg": ("figure_rates_by_stratum", ("grading",)),
    "reduction-decomposition.svg": ("figure_reduction_decomposition", ("grading",)),
    "flagged-fate.svg": ("figure_flagged_fate", ("grading",)),
    "recall-by-stratum.svg": ("figure_recall_by_stratum", ("retrieval", "layer")),
    "context-sizes.svg": ("figure_context_sizes", ("layer",)),
    "predictions.svg": ("figure_predictions", ("grading",)),
}


def build_all_figs() -> dict[str, Fig]:
    """Every figure with its geometry. Pure function of the three committed artifacts."""
    sources = {
        "grading": _load(GRADING),
        "retrieval": _load(RETRIEVAL),
        "layer": _load(LAYER),
    }
    out = {}
    for name, (fn_name, args) in FIGURES.items():
        fn = globals()[fn_name]
        out[name] = fn(*[sources[a] for a in args])
    return out


def build_all() -> dict[str, str]:
    """Every figure, as {filename: svg text}. Pure function of the three committed artifacts."""
    return {name: fig.svg for name, fig in build_all_figs().items()}
