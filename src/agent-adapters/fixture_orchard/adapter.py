"""Orchard Advisor domain behaviour behind the common runtime contract: a fixed, side-effect-free answer."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R004, R035
# Constitutional basis: C-035, C-059, C-071, C-079

from __future__ import annotations

from typing import Any

from runtime_contract import AdapterDescriptorV1, AdapterInvocationEnvelopeV1, ReferenceAdapter


def _handle(envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "SEASON_ADVICE_PROPOSAL",
        "skillId": envelope.skill_id,
        "status": "PROPOSED",
        "sideEffects": [],
    }


def create_adapter() -> ReferenceAdapter:
    return ReferenceAdapter(
        AdapterDescriptorV1(
            protocol_version="1.0.0",
            compatible_minor_versions=("1.0.0",),
            professional_type_id="FIXTURE_ORCHARD_ADVISOR",
            professional_version="1.0.0",
            artifact_digest="sha256:" + "31" * 32,
            admission_content_digest="sha256:" + "32" * 32,
            pac_version="1.0.0",
            pac_digest="sha256:" + "44" * 32,
            skill_versions={"SEASON_PLANNING": "1.0.0"},
            schema_digests={"configuration": "sha256:" + "99" * 32, "goal": "sha256:" + "aa" * 32},
            execution_models=("APPROVAL_GATE",),
            capabilities=("planning", "streaming", "cancellation", "stop", "resume", "result-replay"),
        ),
        _handle,
    )
