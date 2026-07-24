# Session log, architect-rag-verification

Running log owned by Claude Code. One entry per commit, per CLAUDE.md Rule 11.
A new session should be able to resume from `rag_case_study_tracker.md` plus the
last entry here alone. Newest entries at the top.

## 2026-07-24, retrieval build: normalised embeddings, dense quantisation, fixture and artifacts, manifest

The hybrid retriever is built and committed across six scoped commits, all local
only. Every parameter is locked untuned and recorded in the retrieval manifest,
which pre-registration will cite. The query set and gold do not exist yet, so
nothing here is fitted to them.

What changed, with the measurements behind it:

- Embeddings are generated from bge-base-en-v1.5 `onnx/model.onnx` at revision
  a5beb1e3, with the embedding input comparison-normalised on both corpus and query
  side under the shared-path rule. This folds the publisher's curly quotes and en/em
  dashes a typed query never contains, changing 399 of 1,294 embeddings, median
  cosine 0.9995. An earlier claim that the arms diverged on whitespace is retracted:
  the tokenizer folds whitespace, verified as identical token IDs and cosine 1.0 on
  all 32 whitespace pairs, so the divergence was entirely typographic. The claim that
  verbatim-identical tying "was violated for 32 groups" is struck; it was never
  violated, those 32 tied on both arms throughout.
- Dense scores are quantised to 4 decimals before ranking, derived from a measured
  1.49e-6 max deviation between BLAS matvec paths, 67x above it. BM25 is not
  quantised, its cross-path deviation measured exactly zero, scalar scatter-add in
  fixed order with avgdl switched to an exact integer sum, bitwise-identical to
  np.mean at 128.4242658423493. The fused score is not quantised, it is a function of
  the deterministic ranks alone, and rounding it was measured to reshuffle 369 top-10s.
- Determinism footprint is 46 of 1,294 top-10s versus unrounded, all from the dense
  arm. The residual quantisation cannot remove is 4,242 near-boundary dense scores in
  the dense top-100, worst-case 17 of 1,294 known-item top-10s could differ across
  BLAS builds, 7 membership and 10 ordering, scoped in the manifest to reproducibility
  levels 2 and 3 only; level 1 committed outputs are exact.
- Fixtures and artifacts: the known-item fixture pins rank-1 for all 1,294 chunks
  exactly, 1150 self, 36 raw twin, 32 normalised twin, 76 near-duplicate; the verbatim
  group artifact, 55 normalised groups and 23 raw; the near-duplicate exception list,
  64 cross-document statements predicate-clean over the full 96 and 12 hand-audited
  blocks; the reserved 40-unit development pool over all 22 strata.
- The bge `README.md` and `1_Pooling.config.json` are vendored at the revision under
  the verifier, 24 checks, recording MIT via the README frontmatter, no LICENSE file
  exists at the revision which was checked not assumed, and CLS pooling.

Why:
- This is the retrieval layer both conditions share. It is settled and reproducible
  before the query set exists, so no parameter can be fitted to results. 198 tests
  pass, including the exact-equality known-item fixture and the rank-bm25 cross-check.

Caught gap, recorded rather than filed as routine: onnxruntime was a floor at
`>=1.19` in pyproject rather than a pin, with the lock happening to resolve 1.27.0.
Now pinned `==1.27.0` in both. The second time in this work that confirming a
believed-true fact found it was not.

Commits, six, local only:
- 2a65b31 feat: normalised bge-base-en-v1.5 embeddings via ONNX
- bd7c887 feat: hybrid BM25 plus dense retriever with dense-arm quantisation
- 9ffc20f feat: verbatim group and near-duplicate exception artifacts
- c7febcb feat: reserved development unit pool, committed before any dev query
- 3fc8e82 test: known-item fixture and deterministic retrieval checks
- c6a2bfb docs: retrieval manifest recording final config and measurements

Current state:
- Local git on `main`, no remote, nothing pushed. Retriever, embeddings, fixture,
  artifacts, development pool, manifest, and tests committed. Every headline parameter
  is in `data/retrieval/retrieval_manifest.json`.

Next step:
- Author the development queries within the reserved pool, development split, then run
  the embedding-gap and arm-bias diagnostics on this final pipeline, committing query
  embeddings alongside the query set per the level-2 rule in the manifest. Then the
  pre-registration commit that adds the test query set and gold, which must predate any
  generation run.

## 2026-07-24, CORPUS FREEZE, join symmetry, EU downstream_notes, AI 100-1 prose and header strip

This is the corpus freeze. After this commit chunk IDs are cited by
pre-registration and cannot move. Three corrections were made so the
cross-document graph and the manifests are consistent, all verified to leave
chunk IDs unchanged and globally unique at 1,294. A consolidated freeze-point
verification preceded them and reconciled: 1,150 units, 1,294 chunks, all
relations resolving on both endpoints, the verifier's 28 checks passing,
exact-substring passing corpus-wide, and byte-identical reruns.

### 1. structural_join made symmetric, and why it mattered

The Playbook joined only to AI 100-1, not to AI 600-1, so a relation over shared
subcategory identifiers was DIRECTION-DEPENDENT: traversal from AI 600-1 reached
the Playbook counterpart of a subcategory but traversal from the Playbook did not
reach the AI 600-1 one. Ground truth whose content depends on which document you
start from is not a property of the corpus, which is the whole reason the join
spine exists. This was a scoping choice I made silently to avoid a cross-document
dependency, and it should have come as a governance question at the time, because
it changed what the relation CONTAINS rather than merely how it is computed. The
standing rule going forward: a scoping choice that changes what a relation
contains is raised, not noted locally.

The fix is the same mechanical rule applied consistently. The Playbook now derives
joins to both other documents by the identical printed-identifier search AI 100-1
uses (resolved_document_text in nist_pdf_common). Graph is symmetric: AI 100-1 and
Playbook 72/72, AI 100-1 and AI 600-1 49/49, AI 600-1 and Playbook 49/49. Only the
Playbook moved, 72 to 121; AI 100-1 stayed 121 and AI 600-1 stayed 98, nothing
else moved. test_forward_references asserts every edge has its reverse, generally
rather than by count, so it holds if the corpus changes.

### 2. EU AI Act downstream_notes added

The EU manifest was built in part one, before the comparison-time ruling, and
carried no downstream_notes. The freeze-point check caught it, three of four
manifests carrying a requirement the retrieval step will read. Added: the
comparison-time normalisation map, a 7-codepoint non-ASCII inventory of the
stored text (only curly quotes, apostrophe and em dash, all folded by the map;
plus U+00E0 and U+00E9 as genuine content in French terms, marked deliberately
excluded), a verified-absent note that guillemets, the en dash and U+00A0 were
examined and are absent, the U+00A0 part-one note that it is folded at ingestion,
and an integrity-path note that this HTML document is validated by DOM nesting,
ELI anchors and the recital-count assertion rather than a raw_chars partition, by
design, so a future reader does not read the absent partition proof as a gap.

### 3. AI 100-1 prose schema normalised to three classes

Field shape aligned with AI 600-1 and the Playbook, every reference internal by
construction, class set directly. The three-class classifier was run first as a
guard and flagged exactly one of 38 references, "Fig. 3", as cross_document. That
is a classifier false positive, not a real reclassification: the classifier
detects an external instrument by name, and AI 100-1 is itself the AI RMF, so its
own running header "AI RMF 1.0" next to the Fig. 3 caption reads as a citation of
another document. Structural inapplicability, not miscalibration, so the
classifier is not tuned for it and not wired in; the manifest records that it must
not be, to stop a future session repeating the false positive.

### 4. AI 100-1 running-header strip

The false positive exposed the real defect: the running header
"NIST AI 100-1 AI RMF 1.0" was embedded once in a content line, prepended by
PDFium to the Fig. 3 caption in sec_2#p2, so the document title was sitting in a
real content chunk and would inject title terms into BM25 and pollute that
chunk's embedding. Same defect class as the exam-Page footer merge already fixed
in this document, found later. Stripped positionally in the same shape as the
footer tail-strip: the header prefix removed from the content line into a new
Line.head field, its characters accounted to the running_header discard class,
and every character kept in the committed extracted text so nothing leaves the
audit trail.

Verified after the content change: partition still closes over raw_chars 107,702,
running_header rose from 984 to 1,009 and content fell by the same 25, no chunk ID
moved, split count still 10, chunk total still 134, duplication unchanged at 48
and 47 (sec_2 is narrative, not a Core statement), exact-substring passing
corpus-wide, global uniqueness still 1,294. A generalised test asserts no chunk
contains the running-header text, so a further embedded instance fails loudly
rather than surviving. AI 600-1 and the Playbook were swept for the same class,
running headers and repeated table headers checked for merged instances, and both
are clean: AI 600-1's table header and the Playbook's footer are discarded with
zero merged occurrences, and neither has a per-page running header.

### What did not change

AI 600-1's outputs are byte-identical, untouched this step. The Playbook's chunks
are unchanged, only its relations moved with the symmetric join. The EU chunks are
unchanged, only its manifest gained the notes. AI 100-1's chunk IDs did not move;
only sec_2#p2's text lost the stripped header.

Commit: 777235a
  (fix: symmetric structural_join, EU downstream_notes, AI 100-1 prose schema and
  header strip, local only)
  This entry is recorded by the next commit, `docs: log corpus freeze commit,
  local only`, committed immediately after this entry is written, which closes the
  chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-six commits, all trailer-free.
- CORPUS FROZEN. The EU AI Act and all three NIST documents are ingested,
  verified, and consistent: 1,150 units, 1,294 globally unique chunks, all
  relations symmetric and resolving, all four manifests carrying downstream_notes.
  167 tests pass, ruff clean, byte-identical reruns.
- No retrieval, no query set, no gold passages, no results yet.

Next step:
- Phase 1 retrieval, then the query set and gold passages derived from the frozen
  cross-document graph and the duplication map, then the immutable pre-registration
  commit that predates any generation run. At retrieval, apply the recorded
  comparison-time normalisation on both sides for grounding and BM25, and treat the
  GV-4.3-001 lexical-mismatch as a known case, not a designed trap.

## 2026-07-24, NIST corpus ingestion COMPLETE, AI 600-1 and Playbook ingested

AI 600-1 and the Playbook are now ingested with the corrected resolver, from the
clean commit. All three NIST documents and the EU AI Act are ingested. The eight
untracked draft files were reworked against the wired resolver, not trusted.
Ingestion is finished; the next phase is the query set, gold passages, and
pre-registration.

### The one finding that needed a ruling, and how it was handled

AI 600-1 has 212 printed action rows, but the strict anchor found 211. The 212th,
GOVERN 4.3's first action, prints garbled in the PDF's own text layer as
"GV4.3--001" where the correct printed form is "GV-4.3-001". Cross-engine check as
ruled: pypdfium2, poppler plain, poppler layout and pdfminer.six all render it
identically, so the defect is in the source PDF, not our extractor, and there is
no external corroboration. Hasan ruled Option A. Recovered by a tolerant anchor
that validates all three intact components (prefix, subcategory resolving to a
real heading, well-formed number), corroborated by the GOVERN 4.3 heading above
and GV-4.3-002 below. Stored text keeps "GV4.3--001" verbatim so the
exact-substring assertion holds; only the derived key is normalised to
act_GV-4.3-001. Recorded in the manifest as a single documented exception, with
the resulting lexical-mismatch case (a query for GV-4.3-001 will not match the
stored surface) in downstream_notes for the retrieval step. Tests pin that the
tolerant pattern recovers exactly this one row beyond strict, the total is 212,
no duplicate ids exist, and the recovery fills the numbering gap. GV-1.1-002 in
the prose is only the ID-scheme example; GOVERN 1.1 has one real action.

### Forward-reference gate, enforced and passing

IDs derived mechanically from each document's own printed identifiers, no
adjustment to match the prediction. AI 100-1's structural_join decomposes to
exactly 72 Playbook targets and 49 AI 600-1 targets, and every one resolves to a
real unit. The reverse joins (98 and 72), all 95 duplication targets and all 212
action-to-subcategory edges resolve. Enforced by tests in
tests/test_forward_references.py that fail loudly.

### Structure and partition

- AI 600-1: 287 units (212 action, 49 subcategory, 15 section, Appendix A with 9
  numbered subsections, Appendix B as References), 308 chunks. Partition closes
  over 162,204 raw chars, discard classes front_matter and the new table_header,
  the 48-page "Action ID Suggested Action GAI Risks". Action-to-subcategory is
  its own field, 212 edges. tokens 7 to 512, none over cap.
- Playbook: 436 units (72 Core statements separate from their five blocks each,
  4 function intros), 455 chunks. Partition closes over 341,715 raw chars, discard
  classes front_matter and the new positional page_footer "N of 142". References
  blocks chunked and tagged as playbook_references, not excluded. tokens 10 to
  511, none over cap.
- Exact-substring assertion holds on every chunk in both, deterministic
  byte-identical reruns confirmed.

### A structural bug in the draft, found and fixed

The AI 600-1 draft anchored only numbered sections, subcategories and actions, so
Appendix A ("Primary GAI Considerations") and Appendix B (the References
bibliography) were folded into the last action, MG-4.3-003, which became a giant
mis-tagged unit. Fixed by anchoring the appendices and Appendix A's numbered
subsections, and tagging Appendix B as References. MG-4.3-003 is now one chunk and
the bibliography is 12 chunks under app_B.

### Hyphenation agreement, the remaining 98 decisions

AI 600-1 44 applied, 0 conflicts. Playbook 54 applied, 0 conflicts. Both agree
exactly with the committed decision log, completing the 337. Neighbour extraction
is per unit, attestation is corpus-wide, as the committed decisions require. All
98 are kept, matching the log's own split for these two documents.

### Duplication map did NOT move

Still 48 and 47, no-twin 11, unchanged. AI 100-1's haystacks resolve the raw
600-1 and Playbook text directly, which was already the corrected text from the
previous step and is independent of these ingesters, so ingestion cannot move it.
Stated explicitly as requested: no movement, so no stated correction this time.

### Prose references and the non-ASCII ruling

Three classes, every reference audited in full. AI 600-1: 11 content references
audited (the other 2 of the raw 13 are Appendix references in the discarded
front-matter table of contents). Playbook: 1, "ISO/IEC CD 5339. See Section 6",
external. Both demonstrated collisions classify correctly, and a false positive
where a following "AI RMF" clause had flipped AI 600-1's own Appendix A to
cross-document was caught and fixed by requiring the instrument to be connected to
the reference. The comparison-time normalisation ruling (curly quotes and
apostrophe to ASCII, en and em dash to hyphen, non-breaking space to space,
whitespace collapsed, both sides, never on stored text) and a per-document
non-ASCII inventory with leave-alone items marked deliberately excluded are
recorded in downstream_notes of all three NIST manifests, with
normalise_for_comparison in code. AI 100-1 was re-run only to add this note.

Commit: 40ffc2b
  (feat: structure-aware ingestion of NIST AI 600-1 and the Playbook with the
  wired resolver, local only)
  This entry is recorded by the next commit, `docs: log AI 600-1 and Playbook
  ingestion commit, local only`, committed immediately after this entry is
  written, which closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-four commits, all trailer-free.
- Ingested and verified: the EU AI Act, and all three NIST documents, AI 100-1,
  AI 600-1 and the Playbook, with the hyphen resolver applied and the
  cross-document reference graph fully resolving. 164 tests pass, ruff clean.
- No retrieval, no query set, no gold passages, no results yet.

Next step:
- Phase 1 continues with retrieval, then the query set and gold passages, then
  the immutable pre-registration commit that must predate any generation run. The
  duplication map (48 and 47) and the cross-document reference graph are the
  corpus-derived inputs to gold-passage definition. When retrieval and grounding
  are built, apply the recorded comparison-time normalisation on both sides, and
  treat the GV-4.3-001 lexical-mismatch as a known case rather than a designed
  query trap.

## 2026-07-23, hyphenation defect FIXED in AI 100-1 applied output, non-ASCII sweep closed

The hyphenation defect is now corrected in applied document output, not just in
the resolver. AI 100-1 was re-run with the wired resolver and committed. AI 600-1
and the Playbook are the remaining ingestion work, deliberately deferred to the
next step from this clean commit.

### What was wired

`src.ingest.hyphenation.resolve` replaced the per-line `join_soft_hyphens` in the
AI 100-1 ingester. It runs per unit, so a word split across a page boundary
rejoins across the discarded footer and running header, and on the cross-document
haystacks used for duplication and structural_join, so hyphen resolution is
consistent on both sides of every match. Attestation stays corpus-wide:
`resolve` reads `evidence_text` over all three PDFs regardless of the text passed,
so it was not degraded to per-document or per-line evidence. `pdf_extract`'s
`soft_hyphen_rule` fingerprint was updated from "delete U+FFFE" to record that
the resolver decides it.

### Agreement with the committed decision log

The applied result agrees with the committed corpus-wide decision log exactly:
231 content-region decisions, zero conflicts, and the 8 log decisions not applied
are markers in discarded front matter and headers that never reach a unit. A test
pins this. No decision changed between the reviewed log and the applied output.

### What moved in the output

Exactly 12 occurrences changed, in 12 chunks: 10 hyphens now preserved and 2
page-boundary splits rejoined ("example" at page 15, a de-word at page 36). Net
+8 characters. The five confirmed corrupted words are gone and their hyphenated
forms present: third-party, decision-making, human-AI, privacy-enhancing,
context-specific. Five more of the same class were also corrected:
context-relevant, cost-effective, high-or, off-label, on-going.

- Unchanged and byte-identical: extracted.txt and relations.jsonl. structural_join
  stayed 121 (72 Playbook, 49 AI 600-1), prose_xrefs 6 emitted and 32 dropped.
- No chunk IDs moved, no split boundary moved, chunk count still 134, units 121.
  Twelve chunks' token counts shifted by 1 or 2 but no block crossed a split
  boundary. Partition still closes over raw_chars 107702.

### Stated correction, the duplication map moved

Resolving line-break hyphens consistently on both the statements and the target
documents revealed two true duplications the old delete-the-hyphen rule had
hidden. duplicated_in_playbook 47 -> 48, MEASURE 4.3 now matches the Playbook via
"context-relevant". duplicated_in_ai_600_1 46 -> 47, MAP 1.1 now matches AI 600-1
via "context-specific". no_near_miss_twin 13 -> 11. duplicated_in_both unchanged
at 34. The two pinning tests, test_duplication_uses_full_statement_not_prefix_matching
and test_subcategories_without_a_near_miss_twin_are_named, were updated to 48/47
and 11 with the reason recorded in their docstrings. This is a corpus-derived
input to pre-registration, and it surfaced BEFORE pre-registration, so it can
still move freely; had it surfaced afterwards the pre-registration would be void.

### Non-ASCII sweep closed, one item flagged for ruling

Swept all three extracted texts. 23 distinct non-ASCII codepoints, every one
classified. Nothing needs a new ingestion rule. Genuine and preserved: the
accented Latin letters and the registered sign in Playbook author names, U+FFFE
(now resolved), the parrot in a cited title, en and em dashes, curly quotes, the
bullet and almost-equal signs. No space-family surprise: the NIST PDFs carry no
U+00A0, unlike the EUR-Lex HTML.

One item carries an assumption not yet examined: the quote and dash families,
curly apostrophe U+2019, curly double quotes U+201C and U+201D, and en and em
dashes, will silently break lexical matching if a query or a grounding check uses
an ASCII apostrophe or hyphen against them. This is a COMPARISON-TIME
normalisation decision for the retrieval and grounding phase, analogous to the
whitespace note already in the manifest, not an ingestion-time alteration of
source text. Nothing was applied and nothing was decided; it is left for Hasan to
rule on when retrieval is built.

Commit: 7434920
  (fix: apply hyphen resolver to NIST AI 100-1 output, correcting the thirdparty
  defect class, local only)
  This entry is recorded by the next commit, `docs: log AI 100-1 hyphen fix
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-two commits, all trailer-free.
- Ingested and CORRECT: the EU AI Act, and NIST AI 100-1 with the hyphenation
  defect now fixed in its applied output. NOT ingested: AI 600-1 and the Playbook.
- The wordlist is vendored and pinned, the resolver is wired and applied to
  AI 100-1, and the corpus-wide decision log is committed and agrees with the
  applied result.

Next step:
- Ingest AI 600-1 and the Playbook with the corrected resolver, from this clean
  commit. The eight untracked draft files (nist_pdf_common.py, nist_playbook.py,
  nist_ai_600_1.py, and the stale data/chunks/nist_playbook.* outputs) are to be
  reworked against the wired resolver, not trusted as-is. AI 600-1 has two
  non-letter U+FFFE cases the resolver keeps as real hyphens, so its
  find_unjoinable_breaks precondition must be reconsidered rather than left to
  raise. Enforce the forward references: the structural_join must decompose to
  72 for the Playbook and 49 for AI 600-1 against the newly ingested units, and
  the duplication map targets must resolve. Add the regression tests pinning the
  defect class at the ingester level for those two documents. Separately, when
  retrieval is built, rule on comparison-time normalisation of the quote and dash
  families surfaced by the non-ASCII sweep.

## 2026-07-23, hyphen resolver wired and decision log committed, last hyphenation round

Hasan reviewed the decision log from the previous entry and ruled. The resolver
wiring, its refinement, its tests and the decision-log artifact are now committed.
This is the last hyphenation round. The next step is a fresh, separate build.

### The ruling and its refinement

Keep both ambiguous compounds, round-trip and non-inclusive, and reach that
mechanically rather than by hand. The pattern he identified: a syllable break
always leaves at least one fragment that is not a word ("cooper" + "ation",
"nonethe" + "less"), whereas a genuine compound has both fragments as words
("round" + "trip"). Against the wordlist, unlike against the 597k-character
corpus where every fragment appears somewhere, that test separates the two
populations cleanly.

Tier four now has three outcomes, the third labelled distinctly as a tie-break
rather than evidence:
- joined form not a word, keep the hyphen;
- joined a word with a non-word fragment, delete as a syllable break;
- joined a word with both fragments words, keep as an ambiguous compound.

`non` was confirmed present in the SCOWL build, so non-inclusive resolves to keep
mechanically and needed no separate ruling.

### Prediction confirmed

His prediction held exactly. Only two occurrences moved, round-trip and
non-inclusive, both DELETE to KEEP via the tie-break. The eight AI 100-1
syllable breaks were untouched, each having a non-word fragment. Tiers 1, 2, 3
and 5 are unchanged; only tier four's internal split moved, from 10 delete and 45
keep to 8 delete, 45 keep (joined not a word) and 2 keep (ambiguous compound).

### Decision log across all 337

Committed as an audit artifact, not ingestion output:
- tier 1 non-letter neighbour 2, tier 2 corpus attestation one direction 273,
  tier 3 both attested Group A 7, tier 4 wordlist 55, tier 5 unresolved 0.
- Per document: AI 100-1 239 (tier2 228, tier3 1, tier4 10), AI 600-1 44
  (tier1 2, tier2 20, tier3 1, tier4 21), Playbook 54 (tier2 25, tier3 5,
  tier4 24).
- AI 100-1's tier 4 is 10 and its tier 3 is 1 (on-going), reconciling exactly
  with the handoff residue, a strong wiring signal. The three cases Hasan named,
  Al-Ghoneim, all eight Self-Assessment occurrences, and Web-Crawled, all resolve
  to keep. The URL and citation-slug hyphens in the AI 600-1 and Playbook
  reference sections land in tier 4 and are correctly kept, which explains the
  count of 55 rather than a smaller prose-only residue.

### Known limitation recorded

A syllable break whose two fragments both happen to be words, "the" + "rapist"
for "therapist", is wrongly kept by the tie-break. That fails in the safe
direction, a spurious hyphen rather than two welded words. Recorded in both
`src/ingest/hyphenation.py` and `corpus/SOURCES.md`.

### What is committed at 99c4cd3

- `src/ingest/hyphenation.py`: wordlist wired as evidence source four with the
  fragment-test refinement in `_resolve_by_wordlist`, three distinctly labelled
  outcomes, docstring updated.
- `src/ingest/hyphenation_report.py`: runs the resolver over all three documents
  and writes the decision log. Faithful assembly: AI 100-1's two page-boundary
  interruptions are collapsed from the committed constants so all 239 of its
  markers keep correct fragments, and AI 600-1 and the Playbook, which have no
  such case, run on raw text, so all 337 occurrences are covered.
- `data/hyphenation/decision_log.jsonl` (337 rows) and
  `data/hyphenation/decision_log.summary.json`, the reviewed artifact.
- `corpus/SOURCES.md`: the wordlist known-limitation refined to the three-way
  logic and the the-rapist failure mode.
- `tests/test_hyphenation.py`: the three wordlist outcomes, the the-rapist
  failure mode, all eight syllable breaks deleting and both ambiguous compounds
  keeping, end-to-end resolves, and byte-identity of the committed decision log.
  129 tests pass, ruff clean.

### Constraints honoured

No document ingestion was re-run. The eight untracked files were not touched. No
API calls, no spend, no remote, nothing pushed.

Commit: 99c4cd3
  (feat: wire wordlist tier into hyphen resolver with fragment test, commit
  corpus decision log, local only)
  This entry is recorded by the next commit, `docs: log hyphen resolver wiring
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty commits, all trailer-free.
- Ingested: the EU AI Act (clean), NIST AI 100-1 (its committed output STILL
  carries the corrupted words: the corrected resolver is wired and proven but has
  NOT been applied to any document output yet). NOT ingested: AI 600-1 and the
  Playbook.
- The wordlist is vendored and pinned, the resolver is wired and its behaviour
  across all 337 occurrences is committed as a reviewed decision log. Hyphenation
  is done.

Next step:
- A fresh, separate build, started from this clean commit rather than bundled
  onto the end of it: apply the wired resolver to all three documents. Wire
  `hyphenation.resolve` into the ingesters replacing the per-line
  `join_soft_hyphens`, re-run AI 100-1, and complete AI 600-1 and Playbook
  ingestion, with the forward-reference validation, the regression tests pinning
  the thirdparty class at the ingester level, and the non-ASCII sweep. The eight
  currently untracked draft files belong to that build and are still to be
  reworked against the corrected resolver, not trusted as-is. Report any movement
  in the 47 and 46 duplication counts as a stated correction.

## 2026-07-23, wordlist vendored and builder committed, resolver wiring reported not committed

Hasan ruled the wordlist choice this session and it is now committed. The
resolver wiring and the decision-log run follow immediately in the same session
but are deliberately left UNCOMMITTED and applied to no document, for his review
of the wordlist-resolved decisions before anything touches a document.

### The ruling

SCOWL, American English, size levels 10 through 70, vendored as the as-served
component files plus a builder rather than a pre-built list. Three changes from
the recommendation, each with stated reasoning:
- Level 70 rather than 60. The two failure directions are not symmetric. A
  coverage miss keeps a hyphen inside an ordinary word and ships "cooper-ation",
  the visible corruption we are removing. A false positive deletes a real hyphen
  and ships "thirdparty", the original defect, but that direction is
  structurally protected below level 80: proper names live in separate files and
  compounds do not enter until 95, so "alghoneim" and "webcrawled" cannot appear
  at any level used. The coverage direction has no such protection, and NIST
  prose is technical vocabulary, so 70 buys inflection headroom at no measured
  false-positive cost. All 20 false-positive probes stay clean at 70.
- As-served components plus a builder, not a pre-built file. This reproduces the
  pattern the repo already runs: corpus raw is as-served and immutable, the
  built list is derived and reproducible from committed code, and both are
  checksummed. A pre-built file with a prose recipe would make a single
  hand-edited word undetectable.
- Skip the possessive-stripping refinement. Not worth a fifth transformation,
  and it has an edge case: a line break inside a possessive, "manag-er's", would
  look up "manager's" and fail if possessives were stripped.

web2, the macOS Webster's Second 1934 list, was rejected on measured coverage
rather than reputation, and that rejection is recorded in SOURCES.md with its
evidence, so the obvious local option is shown disqualified on data.

### What is committed at 73f22f2

- vendor/scowl/, the 16 english-words and american-words component files at
  levels 10 to 70 as served, plus the Copyright file verbatim to carry the
  component notices. Level 80 excluded deliberately: UKACD's "All Rights
  Reserved" terms and the compound-word false-positive surface both begin there.
  Every component used at 10 to 70 is public domain or permissive, license read
  from the vendored Copyright rather than from memory.
- src/ingest/wordlist.py, the deterministic builder: concatenate, lowercase,
  deduplicate, sort by code point, UTF-8, one word per line. No other
  transformation. The derived list en-american.10-70.lower.txt is 135,951
  entries, 1,361,427 bytes.
- corpus/SOURCES.md gained the full SCOWL section: provenance, source tarball
  checksum, per-file checksums, license, the exact recipe, the deliberate
  level-80 exclusion, the derived-versus-as-served distinction, and the web2
  rejection table.
- tests/test_wordlist.py: rebuild byte-identity, all-lowercase, coverage of the
  residue cases, and absence of the compound and proper-name joined forms.
- verify_vendor now pins all 22 vendored files, 4 tokenizer and 18 SCOWL. 119
  tests pass, ruff clean.

### What follows in-session, uncommitted, reported to Hasan before it is applied

Per his instruction the resolver wiring is left in the working tree, uncommitted,
and applied to no document output. hyphenation.resolve consults the wordlist as
evidence source four in the neither-attested branch, lowercasing the joined form,
with two distinctly labelled outcomes: joined form present means discretionary
hyphen, delete; joined form absent means real hyphen, keep. The resolver is run
across all 337 U+FFFE occurrences corpus-wide (AI 100-1 239, AI 600-1 44,
Playbook 54), and the decision log by evidence tier plus the complete
wordlist-resolved list are reported to Hasan in the session. Nothing of the
wiring or the report is committed; the modified hyphenation.py sits uncommitted
in the working tree, so a fresh session sees it in git status and can regenerate
the decision log by re-running the resolver.

### Constraints honoured

No document ingestion re-run. The eight untracked files were not touched. No API
calls, no spend, no remote, nothing pushed.

Commit: 73f22f2f96ddbb580a575a69c68a96bd30826eb1
  (feat: vendor SCOWL English wordlist and deterministic builder for hyphen
  resolver, local only)
  This entry is recorded by the next commit, `docs: log wordlist vendoring
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is eighteen commits, all trailer-free.
- Ingested: the EU AI Act (clean), NIST AI 100-1 (still carrying the corrupted
  words, since the corrected resolver is not yet applied to any document). NOT
  ingested: AI 600-1 and the Playbook.
- The wordlist is vendored and pinned. The resolver wiring exists in the working
  tree, uncommitted, pending Hasan's review of the wordlist-resolved decisions.

Next step:
- On Hasan's go after he reviews the wordlist-resolved decisions, commit the
  resolver wiring with its tests, then apply the corrected resolver in the full
  three-document re-run: wire hyphenation.resolve into the ingesters, re-run
  AI 100-1, and complete AI 600-1 and Playbook ingestion, committing the full
  per-occurrence decision log, the regression tests pinning the thirdparty
  class, the non-ASCII sweep, and the forward-reference validation. Report any
  movement in the 47 and 46 duplication counts as a stated correction.

## 2026-07-22, HANDOFF, hyphen defect found and partially corrected

Read this entry in full before doing anything. A defect was found in ALREADY
COMMITTED output, it is only partially corrected, and the work is unfinished.
Ingestion part three is NOT done.

### The original defect, and why the check that was supposed to catch it did not

PDFium encodes a hyphen falling at a line break as U+FFFE, a Unicode
noncharacter. The first NIST ingestion used this rule: delete U+FFFE, and
validate that a letter sits on both sides. The precondition looked like a safety
check but was not one. A REAL hyphen in a compound such as "third-party" also
has letters on both sides, so deleting produced "thirdparty".

Confirmed corrupted in the AI 100-1 output committed at 906caab: thirdparty,
decisionmaking, humanAI, privacyenhancing, contextspecific, one occurrence each,
against 20, 10, 11, 2 and 3 correct occurrences of the hyphenated forms
elsewhere in the same document. Corpus-wide the class affects roughly 5
occurrences in AI 100-1, 19 in AI 600-1 and 29 in the Playbook.

The exact-substring assertion could NOT catch this. The corrupted text is
faithfully carried from extraction into the chunk, so the chunk is a true
substring of the extracted text. Only cross-document evidence exposed it. That
is worth remembering: the assertion proves no text was invented, it does not
prove the text is right.

### The second defect, ordering between discard removal and normalisation

Hyphen resolution originally ran on RAW text, before discard lines were removed.
A word split across a PAGE boundary has its continuation after the page footer
and the running header:

    "...for exam<U+FFFE>Page 15 \f NIST AI 100-1 AI RMF 1.0 ple, how a human..."

Reading neighbours from raw text yields "exam" and "Page" instead of "exam" and
"ple". Constraining neighbours to one physical line would NOT fix this, because
the continuation legitimately lives on the next page. The fix is ordering:
resolution must run on text already assembled from CONTENT lines.

A related discovery: the page footer is normally its own line, but twice in
AI 100-1 PDFium appends it to the end of a content line, so line-level discard
cannot catch it. A positional tail-strip was added, and the stripped characters
are still accounted to the page_footer discard class. Only 2 such cases exist
in the whole corpus, both in AI 100-1. AI 600-1 and the Playbook have none.

### What is COMPLETE and committed at 2522fea

- `src/ingest/hyphenation.py`, the corrected rule module. Symmetric evidence in
  both directions, corpus-wide attestation with every line-break hyphen masked
  so no occurrence is evidence about itself, and NO silent default. Not yet
  wired into any ingester.
- The footer tail-strip in `src/ingest/nist_ai_100_1.py`, with the partition
  accounting corrected so that content plus discards still equals line_chars and
  raw minus line_chars still equals structural whitespace. Both invariants pass.
- AI 100-1 re-run so its committed data matches its code. Its duplication counts
  did NOT move: still 47 for the Playbook and 46 for AI 600-1.
- 111 tests pass, ruff clean.

IMPORTANT: the hyphen fix is NOT yet applied to any document. AI 100-1's
committed output STILL CONTAINS thirdparty, decisionmaking, humanAI,
privacyenhancing and contextspecific. The corrected module exists but is unwired.

### What is NOT done

- The full three-document re-run with the corrected hyphen rule.
- AI 600-1 and Playbook ingestion. Draft modules exist but are UNCOMMITTED and
  half-finished: `src/ingest/nist_pdf_common.py`, `src/ingest/nist_playbook.py`,
  `src/ingest/nist_ai_600_1.py`, plus stale `data/chunks/nist_playbook.*`
  outputs produced with the OLD hyphen rule. Do not trust those outputs.
  AI 600-1 currently raises on the U+FFFE precondition, which is correct
  behaviour, not a bug to suppress.
- The non-ASCII sweep across all three extracted texts.
- Regression tests pinning the thirdparty class of defects.
- The forward-reference validation of AI 100-1's duplication map and
  structural_join against the newly ingested Playbook and AI 600-1 units.

### Hasan's ruling on the unresolved residue, which supersedes an earlier one

After the ordering fix, AI 100-1 has 11 occurrences where corpus attestation is
silent in both directions. They are ordinary words that happen to occur exactly
once in the corpus, at a line break: em-phasize, cooper-ation, illus-trated,
formal-ized, man-agers, devel-opments, quanti-ties, Nonethe-less, high-or,
cost-effective, plus on-going where both forms are attested.

Hasan's earlier tie-break, prefer the hyphenated form, holds for Al-Ghoneim and
Self-Assessment and INVERTS for mid-word syllable breaks, where the joined form
is the real word. He has withdrawn it for this sub-case. Do not hand-rule the
list and do not use a capitalisation heuristic. Two mechanical discriminators
were tried and both failed: corpus attestation is zero in both directions, and
fragment attestation returns hyphen for everything because every fragment has
some attestation somewhere in 597,496 characters.

The ruling is to add a FOURTH evidence source: an English wordlist, vendored
into the repository with a recorded license and checksum, under the vendor
verifier exactly like the tokenizer. The reasoning to preserve: a committed
wordlist is not the model's knowledge of English, it is a deterministic external
artifact anyone can reproduce and audit, so looking up whether "cooperation"
appears in a specific committed file is a mechanical lookup rather than a
recollection. That is why it does not violate the no-reconstruction rule the way
morphological judgment would.

Evidence order, wordlist LAST and only where the earlier sources are silent:
  1. non-letter neighbour, real hyphen, structurally decisive;
  2. corpus attestation in exactly one direction, take that direction;
  3. both attested, keep the earlier Group A ruling, prefer hyphenated and
     record that both forms are attested;
  4. neither attested, the wordlist decides. Joined form present in the
     wordlist means the hyphen was typesetting, so delete. Joined form absent
     means the hyphen was real, so keep it.
  5. anything still unresolved goes to Hasan by hand, expected to be nearly empty.

Two constraints recorded with it. Label wordlist-resolved decisions distinctly
from attestation-resolved ones in the decision log, so the strength of evidence
behind each is visible rather than flattened. And record the known limitation:
where a genuinely hyphenated compound occurs exactly once and its joined form
happens to be a dictionary word, the wordlist will wrongly delete the hyphen.
Corpus attestation catches that whenever the compound appears anywhere else, so
the exposure is narrow, but it must be stated rather than discovered.

The wordlist is to be chosen in the fresh session. It must be permissively
licensed and redistributable, verified from its actual license file rather than
from memory, the same standard applied to the corpus and the tokenizer. If
nothing suitable is redistributable, STOP and tell Hasan rather than committing
it.

### Fix forward, no history rewrite

Hasan's explicit ruling: correct the rule, re-run all three documents, and fix
forward with a new commit. Do not rewrite history and do not amend the AI 100-1
commits. Rule 10 is spent and no further exception is invoked. The history
should show that the defect existed, was caught by the system's own check, and
was corrected in the open. He intends to write that into the README.

Timing note he asked to be recorded: this surfaced BEFORE pre-registration, so
the duplication map can still move freely. Had it surfaced afterwards the
pre-registration would have been void.

If the duplication counts move from 47 and 46 during the re-run, report the new
numbers with the reason and update the pinning tests as a STATED correction in
the commit message and this log, never as a silent adjustment.

Commit: 2522fea717acf54d0f84c0eec168234147de1954
  (fix: correct hyphen-join neighbour extraction and footer tail-strip, partial,
  local only)
  This entry is recorded by the next commit, `docs: log hyphen defect checkpoint,
  local only`, committed immediately after this entry is written, which closes
  the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is sixteen commits, all trailer-free.
- Ingested: the EU AI Act (clean), NIST AI 100-1 (ingested but its text still
  carries the five corrupted words listed above). NOT ingested: AI 600-1 and the
  Playbook.

Next step:
- Choose and vendor a permissively licensed English wordlist, verify its license
  from the actual license file, record it in `corpus/SOURCES.md` under vendored
  dependencies with its checksum, and bring it under the vendor verifier. Then
  wire `hyphenation.resolve` into all three ingesters, re-run all three
  documents, commit the full decision log for every U+FFFE occurrence with its
  neighbours, evidence counts, the rule that fired and the outcome, add the
  regression tests, run the non-ASCII sweep, and complete AI 600-1 and Playbook
  ingestion with the forward-reference validation.

## 2026-07-22, checkpoint before ingestion part three

What changed:
- Recorded in the AI 100-1 partition proof why two of its structural whitespace
  classes carry the same number. `intra_page_newlines` and
  `stripped_line_whitespace` are both 1,373 by construction, not by
  coincidence: PDFium emits exactly one trailing space on every line except the
  last line of each page, and never a leading space. The observed padding
  distribution is 1,373 lines with one trailing space and 48 with none, the 48
  being the page-final lines, so both counts equal total lines minus page count.
  A test asserts the equality and the recorded explanation.
- Hasan asked for this so a future reviewer seeing two identical numbers does
  not have to wonder whether one was copied from the other.
- 111 tests pass, ruff clean. The extractor dependencies, pdfplumber and
  pypdfium2, were already committed with the AI 100-1 ingestion commit.

Why:
- Committed as its own checkpoint before ingestion part three, which is a
  substantial build covering two documents. Starting that build from a clean
  tree rather than carrying an uncommitted fix into it, because a long run with
  loose ends is where a rushed tail becomes likely.

Investigation completed this session, carried into part three:
- AI 600-1 prose references number 13, ten `Appendix X`, two `Section`, one
  `Figure`, against 212 Action IDs which are structural rather than prose. The
  Playbook has one. The combined population of 14 is audited exhaustively, so no
  separate step is warranted, unlike the EU AI Act's roughly 721 references.
- Collisions do exist here, so classification is mandatory and needs THREE
  classes rather than two: internal, resolving within the same document;
  cross_document, resolving to a unit in another corpus document, recorded with
  the target's real unit id; and external, pointing outside the corpus, recorded
  with the named instrument and no edge emitted. Two collisions are already
  demonstrated: "Section 4.1(a)(i)(A) of EO 14110" is external, and "See
  Appendix A of the AI RMF" resolves to AI 100-1's Appendix A, which is a real
  unit in our own corpus and would be lost if collapsed into either other class.
- The Playbook has five top-level blocks per subcategory, not six. "About",
  "Suggested Actions", "Transparency & Documentation", "AI Transparency
  Resources" and "References". "Organizations can document the following"
  appears 72 times but is a sub-label inside Transparency & Documentation.
- Two further discard classes are needed: the Playbook's `N of 142` page footer,
  which appears mid-content between bullets so the discard must be positional
  and must not join text across the boundary, and AI 600-1's repeated
  `Action ID Suggested Action GAI Risks` table header on 48 pages.

Commit: 894ce480de1091723c97fdfdfc34e9f2dfef6a08
  (docs: record why two partition whitespace classes are equal, local only)
  This entry is recorded by the next commit, `docs: log partition whitespace
  note commit, local only`, committed immediately after this entry is written,
  which closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is fourteen commits, all trailer-free.
- Ingested and verified: the EU AI Act, and NIST AI 100-1. Not yet ingested:
  NIST AI 600-1 and the AI RMF Playbook.

Next step:
- Ingestion part three, AI 600-1 and the Playbook together, under the same rules
  as part two. Playbook Core statements are separate units from their five
  blocks, References blocks are chunked and tagged rather than excluded, the
  Action ID to subcategory relation is its own field, and the forward references
  that AI 100-1 already committed, the duplication map targets and the
  structural_join edges, must all resolve against the newly ingested units, with
  the join decomposing to exactly 72 for the Playbook and 49 for AI 600-1. Those
  are enforced as tests that fail loudly. Ids are derived by the same mechanical
  rule used in AI 100-1, from each document's own printed identifiers, with no
  adjustment to match the prediction; a mismatch is a finding to report, not to
  reconcile.

## 2026-07-22, Phase 1 ingestion part two, NIST AI 100-1

Ingestion of the three NIST PDFs is split. This is part two, AI 100-1 alone.
Part three is AI 600-1 plus the Playbook. AI 100-1 was separated because the
risk is concentrated in it: it carries the Core tables that are the join spine,
it mixes narrative and tabular content, and it is the document the rejected
extractor fails on.

Extractor decision, made on evidence rather than habit:
- PyMuPDF was rejected before testing because it is AGPL-3.0 or commercial,
  which does not fit an Apache-2.0 public repository.
- Two independent permissively licensed engines were compared against the real
  files, pdfplumber with pdfminer.six (MIT, pure Python) and pypdfium2 (BSD-3
  and Apache-2.0, Google's PDFium in C++). Agreement was measured two ways,
  order-sensitive and order-blind, because the distinction turned out to matter.
- pdfminer.six is materially WRONG on AI 100-1, a pdfTeX-produced document. It
  emits page 16 reversed, "AxidneppAeeS" for "See Appendix A", and drops
  inter-word spaces across the document, 548 run-together tokens of 25
  characters or more against 4 from PDFium. It reported success on all 48 pages,
  zero empty pages, no error. Poppler's pdftotext was used as an independent
  third engine to break the tie and agrees with PDFium.
- pypdfium2 is the extractor of record. Its version and the PDFium build are
  pinned in the manifest for the same reason the tokenizer is, and the raw
  extracted text is committed so extraction is auditable without re-running.
- The defect is pinned as a regression test, so reversing this decision requires
  deleting a failing test and justifying it.

Three guarantees replace the ELI anchors a PDF cannot provide:
- Anchors are validated against the document's own Table of Contents. A heading
  is accepted only if the document declares it, which also excludes the
  enumerated list items in Appendices C and D that look exactly like section
  headings but appear in no TOC. All 30 declared entries were located.
- Partition proof, covering the FULL raw extraction, 107,702 characters:
  97,857 content assigned to units, 6,958 discarded across four named classes
  (front_matter 4,771, running_header 984, table_continuation 932, page_footer
  271), and 2,887 structural whitespace (1,373 intra-page newlines, 1,373
  stripped line padding, 141 page separators). Zero unassigned content lines,
  zero lines assigned twice, and the accounted total equals the raw total
  exactly. Discarded text stays in the committed extraction, so nothing leaves
  the audit trail.
- Every chunk's text must be an exact substring of the persisted text at its
  recorded offsets. This is what makes the no-reconstruction rule enforced
  rather than promised: any sentence not originating in the PDF fails it
  mechanically.

Structure and chunks:
- 121 units: 72 subcategory, 19 category, 23 section, 4 appendix, 2 part, 1
  named section. Subcategories are 72, distributed GOVERN 19, MAP 18,
  MEASURE 22, MANAGE 13, derived from the document.
- 134 chunks, 10 units split, all ids unique, none empty, none over the cap.
  Tokens min 8, median 39, max 512, counted with the same pinned tokenizer and
  the same convention as part one, including the [CLS] and [SEP] special tokens,
  so 512 is the model's real ceiling rather than 514 at embedding time.
- Chunk ids derive from printed identifiers, never position:
  `nist_ai_100_1:sub_GOVERN_1.1`, `:sec_1.2.1`, `:app_A`, splits as `#p2`.
- Line breaks from the PDF are preserved rather than reflowed into paragraphs,
  because guessing paragraph boundaries can join text wrongly. The consequence
  is recorded in the manifest: all whitespace including newlines must be
  normalised on BOTH sides before any grounding comparison and identically for
  BM25 tokenisation, at comparison time only, never applied to stored text.

Relations, kept in separate fields:
- structural_join, 121 edges, decomposing as 72 to the Playbook and 49 to
  AI 600-1, which independently reproduces the coverage counts found during
  investigation. Exact, identifier-based, no regex risk.
- prose_xrefs, 6 emitted and audited in full, all correct, plus 32 drops each
  carrying a reason and sentence, 20 figures and 12 self-references. The
  population here, 38 references over a vocabulary that never collides with the
  external ISO, IEC and OECD citations, is not comparable to the EU AI Act, so
  no separate audit step was needed. AI 600-1's 212 Action IDs may differ and
  will be re-assessed in part three rather than assumed.

Duplication map, corpus-derived input to pre-registration:
- 72 rows. 47 Core subcategory statements appear verbatim in the Playbook, 46 in
  AI 600-1, 34 in both, and 13 in neither. The 13 with no near-miss twin are
  named explicitly, since they behave differently in the distractor bucket.
- The matching method is recorded in the manifest precisely enough to
  reproduce: full-statement exact match over a match form, not a prefix match.
  A 12-word-prefix variant of the same method yields 56 and 48 instead.
- Earlier investigation figures of 41 and 36 came from a different method,
  prefix matching over statements taken from unfiltered raw text that still
  contained running headers and unjoined hyphens. The committed method is the
  stricter one.
- AI 600-1 covers only 49 of the 72 subcategories, recorded in the manifest,
  because any assumption that all three documents share one subcategory set is
  wrong.
- Duplication is kept, not removed. It is the corpus's best near-miss trap.
  Gold sets are defined at unit level and may name several acceptable units, and
  where a statement is genuinely duplicated any carrier satisfies the gold. The
  exception is a query about what the Playbook adds beyond the Core statement,
  which the Core unit does not satisfy.

Known property recorded for the retrieval step: this document is strongly
bimodal by length, 72 of 121 units being one or two line statements against
narrative sections reaching the cap. Authentic to the document and deliberately
unchanged, but length normalisation is to be examined deliberately at retrieval
rather than discovered through a strange result.

Normalisation applied: deletion of U+FFFE, a Unicode noncharacter PDFium emits
for a discretionary hyphen at a line break, which rejoins the split word. All
239 occurrences have a letter on both sides, and the precondition is asserted
before any deletion. No ligatures, soft hyphens or non-breaking spaces are
present. The Playbook's parrot character is genuine, part of a cited paper
title, and is not to be cleaned.

Why:
- Chunk ids freeze here and are cited by pre-registered gold passages. A PDF
  declares no structure, so the invariants above are what make silent content
  loss and text reconstruction detectable rather than merely unlikely.
- 110 tests pass, ruff clean. No API calls, no spend, no remote, nothing pushed.

Commit: 906caab0cd44c188e7ca51b7a8d144a571ccadac
  (feat: structure-aware NIST AI 100-1 ingestion with partition proof, local only)
  This entry is recorded by the next commit, `docs: log NIST AI 100-1 ingestion
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twelve commits, all trailer-free.
- Ingested and verified: the EU AI Act, and NIST AI 100-1. Not yet ingested:
  NIST AI 600-1 and the AI RMF Playbook. No retrieval, no query set, no gold
  passages, no results yet.

Next step:
- Ingestion part three, AI 600-1 and the Playbook, into the same schema. AI
  600-1 carries 212 printed Action IDs and page-spanning action tables with a
  repeated header, and covers only 49 subcategories. The Playbook is the most
  regular of the three, 72 subcategory sections each with the same printed
  sub-blocks. Re-assess whether prose_xrefs there needs the EU AI Act's audit
  depth rather than assuming it does not.

## 2026-07-22, integrity verifier extended to vendored files

What changed:
- `verify_vendor` and `verify_all` added to `src/ingest/corpus_integrity.py`.
  The verifier now checks the vendored tokenizer files under `vendor/` against
  their checksums in `corpus/SOURCES.md`, alongside the corpus. Ingestion calls
  `verify_all` and refuses to run on any mismatch. Corpus and vendor rows are
  parsed separately because they resolve against different roots.
- Three tests added, including a swapped-tokenizer case. 65 tests pass, ruff
  clean, 10 integrity checks: 6 corpus, 4 vendor.
- Ingestion output is byte-identical to the previous commit, so this is
  enforcement only, not a change to any artifact.

Why:
- The chunking tokenizer decides where units split, which decides chunk IDs,
  which the pre-registered gold passages cite. A silently swapped tokenizer
  would move chunk IDs and void the pre-registration without changing a single
  corpus byte. The tokenizer checksum was recorded in the ingestion manifest but
  enforced nowhere, which is documentation rather than enforcement. The verifier
  now covers everything that can move a chunk ID.
- Hasan directed this after it was raised at the end of part one.

Commit: b911062a7e778dab3720686e95a6a53a076a69bd
  (feat: extend integrity verifier to vendored files, local only)
  This entry is recorded by the next commit, `docs: log vendor verifier commit,
  local only`, committed immediately after this entry is written, which closes
  the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is ten commits, all trailer-free.
- EU AI Act ingested and verified. NIST PDFs acquired and checksummed, not yet
  ingested.

Next step:
- Ingestion part two, NIST PDFs. Investigation phase first, extractor
  comparison, silent-failure detection, structural invariants, boundary
  strategy, chunk ID scheme, cross-document structure, near-duplicate
  quantification and normalisation survey. No pipeline is built until that
  investigation is approved.

## 2026-07-22, Phase 1 ingestion part one, EU AI Act

Ingestion is split in two. This is part one, the EU AI Act only. Part two is the
three NIST PDFs. The split is deliberate: the EU HTML carries semantic ELI
anchors verified against the document's true structure, so the schema is proven
on the case where structure is certain, and part two is then debugging PDF text
extraction alone rather than schema and extraction at once.

What changed:
- Added the corpus integrity verifier, `src/ingest/corpus_integrity.py`. It
  recomputes the SHA-256 of every file under `corpus/*/raw/` against
  `corpus/SOURCES.md`, applies the documented `ruxitagentjs` strip rule to the
  EUR-Lex HTML and checks the stable content hash too. Ingestion calls it first
  and refuses to run on any mismatch, so a corrupted or swapped corpus cannot be
  ingested silently.
- Added the chunk schema, `src/ingest/chunk_schema.py`, format-agnostic so it
  serves the NIST PDFs in part two unchanged.
- Added structure-aware EU AI Act ingestion, plus a dependency-free HTML tree,
  minimal text normalisation, the pinned tokenizer, and cross-reference
  extraction.
- Added 62 tests. All pass, ruff clean.

Chunking and identifiers:
- 113 Articles, 13 Annexes, 180 Recitals, 306 units, into 397 chunks: 176
  article, 28 annex, 193 recital. 65 units exceeded the cap and were split.
- Chunk IDs derive from the document's own ELI anchors, `eu_ai_act:art_6`, and
  splits from the parent, `eu_ai_act:art_6#p2`. Never a positional index. Gold
  passages cite the unit via `parent_id`, so a later change to chunk size cannot
  invalidate the pre-registration.
- Token cap 512, which is bge-base-en-v1.5's real 512-position ceiling rather
  than a chosen number, so an over-cap chunk would be truncated at embedding
  time. Max observed 511, none over cap.
- Recitals are ingested and tagged. They are the most realistic near-miss
  distractors available. Whether gold sets may cite them is a pre-registration
  decision, not an ingestion one.
- Output is `data/chunks/`, separate from the immutable `raw/`. Reruns are
  byte-identical.

Tokenizer decision, overriding the tracker's BGE-M3 lean:
- The chunking tokenizer is `BAAI/bge-base-en-v1.5`, vendored under `vendor/`.
  The corpus is entirely English, so BGE-M3's multilingual capacity is unused
  weight, and with an 8192 window a 512 cap would be an arbitrary number. With
  bge-base-en-v1.5 the cap is the model's real ceiling. Recorded in the manifest
  with its identifier and vocabulary checksum so a future model swap cannot move
  chunk IDs without the manifest showing it. Hasan is updating the tracker.

Cross-reference graph, and its deliberate limits:
- 367 internal edges, 102 external references, 25 dropped.
- Precision is 100 percent on a FULL audit of all 581 internal reference
  occurrences, screened against each reference's own sentence and the preceding
  one. Fourteen were flagged and all fourteen were read individually.
- Recall is deliberately sacrificed for precision, costing about 6.4 percent of
  edges. The rule emits an internal edge only on positive evidence and drops on
  doubt. The asymmetry justifies it: roughly 16 multi-hop pairs are needed from
  several hundred candidate edges, so recall is in surplus while one false edge
  inside a gold set would corrupt the ground-truth claim.
- Every dropped reference is recorded with its sentence and reason, so the
  conservatism is auditable rather than taken on faith.
- The field is labelled everywhere as a high-precision candidate extraction,
  derived by our regex from prose rather than read from publisher markup. It is
  never described as the complete cross-reference structure of the Act. Every
  edge entering a gold set is individually verified at the point of use.

Four false-positive modes were found and fixed, three of them by auditing
everything rather than sampling:
- Bare references inside an article amending another instrument, "in Article 17,
  the following paragraph is added" in art_108, which amends Regulation
  2018/1139. Fixed by reading the article's own heading. The carve-out keeps
  art_7, "Amendments to Annex III", internal because it amends this Act.
- Anaphora, "Article 33 of that Regulation".
- A qualifier distributed across an enumeration, "Article 4(2) and Article 10 of
  Directive (EU) 2016/680".
- Instruments named by acronym, "Article 16 TFEU", "Article 4(2) TEU". A 30
  sample missed this entirely; the full audit caught it.
Referential integrity, requiring an internal edge to resolve to a real unit, is
retained as a structural safety net. It currently fires zero times, and the
manifest says so plainly rather than implying it is doing work.

Findings recorded so they are not lost:
- The published Regulation contains a stray backtick in Article 1's heading,
  ``Subject matter` ``. It is in the official PDF too, at line 3023 of the
  pdftotext rendering. Reproduced exactly rather than corrected, recorded in the
  manifest and in `corpus/SOURCES.md`, and asserted by a test. Source text is
  never edited, including where it is visibly wrong.
- Enumerated lists are HTML tables and all 180 Recitals exist only as tables, so
  a parser skipping tables would drop every list item and every Recital while
  appearing to succeed. A test asserts the recital count.
- Unit boundaries come from DOM nesting, not anchor-to-anchor windows. A window
  made art_113 absorb the Annexes. The NIST PDFs have no nesting to fall back
  on, so part two needs its own boundary strategy.

Licensing:
- `corpus/SOURCES.md` gained a vendored third-party dependencies section.
  bge-base-en-v1.5 is MIT, read from the model card metadata, the model card's
  own licence section and the upstream FlagEmbedding repository, all three
  agreeing, with no redistribution restriction. Recorded with source URL,
  retrieval date and per-file checksums, kept separate from the repository's
  Apache 2.0 code licence and from the corpus documents' terms.

Why:
- Chunk IDs are cited by pre-registered gold passages and pre-registration is
  immutable once results exist, so identifiers had to be structure-derived and
  final before any query exists. Committing the cross-reference graph before any
  query exists is also what makes the ground-truth claim demonstrable from the
  commit history rather than asserted.
- No API calls, no spend, no remote configured, nothing pushed.

Commit: 8af050de1f22fee47b67797e76047001aaaaaadf
  (feat: structure-aware EU AI Act ingestion with integrity verifier, local only)
  This entry is recorded by the next commit, `docs: log EU AI Act ingestion
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is eight commits, all trailer-free.
- The EU AI Act is ingested and verified. The NIST PDFs are acquired and
  checksummed but not yet ingested. No retrieval, no query set, no gold
  passages, no results yet.

Next step:
- Ingestion part two: the three NIST PDFs, AI 100-1, AI 600-1 and the Playbook,
  into the same chunk schema. Text extraction from PDF is the risk there, not
  the schema. Needs its own boundary strategy since PDFs have no DOM nesting,
  and needs care with headers, footers, ligatures and tables. The persisted
  normalised text per document is the artifact that makes extraction auditable.

## 2026-07-22, Phase 1 corpus acquisition

What changed:
- Acquired the case study corpus and committed it under `corpus/`, with a full
  provenance record in `corpus/SOURCES.md`. Five files, every download HTTP 200
  and every size matching the `Content-Length` the server advertised:
  - `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.html`, 1,264,455 bytes, the parse
    source for structure-aware chunking.
  - `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.pdf`, 2,583,319 bytes, 144 pages,
    retained as an authoritative reference snapshot, not as a parse source.
  - `nist_ai_rmf/raw/NIST.AI.100-1.pdf`, 1,946,127 bytes, AI RMF 1.0, printed
    cover date January 2023, 48 pages.
  - `nist_ai_rmf/raw/NIST.AI.600-1.pdf`, 1,174,643 bytes, Generative AI Profile,
    printed cover date July 2024, 64 pages.
  - `nist_ai_rmf/raw/AI_RMF_Playbook.pdf`, 2,882,270 bytes, 147 pages, covering
    all 72 AI RMF subcategories.
- Filled `corpus/SOURCES.md` as a real provenance record: per-file identifier,
  version, publisher, retrieval date, size, SHA-256, and the `last-modified` the
  server sent; reuse terms per publisher read from the publishers' own notices;
  formal citations fulfilling the attribution those notices request; and the
  retrieval and ingestion notes below.
- Structural authenticity was checked, not just integrity. The EU HTML carries
  ELI anchors matching the act exactly, `art_1` to `art_113` for 113 Articles,
  `anx_I` to `anx_XIII` for 13 Annexes, `rct_1` to `rct_180` for 180 Recitals,
  and Article 6, Article 14, and Annex III were confirmed to carry their correct
  text. All three NIST documents show Govern, Map, Measure, and Manage as
  expected, and the printed identifiers and cover dates match the landing pages.

The corpus is what the locked decision in the tracker calls for, minus nothing:
NIST AI RMF Core plus the Generative AI Profile plus the Playbook, and the EU AI
Act with Articles, Annexes, and Recitals. ISO/IEC 42001 remains excluded on
copyright grounds and is referenced by pointer only.

Ruling, Official Journal text versus consolidated version:
- The original Official Journal text is used, CELEX 32024R1689, OJ L, 2024/1689,
  12.7.2024. The consolidated version was checked first and rejected.
- The reason is not a preference for one version date. There is no English
  consolidated version of this regulation. Requesting the consolidated text
  through the English interface returns the notice that the document is
  unavailable in that language and serves the French text instead.
- The mechanism: consolidated versions are produced only for the language
  versions that received a corrigendum. Four corrigenda exist against this act,
  R(01) through R(04), and English appears in none of them. The English text has
  therefore never been corrected, so the Official Journal text is both the only
  English text and the authentic one. EUR-Lex states that only Official Journal
  documents are authentic, and consolidated texts carry an explicit disclaimer
  that they have no legal effect.
- The two amending acts listed, 52025PC0836 and 52025PC1023, are Commission
  proposals and neither is in force.

Immutability of `raw/`:
- Everything under `corpus/*/raw/` is byte-identical to what the publisher
  served and is never hand-edited. No document text was reconstructed, retyped,
  summarised, or completed from any other source. Parsing and text extraction
  happen at the ingestion step and write to a separate location, so the raw
  source stays exactly as served. The committed checksums make any later
  modification detectable.

Carried forward for ingestion, recorded in `corpus/SOURCES.md`:
- The EUR-Lex HTML embeds a per-request analytics script, so its raw SHA-256 is
  not reproducible by re-download. A stable content hash and an exact strip rule
  are recorded. Building the verifier script belongs to ingestion, not here.
- Structural titles use a non-breaking space, U+00A0, so a parser matching
  `"Article 6"` with a plain space will silently fail. Normalise before matching.
- Formex 4 XML was considered and rejected on availability, with endpoints and
  status codes recorded. EUR-Lex rate-limits by returning HTTP 202 with an empty
  body, so any re-download must check body size rather than trust the status.

Why:
- Every downstream number in this repository is only as trustworthy as these
  files, so provenance and integrity are the foundation of the result, not
  paperwork. Recording reuse terms for the documents that are shipped is also
  what makes the ISO/IEC 42001 exclusion a consistent rule rather than an
  arbitrary one.
- This step was acquisition only. No parsing, no chunking, no retrieval code, no
  API calls, no spend, no remote configured, and nothing pushed. Hasan reviewed
  and approved `corpus/SOURCES.md` in full before this commit.

Commit: d16d331bf8323d0b91d9c47ca29f0f45c491ab59
  (feat: add NIST AI RMF and EU AI Act corpus with provenance, local only)
  This entry is recorded by the next commit, `docs: log corpus acquisition
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is six commits, all trailer-free:
  a4383816 bootstrap, d311c03f session log, 3e4c68c tracker update, 4ee0632 log
  of the tracker commit, d16d331 corpus acquisition, and this log commit.
- The corpus is in place and verified. Source subpackages are still empty
  placeholders. There is no ingestion code, no chunking, no retrieval, no query
  set, no gold passages, and no results yet.

Next step:
- Structure-aware ingestion: parse the EU AI Act HTML by Article and Annex and
  the NIST PDFs by function, category, and subcategory, writing chunks to a
  location separate from the immutable `raw/`, with tests per CLAUDE.md Rule 12.

## 2026-07-21, tracker update after bootstrap rebuild

What changed:
- Updated `rag_case_study_tracker.md` to reflect the post-rebuild state. The Status
  at a glance section now records Phase 0 as complete, bootstrap committed and
  verified, trailer-free and local only with nothing pushed, and sets the next
  action to Phase 1 corpus acquisition. The Key decisions log gained two dated
  entries: one recording the repo-wide removal of the Claude co-author trailer and
  the pre-push rebuild of the two bootstrap commits under the authorized one-time
  Rule 10 override, and one recording that the Rule 10 exception is now spent.
- This entry logs that tracker commit. To avoid leaving a further unlogged commit,
  this same entry is committed as the immediately following commit,
  `docs: log tracker update commit, local only`, which records this log update
  itself and closes the chain, so the next session inherits no unlogged commit.

Why:
- The tracker is the first file a new session reads, and it still described the
  pre-rebuild state. Correcting it was Hasan-directed in session, permitted under
  CLAUDE.md for stale-reference corrections. CLAUDE.md Rule 11 requires a session
  log entry after each commit, so the tracker commit is logged here, and this entry
  names its own recording commit so the log-of-the-log does not spawn an endless
  tail of unlogged commits.

Commit: 3e4c68c6106752623e0cdc33140e3607afa0d04c
  (docs: update tracker after bootstrap rebuild, local only)
  This entry is recorded by the next commit, `docs: log tracker update commit,
  local only`, committed immediately after it is written.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is four commits, all trailer-free:
  a4383816 bootstrap, d311c03f session log, 3e4c68c tracker update, and this log
  commit.
- Repo contents are unchanged since the Phase 0 bootstrap: source subpackages are
  empty placeholders, and there are no corpus files, no query set, no gold
  passages, and no results yet.

Next step:
- Phase 1: corpus acquisition for the NIST AI RMF and the EU AI Act, then
  structure-aware ingestion and closed-book hybrid retrieval.

## 2026-07-21, Phase 0 bootstrap

What changed:
- Scaffolded the repository structure. Created the `src` package with subpackages
  `ingest`, `retrieve`, `generate`, `verify`, `complete`, `score`, and
  `ragas_validation`, each with an `__init__.py`, plus `src/__init__.py` and
  `tests/__init__.py`.
- Created tracked-but-empty directories with `.gitkeep`: `corpus/nist_ai_rmf`,
  `corpus/eu_ai_act`, `eval`, `data/runs`, and `results/tables`.
- Set up Python tooling with uv targeting Python 3.12. Added `pyproject.toml`
  (project `architect-rag-verification`, version 0.0.0, requires-python >=3.12,
  runtime dependency `anthropic`, dev dependencies `ruff` and `pytest`, ruff
  line-length 100 and target-version py312, pytest testpaths `tests`), pinned
  `.python-version` to 3.12, and generated `uv.lock`.
- Added `.gitignore` (`.env`, `.venv`, `__pycache__`, `*.pyc`, `.ruff_cache`,
  `.pytest_cache`, local model and embedding caches, `.DS_Store`; leaves `data/`,
  `eval/`, and `results/` tracked), `.env.example` documenting the subshell key
  pattern with no real value, the Apache 2.0 `LICENSE` (copyright 2026 Hasan
  Youssef), `corpus/SOURCES.md` provenance skeleton with empty NIST AI RMF and
  EU AI Act rows, and a `README.md` skeleton with section headers and neutral
  TODO placeholders and no result claims.
- Initialized git with `main` as the default branch and made the first commit,
  which also captured the four governance files already present.

Why:
- Phase 0 establishes the reproducible skeleton before any corpus, any code, and
  any spend, so later phases have a clean, testable, key-free foundation. No
  corpus was downloaded, no API was called, nothing was spent, no remote was
  configured, and nothing was pushed.

Commit: a4383816d7583c9ea09987ba13165f0e11022021
  (chore: bootstrap repo scaffolding, tooling, and governance)
  Note: the two bootstrap commits were deliberately rebuilt before any push to remove the Claude co-author trailer, a one-time authorized override of CLAUDE.md Rule 10 valid only in this pre-push window because nothing is pushed and no README or pre-registration cites these hashes; the hash above is the rebuilt bootstrap hash.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
- Tooling verified: `uv sync` builds the environment, `ruff check .` passes, and
  `pytest --collect-only` runs cleanly with zero tests collected so far.
- Source subpackages are empty placeholders. No corpus files, no query set, no
  gold passages, no model outputs, no results yet.

Next step:
- Phase 1: corpus ingestion and closed-book hybrid retrieval. Fill
  `corpus/SOURCES.md`, ship NIST AI RMF and EU AI Act under `corpus/`, implement
  structure-aware chunking and BM25-plus-dense hybrid retrieval with reciprocal
  rank fusion. The Phase 1 pre-registration commit that adds the query set and
  the gold passages must predate any generation run.
