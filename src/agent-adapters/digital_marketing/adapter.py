"""Digital Marketing domain behavior behind the common runtime contract."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

from __future__ import annotations

import os
from typing import Any

from runtime_contract import AdapterContractError, AdapterDescriptorV1, AdapterInvocationEnvelopeV1, ReferenceAdapter

from .skills import SkillInputDenied, create_content_strategy, profile_customer, research_market


def _handle(envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "CUSTOMER_PROFILING": profile_customer,
        "MARKET_RESEARCH": research_market,
        "CONTENT_STRATEGY": create_content_strategy,
    }
    try:
        return handlers[envelope.skill_id](payload)
    except (KeyError, SkillInputDenied) as error:
        raise AdapterContractError("ADAPTER_DOMAIN_INPUT_DENIED", envelope.correlation_id) from error


def create_adapter() -> ReferenceAdapter:
    artifact_digest = os.environ.get("DMA_ARTIFACT_DIGEST")
    if artifact_digest is None:
        raise RuntimeError("DMA_ARTIFACT_DIGEST is required")
    return ReferenceAdapter(
        AdapterDescriptorV1(
            protocol_version="1.0.0",
            compatible_minor_versions=("1.0.0",),
            professional_type_id="DIGITAL_MARKETING_LOCAL_SERVICE",
            professional_version="1.0.0",
            artifact_digest=artifact_digest,
            admission_content_digest="sha256:" + "21" * 32,
            pac_version="1.0.0",
            pac_digest="sha256:" + "44" * 32,
            skill_versions={
                "CUSTOMER_PROFILING": "1.0.0",
                "MARKET_RESEARCH": "1.0.0",
                "CONTENT_STRATEGY": "1.0.0",
            },
            schema_digests={"configuration": "sha256:" + "99" * 32, "goal": "sha256:" + "aa" * 32},
            execution_models=("APPROVAL_GATE", "PRE_AUTHORIZED"),
            capabilities=("planning", "streaming", "cancellation", "stop", "resume", "result-replay"),
        ),
        _handle,
    )