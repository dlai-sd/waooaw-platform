"""Trial induction reply: the agent's deterministic induction turn, reached through its admitted adapter."""

# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R009
# Constitutional basis: C-023, C-035, C-059, C-063, C-071, C-079

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import timezone
from pathlib import Path
from typing import Any

import httpx

INDUCTION_OPERATION = "INDUCTION_TURN"
ADAPTER_SCHEMA_VERSION = "1.0.0"
MAXIMUM_REPLY_CHARACTERS = 1200
MAXIMUM_SENTENCE_CHARACTERS = 400
SUMMARY_STATES = frozenset({"READY", "PARTIAL", "INCOMPLETE"})
TRIAL_NOTICE = (
    "This is your Trial. Here I only ask questions and give advice: I do not use paid services, "
    "post anywhere, or act on any of your accounts."
)
INDUCTION_COMPLETE = "I have what I need for now. Your next step is to review the profile in your workspace."
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class TrialInductionError(RuntimeError):
    """Stable, privacy-safe reason the Trial reply could not be produced."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def canonical_digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def workload_uri_from_credentials(credentials: Path) -> str | None:
    try:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        uri = manifest["workloads"]["professional-runtime"]["identity_uri"]
    except (OSError, KeyError, TypeError, ValueError):
        return None
    return uri if isinstance(uri, str) and uri.startswith("spiffe://") else None


def _sentence(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAXIMUM_SENTENCE_CHARACTERS or _CONTROL.search(value):
        raise TrialInductionError("TRIAL_REPLY_INVALID")
    return value.strip()


def render_reply(turn: dict[str, Any]) -> str:
    """Bounded words for the customer; refuses any turn that claims a side effect."""
    if turn.get("kind") != INDUCTION_OPERATION or turn.get("sideEffects") != [] or turn.get("summaryState") not in SUMMARY_STATES:
        raise TrialInductionError("TRIAL_REPLY_INVALID")
    parts = [TRIAL_NOTICE]
    if turn.get("opening") is not None:
        parts.append(_sentence(turn["opening"]))
    question = turn.get("nextQuestion")
    if question is None:
        parts.append(INDUCTION_COMPLETE)
    elif isinstance(question, dict):
        parts.append(_sentence(question.get("text")))
    else:
        raise TrialInductionError("TRIAL_REPLY_INVALID")
    reply = "\n\n".join(parts)
    if len(reply) > MAXIMUM_REPLY_CHARACTERS:
        raise TrialInductionError("TRIAL_REPLY_INVALID")
    return reply


class AdapterTrialInductionClient:
    """Calls the admitted agent adapter over the private Agent Runtime Adapter transport, in Trial mode only."""

    def __init__(self, base_url: str, bearer: str, workload_uri: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {bearer}", "X-WAOOAW-Workload-URI": workload_uri}
        self._client = client

    async def close(self) -> None:
        await self._client.aclose()

    async def induction_turn(
        self,
        *,
        mandate: Any,
        execution_id: uuid.UUID,
        idempotency_key: uuid.UUID,
        correlation_id: uuid.UUID,
    ) -> dict[str, Any]:
        payload = {"operation": INDUCTION_OPERATION, "engagementMode": "TRIAL"}
        deadline = mandate.deadline if mandate.deadline.tzinfo else mandate.deadline.replace(tzinfo=timezone.utc)
        envelope = {
            "schemaVersion": ADAPTER_SCHEMA_VERSION,
            "tenantRef": mandate.tenant_id,
            "relationshipId": mandate.relationship_id,
            "agentInstanceId": mandate.agent_instance_id,
            "professionalTypeId": mandate.professional_type,
            "professionalVersion": mandate.professional_version,
            "skillId": mandate.skill_id,
            "skillVersion": mandate.skill_version,
            "admissionContentDigest": mandate.admission_content_digest,
            "artifactDigest": mandate.artifact_digest,
            "customerContractDigest": mandate.customer_contract_digest,
            "decisionSpaceVersion": str(mandate.decision_space_revision),
            "configurationRevision": str(mandate.configuration_revision),
            "goalRevision": str(mandate.goal_revision),
            "invocationId": str(execution_id),
            "idempotencyKey": str(idempotency_key),
            "payloadDigest": canonical_digest(payload),
            "ceDecisionRef": mandate.constitutional_decision_ref,
            "evidenceContextRef": mandate.constitutional_evidence_ref,
            "deadline": deadline.isoformat(),
            "correlationId": str(correlation_id),
            "mode": "TRIAL",
        }
        try:
            started = await self._client.post(
                f"{self._base_url}/internal/v1/invocations",
                json={"envelope": envelope, "payload": payload},
                headers=self._headers,
            )
            if started.status_code != 202 or started.json().get("state") != "SUCCEEDED":
                raise TrialInductionError("ADAPTER_REFUSED")
            fetched = await self._client.request(
                "GET",
                f"{self._base_url}/internal/v1/invocations/{execution_id}/result",
                json={"envelope": envelope},
                headers=self._headers,
            )
            if fetched.status_code != 200:
                raise TrialInductionError("ADAPTER_RESULT_UNAVAILABLE")
            result = fetched.json()
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise TrialInductionError("ADAPTER_UNAVAILABLE") from error
        if not isinstance(result, dict):
            raise TrialInductionError("ADAPTER_RESULT_INVALID")
        output = result.get("output")
        if (
            result.get("state") != "SUCCEEDED"
            or result.get("invocationId") != str(execution_id)
            or not isinstance(output, dict)
            or not isinstance(result.get("outputPayloadDigest"), str)
            or not hmac.compare_digest(result["outputPayloadDigest"], canonical_digest(output))
        ):
            raise TrialInductionError("ADAPTER_RESULT_INVALID")
        return output
