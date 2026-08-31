"""Trading domain behavior behind the common runtime contract."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

from __future__ import annotations

from typing import Any

from runtime_contract import AdapterDescriptorV1, AdapterInvocationEnvelopeV1, ReferenceAdapter


def _handle(envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "TRADE_PROPOSAL",
        "skillId": envelope.skill_id,
        "status": "PAPER_ONLY" if envelope.mode == "TRIAL" else "PROPOSED",
        "marketEventReference": payload.get("marketEventReference"),
    }


def create_adapter() -> ReferenceAdapter:
    return ReferenceAdapter(
        AdapterDescriptorV1(
            protocol_version="1.0.0",
            compatible_minor_versions=("1.0.0",),
            professional_type_id="TRADING_FO_CRYPTO",
            professional_version="1.8.0",
            artifact_digest="sha256:" + "14" * 32,
            admission_content_digest="sha256:" + "22" * 32,
            pac_version="1.0.0",
            pac_digest="sha256:" + "44" * 32,
            skill_versions={"MARKET_SIGNAL_ANALYSIS": "1.8.0"},
            schema_digests={"configuration": "sha256:" + "99" * 32, "goal": "sha256:" + "aa" * 32},
            execution_models=("APPROVAL_GATE",),
            capabilities=("planning", "streaming", "cancellation", "stop", "resume", "result-replay"),
        ),
        _handle,
    )