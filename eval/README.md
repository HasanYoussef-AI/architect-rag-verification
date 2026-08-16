# Evaluation queries

## Firewall

Development queries are never scored and never reported in results. They exist only
to catch structural breakage in the retriever. Because every retrieval parameter is
locked and untuned, and was fixed before any query set existed, the development set
has no tuning role. Its single job is to fail loudly if tokenisation, scoring,
fusion, quantisation, or the embeddings break.

The 40-unit development pool in `dev_unit_pool.json` is reserved and committed before
any development query is written. Development queries draw their expected units only
from that pool. The pre-registered test set is filtered against a 50-unit closure: the
40 pool units plus the 10 units carrying a statement verbatim-identical to a pool unit.
The closure exists because a gold slot is satisfied by any unit carrying its statement,
so excluding only the pool unit would leave a slot that either admits a pool unit into
gold or scores a retrieval hit on identical text as a miss. A disjointness assertion
requires that no test gold unit falls in that closure.

The one exception is the out-of-corpus query, which has no gold unit by definition
and may reference material outside the pool; it consumes no pool budget and is
marked as such in `dev_queries.jsonl`. The pre-registered test set lives in
`test_queries.jsonl`, committed and timestamped before any generation run and
immutable once results exist. It is built in batches, one stratum at a time, and
its composition is asserted against `test_frame.json` rather than against a
hardcoded count, so each batch is checked exactly without a number being edited
by hand.

## Discipline

Development queries are authored from unit text and fixed before any retrieval
result is recorded. The query file and its committed embeddings land in one commit;
the retrieval results land in a later commit. What git proves is the narrow,
load-bearing claim: the queries were frozen before any result existed, so no query
could have been edited to match what retrieval returned. It does not prove retrieval
was never run while a query was being drafted, and this file does not claim that. No
query is revised because it retrieved badly. A miss is a finding and stays in the set.

## Not a quality metric

Development results are never reported as a retrieval quality metric. The parameters
are locked and untuned, the queries are informally golded, the sample is twelve, and
the set exists to detect structural breakage. The only quality numbers this
repository produces come from the sealed, pre-registered test set scored by the
deterministic grader. This guard matters here precisely because the development hit
rate looks good.

What the set did and did not show. The three identifier queries hitting at rank one
confirms the identifier-aware tokenisation works end to end on real query text; that
is a confirmation, not a hard test. The one miss, the near-miss `dev_11`, shows the
retriever cannot discriminate a subcategory's AI Transparency Resources block from
its near-duplicates, and is kept as a finding.

## Tests that require the pinned model

Most tests run offline against committed artifacts and need no model. The exceptions are in
`tests/test_query_embeddings_provenance.py`, which registers every committed query set and
runs three checks over each. `test_query_file_has_its_embedding_array` is model-free and runs
everywhere; it pins row count, dtype and L2 norm, and it fails rather than skips when a query
file is committed without its embedding array. `test_regenerated_rankings_match_committed_results`
and `test_committed_array_reproduces_regenerated_rankings` regenerate the embeddings through the
ONNX model and compare rankings, so they need the pinned `bge-base-en-v1.5` revision. That path
asserts the model's sha256 before use, and skips when the model is not already cached, using
`local_files_only` so it never triggers a network download.

Both of those checks call `retriever.search`, so both execute retrieval against the query set.
`PREREGISTRATION.md` commits a query set and its embeddings before retrieval runs on it, so
both are gated shut for any set whose retrieval results are not committed yet, and both open at
the commit that adds them. The gate is derived from the absence of a results file rather than
from a flag, so it cannot be left closed or forced open by accident. It is an ordering
constraint and not a data dependency: the provenance check needs no results file to compute
anything.

Read the skips by name, not by count: the count moves as query sets are registered. Two skips
naming the test set are the ordering gate and are expected until retrieval runs on the sealed
fifty. A skip naming `test_committed_array_reproduces_regenerated_rankings` for a set whose gate
is open means query-embedding provenance was not verified in that run, and is not a pass.
Alignment is pinned by that provenance check, not by the shape check: a row-shuffled array has
the same shape and the same norms. Nothing else in the suite depends on the model.

## Files

- `dev_queries.jsonl`: twelve development queries, one per row, each with `split`
  set to `development`, a `type`, informal `expected_units`, and a `note`.
- `dev_query_embeddings.npy`: their embeddings, float32, aligned row for row with
  `dev_queries.jsonl`, generated on the same `normalise_for_comparison` plus ONNX
  path as the corpus embeddings.
- `dev_unit_pool.json`: the reserved development unit pool.
- `test_queries.jsonl`: the sealed, pre-registered test queries, one per row, each with
  `split` set to `test`, a `type` naming its stratum, a `subtype`, `gold_slots`,
  `expected_units`, and a `note` stating what correct behaviour is.
- `test_query_embeddings.npy`: their embeddings, float32, regenerated wholesale from the
  current query file at every batch commit rather than stitched from partial arrays, so row
  alignment is a property of the commit in hand.
- `test_query_verification.jsonl`: one row per test query, carrying each absence claim with
  its command, target, predicate, result and shape-matched control, the identifier assertions,
  and the bounds on any target that cannot discriminate. Each stratum adds its own nested block,
  null on every row outside it, so the file holds one key set across every row rather than a key
  set that varies by stratum. `tests/test_test_query_verification.py` asserts that key set, the
  one-for-one alignment with `test_queries.jsonl` by id, in order, and with matching query text,
  and the per-stratum properties the blocks carry.
- `test_query_rejections.jsonl`: the adversarial stratum's authoring scan. Each row records an
  identifier considered and not used, with the class rule it was scanned under, its ordinal in
  that scan, and the evidence for the decision. The adversarial stratum has no draw order in the
  frame, so these rows are not draw-order rejections and no selected set reconstructs from them.
- `pass_one_designations.jsonl`: what pass-one screening fixed for each accepted pick of the
  action-to-parent and near-miss strata, committed at the boundary between pass one and pass two
  and before any query text for those strata existed. Twelve rows, one key set, ordered by
  `id_predicted`.

  It exists for the ordering. The commit that places it holds no query text, so a later commit
  carrying query text postdates it, and `tests/test_pass_one_designations.py` then asserts that
  the binding designation, the question class and its fixed-at marker on each authored row are
  the ones committed here, byte for byte. Before this file the evidence that a class and a
  designation predated their query was file modification times in an untracked working tree; it
  is now ordering in git, which is what a reviewer holding the repository can check.

  `id_predicted` is a prediction, not a fact. Ids are assigned in authoring order and an
  authoring rejection at pass two shifts every id after it, which happened four times in the
  single-hop stratum. A row's stable identity is `stratum`, `source` and `draw_entry`; the id is
  asserted separately so a shifted id reports as a contradicted prediction rather than as a lost
  pick, and the contingency is that the rejection appends to the draw-order log, the replacement
  is screened to the full standard after a reviewed boundary, and its designation and class
  append here in their own correction commit before its query is authored.

  The key set is a whitelist pinned as a literal in the test, which is what keeps the file to its
  purpose: no query text, no span beyond the one designation screening fixed, no prediction
  content, no verdicts, arms or slots. Those belong on the verification and rejection rows. A
  separate check compares every value against the committed query set in both directions, because
  a whitelist bars an added field and cannot bar a query spelled as a class.

  One property of the near-miss half is worth stating here rather than leaving to be rediscovered.
  All eight near-miss rows record an empty `anchor_runs_absent_from_competitor` in their
  verification block: the anchor says nothing its designated competitor does not also say. Text
  cannot discriminate anywhere on that stratum. Every one of those units opens with the generic
  heading `AI Transparency Resources` and names no subcategory in its text, so the subcategory
  identity lives in the unit id and in `unit_label` rather than in the span. That is the recorded
  foundation under the scoping rule that decides which screen applies: where the anchor and the
  competitor carry different subcategory identifiers the differential check is evidence and never
  a gate, and where they carry the same identifier it is a rejection route.

- `test_frame_rejections.jsonl`: draw-order rejections for the four drawing strata.
  `tests/test_test_frame.py` reconstructs each stratum's selected set from the committed draw
  order plus these rows alone. The fields:

  - `stratum` and `source` together index the frame's draw order.
  - `rejected` carries the rejected candidate verbatim, so it compares equal to a draw-order
    entry. It is a pair for a source whose draw order holds pairs and a bare unit id for a source
    whose draw order holds bare unit ids.
  - `draw_index` is that candidate's position in its source's draw order.
  - `reason_code` is from the closed vocabulary its stratum fixed before its first pick was
    screened. The vocabularies differ by stratum because the rejection mechanisms do: an edge
    stratum can fail on the relation between two units, a one-endpoint stratum cannot.
  - `reason` is the prose reason, and it is the field a reviewer reads. It is drawn from
    whichever field of the screening record actually carried the rejection rather than being
    summarised for this field, so `reason_source` names that field. The source differs by the
    stage at which the pick fell: a rejection at screening is carried by the self-containedness
    arm that has no committed method, and a rejection at authoring by the sufficiency result.
  - `reason_source_note` is sparse and appears only where the field named by `reason_source` is
    not the one that would normally carry the reason, stating why. Its one occurrence records a
    row that reached authoring in an earlier pass, whose sufficiency result was recorded there
    and not in the screening record this row is built from; the reason is taken from the
    instrument that carried the rejection and the absent block is disclosed rather than
    reconstructed.
  - `selected_instead` is present and null on every row. The walk is a forward pass that stops
    once a source has its allocation, so on any source carrying more than one rejection every
    rejection resolves to the same marginal entry and none of them individually caused it to be
    selected. A per-row value would invent a distinction the walk does not support. Where a
    source carries exactly one rejection the marginal entry is individually determinate, and the
    null there is the stratum-wide convention rather than a derivation; a row in that position
    says so in its `reason` so the two cases are distinguishable on the page.

  Two fields are sparse, and sparseness means different things for each. `ratio_supersession` is
  present only where a measurement published on that row has been retracted and replaced, naming
  the superseded value, the value replacing it, and the reason the two do not reconcile, so a
  retraction is legible from the row itself rather than only from the history. It is absent
  wherever nothing has been superseded, and its absence asserts nothing.

  A row rejected before any span was designated carries no designation and no attributability
  arms, and says so in `evidence_bound`. That is not a thinner record on one side of the verdict:
  a pick that falls on the carrier screen never reaches designation, so the row carries exactly
  what the screen that rejected it looked at. Running the arms for it afterwards would put
  evidence on the row that no verdict rested on. Twenty-two of the near-miss rejections are in
  that position and each names it.

  `matcher_revision` and `matcher_recheck` are scoped by stratum rather than by row. They record
  which revision of the citing-sentence matcher produced a rejection and what a re-derivation
  under the later revision returned, which is a question only an edge-drawing stratum raises.
  They are required present on every `clean_multi_hop` row and asserted absent on every row of
  any other stratum, so a value outside that stratum fails rather than passing as an optional
  extra. Within the stratum, `matcher_revision` carries a value on every row and
  `matcher_recheck` is null wherever the row was not re-derived, so the key is required and its
  value is not.
