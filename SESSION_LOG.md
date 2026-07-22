# Session log, architect-rag-verification

Running log owned by Claude Code. One entry per commit, per CLAUDE.md Rule 11.
A new session should be able to resume from `rag_case_study_tracker.md` plus the
last entry here alone. Newest entries at the top.

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
