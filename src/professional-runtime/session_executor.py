# Implements: adr/ADR-043-skill-architecture-standard.md §3
# constitutional_basis: C-041 (tool authorization governed by Decision Space),
#                       C-023 (Evidence First — CE called for every tool dispatch),
#                       C-059 (traceability), ADR-043 §3
from __future__ import annotations

import logging
from typing import Any, Protocol

from evaluation_workflow import EvaluationMessage, InterviewAnswerService, TypedAnswerEnvelope
from intent_crystallizer import CrystallizerRequiredError, LockedArtifact
from skill_resolver import SessionSkillContext

logger = logging.getLogger(__name__)


class C041ToolAuthorizationError(Exception):
    """Raised when the LLM requests a tool not in the session's authorized_tools.

    C-041: tool authorization is derived from the Employment Contract skills[].
    A tool not in authorized_tools means the agent does not hold a skill that
    declares it. The caller is responsible for writing a CE DENY evidence record
    before propagating this error (C-023 obligation belongs to the session layer).
    """
    def __init__(self, tool_name: str, authorized_tools: set[str]) -> None:
        self.tool_name = tool_name
        super().__init__(
            f"C-041 ToolAuthorizationError: tool '{tool_name}' is not in the "
            f"session authorized_tools. Authorized: {sorted(authorized_tools)}"
        )


class ToolDispatcher(Protocol):  # pragma: no cover
    """Minimal interface for the downstream dispatcher (CTG or stub)."""
    async def dispatch(
        self,
        tool_name: str,
        params: dict[str, Any],
        dcm_category: str,
        skill_id: str,
    ) -> Any:
        ...


class SessionExecutor:
    """Guards tool dispatch in a PAAS session with two constitutional pre-flight checks.

    Pre-flight order (runs BEFORE calling CTG):
      Gate 1 — C-041 tool authorization: tool_name ∈ session_ctx.authorized_tools
      Gate 2 — Crystallizer gate: LockedArtifact exists for skills that require it
      Gate 3 — CE dispatch via injected dispatcher (CTG in production)

    ADR-043 §3: Both gates run before every tool call — no exceptions.
    """

    def __init__(
        self,
        session_ctx: SessionSkillContext,
        dispatcher: ToolDispatcher | None = None,
        interview_service: InterviewAnswerService | None = None,
    ) -> None:
        self._ctx = session_ctx
        self._dispatcher = dispatcher
        self._interview_service = interview_service
        # Temporal-persisted session state (WC041-04)
        self._locked_artifacts: dict[str, LockedArtifact] = {}
        self._crystallization_complete: dict[str, bool] = {}

    # ── Session state management (WC041-04) ────────────────────────────────

    def add_locked_artifact(self, skill_id: str, artifact: LockedArtifact) -> None:
        """Record a customer-approved LockedArtifact. Unblocks tool calls for this skill."""
        self._locked_artifacts[skill_id] = artifact
        self._crystallization_complete[skill_id] = True
        logger.info("LockedArtifact stored for skill_id=%s", skill_id)

    def get_locked_artifact(self, skill_id: str) -> LockedArtifact | None:
        return self._locked_artifacts.get(skill_id)

    def is_crystallization_complete(self, skill_id: str) -> bool:
        return self._crystallization_complete.get(skill_id, False)

    # ── Pre-flight gates ────────────────────────────────────────────────────

    def _check_tool_authorized(self, tool_name: str) -> None:
        """Gate 1: C-041 — tool must be in session authorized_tools."""
        if tool_name not in self._ctx.authorized_tools:
            logger.warning(
                "C-041 ToolAuthorizationError: tool=%s not in authorized_tools",
                tool_name,
            )
            raise C041ToolAuthorizationError(tool_name, self._ctx.authorized_tools)

    def _check_crystallizer_gate(self, tool_name: str) -> None:
        """Gate 2: If the tool's owning skill requires crystallization, assert artifact exists."""
        skill_id = self._ctx.tool_skill_index.get(tool_name)
        if skill_id is None:
            return  # tool not owned by a skill with a crystallizer — skip gate

        config = self._ctx.crystallizer_configs.get(skill_id)
        if config is None or not config.enabled:
            return  # skill exists but has no crystallizer — skip gate

        if not self._crystallization_complete.get(skill_id, False):
            raise CrystallizerRequiredError(skill_id, tool_name)

    # ── Main dispatch ───────────────────────────────────────────────────────

    async def check_and_dispatch(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> Any:
        """Run pre-flight gates then dispatch via injected dispatcher.

        Raises:
            C041ToolAuthorizationError: tool not in authorized_tools (C-041 violation)
            CrystallizerRequiredError: skill requires a LockedArtifact before tool call
        """
        self._check_tool_authorized(tool_name)
        self._check_crystallizer_gate(tool_name)

        dcm_category = self._ctx.dcm_categories.get(tool_name, "DETERMINISTIC_REQUIRED")
        skill_id = self._ctx.tool_skill_index.get(tool_name, "")

        if self._dispatcher is not None:
            return await self._dispatcher.dispatch(
                tool_name=tool_name,
                params=params,
                dcm_category=dcm_category,
                skill_id=skill_id,
            )

        logger.warning("No dispatcher injected — tool call returned stub. tool=%s", tool_name)
        return {"status": "dispatched", "tool": tool_name}

    async def answer_interview(
        self,
        relationship_id: str,
        message: EvaluationMessage,
        evidence_context: tuple[str, ...] = (),
    ) -> TypedAnswerEnvelope:
        if self._interview_service is None:
            raise RuntimeError("Professional evaluation adapter is not configured")
        return await self._interview_service.answer(
            relationship_id,
            message,
            evidence_context,
        )
