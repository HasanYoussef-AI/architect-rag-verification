# Session log, architect-rag-verification

Running log owned by Claude Code. One entry per commit, per CLAUDE.md Rule 11.
A new session should be able to resume from `rag_case_study_tracker.md` plus the
last entry here alone. Newest entries at the top.

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
