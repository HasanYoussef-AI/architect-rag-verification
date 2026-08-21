"""The run manifest, component H1 part three.

On the data/retrieval/retrieval_manifest.json pattern: every generation parameter and the
reason behind it in a committed artifact, so a reviewer checks the run mechanically rather
than reading prose about it. Numbers are measured, not asserted; where a value is not yet
measured it carries PENDING and names the gate that fixes it, rather than carrying a guess
that would later be indistinguishable from a measurement.

THE PER-TIER DIFFERENCES ARE THE POINT OF THIS FILE, NOT A FOOTNOTE. Two parameters differ
across the three pre-registered tiers for reasons outside this repository's control, and
both are disclosed here and beside every cross-tier sentence.

  Temperature. PREREGISTRATION.md was corrected under Rule 4 to temperature 0 where the API
  accepts it and the parameter omitted where it rejects it. Anthropic's model deprecations
  page states that setting temperature to a non-default value on Claude 4.7 and later models
  returns a 400 error. Which tiers reject it is measured at gate 1a and recorded, not
  inferred.

  Thinking. The pre-registration fixes reasoning effort low on the Opus tier and is silent
  on the other two, so those run at the API default. The documented defaults are not
  uniform and are not monotonic in tier strength, which is the single most consequential
  fact in this file. Per the per-model configuration table in Anthropic's thinking
  troubleshooting documentation, quoted in THINKING_DOCUMENTATION below: Claude Sonnet 5 is
  adaptive only with thinking on by default; Claude Opus 4.8 is adaptive only with thinking
  off by default; Claude Haiku 4.5 is extended only, off by default, and rejects
  thinking.type adaptive with a 400.

  So the middle tier reasons the most, at the default effort of high; the top tier reasons
  at effort low by pre-registration; and the bottom tier does not reason at all and cannot
  be made to reason adaptively. Any sentence ordering the tiers by capability must not be
  read as ordering them by reasoning budget, and PREREGISTRATION.md's cross-tier question,
  whether the layer helps more where the base model is weaker, is asked across three
  reasoning regimes rather than one.

MAX_TOKENS IS NOT DERIVED FROM count_tokens. That endpoint counts input tokens and says
nothing about how many output tokens an answer needs. max_tokens is a pre-registered
constant chosen for headroom, and the check that it was large enough is a measurement after
the run: the count of responses with stop_reason max_tokens, which must be zero. A non-zero
count is a defect in this parameter and not a finding about the model. Thinking tokens count
toward max_tokens, per the same documentation, so the tier that reasons most needs the most
headroom.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

# Sentinel for a value that gate 1a fixes by measurement. Distinct from None, which is a
# real setting meaning "omit this parameter".
PENDING = "PENDING_GATE_1A"

# ONE CONSTANT ACROSS ALL THREE TIERS, deliberately not a per-tier field, so that it cannot
# become a fourth cross-tier difference to disclose. It is fixed here rather than at gate 1a
# because count_tokens counts input tokens and says nothing about how many output tokens an
# answer needs, so no measurement at that gate could set it.
MAX_TOKENS = 16000

MAX_TOKENS_REASONING = (
    "16000, one value on every tier. Three things set it. The prompts instruct the model to "
    "be brief and answer the question, so the text half of a response is expected in the "
    "low hundreds of tokens and 16000 covers that many times over. Thinking tokens count "
    "toward max_tokens, per the documented interaction quoted below, and the tier that "
    "reasons most, Sonnet 5 at the API default of adaptive thinking at effort high, needs "
    "the headroom the other two do not; a per-tier value sized to each tier's reasoning "
    "would have made the parameter a fourth asymmetry, so the largest requirement sets the "
    "single constant. It is a ceiling and not a charge: only tokens actually generated are "
    "billed, so headroom costs nothing. The oracle is after the run and not before it. "
    "src/generate/batch.py's max_tokens_stops must return empty. A non-empty list on the "
    "development split raises the parameter and re-runs D1a with the cause recorded, which "
    "is a defect in an instrument rather than a threshold judging its own observations."
)

# Quoted verbatim from Anthropic's thinking troubleshooting documentation, the per-model
# configuration table, so the manifest's claims about defaults sit beside their source.
THINKING_DOCUMENTATION = {
    "source": (
        "https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting"
        "#configurations-each-model-rejects"
    ),
    "table_rows_quoted": {
        "claude-opus-4-8": "| Claude Opus 4.8 | Adaptive only | Off | `\"enabled\"` |",
        "claude-sonnet-5": "| Claude Sonnet 5 | Adaptive only | On | `\"enabled\"` |",
        "claude-haiku-4-5": "| Claude Haiku 4.5 | Extended only | Off | `\"adaptive\"` |",
    },
    "column_meaning_quoted": (
        "The table lists what each model supports, what it defaults to, and which "
        "`thinking.type` values it rejects with a 400 error; any value not listed as "
        "rejected is accepted."
    ),
    "effort_scope_quoted": (
        "On Claude Opus 4.5, the one extended-thinking-only model that supports effort, "
        "effort composes with the budget"
    ),
    "effort_reading": (
        "Claude Haiku 4.5 is extended-thinking-only and is not Claude Opus 4.5, so effort "
        "is not settable on that tier. Confirmed at gate 1a rather than relied on here."
    ),
    "max_tokens_interaction_quoted": (
        "thinking tokens count toward `max_tokens`, so a long thinking pass can consume "
        "the budget before the text response completes"
    ),
}

TEMPERATURE_DOCUMENTATION = {
    "deprecations_page": (
        "https://platform.claude.com/docs/en/about-claude/model-deprecations"
        "#api-parameter-deprecations"
    ),
    "deprecations_quoted": (
        "Returns a 400 error when set to a non-default value on Claude 4.7 and later "
        "models and Claude Mythos Preview."
    ),
    "migration_guide": "https://platform.claude.com/docs/en/about-claude/models/migration-guide",
    "migration_quoted": (
        "Setting `temperature`, `top_p`, or `top_k` to any non-default value on Claude "
        "Opus 4.7 or later models, including Claude Opus 5, returns a 400 error."
    ),
    "scope_disagreement": (
        "The deprecations page says Claude 4.7 and later; the migration guide says Claude "
        "Opus 4.7 or later. The two differ on whether Claude Sonnet 5 is inside the bar, "
        "so the question is settled by measurement at gate 1a and not by reading."
    ),
}

TOKENIZER_DOCUMENTATION = {
    "source": "https://platform.claude.com/docs/en/about-claude/models/migration-guide",
    "quoted": (
        "Claude Opus 4.7 introduced a new tokenizer, which later Opus models, including "
        "Claude Opus 5, also use. It contributes to improved performance on a wide range "
        "of tasks, and it may use roughly 1x to 1.35x as many tokens when processing text "
        "compared to models before Claude Opus 4.7 (up to ~35% more, varying by content)."
    ),
    "use": (
        "Recorded for provenance only. No figure in this repository is derived from it. "
        "Every token count of record comes from count_tokens per model at gate 1a."
    ),
}


@dataclass(frozen=True)
class TierConfig:
    """One tier's generation parameters.

    `temperature` None means omit the parameter, which is the correct setting on a tier
    that rejects a non-default value. PENDING means gate 1a has not measured it yet.
    """

    key: str
    model: str
    temperature: Any = PENDING
    thinking: dict | None = None
    effort: str | None = None
    thinking_rationale: str = ""
    effort_rationale: str = ""

    def assert_resolved(self) -> None:
        if self.temperature == PENDING:
            raise ValueError(
                f"tier {self.key}: temperature not measured yet; "
                "gate 1a fixes it before any request body is built"
            )

    def to_record(self) -> dict:
        return {
            "model": self.model,
            "temperature": {
                "pre_registered": 0,
                "setting": self.temperature,
                "meaning": (
                    "PENDING_GATE_1A: not yet measured. null: parameter omitted because "
                    "the tier rejects a non-default value. 0: accepted and sent."
                ),
            },
            "thinking": {"setting": self.thinking, "rationale": self.thinking_rationale},
            "effort": {"setting": self.effort, "rationale": self.effort_rationale},
        }


# The three pre-registered tiers. Model strings are the API model names on Anthropic's
# model deprecations page; the Haiku entry is dated there and the dated form is pinned.
TIERS: dict[str, TierConfig] = {
    "haiku45": TierConfig(
        key="haiku45",
        model="claude-haiku-4-5-20251001",
        thinking=None,
        effort=None,
        thinking_rationale=(
            "Parameter omitted. The pre-registration is silent on this tier, so it runs at "
            "the API default, which the per-model table records as Off. This tier is "
            "extended-thinking-only and rejects thinking.type adaptive with a 400, so no "
            "adaptive configuration is reachable here even if one were wanted."
        ),
        effort_rationale=(
            "Parameter omitted. effort is not settable on an extended-thinking-only tier "
            "other than Claude Opus 4.5. Confirmed at gate 1a."
        ),
    ),
    "sonnet5": TierConfig(
        key="sonnet5",
        model="claude-sonnet-5",
        thinking=None,
        effort=None,
        thinking_rationale=(
            "Parameter omitted. The pre-registration is silent on this tier, so it runs at "
            "the API default, which the per-model table records as On. Omitting therefore "
            "means adaptive thinking is active here, at the default effort of high."
        ),
        effort_rationale=(
            "Parameter omitted, which the documentation states is identical to sending the "
            "default: effort high matches the API default and omitting it produces "
            "identical behaviour."
        ),
    ),
    "opus48": TierConfig(
        key="opus48",
        model="claude-opus-4-8",
        thinking={"type": "adaptive"},
        effort="low",
        thinking_rationale=(
            "Set explicitly. PREREGISTRATION.md fixes reasoning effort low on the Opus "
            "tier, and the per-model table records this tier's default as Off, so effort "
            "alone would produce a run with no reasoning at all. Adaptive is set so that "
            "the pre-registered setting describes something. Thinking display defaults to "
            "omitted on this tier, so no reasoning text enters the answer body."
        ),
        effort_rationale="Pre-registered: reasoning effort low on the Opus tier.",
    ),
}


def prompt_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class RunManifest:
    """The committed record of how a generation run was parameterised."""

    tiers: dict[str, TierConfig] = field(default_factory=lambda: dict(TIERS))
    probe_records: list[dict] = field(default_factory=list)
    content_digests: dict[str, str] = field(default_factory=dict)
    body_digests: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        from src.generate.prompts import MARKER, PROMPTS

        return {
            "description": (
                "Every generation parameter and decision, with its reason and its source. "
                "Nothing here is tuned to any result. Where a value is not yet measured it "
                "carries PENDING_GATE_1A and names the gate that fixes it."
            ),
            "produced_by": "python -m src.generate.manifest",
            "transport": "Batch API",
            "run_accounting": {
                "reported_conditions": 9,
                "runs": 9,
                "composition": (
                    "three first-pass runs, one per tier, each serving both raw and layer; "
                    "three layer second-call runs, one per tier; three no-context runs, "
                    "one per tier"
                ),
                "source": "PREREGISTRATION.md, Conditions, Run accounting bullet",
            },
            "marker_phrase": MARKER,
            "prompts": {
                name: {"sha256": prompt_digest(text), "chars": len(text)}
                for name, text in PROMPTS.items()
            },
            "no_context_departure": (
                "The no-context prompt carries no closed-book instruction. CLAUDE.md Rule 1 "
                "governs the operational pipeline; this condition is a contamination probe, "
                "and under the closed-book instruction with an empty context the only "
                "compliant output is abstention on every row, which would measure nothing."
            ),
            "cross_tier_asymmetries": {
                "temperature": TEMPERATURE_DOCUMENTATION,
                "thinking": THINKING_DOCUMENTATION,
                "statement": (
                    "Two generation parameters differ across the three tiers for reasons "
                    "outside this repository's control. Rule 3 is unaffected, since each "
                    "tier carries one setting on both sides of its own raw-versus-layer "
                    "comparison. Every cross-tier sentence carries this asymmetry beside it."
                ),
            },
            "tokenizer": TOKENIZER_DOCUMENTATION,
            "max_tokens": {
                "value": MAX_TOKENS,
                "scope": "one constant across all three tiers, not a per-tier setting",
                "reasoning": MAX_TOKENS_REASONING,
            },
            "abstention_detection": {
                "marker": MARKER,
                "rule": (
                    "Abstention is the whole response equalling the marker after "
                    "normalisation, never the marker appearing inside a longer response. A "
                    "response carrying the marker followed by substantive content is not an "
                    "abstention; its content is claim units and is graded."
                ),
                "normalisation": (
                    "Strip the outer whitespace, then collapse every internal whitespace "
                    "run to one space. No case folding and no punctuation removal."
                ),
                "variant_class": (
                    "A response equalling the marker only after case folding or after "
                    "dropping a trailing period is classed marker_variant, counted and "
                    "listed, and treated as answered wherever a binary is needed. That "
                    "direction lowers the abstention rate rather than raising it."
                ),
            },
            "tiers": {k: v.to_record() for k, v in self.tiers.items()},
            "probe_records": self.probe_records,
            "content_digests": self.content_digests,
            "body_digests": self.body_digests,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=1, sort_keys=False) + "\n"
