"""WC176-R009: the Trial first reply comes from the admitted adapter's deterministic induction turn."""

# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R009
# Constitutional basis: C-023, C-035, C-059, C-063, C-071, C-079
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from digital_marketing.adapter import create_adapter
from runtime_contract.http import create_app
from trial_induction import (
    INDUCTION_COMPLETE,
    MAXIMUM_REPLY_CHARACTERS,
    TRIAL_NOTICE,
    AdapterTrialInductionClient,
    TrialInductionError,
    render_reply,
    workload_uri_from_credentials,
)

WORKLOAD_URI = os.environ.get("PR_WORKLOAD_URI", "spiffe://demo.waooaw.internal/workload/professional-runtime")
TRIAL_SKILLS = ["CUSTOMER_PROFILING", "MARKET_RESEARCH_AND_MATURITY", "CONTENT_STRATEGY_AND_CALENDAR"]


def _mandate(skill_id: str = "CUSTOMER_PROFILING", **overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "tenant_id": str(uuid.uuid4()),
        "relationship_id": str(uuid.uuid4()),
        "agent_instance_id": str(uuid.uuid4()),
        "professional_type": "DIGITAL_MARKETING_LOCAL_SERVICE",
        "professional_version": "1.0.0",
        "skill_id": skill_id,
        "skill_version": "1.0.0",
        "admission_content_digest": os.environ["DMA_ADMISSION_CONTENT_DIGEST"],
        "artifact_digest": os.environ["DMA_ARTIFACT_DIGEST"],
        "customer_contract_digest": "sha256:" + "88" * 32,
        "decision_space_revision": 1,
        "configuration_revision": 1,
        "goal_revision": 1,
        "constitutional_decision_ref": "ce-decision:test",
        "constitutional_evidence_ref": "ce-evidence:test",
        "deadline": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _client(bearer: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> AdapterTrialInductionClient:
    adapter_transport = transport or ASGITransport(app=create_app(create_adapter()))
    return AdapterTrialInductionClient(
        "http://dma-adapter",
        bearer or os.environ["PR_SERVICE_JWT_SECRET"],
        WORKLOAD_URI,
        httpx.AsyncClient(transport=adapter_transport),
    )


async def _turn(client: AdapterTrialInductionClient, mandate: SimpleNamespace) -> dict[str, Any]:
    try:
        return await client.induction_turn(
            mandate=mandate,
            execution_id=uuid.uuid4(),
            idempotency_key=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
        )
    finally:
        await client.close()


@pytest.mark.parametrize("skill_id", TRIAL_SKILLS)
async def test_real_adapter_gives_a_bounded_trial_reply_for_every_trial_skill(skill_id: str) -> None:
    turn = await _turn(_client(), _mandate(skill_id))

    assert turn["sideEffects"] == [] and turn["nextQuestion"]["requirementRef"] == "DMA-IND-002"
    reply = render_reply(turn)
    assert reply.startswith(TRIAL_NOTICE)
    assert "selected business outcomes" in reply
    assert len(reply) <= MAXIMUM_REPLY_CHARACTERS


async def test_adapter_refusals_become_one_stable_error() -> None:
    wrong_secret = _client(bearer="not-the-service-secret")
    wrong_artifact = _client()
    with pytest.raises(TrialInductionError) as denied:
        await _turn(wrong_secret, _mandate())
    with pytest.raises(TrialInductionError) as mismatch:
        await _turn(wrong_artifact, _mandate(artifact_digest="sha256:" + "ee" * 32))

    assert denied.value.code == mismatch.value.code == "ADAPTER_REFUSED"


async def test_unreachable_adapter_is_reported_without_exposing_the_cause() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(TrialInductionError) as unavailable:
        await _turn(_client(transport=httpx.MockTransport(refuse)), _mandate())

    assert unavailable.value.code == "ADAPTER_UNAVAILABLE"


async def test_a_result_whose_digest_does_not_match_its_output_is_refused() -> None:
    def tampered(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(202, json={"state": "SUCCEEDED"})
        invocation_id = request.url.path.split("/")[-2]
        return httpx.Response(
            200,
            json={
                "state": "SUCCEEDED",
                "invocationId": invocation_id,
                "output": {"kind": "INDUCTION_TURN"},
                "outputPayloadDigest": "sha256:" + "00" * 32,
            },
        )

    with pytest.raises(TrialInductionError) as invalid:
        await _turn(_client(transport=httpx.MockTransport(tampered)), _mandate())

    assert invalid.value.code == "ADAPTER_RESULT_INVALID"


def test_a_finished_induction_says_so_and_still_carries_the_trial_notice() -> None:
    reply = render_reply({"kind": "INDUCTION_TURN", "nextQuestion": None, "summaryState": "READY", "sideEffects": []})

    assert reply == f"{TRIAL_NOTICE}\n\n{INDUCTION_COMPLETE}"


@pytest.mark.parametrize(
    "change",
    [
        {"sideEffects": ["POST_TO_PLATFORM"]},
        {"kind": "CUSTOMER_PROFILE_PROPOSAL"},
        {"summaryState": "DONE"},
        {"nextQuestion": {"text": "x" * 401}},
        {"nextQuestion": {"text": "Tell me\x00more"}},
        {"nextQuestion": "free text"},
    ],
)
def test_a_turn_that_claims_an_action_or_is_unbounded_is_never_shown(change: dict[str, Any]) -> None:
    turn: dict[str, Any] = {
        "kind": "INDUCTION_TURN",
        "nextQuestion": {"text": "Please tell me about your business identity."},
        "summaryState": "INCOMPLETE",
        "sideEffects": [],
        **change,
    }

    with pytest.raises(TrialInductionError) as invalid:
        render_reply(turn)

    assert invalid.value.code == "TRIAL_REPLY_INVALID"


def test_workload_identity_comes_from_the_runtime_credentials_only_when_it_is_a_spiffe_uri(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"workloads": {"professional-runtime": {"identity_uri": WORKLOAD_URI}}}))
    assert workload_uri_from_credentials(tmp_path) == WORKLOAD_URI

    manifest.write_text(json.dumps({"workloads": {"professional-runtime": {"identity_uri": "https://example.test"}}}))
    assert workload_uri_from_credentials(tmp_path) is None
    assert workload_uri_from_credentials(tmp_path / "missing") is None
