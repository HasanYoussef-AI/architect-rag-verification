# Attributability scan, calibration record

The record behind `src/goldset/attributability.py`. It states what the instrument was calibrated
against, what reproduced, what did not, and the gaps that are recorded as gaps rather than
reconciled.

**Every value in this record was re-derived over the repaired segmentation.** The earlier values
were computed over a corpus text that differed from source on 97 of 1150 units, because
`Corpus.load` joined a unit's chunks with no separator and dropped the newline the chunker had
recorded. Where a value moved, both are shown. Where a value could not move, that is stated rather
than left to look like a re-derivation that tested something. The reason is stated once here and
not repeated per value.

## The re-derivation funnel

Every numeric claim in this file, classified by what it depends on and whether it moved.

**Corpus-dependent and moved.**

| Value | Before | After |
| --- | --- | --- |
| Starting population, raw segments | 14,626 | **14,770** |
| Removed: carries no alphabetic word | 1,057 | **1,113** |
| Comparable segments | 13,228 | **13,316** |
| Cache array bytes | 40,636,416 | **40,906,752** |
| Ratio to committed chunk embeddings | 10.2x | **10.3x** |
| Recital maximum characters | 4,447 | **4,448** |
| `segmentation_fingerprint` | `7ee94406…` | **`547428df…`** |
| `cache_sha256` | `34b786aa…` | **`186a1ffd…`** |

**Corpus-dependent, re-derived, unchanged.** These were re-run against the repaired segmentation
and returned what they returned before. That is a result, not an assumption.

| Value | Re-derived |
| --- | --- |
| Units | 1,150 |
| Removed: is its own unit's recorded heading | 341 |
| Segments equal to some other unit's label, kept | 16 |
| Longest own-label segment | 17 characters, maximum two words |
| Twelve committed blocks reproducing | 12 of 12 |
| test_16 ratios | 0.996 and 0.951, superseding 0.821 under the autojunk correction |
| Units scored, 1150 less the gold unit | 1,149 |
| `art_72` characters | 2,318 |
| Recital minimum and median characters | 145 and 1,030 |
| Recitals inside the withdrawn 1,200 to 3,200 band | 68 of 180 |
| Annex IV point 3 block | 772 characters |
| Longest period-only segment inside that block | 768 characters |
| Period-only blindness on case B | 0.3621, superseding 0.2968 under the autojunk correction |
| Shipped segmentation on the same pair | 0.8982 |
| `Article 43` against `Article 97`, pre-heading-predicate | 0.8 |
| `ANNEX VIII` against `ANNEX III`, pre-heading-predicate | 0.9474 |

**Not corpus-dependent, so incapable of moving.** These compare two literal strings committed in
`tests/test_attributability.py` and never touch `Corpus`. They were re-run and are unchanged, and
that re-run tested nothing about the segmentation. Stating it that way rather than presenting them
among the re-derivations.

0.940, 0.9310 raw, 0.9310 lower-only, 0.9397 in three normalisations, 0.9351, 0.931 unfolded,
0.894 published, 0.8982 derived, 0.8710 word-granularity, 0.8312 and 0.8865 span-boundary
variants, 0.8987, 0.9005, the 0.60 floor, the 123-character span, and 5.3 percent.

**Nothing in this file was unreachable.** Every value listed above was re-derived by its own route.

## What the instrument is for

No committed relation covers near-verbatim restatement outside the NIST subcategory statements,
and none covers the EU AI Act at all. `verbatim_groups.json` is exact identity after
normalisation. The AI 100-1 duplication map is exact substring and NIST only.
`near_duplicate_exceptions.json` is retrieval-conditioned, recording pairs where a near-duplicate
won a known-item retrieval, so absence from it means the twin did not win retrieval rather than
that no twin exists.

The instrument closes that gap for authoring-time screening. It decides nothing. Both arms report
and a human verifies what they surface.

## Calibration is against held-out ground truth, not against fitting

Two positives were published in `eval/test_frame_rejections.jsonl` before this instrument
existed, on picks already rejected. They are not observations this instrument will judge.
Selecting a segmenter that catches two pre-published positives is calibrating a detector against
held-out ground truth, which is the practice rather than a breach of it.

Two conditions keep that true, and both hold:

- The reporting floor is 0.60 and never moves. It is the value already recorded in every
  committed `duplication_scan` block.
- The segmenter is frozen and committed before any single-hop span is designated. No span has
  been designated.

## Case A: reproduces exactly

Articles 26(5) and 72(2), published at **0.940**. Both sides quoted verbatim from the row's
`reason` field.

| Normalisation | Ratio |
| --- | --- |
| raw | 0.9310 |
| lower only | 0.9310 |
| lower + hyphen to space | 0.9397 |
| lower + strip punctuation | 0.9397 |
| **shipped**: normalise_for_comparison + lower + strip punctuation | **0.9397** |
| lower + delete hyphen | 0.9351 |

0.9397 rounds to the published 0.940. This table compares two committed literal strings and does
not touch `Corpus`, so the repaired segmentation could not have moved it.

**Hyphen folding is load-bearing, not cosmetic.** The pair differs by `law-enforcement` against
`law enforcement`, and without the fold the value is 0.931. A test pins that the unfolded form
gives 0.931 and misses.

## Case B: the derived value still does not reproduce, and the pair now surfaces

Annex IV point 3 against Article 13(3)(d), published at **0.894**. The instrument derives
**0.8982** from the two committed literal spans, and that comparison does not touch `Corpus`, so
the repaired segmentation could not move it and did not.

Six normalisations were tried, returning 0.8982 to 0.9005. Four of the six reproduce case A, and
those four return 0.8982 to 0.8987; the two that do not reproduce case A return 0.8987 and 0.9005.
Both difflib granularities: character 0.8982, word 0.8710. Three span-boundary variants: 0.8982,
0.8312, 0.8865. None returns 0.894.

An earlier draft of this record stated "six normalisations, all of which reproduce case A, giving
0.8982 to 0.8987". Both halves were wrong: only four of the six reproduce case A, and the six span
0.8982 to 0.9005. Corrected here rather than quietly restated, because the wrong version had
already been read and relied on.

The search stopped there. A twelfth variant that happened to hit 0.894 would have been selected
because it hit 0.894, which is tuning to a target rather than deriving a value.

**What the repaired segmentation changes.** Comparing the two units segment against segment, the
previous segmentation returned no pair at all. The repaired segmentation returns two, and the
first is:

| | |
| --- | --- |
| Full-precision ratio | 0.8935064935064935 |
| Rounded to three decimals | **0.894** |
| Annex IV side, characters 4569 to 4761 | inside Annex IV point 3, which spans 4036 to 4808 |
| Article 13 side, characters 2460 to 2659 | inside Article 13(3)(d), which spans 2460 to 2660 |

> the human oversight measures needed in accordance with Article 14, including the technical
> measures put in place to facilitate the interpretation of the outputs of AI systems by the
> deployers;

> (d) the human oversight measures referred to in Article 14, including the technical measures put
> in place to facilitate the interpretation of the outputs of the high-risk AI systems by the
> deployers;

The second pair returns 0.7212389380530974, rounding to 0.721. Its Article 13 side is the same
13(3)(d) clause, but its Annex IV side sits at characters 2942 to 3208, inside point 2(e) and not
inside point 3, so it does not meet the reproduction test and is recorded as not meeting it.

**Why this is a reproduction and not a fitted result.** Three grounds, each checkable:

1. The target was published before the repaired segmentation existed. `0.894`, `Annex IV point 3`
   and `Article 13(3)(d)` are all in the `src/goldset/attributability.py` docstring committed at
   `c2106e5`, and `CASE_B_PUBLISHED = 0.894` is a constant in `tests/test_attributability.py` at
   the same commit.
2. The defect that produced the repaired segmentation was found while building an unrelated
   instrument, under an instruction to report it and not fix it, and was logged at `6cc9e6c`. That
   entry contains no occurrence of `case B`, `0.894`, `0.8982`, `Annex IV`, `anx_IV`, `art_13`,
   `Article 13`, `13(3)`, `supersession`, or any decimal matching `0.\d{2,4}`. The scan carries
   positive controls: `141` twice, `13228` once, `14626` once, `fabricated` once and
   `segmentation` six times in the same entry, so it was capable of finding text and found none.
3. The span criterion rejected an available alternative. Pair 2 existed at 0.721 and failed on
   its Annex IV span, so the test could discriminate and did.

**The residual, stated rather than glossed.** The reproduction test was fixed after the ratio
0.894 had been reported, so the number was known when the test was written and could not have
failed. The spans were not known, so the span criterion could have failed, and it did fail on pair
2. The test was not blind and is not described here as blind.

**The verdict does not move, and the supersession stands.** Both values clear the 0.60 floor and
the pick stays rejected as `answer_duplicated_across_endpoints` for the same reason, so the number
is exposition and the verdict is robust to it. The `ratio_supersession` field naming 0.894 as
superseded is unchanged. A superseded number returning under a different segmentation is a finding
about the segmentation, not a reinstatement, and settling it needs a designated span that does not
exist.

**Case A reproducing to the digit bounds the disagreement to case B rather than to the method,
and beyond that no diagnosis is available, because the original method was never committed.**
That sentence is the argument for this entire build: a measurement whose instrument does not ship
cannot be checked, only re-derived and compared, and when the two disagree there is nothing left
to inspect.

The rejection row is amended in a separate commit that cites this one: the `reason` field carries
0.8982 and a `ratio_supersession` field names 0.894 as superseded with the reason. Retracted in
the open, not silently replaced and not left standing.

## Segmentation, and the blindness it fixes

A period-terminated segmenter is blind to case B. Annex IV point 3 is one period-terminated block
whose clauses are separated by semicolons, so the matching clause never becomes its own segment.
It stays buried in a **768**-character span, the longest period-only segment inside a 772-character
block, and the best reachable ratio against Article 13(3)(d) is **0.3621**, far below the floor.
The pick passes and the detector reports nothing on the very case it exists to catch.

MARKED CORRECTION, autojunk. That ratio was **0.2968** while every ratio was built under difflib's
`autojunk=True` default, which junks characters appearing in more than one percent of the second
sequence once it reaches 200 elements. The 768-character period-only span is far past that
threshold, so the blind form's score depended on the length of the span it was blind to. The
control is unchanged in what it establishes: 0.3621 is still far below the 0.60 floor, and the
semicolon companion is unmoved at 0.8982, so the segmenter was selected on the same comparison.

Segmenting on semicolons as well reaches **0.8982** on the same pair. Both the blind form and the
shipped form are driven over the same pair in
`test_period_only_segmentation_is_blind_to_the_published_case`, so the shipped form is trusted
only on a pass it has been shown able to withhold.

Both numbers were re-derived over the repaired segmentation and are unchanged. The helper that
reads the block carried the same concatenation defect and now joins on the same newline, and the
block is 772 characters either way, because no inter-chunk boundary falls inside point 3.

## The join is a reconstruction, not a chosen separator

`Corpus.load` joins a unit's chunk records with a newline. This is not a separator selected for
its effect on segmentation. It is the text the chunker recorded:

- Every one of the 144 inter-chunk gaps in the four `normalized.txt` files is exactly one newline,
  with no other value observed.
- `BLOCK_SEPARATOR` in `src/ingest/eu_ai_act.py`, `src/ingest/nist_ai_100_1.py` and
  `src/ingest/nist_pdf_common.py` is that same newline, because it is what ingest wrote.
- Joining on it reconstructs each unit's slice of the normalised source on **1150 of 1150** units.
  Joining on the empty string reconstructs **1053**, and on the other 97 fabricates a token
  present in no committed record, such as `this Regulation.For example` and `AI models.They
  should`.

Under the previous join, 144 raw segments straddled an inter-chunk boundary and 141 survived into
the comparable segmentation the committed cache embedded. Two tests pin the repair: one asserts
source reconstruction on all 1150 units, the other that no comparable segment of a multi-chunk
unit is absent from every one of that unit's chunk records.

## One segmenter, both arms

`comparable_segments` is the only segmentation in the module and both arms consume it. Two
segmenters would let a pick pass one arm and fail the other for a segmentation reason, and neither
result would mean anything. A test asserts the dense cache's segment order and the lexical arm's
walk are the same list.

## The exclusion funnel

Reported in every scan block rather than performed silently, so a reviewer sees the whole funnel
and can disagree with a predicate on the record.

| Stage | Before | After |
| --- | --- | --- |
| Starting population, raw segments over 1150 units | 14,626 | **14,770** |
| Removed: carries no alphabetic word | 1,057 | **1,113** |
| Removed: is its own unit's recorded heading | 341 | 341 |
| **Comparable segments** | 13,228 | **13,316** |

The heading count is unchanged because a unit's own label is a whole segment either way; the
newline neither creates nor destroys one. The alphabetic-word count rises because splitting the
144 straddling segments exposes 56 fragments that carry no alphabetic word.

**The alphabetic predicate** was added after the twelve-row check found bare paragraph numbers
matching: `1.` against `1.` scores 1.0. The module had argued no length filter was needed because
a short segment cannot reach the floor against a long span. That holds for a long designated span
and is false for short against short. It was a belief written down as a measurement, in a
docstring, justifying skipping the check that then caught it.

**The heading predicate** is byte identity against the unit's own `unit_label`, recorded per chunk
in `data/chunks/<doc>.chunks.jsonl`. Not a cut point: a length rule or a score cutoff would be
fitted, because its threshold is chosen by looking at where the offenders fall. Byte identity
against committed metadata is a structural fact knowable without seeing a single pair.

Enumerated over all 1150 units, not sampled, and re-enumerated over the repaired segmentation with
the same result:

- 341 segments equal their own unit's label. Longest is 17 characters, maximum two words, and
  none exceeds six words, so none can carry a claim.
- A further 16 segments equal some **other** unit's label. The predicate is own-label only, so
  these are kept. A broad any-label form would remove all 16.

An earlier report claimed no content segment matches any label. That claim rested on one content
segment rather than an enumeration, and is corrected here.

## Reproduction of the twelve committed blocks

`python -m src.goldset.check_committed_duplication_scans`, read-only over
`eval/test_query_verification.jsonl`.

**12 of 12 rows reproduce**, on both `top_ratio` and pair count, under the repaired segmentation
and under the previous one. That the repair costs nothing here was measured before the repair
landed.

MARKED CORRECTION, autojunk. This paragraph read that test_16's committed 0.996 and 0.821 both
re-derive to three decimals, and that the other eleven rows carry `top_ratio: null` with an empty
pair list. Both figures are superseded. `difflib.SequenceMatcher` defaults to `autojunk=True`,
which junks characters appearing in more than one percent of the second sequence once it reaches
200 elements and so makes a similarity score depend on the length of one side; every ratio is now
built through `src.goldset.attributability.ratio_matcher` with autojunk disabled. Re-measured
whole under the corrected predicate rather than adjusted: test_16 carries three pairs at 0.996,
0.951 and 0.696, its 0.821 superseded by 0.951; test_10 carries one pair at 0.671 where it
carried none; and the twelve blocks are **ten empty and two non-empty**, not eleven and one. The
positive control is stronger for it, two rows now demonstrating the instrument firing where one
did before. No verdict moves: the duplication verdict rests on whether the designated answer
sentence occurs in both endpoints, and on neither row does it appear as the target of any
corrected pair.

An earlier run of the same check, before the heading predicate, diverged on eleven of twelve by
exactly one pair each. Every one of those was a unit heading matching another unit heading, such
as `Article 43` against `Article 97` at 0.8 and `ANNEX VIII` against `ANNEX III` at 0.9474, which
the record rounds to 0.947. Not one was content. The heading predicate accounts for the whole
divergence. Both values were re-derived over the repaired segmentation and are unchanged.

### The period-only control column is weak, measured

That checker prints a period-only column beside the shipped one so a divergence is attributable to
segmentation rather than left ambiguous. Measured over the twelve rows, that column carries less
attribution than its presence implies, and this was true before the repair was contemplated.

- Its top ratio is **1.0 on eight of the twelve rows**, in both segmentations. The remaining four
  return no pair at all.
- The 1.0 values come from bare paragraph numbers matching each other, `2.` against `2.`, which is
  the exact artefact `carries_alphabetic_content` exists to remove. The period-only column does
  not apply `comparable_segments`, so no such filter runs on it.
- Under the repaired join the column moves on **two of twelve rows**, test_09 from 4 pairs to 5
  and test_15 from 11 to 15. No top ratio changes and no null becomes a value. The added pairs are
  more bare paragraph numbers.
- Corpus-wide the period-only segment count goes from 7,690 to 7,771.

**The control is not being changed.** Changing a control after measuring what it does is fitting
it to that measurement. It is recorded here as a measured limitation of a committed instrument: a
column saturated at 1.0 by segmentation debris has little attribution to lend, whichever
segmentation it runs over.

## The dense arm is segment-level, and why

Built first against committed chunk embeddings, as originally specified, and measured to fail.

On the case A span, a chunk-level dense arm ranks the known partner `eu_ai_act:art_72` at **207 of
1149**, cosine 0.5895, while the lexical arm ranks it **first at 0.9397**. The span is 123
characters and `art_72` is 2318, so **5.3 percent** of the text carries the match and the
remaining 94.7 percent sets the direction. `art_72` is a single-chunk unit, so its length is
unchanged by the join.

That matters most where the arm was needed most. Recital units in the corpus run **145 to 4,448
characters at a median of 1,030**, against an answer that can occupy one sentence, so paraphrase
inside a recital carries the same dilution. The maximum moved by one character under the repair,
from 4,447, because the longest recital is a multi-chunk unit and gained its newline back.

Stated as a corpus statistic rather than as a property of the drawn units, deliberately. An
earlier draft asserted that recitals run 1,200 to 3,200 characters, which the corpus does not
support: only 68 of 180 fall inside that band and the median sits below its floor. The obvious
repair, restating the band over the recital units actually drawn, was rejected on a second ground:
this record lands before any single-hop query text or rejection row exists, so naming a drawn set
would pre-announce picks that screening may reject, and the record would then describe a set that
changed. The corpus statistic makes the same argument with no forward reference.

Segment embeddings put both arms on the same footing. The wrong prediction and its measurement are
recorded in the test docstring rather than deleted.

## Reproducibility levels, stated per arm

- **Lexical arm, level 1.** Exact from committed files, no model, no key.
- **Dense arm, level 3.** Regenerating from ONNX at the pinned revision reproduces rankings, not
  bytes. The pinned model is deliberately outside the offline reproducibility set, so a reviewer
  without it re-derives the lexical arm exactly and the dense arm not at all. When the model is
  absent the block records `ran: false` with a reason rather than omitting the arm.

The segment embedding cache is not committed, on size: 40,906,752 bytes at 13316 segments by 768
float32, which is 10.3 times the committed chunk embeddings at 3,975,296. This is **not** the
pattern the retrieval artifacts follow. `data/retrieval/embeddings.npy` is committed, and that is
exactly what lets retrieval reproduce at level 2 with no model. Declining to commit here is a size
decision, and its cost is that the dense arm sits at level 3 instead. The generator, the pinned
model revision and the per-pick output commit.
The cache records a fingerprint of the exact segmentation it was built from, and a stale cache
raises rather than scoring text nobody is comparing any more. Nothing in the module or the
generator reads or writes anything under `data/retrieval/`.

The cache for the repaired segmentation was generated twice from a clean state, 20.7 and 24.4
minutes of wall time apart in elapsed cost. The array is byte-identical across both,
`186a1ffdf7cd1860e21a10e2a7ee5f1bbb360c6b3ecbc4104fcf2ed84013bba2` at 40,906,880 bytes, and the
committed manifest is byte-identical across both, so the recorded `cache_sha256` is an oracle
rather than a record of one run.

**One file in the cache is not byte-deterministic, and it is not the one the digest covers.**
`segment_index.json` differed between the two generations, at 1135 bytes each. Its only field that
is not derived from the corpus or the pinned configuration is `build_seconds`, which records wall
time, and every other field, including `n_segments`, the exclusion funnel and
`segmentation_fingerprint`, was identical. The index is untracked and no committed value depends
on it. Recorded here because a determinism claim that quietly means "one of the two files" is the
kind of claim this record exists to prevent.

MARKED CORRECTION, the index dependency. The last sentence but one of that paragraph read that
the index is untracked and **no committed value depends on it**. Two did. The manifest generator
read the index and copied `n_segments` and `n_units` out of it into
`eval/segment_embedding_manifest.json`, which ships. The claim was disproved by mutation rather
than by reading: moving `n_segments` to **13317** in the untracked index and re-running the
generator's own `write_manifest` moved the committed manifest to 13317, where it contradicted the
corpus-derived `comparable_segments` of 13316 in the same file, and nothing raised. The exposure
was asymmetric between the two fields. `n_segments` was re-derived from the corpus by
`test_manifest_matches_the_cache_it_describes`, but that test skips when the cache is absent and
the cache is untracked, so the only committed re-derivation never ran for a reviewer who clones
the repository. `n_units` was re-derived by nothing at all.

Corrected in the code rather than in the sentence. `write_manifest` now derives `n_segments` and
`n_units` from the corpus under `data/chunks/`, cross-checks the segment count against the cache
array's row count, and refuses to emit a manifest when the array is absent. The index is read for
the staleness fingerprint alone, a guard that can only refuse, and no value it carries reaches the
committed file. `build_seconds` is removed from the index, so the file is now a function of the
corpus and the segment count alone and the determinism claim covers both files rather than one.
The committed manifest's bytes did not move: the derivation changed and the values did not, at
2403 bytes and `3a2f5de26ea2fea292f83628e15a97b6020c005d7b95a98e9fa14b17fa6ef266` before and
after. Pinned by `tests/test_attributability.py::
test_the_manifest_takes_no_value_from_the_untracked_index`, shown red against the previous
generator on the 13317 mutation and green against this one.

## What this closes

One sealed artifact shipped two verification block types under two standards. The adversarial
`absence_checks` blocks carry `command`, `predicate`, `target`, `result` and `control`. The twelve
`duplication_scan` blocks carried none of those, and eleven of the twelve reported
`top_ratio: null` with an empty list, so eleven of twelve carried no re-derivable content at all.

Tense-marked and corrected, autojunk. The eleven-of-twelve figure describes the artifact as it
stood when this record was written. Under the corrected predicate the split is ten and two, since
test_10 gains a pair at 0.671. The sentence is tense-marked rather than deleted, because it states
what the defect was at the moment it was found, and the count that was true then is what makes the
defect legible.

That is a reproducibility defect and not a V20 breach. The rejection log's two rows show the check
firing and killing two picks, so it was capable of failing and did. The verdicts rest on
individual verification of a designated answer span, not on a ratio. What cannot be reproduced is
the evidence, not the judgment.

Every block this module emits carries its own `predicate`, `command` and `reproducibility_level`.
