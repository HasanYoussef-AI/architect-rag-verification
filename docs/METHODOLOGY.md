# Methodology, architect-rag-verification

This document explains the design and the honest limits of the case study. It is the rationale behind the binding rules in `CLAUDE.md`, and it feeds the design section of the README. It is a governance file, owned by Hasan and the strategy chat.

## Purpose

Demonstrate a deterministic verification layer over a retrieval-augmented generation pipeline, and measure honestly whether it improves documented RAG failure modes, including what it does not fix. The value is honesty and reproducibility. The repo states the problem it targets, shows a baseline that reproduces the failure with real numbers, adds the layer, and reports the measured delta and the failures that remain. The case study deliberately targets specific failure modes to test the verification approach. That is focused engineering, not a staged trick, and it is stated as such.

## The two failure surfaces

Research is consistent that RAG fails on two distinct surfaces, and that most teams blur them. Keeping them separate is the point.

Surface one is generation faithfulness. The model asserts claims the retrieved chunks do not support, including citing a real chunk that does not actually say the thing. Even with perfect retrieval, frontier models still fabricate in a meaningful fraction of summaries, so this is real and unsolved. The layer targets it directly with claim-level grounding checks. Every claim in the answer must be supported by text actually present in the retrieved chunks, and unsupported claims are flagged or refused.

Surface two is retrieval completeness. The retriever misses a relevant passage, the model answers faithfully from the partial context, and the answer is faithful but wrong. This is the trap where faithfulness scores look high while the system misses the passage that mattered. Independent 2026 write-ups describe exactly this: a legal RAG scoring high on faithfulness while roughly one in six answers miss a key statute, because the retriever dropped a passage on multi-hop questions and the generator answered coherently from what it had. Because our corpus is bounded, the layer runs a second-pass completeness check that compares the query, the retrieved chunks, and the full document set to detect relevant passages the first pass missed, triggers corrective re-retrieval, and abstains only if it still cannot ground the answer.

The two surfaces combine into one decision. Answer confidently when retrieval is strong and every claim is grounded. Flag or abstain when retrieval is weak or a claim is unsupported.

## Experiment design, raw versus layer, same ruler

Two conditions share everything except the wrapper: same corpus, same chunking, same first-pass retrieval, same query set, same model, same decoding parameters, same grader.

Raw is standard RAG. The model receives the retrieved chunks and the question under a neutral production prompt that includes the ordinary instruction to say it does not know when the context does not support an answer. It answers in a single pass, and the answer is scored as is. Raw means no verification layer, not no retrieval, and the README states this so the baseline cannot be read as handicapped.

Layer is the same model with the same first-pass prompt, so the model itself is unchanged on the first pass. Deterministic checks are then applied outside the model: grounding flags or refuses unsupported claims, completeness can trigger corrective re-retrieval and a redraft, and the system abstains if it still cannot ground. The layer may issue additional retrieval passes and a second model call, and the README reports that added cost and latency.

Every headline is the layer-minus-raw delta on the identical query set under the identical grader. We also run more than one model tier, a weaker and a stronger base model, so the repo can show whether the layer helps more where the base model is weaker.

## Closed-book enforcement

Both the answering model and every check reason only over the documents and chunks provided, never from training memory. These frameworks are in the models' training data, so without strict closed-book enforcement the system could score well while ignoring retrieval entirely. Closed-book enforcement is the spine of the result and is demonstrable.

## Scoring integrity

The deterministic scorer is the grader of record. It produces every headline number, reproduces for free with no key, and cannot be tuned by rewriting a prompt. Since the person building the checks also reports the results, a promptable LLM judge as grader would be a place to consciously or unconsciously flatter the layer. The deterministic grader removes that risk by construction.

The LLM judge is a one-time validator, never a grader. RAGAS faithfulness runs once on a sample, its outputs are committed, and it exists to answer one question: does the free deterministic scorer agree with the recognized standard metric, and where does it disagree. We report the agreement rate and analyze the disagreements honestly. This proves the deterministic method is sound rather than a rigged shortcut, surfaces the real limitation of deterministic scoring, which is that string and overlap matching can miss genuine paraphrastic support, and demonstrates understanding of both the standard tool and its failure modes.

Ground truth comes from the corpus, not from preference. Gold passages are defined by the documents' own cross-reference structure wherever possible, so the ground truth is a property of the corpus rather than a choice made to flatter the layer. Adversarial and out-of-corpus queries have an empty gold set, and the correct behavior is abstention.

Pre-registration predates results. The query set, gold passages, metrics, thresholds, and pass and fail rules are committed and timestamped before a single answer is generated. The commit history is the proof that the scoring rules predate the results.

Blind grading. The grader runs as a separate invocation over committed files, with no shared state with generation, so scoring cannot be tilted toward a particular answer.

## Metrics

Generation faithfulness is reported as the unsupported-claim rate, the fraction of atomic claims in an answer not grounded in the retrieved chunks, before and after the layer. Retrieval is reported with Precision@10, Recall@10, MRR, and NDCG@10 against the slot-based gold defined in the pre-registration, which surfaces the completeness failures that faithfulness alone hides. Both surfaces are reported separately, so the repo honestly shows what the layer fixes and what it does not.

## Reproducibility model

Running the models under test needs an API key and costs money, which is unavoidable because we test real models. That step runs once and its outputs are committed: queries, retrieved chunks, raw answers, and layer answers. The entire evaluation then runs deterministically over those committed files with no key, so any reviewer can clone the repo and reproduce every number for free. The pipeline also supports regenerating answers with a reviewer's own key, but that is never required to verify a result. No API keys are ever committed, and the documented `.env` pattern is the only way the key enters.

## How this repository was developed

Development used a working file that is not tracked here. It held session state, working notes, and a running index of decisions, and it is named in the session log wherever an entry records work done on it. It is not published and nothing in it is needed to reproduce any number in this repository.

The decisions that govern this repository are in the tracked record: `CLAUDE.md`, `PREREGISTRATION.md`, this document, `SESSION_LOG.md`, `data/retrieval/retrieval_manifest.json`, and `corpus/SOURCES.md`. The retrieval parameters and their provenance live in the last two rather than in prose, so they can be checked mechanically rather than read. A decision found only in the untracked file is a defect, and the audit that produced this statement moved four of them into the files above rather than leaving the statement narrower.

One category is deliberately absent from the tracked record. The identifiers of commits removed by the history rewrite are not written down in the tracked record, because a citation that does not resolve is worse than no citation. The rewrite itself, its scope, and what it did and did not cover are recorded in the session log.

## Honest boundary

The completeness check works precisely because the corpus is bounded and small enough to read in full per query. This does not scale. As the corpus grows, reading every document per query becomes cost-prohibitive and slow, and past that point the honest fallback is retrieval-confidence estimation with abstention rather than full-document checking. The README states this boundary in writing, names the rough point where full-corpus checking stops being practical, and does not claim the bounded-corpus method as a general solution.

## What the layer does not fix

This section holds real entries after the runs. A benchmark that only contains cases the layer passes is disqualifying, so the query set includes cases we expect to struggle with, and the results here are honest. Entries are added once measured.
