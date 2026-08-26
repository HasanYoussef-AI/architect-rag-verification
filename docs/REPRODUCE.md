# How to reproduce every number in this repository

Nothing here needs an API key, a network connection, or money. The generation step ran once and
its outputs are committed. Everything downstream re-derives from those committed files.

Expect the wall clock to be dominated by the test suite, which means it scales with the machine
rather than being a property of this repository. Locally, the suite alone takes 4m10s in a fresh
clone on the development machine, macOS on arm64. On continuous integration the suite step falls
into two clusters, one near five minutes and one near six and a half, with nothing between them.
The gap is consistent with different runner hardware being assigned between jobs rather than with
anything in this repository, so a figure of your own belongs to one cluster or the other rather
than to a bracket worth checking it against.

---

## What reproduces, and what does not

| | Needs | Reproduces |
| --- | --- | --- |
| Every headline number in the README and `docs/RESULTS.md` | a clone and Python 3.12 | exactly, byte for byte |
| The corpus, chunking and retrieval artifacts | the same | exactly, byte for byte |
| The three result artifacts | the same | exactly, byte for byte |
| The dense half of the attributability scan | the pinned ONNX model, not committed | rankings, not bytes |
| Regenerating model answers | your own API key and about four dollars | not byte-identical, see the last section |

The third row is the one that matters: every published rate comes from files in the first three
rows, so a reviewer with nothing but a clone can check every claim.

---

## Setup

```
git clone <this repository>
cd architect-rag-verification
uv sync
```

`uv sync` installs the runtime and dev dependencies from `uv.lock`. It does **not** install the
`embed` group, which is build-only and needed for one optional check described at the end.

On Python versions, the two files say different things and both are load-bearing.
`.python-version` contains exactly `3.12`, which is the interpreter `uv` provisions.
`pyproject.toml` declares `requires-python = ">=3.12"`, which is the floor the project supports.
Reproducing on 3.12 is the path that was measured.

If you prefer not to use `uv`, any environment satisfying `pyproject.toml` works; the pinned
dependency that matters for reproduction is `numpy`, and `tokenizers` for the ingestion tests.

---

## Step 1. Verify the corpus is what the publishers served

```
python -m src.ingest.corpus_integrity
```

Expected, the last line:

```
30 checks passed.
```

Thirty checks: five raw corpus files against the SHA-256 recorded in `corpus/SOURCES.md`, one
stable-content hash for the EU AI Act HTML, and twenty-four vendored files. Every downstream number
rests on these bytes, so this runs first.

The EU AI Act HTML needs the extra check because EUR-Lex embeds a per-request analytics script, so
a fresh download has a different raw checksum while the legal text is unchanged.
`corpus/SOURCES.md` records the exact strip rule and the stable content hash.

If any check fails, stop. Nothing below is meaningful over a corpus that is not the one the
measurements were taken on.

---

## Step 2. Run the suite

```
python -m pytest -q
```

**This is the primary reproduction check, and it is worth saying why rather than treating it as a
formality.** The suite is not only a test of the code. It re-derives the results:

- `tests/test_sealed_grading.py` rebuilds the grading artifact through the runner and compares the
  parsed object against the committed file. It catches the runner and the artifact parting company.
- `tests/test_results_digest.py`, `tests/test_layer_results_digest.py` and
  `tests/test_grading_results_digest.py` compare the committed **bytes** against pinned SHA-256
  digests. They catch every byte change the parsed comparison is blind to: reordered keys, changed
  whitespace, different unicode escaping, translated line endings.
- `tests/test_layer_eval.py` rebuilds the layer artifact and asserts it byte for byte.

Neither kind subsumes the other, which is why both exist. Together they mean that reversing either
check requires deleting a failing test.

### What you should see

Three figures, and which one you get depends on your environment. All three are correct.

Every number in this section was measured by cloning this repository into an empty directory,
running `uv sync`, and running the suite there. None of it is carried over from a working checkout,
because a working checkout accumulates the optional artifacts a fresh clone does not have and will
report fewer skips than a reviewer sees.

| environment | collected | passed | skipped | wall clock |
| --- | --- | --- | --- | --- |
| **a fresh clone**, `uv sync` | 1064 | 1053 | 11 | 4m10s |
| with the `embed` group and the model cache primed, no segment cache | 1064 | 1057 | 7 | 4m23s |
| with the `embed` group, the model primed and the segment cache built | 1064 | 1064 | 0 | 4m28s |

**A fresh clone gives 1053 passed and 11 skipped, and that is the expected result.** The eleven fall
into three classes, and every one names the artifact it needs. Tests are named rather than located
by line, because a line number drifts with every edit above it and has already been wrong in this
file once.

Four in `tests/test_query_embeddings_provenance.py`, needing `onnxruntime`, which `uv sync` does not
install because it is in the build-only `embed` group:

```
test_regenerated_rankings_match_committed_results[development]
test_regenerated_rankings_match_committed_results[test]
test_committed_array_reproduces_regenerated_rankings[development]
test_committed_array_reproduces_regenerated_rankings[test]
    could not import 'onnxruntime': No module named 'onnxruntime'
```

Four in `tests/test_attributability.py`, the dense arm, needing the pinned model:

```
test_dense_arm_scores_the_shared_segments
test_dense_arm_at_segment_granularity_finds_the_case_a_partner
test_dense_arm_applies_no_floor_and_declares_level_3
test_the_dense_arm_scored_population_equals_the_segment_population
    the pinned ONNX model is not cached. It is deliberately outside the offline
    reproducibility set, so its absence skips the dense arm rather than failing it.
```

Three in `tests/test_attributability.py`, needing the segment embedding cache:

```
test_a_stale_segment_cache_raises_rather_than_scoring_the_wrong_text
    no segment cache built; the staleness path needs one to be stale against.
test_manifest_matches_the_cache_it_describes
test_the_manifest_takes_no_value_from_the_untracked_index
    the cache itself is not present; only the manifest ships.
```

**The dense arm's four skips change their reason between the first two environments, and that is
worth knowing before you read your own output.** In a fresh clone they report that the pinned model
is not cached. Once the `embed` group is installed AND the model cache has been primed, the same
four report that the segment embedding cache is absent instead, and name the command that builds it.
Installing the group alone is not enough: nothing in the offline set downloads the weight, by
design, so priming is an explicit step and it is in the optional section below. An earlier revision
of this file quoted the second message under the fresh-clone heading, which is a state no reviewer
following the instructions above will ever be in.

The segment embedding cache is 40,906,880 bytes, about ten times the committed chunk embedding
array, and is deliberately not committed on size. `eval/segment_embedding_manifest.json` carries its
digest, its segment count, its exclusion funnel, the pinned model revision and the command that
builds it, in its place.

**Read the skips by name, not by count.** The count moves as query sets and optional artifacts are
registered, and it has moved three times already. The names above are stable. A skip naming the
segment cache, the pinned model or `onnxruntime` is expected. A skip naming anything else is not,
and is worth reporting.

The collected count is 1064 in every environment. If yours differs, the tree differs.

### Lint

```
python -m ruff check src tests
```

Expected: `All checks passed!`

---

## Step 3. Check the three result artifacts against their digests

The suite already did this. If you want to see it directly:

```
shasum -a 256 eval/test_retrieval_results.json eval/test_layer_results.json eval/test_grading_results.json
```

Expected, exactly:

```
daf58a42a9d77acf91ef0cb168f940f774bc395a08da17dafff27eb91bd763d2  eval/test_retrieval_results.json
7497e19c9a2a18b8ca5080f20c8b6df9d4bd791c3c0e375a4fa153531e4baffb  eval/test_layer_results.json
188dacfb105d5f08ad606bcef2af8e31d836e8000877ca364a3eba8a27ede494  eval/test_grading_results.json
```

Sizes are 71,723, 104,326 and 836,853 bytes. These three digests are asserted by the committed
tests on every suite run, so a mismatch fails the suite rather than passing quietly.

---

## Step 4. Re-derive an artifact yourself

The three runners **refuse to overwrite a committed result**. This is deliberate, not an obstacle:
replacing a committed result is a pre-registration correction under this repository's own rules and
it is logged, so it does not happen by running a command twice.

```
$ python -m src.score.run_retrieval_eval
<your clone>/eval/test_retrieval_results.json already exists. A committed result is not silently
replaced; re-running over one is a Rule 4 correction and takes --overwrite, whose use is logged in
the commit message and the session log.
```

The path the runner prints is absolute, so your output begins with your own clone directory rather
than with the repository-relative path shown above. The message is otherwise verbatim.

Two ways to re-derive without touching anything.

**The layer artifact writes to stdout.** This is the cleanest single command in the repository:

```
python -m src.score.run_layer_eval --stdout | shasum -a 256
```

Expected:

```
7497e19c9a2a18b8ca5080f20c8b6df9d4bd791c3c0e375a4fa153531e4baffb  -
```

That digest is the committed file's, byte for byte, produced by re-running the layer over the
committed first-pass results, the committed chunk store and the committed unit index, with no
model and no key.

**The grading artifact takes a destination path:**

```
python -c "
from pathlib import Path
import src.score.run_sealed_grading as g
g.write(Path('/tmp/grading.json'))
"
shasum -a 256 /tmp/grading.json eval/test_grading_results.json
```

Both digests should read `188dacfb105d5f08ad606bcef2af8e31d836e8000877ca364a3eba8a27ede494`.

**For the retrieval artifact**, or for a full in-place rebuild of any of the three, pass
`--overwrite` and then check `git diff`, which should be empty:

```
python -m src.score.run_retrieval_eval --overwrite
git diff --stat eval/test_retrieval_results.json
```

Expected: no output from `git diff`. If it reports a change, that is a real divergence and worth
reporting.

### Byte-identity carries no platform condition

Both halves of the claim are true by mechanism, so a digest mismatch here is a real divergence and
not a platform artefact.

**The checkout half.** `.gitattributes` sets `-text` across the tree, so a checkout never translates
line endings and a clone holds the committed bytes on every platform.

**The rebuild half.** All three runners pass `newline="\n"` and pin LF rather than inheriting the
runtime's text-mode translation, so a rebuild produces the same bytes on every platform.

The rebuild half carried a stated condition until the writers were pinned: they opened their output
in default text mode, so a runtime writing CRLF produced different bytes without changing a single
figure. That was true of the code it described, and it was removed at its source rather than
restated, because a pin whose failure mode a reader cannot distinguish is a pin that gets deleted
the first time it fires.

Measured on macOS with CPython 3.12: all three artifacts rebuild byte-identically and the committed
files contain zero CRLF sequences.

---

## Step 5. Read the results

- `docs/RESULTS.md` carries the full per-tier, per-stratum, per-condition tables.
- `results/tables/` carries the same tables as CSV, one observation per row, written by
  `python -m src.figures.build_tables` and pinned by digest. Load these rather than walking the
  JSON if you want to plot a series or check an arithmetic identity.
- `eval/test_grading_results.json` is the artifact every headline number is read from. It is
  836,853 bytes and it carries its own derivations: each aggregate block states in its own text how
  it was computed and which counts it sums.
- `eval/test_retrieval_results.json` and `eval/test_layer_results.json` carry the two retrieval
  conditions, under two different metric names, for the reason `docs/RESULTS.md` explains.

---

## Optional: the dense attributability arm

This is the one check that needs the pinned model, and it is deliberately outside the offline
reproducibility set.

```
uv sync --group embed
python -c "from src.retrieve.embed import download_onnx; print(download_onnx())"
python -m src.goldset.build_segment_embeddings
```

The middle command is the one that fetches, and it is separate on purpose. Nothing the offline set
runs will download the weight: `src/goldset/attributability.py` resolves it from the local cache
only, so that `docs/REPRODUCE.md`'s opening claim about not needing a network connection is true by
mechanism rather than because a failed attempt is swallowed. The generator says the same thing in
its own error text, that it never downloads and the cache must be primed first, and until this was
separated that sentence was not true of the code beneath it.

Measured on the machine this file was written on: the build took 19.0 minutes and wrote 40,906,880
bytes to `embeddings_cache/segment_embeddings.npy`, which is git-ignored. After it the suite reports
1064 passed and 0 skipped, which is the third row of the table above.

Two things reproduced exactly on that run and are worth knowing, because they are what the manifest
exists to let you check. The rebuilt cache's SHA-256 matched
`eval/segment_embedding_manifest.json`'s `cache_sha256` exactly, and the build rewrites that
manifest as its last step, which came back byte-identical to the committed one. Both are
same-machine reproductions; see the caveat below.

`onnxruntime` is pinned to `==1.27.0` because its reduction order is version-sensitive and the
committed embeddings were generated with that build. Regenerating from the pinned ONNX revision
reproduces **rankings, not bytes**, across machines. If your cache digest differs from the one in
`eval/segment_embedding_manifest.json`, compare the reported units and cosines rather than the
bytes.

---

## Optional: regenerate the model answers with your own key

Never required to verify a result. Everything above runs without it.

The key enters only through a subshell and is never exported into your session:

```
(set -a; source .env; set +a; COMMAND)
```

`.env` is git-ignored. `.env.example` documents the pattern with no real value.

**Three limits on this path, stated because they are real and none of them is obvious.**

**1. Two of the three model strings float.** Only the Haiku tier is pinned to a dated snapshot:

```
haiku45   claude-haiku-4-5-20251001
sonnet5   claude-sonnet-5
opus48    claude-opus-4-8
```

`claude-sonnet-5` and `claude-opus-4-8` are undated aliases, so a regeneration run resolves them to
whatever those aliases point at on the day you run it. On two of three tiers you will therefore not
be running the same experiment. The committed outputs are what the published numbers rest on.

**2. The dated Haiku snapshot has a published retirement date.** Anthropic's model deprecations page
lists `claude-haiku-4-5-20251001` as Active with a tentative retirement date of not sooner than
October 15, 2026. After retirement, requests naming it fail, and that tier becomes unregenerable at
the pinned version.

**3. Decoding is not uniform across tiers, and it could not be.** Temperature 0 was pre-registered.
Measured per tier with matched controls: Haiku accepted it and it was sent on every Haiku run;
Sonnet 5 and Opus 4.8 both returned HTTP 400 and the parameter was omitted on those tiers. The
probe records and their controls ship in `data/runs/run_manifest.json`. Each tier carries one
setting on both sides of its own comparison, so every published delta is taken under identical
decoding within a tier.

The full generation cost, all nine runs, was 3.218898 dollars.
