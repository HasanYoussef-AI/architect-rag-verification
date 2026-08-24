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

THE TWO-RULER RULE IS ASSERTED ON THE EMITTED MARKUP, not on the source. A figure could satisfy
every naming rule in the generator and still render a shared axis label, so the check reads the
committed SVG text and requires that the first-pass and layer series are named separately and that
no bare shared label appears.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from src.figures.build_figures import FIGURES_DIR
from src.figures.build_tables import TABLES_DIR
from src.figures.build_tables import build_all as build_tables
from src.figures.figures import build_all as build_figures
from src.figures.figures import decomposition
from src.ingest.corpus_integrity import REPO_ROOT

# Computed at the commit that placed these files.
FIGURE_DIGESTS = {
    "context-sizes.svg": "f4d629137f29f78d4b3495adf29677cfb9c671300e49d2979cfe88f59f6d5eef",
    "flagged-fate.svg": "99b60325e982bb4caa1c1f8ae3926dcbcb974f78c475e1f04e8ada8115b09a81",
    "predictions.svg": "bec30eea4c1b8dd4358cb05a07ca2dc2f7154065232261c7c6b3358345c21af5",
    "rates-by-tier.svg": "3ddc2de14407976bbfa6dcbe23e099313820633948e125508fe0a0b599d2af24",
    "recall-by-stratum.svg": "0f96c8bc3d093dfbcc67ab7ddf7994147f019a6b70288030b517c5025baa889f",
    "reduction-decomposition.svg": "8a7e5845ab493220e419692ff148b530c46b1bde2158cb11cf3f094b40e2404b",
}

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
