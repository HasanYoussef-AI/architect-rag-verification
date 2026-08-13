"""The verification record's shape, its join to the query set, and its re-derivable numbers.

Nothing in the suite read eval/test_query_verification.jsonl before this file. The one-row-per-
query property has been cited since the frame was written as though a test held it, and the
one-key-set property likewise; neither was asserted anywhere, and the only committed reader of
the file is src/goldset/check_committed_duplication_scans.py, which filters to multi_hop rows
and looks at nothing else. Two of the four checks here are therefore live on the twenty
committed rows the moment they land, not vacuous:

- the key set is one set across the whole file, ordered identically on every row
- the ids align one for one with eval/test_queries.jsonl, in order, and the query text agrees

The other two are vacuous until single_hop rows land and binding from that commit:

- no row records more than two designation attempts, with exactly one binding
- the recorded query-to-span overlap re-derives from committed code

The one-key-set property is what makes a stratum's block addable at all. Each stratum adds a
nested block that is null on every row outside it, so a row can be checked for the whole key set
rather than for the subset its own stratum happens to use. A varying key set makes that check
impossible, which is worth more than avoiding nulls.
"""

from __future__ import annotations

import json

import pytest

from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import tokenize_query

EVAL = REPO_ROOT / "eval"
VERIFICATION = EVAL / "test_query_verification.jsonl"
QUERIES = EVAL / "test_queries.jsonl"

# The nested per-stratum blocks. A row carries every key and nulls the blocks that are not its
# own, so this names which keys are blocks rather than leaving it to be inferred from a value
# that happens to be a dict.
STRATUM_BLOCKS = ("multi_hop", "single_hop")

# One re-designation is permitted, both attempts are recorded on the row, and a second failure
# rejects the pick. The rule is forced rather than optional because span choice is an unbounded
# fitting surface without it, so the bound is pinned here and reversing it costs a failing test.
MAX_DESIGNATION_ATTEMPTS = 2


def _rows(path):
    if not path.exists():
        pytest.skip(f"{path.name} is not committed yet")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _verification() -> list[dict]:
    return _rows(VERIFICATION)


def _blocks(block: str) -> list[tuple[dict, dict]]:
    """Every (row, block) pair for one stratum block, empty before that stratum lands."""
    return [(r, r[block]) for r in _verification() if r.get(block)]


def test_the_file_has_one_key_set_over_every_row():
    """One key set, and the same order, over the whole file.

    Derived from the file rather than pinned to a literal list, because a literal would have to
    be hand-edited at every stratum commit and a list edited by hand is a list that can be
    edited to fit. What this catches is a row that gained or lost a key relative to its
    neighbours, which is the failure mode a per-row optional-field convention produces.

    Ordered rather than set equality: the ordered form is strictly stronger, it holds on the
    committed file, and it keeps the diff on a stratum commit legible, since a new block appended
    at the end shows as one added key on every row rather than as a reshuffle.
    """
    rows = _verification()
    assert rows, f"{VERIFICATION.name} is present but empty"
    first = list(rows[0].keys())
    assert first[0] == "id", f"the first key is {first[0]!r}, not id"
    for row in rows:
        assert list(row.keys()) == first, (
            f"{row.get('id')}: keys {list(row.keys())} against the file's key set {first}"
        )


def test_stratum_blocks_are_nulled_rather_than_omitted():
    """A stratum block present on any row is a key on every row, and no row carries two.

    The set of blocks is read from the file rather than required to equal STRATUM_BLOCKS. A
    stratum that has not been authored yet has no block anywhere, and demanding its key before
    its commit would assert a property of a later commit from an earlier one. What is asserted
    is the property that actually holds at every commit: once a block exists it exists on every
    row, which is the null-rather-than-omit convention the one-key-set check depends on.

    STRATUM_BLOCKS is still named, and used in the other direction: a non-null block whose name
    is not in it fails, so a block added under a new name is a deliberate act rather than a
    silent one.
    """
    rows = _verification()
    seen = {k for row in rows for k in row if k in STRATUM_BLOCKS}
    for row in rows:
        for block in sorted(seen):
            assert block in row, f"{row['id']}: no {block} key. Null it rather than omitting it"
        present = [b for b in row if b in STRATUM_BLOCKS and row.get(b)]
        assert len(present) <= 1, (
            f"{row['id']}: carries {len(present)} stratum blocks, {present}. A row belongs to one "
            "stratum, so a second non-null block means a block was copied rather than authored"
        )
        unknown = [k for k, v in row.items()
                   if isinstance(v, dict) and k not in STRATUM_BLOCKS and "drawn_unit" in v]
        assert not unknown, (
            f"{row['id']}: carries what looks like a stratum block under an unregistered name, "
            f"{unknown}. Add it to STRATUM_BLOCKS deliberately rather than defaulting"
        )


def test_verification_rows_align_one_for_one_with_the_query_set():
    """One verification row per query row, same ids, same order, same query text.

    eval/README.md states 'one row per test query' and nothing asserted it. The alignment is
    load-bearing in both directions: a verification row with no query is a record of something
    that is not in the set, and a query with no verification row is a gold claim shipped with no
    evidence behind it. Order is asserted too, because the two files are read side by side and a
    reordering that preserved the id sets would still make them unreadable together.

    Query text is compared as well as the id, since an id match with divergent text would mean
    the evidence on the row was gathered against a different question than the one that ships.
    """
    queries = _rows(QUERIES)
    verification = _verification()
    assert [r["id"] for r in verification] == [r["id"] for r in queries], (
        "ids diverge between the two files; "
        f"verification only {sorted({r['id'] for r in verification} - {r['id'] for r in queries})}, "
        f"queries only {sorted({r['id'] for r in queries} - {r['id'] for r in verification})}"
    )
    for q, v in zip(queries, verification, strict=True):
        assert q["query"] == v["query"], (
            f"{q['id']}: the query text differs between the two files.\n"
            f"  queries:      {q['query']!r}\n  verification: {v['query']!r}"
        )


def test_no_row_records_more_than_one_re_designation():
    """The one-re-designation bound, and exactly one binding attempt per row.

    Vacuous until single_hop rows land, which is deliberate: it is committed before the rows it
    judges, so it cannot be read as a bound written around the attempt counts that arrived.
    Measured over the screening record it will judge: 24 rows at one attempt and 3 at two, so
    the bound is not slack against its own data by a wide margin, and a third attempt on any row
    fails here.
    """
    pairs = _blocks("single_hop")
    if not pairs:
        pytest.skip("no committed single_hop rows yet; the bound turns on at that commit")
    for row, block in pairs:
        attempts = block["designation_attempts"]
        assert 1 <= len(attempts) <= MAX_DESIGNATION_ATTEMPTS, (
            f"{row['id']}: {len(attempts)} designation attempts, bound is "
            f"{MAX_DESIGNATION_ATTEMPTS}. A second failure rejects the pick rather than "
            "producing a third attempt"
        )
        binding = [a for a in attempts if a["outcome"] == "binding"]
        assert len(binding) == 1, (
            f"{row['id']}: {len(binding)} attempts marked binding, expected exactly one"
        )
        assert block["binding_designation"] == {"span": binding[0]["span"],
                                                "chunk_id": binding[0]["chunk_id"]}, (
            f"{row['id']}: binding_designation does not equal the attempt marked binding, so the "
            "row states two different spans as the one that binds"
        )


def test_recorded_query_to_span_overlap_re_derives():
    """The overlap numbers, recomputed from the committed query text and the committed span.

    This is what makes the block's reproducibility level a fact rather than a claim. Every value
    in it is a function of three committed things, the query, the binding span, and
    src/retrieve/tokenize.py:tokenize_query, so it re-derives at level 1 with no model and no
    key. The block's command names this test, which is a command a reviewer can actually run;
    naming the tool that first produced the numbers would name something they do not have.

    Vacuous until single_hop rows land. Measured over the 18 rows it will judge: all 18
    re-derive, and a control adding one token to a query moves containment from 0.2222 to
    0.2000, so the comparison is not one that passes on anything.
    """
    pairs = _blocks("single_hop")
    if not pairs:
        pytest.skip("no committed single_hop rows yet; the re-derivation turns on at that commit")
    for row, block in pairs:
        overlap = block["query_span_lexical_overlap"]
        query_tokens = set(tokenize_query(row["query"]))
        span_tokens = set(tokenize_query(block["binding_designation"]["span"]))
        shared = sorted(query_tokens & span_tokens)
        where = f"{row['id']}: "
        assert len(query_tokens) == overlap["query_tokens"], where + "query_tokens"
        assert len(span_tokens) == overlap["span_tokens"], where + "span_tokens"
        assert shared == overlap["shared"], where + "shared"
        assert sorted(query_tokens - span_tokens) == overlap["query_only"], where + "query_only"
        assert round(len(shared) / len(query_tokens), 4) == overlap["containment"], (
            where + f"containment, re-derived {len(shared)}/{len(query_tokens)}"
        )
        assert round(len(shared) / len(query_tokens | span_tokens), 4) == overlap["jaccard"], (
            where + f"jaccard, re-derived {len(shared)}/{len(query_tokens | span_tokens)}"
        )
