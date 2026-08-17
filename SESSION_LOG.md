# Session log, architect-rag-verification

Running log owned by Claude Code. One entry per unit of work, naming the commits
it covers, per CLAUDE.md Rule 11. A new session should be able to resume from the
last entry here plus the governance files alone. Newest entries at the top.

## 2026-08-14, single-hop stratum committed, eighteen rows across three sources

The stratum closes at its allocation on every source: eleven `eu_ai_act`, five `nist_ai_100_1`
and two `nist_ai_600_1`, drawn from eligible populations of 298, 109 and 24. Nine picks were
rejected, six on the EU source and two and one on the NIST sources, under three of the four
codes the vocabulary fixed before the first pick was screened: `unit_defers_for_substance` on
four, `answer_attributable_outside_slot` on three, `no_designable_span` on two.
`needs_two_slots` has never fired. Five picks fell at screening and four at authoring. Slot
widths over the accepted rows are thirteen at one member, two at two and three at three.

Each source's selected set reconstructs from its own committed draw order plus the rejection log
alone, and now at exactness rather than as a bound, because each stands at its allocation. The
subset form the check falls back to exists for a stratum authored in batches and is not a
weaker claim held permanently.

Rejected picks ship the full screening record with the verdict as a field, rather than the
narrow draw-order row clean multi-hop used. That stratum carried structured evidence on its
acceptances and prose on its rejections, so a reader could not tell whether the same evidence
was gathered on both sides. The nine rejection rows carry the same arms, the same funnels and
the same slot derivation as the eighteen acceptances, which is what puts the conservatism in the
tree instead of in a claim about it.

Every assertion the rows are judged by was committed before any row existed. The reason is not
tidiness: a check landing beside the rows it judges cannot be distinguished from a check written
to fit them, which is the condition `a996d65` was in and which `6e3c0ce` corrected for the
reconstruction. Two committed checks were wrong and were corrected under that ordering rather
than after the data arrived. The draw-order key extractor asserted that a row's gold names
exactly one candidate of its source, which fails on two rows whose slots carry a second unit
that is itself eligible in the same document; the recorded `drawn_unit` disambiguates, and the
derivation stays the sole authority where the intersection is a singleton, so a record
disagreeing with a determined draw fails rather than redirecting it. The rejection log's
`matcher_revision` requirement had never met a row lacking it, all nineteen rows then in the
file being clean multi-hop, so it could not have failed; it is scoped to that stratum and
asserted absent outside it, with `matcher_recheck` required present and not required non-empty,
because over those nineteen rows it is present on nineteen and non-null on six and a
non-emptiness rule would have failed thirteen committed rows.

One producer defect was found in committed code and fixed before the rows landed. The
self-containedness calibration took its population as every row of
`eval/test_frame_rejections.jsonl` and reported `starting_population` as that file's length. The
file holds every drawing stratum's rejections, so the figure would have moved from 19 to 25 the
moment an unrelated stratum wrote there. The role split was already confined to its own rows in
effect, since no other stratum uses `source_points_only` or `target_defers_out_of_corpus`, and
its arms do not move; but a filter by effect is not a filter, and the same function unpacks
`rejected` as an ordered source and target pair, which a bare unit id would not survive. The
stratum is now named in code as artifact, field and accepted value.
`eval/self_containedness_calibration.json` re-derives byte-identically and the committed 19
stands unedited. A regression pins it in two halves: a control drives the scoping predicate over
constructed rows of two strata, and the half derived from the file reports a named skip while
the file holds one stratum and goes red if it ever stops holding another. The general rule taken
from this is that a committed producer reading a shared artifact states its population as
artifact, field and accepted values. The other committed reader of a shared artifact was
measured against that rule and states its population already.

Recorded ratios ship under a per-entry predicate drawn from a closed set of three, and no
recorded value was recomputed. Three instruments had run at three stages of screening while the
record disclosed none of them, so one field name carried three different quantities and no single
predicate reproduced the population: six entries are the designated span against the member
unit's best comparable segment, seven the span against the member's whole text, and one the pick
unit's text against the member's text under the comparison-time normalisation. That last is the
0.9338 the carrier standard's refusal of the Playbook GOVERN 1.3 unit rests on, and it now
reproduces from committed code. Unifying the three would have recomputed recorded measurements
to satisfy the check that judges them, and dropping the figures would have left the carrier
standard quoting a number the tree could not produce, which is the condition the 0.894
retraction was the cost of. The disclosure is the repair. One entry reproduces under two of the
three, because its member unit holds a single comparable segment so its best segment and its
whole text are the same string; that entry names the predicate its sibling classifies under, on
the ground that one instrument ran on both members of a pick at one stage, and labels the
assignment an inference rather than a measurement.

Three instrument-wide tables were removed from the rows. They measure how far the
self-containedness detector reaches across the corpus and how the segmenter behaves per
document, which are properties of the instrument rather than of the row, and they belong to
reporting. One figure that lived in the removed material, the register-arm base rate re-derived
with the backfill unit excluded, is not restated anywhere on the row: its only producer is
untracked, and a number with no committed producer does not ship as a number. Its re-derivation
is owed at the sealing boundary, where both base rates ship with their pick sets named. Removing
the tables left `eu_ai_act:rct_87`'s calibration exposure pointing at a field the row no longer
carries; the clause now points at the committed calibration artifact, and the row carries a
marked correction saying what moved and that no figure did.

`nist_ai_600_1:sec_A.1` is the only rejection on its source, so the entry it admitted is
individually determinate: `nist_ai_600_1:sec_2.4` enters that walk because this rejection
removed `sec_A.1` from it. Its `selected_instead` is null by the convention that holds across the
stratum rather than by derivation, and the row says which. On a source carrying more than one
rejection the null is derived, because the walk stops once the source has its allocation and
every rejection there resolves to the same marginal entry, so a per-row value would invent a
distinction the walk does not support. The disclosure is emitted wherever a source carries
exactly one rejection rather than written onto a named row.

Every rejection row names the field its prose reason came from, because the source differs by
the stage at which the pick fell. The five rejections at screening draw on the human verdict
recorded inside the self-containedness record, which that record marks as the one part no
committed method covers: a judgment rather than a computed output, sitting beside two arms that
do have committed methods. Three of the four rejections at authoring draw on the sufficiency
result. The fourth, `eu_ai_act:rct_74`, reached authoring in an earlier pass and its sufficiency
result was recorded there rather than in the screening record the row is built from; its reason
is taken from the distinguishing-term test, the instrument that carried the rejection, and the
absent block is disclosed on the row rather than reconstructed.

The eleven `eu_ai_act` rows rewrote the twenty verification rows already committed, adding the
null `single_hop` block that keeps one key set across the file. No model answer exists, so
nothing scored was disturbed.

Commits:
- 5c78d5a docs(methodology): cross-reference the attributability calibration record
- 69b4a86 test(eval): assert the single-hop row properties before any row lands
- cf7ad28 fix(goldset): scope the calibration population to its own stratum
- ac93eed feat(eval): the eleven eu_ai_act single-hop rows with their screening records
- 6bb7878 feat(eval): the seven NIST single-hop rows, completing the stratum

This entry is placed by the commit that follows `6bb7878` and touches only `SESSION_LOG.md`.

## 2026-08-08, Corpus rejoined on the newline the chunker recorded

`Corpus.load` built a unit's text by concatenating its chunk records with no separator. The
chunker had written a newline between blocks and the reader dropped it, so on 97 of the 1150 units
the reconstructed text contained tokens present in no committed record: `this Regulation.For
example`, `AI models.They should`. The segmenter's boundary pattern requires whitespace after a
terminator, so it did not split at those points, and 144 raw segments straddled an inter-chunk
boundary with 141 surviving into the comparable segmentation the committed cache embedded.

The newline is not a separator chosen for its effect. Three independent lines fix it: every one of
the 144 inter-chunk gaps in the four `normalized.txt` files is exactly one newline with no other
value observed; `BLOCK_SEPARATOR` in the ingest modules is that same value, because it is what
ingest wrote; and joining on it reconstructs each unit's slice of the normalised source on 1150 of
1150 units, against 1053 for the empty join. Framing the change as inserting a separator was
rejected on that evidence. It restores the corpus text.

Repairing was chosen over disclosing. The decisive evidence is that all twelve committed
`duplication_scan` blocks reproduce identically under both segmentations, measured before the
change landed, so the repair costs nothing in sealed-set churn. An earlier argument for repair,
that the previous segmentation suppressed real candidates at better than three to one on 442 pairs
gained against 135 lost, was withdrawn: the counts are measured but the gained pairs are dominated
by bibliography fragments in the playbook reference sections, and the word describing them as real
was never measured. What the repair actually buys is source fidelity and case B.

Case B surfaces. Comparing Annex IV against Article 13 segment by segment, the previous
segmentation returned no pair and the repaired one returns two. The first is
0.8935064935064935, rounding to the published 0.894, with its Annex IV side inside point 3 and its
Article 13 side inside 13(3)(d). The second returns 0.721 and fails the span criterion, its Annex
IV side sitting in point 2(e).

That reproduction is not fitted, on three checkable grounds. The target predates the repaired
segmentation: `0.894`, `Annex IV point 3` and `Article 13(3)(d)` are all in the
`src/goldset/attributability.py` docstring at `c2106e5`, and `CASE_B_PUBLISHED = 0.894` is a
constant in the tests at the same commit. The defect was found while building an unrelated
instrument under an instruction to report and not fix, and the entry recording it at `6cc9e6c`
contains no occurrence of `case B`, `0.894`, `Annex IV`, `art_13`, `13(3)`, `supersession` or any
decimal matching `0.\d{2,4}`, against positive controls of `141`, `13228`, `14626`, `fabricated`
and `segmentation` in the same entry. And the span criterion rejected an available alternative at
0.721. The residual is stated rather than glossed: the reproduction test was fixed after the ratio
had been reported, so the number was known and could not have failed, while the spans were not
known and could, and did. The test was not blind.

The `ratio_supersession` stands. A superseded number returning under a different segmentation is a
finding about the segmentation, not a reinstatement, and settling it needs a designated span that
does not exist.

The exclusion funnel moved to 14,770 raw, 1,113 removed as carrying no alphabetic word, 341
removed as own headings and 13,316 comparable. The arithmetic closes: splitting 144 straddling
segments exposes 56 fragments with no alphabetic word, and 144 less 56 is the 88 the comparable
count gained. Re-derived and unchanged across the repair: 1150 units, 341 own-label and 16
other-label segments, twelve of twelve blocks reproducing, test_16 at 0.996 and 0.821, superseded
to 0.996 and 0.951 by the later autojunk correction and marked there, the
772-character Annex IV point 3 block and its 768-character period-only span, 0.2968, superseded to
0.3621 by the later autojunk correction and marked there, 0.8982, unmoved by it, and
the pre-heading-predicate values 0.8 and 0.9474. The whole case A normalisation table compares two
committed literal strings and never touches `Corpus`, so it could not move; the calibration record
states that rather than presenting it among the re-derivations.

The period-only control column in `check_committed_duplication_scans` is weak and is recorded as
weak rather than repaired. Its top ratio is 1.0 on eight of the twelve rows in both segmentations,
from bare paragraph numbers matching each other, which is the artefact `carries_alphabetic_content`
exists to remove and which that column does not apply. Under the repair it moves on two rows,
test_09 from four pairs to five and test_15 from eleven to fifteen, adding more of the same, with
no top ratio changing and no null flipping. Changing a control after measuring what it does would
fit it to that measurement.

Measuring that column before the change was ordered on the ground that measuring afterwards would
lose the attribution. That ground does not hold, and the correction is recorded because it was a
claim about how the code behaves: both conditions reconstruct from the frozen chunk records by a
one-character difference in the join, in either order, and nothing is lost by measuring later. The
ordering was kept on V16 and V19, that a measurement committed before a change cannot be shaped by
it and a result stated beforehand can contradict the plan.

The cache was regenerated twice from a clean state. The array is byte-identical across both at
`186a1ffdf7cd1860e21a10e2a7ee5f1bbb360c6b3ecbc4104fcf2ed84013bba2`, 40,906,880 bytes, and the
committed manifest is byte-identical across both. `segment_index.json` is not, at 1135 bytes each,
and the difference is its `build_seconds` field alone; every other field it carries, including
`n_segments`, the funnel and the segmentation fingerprint, was identical. The index is untracked
and no committed value depends on it. Recorded because a determinism claim that quietly covers one
of two files is the failure this kind of note exists to prevent.

A stale size string was caught by sweeping rather than by reading the diff: the manifest generator
carried `40.6 MB` in a description it emits into the committed manifest, which then contradicted
the `cache_bytes` field in the same file.

Two regression tests pin the join. One asserts unit text reconstructs the normalised source on all
1150 units; the other that no comparable segment of a multi-chunk unit is absent from every one of
that unit's chunk records. Reversing the join fails both.

Commits:
- 769f6ea fix(goldset): join a unit's chunks with the newline the chunker recorded

This entry is placed by the commit that follows `769f6ea` and touches only `SESSION_LOG.md`.

## 2026-08-07, self-containedness candidate generator, and the segmentation artifact it surfaced

Eighteen single-hop rows require an enumeration of every phrase pointing outside the unit, each
quoted with its chunk id and verdicted a signpost or a dependency, with a funnel. Several of the
eleven EU picks were expected to terminate that funnel at zero. No committed method for the
property existed: `self.contain` and `points_only` appear across the tracked tree only as recorded
data in `eval/test_frame_rejections.jsonl` and as prose in this file.

The argument for committing an instrument is V10, not V7. A number carrying its method is the
weaker case here, because the deliverable is a census with a human verdict on each item rather
than a score, and V11 is already satisfied by the quote sitting beside the verdict. The exposure
is that a human enumeration has no starting population, so a zero funnel cannot be distinguished
from an unlooked-at funnel. What `src/goldset/self_containedness.py` produces is the denominator.
Optimising its judgment was explicitly not attempted, because it has none.

Chunk records are the artifact of record, read per record. `attributability.Corpus` was rejected
as the reader. It builds unit text by concatenating chunk text with no separator, and across the
64 multi-chunk `eu_ai_act` units outside the eleven picks, 90 adjacent chunk pairs join with no
whitespace on either side, fabricating tokens that appear in no committed record: "this
Regulation.For example", "AI models.They should". A candidate matched across such a join could
not be attributed to a `chunk_id`. Every candidate now carries offsets that slice its own record
back to its own surface, checked exhaustively over 2760 candidates rather than sampled.

`data/chunks/eu_ai_act.xrefs.jsonl` was also rejected as an input. It is precision tuned and drops
32 matches by design, which is backwards for a recall-tuned generator, and keeping the instrument
to unit text alone means no question arises about a screening instrument reading a relation that
defines gold for another stratum.

Three arms with stated scope, and the third states that it has none. Arm 1 covers named pointers
in three classes. The external-instrument class is named explicitly rather than reached through an
adjacent locution, because the admissibility ruling makes a unit inadmissible where it defers to
an instrument the corpus does not contain, and a bare naming with no locution would otherwise be
invisible; the three committed `target_defers_out_of_corpus` positives carry exactly that surface
and are pinned as its test. Arm 2 covers defined-term deference against a 67-term inventory
derived from `eu_ai_act:art_3`. Arm 3 covers unnamed substantive deference, has no committed
method, and records that as an explicit gap. A predicate over purposive prose either fires on
substantially all recitals or is fitted to the observations it would judge, which V15 bars.

The row carries four named parts and the roll-up is not their conjunction. Two empty funnels plus
an unverdicted third part is not a verified property, and a committed method lends a zero an
authority it did not earn. The emitted block states that in its own text rather than leaving a
reviewer to infer it.

Arm 2's scope is bounded by Article 3 and the bound is not where it would be assumed. "high-risk
AI system" is not an Article 3 definition, classification living in Article 6, and it occurs in
120 of the 295 non-pick `eu_ai_act` units that this arm does not reach on that ground. The limit
is pinned by a test so it is visible in the suite. Reading the definitions unit by prefix rather
than by exact id pulls in `art_30` through `art_39`; the inventory count is unchanged at 67
either way, because those ten articles carry no quoted-term-plus-means construction, so the
regression pins foreign text entering the read rather than a count difference that does not exist.

Two calibration criteria were corrected before implementation. The first required every unit named
in ten rejection rows to produce a candidate, but `rejected` is ordered as citing source then
cited target, and on the six `source_points_only` rows the record characterises the target as
answering without reference back. The criterion therefore required the instrument to contradict
the record on six of eighteen units. The role split is twelve positives and six negatives, derived
from `reason_code` rather than named. The six negatives bound a claim about the verdict step and
not about the instrument: arm 1 fires on all six, on references unrelated to the rejection, and
what they control is that a verdict protocol reading every named reference as a dependency would
flag all six and be visibly wrong.

The second criterion proposed the two recital-sourced entries of the internal cross-reference
draw order as a register control. Both are in that relation precisely because their text names
Article 26, so selecting them selects on the property under test, and the blindness the control
existed to catch would pass through it. They are retained as a floor check on arm 1, with that
limit recorded, and the register claim moved to the 145 held-out recitals carrying no named
reference, that population defined by arm 1's own class and fixed before the distribution was
observed.

Calibration ran on held-out units only, with the eleven picks removed as the first filter of every
enumeration. Twelve of twelve positives produced a candidate. Arm 2 fired on 131 of the 145
register units, against a prediction of a large majority recorded before the run. Fourteen of
those 145 produced nothing from arm 2 and 51 produced nothing from arm 1, but the two sets overlap
on only six: `rct_4`, `rct_45`, `rct_98`, `rct_142`, `rct_144` and `rct_150`. Those six are the
population where a row would ship two empty funnels and the whole question would rest on the arm
that has no method. The count was first written as fourteen by taking the arm 2 zeroes for the
intersection without measuring it.

The near-absence of recitals from the internal cross-reference relation is a property of the text
and not of the builder. `src/ingest/xref.py` applies no source-kind filter, and a synthetic
recital-register sentence naming an Article of this Regulation yields an internal edge, so the
builder is capable of emitting one. Of 180 recitals, 149 carry no Article or Annex surface form at
all, and of the 31 that do, 54 of 68 matches are qualified to an external instrument. A zero-edge
reading on a recital is therefore a true measurement of a much narrower property than
self-containedness, and nothing about admissibility should rest on it.

One measurement is reported rather than fixed, on the owner's instruction. The committed
attributability segmentation consumes concatenated unit text, reproduced here on all 1150 units,
and the boundary pattern requires whitespace after a terminator, so it does not split at a
fabricated join. 144 of the 14626 raw segments span one, and 141 survive into the 13228
comparable segments, 1.07 percent of the embedded segmentation. The recomputed raw total matches
the manifest's `starting_population` exactly and the recomputed fingerprint matches
`segmentation_fingerprint` exactly, so the manifest describes a segmentation with those 141
segments in it and the committed cache embedded them. A control over units whose joins carry
whitespace found none, so the measurement discriminates. Eighteen rows will ship attributability
output over that segmentation.

Recorded before any designation: four of the six recitals among the eleven picks carry no named
Article or Annex reference. This was arithmetic over the committed cross-reference evidence field,
not a run of this instrument, which has never been evaluated against a pick. It is recorded rather
than buried, and the design was frozen against criteria that do not depend on it.

Commits:
- ee8e497 feat(goldset): add the self-containedness candidate generator with its calibration

This entry is placed by the commit that follows `ee8e497` and touches only `SESSION_LOG.md`.

## 2026-08-06, carrier attribution corrected in a shipped docstring

The `_bare_unit_key` docstring credited the frame with recording the GOVERN 1.3 statement as
carried by `nist_ai_100_1`, `nist_ai_600_1` and `nist_playbook` units. The frame's
`cross_stratum_gold_govern_1_3` finding names two, `nist_ai_100_1:sub_GOVERN_1.3` and
`nist_ai_600_1:sub_GOVERN_1.3`, and states that one slot is satisfied by either carrier. A
reviewer opening the frame to check that sentence finds two where the docstring claimed three.

The playbook carrier is a real unit and is named by `structural_join` in all three relations
files, on the basis of a same printed subcategory identifier. It is named by neither the
duplication map nor `data/retrieval/verbatim_groups.json` nor the frame's finding, and
`structural_join` is barred as a gold source by the pre-registration, so it is not a gold
relation. The correction states no provenance for it at all. The argument the docstring exists to
carry does not need it: `nist_ai_600_1:sub_GOVERN_1.3` carries the same statement and is not a
candidate of the `nist_ai_100_1` source, which is what establishes that a slot may name carriers
outside its source and that `expected_units` cannot therefore be the key.

A second clause in the same sentence placed the draw among the eighteen. That is true of the draw
and false as soon as screening rejects the pick and a backfill enters, which is a decision the
next scope makes. It now reads as the draw index, invariant under any rejection.

Fixed forward. Rule 10 permits no rewrite of committed history and states that a defect there is
fixed forward or lived with, with no exception for an unmerged branch.

One false positive, caught by the check that resolved the question. A substring count reported
five occurrences of `nist_playbook:sub_GOVERN_1.3` in the frame and four in
`data/retrieval/verbatim_groups.json`, which would have contradicted the finding. All nine are
`nist_playbook:sub_GOVERN_1.3.ai_transparency_resources`, a different unit that also exists in the
index. Occurrences of the unit id itself are zero in both files. Two real identifiers, one a
prefix of the other, conflated by a substring test.

The same misattributed sentence was carried by the 2026-08-06 entry below, placed at 9a5cc9e, and
is corrected there in place. `SESSION_LOG.md` is a tracked file and editing a past entry in a
later commit is not a history rewrite; the precedent is the scope that corrected eleven false
commit-count claims in this file in place rather than annotating them. A false claim standing in
the log's own voice, with its correction two entries away, asserts something untrue and asks the
reader to keep going to find out. Owner's ruling, overriding the draft-once reading that had left
it marked rather than repaired.

One divergence survives and is not repairable. The commit message at 6e3c0ce still states the
three-carrier version. A commit message is not forward-editable, and Rule 10's two authorised
rewrites are spent, so it stands as written. A reviewer running `git show 6e3c0ce` reads a claim
the frame contradicts, and this paragraph is the account of why. The tracked text is correct in
every file; the divergence is confined to that one message and to the message at dce916e that
quotes it in order to correct it.

Bare-string rejection keys were exercised against the committed walk before the batch that will
produce them. A single-hop rejection injected at draw index 3 of `eu_ai_act` is skipped, the next
unrejected entry backfills in, and the count still equals the allocation of eleven. The committed
log holds no single-hop rejection, so until this was run the serialisation had only ever been
matched for pair-shaped keys.

Commits:
- dce916e fix(test): correct the carrier attribution in the _bare_unit_key docstring

## 2026-08-06, dangling module path corrected, authored-set reconstruction generalised

The `ratio_supersession` field on the `anx_IV` to `art_13` rejection row cited
`src/verify/attributability.py`, and no such file exists. `src/verify/` exists as a tracked empty
`__init__.py`, so the citation resolved to a real package and an absent module, which is the form
a reading is least likely to catch. The module that derives the replacing value is
`src/goldset/attributability.py`, named correctly in `docs/attributability_calibration.md`.

The defect is not orthographic. That row exists to record a retraction, and it asks a reviewer to
accept a re-derived number while naming a file the reviewer cannot open. A retraction whose
instrument cannot be located is the class of claim the row was written to replace.

The correction is the path and nothing else. The superseded 0.894, the replacing 0.8982, the
reason, the reason code `answer_duplicated_across_endpoints`, the draw index and the verdict do
not move, and the retraction is not restated. Hasan-directed, logged here and in the commit
message under Rule 4's discipline. `eval/test_frame_rejections.jsonl` is not one of the artifacts
Rule 4 enumerates, nor one of those the pre-registration's ordering clause lists: it was created
at a996d65 after the frame was sealed at c559130, and `eval/README.md` describes it as the
draw-order rejections for the four drawing strata. It is a committed authoring record read by the
frame's reconstruction test, and the discipline is applied to it as the conservative call.

The set-equality check was hard-coded to the literal pair `("clean_multi_hop",
"eu_internal_xref")`, leaving the other five drawing sources uncovered. It is generalised to run
per source over the frame's own source list, and it lands before any row it will judge on
single-hop, action-to-parent or near-miss exists. The ordering carries the claim: a check that
lands beside the rows it judges cannot be told from a check written to fit them, which is the
condition a996d65 was in, where the committed reconstruction asserted the count and the
not-rejected property and never the set.

The claim is that every candidate a source's rows were authored against is in that source's
reconstruction, with equality once the source's row count reaches its allocation. Bound at every
commit and exactness at completion, the form the row-count test already uses, because a stratum
authored in batches is partial by construction until the last batch lands. It is not vacuous at
landing: clean multi-hop stands at twelve rows against an allocation of twelve, so the exactness
branch is live and the companion has real data to move. A per-source over-fill guard arrives with
it, which the row-count test cannot supply, since that test guards per type and `multi_hop` spans
two frame sources.

What is tabulated is which element of a candidate a row is keyed by, and only that. The join is
derived: frame stratum to row type inverts the committed stratum map, and row subtype is the
frame's source key verbatim. Entry shape does not follow stratum, so it cannot be inferred:
`near_miss/block_clusters` entries are bare unit ids while `action_to_parent/action_subcategory`
entries are pairs, and applying a tuple conversion to a bare id yields a tuple of its sixteen
characters rather than a one-element key. Three sources are absent from the table on purpose,
their row shape being unsettled, so the first row authored against one of them fails rather than
being skipped.

Between-slot order is preserved and within-slot order is not constrained, and a measurement
decides it rather than taste. On one of the twelve committed clean multi-hop picks the reversed
pair is itself a separate draw-order entry, so the pair does not identify its candidate without
its order. Within a slot the sealed rule makes any carrying unit sufficient, so membership is a
set, and naming the drawn unit first would privilege it in the way that rule forbids, since the
first thing a consumer does with a list is take element zero.

The single-hop key is the row's gold intersected with that source's full candidate population,
asserted to be a singleton, rather than the gold itself. A slot may name carriers outside the
source: the frame's own `cross_stratum_gold_govern_1_3` finding records that the statement
single-hop draws at `nist_ai_100_1:sub_GOVERN_1.3` is the same statement action-to-parent draws at
`nist_ai_600_1:sub_GOVERN_1.3`, so one slot is satisfied by either carrier under the any-carrier
gold rule, and the second is not a candidate of the `nist_ai_100_1` source. That draw sits at
index 2 of that source's draw order. Intersecting against the eligibility list rather than the
selection derives the key without consulting the answer being checked.

Two rejections recorded. A prefix assertion over every gold unit on a row whose subtype names a
document was specified and dropped: it fails on that GOVERN 1.3 row, and it would have landed
green, because no single-hop row exists to fire it, then failed at authoring on the one pick the
frame flags as its recorded cross-stratum case. Narrowing it to the extracted key was measured to
assert nothing further, since all 431 single-hop draw-order entries carry their source prefix and
the three sources share no candidate, so a mis-joined row is already caught by the singleton
assertion returning zero. No assertion was kept in its place.

One prediction was wrong. The path sweep was predicted to move from six resolving literals to
seven. It moved from six to six: the corrected path is the literal already cited in the
calibration record, so the distinct-literal count fell from seven to six and that literal now
carries two occurrences. The count that carried the claim, non-resolving one to zero, held.

Commits:
- 5762a6e fix(eval): correct the module path cited in the anx_IV to art_13 supersession
- 6e3c0ce test(eval): generalise the authored-set reconstruction to every drawing source

## 2026-08-06, attributability scan committed, one published ratio retracted

The twelve clean multi-hop rows shipped a `duplication_scan` block carrying a reporting floor, a top ratio and a pair list, with no method, command or control. The `absence_checks` blocks in the same file carry command, predicate, target, result and a shape-matched control. One artifact held two verification blocks under two reproducibility standards, and eleven of the twelve duplication blocks reported an empty result that nothing in the repository could re-derive. The check that produced them was never committed in any form: no similarity implementation appears in the tracked tree, and a pickaxe search over the full history returns no commit that added or removed one.

The scan is now committed with two arms over one segmentation. The lexical arm reports the sequence-matcher ratio between a designated span and every comparable corpus segment, at a reporting floor of 0.60 that decides nothing, and reproduces from committed files alone. The dense arm reports the five highest-cosine non-gold units for every span, at no floor, and requires the pinned embedding model. A fixed count fixed before any observation cannot be fitted to a distribution; a floor chosen after seeing one can. Every block the module emits carries its predicate, its command and its reproducibility level, including the block that records the dense arm as not run.

The segmenter is load-bearing and was selected against two positives published before the instrument existed. A period-terminated segmenter scores the Annex IV point 3 and Article 13(3)(d) pair at 0.2968 against a 0.60 floor, so the check returns nothing on one of the two cases it exists to catch, the failure a detector built the obvious way is most likely to have. Segmenting on semicolons as well reaches 0.8982 on the same pair. The floor was not moved.

MARKED CORRECTION, added under the autojunk correction on Hasan's explicit direction. The blind form's 0.2968 is superseded by 0.3621. Every ratio was built under difflib's `autojunk=True` default, which junks characters appearing in more than one percent of the second sequence once it reaches 200 elements; the 768-character period-only span is far past that threshold, so the blind form's score depended on the length of the span it was blind to. The paragraph's argument is unchanged and rests on the same comparison: 0.3621 is still far below the 0.60 floor, the semicolon companion is unmoved at 0.8982, and the floor was still not moved.

The rejection row for that pair published a ratio of 0.894, and it does not reproduce. Six normalisations return 0.8982 to 0.9005, character and word granularity return 0.8982 and 0.8710, and three span-boundary variants return nothing nearer. The row now carries 0.8982 and names 0.894 as superseded with its reason. The verdict is unchanged: both values clear the reporting floor, and the reason code, the rejection and the draw index stand. The other published ratio, 0.940, reproduces to the digit, which bounds the disagreement to that row rather than to the method. No further diagnosis is available, because the original method was never committed. Hyphen folding is load-bearing on the reproducing case: without it the value is 0.931 rather than 0.9397.

All twelve committed duplication blocks now re-derive. Two ratios on one row, 0.996 and 0.821, re-derive with a matching pair count, and the eleven empty blocks re-derive as empty under a method that fires on the row that is not empty. Eleven emptiness claims that no reviewer could check are now checkable, with a positive control inside the artifact that reported them.

MARKED CORRECTION, added under the autojunk correction on Hasan's explicit direction. The counts in the paragraph above are superseded. `difflib.SequenceMatcher` defaulted to `autojunk=True`, which junks characters appearing in more than one percent of the second sequence once it reaches 200 elements, making a similarity score depend on the length of one side; every ratio is now built through `src.goldset.attributability.ratio_matcher` with autojunk disabled. Re-measured whole rather than adjusted: the twelve blocks are ten empty and two non-empty, test_16 carrying three pairs at 0.996, 0.951 and 0.696 with its 0.821 superseded by 0.951, and test_10 carrying one pair at 0.671 where it carried none. The positive control is stronger for it: two rows now demonstrate the instrument firing where one did. No verdict moves, because the duplication verdict rests on whether the designated answer sentence occurs in both endpoints and it is the target of no corrected pair on either row.

The dense arm was first specified over chunk embeddings and does not work at that granularity. On the 123-character span of the reproducing case it ranks the known partner unit 207th of 1,149 at cosine 0.5895, while the lexical arm ranks the same unit first at 0.9397, because the span is 5.3 percent of a 2,318-character unit and the remainder sets the direction. Recital units in the corpus run 145 to 4,447 characters at a median of 1,030, against an answer that can occupy one sentence, so the specification was weakest on the paraphrase case the arm was added to reach. The measurement is recorded in the calibration record; no test pins it and no commit ordering supports it, because the chunk-level path was removed rather than kept and nothing remains for a test to drive. What is pinned instead is the invariant that both arms compare the same segment population, so a return to chunk granularity fails a test. Over segment embeddings the same span ranks its partner unit first at 0.9079, and the second published case's partner first at 0.9514.

Segmentation carries unit headings into the comparison stream, where they match one another on their shared form rather than on content. Segments byte-identical to their own unit's `unit_label` in `data/chunks/<doc>.chunks.jsonl` are excluded, and the count is reported with every scan. The exclusion is by provenance rather than by a score cut, so no cut point was chosen by looking at where the excluded pairs fell. Enumerated over all 1,150 units, 341 segments equal their own unit's label and 16 equal another unit's; the own-label form keeps the 16, all of which are bare list markers removed by the separate requirement that a comparable segment carry an alphabetic word. That requirement replaced a justification that a short segment cannot reach the floor against a long span, which holds against a long span and fails short against short, where two identical list markers score 1.0. The funnel is 14,626 segments, 1,057 without an alphabetic word, 341 own headings, 13,228 comparable.

The segment embedding cache is not committed. At 40,636,544 bytes it is 10.2 times the tracked chunk embedding array, and the decision is one of size and not of precedent: `data/retrieval/embeddings.npy` is tracked at 3,975,296 bytes precisely so retrieval reproduces without the model. The cost is that a reviewer without the model re-derives the lexical arm exactly and the dense arm not at all. A manifest carrying the cache digest, the segment count, the funnel, the pinned model revision and the generator command is committed in its place. Two clean-state generations eight minutes apart in wall time produced identical bytes, so the digest is an oracle rather than a record.

The module is placed in its own package rather than beside the existing test-frame builder. That builder imports nothing from the package it sits in, against a control where both genuine retrieval builders do, so co-locating would have compounded a misplacement; and the sealed frame embeds that builder's path as a literal string with its bytes pinned by a rederivation test, so correcting the misplacement would cost a Rule 4 correction to a sealed artifact for a naming gain. The misplacement is recorded and left in place. A package named for what it builds also puts any import of it from the operational layer on sight as a firewall question.

A predicted build time of 29 minutes, extrapolated from a 96-segment two-batch sample, was wrong. The run took 20.1 minutes, and progress estimates during it peaked near 43 minutes. A sample of that size does not model a 13,228-segment sequential run in either direction.

Commits:
- ddd9e7f feat(goldset): two-armed attributability scan, calibrated and reproducing the committed scans
- 518522e fix(eval): supersede the 0.894 ratio on the anx_IV to art_13 rejection row

## 2026-08-03, clean multi-hop stratum drawn, twelve edges with their verification records

The clean multi-hop stratum is twelve EU AI Act internal cross-references, drawn by a forward walk over the committed draw order to index 33 under `select_distinct_target`. The selected set reconstructs from that draw order plus `eval/test_frame_rejections.jsonl` alone.

Thirty-four draw-order entries were walked, three skipped by the distinctness rule and thirty-one judged. Twelve passed and nineteen were rejected. Reason codes over the nineteen: `source_points_only` six, `target_defers_out_of_corpus` four, `target_self_identifies` four, `answer_duplicated_across_endpoints` two, `query_link_not_the_cited_link` two, `target_already_covers_source` one. The denominator is every candidate judged, not the survivors: nineteen of the thirty-one candidates judged are not content dependencies. The largest class, six of nineteen, carries a recorded caution. The form of a citing sentence is not diagnostic of whether an edge is a content dependency: four rejections were predicted from a bare list-item form and two of those predictions were wrong, and one rejection issued on that basis was reversed after its structural twin was screened.

A rejection can free a target and reopen an entry the distinctness rule had skipped. Draw index 4 held the target `art_72` and was a pass when the walk was screened, so draw index 10 was skipped. Draw index 4 was later rejected because its answer appeared in both endpoints, which freed `art_72` and made draw index 10 eligible. Nothing in the procedure reopened the skip that decision caused. The condition was found by reconstructing the selected set from the committed files, not by review, and every individual verdict was correct while the sequence that produced them was not. Draw index 10 was then screened on the same standard as the other thirty and rejected as `source_points_only`, so the twelve stand as drawn. Re-deriving the selection after all nineteen rejections converges in two iterations, and the three remaining skips have targets held by selected picks, so none can reopen.

The property is now asserted rather than left to procedure. The committed reconstruction test checks the count and the not-rejected property and never the set, which is why a set that was twelve entries but not the twelve the queries were authored against passed it. A test now asserts that the reconstructed set equals the units in the committed query rows, and a companion drops one rejection, reopens the skip it was holding, and asserts the comparison detects the change.

The duplication check exists because two picks that careful reading passed carried their answer in both endpoints. Its verdict rests on the designated answer sentence, not on a ratio: a pick fails when the sentence carrying its answer occurs in both endpoint units. The answer sentence is designated at screening, before acceptance, so it cannot be fitted to a query already drafted, and a drafted query resting on a different sentence returns the pick to screening. A reporting floor of 0.60 is recorded and decides nothing; every surviving row ships the ratios above it so a reviewer can disagree in the open. The check is calibrated against the case that motivated it, which scores 0.940 and is near-verbatim rather than verbatim, so an exact-match check would have passed it. The highest ratio in the set, 0.996, sits on a pick that was kept: Articles 91(5) and 92(5) share a procedural sentence about who supplies requested information, and no query rests on it. A negative worth recording: Articles 9 and 72 both discuss post-market monitoring data and returned no pair at or above the floor.

Three of the twelve share an endpoint with another pick, one as a source and one as a target. The frame's constraint reaches shared targets only. The property is recorded rather than removed, because a structural rejection criterion invented after seeing which picks it would remove is a threshold fitted to its own observations.

The query row's `type` field names the pre-registered stratum and `subtype` names the source within it. That is why these rows carry `multi_hop` with subtype `eu_internal_xref`, and why the four action-to-parent rows will carry the same type with a different subtype. A frame stratum name in `type` would make the pre-registration's stratum of sixteen unrepresentable in the file that instantiates it. The row-count test is relaxed from batch exactness to a bound at every commit plus exactness once the file reaches the frame's grand total, because a type mapping to two separately authored strata is partial by construction until both land.

The adversarial per-row grader pre-declaration is scoped to adversarial rows, and the complement is asserted so a gold-bearing row carrying it fails. The paragraph defines failure as asserting substantive content rather than abstaining, which is false about a gold-bearing query. Adversarial rows need it because the retrieval metrics do not apply to an empty gold set and an abstention carries no atomic claims to score. Gold-bearing rows are scored by rates declared before any query existed, and a per-row failure condition for them would invent a verdict this study does not use.

Commits:
- a996d65 feat(eval): twelve clean multi-hop queries with their verification records

## 2026-08-03, em-dash prohibition scoped to authored text

The output convention barred em dashes anywhere. The tracked tree carries 164 occurrences of them across 19 files: 139 in corpus text and its derived chunk artifacts, 24 in files redistributed unmodified from outside the repository, and one as the value of the fold-table entry in `src/ingest/normalize.py` that exists to handle the character. Every prose file the rule was written for is clean. The prohibition asserted something the repository contradicted from the point the corpus was ingested.

It is scoped to authored text rather than narrowed by exception. The three classes are not exceptions to the rule; they are outside what it governs, and stating them as exceptions would have made the largest of them, the derived artifacts, depend on reading a chunk record as a quotation.

No test or sweep asserted the prohibition, so nothing changed behaviour. `normalise_for_comparison` folds U+2014 to an ASCII hyphen at comparison time, so the character never reaches retrieval matching.

The rule was reached through a rejection reason whose argument is what an annex heading says, where paraphrasing to remove the character would have broken the requirement that a characterisation of corpus text ship with a verbatim quote of that text.

Commits:
- 71275cc docs(governance): scope the em-dash prohibition to authored text

## 2026-08-01, authorship division extended to every governance file

The division placed at de366c4, that the owner states the judgment a change must carry and the side holding the repository checks every factual claim in it, was written for SESSION_LOG.md alone. Actors and ownership still carried the rule it supersedes, which barred Claude Code from a governance file and admitted one enumerated exception. The division now stands once, in Actors and ownership, and covers every governance file, and the session log writing standard applies it to entries and states the reasoning. Hasan-directed, overriding the rule the file previously carried.

The file's own history places this as a migration rather than the correction of a statement that became false. The exception sentence is byte-identical from f98a03bd to the revision preceding this commit, sits at line 12 in every one of them, and appears in each governance diff only as unchanged context. The paragraph above it was rewritten at 5bc01d3. It is bootstrap text the file revised around and never reached.

Two defects closed.

The opening paragraph forbade editing without exception what the ownership bullet permitted with one, so the file contradicted itself about Claude Code. The contradiction needed no history to find: the paragraph's imperative and the bullet both bind the same actor, and the paragraph's antecedent is the file the bullet's exception also covers. The gap between them has no instances. Six commits had touched CLAUDE.md before this change, the first creating it and five changing prose, and none carried a commit hash or a tag. CLAUDE.md held no commit-shaped string at any of those six revisions, so the correction the bullet permitted never had a subject in that file. The detector returning those zeros returns three on PREREGISTRATION.md at dbe8b33^, which are the three citations dbe8b33 re-anchored.

The exception was narrower than the changes a governance file takes, so a change outside it had no stated authority. Of the ten commits that had touched a governance file before this change, eight changed content, one created them, and one, dbe8b33, corrected commit citations. The defect was the exception's reach and not its form: correcting a stale mechanical reference is already a property, carrying a commit hash or a tag as an appositive gloss.

Rule 4 was considered as the authority for the governance edits already in the history and rejected. It names no file. Its subject is the query set, the ground-truth passages, the metrics, the thresholds, and the pass and fail rules, and the files it makes immutable are that list rather than a path. Its trigger, that results exist, has not fired. Pointing the ownership bullet at Rule 4 would have widened it across the governance set by implication, or left the CLAUDE.md and docs/METHODOLOGY.md edits unauthorised.

Whether the practice ever departed from the superseded bullet is not determinable from this history, and is recorded as open rather than answered in either direction. Every commit carries one author identity and one committer identity, so composing a change is not distinguishable from placing it. The session trailer does not separate them either: it is absent from the first 25 commits, carried by 42 of the 43 that follow, and absent from 9e13d61 onward, which tracks a convention change rather than who wrote a diff.

docs/METHODOLOGY.md's ownership line named a second owner in vocabulary a reader of this repository cannot resolve. CLAUDE.md carried the same phrase at f98a03bd and fe9487c and lost it at 5bc01d3, and the design document was the site that edit did not reach. The phrase occurred once in the tracked tree, at that line.

The 2026-07-24 entry recording the commit-trailer transition stated that the retrieval-build commits and every commit onward carry the trailer. That held when it was written and is contradicted by the distribution above. It is past-tense-marked in the commit placing this entry, recording when the claim held rather than removing it, following the marking at b048cab.

Commits:
- ad691ef docs(governance): extend the authorship division to every governance file

## 2026-08-01, removed-identifier claim narrowed to the tracked record

A statement in docs/METHODOLOGY.md asserted that the identifiers of commits removed by the history rewrite are not written down anywhere. The surrounding sentences scope the section to the tracked record, and within that scope the claim holds: none of the four identifiers appears in any tracked file. The word anywhere reaches past that scope, so the claim was stated more broadly than the evidence behind it. It is narrowed to the tracked record rather than deleted, because the reason for withholding the identifiers is unchanged and the sentence carries it. Hasan's ruling.

What the repository withholds and why did not change, and the correction states no location for the withheld identifiers. That absence is deliberate: naming where removed material sits is the exposure the removal exists to prevent, and a claim that something is absent from one record is not a claim about where else it may be.

Commits:
- 354c70b docs(methodology): scope the removed-identifier claim to the tracked record

## 2026-08-01, session log authorship divided by what each side can verify

The authorship rule under the session log writing standard assigned every entry carrying a governance or disclosure judgment to Hasan, written away from the repository and placed verbatim. It now divides by what each side can check. Hasan states the judgment an entry must establish, what a scope decided, what it retracted, what it discloses and how far a claim may reach, and reviews the draft against that. Claude Code drafts the prose and checks every factual claim in it against the repository as it writes. An entry is drafted once, after the measurements it describes are final, rather than revised alongside measurements that are still moving. Hasan-directed, overriding the rule this file previously carried.

The reason is an asymmetry in what carries a control. A measurement is produced under rules that require one: a funnel, a positive control on an emptiness claim, a named check reporting its output. A claim written in prose about a file's contents, a count, a convention or a format carries none, so it is found wrong only by someone holding the repository who checks it against the files. The adversarial stratum produced five defects of that second kind in authored text: a claim about which sections of a standard are published freely, made without the standard; a verification criterion requiring a quote to appear exactly once, where the corpus repeats the quoted span three times across three references blocks; a heading convention stated as measured, where seven of this file's headings contradict it; a count of what a commit's diff carried, where it carried seven files; and a scope stated as three rows, where the property it named held on five. Measurement in the same scope was also wrong at points, and those errors are checkable by the controls the discipline already requires of a measurement, which is what a prose claim lacks.

Four rules accompany the change, each recorded with the defect that forced it. The file carries 46 numbered items, from 44: V20 and V21 are new, and V11 and the receiving-an-instruction section each gained a clause.

V20 requires a check that reports a pass or an absence to be shown capable of failing before it is trusted. Two forms failed. A digest verification loop reported a match on a copy that had not happened, because both hash commands failed on a malformed path, both returned empty, and the empty strings compared equal; what caught it was a separately derived count of staged paths, not the comparison. Three detectors matched on structure where the claim lived in content, and each returned a pass on the one site it existed to check. The rule is scoped to a pass or an absence so that it does not revoke V8's exemption, that a non-empty result certifies its own predicate.

V21 requires artifacts committed together to be cross-checked against each other rather than only against their sources. Three defects were a claim in one file contradicted by a number or a quote in a file committed beside it, and each survived readings of the files separately.

V11 gained a clause requiring a characterization of what a piece of corpus text is or means to ship with a quote of that text in the same commit. A wrong count is caught by cross-checking against a recorded count; a wrong description has nothing to check against unless the text sits beside it. The defect was in the rejection log. Three rows assert that a candidate's string appears under a different referent, which is a characterization rather than a count, and they name three distinct candidates. Two of those decoys were quoted in a sibling artifact and the third was quoted nowhere, so that claim rested on text a reviewer could not reach. The gap was closed before the artifacts were committed, and every row making such a claim now carries the occurrence verbatim.

The receiving-an-instruction section gained a clause on scope stated as a count. An instruction naming how many items a change covers, rather than the property those items share, is answered with the property and the count that property yields.

Rule 13 states that clause number and published title are a ceiling on a permitted reference to ISO/IEC 42001, not its required form. What the rule permits is unchanged, which a reviewer can confirm by diffing this commit against the previous version. The ordering is the weaker one: the three queries referencing the standard by number alone shipped at 6540c0c, and the clarification follows here, where V16 prefers a claim to be committed before the thing that could contaminate it. Both authorized history rewrites are spent, so the ordering is recorded rather than corrected. Hasan's ruling.

Commits:
- de366c4 docs(governance): divide session log authorship by what each side can verify

## 2026-07-30, adversarial stratum committed, ISO constraint replaced, retrieval gated for the sealed set

The first eight of the fifty pre-registered queries were committed: three referencing ISO/IEC 42001, four naming a fabricated identifier, one out of domain. Gold is empty on all eight, correct behaviour is abstention from retrieved context, and no retrieval metric is computed for the stratum.

### ISO authoring constraint replaced

The ISO queries were originally to be built from the standard's published contents listing, referencing clause number and published title and nothing further. That constraint was withdrawn. ISO publishes only the informative sections of a standard publicly, so a listing of normative clause titles is not freely available, and the constraint governed the author rather than the artifact: a reviewer holding the repository could not check whether it had been honoured.

Four checkable constraints replaced it. The queries carry no clause reference. They ask what the standard requires rather than what it defines, and the requirements clauses are not among the sections ISO publishes freely. Every token other than 42001 is a member of the corpus primary-token vocabulary, measured at 8670 distinct tokens over the four committed chunk files; 42001 is the sole exemption, because iso and iec are already corpus vocabulary through NIST's own citations of ISO documents. Each query is interrogative and carries no numeric token other than 42001, which pins the absence of a clause number to a test rather than to a reading. All four properties are asserted against the shipped file.

The vocabulary check ships with its scope stated narrowly: it establishes that no ISO-specific vocabulary entered the query text, and does not establish that no ISO material did. A query assembled entirely from corpus words could still mirror a clause's propositional structure, and no mechanical check available here detects that. Rule 13 is unchanged and no ISO text is included in any form.

### Retrieval ordering for the sealed set

The pre-registration commits the queries and their embeddings before retrieval runs on them. Parameterising the query-embedding provenance tests over both query sets would have executed retrieval against the sealed eight at test time, before the commit that freezes them existed. Two readings were available: retrieval as the numbered metric-producing step, under which an in-memory unit test violates nothing, or the clause read literally. The literal reading was adopted, because the ordering claim is the load-bearing claim of the repository and a run cannot be un-run.

No code path in the committed tree executes retrieval against `eval/test_queries.jsonl`. The gate derives from the absence of a committed results file for a query set rather than from a flag, so it opens at the commit adding those results and requires no manual change. It was verified by instrumenting the retriever for one suite run: 36 search calls, none of them a sealed query, against 12 of 12 development queries as the positive control. A regression test asserts the gate, and removing the gate call from a retrieval-performing test was confirmed to fail it.

The reading of that clause is now load-bearing and should be settled explicitly at the retrieval commit rather than left to whichever interpretation is convenient then.

### Row-count assertions do not establish alignment

The provenance suite asserts row count, dtype and unit L2 norm on a committed embedding array. A row-shuffled array satisfies all three. Alignment is established only by rank reproduction, which compares the committed array against a regenerated one row by row, and that check is gated for the sealed set until its retrieval results exist. Its own blind spot, two rows producing an identical top ten, is recorded in the test.

### The frame's absence predicate reports real units as absent

The candidate frame requires each fabricated identifier to be checked absent against the unit index and the frozen chunk-id set. Read as bare membership, that predicate reports 97 of 1150 real unit ids as absent, because a split unit carries `#pN` chunk ids; `eu_ai_act:art_10` and `eu_ai_act:anx_III` both fail it. A predicate that reports real units as absent cannot make an empty result evidence. The prefix form recovers all 97 with no residue and is what the verification records use, including in every positive control. The frame was not amended: it states a requirement, and bare membership is the wrong implementation of it.

Absence was also checked against corpus text, which the frame does not require. `data/chunks/*.normalized.txt` is the target of record, being byte-equivalent to the chunk text the retriever surfaces. Searches over the extracted text carry a known false-negative mode from U+FFFE at hyphen positions and are recorded as a bound. Publisher PDF bytes are searchable only for the playbook, where 72 of 72 real subcategory identifiers are findable; the EU PDF returns nothing for the real Article 113 and is excluded rather than counted as a passing check.

### Identifier selection and its amendment

The four fabricated identifiers were selected by rule from an enumeration of the corpus identifier space rather than chosen. All 193 rejected candidates are recorded with their reasons, so the picks reconstruct from the enumeration and the log alone.

The rule was amended after its first three checks were written. A fabricated EU article number tokenises to the word and a bare number, and the recital series prints bare parenthesised numbers to 180, so every candidate from 115 to 180 carries its number on a real chunk. Article 115 would have driven BM25 onto Recital 115 through a document-frequency-1 token, the highest inverse document frequency available in this corpus, which is the opposite of what its class exists to test. A fourth check was added, that no chunk carries the bare number, and the pick moved to Article 181. The added property is a frozen-corpus property, derivable before any query text existed and independent of every outcome the stratum measures. The check was applied to three of the four classes and left both other picks unchanged, which is recorded. It does not apply to the class requiring a text decoy, because a decoy of the form "Article N" contains N, so the two checks are logically incompatible there; measured exhaustively, all three candidates with a decoy carry the bare number, while 68 of the 84 without one carry it anyway.

Article 181 sits 68 past the last real article, a weaker plausibility claim than a number nearer the end. It was taken because it is the only route to a fabricated article number with no lexical anchor: candidates carrying a text decoy above 113 are 114, 119 and 188, and the first candidate with no carrier of any kind is 181.

One identifier was drawn deliberately from the class that is absent from both id spaces while present in corpus text under a different referent. Article 114 appears in a recital as a reference to the Treaty on the Functioning of the European Union. Declining on a retrieved context that contains the exact string attached to a different instrument is a harder abstention than declining on a context that contains nothing relevant.

### Wrong predictions, recorded

Three predictions made before measurement were contradicted and are recorded in the artifacts rather than removed.

Fabricated identifiers were expected to be available in both interior-gap and past-the-end shapes. No interior gap exists anywhere in the corpus identifier space: EU articles run 1 to 113 complete, and both the framework and the playbook carry all 72 subcategories with no gap in any category. The only gaps are the generative-AI profile's own subcategory selection, and those two subcategories are real, printed and unit-bearing in the other two documents. Every fabricated identifier is therefore past the end of its series.

A fabricated leaf under a real parent was expected to retrieve its real siblings while a fabricated parent retrieved nothing structurally near. Both numeric tokens have document frequency 0 and the scorer skips a term with no inverse document frequency, so the two queries produce identical BM25 scores. The contrast between them is generation-side, not retrieval-side.

Retrieval on a fabricated identifier was expected to be dense-driven, because the identifier reaches the index only through parts that mostly do not exist in it. That holds for the compositional NIST identifiers and fails for the EU ones, where the bare number is a rare token present in the index. Fabricating an identifier in a compositional grammar leaves no lexical footprint; fabricating one in a bare-integer grammar collides with another family's numbering in the same document.

### Exposure recorded before any run

Because every fabricated identifier is past the end of its series, a model with accurate parametric knowledge of the instrument's length can reject all four without reading the retrieved context. Abstention driven by parametric knowledge is not the context grounding this stratum measures. The pre-registered no-context condition measures that share directly, one run per tier, so the exposure converts to a number rather than remaining a caveat. The NIST picks are less exposed than the EU ones, since the count of subcategories under a given category is less likely to be memorised than the article count of a named regulation.

Grading is pre-declared per row before any generation. The failure is asserting substantive content as the answer, whether attributed to the named standard, to the named provision, or to nothing at all. Every other response is not a failure, including reporting that the retrieved context does not support an answer, and including stating that a named provision does not exist.

### Retracted count claim

An earlier record stated that candidates above 113 carrying the string in corpus text were exactly 114 and 119. A wider scan found a third at 188. No pick changes: the class requiring a decoy takes the lowest satisfying candidate and 114 is lowest, and the clean class's pick at 181 is below 188. The claim was stated more broadly than the scan behind it, which is a defect whether or not it changed an outcome.

### Worktree directories ignored ahead of the stratum

An ignore rule for isolated working copies created under `.claude` was committed separately and first, so the ignore rule does not appear in the stratum's own diff. Without the rule, staging from the repository root recurses into a working copy and stages a second copy of the whole tree. Measured before adding: `git check-ignore` reported no match on a path inside a working copy, at exit 1, against a positive control matching a path under `.venv`.

Commits:
- 9e13d61 chore(git): ignore worktree directories under .claude
- 6540c0c feat(eval): add the eight adversarial queries with their verification record

## 2026-07-28, use of an untracked working file disclosed, S9 scoped to match

Nine sites in this log describe an untracked working file used during development.
They were left uncorrected when the session log writing standard landed, because
whether they were defects depended on a decision not then made. The decision is that
the repository discloses the file rather than removing the references. The filename
already appears in `.gitignore`, so the existence was public either way, and a
reviewer finding nine references to a file absent from a clone with no acknowledgment
learns less than one who finds the acknowledgment. Editing nine historical entries to
satisfy a rule shipped days earlier is the more suspicious of the two options.

The disclosure could not be written until it was true. An audit of the decisions
recorded in that file against the tracked tree found four that existed in no tracked
file: the generation transport, the Opus reasoning-effort setting, the withdrawal of
orthographic variation traps, and a ruling on metric inflation over duplicated gold.
All four were placed before this statement, so the statement describes the repository
rather than an intention. The audit also found the intended wording too narrow: the
retrieval parameters and the corpus provenance are governed by the manifest and by
`corpus/SOURCES.md`, not by prose, so both are named alongside the four prose files.

The statement carries no universal claim. The decisions checked were enumerated by
hand rather than extracted mechanically, so what is stated is where the record is and
that a decision found only in the untracked file is a defect, not that none remains.

S9 was scoped to the disclosure and not weakened to fit it. Naming a disclosed
untracked file, and describing an edit to it by its mechanism and by which decision it
records, is permitted; reproducing its text is not; and untracked material the
repository does not disclose is not described at all. The bar on naming a commit hash
as the location of removed or private material is unchanged and absolute.

The entry recording the metric correction understated its own evidence, citing one
development query where an exhaustive audit of all twelve found five returning more
than one carrier inside the top 10. Corrected in this commit.

Commits:
- f33e5ca docs: disclose the untracked working file and scope S9 to match

## 2026-07-28, retrieval metric definitions corrected before any generation

The retrieval metrics section specified its scoring level twice and disagreed with
itself. The header named gold chunks and the rule named units, and NDCG@10 named a
gain without naming the ideal it is normalised against, so it had no value at all.
Both were found before any generation ran, so the file was revisable under Rule 4.

Precision@10 is now the fraction of the ten retrieved chunks whose unit satisfies a
slot. The ten positions are chunks, and a chunk the model receives occupies context
whether or not another chunk of the same unit is also present. That leaves precision
raised by a retrieval returning several verbatim carriers of one statement, which is
correct behaviour under a gold rule where any carrier satisfies. The development
results show it: five of the twelve queries returned more than one carrier of a
single statement inside the top 10, four of them returning three. The definition
stands rather than being changed, because counting satisfied slots instead collapses
precision into a rescaling of recall and carries no independent information. Each
query's carrier count is reported alongside the metric and no precision figure is
quoted without it.

NDCG@10 now assigns gain 1 to each slot at the rank of the first chunk satisfying
it, normalised against those gains at the leading ranks. An earlier draft normalised
against every chunk of every acceptable unit, which scored one correct carrier of a
three-carrier slot at 0.4693 and made a perfect score reachable only by returning
redundant copies. That draft was rejected before placement: 61 of the 72 duplication
groups have more than one carrier, so the defect would have applied to most of them.

A Gold set rule now requires a query's slots to have disjoint acceptable-unit sets.
Without it a single retrieved unit could satisfy two slots, which scores recall 1.0
on a query built to require two units and lifts NDCG@10 above 1. No candidate in the
committed frame violates it and a backfill could have introduced one silently. A
drawn candidate whose slots cannot be made disjoint is a recorded rejection.

Two decisions that were settled earlier and recorded in no tracked file are now in
the pre-registration: the Batch API as the generation transport, and reasoning effort
low on the Opus tier. Both fix cost and output and had to be frozen before the paid
step. A third, the withdrawal of orthographic variation traps from the query set, is
recorded in Composition with its reason, that the shared retrieval path should handle
hyphenation and spelling variants and a failure mode is not preserved so the layer
has something to fix.

Commits:
- bc4b2d4 fix: correct the retrieval metric definitions before any generation

## 2026-07-28, commit-count claims corrected across eleven sites

Eleven claims about the length of the history were false. Ten share one cause and
the eleventh is separate.

Ten entries state, in the form "once this log commit lands the history is N
commits, all trailer-free", values of 26, 24, 22, 20, 18, 16, 14, 12, 10 and 8
against measured 25, 23, 21, 19, 17, 15, 13, 11, 9 and 7. Each is stale by one in
the same direction. The convention is fixed by the wording and confirmed by the two
entries in the same class that enumerate their commits by hash and so verify
themselves: N is the history length once the placing commit lands.

The cause is recorded because it bounds what an earlier operation covered. The
history rebuild re-anchored citations by hash, so it reached the two claims in this
class that carry hashes and corrected them, and never examined the ten that do not.
An earlier entry states that two commit-count enumerations were corrected against
the rebuilt history. That was accurate about what was done and silent about the
remainder; the class held twelve.

The eleventh is a different shape. A claim of 27 commits preceding the retrieval
build measures 25, having been off by one when authored before the rebuild removed
one more. Its companion claim of seven retrieval-build commits holds exactly.

Claims that record a measurement taken during a session are not corrected. Those
describe an act at a time, and the history they measured no longer exists to
re-derive; correcting them would restate them as claims about a later state. The
distinction is recorded so the omission is deliberate rather than overlooked.

Rule 11 gained a clause fixing the one commit an entry may omit. An entry does not
name the commit that places it, because that commit's content is the entry, and the
convention had been left implicit. A reviewer resolving a commit that appears in no
entry could not distinguish that case from an unlogged one. The clause is narrow by
design: a commit touching any file other than this one is named by some entry, so a
genuinely unlogged commit stays visible rather than being absorbed by the exemption.

The corpus unit-to-chunk cardinality was recorded in the retrieval manifest and
pinned by a test that re-derives every figure from the unit index and the test
frame. Gold is defined at unit level and retrieval returns a top ten of chunks, so a
unit spanning several chunks occupies several of the ten. The distribution is uneven
across the strata, from 45 percent of clean multi-hop targets to none of the
action-to-parent parents, which constrains any metric later defined over those ten
slots. Recorded before the metrics were settled and before any retrieval ran on the
sealed set.

Commits:
- 140d167 fix: correct eleven false commit-count claims in the session log

## 2026-07-28, near-miss population corrected to the sealed specification

The frame's near-miss stratum drew its three measured picks from one of the two
populations the sealed specification names for them. Sealed line 58 names the 12
hand-audited near-block-duplicate pairs both as a source for those three and inside
the committed near_duplicate class the five authored picks come from; the builder
gave them to near_duplicate alone and recorded no choice. The three were therefore
drawn entirely from the normalise-identical population, where 16 of 17 candidates
were the lexicographic minimum of their own identity group, so the chunk-id
tie-break rather than retrieval decides the ordering among byte-identical text. The
development query the specification names as the structure those three reproduce has
gold in no identity group, so that structure was absent from the pool.

Correcting rather than recording was decided on measurement: 8 of the 12 query-side
units belong to no identity group, and 8 of 12 or 9 of 12, depending on which of
three fields is trusted, resolve by a BM25 term-density separation rather than by the
tie-break. The block_clusters population became the union of the 17 surviving
clusters and the 12 query-side units, 27 after 2 duplicates, 0 removed by closure.
The 12 entered whole. Filtering them by any measured property was rejected, because
selecting a population on a property observed after the draw is shaping.

Two draw-time rules were added, both ruled before the corrected draw was computed.
Cross-source distinctness prevents the three measured and the five authored from
selecting the same unit, which the overlapping populations now make possible.
Identity-group distinctness prevents two of the three measured being over
byte-identical normalised text, extending to normalise-identity the principle the
frame already applies to a shared gold target. Both apply during backfill, and a test
exercising them under a synthetic rejection log replaces a reconstruction test that
passed vacuously on an absent rejection log.

The corrected three were predicted before the rebuild ran, from the union order and
the spacing formula alone, and the rebuild confirmed each of them, both rules not
firing, and the five unchanged. A byte-equality control reproduced the pre-correction
draw orders from the same code path before any rebuilt number was accepted.

The correction does not remove the property that prompted it. One of the three
corrected picks has gold in no identity group, against none before; the other two
remain identity-group cases decided by the tie-break. That is a property of a corpus
whose block clusters are predominantly identity groups, and no adjustment to the
offset, the spacing rule or the population was made to improve the ratio.

Commits:
- 5ea39cc, fix: near-miss block_clusters population corrected to the sealed specification

## 2026-07-28, session log standard and verification discipline written into CLAUDE.md

SESSION_LOG.md ships. It is the file in this repository written most often by an
agent and reviewed least per line, and every process claim the README makes rests
on it. The standard it is held to, and the verification discipline behind the
deterministic checks, were not in the file read at the start of every session.
Both are now in CLAUDE.md as S1 through S11 and V1 through V19. Each item was
paid for by a defect recorded elsewhere in this log.

Rule 11 was corrected on the owner's ruling. It required an entry immediately
after each commit, and this file's header repeated that claim. Measured: 22
entries against a rev-list count of 57. The practice is one entry per unit of
work, naming the commits it covers, which is what the writing standard requires,
since an entry recording decisions rather than a sequence of events cannot be one
per commit. The rule was stale, not the practice. Changing the practice to match
the rule was rejected for that reason. The header line and one stale restatement
in an earlier entry were corrected in the same commit.

Rule 10 now records that both authorized history-rewrite exceptions are spent, so
a defect in history is fixed forward or lived with.

Rule 13 now forbids reconstructing ISO/IEC 42001 clause content by paraphrase and
not only by quotation. Three pre-registered adversarial queries will reference
that standard, which is excluded from the corpus on copyright grounds, and a
question specific enough to probe a clause can encode the clause without quoting
it. The rule was committed before any of those queries was written.

The layer-gold firewall moved into CLAUDE.md and gained a clause. It bars the
operational layer from using any relation that defines the gold for the query it
is answering, which leaves the empty-gold case uncovered: adversarial queries have
no gold, so no such relation exists to bar. The added clause gives the layer the
query text and the retrieved context and nothing else, barring it from a query
row's stratum label, row identifier, and notes. Ruled before the layer exists,
because ruling it once an abstention rate is known would be indistinguishable
from rescuing one.

S9 ships as a rule this log does not yet satisfy. It bars describing the contents
or purpose of an ignored working file. Fifteen lines in earlier entries reference
that file, and nine of them state its contents or its purpose rather than only the
mechanism of an edit, on two independent classifications of the same fifteen lines
that agreed line for line. The mechanism and content boundary is a judgment and
not a mechanical test, and the count carries that limitation. Those nine are left
uncorrected. Whether they are defects or are consistent with disclosed practice
turns on a decision not yet made, and correcting them ahead of that decision would
be scrubbing rather than fixing.

Commits:
- 5bc01d3, governance: consolidate session log standard and verification discipline into CLAUDE.md

## 2026-07-27, sealed test-set candidate frame, corpus unit index, query-embedding builder

The sealed specification fixes the stratum counts and the gold rules and leaves one degree
of freedom, which specific units are drawn within a stratum. A selection described after the
queries are authored is unfalsifiable. The candidate frame is therefore derived from the
committed artifacts by committed code and frozen before any query text, gold, rank or result
exists, the same discipline the reserved development pool already applies.

### The development firewall and the duplication gold rule had not been composed

The firewall requires that no pre-registered gold unit be drawn from the reserved forty-unit
development pool. The gold rule states that a slot is satisfied by any unit carrying its
statement. The first is written in units and the second operates on equivalence classes of
units, so excluding the forty does not keep the pool out of gold. A slot for a statement
with a carrier in the pool either names that carrier, breaking the firewall, or omits it,
which scores a retrieval hit on byte-identical text as a miss.

Candidates are filtered against a closure rather than the pool. Measured over the committed
artifacts the closure is fifty units, the forty plus ten. Two of the ten are reachable only
through the normalised-identity groups and not through the duplication map, so both
relations are composed rather than either alone. The burn is at unit-equivalence
granularity rather than subcategory granularity: MAP 3.4's statement unit is burned while
its Playbook block units are not, so excluding everything under a subcategory would
over-burn and excluding only the pool unit would under-burn. Eighteen of the twenty
normalise-identical block clusters survive the closure. The closure is a strict superset of
the pool, so the pre-registered disjointness promise is honoured and exceeded, and the
sealed file is unchanged.

### Single-hop eligibility is the sealed criterion in mechanical form

The sealed specification excludes the Playbook from single-hop because its only
atomic-factual candidates duplicate the NIST subcategory statements and its unique content
is block elaboration. Those are two criteria, atomic-factual and not a duplicate, and the
per-document unit-type allow-list is their mechanical form rather than a new composition
decision.

Excluded with reasons recorded in the frame: AI 600-1 actions, which are procedural
suggested-action items rather than atomic fact and are the action-to-parent stratum's own
source, so including them would overlap two strata on one unit type; AI 100-1 parts, the one
remaining unit reading "Part 2: Core and Profiles"; and AI 600-1 subcategory statements the
duplication map records as duplicated, which are verbatim restatements rooted at AI 100-1
and eligible only in their originating document. Forty-three of the forty-five non-closure
statements fall to that last rule, leaving two.

AI 100-1 categories were included over an ambiguity. They carry statements and duplicate
nothing, so both criteria pass. Retrieval adjacency to their own subcategories is a
difficulty property rather than an eligibility criterion, and excluding a type because it
might retrieve hard would fit the stratum to the outcome it exists to measure. An
unanswerable draw is handled by the recorded rejection procedure instead.

Eligible populations are 298, 109 and 24, and one per source with largest remainder gives
eleven, five and two. The allocation follows eligible supply, which is a property of the
corpus.

### Clean multi-hop is twelve EU cross-references and no NIST

The one-per-source floor introduced during frame design is withdrawn for this stratum only.
Single-hop keeps its floor because all three of its sources have supply. This withdraws a
design-time allocation rule rather than a split mandated by the sealed specification, which
names eligible sources and mandates no split, so no correction to that file is required.

Two measured causes. The NIST prose reference supply is thin and pointer-class, thirteen
references against 367 EU internal edges before any closure, and the survivors are see-also
and bibliography pointers rather than different-content hops. Separately, the development
pool's one-unit-per-stratum design burned the units those references cite: of the eight
same-document references lost, five fall to size-one NIST structural strata the pool
necessarily takes whole, and three to the single AI 100-1 section the pool drew from a
stratum of twenty-three, which is a dense cross-referencing hub. The first cause is prior
and dominant and the second jointly determines the final zero. Naming only the frameworks
would book a property of the pool's design as a property of the corpus.

The candidates rejected under this rule are recorded: two intra-document pointers and one
cross-document reference, all of which resolve on both endpoints and carry different content
but cite the target as machinery, a list item, or a glossary location. The test applied is
whether answering requires content from both endpoints or whether the source only points at
where the answer lives.

### Selection under skip and rejection

Selection is a forward walk over the committed draw order, taking the first entries not in
the rejection log, so the selected set is reconstructible from the draw order and the
rejection log alone. That property ships as a test now and passes vacuously on an empty log.

Clean multi-hop additionally skips an entry whose target unit is already selected. One
target was gold for two spaced picks, which would correlate those outcomes and shrink the
effective sample size of a twelve-query stratum. The constraint is enforced by the same
forward walk rather than by removing candidates, so the reconstruction property is
unaffected.

The draw order's tail disperses rather than following sorted order. A sorted tail was
measured to draw the alphabetical head of each candidate list: eighteen of the first thirty
backfill entries for AI 100-1 single-hop were categories, sixteen percent of that
population, with no subcategories at sixty-one percent of it; twenty-four of the first
thirty for clean multi-hop were annex-sourced against a share of 7.7 percent. Every
replacement, from a target skip or an authoring rejection, would have come from that head.
The tail is ordered by maximum minimum circular distance to every already-taken index, ties
to the lower index, which leaves the spaced picks unchanged and returns the backfill head to
population proportions. One selected candidate moved.

Block-cluster candidates are unit ids rather than the chunk-level representatives the
identity groups carry. Identity is a chunk property and correct as such in that artifact,
but gold is unit-level, so a candidate that cannot be a gold identifier is the wrong object,
and one unit holding two draw slots would double-weight it. Two entries were two chunks of
one unit, so the eighteen surviving clusters yield seventeen distinct unit candidates.

### A shared gold class recorded rather than removed

Single-hop draws the AI 100-1 carrier of GOVERN 1.3 and action-to-parent draws the AI 600-1
carrier as its gold parent. The duplication map records that statement as duplicated, so
under the any-carrier rule one slot is satisfied by either. This is the closure's defect
shape, unit identity against equivalence class, and a unit-id collision check does not see
it. It is recorded rather than removed: the same statement reached by an easy query and by a
hard structural hop, carrying opposite pre-registered predictions, is a controlled pair. A
cross-stratum disjointness constraint was considered and rejected as machinery introduced to
erase an informative coincidence.

### Corpus unit index

Units are keyed on parent_id by the chunk artifacts and on unit_id by the pool, relation,
cross-reference and duplication artifacts. The index makes that join once, covering 1,150
units over 1,294 chunks. Its test re-derives byte-for-byte, which is the correct pin here
because the derivation is machine-independent, and asserts that every unit_id referenced by
those artifacts resolves to an index unit, which is what actually tests the bridge.

### Query-embedding provenance

No committed script produced the development query embedding array. The array was committed
and level two held, but a reviewer could not verify that those bytes came from those queries
through the declared path. A builder now produces both arrays through the shared
normalise_for_comparison and ONNX path.

Byte-identity of a regenerated array is not asserted. The manifest already records that ONNX
reproduces rankings and not bytes across machines, so a byte assertion would pass locally and
fail for a reviewer. The pins are shape, dtype, row alignment and L2 norm, plus rank
reproduction from the regenerated array against the committed array, which is the assertion
that carries provenance. Comparing against the committed results file tests the pipeline
instead. The model's sha256 is asserted before use so a cache holding another revision fails
loudly, and the gate is offline-only, so the tests skip rather than download.

Rank reproduction is not available for the sealed set at its own commit, because that commit
carries no ranks by construction. It is added when retrieval runs on that set.

### Manifest stale statements corrected

Two statements in the retrieval manifest were true when written and were contradicted by the
committed development query set. Both are past-tense-marked rather than deleted, so the
record of when they held survives. No parameter, measurement or decision in that file
changed.

Commits, local only:
- 0453d9c, corpus unit index derived from chunk artifacts
- 94a418c, query-embedding builder with provenance tests
- c559130, sealed test-set candidate frame, committed before any query text
- b048cab, retrieval manifest stale statements past-tense-marked

Current state:
- Local git on `main`, no remote configured, nothing pushed. The candidate frame is committed
  and carries no query text, gold, rank or result. Suite 214 passes, or 212 with two skipped
  where the pinned model is not cached, ruff clean, vendor verifier 30 checks.

Next step:
- The sealed fifty: query text, slot-based gold, per-edge verification records and the
  rejection log, authored against the committed draw order, with query embeddings built by
  `src/retrieve/build_query_embeddings.py`, committed before retrieval runs on them.

## 2026-07-27, session log heading dates derived from commit metadata

The heading date on the history rebuild entry below was authored rather than read
from the repository, and disagreed with the metadata of the commits that entry
records. Both of those commits carry committer date 2026-07-27 in the
repository's local timezone. The heading is corrected to that date.

Convention recorded so it is applied consistently: a heading date is the
committer date, in the repository's local timezone, of the commit whose work the
entry records, not of the commit that places the entry. A rebuild leaves no
timestamp of its own, since author and committer times are preserved across it,
so the derived evidence for when such an operation ran is the first commit made
after it.

Mechanical references, commit hashes and dates, are corrected in place. Claims
and findings are corrected forward in a new entry, as the 2026-07-24 dense-arm
relabelling was. Only the first of those rewrites a committed entry, and it
rewrites a reference rather than a statement.

Commits, local only:
- bdd548d, session log heading date corrected to the committed date

Current state:
- Local git on `main`, no remote configured, nothing pushed.

Next step:
- Pre-registration, second sealing commit: instantiate the 50-query sealed test
  set and its gold sets against the frozen specification, with per-edge
  verification records and query embeddings, committed before retrieval runs on
  them.

## 2026-07-27, history rebuilt before first publication, citations re-anchored

Repository history was rebuilt with git-filter-repo 2.47.0 on a local repository with no
remote configured that had never been pushed. Hasan-directed, authorized in session as a
second exception to CLAUDE.md Rule 10. The first was the pre-push bootstrap rebuild recorded
in the 2026-07-21 entries below, which that entry records as spent. No further exception is
available.

Commit hashes changed. Author and committer identities and timestamps, and commit ordering,
are unchanged for every surviving commit, verified by generating the full commit ledger
before and after the rebuild and comparing those fields directly. The tree at the tip is
byte-identical to the tree before the rebuild, so no published file content moved. Three
commits became empty under the rebuild and were pruned, taking the history from 51 commits
to 48.

Citations were re-anchored mechanically from the rebuild's commit map: 40 occurrences across
29 commits in this file, and 3 across 3 commits in `PREREGISTRATION.md`. Abbreviation
lengths were preserved and every rewritten abbreviation was verified to resolve
unambiguously in the rebuilt history. Four citations named commits that no longer exist;
those were removed rather than remapped, and two commit-count enumerations in this file were
corrected to counts measured against the rebuilt history.

Verified after the re-anchoring commit: every hex string of length 7 to 40 in the tracked
tree either resolves to a commit in the rebuilt history or is individually accounted for.
The accounted-for set is the pinned bge model revision, its abbreviated mention in this
file, the fractional digits of the avgdl constant, and the generated and vendored content
under `data/`, `corpus/`, `vendor/` and `uv.lock`, none of which resolves to a commit in
this repository.

Commits, local only:
- dbe8b33, commit citations re-anchored after the rebuild

Current state:
- Local git on `main`, no remote configured, nothing pushed. 203 tests pass, ruff clean,
  vendor verifier 30 checks.

Next step:
- Pre-registration, second sealing commit: instantiate the 50-query sealed test set and its
  gold sets against the frozen specification, with per-edge verification records and query
  embeddings, committed before retrieval runs on them.

## 2026-07-26, governance: firewall rule generalised, local working files separated

Governance file maintenance ahead of publication. Nothing pushed.

Firewall rule generalised. CLAUDE.md Rule 14 previously named specific components. It now
forbids importing, referencing, reproducing, or describing code, components, or internal
design belonging to any other private project, naming none. The substance and force are
unchanged: it forbids the same thing and still says to stop and raise. Hasan-directed
governance edit, an owner override of the file's own do-not-rewrite rule.

Local working files separated from the published artifact. Machine-local working notes are
git-ignored and are no longer tracked. Session-open instructions that refer to them moved to
`CLAUDE.local.md`, which is also ignored. `CLAUDE.md` and this log now reference only files
that ship, so the published repository is the engineering artifact and nothing else.

Commits, local only:
- 44e9fe5, local working files removed from tracking and added to .gitignore
- fe9487c, session-open instructions moved to CLAUDE.local.md, governance scoped to shipping files

Current state:
- Local git on `main`, no remote configured, nothing pushed. Governance files reference only
  published files.

Next step:
- Pre-registration, second sealing commit: instantiate the 50-query sealed test set and its
  gold sets against the frozen specification, with per-edge verification records and query
  embeddings, committed before retrieval runs on them.

## 2026-07-25, pre-registration extended and corrected: no-context condition, near-miss redefinition

Two Hasan-directed corrections to PREREGISTRATION.md, made before any result exists and
revisable under Rule 4, committed at 18603e9. No generation has run; the file still
predates all results.

Near-miss redefined. The near-miss stratum changes from a faithfulness trap, terms present
but not answering, to a retrieval discrimination trap, a plausible near-identical unit
surfaced over the actually-right one. Reason: the measured development query 11 case is a
discrimination failure by construction, and the bootstrap definition predated that
measurement.

Third condition named no-context, not closed-book. Closed-book is reserved in this repo for
the grounding discipline of answering only from retrieved chunks and never from training
memory, per CLAUDE.md Rule 1. Reusing it for the no-retrieval diagnostic condition would
collide with that, so the condition is named no-context in the pre-registration, and the
tracker was aligned to no-context in the same pass at its three condition lines, with the
decisions-log entry recording the rename.

Both changes sit alongside the extensions the bootstrap file explicitly deferred to Phase 1:
the no-context condition, the sealed-set composition, the gold set rules, and the
per-stratum predictions, all added in this revision.

Commit, local only:
- 18603e9 docs: extend and correct pre-registration, no-context condition and near-miss redefinition

Current state:
- Local git on `main`, no remote, nothing pushed. Pre-registration extended and corrected;
  the file still predates all results. The tracker is modified in the working tree, its
  no-context alignment and other governance edits, and is deliberately not committed by
  this pass.

Next step:
- Author the sealed 50-query set and its gold sets within the pre-registered composition,
  committed before generation, with per-edge gold verification recorded. Then generation
  behind the spend gate.

## 2026-07-24, correction: the 127 is a dense-arm property, not a context-set finding

The previous entry and the manifest framed the 127-of-1506 rank 10/11 sub-grain gaps as a
context-set finding. That was inherited from a wrong framing of mine, corrected here fixed
forward rather than by rewriting the committed entry. The rank 10/11 boundary those 127
measure is the dense arm's, one input to reciprocal rank fusion, not the fused top 10 that
reaches the model.

Kept as a dense-arm property: for those 127 queries quantisation merges the two dense
scores into a tie, and chunk id decides which takes dense rank 10 and which 11, an RRF
contribution difference of 1/70 minus 1/71, about 2.1e-4. Both remain in the dense top 100
and both contribute to fusion either way.

The context-set answer stated directly from the measurements that address it: fused rank
10/11 ties, membership decided by chunk id, are 11 of 1294 known-item and 0 of 212 action,
11 of 1506 over the same population; cross-path disagreement after quantisation is 1 of
1506 with zero membership changes. The 0 of 212 closes a twice-raised concern: the
chunk-id tie-break does not touch the action-to-parent relation at the top-10 boundary, so
it does not inflate that expected-hard stratum's measured failure.

Two further one-line corrections in the manifest. The b=0.75 length bias (2.70x, a
single-term term-frequency ratio) and the arm-bias medians (BM25 113 against dense 83,
realised multi-term retrieval) are different quantities, not a contradiction. And on the
GV-4.3-001 correct-identifier case only, fused rank 28 is worse than dense 12 because BM25
at 568 drags fusion, recorded as a single case, not a claim about RRF.

Commit, local only:
- 5a240b7 docs: relabel the 127 as a dense-arm property, state the context-set boundary directly

Current state:
- Local git on `main`, no remote, nothing pushed. Retrieval scope complete and its
  determinism story corrected to distinguish the dense arm from the fused context set. Two
  governance drafts remain for Hasan to place in `rag_case_study_tracker.md`: the Section 4
  defect 6 entry and the Section 3 verifier count 28 to 30.

Next step:
- Pre-registration: the sealed test query set and gold passages, committed and timestamped
  before any generation run, immutable once results exist.

## 2026-07-24, retrieval scope closed: development queries, full-population diagnostics, GV-4.3-001

Development queries authored and run under a two-commit blindness protocol, both
diagnostics extended to the full population, and one documented extraction property
verified against the shipped retriever. This closes the retrieval scope.

Development queries. Twelve authored blind from unit text, committed with their
embeddings before any retrieval ran (0b9c6e2), results committed after (78cc246), so the
freeze is provable from git. 10 of 11 gold queries hit; the one miss, near-miss dev_11,
is kept as a finding: querying GOVERN 6.1's AI Transparency Resources returned
near-duplicate resource blocks from other subcategories, the discrimination failure it
was written to probe. The out-of-corpus query returns unrelated chunks; abstention is the
layer's job. Development results are guarded, in the README and the manifest, as never a
quality metric; the only quality numbers come from the sealed pre-registered set under
the deterministic grader.

Blind-authoring claim narrowed. The commit ordering proves the queries were frozen before
any result existed, not that retrieval was never run during drafting. The README now says
the first and not the second.

Diagnostics at scale. Extended from 12 to the full 1506 population, recorded distinct.
Embedding gap: 127 of 1506 queries have a rank 10 to 11 boundary gap below the 1e-4 grain,
which corrects the thin-sample claim that the boundary stays above it. Those boundaries
merge into ties resolved deterministically by chunk id, so reproducible across
implementations, but decided by chunk id rather than a score margin. Arm bias over 1506:
BM25 113, dense 83, fused 94; the fused-longer-than-both seen on 12 queries does not hold
at scale, recorded and left uncharacterised.

GV-4.3-001 verified. The action id the PDF prints garbled as GV4.3--001, stored verbatim
with only the derived key normalised. Against the shipped retriever the correct identifier
GV-4.3-001 ranks the target at BM25 568, dense 12, fused 28, out of the top-10; the garbled
surface and the action text rank it 1. The documented lexical-mismatch behaviour held. A
one-off verification, not added to the query set.

Commits, local only:
- 0b9c6e2 feat: twelve blind-authored development queries and their embeddings
- 78cc246 feat: development-query retrieval results and diagnostics
- bb1141d docs: full-population diagnostics, dev-set guards, GV-4.3-001 verification

Current state:
- Local git on `main`, no remote, nothing pushed. Retrieval scope complete: retriever,
  embeddings, fixture, artifacts, development pool, development queries and results,
  manifest, and tests all committed. Two governance drafts remain for Hasan to place in
  `rag_case_study_tracker.md`: the Section 4 defect 6 entry, and the Section 3 verifier
  count 28 to 30.

Next step:
- Pre-registration: the sealed test query set and gold passages, committed and timestamped
  before any generation run, immutable once results exist. Then the single paid generation
  step, which requires the stated Console balance first.

## 2026-07-24, residual mechanism clarified, the straddling chunk need not be one that swaps

The score determinism residual recorded its measurement and its single audited case
but not the shape of the mechanism, which left a narrow test available: look at the
two chunks whose order changes, find neither near a rounding boundary, and conclude
no straddle occurred. The commit predates this entry, which carried none when it
landed.

That test is wrong. A boundary straddle anywhere in the dense top-100 moves the
straddling chunk's rank, which moves the rank of every chunk it passes, and
reciprocal rank fusion converts those moved ranks into changed contributions. The
swap therefore surfaces between two chunks that need not sit near any boundary. The
audited case is the demonstration: nist_playbook:sub_GOVERN_1.7.suggested_actions
straddles the 0.76355 boundary, and the pair that reorders is act_GV-6.2-003 with
sub_GOVERN_6.2.about, neither of which is the straddling chunk.

Recorded in the manifest as boundary_can_be_a_third_chunk, inside the residual block
it qualifies, so the narrow test is refused where the measurement that invites it is
stated rather than in a separate note. No measurement changed: the 63 to 1 cross-path
reduction, the zero membership changes across 1506 queries and the 4dp precision
stand as recorded.

Commits:
- f9f93fe docs: clarify residual mechanism, straddling chunk need not be a swapped one, local only

## 2026-07-24, retrieval determinism residual corrected, defect 6, and a commit-trailer transition

### Defect 6, residual measurement corrected

The quantisation residual worst-case, recorded in an earlier manifest as 17 affected
known-item queries, was measured by an enumeration over near-boundary chunks that
excluded identical-vector pairs as deterministic. That holds for the per-query matvec the
retriever ships, but not for a batched matrix product, which reduces identical rows in
different tile orders and assigns them scores differing by ~1e-7, breaking their tie
nondeterministically. Reciprocal rank fusion sums over ranks, not scores, so a single
dense-rank flip near position 10 changes an RRF contribution by ~1/70 minus 1/71, about
2e-4, three orders of magnitude larger than the score difference that caused it. The
enumeration's framing, a score being near a boundary, was the wrong question, and it
under-counted the unquantised case at 4 against a direct 63.

Corrected to the direct measurement: cross-path top-10 disagreement between the shipped
per-query matvec and a batched matmul, a local proxy for cross-implementation variation
and explicitly not a cross-hardware measurement. Unquantised 63 of 1506 queries, quantised
1 of 1506 with zero membership changes across all 1506; the model receives the identical
chunk set on both paths and one query differs only in order. Quantisation reduces
cross-path disagreement 63 to 1, the measured justification that it earns its place,
stronger than the enumeration it replaces. The single residual case is audited in the
manifest and behaves exactly as the mechanism predicts. The 4dp precision is unchanged.

Same class as the U+FFFE hyphenation defect: our own residual measurement was wrong, our
own follow-up counterfactual caught it, the correction strengthened the case for
quantisation rather than weakening it, fixed forward with no rewrite, pinned in a test.
The 17 is kept in the manifest as superseded with the reason it was wrong, per the repo
pattern that corrections are visible rather than history looking clean.

### Commit-trailer transition, recorded

The 25 commits before this session's retrieval build carried no trailer. The 7
retrieval-build commits, and every commit onward when this was written, carried a
Claude-Session provenance trailer. The reason is the harness default: unlike the co-author
byline, which `includeCoAuthoredBy` disables and which was removed repo-wide under the spent
Rule 10 override, the session trailer is not configurable through any setting, environment
variable, or flag, confirmed against the settings schema. The decision was to fix forward
rather than rewrite, consistent with Rule 10 being spent, so the seven were the start of the
convention then in force.

Commits, local only:
- 8685632 docs: correct retrieval determinism residual, defect 6
- 935c6aa test: pin cross-path fusion determinism, defect 6 regression

Current state:
- Local git on `main`, no remote, nothing pushed. Manifest residual corrected, defect 6
  pinned in `tests/test_retrieval_determinism.py`. Two governance items are drafted for
  Hasan to place, both in `rag_case_study_tracker.md`: the Section 4 defect 6 entry, and a
  stale mechanical reference, the verifier check count moved from 28 (22 vendor) to 30 (24
  vendor) when `README.md` and `1_Pooling.config.json` were vendored.

Next step:
- Development queries, twelve from the reserved pool, authored blind before any retrieval
  run, no query revised for performing badly. Then the embedding-gap and arm-bias
  diagnostics on this final pipeline, with query embeddings committed alongside.

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
- 2205607 feat: normalised bge-base-en-v1.5 embeddings via ONNX
- 8f07f2c feat: hybrid BM25 plus dense retriever with dense-arm quantisation
- beb3216 feat: verbatim group and near-duplicate exception artifacts
- a338376 feat: reserved development unit pool, committed before any dev query
- 691c4bf test: known-item fixture and deterministic retrieval checks
- a5a74dc docs: retrieval manifest recording final config and measurements

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

Commit: aa61ea9
  (fix: symmetric structural_join, EU downstream_notes, AI 100-1 prose schema and
  header strip, local only)
  This entry is recorded by the next commit, `docs: log corpus freeze commit,
  local only`, committed immediately after this entry is written, which closes the
  chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-five commits, all trailer-free.
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

Commit: 66448f0
  (feat: structure-aware ingestion of NIST AI 600-1 and the Playbook with the
  wired resolver, local only)
  This entry is recorded by the next commit, `docs: log AI 600-1 and Playbook
  ingestion commit, local only`, committed immediately after this entry is
  written, which closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-three commits, all trailer-free.
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

Commit: 44f2368
  (fix: apply hyphen resolver to NIST AI 100-1 output, correcting the thirdparty
  defect class, local only)
  This entry is recorded by the next commit, `docs: log AI 100-1 hyphen fix
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is twenty-one commits, all trailer-free.
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

### What is committed at f80d46e

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

Commit: f80d46e
  (feat: wire wordlist tier into hyphen resolver with fragment test, commit
  corpus decision log, local only)
  This entry is recorded by the next commit, `docs: log hyphen resolver wiring
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is nineteen commits, all trailer-free.
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

### What is committed at 29cc8fc

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

Commit: 29cc8fcfeb841cee5c0bde6b154c147ba9c7705d
  (feat: vendor SCOWL English wordlist and deterministic builder for hyphen
  resolver, local only)
  This entry is recorded by the next commit, `docs: log wordlist vendoring
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is seventeen commits, all trailer-free.
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

Confirmed corrupted in the AI 100-1 output committed at e4fd217: thirdparty,
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

### What is COMPLETE and committed at be81945

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

Commit: be8194593e9e8c0f3d09c798b0c21186145bb98c
  (fix: correct hyphen-join neighbour extraction and footer tail-strip, partial,
  local only)
  This entry is recorded by the next commit, `docs: log hyphen defect checkpoint,
  local only`, committed immediately after this entry is written, which closes
  the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is fifteen commits, all trailer-free.
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

Commit: e8ee5c995066f82a8842edb02c34e3d7dc054e96
  (docs: record why two partition whitespace classes are equal, local only)
  This entry is recorded by the next commit, `docs: log partition whitespace
  note commit, local only`, committed immediately after this entry is written,
  which closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is thirteen commits, all trailer-free.
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

Commit: e4fd217bd4a1bec41577765d12b3e859743ba18d
  (feat: structure-aware NIST AI 100-1 ingestion with partition proof, local only)
  This entry is recorded by the next commit, `docs: log NIST AI 100-1 ingestion
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is eleven commits, all trailer-free.
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

Commit: bade8bdd7f4ce0071d7c333dda1437be9f77a0d4
  (feat: extend integrity verifier to vendored files, local only)
  This entry is recorded by the next commit, `docs: log vendor verifier commit,
  local only`, committed immediately after this entry is written, which closes
  the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is nine commits, all trailer-free.
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

Commit: f4d21deaff8ca968a0db14e9ddae47cb62ec00af
  (feat: structure-aware EU AI Act ingestion with integrity verifier, local only)
  This entry is recorded by the next commit, `docs: log EU AI Act ingestion
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is seven commits, all trailer-free.
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

Commit: 57e633f6f50d2051ed99ba701bd8a4143c8ce601
  (feat: add NIST AI RMF and EU AI Act corpus with provenance, local only)
  This entry is recorded by the next commit, `docs: log corpus acquisition
  commit, local only`, committed immediately after this entry is written, which
  closes the chain so the next session inherits no unlogged commit.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is five commits, all trailer-free:
  f98a03bd bootstrap, d574a88b session log, 0d19261 log of the tracker commit,
  57e633f corpus acquisition, and this log commit.
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
  CLAUDE.md for stale-reference corrections. The tracker commit is logged here, and
  this entry names its own recording commit so the log-of-the-log does not spawn an
  endless tail of unlogged commits.

Current state:
- Local git repository on branch `main`, no remote configured, nothing pushed.
  Once this log commit lands the history is three commits, all trailer-free:
  f98a03bd bootstrap, d574a88b session log, and this log commit.
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

Commit: f98a03bd7b7afbb2aac2b921f8ff0ab201a267c1
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
