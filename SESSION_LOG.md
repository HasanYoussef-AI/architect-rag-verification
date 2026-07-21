# Session log, architect-rag-verification

Running log owned by Claude Code. One entry per commit, per CLAUDE.md Rule 11.
A new session should be able to resume from `rag_case_study_tracker.md` plus the
last entry here alone. Newest entries at the top.

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
