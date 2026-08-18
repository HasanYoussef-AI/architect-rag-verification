"""The verification record's shape, its join to the query set, and its re-derivable numbers.

Nothing in the suite read eval/test_query_verification.jsonl before this file. The one-row-per-
query property has been cited since the frame was written as though a test held it, and the
one-key-set property likewise; neither was asserted anywhere, and the only committed reader of
the file is src/goldset/check_committed_duplication_scans.py, which filters to multi_hop rows
and looks at nothing else. Two of the four checks here are therefore live on the twenty
committed rows the moment they land, not vacuous:

- the key set is one set across the whole file, ordered identically on every row
- the ids align one for one with eval/test_queries.jsonl, in order, and the query text agrees

Two more were vacuous until single_hop rows landed and are binding from that commit. Both were
scoped to the single_hop block and are now selected on the field they judge, so a later stratum
shipping the same field is judged by the same predicate rather than passing unseen:

- no block records more than two designation attempts, with exactly one binding
- the recorded query-to-span overlap re-derives from committed code

The one-key-set property is what makes a stratum's block addable at all. Each stratum adds a
nested block that is null on every row outside it, so a row can be checked for the whole key set
rather than for the subset its own stratum happens to use. A varying key set makes that check
impossible, which is worth more than avoiding nulls.

The last section resolves every pytest node id a command field names, across this artifact and
the rejection log. It exists because 18 committed rows cited a node defined in another file,
which collects zero tests and reports 'no tests ran' rather than failing.
"""

from __future__ import annotations

import ast
import json

import pytest

from src.goldset.relation_positions import (
    INCLUDES,
    document_of,
    load_relations,
    relation_derived_carriers,
)
from src.ingest.corpus_integrity import REPO_ROOT
from src.retrieve.tokenize import tokenize_query

EVAL = REPO_ROOT / "eval"
VERIFICATION = EVAL / "test_query_verification.jsonl"
QUERIES = EVAL / "test_queries.jsonl"

# The nested per-stratum blocks. A row carries every key and nulls the blocks that are not its
# own, so this names which keys are blocks rather than leaving it to be inferred from a value
# that happens to be a dict.
#
# Appended in authoring order rather than sorted, so a stratum commit shows one added key at the
# end of every row instead of a reshuffle of the ordered key set.
STRATUM_BLOCKS = ("multi_hop", "single_hop", "action_to_parent", "near_miss")

# Top-level keys that are dict-valued and are NOT stratum blocks. The adversarial stratum ships
# its evidence on nulled top-level keys rather than in a nested block, a convention this file has
# carried since that stratum landed, so a detector that failed every dict-valued non-block key
# would fail three committed fields across four rows.
#
# Registered explicitly for the same reason STRATUM_BLOCKS is: the unregistered-block detector
# below is content-independent and consults both lists, so adding either kind of field is a
# deliberate edit that shows in the diff rather than something a value's shape decides.
NON_BLOCK_FIELDS = ("identifier", "vocabulary", "retrieval_mechanism_prediction")

# The unit a block's slot and its recorded ratios are anchored on. Named per block because the
# field differs by what the stratum draws: single-hop and near-miss draw one unit, action-to-parent
# draws an action and its parent and the slot hangs off the parent.
SLOT_ANCHOR_FIELD = {
    "multi_hop": None,
    "single_hop": "drawn_unit",
    "action_to_parent": "drawn_parent",
    "near_miss": "drawn_unit",
}

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


def _blocks_carrying(field: str) -> list[tuple[dict, str, dict]]:
    """(row, block name, block) for every stratum block carrying a named field.

    Selected on the field rather than on one stratum name. The superseded form of the two checks
    below read _blocks("single_hop"), a structural filter standing in for a content question: a
    later stratum shipping the same field got no coverage while the check reported a pass over
    the rows it did reach. That is the pass-by-blindness V20 names, and it is why the
    action-to-parent rows would have shipped a query_span_lexical_overlap block with no committed
    re-derivation and a designation_attempts list with no bound.
    """
    out = []
    for row in _verification():
        for name in STRATUM_BLOCKS:
            block = row.get(name)
            if block and field in block:
                out.append((row, name, block))
    return out


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

    The unregistered-block half is content-independent. An earlier form matched on the literal
    `drawn_unit` inside the value, which is a detector deciding a structural question from one
    field name: a block that happened not to carry that field passed unseen, the pass-by-blindness
    V20 names. It now consults the two registries and nothing else.
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
        assert not _unregistered_dict_fields(row), (
            f"{row['id']}: carries dict-valued top-level key(s) "
            f"{_unregistered_dict_fields(row)} registered neither as a stratum block nor as a "
            "non-block field. Add the name to STRATUM_BLOCKS or NON_BLOCK_FIELDS deliberately "
            "rather than defaulting"
        )


def _unregistered_dict_fields(row: dict) -> list[str]:
    """Dict-valued top-level keys in neither registry. One predicate, driven by the check above
    and by its companion, so what is shown capable of failing is what actually runs."""
    return sorted(k for k, v in row.items()
                  if isinstance(v, dict)
                  and k not in STRATUM_BLOCKS
                  and k not in NON_BLOCK_FIELDS)


def test_the_non_block_field_registry_matches_the_committed_file():
    """NON_BLOCK_FIELDS is a literal, so it can go stale against the file it describes.

    Asserted in the tight direction: every dict-valued non-block key the file actually holds is
    registered, and every registered name is one the file actually uses as a dict somewhere. A
    registry naming a field nobody carries would let the detector pass a name that has quietly
    changed meaning.
    """
    rows = _verification()
    dict_keys = {k for row in rows for k, v in row.items() if isinstance(v, dict)}
    held = dict_keys - set(STRATUM_BLOCKS)
    assert held == set(NON_BLOCK_FIELDS), (
        f"the file holds dict-valued non-block keys {sorted(held)} and NON_BLOCK_FIELDS names "
        f"{sorted(NON_BLOCK_FIELDS)}"
    )


def test_the_unregistered_block_detector_can_fail():
    """V20, both directions, driven through the predicate the check itself runs.

    The direction that matters most is the second: the blanket form of this detector, failing any
    dict-valued key outside STRATUM_BLOCKS, would have failed three committed adversarial fields
    on twelve row-instances. A detector that cannot admit the file it guards is not stricter, it
    is broken.
    """
    caught = {"id": "test_00", "near_miss": None, "surprise": {"anything": 1}}
    assert _unregistered_dict_fields(caught) == ["surprise"], (
        "a dict under an unregistered name was not caught"
    )

    no_drawn_unit = {"id": "test_00", "surprise": {"competitor_unit": "x"}}
    assert _unregistered_dict_fields(no_drawn_unit) == ["surprise"], (
        "the superseded form keyed on the literal 'drawn_unit' and would pass this row, which is "
        "the pass-by-blindness the content-independent form removes"
    )

    for field in NON_BLOCK_FIELDS:
        legitimate = {"id": "test_00", field: {"evidence": 1}}
        assert _unregistered_dict_fields(legitimate) == [], (
            f"{field} is a committed non-block dict field and must not be flagged"
        )
    for block in STRATUM_BLOCKS:
        legitimate = {"id": "test_00", block: {"drawn_unit": "x"}}
        assert _unregistered_dict_fields(legitimate) == [], f"{block} is a registered block"

    assert _unregistered_dict_fields({"id": "test_00", "note": "a string, not a dict"}) == []


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

    Measured over the screening record it judges: 24 rows at one attempt and 3 at two, so
    the bound is not slack against its own data by a wide margin, and a third attempt on any row
    fails here.

    Selected on designation_attempts rather than on the single_hop block, so a stratum shipping
    the same field is bound by the same rule. See _blocks_carrying.
    """
    held = _blocks_carrying("designation_attempts")
    if not held:
        pytest.skip("no committed block records designation attempts yet")
    for row, name, block in held:
        where = f"{row['id']}/{name}"
        attempts = block["designation_attempts"]
        assert 1 <= len(attempts) <= MAX_DESIGNATION_ATTEMPTS, (
            f"{where}: {len(attempts)} designation attempts, bound is "
            f"{MAX_DESIGNATION_ATTEMPTS}. A second failure rejects the pick rather than "
            "producing a third attempt"
        )
        binding = [a for a in attempts if a["outcome"] == "binding"]
        assert len(binding) == 1, (
            f"{where}: {len(binding)} attempts marked binding, expected exactly one"
        )
        assert block["binding_designation"] == {"span": binding[0]["span"],
                                                "chunk_id": binding[0]["chunk_id"]}, (
            f"{where}: binding_designation does not equal the attempt marked binding, so the "
            "row states two different spans as the one that binds"
        )


def test_recorded_query_to_span_overlap_re_derives():
    """The overlap numbers, recomputed from the committed query text and the committed span.

    This is what makes the block's reproducibility level a fact rather than a claim. Every value
    in it is a function of three committed things, the query, the binding span, and
    src/retrieve/tokenize.py:tokenize_query, so it re-derives at level 1 with no model and no
    key. The block's command names this test, which is a command a reviewer can actually run;
    naming the tool that first produced the numbers would name something they do not have.

    Measured over the 22 rows it judges: all 22 re-derive, and a control adding one token to a
    query moves containment from 0.2222 to 0.2000, so the comparison is not one that passes on
    anything.

    Selected on query_span_lexical_overlap rather than on the single_hop block, so a stratum
    shipping the same block is re-derived by the same predicate. See _blocks_carrying.
    """
    held = _blocks_carrying("query_span_lexical_overlap")
    if not held:
        pytest.skip("no committed block records a query-to-span overlap yet")
    for row, name, block in held:
        defects = _overlap_defects(row["query"], block["binding_designation"]["span"],
                                   block["query_span_lexical_overlap"])
        assert not defects, f"{row['id']}/{name}: " + "; ".join(defects)


def _overlap_defects(query: str, span: str, overlap: dict) -> list[str]:
    """Every way a recorded overlap block disagrees with its own re-derivation.

    One predicate, driven by the check above and by its companion, so what is shown capable of
    failing is what actually runs rather than a second copy that can drift.
    """
    query_tokens = set(tokenize_query(query))
    span_tokens = set(tokenize_query(span))
    shared = sorted(query_tokens & span_tokens)
    derived = {
        "query_tokens": len(query_tokens),
        "span_tokens": len(span_tokens),
        "shared": shared,
        "query_only": sorted(query_tokens - span_tokens),
        "containment": round(len(shared) / len(query_tokens), 4),
        "jaccard": round(len(shared) / len(query_tokens | span_tokens), 4),
    }
    return [f"{field} recorded {overlap[field]!r}, re-derived {value!r}"
            for field, value in derived.items() if overlap[field] != value]


def test_the_overlap_re_derivation_can_fail():
    """V20, through the predicate the check itself runs, on a row of each stratum that ships the
    block. A re-derivation that cannot reject a wrong number is not a re-derivation."""
    held = _blocks_carrying("query_span_lexical_overlap")
    if not held:
        pytest.skip("no committed block records a query-to-span overlap yet")
    seen = set()
    for row, name, block in held:
        if name in seen:
            continue
        seen.add(name)
        overlap = block["query_span_lexical_overlap"]
        query, span = row["query"], block["binding_designation"]["span"]
        assert not _overlap_defects(query, span, overlap), (
            f"{row['id']}/{name}: the honest row does not re-derive"
        )
        moved = dict(overlap, containment=round(overlap["containment"] + 0.01, 4))
        assert _overlap_defects(query, span, moved), (
            f"{row['id']}/{name}: a moved containment was not caught"
        )
        assert _overlap_defects(query, span, dict(overlap, shared=[])), (
            f"{row['id']}/{name}: an emptied shared list was not caught"
        )
        assert _overlap_defects(query + " extra", span, overlap), (
            f"{row['id']}/{name}: a query edited after the block was written was not caught"
        )
    assert len(seen) >= 2, (
        f"the block was reached in only {sorted(seen)}, so the widening past single_hop is not "
        "demonstrated on committed data"
    )


# ---------------------------------------------------------------------------------------------
# The ordering guard, and the carrier predicate.

PRODUCER = "src.goldset.relation_positions.relation_derived_carriers"


# Leaf keys that record how retrieval actually went, as opposed to how it was predicted to go.
# A closed vocabulary rather than a pattern, so adding a name is a deliberate edit visible in the
# diff. Checked anywhere in the row at any depth, not at one field path.
OUTCOME_KEYS = frozenset({
    "resolved", "resolved_branch", "outcome", "fired", "actual", "observed",
    "result_branch", "which_branch", "retrieval_outcome", "branch_that_fired",
})

# Values that assert an outcome whatever key carries them. The value vocabulary exists beside the
# key vocabulary because a detector keyed on structure alone is the pass-by-blindness V20 names,
# and this repository has paid for that three times. It is what catches an outcome written under a
# key nobody thought to enumerate.
OUTCOME_VALUES = frozenset({
    "bm25_anchored", "dense_anchored", "equal_rank",
    "hit", "miss", "first-pass hit", "first-pass miss", "recovered", "not recovered",
})

# The exemptions, by exact field path. None of these claims a retrieval outcome. Every count is
# asserted below, so an exemption cannot silently widen.
EXEMPT_LEAF_PATHS = (
    ".retrieval_mechanism_prediction.prediction",
    ".retrieval_mechanism_prediction.branches[].branch",
    ".retrieval_mechanism_prediction.branches[].condition",
)

# `outcome` is an overloaded word in this file and the overload was found by this detector rather
# than reasoned about in advance. Three stratum blocks record a DESIGNATION outcome under that
# key, .single_hop, .near_miss and .action_to_parent designation_attempts[].outcome, holding
# 'binding' or 'rejected'. Those say which span bound, not how retrieval went, and they predate
# any retrieval. Exempted by path suffix rather than by dropping `outcome` from OUTCOME_KEYS,
# because dropping it would blind the guard to an outcome written under that name anywhere else.
EXEMPT_LEAF_SUFFIXES = (".designation_attempts[].outcome",)


def _leaves(value, path=""):
    """Every (path, leaf) in a row. List indices collapse to [] so a path is stable across rows."""
    if isinstance(value, dict):
        for key, inner in value.items():
            yield from _leaves(inner, f"{path}.{key}")
    elif isinstance(value, list):
        for inner in value:
            yield from _leaves(inner, f"{path}[]")
    else:
        yield path, value


def recorded_outcomes(row: dict) -> list[tuple[str, object]]:
    """Every leaf anywhere in the row that records how retrieval actually went.

    Two independent grounds, either sufficient. A leaf whose key is an outcome key and whose value
    is not None; or a leaf whose value is an outcome value, whatever its key. The exemptions are
    subtracted by exact path rather than by key, so a `prediction` key appearing somewhere new is
    still judged.
    """
    found = []
    for path, leaf in _leaves(row):
        if path in EXEMPT_LEAF_PATHS or path.endswith(EXEMPT_LEAF_SUFFIXES):
            continue
        key = path.rsplit(".", 1)[-1].removesuffix("[]")
        if key in OUTCOME_KEYS and leaf is not None:
            found.append((path, leaf))
        elif isinstance(leaf, str) and leaf in OUTCOME_VALUES:
            found.append((path, leaf))
    return found


def test_no_row_records_the_outcome_of_a_retrieval_prediction():
    """A prediction may ship before retrieval; its outcome may not. Anywhere in the row.

    PREREGISTRATION.md orders the queries and their embeddings before retrieval runs on them, so
    a field holding which branch of a pre-registered prediction actually fired could only be
    filled after that ordering is spent. The branch table is pre-registration and belongs here;
    the branch that fired is a result and does not. Prediction scoring lives in the retrieval
    results artifact and in the session log entry.

    UNCONDITIONAL BY DECISION, and it never consults the retrieval gate. Where an outcome lives is
    a question about this artifact, not a question about when retrieval ran, so the guard reads
    the same before and after the results commit. tests/test_retrieval_ordering_gate.py asserts
    this module never imports the gate, so that cannot be quietly reversed.

    WIDENED, and this is why. The superseded accessor read exactly one field path,
    retrieval_mechanism_prediction.resolved. Measured through that accessor, five shapes that
    record which branch fired returned nothing and passed: a differently named sibling, a `fired`
    flag nested inside the row's own `branches` table, a value on a stratum block, a new scalar
    top-level key, and the prediction block replaced by a list of outcome dicts. The third is the
    sharp one: the branch table sits on the same row, one level below where the guard looked. Each
    of the five is now a mutation companion below.
    """
    for row in _verification():
        found = recorded_outcomes(row)
        assert not found, (
            f"{row['id']}: an outcome is recorded at "
            + ", ".join(f"{path} = {leaf!r}" for path, leaf in found)
            + ". That is the outcome of a prediction, and outcomes belong in the retrieval "
            "results artifact and the log entry, not in this pre-registration record"
        )


def test_the_post_retrieval_guard_can_fail():
    """V20, through the same accessor the check runs, on the guarded path."""
    fabricated = {"id": "test_00",
                  "retrieval_mechanism_prediction": {"prediction": "first-pass miss",
                                                     "resolved": "hit"}}
    found = recorded_outcomes(fabricated)
    assert found, "the accessor did not reach a resolved value"
    assert any(p.endswith(".resolved") for p, _ in found)
    nulled = {"id": "test_00",
              "retrieval_mechanism_prediction": {"prediction": "x", "resolved": None}}
    assert recorded_outcomes(nulled) == []
    absent = {"id": "test_00", "retrieval_mechanism_prediction": {"prediction": "x"}}
    assert recorded_outcomes(absent) == []
    assert recorded_outcomes({"id": "test_00", "retrieval_mechanism_prediction": None}) == []


def test_the_guard_catches_a_renamed_sibling():
    """Shape one of five measured passing the superseded accessor."""
    row = {"id": "test_00",
           "retrieval_mechanism_prediction": {"prediction": "first-pass miss",
                                              "resolved_branch": "bm25_anchored"}}
    found = recorded_outcomes(row)
    assert found, "an outcome under a renamed sibling was not seen"
    assert found[0][1] == "bm25_anchored"


def test_the_guard_catches_a_flag_inside_the_branch_table():
    """Shape two, the sharp one: the branch table is on the row the guard already reads."""
    row = {"id": "test_00",
           "retrieval_mechanism_prediction": {
               "prediction": "first-pass miss",
               "branches": [{"branch": "bm25_anchored", "condition": "x", "fired": True},
                            {"branch": "dense_anchored", "condition": "y", "fired": False}]}}
    found = recorded_outcomes(row)
    paths = {p for p, _ in found}
    assert ".retrieval_mechanism_prediction.branches[].fired" in paths, (
        f"a fired flag inside the branch table was not seen; found {sorted(paths)}"
    )
    assert ".retrieval_mechanism_prediction.branches[].branch" not in paths, (
        "the branch table's own names were flagged; naming a branch is not claiming it fired"
    )


def test_the_guard_catches_an_outcome_on_a_stratum_block():
    """Shape three: a stratum block is a dict like any other and the walk reaches it."""
    row = {"id": "test_00",
           "retrieval_mechanism_prediction": {"prediction": "first-pass miss"},
           "action_to_parent": {"drawn_parent": "x:y", "resolved": "dense_anchored"}}
    found = recorded_outcomes(row)
    assert (".action_to_parent.resolved", "dense_anchored") in found


def test_the_guard_catches_a_new_top_level_key():
    """Shape four. A scalar top-level key passes every other check in this file."""
    row = {"id": "test_00",
           "retrieval_mechanism_prediction": {"prediction": "first-pass miss"},
           "retrieval_outcome": "bm25_anchored"}
    found = recorded_outcomes(row)
    assert (".retrieval_outcome", "bm25_anchored") in found


def test_the_guard_catches_a_list_valued_prediction_block():
    """Shape five. The superseded accessor required a dict and returned nothing for a list."""
    row = {"id": "test_00",
           "retrieval_mechanism_prediction": [{"resolved": "hit"}]}
    found = recorded_outcomes(row)
    assert found, "a list-valued prediction block was not walked"
    assert found[0][1] == "hit"


def test_the_prediction_exemption_reaches_exactly_the_committed_predictions():
    """The exemption is bounded by count, so it cannot silently widen.

    Measured rather than assumed, and the first measurement contradicted the guess behind it.
    Twelve rows carry a resolved key, but only FOUR carry a prediction string that is in the
    outcome vocabulary, the action-to-parent rows at 'first-pass miss'. The eight near-miss rows
    state their prediction as a sentence, 'first-pass discrimination failure: a near-identical
    neighbour of the anchor surfaces and the anchor's own block is absent from the fused top 10',
    which no vocabulary entry matches.

    That is a stated limit of the value clause and not a hole to paper over. A vocabulary of exact
    strings cannot catch an outcome phrased as a sentence, so the value clause is a supplement and
    the key clause is the primary net. An outcome recorded in prose under a key nobody enumerated
    would pass, and nothing in this file claims otherwise.
    """
    rows = _verification()
    with_prediction = [
        r for r in rows
        if isinstance(r.get("retrieval_mechanism_prediction"), dict)
        and r["retrieval_mechanism_prediction"].get("prediction") in OUTCOME_VALUES
    ]
    assert len(with_prediction) == 4, (
        f"{len(with_prediction)} rows carry a prediction in the outcome vocabulary, not 4"
    )
    assert [r["id"] for r in with_prediction] == ["test_39", "test_40", "test_41", "test_42"]
    for row in with_prediction:
        assert recorded_outcomes(row) == [], f"{row['id']} was flagged despite the exemption"

    resolved_bearing = [
        r for r in rows
        if isinstance(r.get("retrieval_mechanism_prediction"), dict)
        and "resolved" in r["retrieval_mechanism_prediction"]
    ]
    assert len(resolved_bearing) == 12
    prose = [r for r in resolved_bearing if r not in with_prediction]
    assert len(prose) == 8, f"{len(prose)} rows state their prediction as prose, not 8"
    for row in prose:
        assert recorded_outcomes(row) == [], f"{row['id']} was flagged"


def test_the_designation_outcome_exemption_is_bounded():
    """`outcome` is overloaded, and the exemption for the other meaning is counted.

    Three stratum blocks record a designation outcome under that key. Measured: 20 on
    single_hop, 8 on near_miss, 4 on action_to_parent, 32 leaves, holding 'binding' on 30 and
    'rejected' on 2. None is a retrieval outcome and all predate any retrieval. A fourth block
    gaining the field, or one of these gaining a row, moves this number and has to be looked at.
    """
    rows = _verification()
    hits = [(path, leaf) for row in rows for path, leaf in _leaves(row)
            if path.endswith(EXEMPT_LEAF_SUFFIXES)]
    assert len(hits) == 32, f"the designation exemption matches {len(hits)} leaves, not 32"
    assert {leaf for _, leaf in hits} == {"binding", "rejected"}, (
        f"designation outcomes now hold {sorted({leaf for _, leaf in hits})}"
    )
    blocks = sorted({path.split(".")[1] for path, _ in hits})
    assert blocks == ["action_to_parent", "near_miss", "single_hop"], (
        f"designation_attempts now appears under {blocks}"
    )


def test_the_designation_exemption_does_not_blind_the_guard_elsewhere():
    """V20 on the exemption itself: it is scoped to the path, not to the word.

    An `outcome` key anywhere other than a designation attempt is still caught, which is the
    reason the exemption is a path suffix rather than a removal from OUTCOME_KEYS.
    """
    row = {"id": "test_00",
           "single_hop": {"designation_attempts": [{"outcome": "binding"}],
                          "outcome": "bm25_anchored"}}
    found = recorded_outcomes(row)
    paths = {p for p, _ in found}
    assert ".single_hop.outcome" in paths, f"the guard was blinded; found {sorted(paths)}"
    assert ".single_hop.designation_attempts[].outcome" not in paths


def test_the_branch_table_exemption_reaches_exactly_the_committed_branches():
    """The other exemption, bounded the same way.

    One row carries a branch table, test_41's three-branch note, so the two exempt branch paths
    match three leaves each. A fourth branch, or a table appearing on a second row, moves this.
    """
    rows = _verification()
    branches = [
        (path, leaf)
        for row in rows
        for path, leaf in _leaves(row)
        if path in (".retrieval_mechanism_prediction.branches[].branch",
                    ".retrieval_mechanism_prediction.branches[].condition")
    ]
    assert len(branches) == 6, (
        f"the branch exemptions match {len(branches)} leaves, not the 6 on test_41's three "
        "branches"
    )
    carriers = [r["id"] for r in rows
                if isinstance(r.get("retrieval_mechanism_prediction"), dict)
                and r["retrieval_mechanism_prediction"].get("branches")]
    assert carriers == ["test_41"], f"branch tables now sit on {carriers}"


def _slot_members(block: str):
    """(row, anchor, member) for every slot member of one block, across the file."""
    field = SLOT_ANCHOR_FIELD[block]
    out = []
    for row, held in _blocks(block):
        if field is None or "slot" not in held:
            continue
        for member in held["slot"].get("members") or []:
            out.append((row, held[field], member))
    return out


def _relation_admits(member: dict) -> list[str]:
    """The relations recording this member as a carrier, read off the enumerated verdicts.

    Asserted on the verdict constants rather than on the free-text contributing_relation field.
    The committed rows write that field as prose, "individual verification at pass one" against
    "committed duplication map", and a substring match on prose is the compare-structure-where-
    the-claim-is-content failure this repository has paid for three times. The mechanical fact is
    already on every member in committed_relation_positions, whose verdicts come from the SILENT,
    INCLUDES and EXCLUDES constants in src/goldset/relation_positions.py.
    """
    positions = member.get("committed_relation_positions") or {}
    return sorted(name for name, sentence in positions.items()
                  if sentence.split(":", 1)[0] == INCLUDES)


def test_a_slot_member_admitted_by_a_relation_is_cross_document():
    """Part one of the carrier ruling, asserted from the row.

    PREREGISTRATION.md scopes the any-carrier clause in its own words to a statement duplicated
    verbatim ACROSS DOCUMENTS, so a committed relation cannot admit a unit sharing the anchor's
    document. Individual verification is the other route and is unrestricted by document, which
    is how the two committed same-document members entered.

    Live in both directions on committed data today, not vacuous, and both directions are
    asserted to have fired so a reader returning nothing cannot pass this.
    """
    checked, admitted, same_document = 0, 0, 0
    for block in STRATUM_BLOCKS:
        for row, anchor, member in _slot_members(block):
            unit = member["unit_id"]
            if unit == anchor:
                continue
            checked += 1
            admits = _relation_admits(member)
            where = f"{row['id']}/{block}/{unit}"
            if admits:
                admitted += 1
                assert document_of(unit) != document_of(anchor), (
                    f"{where}: admitted by {admits} while sharing the anchor's document. A "
                    "relation may admit only across documents"
                )
            if document_of(unit) == document_of(anchor):
                same_document += 1
                assert not admits, (
                    f"{where}: a same-document slot member is recorded as admitted by {admits}. "
                    "A relation may admit only across documents; a same-document member enters "
                    "by individual verification alone"
                )
    assert checked, "no slot member was reached, so this assertion ran on nothing"
    assert admitted, (
        "no slot member anywhere reads INCLUDES, so the cross-document half of this assertion "
        "never fired and a reader that returned nothing would pass it"
    )
    assert same_document, (
        "no same-document slot member exists, so the individual-verification half never fired. "
        "Measured at this commit: two, eu_ai_act:rct_179 on test_22 and eu_ai_act:art_3 on "
        "test_25, both SILENT on both relations"
    )


def test_relation_derived_carriers_agrees_with_every_committed_slot_member():
    """The row's recorded relation position, re-derived from the relations themselves.

    Two implementations rather than one: the row carries what relation_positions said at
    authoring, and this re-runs the shipped predicate now. A row edited by hand, or a relation
    that moved underneath it, fails here.
    """
    groups, duplication_map = load_relations()
    checked = 0
    for block in STRATUM_BLOCKS:
        for row, anchor, member in _slot_members(block):
            unit = member["unit_id"]
            if unit == anchor:
                continue
            checked += 1
            derived = relation_derived_carriers(anchor, groups, duplication_map)
            recorded = _relation_admits(member)
            where = f"{row['id']}/{block}/{unit}"
            if recorded:
                assert unit in derived, (
                    f"{where}: the row records admission by {recorded} and "
                    f"relation_derived_carriers does not return it. Derived: {sorted(derived)}"
                )
                assert derived[unit] == recorded, (
                    f"{where}: the row records {recorded} and the predicate derives "
                    f"{derived[unit]}"
                )
            else:
                assert unit not in derived, (
                    f"{where}: the row records no relation admitting this member and "
                    f"relation_derived_carriers returns {derived.get(unit)}"
                )
    assert checked, "no slot member was reached, so this assertion ran on nothing"


def _near_miss_defects(block: dict, groups: list, duplication_map: list) -> list[str]:
    """Every way a near-miss block violates the carrier ruling, as a list of messages.

    One predicate, driven by the check below and by its companion, so what is shown capable of
    failing is what actually runs rather than a second copy that can drift.
    """
    defects: list[str] = []
    anchor, competitor = block["drawn_unit"], block["competitor_unit"]
    flag = block["competitor_is_a_carrier_of_gold"]
    derived = relation_derived_carriers(anchor, groups, duplication_map)
    arm = flag["mechanical_arm"]

    if arm["competitor_in_relation_derived_carriers"] != (competitor in derived):
        defects.append(
            f"mechanical arm records {arm['competitor_in_relation_derived_carriers']} and the "
            f"predicate derives {competitor in derived}")
    if arm["relations"] != derived.get(competitor, []):
        defects.append(f"mechanical arm records relations {arm['relations']} and the predicate "
                       f"derives {derived.get(competitor, [])}")
    if arm["producer"] != PRODUCER:
        defects.append(f"mechanical arm names producer {arm['producer']!r}, expected {PRODUCER!r}")

    expected = bool(competitor in derived) or flag["individual_verification"] == "carrier"
    if flag["value"] != expected:
        defects.append(
            f"value recorded {flag['value']}, re-derived {expected} from the mechanical arm and "
            f"the recorded individual verification {flag['individual_verification']!r}")
    if block.get("verdict") == "accepted" and flag["value"]:
        defects.append(
            "accepted with a competitor that carries its gold, so no discrimination failure on "
            "this row is observable by the metrics")
    return defects


def test_near_miss_blocks_satisfy_the_carrier_ruling():
    """The near-miss admissibility screen, through one predicate.

    Vacuous until near-miss rows land and binding from that commit, the matcher-scoping precedent.
    The mechanical arm is relation_derived_carriers; a competitor that individual verification
    verdicts a carrier also sets the flag, which only ever removes a pick.

    Measured before any pick was screened: 54 of the 71 near_duplicate draw-order pairs have a
    competitor that is a carrier of the gold, so this rejects rather than decorates.
    """
    pairs = _blocks("near_miss")
    if not pairs:
        pytest.skip("no committed near_miss rows yet; this turns on at that commit")
    groups, duplication_map = load_relations()
    for row, block in pairs:
        defects = _near_miss_defects(block, groups, duplication_map)
        assert not defects, f"{row['id']}: " + "; ".join(defects)


def test_the_near_miss_carrier_checks_can_fail():
    """V20, on real corpus units rather than invented ids, driving the predicate the check runs.

    nist_ai_600_1:sub_MAP_2.2 against nist_ai_100_1:sub_MAP_2.2 is draw index 0 of the committed
    near_duplicate order and is one of the 54 whose competitor carries its gold, so it is the
    case this screen exists to reject. nist_playbook:sub_MAP_3.4.ai_transparency_resources
    against nist_playbook:sub_MAP_1.5.ai_transparency_resources is draw index 3 and is clean on
    the same screen, so both verdicts are reachable.
    """
    groups, duplication_map = load_relations()
    colliding = "nist_ai_600_1:sub_MAP_2.2"
    competitor = "nist_ai_100_1:sub_MAP_2.2"
    derived = relation_derived_carriers(colliding, groups, duplication_map)
    assert competitor in derived, (
        "the corpus case this control is built on no longer collides, so the control proves "
        "nothing; re-derive it before trusting the screen")

    honest = {
        "drawn_unit": colliding, "competitor_unit": competitor, "verdict": "rejected",
        "competitor_is_a_carrier_of_gold": {
            "value": True, "individual_verification": "carrier",
            "mechanical_arm": {"competitor_in_relation_derived_carriers": True,
                               "relations": derived[competitor], "producer": PRODUCER}}}
    assert _near_miss_defects(honest, groups, duplication_map) == [], (
        "the companion's baseline block must itself pass")

    accepted = {**honest, "verdict": "accepted"}
    assert _near_miss_defects(accepted, groups, duplication_map), (
        "a pick accepted with a carrier competitor was not caught, which is the whole screen")

    lied = json.loads(json.dumps(honest))
    lied["competitor_is_a_carrier_of_gold"]["value"] = False
    lied["competitor_is_a_carrier_of_gold"]["individual_verification"] = "non-carrier"
    lied["competitor_is_a_carrier_of_gold"]["mechanical_arm"][
        "competitor_in_relation_derived_carriers"] = False
    lied["competitor_is_a_carrier_of_gold"]["mechanical_arm"]["relations"] = []
    assert _near_miss_defects(lied, groups, duplication_map), (
        "a block asserting its competitor is not a carrier when the relations say otherwise was "
        "not caught")

    wrong_producer = json.loads(json.dumps(honest))
    wrong_producer["competitor_is_a_carrier_of_gold"]["mechanical_arm"]["producer"] = "somewhere"
    assert _near_miss_defects(wrong_producer, groups, duplication_map)

    clean_anchor = "nist_playbook:sub_MAP_3.4.ai_transparency_resources"
    clean_competitor = "nist_playbook:sub_MAP_1.5.ai_transparency_resources"
    clean_derived = relation_derived_carriers(clean_anchor, groups, duplication_map)
    assert clean_competitor not in clean_derived
    clean = {
        "drawn_unit": clean_anchor, "competitor_unit": clean_competitor, "verdict": "accepted",
        "competitor_is_a_carrier_of_gold": {
            "value": False, "individual_verification": "non-carrier",
            "mechanical_arm": {"competitor_in_relation_derived_carriers": False,
                               "relations": [], "producer": PRODUCER}}}
    assert _near_miss_defects(clean, groups, duplication_map) == [], (
        "an admissible near-miss pick must pass, or the screen bars the rows it was written to "
        "admit")


# ---------------------------------------------------------------------------------------------
# The command fields. A block promising a re-derivation names the command that runs it, and a
# command naming a node that does not exist is a promise a reviewer cannot collect on.

REJECTIONS = EVAL / "test_frame_rejections.jsonl"

# Population, named as artifact, field and accepted values rather than by effect: every value of
# a field named `command`, in these two artifacts, whose value invokes pytest. Measured over the
# committed tree at this commit: 186 command fields in total, 139 in the verification file and 47
# in the rejection log; 22 invoke pytest and 164 do not (166 `python -c` and 2 `grep` before this
# commit's four rows landed). The non-pytest shapes are out of scope here because there is no
# collectible node to resolve, not because they are trusted.
COMMAND_ARTIFACTS = (VERIFICATION, REJECTIONS)
PYTEST_INVOCATION = "-m pytest"


def _command_values(obj, path=""):
    """Every (path, value) under a key named `command`, at any depth."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "command" and isinstance(value, str):
                yield f"{path}.{key}", value
            else:
                yield from _command_values(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _command_values(value, f"{path}[{index}]")


def _pytest_node_ids() -> list[tuple[str, str]]:
    """(where, node id) for every pytest-invoking command field across both artifacts."""
    out = []
    for artifact in COMMAND_ARTIFACTS:
        if not artifact.exists():
            continue
        for line in artifact.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for path, value in _command_values(row):
                if PYTEST_INVOCATION in value:
                    node = next((tok for tok in value.split() if "::" in tok), None)
                    out.append((f"{artifact.name}:{row.get('id') or row.get('rejected')}{path}",
                                node if node is not None else value))
    return out


def _node_defects(node_id: str) -> list[str]:
    """Every way a pytest node id fails to resolve, read from the source rather than collected.

    Parsed with ast rather than imported or collected, so this stays a level-1 check with no
    import side effects and no dependence on pytest's collection order. What it catches is the
    defect it was written for: a node id whose function is defined in some other file, which
    collects zero tests and reports 'no tests ran' rather than failing.
    """
    if "::" not in node_id:
        return [f"{node_id!r} names no pytest node"]
    path, _, name = node_id.partition("::")
    target = REPO_ROOT / path
    if not target.exists():
        return [f"{node_id}: {path} does not exist"]
    tree = ast.parse(target.read_text(encoding="utf-8"))
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if name not in defined:
        return [f"{node_id}: {path} defines no top-level function {name!r}"]
    return []


def test_every_pytest_command_field_names_a_collectible_node():
    """A command field names something a reviewer can actually run.

    Paid for by 18 committed rows whose overlap block named
    tests/test_single_hop_row_numbers.py::test_recorded_query_to_span_overlap_re_derives, a node
    that collects zero tests because the function is defined in this file and in no other. The
    block's whole claim is that its numbers re-derive; a reviewer following the citation got 'no
    tests ran'. Corrected at this commit with the reason on every corrected block.
    """
    nodes = _pytest_node_ids()
    assert nodes, (
        "no command field invokes pytest, so this check ran on nothing. It was written against a "
        "population measured at 22 across the two artifacts"
    )
    defects = [d for _, node in nodes for d in _node_defects(node)]
    assert not defects, "; ".join(defects)


def test_the_command_resolution_check_can_fail():
    """V20, through the same predicate, driven against the exact defect this commit corrected."""
    dangling = ("tests/test_single_hop_row_numbers.py"
                "::test_recorded_query_to_span_overlap_re_derives")
    assert _node_defects(dangling), (
        "the superseded citation resolved, so this check could not have caught the defect it "
        "exists for"
    )
    good = "tests/test_test_query_verification.py::test_recorded_query_to_span_overlap_re_derives"
    assert _node_defects(good) == [], f"the corrected citation does not resolve: {good}"
    assert _node_defects("tests/does_not_exist.py::test_x"), "a missing file was not caught"
    assert _node_defects("not a node id"), "a value with no node id was not caught"


# ---------------------------------------------------------------------------------------------
# The ratio path. Every committed ratio and every committed opcode set is built through one
# constructor with autojunk disabled, and this pins both halves of that.

RATIO_PATH_MODULES = (
    "src/goldset/attributability.py",
    "src/goldset/check_committed_duplication_scans.py",
    "tests/test_single_hop_row_numbers.py",
    "tests/test_attributability.py",
    "tests/test_test_query_verification.py",
)


def _direct_constructions() -> list[tuple[str, str]]:
    """(module, enclosing function) for every direct difflib.SequenceMatcher construction."""
    found = []
    for rel in RATIO_PATH_MODULES:
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == "SequenceMatcher"):
                    found.append((rel, node.name))
    return sorted(set(found))


def test_the_ratio_path_builds_every_matcher_through_one_constructor():
    """No module in the ratio path constructs difflib.SequenceMatcher directly, bar the
    registered controls.

    Paid for by a length-triggered artifact: difflib junks characters appearing in more than one
    percent of the second sequence once it reaches 200 elements, so a similarity score depended
    on the length of one side. Six committed figures moved when it was disabled. A second call
    site reintroducing the default would move them back silently, so the construction point is
    pinned here rather than left to review.

    The exemptions are read from the file rather than pinned to a literal, because the two that
    exist are inside tests whose whole subject is a superseded or degenerate comparison, and a
    literal list would go stale against a renamed test. What is asserted is the property that
    matters: every direct construction sits in a function this file can name and account for.
    """
    found = _direct_constructions()
    accounted = {
        # The one constructor. Every other site routes through it, so this is the site the rule
        # exists to concentrate rather than a breach of it.
        ("src/goldset/attributability.py", "ratio_matcher"),
        # Two controls, both measured unexposed: CASE_A_LEFT is 123 characters and CASE_A_RIGHT
        # 109 against difflib's 200-element threshold on the second sequence, and the "1." pair is
        # two. The first reproduces a superseded normalisation to show the hyphen fold is
        # load-bearing; the second exists to score 1.0. Routing either through the corrected
        # constructor would change what the control demonstrates for no measured gain.
        ("tests/test_attributability.py",
         "test_case_a_needs_the_hyphen_fold_and_would_miss_without_it"),
        ("tests/test_attributability.py",
         "test_bare_paragraph_numbers_are_not_comparable_segments"),
        # The regression below, which must construct the default to pin the artifact it removes.
        ("tests/test_test_query_verification.py",
         "test_autojunk_is_disabled_and_the_artifact_it_removes_is_pinned"),
    }
    unexpected = [c for c in found if c not in accounted]
    assert not unexpected, (
        f"direct difflib.SequenceMatcher construction outside the accounted set: {unexpected}. "
        "Build it through src.goldset.attributability.ratio_matcher, or account for the call here "
        "with its measured exposure"
    )


def test_the_ratio_path_guard_can_fail():
    """V20. The detector must find the constructions that do exist, or it would pass a module
    that reintroduced the default."""
    found = _direct_constructions()
    assert found, (
        "no direct construction was found anywhere, so this detector proves nothing. The two "
        "controls in tests/test_attributability.py are expected to be found"
    )
    assert all(rel in RATIO_PATH_MODULES for rel, _ in found)


def test_autojunk_is_disabled_and_the_artifact_it_removes_is_pinned():
    """The observed defect, kept as a regression so reversing the fix costs a failing test.

    nist_playbook:sub_MANAGE_4.3.ai_transparency_resources against
    sub_MANAGE_4.2.ai_transparency_resources: a 133-character sequence against a 209-character one
    that is a near prefix of it. difflib's default junks sixteen characters and returns 0.2865;
    the corrected constructor returns 0.7719. That gap is the whole reason the correction exists.
    """
    import difflib

    from src.goldset.attributability import Corpus, ratio_matcher
    from src.ingest.normalize import normalise_for_comparison

    corpus = Corpus.load()
    a = normalise_for_comparison(
        corpus.unit_text["nist_playbook:sub_MANAGE_4.3.ai_transparency_resources"])
    b = normalise_for_comparison(
        corpus.unit_text["nist_playbook:sub_MANAGE_4.2.ai_transparency_resources"])
    assert (len(a), len(b)) == (133, 209), (
        f"the pinned pair changed shape: {len(a)} against {len(b)}. The 200-element threshold on "
        "the second sequence is what makes this case fire"
    )
    assert round(ratio_matcher(a, b).ratio(), 4) == 0.7719, "the corrected value moved"
    assert round(difflib.SequenceMatcher(None, a, b).ratio(), 4) == 0.2865, (
        "difflib's default no longer produces the artifact this correction removed, so the "
        "regression pins nothing and the reason for the fix needs re-measuring"
    )
