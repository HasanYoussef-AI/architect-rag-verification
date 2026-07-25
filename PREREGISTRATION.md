# Pre-registration, architect-rag-verification

This document defines the evaluation before any model answer is generated, so results cannot be tuned after the fact. Per CLAUDE.md Rule 4 it is immutable once results exist, except by an explicit Hasan-directed correction logged in the commit message and the session log. The commit history is the proof that the scoring rules predate the results.

## Revision note

This revision extends the bootstrap pre-registration placed at a4383816 on 2026-07-21. No generation has run and no result exists, so the file is revisable under Rule 4 and nothing below is a post-hoc rescue.

- **Extended, as the bootstrap file said Phase 1 would.** The sealed-set composition, the gold set rules, the per-stratum predictions, and the retrieval scoring detail are added. These were always deferred to this commit.
- **Added.** The no-context condition, approved on 2026-07-24 before any result, so contamination is measured directly rather than left as a caveat. Named no-context rather than closed-book, since in this repo closed-book already denotes the grounding discipline of answering only from retrieved chunks and never from training memory, per CLAUDE.md Rule 1. Reusing the term for a no-retrieval condition would collide with that.
- **Corrected, one pre-registered definition.** The near-miss stratum is redefined from a faithfulness trap, terms present but not answering, to a retrieval discrimination trap, a plausible near-identical unit surfaced over the actually-right one. Reason: the measured development query 11 case is a discrimination failure by construction, and the bootstrap definition predated that measurement. Logged here, in the commit message, and in the session log per the immutability clause.

## Status

The evaluation design below is locked. The query set and the ground-truth passages are added in a dedicated pre-registration commit that predates any generation run.

Frozen inputs this pre-registration is derived from and cites: the corpus frozen at aea1279, 1,294 globally unique chunks, chunk IDs immovable; retrieval locked and declared untuned at b0605fb, first-pass context set the fused top 10; and the reserved 40-unit development pool committed before any development query was written. No gold unit in this test set may be drawn from that pool, and the test-set builder will assert this mechanically when it is built.

## Conditions

- **Raw:** standard RAG. Neutral production prompt including the ordinary instruction to say it does not know when the retrieved context does not support an answer. Single pass, no verification, answer scored as is. Raw means no verification layer, not no retrieval.
- **Layer:** same model, same first-pass prompt. Deterministic grounding check, deterministic completeness check, corrective re-retrieval, abstain if still ungrounded. May issue extra retrieval passes and a second model call, and the added cost and latency are reported.
- **No-context:** same model, no retrieved context, single pass. Measures how much of the raw score is carried by parametric knowledge of a public corpus rather than by retrieval. One run per tier, added per the 2026-07-24 decision.
- **Shared across raw and layer:** corpus, chunking, first-pass retrieval, query set, decoding parameters (temperature 0), grader. The no-context condition shares the subject matter, the decoding parameters, and the grader, but by definition receives no retrieved context.
- **Models:** Haiku 4.5, Sonnet 5, Opus 4.8, same model on both sides of every comparison, each also wrapped in the layer.
- **Run accounting:** nine reported conditions from six runs. Three first-pass runs, one per tier, each serving both raw and layer because the layer is post-hoc on the identical first pass, which removes generation variance from the delta. Three no-context runs, one per tier.

## Metrics

Generation faithfulness, grader of record, deterministic:
- Unsupported-claim rate, the fraction of atomic claims in an answer not grounded in the retrieved chunks, reported before and after the layer.
- Grounded is defined by span alignment and semantic-overlap thresholds finalized with the scorer and recorded here before generation. The deterministic grounding check is built and frozen against the twelve development generations before the sealed fifty run, so it cannot be shaped by the real outputs.

Retrieval, deterministic, computed from gold chunks:
- Precision@k, Recall@k, MRR, NDCG@10, against the fused top 10.
- Scored against slot-based gold, defined under Ground truth. A slot is satisfied by any unit in its acceptable-unit set, so recall is slots satisfied over total slots, precision is retrieved units satisfying some slot over ten, MRR uses the first gold-satisfying unit, and NDCG@10 gives gold-satisfying units gain 1. Not computed for adversarial queries, whose gold is empty.

Validator, LLM judge, one-time, not a grader:
- RAGAS faithfulness on a sample. Report the agreement rate with the deterministic scorer and analyze the disagreement cases. Never produces a headline number.

## Thresholds and pass or fail rules

- Any grounding, abstention, or completeness threshold is finalized on the development split only, against the twelve development generations, and is never touched on the sealed test set.
- The headline result is the layer-minus-raw delta on the identical query set under the identical deterministic grader, per tier and per surface.
- Pre-registered null interpretation, recorded before running: if the layer does not reduce the unsupported-claim rate or does not improve recovered-passage recall on a tier, that is a real finding reported as is. A clean null is diagnostic, not a failure, and is not to be rescued by post-hoc tuning. If a strong tier self-governs in prose so the delta is null, that is a real finding about where a verification layer is measurable, recorded plainly rather than spun.

## Query set

Added in the Phase 1 pre-registration commit, before generation. 50 queries, stratified 18 single-hop, 16 multi-hop, 8 adversarial, 8 near-miss. Query embeddings ship in the same commit as the queries, per the level-2 reproducibility rule in the retrieval manifest.

### Composition

Counts are fixed. Expected-hard and measured cases are carved out from within a stratum's count, never added on top. The majority of each stratum is clean, so every baseline is real and any layer delta is earned rather than staged.

- **Single-hop factual, 18.** Retrieval easy, answer grounded in one unit. Spread across the EU AI Act, NIST AI 100-1, and NIST AI 600-1. The Playbook is excluded here; its only atomic-factual candidates are duplicates of the NIST subcategory statements, and its unique content is block elaboration rather than atomic fact.
- **Multi-hop cross-reference, 16.** Twelve clean, built on cross-references that resolve on both endpoints and link genuinely different content, sourced from EU AI Act internal cross-references and NIST prose references. Four action-to-parent, expected-hard, each asking for a parent subcategory statement given its action text, where measured first-pass fused recall is 4.7 percent against a 0.77 percent random baseline, so each carries a pre-registered first-pass-miss prediction. The cap is four so at least twelve clean cross-references remain. `structural_join` is not a multi-hop basis: it links the same subcategory statement across documents, which is duplication, not a different-content hop. Recorded corpus finding: the EU AI Act carries genuine internal cross-reference structure while NIST cross-document structure is restatement, so clean multi-hop is EU-concentrated by a real property of the frameworks.
- **Adversarial, 8.** Gold empty, correct behaviour is abstention from context. Three grounded on ISO/IEC 42001, excluded from the corpus on copyright grounds but known to the models parametrically, where correct behaviour is to state the answer is not in context and withhold the parametric answer. Four on plausible-nonexistent identifiers, each a well-formed EU article number or NIST subcategory id verified absent against the frozen chunk-id set, where correct behaviour is to refuse to fabricate a provision. One pure out-of-domain.
- **Near-miss discrimination, 8.** The retriever surfaces a plausible near-identical unit over the actually-right one, a discrimination failure distinct from the multi-hop completeness gap. Gold is the correct unit. Three measured, the development query 11 structure where a subcategory's own block was crowded out of the top 10 by other subcategories' near-identical blocks, drawn from the 20 normalise-identical block clusters and the 12 fixture near-block-duplicates. Five authored from units with a high-similarity non-identical neighbour in the committed `near_duplicate` class. The uncommitted 604 near-tie pairs are not used, since folding an uncommitted measurement into a sealed set would break the derive-from-a-committed-source rule.

## Ground truth

Added in the Phase 1 pre-registration commit, before generation. Gold passages are derived from the documents' own cross-reference structure wherever possible. Multi-hop queries are built on top of an existing cross-reference so the correct passages are defined by the document. Adversarial and out-of-corpus queries have an empty gold set, and the correct behavior is abstention.

### Gold set rules

- **Unit-level, slot-based.** A gold set is a set of required slots; each slot is satisfied by any unit in its acceptable-unit set. Single-hop queries have one slot, multi-hop queries have the slots their hops require. Where a statement is duplicated verbatim across documents, any one carrying unit satisfies that slot.
- **Playbook-adds-beyond-Core exception.** Where a query asks specifically what the Playbook adds beyond the Core statement, the Core unit does not satisfy the slot.
- **The cross-reference graph is a candidate generator, not the authority.** Every edge entering a gold set is read and verified individually at authoring, and that verification is recorded alongside the query. Near-verbatim duplication gets no automated map; it is handled by this individual verification.
- **Gold sources.** EU AI Act internal cross-references, `action_to_subcategory`, NIST prose references, the duplication map, the normalise-identical block clusters, and the `near_duplicate` class. `structural_join` is not a gold source for multi-hop.

## Pre-registered predictions

Recorded before any run so no outcome can be spun after the fact.

- **Single-hop.** Layer delta near zero; nothing to fix on easy grounded cases. A null confirms the layer does not degrade the easy path.
- **Multi-hop clean.** Small positive completeness delta where the first pass drops a linked slot and corrective re-retrieval recovers it.
- **Action-to-parent.** First-pass miss pre-registered on all four. Recovery confirms the prediction; a non-recovery is a what-still-fails entry. Neither is spun.
- **Adversarial.** Raw predicted to answer some, especially the ISO cases, from parametric knowledge. Layer predicted to raise abstention correctness. This is the sharpest edge of the faithfulness story.
- **Near-miss.** The stratum separates faithfulness from answer-correctness. A response can be faithful, every claim grounded in a retrieved unit, and still wrong, when the near-identical neighbour is retrieved and the target is not. The completeness check is what addresses this: the layer is predicted to flag near-miss queries whose target slot is absent and re-retrieve.

## Firewall, commit ordering, immutability

1. This specification commits first, with no query, gold, rank, score, or result present.
2. The instantiated queries, their gold sets, the per-edge verification records, and the query embeddings commit second, before retrieval runs on them, carrying no rank, score, or result.
3. Retrieval runs on the fifty third, producing the frozen retrieval metrics.
4. Generation runs last, behind the spend gate.

The test-set builder will assert that no gold unit is drawn from the reserved 40-unit development pool. Once any result exists, the sealed set and this specification are immutable except by a logged Hasan-directed correction.

## Spend

Pre-registration and retrieval on the fifty spend nothing: no API call, no key, no balance confirmation for either. Generation is the single paid step, and runs only after the confirmed Anthropic Console balance is stated in session and the projected cost is computed from real token counts. The balance is a session fact recorded in the session log at generation time, not committed here.

## Contamination

The corpus is public and pre-dates every tier's training cutoff, so it cannot be firewalled from the models. Parametric knowledge is present identically on both sides of the raw-versus-layer comparison, so it cancels in the delta. What it distorts is the absolute numbers: raw retrieval-augmented generation looks better than it would on a genuinely unseen corpus, which compresses the delta rather than inflating it, the safe direction. The no-context condition measures this directly and turns the caveat into a number.
