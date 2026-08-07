# Implements: adr/ADR-043-skill-architecture-standard.md §3
# constitutional_basis: C-023 (Evidence First — customer approval is an evidence event),
#                       C-036 (skills are constitutional units), C-059 (traceability),
#                       ADR-043 §3 (Intent Crystallizer before any tool call in skill's tool set)
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class LockedArtifact:
    """Customer-approved artifact produced by the Intent Crystallizer.

    ADR-043 §3: Persisted in Temporal workflow state — survives session restart.
    Any tool call in a skill's authorized_tools set is blocked until the corresponding
    LockedArtifact exists in session state.
    """
    skill_id: str
    artifact_type: str  # e.g. "campaign_brief"
    content: dict[str, Any] = field(default_factory=dict)
    approval_evidence_id: str = ""  # CE evidence record ID for the customer's approval (C-023)


class CrystallizerRequiredError(Exception):
    """Raised when a tool call is blocked because no LockedArtifact exists for the skill.

    ADR-043 §3: Maps to MCPToolError(CONSTITUTIONAL_BLOCKED) — caller must present the
    crystallizer to the customer before retrying the tool call.
    """
    def __init__(self, skill_id: str, tool_name: str) -> None:
        self.skill_id = skill_id
        self.tool_name = tool_name
        super().__init__(
            f"Tool '{tool_name}' requires a LockedArtifact for skill '{skill_id}'. "
            "Run IntentCrystallizer and obtain customer approval first."
        )


class LLMClient(Protocol):  # pragma: no cover
    """Minimal interface for calling the LLM (injectable for tests)."""
    async def generate(self, prompt_template: str, skill_id: str) -> dict[str, Any]:
        ...


class CEApprovalClient(Protocol):  # pragma: no cover
    """Minimal interface for writing a CE evidence record for customer approval (C-023)."""
    async def record_approval(self, skill_id: str, artifact_content: dict[str, Any]) -> str:
        """Return the CE evidence_record_id."""
        ...


class IntentCrystallizer:
    """Produces a LockedArtifact by prompting the LLM and recording customer approval.

    ADR-043 §3:
    - Called once per crystallizer-enabled skill at session open (before any tool call).
    - The customer must approve the artifact; approval writes a CE evidence record (C-023).
    - The resulting LockedArtifact is stored in Temporal session state (WC041-04).
    - Any tool call in the skill's authorized_tools set without a LockedArtifact →
      CrystallizerRequiredError → MCPToolError(CONSTITUTIONAL_BLOCKED).
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        ce_client: CEApprovalClient | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._ce_client = ce_client

    async def crystallize(
        self,
        skill_id: str,
        prompt_template: str,
        session_metadata: dict[str, Any] | None = None,
    ) -> LockedArtifact:
        """Build structured intent artifact → present for customer approval → record evidence.

        Returns a LockedArtifact with a populated approval_evidence_id.
        """
        logger.info("IntentCrystallizer starting. skill_id=%s", skill_id)

        artifact_content = await self._generate_artifact(skill_id, prompt_template, session_metadata or {})
        evidence_id = await self._record_approval(skill_id, artifact_content)

        locked = LockedArtifact(
            skill_id=skill_id,
            artifact_type="campaign_brief",
            content=artifact_content,
            approval_evidence_id=evidence_id,
        )
        logger.info(
            "IntentCrystallizer complete. skill_id=%s evidence_id=%s",
            skill_id,
            evidence_id,
        )
        return locked

    async def _generate_artifact(
        self,
        skill_id: str,
        prompt_template: str,
        session_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if self._llm_client is not None:
            return await self._llm_client.generate(
                prompt_template=prompt_template, skill_id=skill_id
            )
        # Stub — real implementation routes through AIR via CTG
        return {
            "skill_id": skill_id,
            "prompt_template": prompt_template,
            "status": "pending_customer_approval",
        }

    async def _record_approval(self, skill_id: str, artifact_content: dict[str, Any]) -> str:
        if self._ce_client is not None:
            return await self._ce_client.record_approval(skill_id, artifact_content)
        # Stub — real implementation calls CE gRPC with action_type=SKILL_APPROVAL
        return f"evidence-{skill_id}-approval-stub"
