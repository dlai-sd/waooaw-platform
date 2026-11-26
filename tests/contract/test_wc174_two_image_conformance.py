"""WC-174 R004, R035: the same conformance kit passes for two sealed agent images with no platform change."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R004, R035
# Constitutional basis: C-023, C-035, C-059, C-079, ADR-049

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[2]
for relative in ("src/digital-marketing-agent", "src/agent-adapters", "src/professional-runtime"):
    sys.path.insert(0, str(ROOT / relative))
os.environ.setdefault("DMA_ARTIFACT_DIGEST", "sha256:" + "ab" * 32)
os.environ.setdefault("DMA_ADMISSION_CONTENT_DIGEST", "sha256:" + "cd" * 32)
os.environ.setdefault("PR_SERVICE_JWT_SECRET", "test-service-assertion")

from digital_marketing import (  # noqa: E402
    DmaEmploymentSemantics,
    MaterialChangeContext,
    PlanContext,
    RelationshipContext,
)
from digital_marketing import create_adapter as create_dma_adapter  # noqa: E402
from digital_marketing.service import create_service_app as create_dma_app  # noqa: E402
from fixture_orchard.adapter import create_adapter as create_fixture_adapter  # noqa: E402
from fixture_orchard.service import create_service_app as create_fixture_app  # noqa: E402
from runtime_contract import (  # noqa: E402
    AdapterContractError,
    AdapterDescriptorV1,
    AdapterInvocationEnvelopeV1,
    InvocationState,
)
from runtime_contract.employment import PerformanceAssessment  # noqa: E402

NOW = datetime(2026, 11, 26, 7, 30, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Image:
    name: str
    adapter: Any
    app: Any
    manifest_version: str
    requirement_set_version: str
    goal_type: str
    skill: str
    milestone: str
    payload: dict[str, Any]


def _dma_semantics() -> DmaEmploymentSemantics:
    return DmaEmploymentSemantics(
        lambda _relationship: RelationshipContext(frozenset({"CUSTOMER_PROFILING"})),
        lambda _relationship, _plan: PlanContext(source_version="profile-1", mandatory_requirements_confirmed=True),
        lambda _relationship, _patch: MaterialChangeContext(calendar_within_accepted_tolerance=True),
        lambda _relationship, period: PerformanceAssessment(
            assessmentVersion="1.0.0",
            reviewPeriodRef=period,
            outcomeLabel="Profile coverage",
            outcomeState="UNKNOWN",
            attributionBasis="No customer-owned evidence yet.",
            attributionConfidence=0,
            agentPerformanceState="MEETING",
            missedReviewPeriods=0,
            evidenceRefs=(),
            limitations=(),
            producedAt=NOW,
        ),
        clock=lambda: NOW,
    )


async def _authorize(_request: object) -> None:
    return None


def _images() -> list[Image]:
    return [
        Image(
            "digital-marketing",
            create_dma_adapter(),
            create_dma_app(_dma_semantics(), _authorize),
            "1.2.0",
            "1.1.0",
            "UNDERSTAND_CURRENT_POSITION",
            "CUSTOMER_PROFILING",
            "PROFILE_CONFIRMED",
            {
                "fields": {
                    "accountMode": {"value": "OWNER_OPERATED", "provenance": "CONFIRMED"},
                    "businessIdentity": {"value": "Local clinic", "provenance": "CONFIRMED"},
                    "audience": {"value": "Local families", "provenance": "CONFIRMED"},
                    "priority": {"value": "Qualified enquiries", "provenance": "CONFIRMED"},
                    "constraints": {"value": "No health claims", "provenance": "CONFIRMED"},
                    "approvedChannels": {"value": ["WEB"], "provenance": "CONFIRMED"},
                }
            },
        ),
        Image(
            "fixture-orchard",
            create_fixture_adapter(),
            create_fixture_app(_authorize),
            "1.0.0",
            "1.0.0",
            "PLAN_THE_SEASON",
            "SEASON_PLANNING",
            "SEASON_PLAN_ACCEPTED",
            {"inputReference": "opaque-input-1"},
        ),
    ]


def _digest(payload: dict[str, Any]) -> str:
    value = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _envelope(descriptor: AdapterDescriptorV1, payload: dict[str, Any], **changes: Any) -> AdapterInvocationEnvelopeV1:
    values: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_ref": "tenant-opaque-1",
        "relationship_id": str(uuid4()),
        "agent_instance_id": str(uuid4()),
        "professional_type_id": descriptor.professional_type_id,
        "professional_version": descriptor.professional_version,
        "skill_id": next(iter(descriptor.skill_versions)),
        "skill_version": next(iter(descriptor.skill_versions.values())),
        "admission_content_digest": descriptor.admission_content_digest,
        "artifact_digest": descriptor.artifact_digest,
        "customer_contract_digest": "sha256:" + "31" * 32,
        "decision_space_version": "decision-space-7",
        "configuration_revision": "configuration-3",
        "goal_revision": "goal-4",
        "invocation_id": str(uuid4()),
        "idempotency_key": str(uuid4()),
        "payload_digest": _digest(payload),
        "ce_decision_ref": "ce-decision-9",
        "evidence_context_ref": "evidence-context-2",
        "deadline": datetime.now(timezone.utc) + timedelta(minutes=1),
        "correlation_id": str(uuid4()),
        "mode": "LIVE",
    }
    values.update(changes)
    return AdapterInvocationEnvelopeV1(**values)


@pytest.fixture(params=["digital-marketing", "fixture-orchard"])
def image(request: pytest.FixtureRequest) -> Image:
    return next(item for item in _images() if item.name == request.param)


def test_both_images_describe_themselves_and_run_the_same_invocation_lifecycle(image: Image) -> None:
    adapter = image.adapter
    descriptor = adapter.describe()
    assert adapter.health()["status"] == "READY"
    assert {"stop", "resume", "cancellation", "result-replay"} <= set(descriptor.capabilities)

    request = _envelope(descriptor, image.payload)
    invocation = adapter.execute(request, image.payload)
    assert invocation.state is InvocationState.SUCCEEDED
    assert adapter.result(request, request.invocation_id) is not None
    assert adapter.events(request, request.invocation_id)
    assert adapter.cancel(request, request.invocation_id).state in {InvocationState.SUCCEEDED, InvocationState.CANCELLED}

    other = _envelope(descriptor, image.payload)
    with pytest.raises(AdapterContractError, match="ADAPTER_NOT_ACCESSIBLE"):
        adapter.status(other, request.invocation_id)


def test_both_images_honour_emergency_stop_and_resume(image: Image) -> None:
    adapter = image.adapter
    descriptor = adapter.describe()
    first = _envelope(descriptor, image.payload)
    adapter.emergency_stop(first, "stop-evidence-1")

    follow_up = _envelope(
        descriptor, image.payload, relationship_id=first.relationship_id, agent_instance_id=first.agent_instance_id
    )
    with pytest.raises(AdapterContractError, match="ADAPTER_STOPPED"):
        adapter.execute(follow_up, image.payload)
    resume = _envelope(
        descriptor,
        image.payload,
        relationship_id=first.relationship_id,
        agent_instance_id=first.agent_instance_id,
        stop_evidence_ref="stop-evidence-1",
    )
    assert adapter.resume(resume)["state"] == "ELIGIBLE"
    assert adapter.execute(follow_up, image.payload).state is InvocationState.SUCCEEDED


@pytest.mark.asyncio
async def test_both_images_answer_the_same_six_domain_operations_with_their_own_declaration(image: Image) -> None:
    relationship = uuid4()
    headers = {"X-Correlation-Id": str(uuid4())}
    descriptor = image.adapter.describe()
    async with AsyncClient(transport=ASGITransport(app=image.app), base_url="http://adapter") as client:
        manifest = (
            await client.get(
                "/internal/v1/employment-interface/manifest",
                params={
                    "agentType": descriptor.professional_type_id,
                    "agentVersion": descriptor.professional_version,
                    "manifestVersion": image.manifest_version,
                },
                headers=headers,
            )
        ).json()
        requirements = (
            await client.get(
                f"/internal/v1/relationships/{relationship}/employment/induction-requirements",
                params={"manifestVersion": image.manifest_version},
                headers=headers,
            )
        ).json()
        plan = await client.post(
            f"/internal/v1/relationships/{relationship}/employment/plan-validation",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={
                "schemaVersion": "1.0",
                "manifestVersion": image.manifest_version,
                "requirementSetVersion": image.requirement_set_version,
                "planVersion": "plan-1",
                "goalType": image.goal_type,
                "skillRefs": [image.skill],
                "milestoneTypes": [image.milestone],
                "sourceVersion": "profile-1",
            },
        )
        change = await client.post(
            f"/internal/v1/relationships/{relationship}/employment/material-change-classification",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={
                "schemaVersion": "1.0",
                "manifestVersion": image.manifest_version,
                "currentPlanVersion": "plan-1",
                "candidatePatchRef": str(UUID(int=7)),
                "protectedCategoryFlags": ["TARGET"],
            },
        )
        isolation = await client.post(
            f"/internal/v1/relationships/{relationship}/employment/dependency-isolation",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={
                "schemaVersion": "1.0",
                "manifestVersion": image.manifest_version,
                "dependencyRef": "DEPENDENCY-1",
                "dependencyState": "LOST",
                "candidateAffectedSkillRefs": [image.skill],
            },
        )
        performance = await client.get(
            f"/internal/v1/relationships/{relationship}/employment/performance-assessments/2026-11",
            headers=headers,
        )

    assert manifest["agentType"] == descriptor.professional_type_id
    assert manifest["experience"]["modes"] and len(manifest["experience"]["modes"]) == 3
    assert requirements["requirementSetVersion"] == image.requirement_set_version
    assert requirements["requirements"]
    assert plan.status_code == 200 and plan.json()["state"] == "VALID"
    assert change.status_code == 200 and change.json()["classification"] in {"MATERIAL", "NON_MATERIAL", "UNKNOWN"}
    assert isolation.status_code == 200 and isolation.json()["isolation"] in {"PROVEN_BOUNDED", "NOT_BOUNDED", "UNKNOWN"}
    assert performance.status_code == 200 and performance.json()["outcomeState"]


def test_the_two_images_are_different_agents_declared_through_the_same_fields() -> None:
    dma, fixture = [item.adapter.describe() for item in _images()]
    manifests = [
        json.loads((ROOT / path).read_text(encoding="utf-8"))["experience"]
        for path in (
            "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json",
            "src/agent-adapters/fixture_orchard/contracts/employment-interface-manifest.v1.json",
        )
    ]

    assert dma.professional_type_id != fixture.professional_type_id
    assert dma.artifact_digest != fixture.artifact_digest
    for experience in manifests:
        assert [mode["modeId"] for mode in experience["modes"]] == ["INDUCT", "GOALS", "OPERATIONS"]
    labels = [[mode["label"] for mode in experience["modes"]] for experience in manifests]
    assert labels[0] != labels[1]
    assert [level["levelId"] for level in manifests[0]["planLevels"]] != [
        level["levelId"] for level in manifests[1]["planLevels"]
    ]
    assert len(manifests[0]["planLevels"]) == 4 and len(manifests[1]["planLevels"]) == 3
    assert {layer["layerId"] for layer in manifests[0]["eventLayers"]} != {
        layer["layerId"] for layer in manifests[1]["eventLayers"]
    }
