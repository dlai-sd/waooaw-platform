# Implements: adr/ADR-043-skill-architecture-standard.md §3
# constitutional_basis: C-036 (skills are constitutional units), C-041 (tool auth),
#                       C-059 (traceability), ADR-043 §3 (skill resolution at session open)
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillAssignment:
    """Pinned skill assignment from an Employment Contract (ADR-043 §4)."""
    skill_id: str
    version: str


@dataclass(frozen=True)
class CrystallizerConfig:
    """Intent Crystallizer configuration extracted from a skill definition."""
    enabled: bool
    prompt_template: str
    requires_customer_approval: bool
    locked_artifact_schema: str = ""


@dataclass
class SessionSkillContext:
    """Resolved skill context for a single PAAS session.

    Built once at session open (ADR-043 §3). Capability-complete and
    constitutionally bounded — all tool authorization is derived from this object.
    """
    authorized_tools: set[str] = field(default_factory=set)
    crystallizer_configs: dict[str, CrystallizerConfig] = field(default_factory=dict)
    autonomy_levels: dict[str, str] = field(default_factory=dict)
    required_providers: set[str] = field(default_factory=set)
    # tool → DCM category (from skill's default_dcm_category — passed to CE.ValidateAction)
    dcm_categories: dict[str, str] = field(default_factory=dict)
    # tool → owning skill_id (for crystallizer gate lookup)
    tool_skill_index: dict[str, str] = field(default_factory=dict)


class SkillResolutionError(Exception):
    """Raised when a skill assignment cannot be resolved from the BP Skill Catalog.

    ADR-043 §3: session fails to open on SkillResolutionError — no tool calls permitted.
    """
    def __init__(self, skill_id: str, version: str, reason: str = "") -> None:
        self.skill_id = skill_id
        self.version = version
        super().__init__(f"SkillResolutionError: {skill_id}@{version} — {reason}")


class SkillResolver:
    """Resolves skill manifests from the BP Skill Catalog at PAAS session open.

    ADR-043 §3: One resolver per session. Called exactly once during STARTING phase.
    Not called during the ACTIVE phase hot path.
    """

    def __init__(
        self,
        bp_base_url: str,
        auth_token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._bp_base_url = bp_base_url.rstrip("/")
        self._auth_token = auth_token
        self._http_client = http_client  # injectable for tests (respx / httpx mock)

    async def resolve_skills(
        self,
        contract_id: str,
        skills: list[SkillAssignment],
    ) -> SessionSkillContext:
        """For each skill assignment, fetch the manifest from BP and build SessionSkillContext.

        Raises SkillResolutionError on unknown or unavailable skill — session fails to open.
        """
        ctx = SessionSkillContext()

        for assignment in skills:
            definition = await self._fetch_skill(assignment.skill_id, assignment.version)
            _merge_into_context(ctx, assignment.skill_id, definition)

        logger.info(
            "Skill resolution complete. contract_id=%s authorized_tools=%d providers=%d",
            contract_id,
            len(ctx.authorized_tools),
            len(ctx.required_providers),
        )
        return ctx

    async def _fetch_skill(self, skill_id: str, version: str) -> dict[str, Any]:
        url = f"{self._bp_base_url}/api/v1/skills/{skill_id}/{version}"
        headers: dict[str, str] = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        try:
            if self._http_client is not None:
                resp = await self._http_client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise SkillResolutionError(skill_id, version, f"HTTP request failed: {exc}") from exc

        if resp.status_code == 404:
            raise SkillResolutionError(skill_id, version, "not found in Skill Catalog (404)")
        if not resp.is_success:
            raise SkillResolutionError(
                skill_id, version, f"BP Skill Catalog returned {resp.status_code}"
            )

        payload = resp.json()
        # BP wraps the JSONB definition field in the SkillResponse DTO:
        # { "skillId": "...", "version": "...", "definition": { <ADR-043 §1 schema> }, ... }
        defn = payload.get("definition", {})
        if isinstance(defn, str):
            defn = json.loads(defn)
        if not isinstance(defn, dict):
            raise SkillResolutionError(
                skill_id, version, "definition field is not a JSON object"
            )
        return defn


def _merge_into_context(
    ctx: SessionSkillContext, skill_id: str, defn: dict[str, Any]
) -> None:
    """Merge a single skill definition into the session context (union semantics)."""
    dcm = defn.get("default_dcm_category", "DETERMINISTIC_REQUIRED")

    for tool in defn.get("tools", []):
        ctx.authorized_tools.add(tool)
        ctx.dcm_categories[tool] = dcm
        ctx.tool_skill_index[tool] = skill_id

    for provider in defn.get("required_providers", []):
        ctx.required_providers.add(provider)

    ctx.autonomy_levels[skill_id] = defn.get("default_autonomy_level", "APPROVAL_REQUIRED")

    ic = defn.get("intent_crystallizer")
    if ic and isinstance(ic, dict):
        ctx.crystallizer_configs[skill_id] = CrystallizerConfig(
            enabled=bool(ic.get("enabled", False)),
            prompt_template=str(ic.get("prompt_template", "")),
            requires_customer_approval=bool(ic.get("requires_customer_approval", True)),
            locked_artifact_schema=str(ic.get("locked_artifact_schema", "")),
        )
