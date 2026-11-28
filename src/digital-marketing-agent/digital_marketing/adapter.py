"""Digital Marketing domain behavior behind the common runtime contract."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §4, §20
# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R009
# Constitutional basis: C-035, C-059, C-071, C-079

from __future__ import annotations

import os
from typing import Any

from runtime_contract import AdapterContractError, AdapterDescriptorV1, AdapterInvocationEnvelopeV1, ReferenceAdapter

from .operation import (
    build_digest,
    build_plan_level,
    create_platform_drafts,
    enrich_public_footprint,
    induction_turn,
    propose_goals,
    research_calendar_events,
)
from .skills import SkillInputDenied, create_content_strategy, profile_customer, research_market

# WC-174: each mode's work is a skill invocation that returns typed proposals. No new port operation is added: the
# payload names the operation inside a skill the descriptor already declares.
OPERATIONS = {
    ("CONTENT_STRATEGY_AND_CALENDAR", "RESEARCH_CALENDAR_EVENTS"): research_calendar_events,
    ("CONTENT_STRATEGY_AND_CALENDAR", "BUILD_PLAN_LEVEL"): build_plan_level,
    ("CUSTOMER_PROFILING", "INDUCTION_TURN"): induction_turn,
    # WC176-R009: the induction is shared by the three Trial skills, so the first Trial reply works for whichever is selected.
    ("MARKET_RESEARCH_AND_MATURITY", "INDUCTION_TURN"): induction_turn,
    ("CONTENT_STRATEGY_AND_CALENDAR", "INDUCTION_TURN"): induction_turn,
    ("CUSTOMER_PROFILING", "PROPOSE_GOALS"): propose_goals,
    ("MARKET_RESEARCH_AND_MATURITY", "PUBLIC_ENRICHMENT"): enrich_public_footprint,
    ("SOCIAL_CONTENT_CREATION_AND_PUBLISHING", "CREATE_DRAFTS"): create_platform_drafts,
    ("MARKETING_PERFORMANCE_AND_IMPROVEMENT", "BUILD_DIGEST"): build_digest,
}


def _handle(envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "CUSTOMER_PROFILING": profile_customer,
        "MARKET_RESEARCH_AND_MATURITY": research_market,
        "CONTENT_STRATEGY_AND_CALENDAR": create_content_strategy,
    }
    try:
        operation = payload.get("operation")
        if operation is not None:
            return OPERATIONS[(envelope.skill_id, str(operation))](payload)
        return handlers[envelope.skill_id](payload)
    except (KeyError, SkillInputDenied) as error:
        raise AdapterContractError("ADAPTER_DOMAIN_INPUT_DENIED", envelope.correlation_id) from error


def create_adapter() -> ReferenceAdapter:
    artifact_digest = os.environ.get("DMA_ARTIFACT_DIGEST")
    if artifact_digest is None:
        raise RuntimeError("DMA_ARTIFACT_DIGEST is required")
    admission_content_digest = os.environ.get("DMA_ADMISSION_CONTENT_DIGEST")
    if admission_content_digest is None:
        raise RuntimeError("DMA_ADMISSION_CONTENT_DIGEST is required")
    return ReferenceAdapter(
        AdapterDescriptorV1(
            protocol_version="1.0.0",
            compatible_minor_versions=("1.0.0",),
            professional_type_id="DIGITAL_MARKETING_LOCAL_SERVICE",
            professional_version="1.0.0",
            artifact_digest=artifact_digest,
            admission_content_digest=admission_content_digest,
            pac_version="1.0.0",
            pac_digest="sha256:" + "44" * 32,
            skill_versions={
                "CUSTOMER_PROFILING": "1.0.0",
                "MARKET_RESEARCH_AND_MATURITY": "1.0.0",
                "CONTENT_STRATEGY_AND_CALENDAR": "1.0.0",
                "SOCIAL_CONTENT_CREATION_AND_PUBLISHING": "1.0.0",
                "MARKETING_PERFORMANCE_AND_IMPROVEMENT": "1.0.0",
            },
            schema_digests={"configuration": "sha256:" + "99" * 32, "goal": "sha256:" + "aa" * 32},
            execution_models=("APPROVAL_GATE", "PRE_AUTHORIZED"),
            capabilities=("planning", "streaming", "cancellation", "stop", "resume", "result-replay"),
        ),
        _handle,
    )
