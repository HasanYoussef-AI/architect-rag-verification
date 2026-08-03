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
  and the bounds on any target that cannot discriminate.
- `test_query_rejections.jsonl`: the adversarial stratum's authoring scan. Each row records an
  identifier considered and not used, with the class rule it was scanned under, its ordinal in
  that scan, and the evidence for the decision. The adversarial stratum has no draw order in the
  frame, so these rows are not draw-order rejections and no selected set reconstructs from them.
- `test_frame_rejections.jsonl`: draw-order rejections for the four drawing strata. Each row
  names its `stratum` and `source`, which together index the frame's draw order, and carries the
  rejected candidate verbatim in `rejected` so it compares equal to a draw-order entry.
  `tests/test_test_frame.py` reconstructs each stratum's selected set from the committed draw
  order plus these rows alone.
