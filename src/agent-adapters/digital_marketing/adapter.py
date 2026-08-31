"""Digital Marketing domain behavior behind the common runtime contract."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

from __future__ import annotations

from typing import Any

from runtime_contract import AdapterDescriptorV1, AdapterInvocationEnvelopeV1, ReferenceAdapter


def _handle(envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "CAMPAIGN_PLAN",
        "skillId": envelope.skill_id,
        "status": "DRAFT" if envelope.mode == "TRIAL" else "PREPARED",
        "inputReference": payload.get("inputReference"),
    }


def create_adapter() -> ReferenceAdapter:
    return ReferenceAdapter(
        AdapterDescriptorV1(
            protocol_version="1.0.0",
            compatible_minor_versions=("1.0.0",),
            professional_type_id="DIGITAL_MARKETING_LOCAL_SERVICE",
            professional_version="3.1.0",
            artifact_digest="sha256:" + "12" * 32,
            admission_content_digest="sha256:" + "21" * 32,
            pac_version="1.0.0",
            pac_digest="sha256:" + "44" * 32,
            skill_versions={"LOCAL_CAMPAIGN_MANAGEMENT": "3.1.0", "LOCAL_CONTENT_PLANNING": "3.1.0"},
            schema_digests={"configuration": "sha256:" + "99" * 32, "goal": "sha256:" + "aa" * 32},
            execution_models=("APPROVAL_GATE", "PRE_AUTHORIZED"),
            capabilities=("planning", "streaming", "cancellation", "stop", "resume", "result-replay"),
        ),
        _handle,
    )