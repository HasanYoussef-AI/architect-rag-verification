# Layer predictions

Recorded before any component of the verification layer is written, so no outcome can be fitted
after the fact. The retrieval results predicted against are frozen in `eval/test_retrieval_results.json`,
committed at `356f23d` and pinned at `14251d1`. This file commits before `src/complete/` holds any
module.

The layer-gold firewall in `CLAUDE.md` governs. Two routes are barred there and neither appears in
the grammar below: no parent subcategory identifier is derived from an action identifier, and no
inverse citation index is built.

## Epistemic status

The stratum figures below are hand derivations, produced by scratch computation over committed
artifacts before any shipped component existed. They are not measurements of the layer, which does
not exist at this commit.

The falsifiable claim this file commits is therefore narrow and exact: the shipped C1 to C3
reproduce every figure below, to the row. A disagreement between the shipped output and the
derivation here is information and stops the scope, and it is resolved by finding which of the two
is wrong rather than by editing this file to match the code. That is the cross-implementation
discipline of V4 applied to a prediction: two implementations of the same rule disagreeing is the
signal, and only one of them can be committed before the other exists.

The grammar in section 2 was fixed on the corpus's own citation forms, not on the query set's
outcomes, and its design choices are disclosed rather than left implicit. The one choice that could
have been fitted is block composition, which is restricted to query text; re-deriving every figure
below with block composition also allowed on retrieved text changes no recovery on any of the fifty
rows while raising reference volume, so the restriction is verified to be null on outcomes and is
taken for the false-positive surface it removes. No augmentation bound is chosen anywhere in this
file, for the reason recorded in section 5.

The sealed gold was visible to this derivation, because the repository holds it and the derivation
was performed by reading committed files. That is not a firewall breach. The firewall binds the
operational layer's runtime inputs, not the measurement or the person writing the prediction, and
the components specified here receive only what `CLAUDE.md` allows them. The asymmetry is
deliberate: a prediction that could not be checked against gold before the run would be unable to
state anything falsifiable.

## 1. Measured statics

Three static measurements bound what any prediction may claim. Each re-derives from committed files
with no model and no key.

### A. The anchor print condition on the action-to-parent stratum

All four action anchors print their identifier as the first token of their own chunk text, and all
four sit at fused rank 1 in their row's committed top 10.

    nist_ai_600_1:act_MG-2.2-003   "MG-2.2-003\nEvaluate feedback loops between GAI system content provenance and human\nreviewers, and update where needed. ..."
    nist_ai_600_1:act_MP-2.3-001   "MP-2.3-001\nAssess the accuracy, quality, reliability, and authenticity of GAI output by\ncomparing it to a set of known ground truth data ..."
    nist_ai_600_1:act_MS-2.2-003   "MS-2.2-003 Provide human subjects with options to withdraw participation or revoke their\nconsent for present or future use of their data in GAI applications. ..."
    nist_ai_600_1:act_GV-3.2-004   "GV-3.2-004 Establish policies for user feedback mechanisms for GAI systems which include\nthorough instructions and any mechanisms for recourse. ..."

`unit_label` carries the same identifier on each, and is present and non-empty on every committed
chunk.

The corpus prints the prefix legend. Its carrier is `nist_ai_600_1:sec_3#p1`, the only committed
chunk whose text contains the string "GV = Govern":

    Action ID: Each Action ID corresponds to the relevant AI RMF function and subcategory (e.g.,
    GV-1.1-001 corresponds to the first suggested action for Govern 1.1, GV-1.1-002 corresponds to
    the second suggested action for Govern 1.1). AI RMF functions are tagged as follows: GV =
    Govern; MP = Map; MS = Measure; MG = Manage.

The route this would open is barred by the firewall. The measurement is recorded so the bar reads
as removing a route that exists rather than one that does not.

Recorded with it, because a null result is only trustworthy beside evidence of what the command
did: two detectors run before the one that found this legend returned zero. A co-occurrence window
around each bare two-letter code tested for the uppercase function word and matched only layout
adjacency; a line-scoped scan for two codes and two function words returned zero on all four
documents. Both missed because the legend prints "Govern" in title case where the headings print
"GOVERN", and the second additionally because the legend spans a line break. The exhaustive funnel
found it: survivors after removing action-id heads were 1 of 60 for GV, 1 of 40 for MP, 1 of 73 for
MS and 1 of 44 for MG, all four the same sentence. A stated lexical rule over this scheme has to
casefold, and any detector the layer ships that matches an identifier must be case-normalised and
must not be line-scoped.

### B. Back-references on the five clean multi-hop misses

Whether any pointer to the missing unit is present in the row's retrieved context. Scanned over the
committed text of every chunk in each row's top 10, each candidate adjudicated against the
committed classifier's own evidence record.

    row      retrieved unit    missing unit       pointer in retrieved context
    test_10  art_60, source    eu_ai_act:art_49   yes, in art_60#p2 at rank 3, twice
    test_19  art_25, source    eu_ai_act:art_16   yes, in art_25#p1 at rank 2, twice
    test_13  art_78, target    eu_ai_act:art_113  no, 0 of 8 Article surfaces
    test_16  art_91, target    eu_ai_act:art_92   no, 0 of 6 Article surfaces
    test_18  art_14, target    eu_ai_act:art_13   no, 1 surface, external

The single test_18 surface, from `eu_ai_act:art_26#p3` at rank 3:

    For high-risk AI systems used for law enforcement purposes Article 13 of Directive (EU)
    2016/680 shall apply.

It names Directive (EU) 2016/680 and resolves to no unit in this corpus. The genuine internal
citation to `eu_ai_act:art_13` lives in `eu_ai_act:art_26#p2`, which is not in test_18's top 10.
That is the measured case behind the firewall's per-chunk clause: a unit-level read would report a
pointer the first pass never returned.

The split is by citation direction. Where the retrieved unit is the citing source, a forward
pointer is present. Where the retrieved unit is the cited target, no pointer exists in retrieved
context, and reaching the source would require the inverse citation walk the firewall bars.

### C. What enters the retrieval index

Neither arm indexes an identifier that the span text does not contain.

    src/retrieve/retriever.py         self.texts = [c["text"] for c in chunks]
                                      self.bm25 = BM25([tokenize_document(t) for t in self.texts], ...)
                                      self.chunk_ids is a label array, passed only to rank_within_arm
    src/retrieve/build_embeddings.py  texts = [c["text"] for c in chunks]
                                      embeddings = embed_texts(texts, session, batch_size=BATCH_SIZE)
    src/retrieve/tokenize.py          def tokenize_document(text: str) -> list[str]

A lexical re-retrieval keyed on an identifier can therefore reach a unit only through that
identifier's presence in the unit's own span text. The corpus carries one recorded counter-example.
The retrieval manifest's `garbled_identifier_verification` records that a query carrying the
correct `GV-4.3-001` ranks its target at BM25 568 of 1294 and fused 28, while the garbled printed
surface `GV4.3--001` ranks it 1 and 1.

This is the measured basis for resolution and direct fetch rather than lexical re-retrieval.
Composing `GV-4.3-001` into a unit id and testing membership against `eval/corpus_unit_index.json`
returns the target; a BM25 query for the same string does not reach a top 10.

## 2. The reference grammar, fixed

Fixed here, before any component executes. Applied uniformly to every stratum.

### 2.1 Extraction patterns

Applied to the query text, and to the `text`, `chunk_id` and `unit_label` of every chunk in the
fused top 10. Case sensitive as printed.

    R_ART   \bArticles?\s+(\d{1,3})\b
    R_ANX   \bAnnexe?s?\s+([IVXLC]{1,6})\b
    R_SUB   \b(GOVERN|MAP|MEASURE|MANAGE)\s+(\d+\.\d+)\b
    R_ACT   \b(GV|MP|MS|MG)-?(\d+\.\d+)-+(\d{3})\b

`R_ACT` is the tolerant form, deliberately identical in shape to `_ACTION_TOLERANT` in
`src/ingest/nist_ai_600_1.py`, which is the pattern the corpus was ingested under. It matches the
correct printed form and the one damaged surface alike.

### 2.2 Composition into unit ids

    R_ART   -> eu_ai_act:art_<n>
    R_ANX   -> eu_ai_act:anx_<ROMAN>
    R_ACT   -> nist_ai_600_1:act_<PREFIX>-<n.m>-<ddd>
    R_SUB   -> {nist_ai_100_1, nist_ai_600_1, nist_playbook}:sub_<FUNC>_<n.m>, three candidates

This is identity resolution and not relation traversal: each pattern composes a printed name into
the unit id of the unit bearing that name. No pattern maps one unit's identifier to a different
unit that a relation asserts is related to it.

`R_SUB` composes three candidates because the same printed subcategory identifier names a unit in
up to three documents. NIST AI 600-1 is a profile covering 49 of the 72 subcategories, so a
subcategory reference resolving in two documents rather than three is normal and is not evidence of
non-existence.

### 2.3 Block composition, query text only

Where the query text carries both an `R_SUB` surface and a Playbook block phrase, the two compose:

    nist_playbook:sub_<FUNC>_<n.m>.<slug>

The five slugs are the whole vocabulary, measured over the committed unit index at 72 units each,
360 in total beside the 72 bare subcategory statement units:

    "about"                        -> about
    "suggested actions"            -> suggested_actions
    "transparency & documentation" -> transparency_documentation
    "ai transparency resources"    -> ai_transparency_resources
    "references"                   -> references

Phrases match case-insensitively, longest phrase first, and the first match in that fixed order is
taken, so the rule is deterministic.

Block composition is restricted to query text on a stated principle: the block type is part of the
information need, which the query states. A retrieved chunk containing the ordinary English word
"references" or "about" is not asking for that block. The restriction's null effect on recovery is
recorded under Epistemic status.

### 2.4 The external-instrument filter

An `R_ART` surface is dropped where the text immediately following it, within 40 characters and
allowing one parenthesised subdivision, matches:

    ^\s*(?:\([^)]*\)\s*)?of\s+(?:the\s+)?(Directive|Regulation|Treaty|Charter|Decision|Convention)\b

This is the layer's own filter over text it reads. It does not consult
`data/chunks/eu_ai_act.xrefs.jsonl`, which is a gold source for the clean multi-hop stratum and is
barred.

Measured over the fifty rows, the filter drops 44 surfaces on 13 rows, including the exact case
that would otherwise produce a false recovery signal on test_18:

    Article 13   "of Directive (EU) 2016/680 shall apply."

That case is the filter's V20 demonstration. It is shown red on the one occurrence it exists to
catch before it is trusted anywhere.

44 is a count of drop events and needs no deduplication key. Any deduplicated figure quoted
anywhere ships with its key stated as artifact, field and accepted values, because the same
population yields different counts under different keys: deduplicating on the row, the surface and
the matched qualifier gives 36, and on the row, the surface and a 39-character trailing context
gives 42. The row count of 13 is stable across all three.

SUPERSEDED. This paragraph read "the filter drops 42 distinct surfaces on 13 rows". Replaced by 44
drop events on 13 rows. The defect is not the number 42, which is correct under one key; it is that
the sentence described a filter by a property in prose, "distinct", with no key stated, which is
the failure the Receiving an instruction section of CLAUDE.md describes and which landed here in
this repository's own file. The corrected figure is the key-free one, chosen before the shipped
module's own key was known to differ and not equal to it.

### 2.5 Resolution and fetch

A composed unit id resolves when it is a member of `eval/corpus_unit_index.json`. A reference
resolves when any of its candidates resolves. A resolved unit is absent when none of its chunks is
in the fused top 10. Fetching an absent resolved unit returns its committed chunks from
`data/chunks/*.chunks.jsonl`.

Resolution and fetch involve no model, no key, no embedding and no ranking, so every figure the
layer produces stays at reproducibility level 1.

### 2.6 The GV4.3--001 handling, a fixed grammar test case

The single documented garbled identifier is a required test case rather than an exception. Both
printed surfaces normalise to one resolvable unit id:

    "GV-4.3-001"  -> nist_ai_600_1:act_GV-4.3-001   resolves
    "GV4.3--001"  -> nist_ai_600_1:act_GV-4.3-001   resolves
    "GV-4.3-002"  -> nist_ai_600_1:act_GV-4.3-002   resolves

The third is a negative control on the tolerance: a neighbouring well-formed identifier must not
collapse onto the garbled one. A grammar that resolves only the correct form, or that maps the two
surfaces to different ids, is wrong, and the regression test pins both directions.

## 3. The measurement convention

The two conditions never share a metric label anywhere in this repository.

    first pass       Recall@10, Precision@10, MRR, NDCG@10, against the fused top 10 of chunks,
                     exactly as PREREGISTRATION.md defines them and exactly as frozen.
    layer condition  recovered-passage recall, over the final context set, with the final context
                     set size reported per row beside it.

The layer condition reports no Precision@10, no MRR and no NDCG@10. Under augmentation the context
set is not ten chunks, and the fetched units carry no rank order comparable to a fused ranking, so
every rank-based figure would be about arithmetic rather than about the layer. A precision that
falls purely because k grew would be the clearest example.

"recovered-passage recall" is `PREREGISTRATION.md`'s own term for this quantity. Its null-
interpretation clause reads "does not improve recovered-passage recall", written before any result
existed, so the layer condition is reported under the name the pre-registration already gave it
rather than under a first-pass label it does not satisfy.

First-pass figures are quoted unchanged wherever they appear.

## 4. The augmentation policy

Augmentation is uniform across all fifty rows. The layer cannot condition on stratum, because
`type` and `subtype` are barred, so no policy that varies by stratum is implementable without
breaking the firewall.

The policy is augmentation-only: the first-pass ten are never removed, never reordered and never
truncated. Every absent resolved unit is fetched and appended.

Measured volume, absent resolved units per row:

    stratum                              n    min  median  max   mean
    single_hop/eu_ai_act                 11   1    9       24    9.7
    single_hop/nist_ai_100_1              5   0    5       21    6.6
    single_hop/nist_ai_600_1              2   3    5        5    4.0
    multi_hop/eu_internal_xref           12   2    11      19    10.2
    multi_hop/action_subcategory          4   0    11      17    7.8
    near_miss/block_clusters              3   21   22      27    23.3
    near_miss/near_duplicate              5   25   28      29    27.6
    adversarial/iso                       3   11   19      27    19.0
    adversarial/nonexistent_identifier    4   6    20      21    13.5
    adversarial/out_of_domain             1   12   12      12    12.0
    adversarial, three subtypes           8   6    19      27    15.375
    all fifty                            50   0    11      29    12.66

The adversarial mean is 123 over 8. The three subtype rows are carried beside the combined row so
that arithmetic is checkable from the table rather than taken on trust, which is what the combined
row alone did not allow.

SUPERSEDED, two figures in this table, both under section 2.3's grammar rather than the variant the
table was first computed under.

The `adversarial/out_of_domain` row read 13 for its single row, test_08, and reads 12. Cause: the
table was computed with block composition allowed on retrieved text, the unrestricted variant that
section 2.3 of this file rejects. test_08 is the only row of the fifty whose absent count differs
between the two variants, and no recovery on any row differs, which is the measurement recorded
under Epistemic status.

The `adversarial, three subtypes` mean read 15.9 and reads 15.375. Cause: arithmetic error. 15.9
matches neither grammar variant; the unrestricted variant gives 15.5 and the committed grammar
gives 15.375. The figure was never derived, and the combined row carried it without the component
rows that would have exposed it. The `all fifty` mean moves from 12.7 to 12.66 as a consequence of
the test_08 correction; both round to 12.7 at one decimal place, so the displayed change is
precision rather than a superseded value.

Neither supersession touches a prediction. Every recovery, every per-row single-hop count, every
stratum recall figure and the overall figure in section 6 are unchanged and were reproduced exactly
by the shipped component.

The adversarial consequence is stated here rather than discovered at the generation scope.
Abstention on that stratum will be evaluated against augmented context, mean 15.375 added units,
and the layer has no permitted way to decline. This pushes the stratum in the harder direction,
since more plausible in-corpus text is a stronger invitation to answer than less, so whatever
abstention survives is a stronger result than the same figure on the first pass alone. The
generation predictions themselves belong to the generation scope and none is made here.

## 5. The absence of a bound, as a named condition

No bound on augmentation volume is chosen in this file.

Every figure in section 6 assumes the policy admits every absent resolved unit. A bound would leave
them unaffected only if it admitted references carried by chunks at ranks 2 and 3, which is where
test_10, test_19 and test_41 draw theirs. That fact was known before this file was written, which
is precisely why no bound is set here: a threshold chosen after deriving the table it will judge is
fitted to its own observations, per V15.

If a bound is adopted later it is a cost decision, set from the cost budget rather than from the
recovery table, and it ships with the recoveries it removes reported by row.

## 6. Predictions

Recall figures are macro-averaged over queries, matching the frozen artifact's own convention. The
first-pass column re-derives from the committed artifact; the derivation was cross-checked against
the committed overall figure and agreed at 0.6785714285714286.

### 6.1 Clean multi-hop, twelve rows

Recovery on exactly two rows, by forward citation resolution from retrieved text:

    test_10   eu_ai_act:art_49   from "Article 49(4), point (d)" and "Article 49(5)" in art_60#p2, rank 3
    test_19   eu_ai_act:art_16   from two "Article 16" surfaces in art_25#p1, rank 2

Zero recovery on test_13, test_16 and test_18, on measurement B. No pointer to the missing unit
exists anywhere in those rows' retrieved context, so no component reading retrieved context can
reach it, and the only route that could is the inverse citation walk the firewall bars. This is
predicted as a permanent limit of the design rather than a tuning shortfall, and it ships as a
what-still-fails entry whatever the run shows.

    stratum recall, first pass Recall@10          0.7917
    predicted recovered-passage recall             0.8750

Contradicted by: recovery on any of test_13, test_16 or test_18; non-recovery on test_10 or
test_19; a stratum figure other than 0.8750.

### 6.2 Action-to-parent, four rows

Zero recovery on test_39, test_40 and test_42. On test_39 the grammar extracts seven references and
every one is already in the top 10, so nothing is fetched at all. On test_40 and test_42 the
grammar fetches units, none of them gold: test_40's retrieved Playbook blocks carry MEASURE 1.1,
MEASURE 2.13 and MEASURE 2.2 labels against a gold of MAP 2.3, and test_42's carry GOVERN 5.1, 1.5,
6.1 and 1.3 against a gold of GOVERN 3.2. The grammar is not an oracle and these three rows
demonstrate it.

Recovery on test_41, of all three carriers of its single slot, by a route that is not the barred
one. The mechanism, named:

    the first pass returned three Playbook sibling blocks of the gold subcategory,
    nist_playbook:sub_MEASURE_2.2.suggested_actions at rank 2,
    nist_playbook:sub_MEASURE_2.2.transparency_documentation at rank 3, and
    nist_playbook:sub_MEASURE_2.2.about at rank 5. Their unit_label values begin "MEASURE 2.2".
    R_SUB extracts that printed subcategory citation from the label and composes three candidates,
    all three of which resolve and all three of which are the slot's acceptable units. No action
    identifier is read and no legend is applied.

Measured, the label is the only carrier. On the four rows the derived parent label occurs in chunk
`text` 0 times out of 10 on every row, and in `unit_label` 0, 0, 3 and 0 times. test_41 recovers
because the first pass happened to surface the parent's own neighbourhood; the other three do not
because it did not.

    stratum recall, first pass Recall@10          0.0000
    predicted recovered-passage recall             0.2500

The split form ships everywhere this stratum figure appears: zero of four by any parent-derivation
route, one of four by sibling-label resolution, with the mechanism named on the row. The bare
sentence "the layer recovers an action-to-parent row" is false about the route that matters and is
not used.

Contradicted by: any recovery on test_39, test_40 or test_42; non-recovery on test_41; any recovery
on test_41 whose trace shows an action identifier or the legend being read.

### 6.3 Near-miss, eight rows

The context-absence flag fires on exactly seven rows, test_43, test_44, test_46, test_47, test_48,
test_49 and test_50, and does not fire on test_45.

The mechanism is query-text resolution and it is close to tautological, which is stated here rather
than discovered later. Every query in the stratum has the fixed form "Which AI transparency
resources does the Playbook list under <IDENTIFIER>?", so the query text names the document, the
block type and the subcategory identifier, and composing the three under section 2.3 yields exactly
the row's gold unit id. All eight gold unit ids are members of the committed unit index. On test_45
the composed id is already in the top 10 at rank 7, so it is not absent and the flag does not fire;
on the other seven it is absent and the flag fires.

    predicted recovery                             7 of 7 missed rows
    block_clusters, first pass Recall@10  0.3333 -> recovered-passage recall 1.0000
    near_duplicate, first pass Recall@10  0.0000 -> recovered-passage recall 1.0000

Recovery here is a property of how the queries were written, not a demonstration that a
verification layer finds passages a retriever missed. That attribution is a locked disclosure: it
travels with this figure into the README and the results tables, and the figure is not quoted
without it.

The retrieval-path result stands unchanged and is the finding of substance for this stratum. On the
seven missed rows neither the anchor nor its designated competitor is in the top 10, so the stratum
measured crowding by other subcategories' blocks under the same generic heading, between 7 and 10
of the ten places with median 8, rather than the pairwise displacement its rows predicted. The
layer's completeness check acts on crowding. A recovery figure of 7 of 7 does not retire that
finding and does not convert it into a discrimination result.

Contradicted by: the flag firing on test_45; the flag failing on any of the seven; recovery below
seven.

### 6.4 Single-hop, eighteen rows

Completeness delta exactly zero on 18 of 18. All eighteen are at recall 1 on the first pass, every
gold slot is already satisfied, and the policy is augmentation-only, so no committed gold chunk
leaves any context set and no slot can become unsatisfied. The prediction is exact rather than
approximate: the delta is 0.0000, and any non-zero value is a defect in the augmentation policy
rather than a result.

The flag fires widely here, which is expected and is not a completeness failure. The EU AI Act
cites itself densely, so a row whose gold is fully retrieved still carries many resolvable
references to units outside its top 10. Predicted counts of absent resolved units, per document
family:

    single_hop/eu_ai_act       11 rows, 11 with at least one absent reference, 107 total
                               per row: 9, 17, 9, 24, 1, 3, 7, 12, 14, 2, 9
    single_hop/nist_ai_100_1    5 rows,  4 with at least one absent reference,  33 total
                               per row: 5, 5, 0, 21, 2
    single_hop/nist_ai_600_1    2 rows,  2 with at least one absent reference,   8 total
                               per row: 5, 3

test_34 is the only row of the fifty at zero absent references, so a zero there reads as reproduced
rather than as a missing measurement.

Contradicted by: any non-zero completeness delta; any per-row count differing from the lists above.

### 6.5 Adversarial, eight rows, detection only

No augmentation figure is predicted, because gold is empty and the retrieval metrics are not
computed for this stratum by the pre-registration's own exclusion. What is predicted is the
detection signal, and it splits by a property the layer can see without reading any annotation.

    subtype                  rows  citation-formed reference in query text  resolves
    nonexistent_identifier      4  yes, one per row                         0 of 4
    iso                         3  none                                     not applicable
    out_of_domain               1  none                                     not applicable

The four `nonexistent_identifier` queries name `Article 114`, `Article 181`, `GOVERN 1.8` and
`GOVERN 7.1`. Each is well formed under the grammar and each composes to a unit id, or three, that
is absent from the committed unit index. Non-resolution is therefore a deterministic abstention
signal available on all four rows, reached from the query text and the unit index alone.

The three `iso` queries and the one `out_of_domain` query carry no citation-formed reference at
all, so this component supplies no signal on them and abstention has to come from the grounding
check. That asymmetry is a real limit, predicted rather than discovered: a deterministic identifier
check addresses the fabricated-provision half of the adversarial stratum and contributes nothing to
the other half.

The subtype grouping in the table is an analysis grouping applied by the reader of this file. The
layer never reads `subtype`, and both behaviours above are reached only from the query text and the
unit index.

Contradicted by: any of the four fabricated identifiers resolving; a citation-formed reference
being extracted from an `iso` or `out_of_domain` query text; the layer behaving differently on two
rows that present identically on these two properties.

### 6.6 Overall

    gold-bearing rows                              42, the eight adversarial rows excluded
    first pass Recall@10                           0.6786
    predicted recovered-passage recall             0.8929
    predicted delta                                +0.2143

The delta is dominated by the near-miss stratum, which contributes seven of the ten recovered rows.
Its recovery is a query-construction property, per section 6.3, and reported without that
attribution the overall figure would overstate what the layer does. The clean multi-hop delta of
+0.0833 on two rows recovered from printed forward citations is the figure that reflects the
completeness surface as `docs/METHODOLOGY.md` describes it.
