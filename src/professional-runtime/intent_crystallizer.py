# Implements: adr/ADR-043-skill-architecture-standard.md §3
# constitutional_basis: C-023 (Evidence First — customer approval is an evidence event),
#                       C-036 (skills are constitutional units), C-059 (traceability),
#                       ADR-043 §3 (Intent Crystallizer before any tool call in skill's tool set)
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
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
    artifact_type: str  # derived from CrystallizerConfig.locked_artifact_schema
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

    async def generate(self, prompt_template: str, skill_id: str) -> dict[str, Any]: ...


class CEApprovalClient(Protocol):  # pragma: no cover
    """Minimal interface for writing a CE evidence record for customer approval (C-023)."""

    async def record_approval(self, skill_id: str, artifact_content: dict[str, Any]) -> str:
        """Return the CE evidence_record_id."""
        ...


def _artifact_type_from_schema(schema_path: str) -> str:
    """Derive a stable artifact_type token from the locked_artifact_schema path.

    "schemas/campaign_brief_v1.json" → "campaign_brief"
    "schemas/ad_plan_v2.json"        → "ad_plan"
    ""                                → "artifact"
    """
    if not schema_path:
        return "artifact"
    stem = PurePosixPath(schema_path).stem  # "campaign_brief_v1"
    return re.sub(r"_v\d+.*$", "", stem) or "artifact"  # "campaign_brief"


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
        config: CrystallizerConfig,  # CrystallizerConfig lives in skill_resolver (imported at module bottom)
    ) -> LockedArtifact:
        """Build structured intent artifact → present for customer approval → record evidence.

        WC-041-03 contract: crystallize(skill_id, config: CrystallizerConfig) → LockedArtifact.
        Returns a LockedArtifact with a populated approval_evidence_id (C-023).
        """
        logger.info("IntentCrystallizer starting. skill_id=%s", skill_id)

        artifact_content = await self._generate_artifact(skill_id, config.prompt_template)
        artifact_type = _artifact_type_from_schema(config.locked_artifact_schema)
        evidence_id = await self._record_approval(skill_id, artifact_content)

        locked = LockedArtifact(
            skill_id=skill_id,
            artifact_type=artifact_type,
            content=artifact_content,
            approval_evidence_id=evidence_id,
        )
        logger.info(
            "IntentCrystallizer complete. skill_id=%s artifact_type=%s evidence_id=%s",
            skill_id,
            artifact_type,
            evidence_id,
        )
        return locked

    async def _generate_artifact(
        self,
        skill_id: str,
        prompt_template: str,
    ) -> dict[str, Any]:
        if self._llm_client is not None:
            return await self._llm_client.generate(prompt_template=prompt_template, skill_id=skill_id)
        # Stub — real implementation routes through AIR via CTG
        return {
            "skill_id": skill_id,
            "prompt_template": prompt_template,
            "status": "pending_customer_approval",
        }

    async def _record_approval(self, skill_id: str, artifact_content: dict[str, Any]) -> str:
        if self._ce_client is not None:
            return await self._ce_client.record_approval(skill_id, artifact_content)
        # GAP-004 fix: warn when ce_client absent — C-023 violated in production
        logger.warning(
            "ce_client not configured — LockedArtifact has no CE evidence record. C-023 violated in production. skill_id=%s",
            skill_id,
        )
        return f"evidence-{skill_id}-approval-stub"


# Avoid circular import: CrystallizerConfig is defined in skill_resolver but used here
# only as a type annotation. Import at runtime to keep the dependency direction clear.
from skill_resolver import CrystallizerConfig as CrystallizerConfig  # noqa: E402
