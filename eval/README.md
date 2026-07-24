# Evaluation queries

## Firewall

Development queries are never scored and never reported in results. They exist only
to catch structural breakage in the retriever. Because every retrieval parameter is
locked and untuned, and was fixed before any query set existed, the development set
has no tuning role. Its single job is to fail loudly if tokenisation, scoring,
fusion, quantisation, or the embeddings break.

The 40-unit development pool in `dev_unit_pool.json` is reserved and committed
before any development query is written. Development queries draw their expected
units only from that pool, so that no pre-registered gold unit can be drawn from it.
The one exception is the out-of-corpus query, which has no gold unit by definition
and may reference material outside the pool; it consumes no pool budget and is
marked as such in `dev_queries.jsonl`.

The pre-registered test set will live in `test_queries.jsonl`, committed and
timestamped before any generation run and immutable once results exist. A
disjointness assertion will require that no test gold unit is drawn from the
development pool.

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

## Files

- `dev_queries.jsonl`: twelve development queries, one per row, each with `split`
  set to `development`, a `type`, informal `expected_units`, and a `note`.
- `dev_query_embeddings.npy`: their embeddings, float32, aligned row for row with
  `dev_queries.jsonl`, generated on the same `normalise_for_comparison` plus ONNX
  path as the corpus embeddings.
- `dev_unit_pool.json`: the reserved development unit pool.
