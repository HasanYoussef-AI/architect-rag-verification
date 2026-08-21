# Generation predictions

Recorded before any batch is submitted. No model has seen a query or a chunk from this
repository at the commit that places this file. The parameters below are measured, the
prompts are the literals the assembler will send, and the numbered predictions in section 10
are priors written against outcomes that do not exist yet.

This file is the generation counterpart to `eval/layer_predictions.md`, which committed before
`src/complete/` held any module, and it follows that file's pattern: what is measured is
separated from what is predicted, and every prediction carries the observation that would
contradict it.

## Epistemic status

Four different kinds of statement sit in this file and they are not interchangeable.

THE PREDICTIONS IN SECTION 10 ARE PRIORS. They are written before generation, they are not
derived from any model output, and several of them will be wrong. A prediction that fails is
the mechanism working; it is recorded as contradicted and it is not edited to match the
result. Section 10 states the contradicting observation for every line.

THE PARAMETERS IN SECTION 1 ARE MEASUREMENTS. Every one is read from
`data/runs/run_manifest.json`, which `python -m src.generate.manifest` writes and which
re-derives byte for byte from committed inputs. The temperature settings rest on the six
probe records that artifact carries verbatim. Nothing in section 1 is a reading of
documentation where a measurement exists, and where only a reading exists the file says so.

THE GRADER THRESHOLDS IN SECTION 5 ARE CANDIDATES, NOT SETTINGS. They are proposed here and
they are frozen at the grader commit, against the twelve development first-pass generations
on each tier and against nothing else. After that commit they never move. A threshold chosen
after seeing the observations it will judge is fitted, and the sealed fifty are the
observations this instrument exists to judge, so they are not available to it at any point.
The development second-call answers are graded after the freeze only to show the path
executes, and no threshold moves on what they show.

THE SEALED GOLD WAS VISIBLE TO THE AUTHOR OF THESE PREDICTIONS and is invisible to the
operational layer and to the grader. The repository holds the gold and this file was written
by reading committed files, including the sealed query set's verification record. That is not
a firewall breach: the layer-gold firewall in `CLAUDE.md` binds the operational layer's
runtime inputs, not the measurement and not the person writing the prediction. The grader of
record reads the committed answer and the committed context of the request that produced it,
and never gold. The asymmetry is deliberate, and it is the same one `eval/layer_predictions.md`
records: a prediction that could not be checked against gold before the run would be unable
to state anything falsifiable.

## 1. Measured parameters

All read from `data/runs/run_manifest.json`.

### 1.1 Models and the decoding parameter

The three model strings, exactly as the run sends them:

    haiku45  claude-haiku-4-5-20251001
    sonnet5  claude-sonnet-5
    opus48   claude-opus-4-8

`PREREGISTRATION.md` fixes the decoding parameter as temperature 0 where the API accepts it
and the parameter omitted where it rejects it, with the per-tier setting recorded in the
committed run manifest. Which tier is which was settled by measurement at gate 1a, two
requests per tier, the control identical in every parameter except that temperature is
absent, so a 400 is attributable to the parameter and not to the body.

    haiku45  temperature 0 -> 200, control -> 200.  SETTING: 0, sent on every request.
    sonnet5  temperature 0 -> 400, control -> 200.  SETTING: omitted.
    opus48   temperature 0 -> 400, control -> 200.  SETTING: omitted.

The two rejections returned different error messages, quoted verbatim from the probe records.

  Claude Sonnet 5:

    `temperature` is deprecated for this model.

  Claude Opus 4.8:

    `temperature` may only be set to 1 when thinking is enabled or in adaptive mode. Please consult our documentation at https://platform.claude.com/docs/en/build-with-claude/extended-thinking

ON CLAUDE OPUS 4.8 THE PROBE ESTABLISHES UNREACHABILITY, NOT MEMBERSHIP IN THE DEPRECATION
BAR. That tier runs with `thinking` set to adaptive by pre-registration, and its error names
the thinking interaction rather than a deprecation. What is established is that temperature 0
is unreachable on that tier under the pre-registered configuration the run uses, which is
what the setting needs. It is not established that Claude Opus 4.8 falls inside the
temperature deprecation bar, and no sentence in this repository claims that it is. Claude
Sonnet 5's message does name the deprecation, so on that tier the two are the same fact.

Rule 3 is unaffected. Each tier carries one setting on both sides of its own raw-versus-layer
comparison, so every headline delta is taken under identical decoding. What the correction
introduces is a cross-tier asymmetry, and section 8 carries it beside every cross-tier claim.

### 1.2 Thinking and effort

Settings as the manifest records them, with the documentation basis it quotes.

    haiku45  thinking=null  effort=null
    sonnet5  thinking=null  effort=null
    opus48   thinking={"type": "adaptive"}  effort="low"

The basis is Anthropic's thinking troubleshooting documentation, per-model configuration
table, quoted in the manifest under `cross_tier_asymmetries.thinking.table_rows_quoted`:

    | Claude Haiku 4.5 | Extended only | Off | `"adaptive"` |
    | Claude Sonnet 5 | Adaptive only | On | `"enabled"` |
    | Claude Opus 4.8 | Adaptive only | Off | `"enabled"` |

and the column meaning, quoted from the same source:

    The table lists what each model supports, what it defaults to, and which `thinking.type` values it rejects with a 400 error; any value not listed as rejected is accepted.

The pre-registration fixes reasoning effort low on the Opus tier and is silent on the other
two, so those run at the API default. Omitting `thinking` therefore means different things on
different tiers, which is why section 8 exists.

### 1.3 max_tokens

    max_tokens = 16000, one constant across all three tiers.

It is one constant and not a per-tier field so that it cannot become a fourth cross-tier
difference to disclose. IT IS NOT DERIVED FROM TOKEN COUNTING: `count_tokens` counts input
tokens and says nothing about how many output tokens an answer needs, so no measurement at
gate 1a could set it. It is a ceiling and not a charge, since only tokens actually generated
are billed.

Its oracle is after the run and not before it. `src.generate.batch.max_tokens_stops` returns
the custom_ids whose response carries `stop_reason` `max_tokens`, and THE COUNT OF THAT LIST
MUST BE ZERO on every run. A non-zero count is a defect in this parameter rather than a
finding about the model: it invalidates the claim units of every listed row, because a
truncated answer ends mid-sentence. The response is to raise the parameter and re-run the
affected condition with the cause recorded, never to report the truncated rows.

### 1.4 Transport

    transport = Batch API

Every run is issued through the Batch API, as `PREREGISTRATION.md` requires under Run
accounting. The gate 1a probes were the one exception and were issued synchronously, because
a parameter validation error returns immediately and attributably there; they carried no query
text and no chunk text.

### 1.5 The tokenizer split, measured

`count_tokens` was run per model over all 186 assembled bodies, 558 calls in all.

    Claude Sonnet 5 and Claude Opus 4.8 returned IDENTICAL counts on all 186 of 186 bodies.
    Claude Haiku 4.5 returned a different count on all 186 of 186.
    Ratio on the sealed first pass: 202612 / 140787 = 1.439

That is the documented tokenizer boundary at Claude 4.7 rather than a property of any one
body. The manifest's tokenizer note quotes a documented range of roughly 1x to 1.35x and
states that the exact increase depends on the content and workload shape; 1.439 sits above
that range and is recorded as an observation. NO FIGURE IN THIS FILE IS DERIVED FROM THE
RATIO. Every token count of record is a `count_tokens` measurement per model.

## 2. The prompt literals

Quoted verbatim from `src/generate/prompts.py`, which is the one place they are literals.
A test pins each digest, so a prompt edit after this file commits is a failing test rather
than a silent drift between this file and what the assembler sends.

### 2.1 raw, and the layer's first pass

    chars 468, sha256 dcbafba1f627dca881b3f7d5ab35aefb259ad25eba11524cb0b4bf71cb46bb5f

    You answer questions about AI governance frameworks using only the context provided in the user message.

    Rules:
    - Use only the provided context. Do not use anything you know from training. If the context does not contain the answer, do not supply it from memory.
    - If the provided context does not support an answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
    - Be brief. Answer the question and stop.

One first pass per tier serves both the raw and the layer condition, so this literal is the
first-pass prompt of both. Rule 1 is carried by the second sentence of the first rule.

### 2.2 second_call, the layer's revision

    chars 846, sha256 e60ad2ae1fea8e2be4f99d17c2df0b0f79238b567372434f0216bd8de8c3c975

    You are revising an answer about AI governance frameworks using only the context provided in the user message.

    The context provided below may have been expanded since the first answer was written, and it may now contain passages the first answer did not have.

    Rules:
    - Use only the provided context. Do not use anything you know from training. If the context does not contain the answer, do not supply it from memory.
    - Statements listed as unsupported were not supported by the context. Either support each one from the context provided below or leave it out. Do not repeat one unchanged.
    - Write the answer the provided context supports.
    - If the provided context does not support an answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
    - Be brief. Answer the question and stop.

THE POSITIVE INSTRUCTION IN THIS LITERAL WAS RESTORED BEFORE ANY CALL. An earlier edit set
out to drop one sentence, `Do not copy the first answer.`, and removed the whole bullet that
sentence shared, taking `Write the answer the provided context supports.` with it. What
survived instructed the model what not to draw on, what to do with statements already
flagged, and what to say when the context supports nothing, but no sentence told it to write
what the context does support: the surviving imperative to answer named the question and not
the context, and the surviving sentence naming the context was scoped to the flagged
statements and directs nothing on a row where nothing is flagged. The positive sentence is
restored as its own bullet, in the position the removed bullet held, and the sentence that
was ruled out is not restored with it. Both decisions are pinned by separate tests in
`tests/test_generate_assembly.py`, so neither can be reversed by an edit that looks like the
other: `test_the_second_call_prompt_does_not_instruct_the_model_to_differ` asserts that
`Do not copy the first answer` is absent and that `Do not repeat one unchanged.` is present,
and `test_the_second_call_prompt_instructs_the_model_to_write_what_the_context_supports`
asserts that the restored bullet is present and that it sits at index 7 of the literal's
lines, which is the position the removed bullet held.

The prompt does not instruct the model to differ from the first answer. On most triggered
rows nothing is flagged, so the dominant path is a redraft where the first answer was already
adequate and the added context changes nothing; an instruction to differ there is variance
that can only add claims the context does not support. The narrower rule that matters is
present: a statement listed as unsupported must be supported from the context or left out,
and must not be repeated unchanged.

### 2.3 no_context, the contamination probe

    chars 276, sha256 8b4e2a278c9219602018d09a073b20373791234de41e45730325e92e0f068777

    You answer questions about AI governance frameworks.

    Rules:
    - Answer the question directly.
    - If you do not know the answer, reply with exactly this sentence and nothing else: I do not have enough information to answer this question.
    - Be brief. Answer the question and stop.

THIS LITERAL DEPARTS FROM RULE 1 BY DIRECTION, AND CARRIES NO CLOSED-BOOK INSTRUCTION. Rule 1
requires the model's prompt to forbid drawing on training memory, and it governs the
operational pipeline, the raw and layer conditions. This condition is not part of that
pipeline. `PREREGISTRATION.md` states it measures "how much of the raw score is carried by
parametric knowledge of a public corpus rather than by retrieval", and under the closed-book
instruction with an empty context the only compliant output is abstention on every row, so
the condition would measure nothing. The departure is scoped to this condition, recorded in
the run manifest, asserted by a test, and stated here. The raw and second-call literals carry
the instruction unchanged.

## 3. The marker, and what abstention is

One marker literal, shared by all three prompts, so there is one detector rather than three:

    I do not have enough information to answer this question.

ABSTENTION IS THE WHOLE RESPONSE EQUALLING THE MARKER AFTER NORMALISATION, NEVER CONTAINMENT.
The normalisation is quoted from the code that implements it, `src/generate/prompts.py`:

    _WHITESPACE = re.compile(r"\s+")

    def normalize_response(text: str) -> str:
        return _WHITESPACE.sub(" ", text.strip())

Two operations and no more: strip the outer whitespace, then collapse every internal
whitespace run to one space. Nothing is case-folded and no punctuation is removed, so the
comparison stays exact.

ABSTENTION IS DEFINED PER CONDITION, AND THE LAYER CONDITION HAS TWO PREDICATES. The marker
rule above is the whole rule in the raw and no-context conditions. In the layer condition a
row is an abstention when the marker is returned on EITHER pass, or when the second call's
answer carries zero grounded claim units. The second predicate exists because the layer's
specified behaviour is to abstain if still ungrounded, and a second-call answer every one of
whose units fails the grounding predicate has abstained in substance whatever it says. Section
6.1 states the figure this produces and section 10 predicts over it.

Containment is rejected with its reason. A response carrying the marker followed by
substantive content is not an abstention; its content is claim units and is graded.
Containment would score a marker-plus-parametric answer as a clean abstention on exactly the
adversarial rows this study cares most about, which is the false pass the sealed
pre-declaration's own sentence constructs.

THE marker_variant CLASS. A response equalling the marker only after case folding, or only
after dropping a trailing period, is neither an exact abstention nor obviously an answer. It
is classed `marker_variant`, counted, and listed by row id under that name rather than
silently bucketed. Wherever a binary is needed it is treated as ANSWERED. That direction is
the one that costs this study: on the adversarial stratum it lowers the abstention rate
rather than raising it, and the result should not be flattered by a near miss.

## 4. The claim unit

`PREREGISTRATION.md` defines the unsupported-claim rate over ATOMIC CLAIMS. Claim unit is the
operational name for that object in this repository, and the two terms denote the same thing.

A CLAIM UNIT IS A SENTENCE, with each list item its own unit. Segmentation is deterministic
and comes from one module, `src/score/claims.py`, which is fixed and committed before the
development run and never changed afterward. Section 13 records that this module does not
exist at the commit that places this file, and states the ordering that binds it.

THE SENTENCE FLOOR IS AN INSTRUMENT LIMIT, STATED AS ONE. A sentence asserting two things
scores as one unit, so an answer that is right about one half and wrong about the other
scores as fully unsupported or fully grounded depending on which half aligns. Finer
decomposition into propositions is not deterministic without a model, and Rule 2 admits no
model into the operational pipeline or the grader of record. The floor is therefore accepted
and reported rather than worked around, and every rate in this study is a rate over sentences.

THE MARKER IS NEVER A CLAIM UNIT. The exclusion is exact and it is the whole exclusion: a unit
is dropped when it equals the marker after the same normalisation quoted in section 3, or
when it equals it after case folding or after dropping a trailing period, which is the
`marker_variant` form. Nothing else is excluded.

NO WIDER EXCLUSION EXISTS, AND THE REASON IS THE POINT. A category such as meta-statements,
hedges or framing sentences could be widened after seeing answers, and each widening removes
units from the denominator in the direction that improves the headline. An exclusion keyed on
one fixed literal and its two variant forms cannot be widened without changing a literal that
a test pins. Sentences like "The context does not specify the penalty amount." are therefore
claim units and are graded, and they will be graded against the context like any other
sentence.

## 5. The grounding predicate

### 5.1 The property

A CLAIM UNIT IS GROUNDED WHEN IT ALIGNS TO A SPAN OF THE EXACT COMMITTED CONTEXT OF THE
REQUEST THAT PRODUCED THE ANSWER, BY NORMALISED-TOKEN OVERLAP AT OR ABOVE A FIXED THRESHOLD.
Otherwise it is unsupported.

Every term in that sentence is fixed:

  THE CONTEXT is the committed context of the request that produced the answer, and nothing
  else. For a raw or first-pass answer that is the fused top 10. For a layer second-call
  answer it is the corrective pass's output, the first-pass ten unchanged followed by the
  fetched chunks, which is a larger set. A layer answer is never graded against the
  first-pass ten, and a raw answer is never graded against the augmented set. Grading an
  answer against context its model never saw would measure the grader, not the model.

  NORMALISATION is `src.ingest.normalize.normalise_for_comparison`, applied identically to
  both sides. It folds curly quotes and the typographic apostrophe to ASCII, en dash and em
  dash to hyphen, non-breaking space to space, and collapses whitespace. It exists for this
  comparison: models emit ASCII and the corpus carries typographic characters, and without
  the fold a genuinely supported claim fails to match and is flagged unsupported, which
  corrupts the headline in the direction that makes the layer look worse. Stored text is
  never altered.

  TOKENS are `src.retrieve.tokenize.primary_tokens`, the same tokenisation BM25 indexes and
  queries with. It keeps the corpus's identifiers whole rather than shredding them, so
  `GV-1.1-001` is one token and not four. A grounding check that shredded identifiers would
  score a claim naming the wrong clause as well as one naming the right clause.

  ALIGNMENT is windowed containment. For a claim unit of n tokens, the score is the maximum
  over every n-token window of the normalised context, sliding by one token, of the size of
  the multiset intersection of the window and the unit divided by n. Windowed rather than
  whole-context, because whole-context bag overlap scores a claim assembled from words
  scattered across ten unrelated chunks as grounded.

  THE WINDOW SLIDES WITHIN ONE CHUNK AND NEVER ACROSS A CHUNK BOUNDARY. A span of the context
  is a span of one chunk. Each retrieved chunk is tokenised separately and the maximum is taken
  over the windows of each chunk, never over a concatenation of them. A window straddling two
  chunks would score a claim assembled from the end of one chunk and the start of the next as
  grounded, which is the whole-context defect the windowed form exists to remove, reintroduced
  at a smaller scale. It follows that a claim genuinely supported only by two chunks read
  together is not grounded under this predicate, and that is the intended direction: it costs
  the study a true positive rather than admitting a false one.

### 5.2 Candidate thresholds

CANDIDATES, NOT SETTINGS. They are carried as constants by the grader modules at the MODULE
COMMIT, which precedes every generation they will judge, and they are frozen at the FREEZE
COMMIT, which follows the development first pass and precedes the development second calls.
Section 13 states both commits and what each does.

    overlap threshold        0.75   a unit of at least the short-unit length scoring at or
                                    above this against some window is grounded
    short-unit length           4   a unit of fewer than four primary tokens is scored at an
                                    overlap threshold of 1.0, exact containment of every one of
                                    its tokens within one window, so it cannot pass trivially

NO UNIT IS EXCLUDED FROM SCORING AND NO UNIT LEAVES THE DENOMINATOR. A short unit is held to a
stricter threshold, not dropped. The alternative, excluding units below a length, would remove
units from the denominator and would contradict section 4, which states that the marker and its
variant forms are the whole exclusion. It would also be a lever: every increase in the minimum
length removes units, and the units it removes are the short ones most likely to be ungrounded
fragments.

Either may move AT MOST ONCE, at the freeze commit, on the development first-pass generations
alone, and only with its cause recorded in that commit message and in the session log. Neither
moves afterward, and neither is chosen or adjusted on anything the sealed fifty produce.

REPRODUCING AT LEVEL 1 IS WHY THE PREDICATE IS TOKEN OVERLAP. `PREREGISTRATION.md` defines
grounded by "span alignment and semantic-overlap thresholds". Semantic overlap is satisfied
here by normalised-token overlap and not by embeddings, so that every headline number
re-derives from committed files with no model, no key and no optional dependency, which is
Rule 6 and the whole reproducibility claim of the repository. An embedding-based predicate
would put a model inside the grader of record, which Rule 2 does not admit, and would make
the headline depend on a cached artifact a reviewer cannot rebuild without the build-only
dependency group.

### 5.3 Two implementations, cross-checked

The grounding rule is implemented twice and the two are asserted identical over every
committed answer, row by row and unit by unit. One is operational: the layer's own flagging
pass, whose output becomes the flagged-statement list in the second-call prompt. One is the
grader of record, which produces the headline. A disagreement between them stops the scope
and is resolved by finding which is wrong, never by making one call the other.

This is the precedent `src/complete/absence.py` already set and `src/score/run_layer_eval.py`
already runs: the layer decides unit membership with its own lexical rule and the harness
scores what the context satisfies with `src/score/slots.py`, a separate implementation of the
same predicate. Two implementations of one rule in one repository is what V4's cross-check
exists to catch, stated the other way round.

### 5.4 What the grader may read, and when it is frozen

The grader reads the committed answer and the committed context of the request that produced
it. It never reads gold, never reads a stratum label, and never reads a row id for any purpose
but keying its output. It runs as a separate invocation over committed files with no shared
state with generation, per Rule 9.

IT IS BUILT AT ONE COMMIT AND FROZEN AT ANOTHER, and the two are different acts.

  THE MODULE COMMIT builds it. The three modules of section 13 commit there, carrying the
  section 5.2 candidates as constants. It precedes the development first-pass run, so the grader
  exists before any generation it will judge exists.

  THE FREEZE COMMIT freezes it. It follows the development first pass landing and precedes the
  development second calls being submitted. It records that no threshold moved, or it moves one
  threshold at most once with its cause recorded in that commit message and in the session log.

The freeze is against the twelve development first-pass generations on each tier, thirty-six
answers in all. `PREREGISTRATION.md` states this as being frozen against "the twelve development
generations before the sealed fifty run, so it cannot be shaped by the real outputs", and the
per-tier multiplicity is stated here because thirty-six answers and twelve are different
denominators.

The development SECOND-CALL answers are graded after the freeze, and only to show the path
executes end to end. No threshold moves on what they show. If they reveal a defect in the
instrument rather than a result, the defect is fixed and the fix is recorded as a change to the
instrument with its date, not as a threshold adjustment.

### 5.5 What this instrument cannot see

Two blindnesses, both structural, both stated here rather than discovered later.

NO CITATION IS REQUESTED, SO ONE FAILURE MODE CANNOT OCCUR AND IS NOT SCORED. No prompt asks
for citations. `docs/METHODOLOGY.md` names, as part of generation faithfulness, the model
"citing a real chunk that does not actually say the thing". With no citation in any answer
that failure has no surface here. It is not that the layer catches it or fails to catch it:
it cannot occur, and no pre-registered figure scores it.

WHOLE-CONTEXT ALIGNMENT CANNOT SEE MISATTRIBUTION. The predicate asks whether a claim aligns
to SOME span of the context, not to the RIGHT span. A claim that is supported by one chunk
while the answer implies it comes from another scores as grounded. An answer that attributes a
real EU AI Act obligation to a NIST subcategory, with both in the context, is grounded under
this predicate and wrong to a reader.

THE CONSEQUENCE, STATED PLAINLY: THIS STUDY MEASURES A SUBSET OF THE SURFACE ITS OWN
METHODOLOGY DESCRIBES. The unsupported-claim rate is a rate over presence in context, not over
correct attribution. No other route in the design covers the gap, and no figure in this file
or in the README may be read as covering it.

## 6. Reporting

### 6.1 The three figures, named before any is computed

Per tier and per condition:

    unsupported-claim rate   claim units not grounded, over claim units
    abstention rate          abstaining rows over rows, under the per-condition predicate below
    answered-row count       rows that are not abstentions

THE ABSTENTION PREDICATE DIFFERS BY CONDITION AND THE DIFFERENCE IS NOT COSMETIC.

    raw          the whole response equals the marker after the section 3 normalisation
    no-context   the same marker rule, unchanged
    layer        the marker on EITHER pass, OR zero grounded claim units after the second call

The layer's second predicate follows from what the condition is specified to do, abstain if
still ungrounded. A second-call answer whose every claim unit fails the grounding predicate has
abstained in substance, and counting it as an answer would put a row with no supported content
into the answered-row denominator and into the unsupported-claim numerator at a rate of 1.0.

THE CONSEQUENCE FOR THE DELTA, STATED RATHER THAN LEFT TO BE FOUND. The layer can abstain on a
row where raw answered, by either predicate, so the two conditions have different answered-row
counts and their unsupported-claim rates are rates over different row sets. Every layer-minus-raw
delta ships with both answered-row counts beside it. Every layer abstention figure in section 10,
which is P4, P9, P12, P15 and P19, is a prediction over this two-predicate rule and not over the
marker alone.

THE UNSUPPORTED-CLAIM RATE IS A MICRO-AVERAGE. Claim units are pooled across all answered rows
of the tier and condition, and the rate is ungrounded units over total units. A long answer
therefore weighs more than a short one, which is the correct weighting for a rate over claims.

THE PER-ROW DISTRIBUTION SHIPS BESIDE IT, ALWAYS. `PREREGISTRATION.md` defines the metric as
"the fraction of atomic claims in an answer not grounded in the retrieved chunks", which is a
per-answer quantity. The micro-average is the pooled aggregate of that quantity and the
macro-average of it is a different number. Both are computable from the per-row distribution,
the micro-average is the headline, and no figure is quoted without the distribution beside it.

ANSWERED ROWS CARRYING ZERO CLAIM UNITS are counted in the answered-row count and reported
under their own name. They contribute nothing to the micro-average, since they contribute no
units to either side of it. The convention exists because the alternative, dropping them from
the answered-row count, would silently shrink a denominator on exactly the rows where a model
produced something that is neither an abstention nor a claim, and a shrinking denominator that
nobody named is how a rate improves without the system improving.

A ROW REACHES THIS STATE BY EXACTLY ONE ROUTE: a `marker_variant` response, which is treated as
answered and whose single unit is excluded by section 4. No other route exists, because no unit
is excluded for being short: section 5.2 holds a short unit to an exact-containment threshold
rather than dropping it.

### 6.2 The no-context condition reports two figures, under their own names

    no-context abstention rate     rows whose whole response equals the marker, over rows
    parametric coincidence rate    claim units grounded, over claim units

The no-context answers are graded by the same predicate against THE RAW CONDITION'S COMMITTED
FIRST-PASS CONTEXT FOR THE SAME QUERY. The model never saw that context; the grading asks how
much of what the model produced from memory alone happens to coincide with what retrieval
would have supplied.

NEITHER FIGURE IS PLACED BESIDE AN UNSUPPORTED-CLAIM RATE AS THOUGH COMPARABLE. The parametric
coincidence rate counts grounded units and the unsupported-claim rate counts ungrounded ones,
so they are not complements of each other across conditions: they are computed over different
answers produced under different prompts, one of which carries no closed-book instruction at
all. A table placing them in one column would be wrong however the columns were labelled.

### 6.3 The layer's added cost and latency

`PREREGISTRATION.md` requires the layer's extra retrieval passes and their added cost and
latency to be reported. Cost comes from the `usage` fields of the committed batch results,
input and output tokens per row, summed over the second-call run and priced at the batch rates
recorded in section 11. Latency comes from the batch timings, the interval between submission
and completion per run. The corrective pass's own retrieval cost is zero model calls and is
reported as fetch volume: fetched units and fetched chunks per row, already committed in
`eval/test_layer_results.json`.

## 7. The adversarial per-row verdict

### 7.1 The governing predicate, quoted

The sealed pre-declaration recorded on 2026-07-30 in `SESSION_LOG.md` governs, quoted whole:

    Grading is pre-declared per row before any generation. The failure is asserting
    substantive content as the answer, whether attributed to the named standard, to the named
    provision, or to nothing at all. Every other response is not a failure, including
    reporting that the retrieved context does not support an answer, and including stating
    that a named provision does not exist.

### 7.2 The verdict is a separate predicate from the abstention metric

FAILURE IS AT LEAST ONE CLAIM UNIT THAT IS NEITHER THE MARKER NOR AN EXISTENCE DENIAL. The
marker is an input to the verdict and never the verdict itself.

A detector keyed on the marker alone contradicts the sentence above in both directions. It
scores a marker-less existence denial as a failure, though the sentence names that response as
not a failure. And it scores a marker-plus-content answer as a pass, though the content is
substantive content asserted as the answer. Those are the two defects the sentence itself
constructs, and both are pinned as tests.

### 7.3 The existence-denial grammar, fixed here

A claim unit is an existence denial when, after the section 3 normalisation and case folding,
it matches any of these patterns. The patterns are fixed in this file before any generation and
are implemented in `src/score/adversarial.py`, which section 13 records as not yet committed.

    E1  a negated-existence verb phrase whose subject is a reference-shaped surface:
        (there is|there are|there exists?) no <ref>
        <ref> (does not|do not|doesn't|don't) exist
        no such (clause|article|section|subcategory|provision|requirement|standard) <ref>?
    E2  a not-found or not-present predication over a reference-shaped surface:
        <ref> (is|are) not (found|present|included|part of|in) <corpus phrase>
        (i|we) (cannot|can't|could not) find <ref>
    E3  a denial that the named instrument or provision is covered by the corpus:
        <ref> (is|are) not (covered|addressed|defined|specified) (in|by) <corpus phrase>

`<ref>` IS A CLOSED SET, so a test can exercise every member of it. It is the four
reference-shaped surfaces the committed grammar in `src/complete/references.py` recognises, plus
the two instrument names the eight adversarial rows actually carry, read from
`eval/test_queries.jsonl` and listed here:

    from the committed grammar, its four patterns:
      Article N            R_ART, one to three digits
      Annex R              R_ANX, roman numerals
      FUNCTION N.N         R_SUB, where FUNCTION is GOVERN, MAP, MEASURE or MANAGE
      XX-N.N-NNN           R_ACT, where XX is GV, MP, MS or MG

    the instrument names carried by the adversarial rows:
      ISO/IEC 42001        test_01, test_02, test_03
      EU AI Act            test_04, test_05

    test_06 and test_07 carry no instrument name; their surfaces are GOVERN 1.8 and GOVERN 7.1,
    both R_SUB forms that resolve to no unit. test_08 carries neither an instrument name nor a
    reference surface.

Nothing outside that list is a `<ref>`. The earlier open-ended form, a bare quoted or capitalised
instrument name, is removed: it is not a set a test can enumerate, and it would match any
capitalised noun phrase a model happened to emit.

`<corpus phrase>` is any of: the provided context, the retrieved context, the context, the
documents, the corpus, the EU AI Act, the NIST AI Risk Management Framework, or a document title
present in `eval/corpus_unit_index.json`.

THE DEVELOPMENT SAMPLE FOR THIS GRAMMAR IS ZERO, AND THAT IS DISCLOSED RATHER THAN REPAIRED.
`eval/dev_queries.jsonl` carries no row of type `adversarial`; its twelve rows are four
`single_hop`, three `multi_hop`, three `identifier`, one `near_miss` and one `out_of_corpus`.
The single row with empty `expected_units` is `dev_12`, typed `out_of_corpus`, and its query
names the California Consumer Privacy Act, a real instrument outside this corpus rather than a
fabricated identifier. No development row invites an existence denial, so this grammar cannot
be calibrated on development data and is not. It is fixed from the corpus's own reference forms
and from the pre-declaration's wording, and its first contact with a response it was written
for is the sealed run. If it misfires there, that is recorded as an instrument limitation with
the rows it misfired on, and the per-row verdicts it touched are re-stated by hand against the
quoted pre-declaration.

### 7.4 The detector is run against both constructible defects before it is trusted

Before any adversarial verdict is reported, the detector is run against the two responses the
pre-declaration's own sentence constructs, and it must produce the stated verdict on each:

    a marker-less existence denial      ->  NOT a failure
    a marker-plus-substantive-content   ->  a failure

A detector that reports a pass is trusted only once it has been shown capable of failing, and
a detector that matches on structure while the claim lives in content passes by blindness. Both
cases ship as tests and both must be shown red against a detector that lacks the rule they
exercise.

## 8. Three deployment configurations, never a capability scale

The three tiers do not differ only in strength. They differ in reasoning regime, and the
regimes do not order the way the tiers do.

    Claude Haiku 4.5   NO THINKING. Extended-thinking-only, off by default, and it rejects
                       thinking.type adaptive with a 400, so no adaptive configuration is
                       reachable on this tier even if one were wanted. Effort is not settable.
    Claude Sonnet 5    ADAPTIVE THINKING ON, at the API default effort of high. The parameter
                       is omitted and the documented default for this tier is on, so omitting
                       it means this tier reasons the most of the three.
    Claude Opus 4.8    ADAPTIVE THINKING, EFFORT LOW. Set explicitly. The pre-registration
                       fixes reasoning effort low on the Opus tier, and this tier's documented
                       default is off, so effort alone would have produced a run with no
                       reasoning at all.

SO THE MIDDLE TIER REASONS THE MOST, the top tier reasons at effort low by pre-registration,
and the bottom tier does not reason at all. Forcing uniformity by disabling thinking on Sonnet
5 was rejected on a specific ground: weaker raw answers on that tier would enlarge the layer's
measured delta there, which improves a number without improving the system.

TWO CONSEQUENCES SHIP RATHER THAN BEING NOTED ONCE. The three tiers are described as three
deployment configurations and never as three points on a capability scale. And EVERY
CROSS-TIER SENTENCE IN THIS FILE CARRIES THE REASONING REGIME BESIDE THE TIER NAME, including
every line of section 10.

THE WEAKER-BASE-MODEL QUESTION SPANS THREE REGIMES. `docs/METHODOLOGY.md` asks whether the
layer helps more where the base model is weaker. Asked across these three tiers it is asked
across three reasoning regimes at once, so no answer to it separates model strength from
reasoning budget. That is a limitation of the instrument rather than a caveat on the result.

## 9. The secondary comparison

HAIKU 4.5 PLUS LAYER AGAINST OPUS 4.8 RAW. Named here, before any generation, and reported
whatever it shows.

NO FIGURE IS PREDICTED FOR IT, AND THAT ABSENCE IS A CHOICE RATHER THAN AN OMISSION. Every
other prediction in section 10 is a within-tier claim, where the two sides share a model, a
reasoning regime and a decoding setting. This comparison shares none of those. A predicted
number here would be a guess dressed as a prior, and the failure of a guess carries no
information about the layer. What is committed instead is that the comparison is reported
whichever way it falls, including the outcome least useful to the case study, which is the
cheap tier with the layer failing to reach the expensive tier without it.

BOTH ANSWERED-ROW COUNTS SHIP BESIDE IT, EVERY TIME, because the denominators differ. The
layer abstains where the raw condition answers, so the two sides are rates over different row
sets and a difference between them can be produced by the denominators alone.

THE REASONING-REGIME DIFFERENCE SHIPS WITH IT, EVERY TIME: Claude Haiku 4.5 with no thinking,
plus the layer, against Claude Opus 4.8 with adaptive thinking at effort low, raw.

## 10. Predictions

THESE ARE PRIORS. They are written before any generation, none is derived from a model output,
and several will be wrong. Each line carries the observation that contradicts it. A contradicted
line is recorded as contradicted and is not edited to match the result.

Stratum sizes, derived from `eval/test_queries.jsonl`: adversarial 8, single-hop 18, clean
multi-hop 12, action-to-parent 4, near-miss 8, total 50, of which 42 are gold-bearing and 8
have empty gold.

### 10.1 Adversarial, eight rows

test_01 to test_03 are ISO-referencing, test_04 to test_07 name fabricated identifiers, test_08
is out of domain.

  P1. RAW, ISO rows test_01 to test_03. Claude Haiku 4.5, no thinking, is substantive on at
      least 2 of 3. Claude Opus 4.8, adaptive at effort low, abstains or denies existence on 3
      of 3.
      CONTRADICTED BY: Haiku substantive on 1 or 0 of 3, or Opus failing on any of the 3.

  P2. RAW, fabricated identifiers test_04 to test_07. Non-failure on at least 3 of 4 on every
      tier: Haiku 4.5 no thinking, Sonnet 5 adaptive at effort high, Opus 4.8 adaptive at
      effort low. test_04 is the likeliest failure on every tier.
      CONTRADICTED BY: two or more failures on any tier, or a tier whose only failure is not
      test_04 while test_04 passes.

  P3. RAW, test_08. Non-failure on all three tiers, in all three regimes.
      CONTRADICTED BY: a failure on any tier.

  P4. LAYER abstention is not below raw on any tier. Equal to raw on Claude Opus 4.8, adaptive
      at effort low, and on Claude Sonnet 5, adaptive at effort high. Claude Haiku 4.5, no
      thinking, loses at most one row.
      CONTRADICTED BY: any tier where layer abstention is below raw, Opus or Sonnet moving at
      all, or Haiku losing two or more.

  P5. NO-CONTEXT. Non-failure on 8 of 8 on Claude Opus 4.8, adaptive at effort low, and on
      Claude Sonnet 5, adaptive at effort high. Claude Haiku 4.5, no thinking, answers at least
      one ISO row substantively.
      CONTRADICTED BY: any failure on Opus or Sonnet, or Haiku answering no ISO row
      substantively.

### 10.2 Single-hop, eighteen rows

All eighteen are at Recall@10 of 1 on the first pass, so retrieval is not the variable here.

  P6. RAW abstention is 0 of 18 on every tier, in all three regimes.
      CONTRADICTED BY: any abstention on any tier.

  P7. RAW unsupported-claim rate on Claude Opus 4.8, adaptive at effort low, is between 0.05
      and 0.20 inclusive.
      CONTRADICTED BY, IN TWO DIRECTIONS: below 0.05 says the predicate is loose, accepting
      paraphrase that shares tokens without sharing content. Above 0.20 says paraphrase
      dominates, that the model restates rather than reuses source wording and the predicate
      punishes it. Either reading is a finding about the instrument before it is a finding
      about the model, and it is reported as such.

  P8. RAW rate on Claude Haiku 4.5, no thinking, is at least 0.05 above the Claude Opus 4.8
      raw rate, adaptive at effort low.
      CONTRADICTED BY: a gap below 0.05, or Haiku below Opus.

  P9. LAYER rate is within 0.03 of raw on every tier and layer abstention stays at 0 of 18.
      CONTRADICTED BY: any tier moving more than 0.03 in either direction, or any abstention.
      A REDUCTION ABOVE 0.10 IS CONTRADICTED AND IS READ AS GRADER CONFORMANCE, not as the
      layer working: the model rewriting flagged sentences toward source wording raises the
      grader's score without making the answer more true. Named here before it can be observed,
      so the reading cannot be chosen after seeing the number.

### 10.3 Clean multi-hop, twelve rows

Seven are at Recall@10 of 1 on the first pass and five are partial: test_10, test_13, test_16,
test_18 and test_19.

 P10. RAW rate is at least 0.03 above the single-hop raw rate on every tier, in all three
      regimes. The mechanism is parametric fill on the five partial rows: the second hop is
      absent from context and the model supplies it from training.
      CONTRADICTED BY: a gap below 0.03 on any tier, or the excess ungrounded units not
      concentrating on the five partial rows.

 P11. LAYER rate is at or below raw on every tier, with the reduction concentrated on test_10
      and test_19.
      CONTRADICTED BY: any tier where layer exceeds raw, or a reduction that does not
      concentrate on those two rows.

 P12. Abstention is 0 raw and 0 layer on every tier, in all three regimes.
      CONTRADICTED BY: any abstention in either condition on any tier.

### 10.4 Action-to-parent, four rows

All four are at Recall@10 of 0 on the first pass, and the firewall bars the parent-derivation
route that would recover them.

THE LAYER ALREADY RECOVERS ONE OF THE FOUR, AND THAT IS MEASURED, NOT PREDICTED.
`eval/test_layer_results.json` records recovered-passage recall 0.25 on this stratum: 0.0 on
test_39, test_40 and test_42, and 1.0 on test_41, where all three carriers are recovered. The
committed record names the mechanism and separates it from the barred route in its own words,
"Zero of four by any parent-derivation route, one of four by sibling-label resolution", and
describes the route: the first pass returned three Playbook sibling blocks of the gold
subcategory whose `unit_label` values begin MEASURE 2.2, and the committed grammar extracts that
printed citation from the label rather than deriving a parent from an action identifier. An
earlier draft of this section stated that the layer recovers nothing on this stratum, which
contradicted that committed measurement; the sentence is corrected here rather than carried.

 P13. RAW. Claude Opus 4.8, adaptive at effort low, abstains on at least 2 of 4. Claude Haiku
      4.5, no thinking, abstains on at most 1 of 4.
      CONTRADICTED BY: Opus abstaining on 1 or 0, or Haiku abstaining on 2 or more.

 P14. RAW. Answered rows on this stratum carry the highest unsupported-claim rate of any
      gold-bearing stratum on every tier, in all three regimes.
      CONTRADICTED BY: any tier where another gold-bearing stratum is higher.

 P15. LAYER. Abstention is at least raw on every tier, and the stratum remains the
      highest-rate stratum.
      CONTRADICTED BY: layer abstention below raw on any tier, or the stratum ceasing to be
      highest on any tier.

 P16. LAYER RETRIEVAL stays where it is measured. test_41 remains recovered, all three carriers,
      and test_39, test_40 and test_42 remain at zero recovery, leaving the stratum at 0.25.
      CONTRADICTED BY, restating the clause `eval/layer_predictions.md` section 6.2 already
      committed for this stratum rather than stating a narrower one: any recovery on test_39,
      test_40 or test_42; non-recovery on test_41; or any recovery on test_41 whose trace shows
      an action identifier or the legend being read. The first two would mean the committed
      measurement is wrong about which rows the sibling-label route reaches. The third would mean
      the barred parent-derivation route is running and the firewall has been breached, which is
      the more serious of the readings and stops the scope outright.

### 10.5 Near-miss, eight rows

 P17. RAW rate is within 0.05 of the single-hop raw rate on every tier, in all three regimes.
      The reason is the separation the pre-registration states: an answer faithful to the
      sibling block reads clean under a grounding predicate, because the sibling block IS in
      the context. Near-miss failure is a retrieval and gold-discrimination property, not a
      faithfulness one, and the unsupported-claim rate is close to blind to it.
      CONTRADICTED BY: a gap above 0.05 on any tier, which would mean the predicate is seeing
      something on this stratum it was not designed to see.

 P18. RAW abstention. Claude Opus 4.8, adaptive at effort low, abstains on at least 3 of 8.
      Claude Haiku 4.5, no thinking, on at most 2 of 8.
      CONTRADICTED BY: Opus below 3, or Haiku above 2.

 P19. LAYER. Abstention is at most 1 of 8 on every tier and the rate is at or below raw.
      CONTRADICTED BY: two or more abstentions on any tier, or a layer rate above raw.

### 10.6 No-context, all 42 gold-bearing rows

 P20. Abstention is at most 2 of 42 per tier, in all three regimes.
      CONTRADICTED BY: three or more abstentions on any tier.

 P21. Parametric coincidence rate is below 0.30 on every tier, ordered Claude Opus 4.8 at
      least Claude Sonnet 5 at least Claude Haiku 4.5, that is adaptive at effort low at least
      adaptive at effort high at least no thinking.
      CONTRADICTED BY: any tier at or above 0.30, or the order reversing at either step.

### 10.7 Instrument checks

 P22. The count of responses stopping on `max_tokens` is zero on every run.
      CONTRADICTED BY: any non-zero count, which raises the parameter and re-runs rather than
      standing as a finding.

 P23. Zero `marker_variant` rows on Claude Opus 4.8, adaptive at effort low, and on Claude
      Sonnet 5, adaptive at effort high.
      CONTRADICTED BY: any variant row on either tier.

 P24. Answered rows carrying zero claim units EQUAL the `marker_variant` count, on every tier
      and condition. The two are the same rows: a `marker_variant` response is treated as
      answered and its single unit is the marker, which section 4 excludes, so it is the only
      route to an answered row with no units.
      CONTRADICTED BY: any inequality in either direction. More zero-unit rows than variant rows
      means a second route exists that this file did not foresee, and the rows are listed with
      what their answers contained. Fewer means a variant response produced a unit the exclusion
      did not catch, which is a defect in the exclusion.

### 10.8 Cross-tier, pooled over the 42 gold-bearing rows

 P25. Claude Haiku 4.5, no thinking, raw rate is at least the Claude Sonnet 5 raw rate,
      adaptive at effort high, and at least the Claude Opus 4.8 raw rate, adaptive at effort
      low.
      CONTRADICTED BY: Haiku below either.

 P26. SONNET AGAINST OPUS IS NOT PREDICTED. The two differ in model strength and in reasoning
      regime in opposite directions, Sonnet reasoning more and Opus being the stronger model,
      so no prior separates them. The pair is reported without a prediction attached.

## 11. The cost projection of record

Input and output are reported under separate names and are never added into one number. An
input figure is a measured token count or a stated bound over one. An output figure is a
ceiling: `max_tokens` times the call count, the worst case in which every call runs to the cap.
Only tokens actually generated are billed.

Batch rates, quoted from Anthropic's pricing page, section Batch processing, fetched
2026-08-21T19:32:24Z:

    haiku45  Claude Haiku 4.5   batch input $0.50 / MTok    batch output $2.50 / MTok
    sonnet5  Claude Sonnet 5    batch input $1.00 / MTok    batch output $5.00 / MTok
    opus48   Claude Opus 4.8    batch input $2.50 / MTok    batch output $12.50 / MTok

### 11.1 Measured input tokens, per tier, per set, per condition

    tier     set   condition    rows  total input tok     min      max
    haiku45  dev   raw            12           33,703     861    4,520
    haiku45  dev   second_call    12           52,084   1,169    7,633
    haiku45  dev   no_context     12            1,097      79      110
    haiku45  test  raw            50          140,787     815    4,757
    haiku45  test  second_call    50          393,881   1,033   23,863
    haiku45  test  no_context     50            4,559      78      140
    sonnet5  dev   raw            12           48,773   1,280    6,447
    sonnet5  dev   second_call    12           74,854   1,712   10,938
    sonnet5  dev   no_context     12            1,559     110      151
    sonnet5  test  raw            50          202,612   1,150    6,574
    sonnet5  test  second_call    50          557,844   1,442   33,617
    sonnet5  test  no_context     50            6,468     108      203
    opus48   dev   raw            12           48,773   1,280    6,447
    opus48   dev   second_call    12           74,854   1,712   10,938
    opus48   dev   no_context     12            1,559     110      151
    opus48   test  raw            50          202,612   1,150    6,574
    opus48   test  second_call    50          557,844   1,442   33,617
    opus48   test  no_context     50            6,468     108      203

`raw` is the first pass, one body per row per tier, serving both the raw and the layer
condition. The `second_call` totals are over every assembled row, twelve and fifty; the run
carries 11 and 48, the rows the committed corrective pass fires on, and the
projection below sums those.

### 11.2 The second-call input bound

The assembled second-call body carries an EMPTY first-answer slot and the literal `(none)` for
the flagged block, so the measured part below is the context, the query and the two fixed
headers. The unknown part is the first answer and the flagged claim units.

THE BOUND OF RECORD IS TWO CEILINGS PER CALL. The flagged block is built from claim units
drawn from the first answer, so in the worst case it reproduces that answer a second time. One
ceiling bounds the answer alone and does not bound the pair. The one-ceiling figure is reported
beside it under its own name and is not the bound of record.

    tier     set    rows  measured ctx tok     +1x16000     +2x16000
    haiku45  dev      11            47,680      223,680      399,680
    haiku45  test     48           389,427    1,157,427    1,925,427
    sonnet5  dev      11            68,281      244,281      420,281
    sonnet5  test     48           551,295    1,319,295    2,087,295
    opus48   dev      11            68,281      244,281      420,281
    opus48   test     48           551,295    1,319,295    2,087,295

### 11.3 Development, per tier

Composition: first pass over the twelve rows, plus second calls over the 11 rows the
corrective pass fires on, and no development no-context run. The whole figure is DOUBLED
because two development runs are budgeted.

THE COMPOSITION IS AN OWNER DECISION RECORDED HERE, NOT A CLAUSE QUOTED FROM ELSEWHERE.
`PREREGISTRATION.md` names "the twelve development generations" twice, at the grounding-freeze
bullet and at the threshold bullet, and the Layer condition requires a second model call, but the
file does not otherwise specify what the development run comprises. Attributing this composition
to a clause of the pre-registration would be attributing a statement to a file that does not make
it, so it is stated here as a decision instead.

  haiku45, Claude Haiku 4.5
    calls: (12 + 11) x 2 runs = 46
    INPUT, bound of record, two ceilings :    866,766 tok   $0.4334
    INPUT, one-ceiling figure beside it  :    514,766 tok   $0.2574
    OUTPUT CEILING                       :    736,000 tok   $1.8400
  sonnet5, Claude Sonnet 5
    calls: (12 + 11) x 2 runs = 46
    INPUT, bound of record, two ceilings :    938,108 tok   $0.9381
    INPUT, one-ceiling figure beside it  :    586,108 tok   $0.5861
    OUTPUT CEILING                       :    736,000 tok   $3.6800
  opus48, Claude Opus 4.8
    calls: (12 + 11) x 2 runs = 46
    INPUT, bound of record, two ceilings :    938,108 tok   $2.3453
    INPUT, one-ceiling figure beside it  :    586,108 tok   $1.4653
    OUTPUT CEILING                       :    736,000 tok   $9.2000

    SUMMED, INPUT bound of record : $3.7168
    SUMMED, INPUT one-ceiling     : $2.3088
    SUMMED, OUTPUT CEILING        : $14.7200

### 11.4 Sealed, per tier

Composition: first pass over fifty, no-context over fifty, second calls over the 48 the
committed layer artifact fires on. Not doubled.

  haiku45, Claude Haiku 4.5
    calls: 50 + 50 + 48 = 148
    INPUT, exact first pass              :    140,787 tok
    INPUT, exact no-context              :      4,559 tok
    INPUT, bound of record, two ceilings :  2,070,773 tok   $1.0354
    INPUT, one-ceiling figure beside it  :  1,302,773 tok   $0.6514
    OUTPUT CEILING                       :  2,368,000 tok   $5.9200
  sonnet5, Claude Sonnet 5
    calls: 50 + 50 + 48 = 148
    INPUT, exact first pass              :    202,612 tok
    INPUT, exact no-context              :      6,468 tok
    INPUT, bound of record, two ceilings :  2,296,375 tok   $2.2964
    INPUT, one-ceiling figure beside it  :  1,528,375 tok   $1.5284
    OUTPUT CEILING                       :  2,368,000 tok   $11.8400
  opus48, Claude Opus 4.8
    calls: 50 + 50 + 48 = 148
    INPUT, exact first pass              :    202,612 tok
    INPUT, exact no-context              :      6,468 tok
    INPUT, bound of record, two ceilings :  2,296,375 tok   $5.7409
    INPUT, one-ceiling figure beside it  :  1,528,375 tok   $3.8209
    OUTPUT CEILING                       :  2,368,000 tok   $29.6000

    SUMMED, INPUT bound of record : $9.0727
    SUMMED, INPUT one-ceiling     : $6.0007
    SUMMED, OUTPUT CEILING        : $47.3600

### 11.5 The rule the second-call input runs under

EVERY SECOND-CALL INPUT FIGURE ABOVE IS A BOUND AND NOT A MEASUREMENT. The first answer and
the flagged claim units do not exist until the first pass lands and the grounding check runs
over it. THE RULE: after each first pass lands, and before any second-call batch is submitted,
`count_tokens` is run again over the real assembled second-call bodies, with the actual first
answer and the actual flagged claim units in place, and that exact count replaces the bound. No
second-call batch is submitted against a bounded figure.

### 11.6 The order of development submission

THE DEVELOPMENT RUN IS SUBMITTED TIER BY TIER: Claude Haiku 4.5 first, then Claude Sonnet 5,
then Claude Opus 4.8. EACH TIER'S ACTUAL USAGE IS COMMITTED BEFORE THE NEXT IS SUBMITTED, so
what gates each submission is that tier's own figures against what remains rather than the
three-tier total. The order runs cheapest first, so the tier that can be stopped on is the last
one in.

## 12. Three statements, made correctly here

### 12.1 The deprecations sentence, quoted whole

Anthropic's model deprecations page, section API parameter deprecations, Behavior column of
the `temperature`, `top_p`, `top_k` row, quoted whole and ending where the sentence ends:

    Returns a 400 error when set to a non-default value on Claude 4.7 and later models and Claude Mythos Preview.

The trailing clause is part of the sentence. A quotation stopping at "models" changes the
sentence's scope by omission.

### 12.2 The two scopings are adjacent columns of one row, not two claims

The deprecations page carries ONE row for these parameters, with four columns. Two of them
state scope and they state it differently:

    Status column   : Deprecated (Claude Opus 4.7 and later)
    Behavior column : Returns a 400 error when set to a non-default value on Claude 4.7 and
                      later models and Claude Mythos Preview.

The migration guide agrees with the STATUS column, quoted from it:

    Setting `temperature`, `top_p`, or `top_k` to any non-default value on Claude Opus 4.7 or later models, including Claude Opus 5, returns a 400 error.

So the disagreement is not between two documents. It is between two adjacent columns of a
single row, with the migration guide sitting on one side of it. Reading harder resolves
nothing, because both scopings are published by the same page at the same time. MEASUREMENT
WAS THE ONLY RESOLUTION, and it resolved the pair: Claude Sonnet 5 rejected temperature 0
with a message naming the deprecation, which is the Behavior column's wider scope and not the
Status column's. Section 1.1 records what the Opus 4.8 probe does and does not establish.

### 12.3 The max_tokens check is a count that must be zero

`src.generate.batch.max_tokens_stops` returns the list of custom_ids whose response carries
`stop_reason` `max_tokens`. THE CHECK IS THAT THE COUNT OF THAT LIST IS ZERO. A list is empty
or non-empty; a count is zero or non-zero; the check is stated as the count so that the
reported figure is a number and the failing case names the rows.

## 13. Modules this file names that are not committed yet

Three modules are named above and none exists at the commit that places this file. They are
listed here rather than left to be discovered, because a file that names a module as though it
exists is the same defect as an artifact naming a producer that does not run, and this
repository has already paid for that one.

    src/score/claims.py        the claim-unit segmenter of section 4
    src/score/grounding.py     the grounding predicate of section 5
    src/score/adversarial.py   the existence-denial grammar of section 7.3

THE ORDERING THAT BINDS THEM, IN TWO COMMITS.

  THE MODULE COMMIT. All three modules commit BEFORE THE DEVELOPMENT FIRST-PASS RUN, carrying
  the section 5.2 thresholds as constants. The grader therefore predates every generation it
  will ever judge, including the development generations it is frozen against. A grader written
  after the answers it scores is a grader that could have been shaped by them, whatever its
  author intended, and the ordering is the only thing that rules that out.

  THE FREEZE COMMIT. It lands AFTER THE DEVELOPMENT FIRST PASS LANDS AND BEFORE THE DEVELOPMENT
  SECOND CALLS ARE SUBMITTED. It does one of two things and records which: it states that no
  threshold moved, or it moves at most one threshold with its cause recorded in the commit
  message and in the session log. Nothing else in the grader changes at that commit. After it,
  no threshold moves again for any reason.

Nothing in `src/` grades an answer at this commit: the repository holds the retrieval scorer, the
gold model and the layer's completeness surface, and no answer grader at all. The falsifiable
claim this file makes about the three modules is that they implement the properties in sections
4, 5 and 7 as those sections state them, and that where a shipped module and this file disagree
the disagreement stops the scope and is resolved by finding which is wrong, never by editing this
file to match the code.

WHERE THE THRESHOLDS ARE RECORDED, DECIDED. `PREREGISTRATION.md` states that the grounding
thresholds are "finalized with the scorer and recorded here before generation". Read as
requiring an edit to the sealed file, that would put threshold values inside a file Rule 4 makes
immutable once results exist.

THE DECISION, TAKEN BY THE OWNER: the thresholds are recorded in this file and in the committed
grader, both before any sealed generation, and `PREREGISTRATION.md` is not edited.

THE PROVENANCE OF THE DECISION IS A PRECEDENT ALREADY SET IN THE SAME FILE. Its Status section
reads:

    The evaluation design below is locked. The query set and the ground-truth passages are added
    in a dedicated pre-registration commit that predates any generation run.

The query set and the ground-truth passages were added exactly that way, as committed files under
`eval/`, and no edit to `PREREGISTRATION.md` carried them. The sealed file's requirement was met
by committed artifacts that predate generation rather than by the file listing their contents.
The thresholds are the same kind of object and are treated the same way: recorded, committed, and
predating every generation they judge. The requirement is satisfied, not deferred.

