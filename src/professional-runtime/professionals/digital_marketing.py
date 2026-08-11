# Implements: WC058-07 DMA-owned Professional Evaluation Adapter
# constitutional_basis: C-036, C-041, C-048, C-049, C-050, C-055, C-056, C-057
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from evaluation_workflow import (
    AdapterAnswerProposal,
    TrialDemonstration,
    TrialDemonstrationRequest,
)


@dataclass(frozen=True)
class DemonstrationRecipe:
    artifact_type: str
    capability_ids: tuple[str, ...]
    sections: tuple[str, ...]
    context_gate: str | None = None
    non_applicable_reason: str | None = None
    activation_condition: str | None = None


DMA_TRIAL_CAPABILITIES: Mapping[str, str] = {
    "local-inference": "LOCAL_INFERENCE",
    "deterministic-analysis": "DETERMINISTIC_TOOL",
    "public-free-research": "PUBLIC_FREE_SOURCE",
    "approved-template": "APPROVED_TEMPLATE",
    "synthetic-recipient": "SYNTHETIC_FIXTURE",
    "simulated-campaign": "SYNTHETIC_FIXTURE",
    "pregenerated-asset": "PREGENERATED_ASSET",
    "customer-approved-asset": "CUSTOMER_APPROVED_ASSET",
}


DMA_RECIPES: Mapping[str, DemonstrationRecipe] = {
    "CUSTOMER_PROFILING": DemonstrationRecipe(
        "customer-profile", ("approved-template", "local-inference"),
        ("confirmed_context", "open_questions", "assumptions"),
    ),
    "MARKET_RESEARCH": DemonstrationRecipe(
        "market-maturity-brief", ("public-free-research", "deterministic-analysis"),
        ("public_observations", "maturity_score", "limitations"),
    ),
    "CONTENT_STRATEGY": DemonstrationRecipe(
        "content-calendar", ("local-inference", "approved-template"),
        ("campaign_theme", "channel_plan", "approval_points"),
    ),
    "INSTAGRAM": DemonstrationRecipe(
        "simulated-instagram-post", ("local-inference", "pregenerated-asset"),
        ("caption", "asset_reference", "simulated_preview"),
    ),
    "FACEBOOK": DemonstrationRecipe(
        "simulated-facebook-post", ("local-inference", "customer-approved-asset"),
        ("copy", "asset_reference", "simulated_preview"),
    ),
    "GOOGLE_BUSINESS_PROFILE": DemonstrationRecipe(
        "gbp-optimisation-draft", ("public-free-research", "approved-template"),
        ("profile_gaps", "draft_update", "customer_decisions"),
    ),
    "WHATSAPP_BUSINESS": DemonstrationRecipe(
        "synthetic-whatsapp-flow", ("approved-template", "synthetic-recipient"),
        ("entry_message", "synthetic_conversation", "opt_in_boundary"),
    ),
    "VIDEO_VISUAL_CONTENT": DemonstrationRecipe(
        "storyboard", ("local-inference", "pregenerated-asset"),
        ("shot_list", "script", "asset_references"),
    ),
    "PERFORMANCE_ANALYTICS": DemonstrationRecipe(
        "synthetic-performance-report", ("deterministic-analysis", "simulated-campaign"),
        ("synthetic_metrics", "calculation", "interpretation"),
    ),
    "LOCAL_SEO": DemonstrationRecipe(
        "local-seo-audit", ("public-free-research", "deterministic-analysis"),
        ("observations", "keyword_map", "recommended_changes"),
    ),
    "PAID_ADVERTISING": DemonstrationRecipe(
        "simulated-paid-campaign", ("simulated-campaign", "approved-template"),
        ("campaign_structure", "synthetic_budget", "no_spend_confirmation"),
    ),
    "EMAIL_MARKETING": DemonstrationRecipe(
        "synthetic-email-sequence", ("approved-template", "synthetic-recipient"),
        ("subject_variants", "message_sequence", "synthetic_delivery"),
    ),
    "CUSTOMER_LIFECYCLE": DemonstrationRecipe(
        "lifecycle-map", ("approved-template", "local-inference"),
        ("stages", "signals", "consent_boundaries"),
    ),
    "CONVERSION_OPTIMISATION": DemonstrationRecipe(
        "conversion-hypothesis", ("deterministic-analysis", "approved-template"),
        ("funnel_observation", "hypothesis", "measurement_plan"),
    ),
    "COMPETITIVE_INTELLIGENCE": DemonstrationRecipe(
        "competitive-public-brief", ("public-free-research", "local-inference"),
        ("public_observations", "inferences", "limitations"),
    ),
    "AGENCY_OPERATIONS": DemonstrationRecipe(
        "agency-workspace-plan", ("approved-template", "deterministic-analysis"),
        ("client_partitioning", "approval_routing", "reporting_model"),
        context_gate="agency_mode",
        non_applicable_reason="The confirmed business context does not identify an agency or reseller.",
        activation_condition="Applicable when the customer confirms agency or reseller operations.",
    ),
    "MULTI_LOCATION_MANAGEMENT": DemonstrationRecipe(
        "multi-location-plan", ("approved-template", "deterministic-analysis"),
        ("location_matrix", "shared_standards", "local_variations"),
        context_gate="multi_location",
        non_applicable_reason="The confirmed business context contains only one operating location.",
        activation_condition="Applicable when the customer confirms more than one operating location.",
    ),
    "CRISIS_COMMUNICATIONS": DemonstrationRecipe(
        "simulated-crisis-response", ("approved-template", "synthetic-recipient"),
        ("scenario", "holding_statement", "approval_escalation"),
    ),
    "QUARTERLY_STRATEGY_REVIEW": DemonstrationRecipe(
        "synthetic-strategy-review", ("simulated-campaign", "deterministic-analysis"),
        ("synthetic_outcomes", "lessons", "next_quarter_options"),
    ),
}


class DigitalMarketingEvaluationAdapter:
    async def describe_suitability(
        self,
        outcome: str,
        confirmed_context: Mapping[str, str],
    ) -> Mapping[str, object]:
        return {
            "outcome": outcome,
            "fit": "Digital marketing planning and simulated demonstrations for lawful local-service outcomes.",
            "confirmed_context_keys": tuple(sorted(confirmed_context)),
            "limitations": ("Trial results do not guarantee acquisition, revenue, ranking, or campaign outcomes.",),
        }

    async def answer_interview(
        self,
        question: str,
        evidence_context: tuple[str, ...],
    ) -> tuple[AdapterAnswerProposal, ...]:
        return (AdapterAnswerProposal(
            proposed_tag="LIMITATION",
            content="This adapter answers only from validated evidence supplied by the evaluation runtime.",
        ),)

    async def demonstrate(self, request: TrialDemonstrationRequest) -> TrialDemonstration:
        try:
            recipe = DMA_RECIPES[request.skill_id]
        except KeyError as exc:
            raise ValueError(f"Unknown DMA skill: {request.skill_id}") from exc

        if recipe.context_gate and request.context.get(recipe.context_gate, "false").lower() != "true":
            return TrialDemonstration(
                skill_id=request.skill_id,
                applicable=False,
                artifact_type=None,
                artifact=None,
                capability_ids=(),
                reason=recipe.non_applicable_reason,
                activation_condition=recipe.activation_condition,
            )

        permitted = {capability.capability_id for capability in request.capabilities}
        selected = tuple(item for item in recipe.capability_ids if item in permitted)
        if selected != recipe.capability_ids:
            raise ValueError(f"Required trial capability unavailable for {request.skill_id}")
        artifact = {
            "mode": "SIMULATION_ONLY",
            "goal": request.goal,
            "sections": recipe.sections,
            "context_keys": tuple(sorted(request.context)),
            "disclaimer": "No publishing, spend, credential use, third-party messaging, or provider mutation occurred.",
        }
        return TrialDemonstration(
            skill_id=request.skill_id,
            applicable=True,
            artifact_type=recipe.artifact_type,
            artifact=artifact,
            capability_ids=selected,
        )

    async def plan_trial(
        self,
        days: int,
        applicable_skills: tuple[str, ...],
    ) -> tuple[Mapping[str, object], ...]:
        if days != 14:
            raise ValueError("DMA evaluation trials span exactly 14 calendar days")
        unknown = set(applicable_skills) - set(DMA_RECIPES)
        if unknown:
            raise ValueError(f"Unknown DMA skills: {sorted(unknown)}")
        return tuple(
            {
                "day": 1 + (index * days // max(len(applicable_skills), 1)),
                "skill_id": skill_id,
                "mode": "SIMULATION_ONLY",
            }
            for index, skill_id in enumerate(applicable_skills)
        )

    async def propose_configuration(
        self,
        goals: tuple[str, ...],
        measures: tuple[str, ...],
        skills: tuple[str, ...],
    ) -> Mapping[str, object]:
        unknown = set(skills) - set(DMA_RECIPES)
        if unknown:
            raise ValueError(f"Unknown DMA skills: {sorted(unknown)}")
        return {
            "goals": goals,
            "measures": measures,
            "skills": skills,
            "status": "PROPOSED",
            "requires_item_level_customer_decision": True,
        }