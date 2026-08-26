# CLAUDE.md, architect-rag-verification

This file governs how Claude Code behaves in this repository. Read it in full at the start of every session. It is a governance file: Hasan decides what it says, and the conditions under which a change to it is applied are stated in Actors and ownership below. A rule that needs to change is raised under that division rather than rewritten.

## What this repo is

A public case study demonstrating a deterministic verification layer over a retrieval-augmented generation pipeline, evaluated honestly on a bounded public corpus of AI governance frameworks. The whole value of the repo is reproducibility and honesty. Every headline number can be reproduced from committed files with no API key and no cost. The repo openly states the failure modes it targets, reproduces them with real baseline numbers, adds the verification layer, and reports the measured delta including what the layer does not fix.

## Actors and ownership

- Hasan owns all go and no-go decisions, file placement, spend authorization, and the governance files: this `CLAUDE.md`, `docs/METHODOLOGY.md`, `PREREGISTRATION.md`, and any result claim written into the README. Owning a governance file means deciding what it says.
- Claude Code owns source code under `src/`, tests under `tests/`, derived artifacts under `data/` and `eval/`, and the running `SESSION_LOG.md`. It does not decide what a governance file says. It applies a change to one only on Hasan's explicit direction in the current session, checks every factual claim in that change against the repository before it lands, and records the change in the commit message and in `SESSION_LOG.md`. The division is by what each side can verify. Session log writing standard below applies that principle to log entries and states the reasoning.

## Session start

Read, in this order, before any substantive claim:

1. This file, in full.
2. `PREREGISTRATION.md` and `docs/METHODOLOGY.md`.
3. `data/retrieval/retrieval_manifest.json`, the parameter record and path index for the retrieval layer.
4. The most recent `SESSION_LOG.md` entry.
5. `CLAUDE.local.md`, if present. It carries machine-local working instructions, including any further reading, and is not part of the published artifact.

A reviewer with a clone can follow the session-start list above in full. `CLAUDE.local.md` is the one entry in it that may be absent, and it is named with that condition. Files named elsewhere in this document that are deliberately untracked are identified as untracked where they appear.

## Binding rules

1. Closed book. The model under test answers only from the retrieved chunks passed to it. Its prompt forbids drawing on training memory. These frameworks are in the model's training data, so closed-book enforcement is the spine of the whole result, not a formality. Without it the system can score well while ignoring retrieval entirely.

2. The only LLM in the operational pipeline is the model under test. One separate, offline step uses an LLM judge (RAGAS) solely to validate the deterministic grader against the recognized metric on a sample. Its outputs are committed, and it never produces a headline number or influences an answer, a flag, or an abstention.

3. Raw versus layer, same ruler. Two conditions share everything except the wrapper: same corpus, same chunking, same first-pass retrieval, same query set, same model, same decoding parameters, same grader. Raw is standard RAG with a neutral prompt, a single pass, no verification, and the answer accepted as is. Layer is the same model with the same first-pass prompt, followed by deterministic post-hoc checks that flag, refuse, re-retrieve, or abstain. Every headline is the layer-minus-raw delta on the identical query set under the identical grader. Document the layer's extra retrieval passes and their added cost and latency. Never handicap the raw condition, and state in the README that raw means no verification layer, not no retrieval.

4. Pre-registration is immutable. The query set, the ground-truth passages, the metrics, the thresholds, and the pass and fail rules are committed and timestamped before a single model answer is generated. After results exist, these files are never edited except by an explicit Hasan-directed correction, and that correction is logged in both the commit message and the session log.

5. Ground truth comes from the corpus, not from preference. Gold passages are defined by the documents' own cross-reference structure wherever possible. Adversarial and out-of-corpus queries have an empty gold set, and the only correct behavior is abstention.

6. Generation is the only paid step, and it is isolated. Running the models under test requires an API key and costs money. Run it once and commit the outputs: queries, retrieved chunks, raw answers, and layer answers. Every downstream number then reproduces deterministically over those committed files with no key. The pipeline must also support regenerating answers with a reviewer's own key, but that path is never required to verify a result.

7. Spend gate. No command that spends API credit runs until Hasan states the Anthropic Console balance explicitly in the current session. If the balance has not been stated, stop and ask.

8. Key hygiene. The API key is loaded only inside a subshell, `(set -a; source .env; set +a; COMMAND)`, never exported into the session and never committed. `.env` is git-ignored. `.env.example` documents the pattern with no real values.

9. Blind grading. The grader that scores supported versus unsupported runs as a separate invocation over committed files, with no shared state with generation. Scoring cannot see or be tuned to a single answer.

10. Git flow. Local first. Commit locally with conventional-commit messages. Push to the public GitHub remote only on Hasan's explicit go. Never force-push. Never rewrite committed history. Both authorized rewrite exceptions are spent; a defect in history is fixed forward or lived with.

11. Session log. `SESSION_LOG.md` records the work, not the commits. One entry covers one unit of work, which is usually several commits, and names every commit it covers with the hash and its subject. An entry does not name the commit that places it, since that commit's content is the entry, and that is the only commit an entry may omit: a commit touching any file other than `SESSION_LOG.md` is named by some entry. Where the placing commit needs to be identifiable, the entry states which commit will place it rather than citing a hash it cannot yet know. An entry is appended before the work is set aside, and a new session must be able to resume from the last entry plus the governance files alone. Entries are written to the standard below.

12. Tests for every deterministic check. Any grounding, completeness, retrieval-metric, or scoring function ships with tests. A deterministic check with no test does not merge.

13. Corpus integrity. Only the NIST AI RMF and the EU AI Act are shipped, both public and redistributable, with provenance and license recorded in `corpus/SOURCES.md`. ISO/IEC 42001 is copyrighted and is never included in any form. It is referenced by pointer only, by clause number and published title, never by quotation and never by a paraphrase that reconstructs clause content. Clause number and published title are the ceiling on a permitted reference, not its required form; referencing the standard by less than that, such as by its number alone, satisfies this rule.

14. Firewall. This repo is standalone. It must never import, reference, reproduce, or describe code, components, or internal design belonging to any other private project. The verification principle is re-implemented here from scratch. If a task appears to require anything from another project, stop and raise it.

15. Offline suite, no sockets. No test in the suite may open a network connection. The claim in `docs/REPRODUCE.md` that reproduction needs no network is asserted across the whole session by `tests/conftest.py`, which records every attempt, names the test that made it, and fails the run on a non-zero total. There is no exemption list and one is not added: a test that needs the network is either outside the offline set, which is a decision about where that set ends, or it is a defect. Two defects forced this. A dependency's telemetry opened a socket inside the offline set while building a user agent, which nothing here called deliberately; and the guard that was supposed to catch it passed precisely when a network was available, because a warm cache populated early by another test masked the fetch. The consequence is accepted with the rule: a dependency that begins fetching on import can turn the build red with nothing in this tree changing, which is the correct sensitivity for a repository whose central claim depends on how its dependencies behave. The guard's own control calls the connection helper so the recording stubs can be shown able to move; its stub intercepts before a socket exists, so nothing is opened and the control is not an exception to this rule.

## Verification discipline

Each of these was paid for by a defect in this repository. They are not style preferences.

V1. Investigate before building, and report before committing. No commit lands without its plan reviewed first.

V2. Read the code before deciding a fix. This has killed several bad fixes before they were written.

V3. Never resolve an ambiguity from model knowledge when a mechanical test exists. Run the test.

V4. Cross-check against an independent implementation rather than trusting one. Two implementations disagreeing is information.

V5. Audit exhaustively rather than sampling when the population is small enough to enumerate.

V6. Derive counts from a source rather than observing them. If a derivation does not match, stop. Do not adjust the derivation to fit.

V7. Never write a belief down as a measurement. "Should be", "is equivalent", "does not change" and "clean" either carry a number and the method that produced it, or they do not get written.

V8. Positive control on every emptiness claim. An empty result is accepted only alongside a control proving the same command, with the same flags, on the same file, finds hits. Four tools have returned false empties here: a shell not word-splitting an unquoted variable, a grep implementation parsing a leading dash as an option, a diff disagreeing with git on blank-line alignment, and a grep lacking an exact-line flag. A non-empty result certifies its own predicate and needs no control.

V9. Never suppress stderr in a sweep. A silent failure is indistinguishable from a clean result.

V10. Every enumeration reports its funnel: the starting population, each filter in order, the count each filter removed, and the removed items in full for any filter that takes out more than it leaves. A thin result is trustworthy only alongside evidence of what the command actually did. The one filter defect in this repo was invisible in the survivor list and visible only in the funnel.

V11. Quote a file verbatim from disk before writing a claim about it. A remembered fragment is not a source, and a path is not known until it has been read from a file that names it. Point at files rather than describing them. Where the claim is a characterization of what a piece of corpus text is or means, rather than a count of how often a string occurs, the quote ships alongside the claim in the same commit. A wrong count is caught by cross-checking against a recorded count; a wrong characterization has nothing to check against unless the text sits beside it. The same applies to attributions. A sentence stating that a named committed artifact records, states, shows or lists something ships with that artifact's relevant text quoted beside it in the delivery that proposes the sentence, before the commit lands, and this covers code comments, docstrings, commit messages, session log entries and governance files. One attribution here reached a docstring, a commit message and a log entry in a single drafting round and survived three readings of the docstring alone; it was visible in seconds once the source sentence sat beside it.

V12. Run the contradiction sweep across the whole repository before every governance commit, as standing practice rather than when someone thinks of it. Every hash resolves or is individually accounted for; every stated count is derivable and matches; every referenced file exists and ships; terminology matches Rule 1; every stated invariant carries a measurement. The sweep covers the ignored governance files by name, because they sit outside every mechanical guarantee the tracked tree makes about itself.

V13. Pin every defect in a regression test, so reversing the decision requires deleting a failing test.

V14. Record drops, exclusions, retractions and wrong predictions with their reasons, so conservatism is auditable and a wrong claim is retracted in the open rather than silently replaced.

V15. A threshold chosen after seeing the observations it will judge is fitted. A test cannot use its own subject as its oracle.

V16. Ordering in git is stronger evidence than assertion in a report. Commit a claim before the thing that could contaminate it.

V17. For any irreversible operation, reconnaissance precedes scoping. Measure first, scope second, and work from the verbatim text of every span the operation will touch rather than from facts about those spans.

V18. Name the check that proves a task worked and report its output, not an assertion that it passed.

V19. State predictions before an irreversible step so the result can contradict them. A prediction that fails is the mechanism working.

V20. A check that reports a pass or an absence is trusted only once it has been shown capable of failing. This is V8 generalised from emptiness to every check. Two forms have failed here. A comparison passes when both sides are absent: a digest verification loop reported a match on a completely failed copy, because both hash commands failed on a bogus path, both returned empty, and the empties compared equal. Assert the shape of each side before comparing it, and assert the expected count of things independently, since that is what caught it. A detector passes by blindness when it matches on structure and the claim lives in content: three detectors here matched a field path, a fixed prefix pattern, and a truncated span, and each returned a pass on the one site it existed to check. Before trusting a detector, run it against the known defect and confirm it fails.

V21. Artifacts committed together are cross-checked against each other, not only against their sources. Enumerate every claim one artifact makes that another artifact in the same commit also records, and re-derive each from the corpus or the code rather than from either file. Three defects here were a claim in one file contradicted by a number or a quote in a file committed beside it, and each survived several careful readings of the files separately.

V22. Every mutation run opens with a harness control: one known-catchable mutation shown red before any green from that run is trusted. Two harness defects here produced false greens, one from stale same-size bytecode compiled within the same second, and one from a companion that duplicated the check it existed to exercise.

V23. The predicted suite count is a collect-only measurement against the working tree, stated immediately before the full run with the arithmetic derivation beside it as a cross-check, and a disagreement is investigated before the run. Two tallies here undercounted a required companion; the count is measured, not remembered.

## Session log writing standard

`SESSION_LOG.md` ships. It is the contemporaneous record behind every process claim the README makes, and it is the file written most often by an agent with the least review per line. It is held to the README's standard, not to a working-notes standard.

The governing test: an entry that only makes sense to someone who was present when the work was done does not belong. The reader is a senior engineer with the repository and nothing else.

S1. Record the decision, the reasoning, the evidence, and what was rejected and why. Not the sequence of events.

S2. No process narration. Not who suggested what, not what was tried first, not how many attempts a fix took, not that a file was read before a claim was made. The discipline shows in the outcome; narrating it is padding.

S3. No internal workflow vocabulary in the shipped text. Terms describing how the work is organised rather than what was built do not appear. Name the actor or drop the reference.

S4. Provenance is marked only where it is load-bearing: where an owner decision overrode a governance rule, or overrode an agent's output, or where a claim's authority rests on who made it. Routine work is not attributed.

S5. No quality adjectives without a measurement. "Clean", "robust", "comprehensive", "successfully", "thorough" either carry a number and its method, or do not get written. This is V7 applied to prose.

S6. Failures, retractions, false-empty results and wrong predictions are recorded with the same weight as successes, in the same voice, without apology and without self-congratulation for having caught them.

S7. No first person, no second person, no present-tense enthusiasm. Past tense, stating what the repository does and why.

S8. Never restate what the diff shows. Length is set by the decisions in the commit, not by the size of the change.

S9. Never name a commit hash as the location of removed or private material. An untracked file whose use the repository discloses may be named, and an edit to it may be described by its mechanism and by which decision it records; its text is not reproduced. Untracked material the repository does not disclose is not described at all, by content or by purpose.

S10. Never cite a hash that does not resolve in the current history. A dangling citation is a defect wherever it appears.

S11. No em dashes, no emojis, consistent with every other file in the repo.

Authorship. Hasan owns the judgment in every entry: what a scope decided, what it retracted, what it discloses and how far a claim reaches. Claude Code drafts the prose, checking every factual claim in it against the repository as it writes, and Hasan reviews and rules. Where an entry carries a governance or disclosure judgment, Hasan states the judgment and what the entry must establish, and reviews the draft against it; where the entry is routine, Claude Code writes it outright.

The division follows what each side can verify. A claim about a file's contents, a count, a convention or a format is checkable only by the side holding the repository, and prose authored away from it reproduces exactly the errors the verification discipline exists to catch. Judgment about what may be disclosed and how strongly a claim may be stated is not mechanically checkable and stays with the owner. An entry is drafted once, after the measurements it describes are final, rather than revised alongside them.

Thoroughness is not the safeguard here; the standard is.

Heading dates are derived, not authored. A heading date is the committer date, in the repository's local timezone, of the commit whose work the entry records, not of the commit that places the entry.

## Layer-gold firewall

This constrains the operational layer.

The layer may not use any relation that defines the gold for the query it is answering. Corrective re-retrieval on an action-to-parent query may not traverse `action_subcategory`, because that relation is the gold. A layer that reads its own answer key recovers everything and measures nothing. Zero recovery under this constraint is a publishable finding. Total recovery by graph traversal is not a finding at all.

The layer's readable surface is an allowlist, and it is the same allowlist for every query including those with empty gold. By artifact and field:

- The `query` field of `eval/test_queries.jsonl`, and no other field of that file. The file's rows carry the keys `expected_units`, `gold_slots`, `id`, `note`, `query`, `split`, `subtype` and `type`, and every one of them other than `query` is barred.
- The retrieved context, defined below.
- The committed chunk-store text, meaning `data/chunks/*.chunks.jsonl` and `data/chunks/*.normalized.txt` and nothing else filed under `data/chunks/`. A derived relation artifact is not corpus text however it is filed, and several sit in that same directory.
- The committed unit index `eval/corpus_unit_index.json`, which is the set of unit ids and the chunks belonging to each, derived by grouping chunks on `parent_id`. It records which chunks compose a unit and never which unit relates to another.
- The committed retriever under `src/retrieve/`, which the layer may call with query strings it derives.

Everything else in the evaluation apparatus is barred. The barred set includes, as examples of the property and not as its boundary, `data/chunks/*.relations.jsonl`, `data/chunks/*.xrefs.jsonl`, `data/chunks/nist_ai_100_1.duplication_map.json`, `data/retrieval/verbatim_groups.json`, `data/retrieval/near_duplicate_exceptions.json`, `eval/test_query_verification.jsonl`, `eval/test_frame.json`, `eval/pass_one_designations.jsonl` and `eval/test_retrieval_results.json`.

Retrieved context is, per retrieved chunk, three values from `data/chunks/*.chunks.jsonl` and no others: the chunk's `text`, its `chunk_id`, and its `unit_label`. Every committed chunk carries one schema, whose fields are fixed by the frozen `Chunk` dataclass in `src/ingest/chunk_schema.py`, and every field of it other than those three is outside retrieved context. `structural_path` and `parent_id` are named because they carry unit structure directly: on an action chunk `structural_path` holds its parent subcategory's printed label. Retrieved context is per chunk and never per unit, so a sibling chunk of a retrieved chunk is not retrieved context unless it was itself in the fused top 10. Chunk ids and labels are the documents' own structural identifiers and are what any deployed retriever returns with a hit; they are not gold-defining relations.

The layer may use signals present in the query text itself. That is what makes a deterministic identifier comparison legitimate: the query names a subcategory, the retrieved blocks carry other identifiers, and the mismatch is detectable without touching any gold-defining relation.

The layer may not apply the function a gold-defining relation was derived by, in either direction. Re-deriving an edge is traversing it; the artifact read is not what makes the traversal legitimate. Relation traversal is mapping one unit's identifier to the identity of a different unit that a relation asserts is related to it, and that is what is barred; identity resolution, composing a printed name into the unit id of the unit bearing that name, is not traversal and is permitted. Two instances of the bar are named below, and the property governs rather than the naming.

The first is the action-identifier derivation. On every row whose gold is defined by `action_subcategory` in `data/chunks/nist_ai_600_1.relations.jsonl`, the layer may not derive a parent subcategory identifier from an action identifier taken from query text, chunk text, chunk id or unit_label, by suffix strip, by the legend printed at `nist_ai_600_1:sec_3#p1`, or by any equivalent map. The sealed query set records why, on every row of that stratum in `eval/test_query_verification.jsonl`: "The identifier is dropped because it is the gold-defining relation in string form, the 212 edges being derived from printed identifiers, and a layer parsing it out of the query recovers the parent without traversing the relation the firewall bars." Action-to-parent reports zero recovery through any parent-derivation route.

The second is the inverse citation walk. Following a citation printed in retrieved context forward, from a citing source to the unit it names, is legitimate. Walking backward from a retrieved target to an unretrieved unit that cites it is a corpus-wide cited-by lookup, which re-derives the clean multi-hop gold relation in reverse and is barred. No inverse citation index is built, from a committed relation artifact or by re-parsing corpus text.

Within those bars, references printed in query text and in retrieved context may be resolved and fetched, uniformly across every stratum, because the reference arrives printed rather than derived. A reference is a citation-formed surface under a grammar fixed before anything executes; resolution is composing the surface into a unit id and testing membership against the committed unit index; fetching returns that unit's committed chunks. Nothing is inserted by oracle: a surface that resolves to no unit is not fetched, and a surface absent from the query text and from the fused top 10 is never constructed.

Where a query's gold set is empty, as it is for every adversarial query, no gold-defining relation exists and the relation bar above does not bite. The allowlist is the whole constraint, unchanged and not relaxed: the layer sees the `query` field and the retrieved context, and abstention is reached from those or it is not reached.

## Receiving an instruction

An instruction that describes a filter as a property, rather than naming the artifact, the field and the accepted values, is sent back for the field and the values before it is implemented. Prose lifted from a sealed or governance file describes intent to a reader correctly; the same prose becomes a silent misfilter when it becomes code. This has already cost one defect, where a filter described in prose excluded the single class that could carry the relation it was meant to find.

The same applies to scope. An instruction naming how many items a change covers, rather than the property those items share, is answered with the property and the count it actually yields. A count is a description of the answer, and the side holding the schema is the side that can derive it. This has cost one defect, where a change scoped to three rows had a property holding on five.

Raise an objection on correctness before implementing, whenever one exists. An instruction that is wrong is more useful caught than executed. Style is not the target; correctness is.

## Output conventions

No em dashes and no emojis in text authored for this repository, including code comments, commit messages, documentation, and the session log. Use commas, periods, and ellipses. The prohibition reaches authored text only. It follows that source text is reproduced exactly wherever it appears, whether quoted inside authored prose or carried in a derived artifact, including punctuation this rule would otherwise bar, since altering it to satisfy a style rule breaks the fidelity to the source that the quotation or the artifact exists to preserve; that a file redistributed unmodified from outside this repository is left as received; and that a character appearing in code as a value the code exists to handle is not prose about that character. Keep the README and docs plain, precise, and free of marketing language. The audience is an engineering team that will clone the repo, run it, and judge whether it reflects real understanding of production RAG.
