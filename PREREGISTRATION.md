# Pre-registration, architect-rag-verification

This document defines the evaluation before any model answer is generated, so results cannot be tuned after the fact. Per CLAUDE.md Rule 4 it is immutable once results exist, except by an explicit Hasan-directed correction logged in the commit message and the session log. The commit history is the proof that the scoring rules predate the results.

## Status

Bootstrap: the evaluation design below is locked. The query set and the ground-truth passages are added in a dedicated pre-registration commit at the start of Phase 1, and that commit predates any generation run.

## Conditions

- Raw: standard RAG. Neutral production prompt including the ordinary instruction to say it does not know when the retrieved context does not support an answer. Single pass, no verification, answer scored as is. Raw means no verification layer, not no retrieval.
- Layer: same model, same first-pass prompt. Deterministic grounding check, deterministic completeness check, corrective re-retrieval, abstain if still ungrounded. May issue extra retrieval passes and a second model call, and the added cost and latency are reported.
- Shared across conditions: corpus, chunking, first-pass retrieval, query set, decoding parameters (temperature 0), grader.
- Models: raw Haiku 4.5, Sonnet 5, Opus 4.8, each also wrapped in the layer.

## Metrics

Generation faithfulness, grader of record, deterministic:
- Unsupported-claim rate, the fraction of atomic claims in an answer not grounded in the retrieved chunks, reported before and after the layer.
- Grounded is defined by span alignment and semantic-overlap thresholds finalized with the scorer and recorded here before generation.

Retrieval, deterministic, computed from gold chunks:
- Precision@k, Recall@k, MRR, NDCG@10.

Validator, LLM judge, one-time, not a grader:
- RAGAS faithfulness on a sample. Report the agreement rate with the deterministic scorer and analyze the disagreement cases. Never produces a headline number.

## Thresholds and pass or fail rules

- Any abstention threshold and any completeness threshold are tuned on a dev split only, never on the sealed test set.
- The headline result is the layer-minus-raw delta on the identical query set under the identical deterministic grader, per tier, and per surface.
- Pre-registered null interpretation, recorded before running: if the layer does not reduce the unsupported-claim rate or does not improve recovered-passage recall on a tier, that is a real finding reported as is. A clean null is diagnostic, not a failure, and is not to be rescued by post hoc tuning.

## Query set

Added in the Phase 1 pre-registration commit, before generation. 50 queries, stratified:
- 18 single-hop factual, retrieval easy, answer grounded.
- 16 multi-hop cross-reference, retrieval hard, the completeness trap.
- 8 adversarial or out-of-corpus, correct behavior is abstention.
- 8 near-miss distractor, terms present in the corpus but not answering the question, the faithfulness trap.

## Ground truth

Added in the Phase 1 pre-registration commit, before generation. Gold passages are derived from the documents' own cross-reference structure wherever possible. Multi-hop queries are built on top of an existing cross-reference so the correct passages are defined by the document. Adversarial and out-of-corpus queries have an empty gold set, and the correct behavior is abstention.
