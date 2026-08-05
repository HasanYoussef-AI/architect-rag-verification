# Attributability scan, calibration record

The record behind `src/goldset/attributability.py`. It states what the instrument was calibrated
against, what reproduced, what did not, and the one gap that is recorded as a gap rather than
reconciled.

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

0.9397 rounds to the published 0.940.

**Hyphen folding is load-bearing, not cosmetic.** The pair differs by `law-enforcement` against
`law enforcement`, and without the fold the value is 0.931. A test pins that the unfolded form
gives 0.931 and misses.

## Case B: does not reproduce, and the gap stands

Annex IV point 3 against Article 13(3)(d), published at **0.894**. The instrument derives
**0.8982**.

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

**The verdict does not move.** Both values clear the 0.60 floor and the pick stays rejected as
`answer_duplicated_across_endpoints` for the same reason, so the number is exposition and the
verdict is robust to it.

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
It stays buried in a 768-character span and the best reachable ratio against Article 13(3)(d) is
**0.2968**, far below the floor. The pick passes and the detector reports nothing on the very case
it exists to catch.

Segmenting on semicolons as well reaches **0.8982** on the same pair. Both the blind form and the
shipped form are driven over the same pair in
`test_period_only_segmentation_is_blind_to_the_published_case`, so the shipped form is trusted
only on a pass it has been shown able to withhold.

## One segmenter, both arms

`comparable_segments` is the only segmentation in the module and both arms consume it. Two
segmenters would let a pick pass one arm and fail the other for a segmentation reason, and neither
result would mean anything. A test asserts the dense cache's segment order and the lexical arm's
walk are the same list.

## The exclusion funnel

Reported in every scan block rather than performed silently, so a reviewer sees the whole funnel
and can disagree with a predicate on the record.

| Stage | Count |
| --- | --- |
| Starting population, raw segments over 1150 units | 14,626 |
| Removed: carries no alphabetic word | 1,057 |
| Removed: is its own unit's recorded heading | 341 |
| **Comparable segments** | **13,228** |

**The alphabetic predicate** was added after the twelve-row check found bare paragraph numbers
matching: `1.` against `1.` scores 1.0. The module had argued no length filter was needed because
a short segment cannot reach the floor against a long span. That holds for a long designated span
and is false for short against short. It was a belief written down as a measurement, in a
docstring, justifying skipping the check that then caught it.

**The heading predicate** is byte identity against the unit's own `unit_label`, recorded per chunk
in `data/chunks/<doc>.chunks.jsonl`. Not a cut point: a length rule or a score cutoff would be
fitted, because its threshold is chosen by looking at where the offenders fall. Byte identity
against committed metadata is a structural fact knowable without seeing a single pair.

Enumerated over all 1150 units, not sampled:

- 341 segments equal their own unit's label. Longest is 17 characters, maximum two words, and
  none exceeds six words, so none can carry a claim.
- A further 16 segments equal some **other** unit's label. The predicate is own-label only, so
  these are kept. A broad any-label form would remove all 16.

An earlier report claimed no content segment matches any label. That claim rested on one content
segment rather than an enumeration, and is corrected here.

## Reproduction of the twelve committed blocks

`python -m src.goldset.check_committed_duplication_scans`, read-only over
`eval/test_query_verification.jsonl`.

**12 of 12 rows reproduce**, on both `top_ratio` and pair count. test_16's committed 0.996 and
0.821 both re-derive to three decimals. The other eleven rows carry `top_ratio: null` with an
empty pair list and the instrument finds nothing on any of them.

An earlier run of the same check, before the heading predicate, diverged on eleven of twelve by
exactly one pair each. Every one of those was a unit heading matching another unit heading, such
as `Article 43` against `Article 97` at 0.8 and `ANNEX VIII` against `ANNEX III` at 0.947. Not one
was content. The heading predicate accounts for the whole divergence.

## The dense arm is segment-level, and why

Built first against committed chunk embeddings, as originally specified, and measured to fail.

On the case A span, a chunk-level dense arm ranks the known partner `eu_ai_act:art_72` at **207 of
1149**, cosine 0.5895, while the lexical arm ranks it **first at 0.9397**. The span is 123
characters and `art_72` is 2318, so **5.3 percent** of the text carries the match and the
remaining 94.7 percent sets the direction.

That matters most where the arm was needed most. Recital units in the corpus run **145 to 4,447
characters at a median of 1,030**, against an answer that can occupy one sentence, so paraphrase
inside a recital carries the same dilution.

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

The segment embedding cache is not committed, on size: 40,636,416 bytes at 13228 segments by 768
float32, which is 10.2 times the committed chunk embeddings at 3,975,296. This is **not** the
pattern the retrieval artifacts follow. `data/retrieval/embeddings.npy` is committed, and that is
exactly what lets retrieval reproduce at level 2 with no model. Declining to commit here is a size
decision, and its cost is that the dense arm sits at level 3 instead. The generator, the pinned
model revision and the per-pick output commit.
The cache records a fingerprint of the exact segmentation it was built from, and a stale cache
raises rather than scoring text nobody is comparing any more. Nothing in the module or the
generator reads or writes anything under `data/retrieval/`.

## What this closes

One sealed artifact currently ships two verification block types under two standards. The
adversarial `absence_checks` blocks carry `command`, `predicate`, `target`, `result` and
`control`. The twelve `duplication_scan` blocks carry none of those, and eleven of the twelve
report `top_ratio: null` with an empty list, so eleven of twelve carry no re-derivable content at
all.

That is a reproducibility defect and not a V20 breach. The rejection log's two rows show the check
firing and killing two picks, so it was capable of failing and did. The verdicts rest on
individual verification of a designated answer span, not on a ratio. What cannot be reproduced is
the evidence, not the judgment.

Every block this module emits carries its own `predicate`, `command` and `reproducibility_level`.
