# Implements: work-contracts/WC-041-skill-architecture-s2-skill-runtime.md §WC041-05
# constitutional_basis: C-036, C-041, C-059, C-076 (≥90% coverage), ADR-043 §3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from intent_crystallizer import (
    CrystallizerRequiredError,
    IntentCrystallizer,
    LockedArtifact,
)
from session_executor import (
    C041ToolAuthorizationError,
    SessionExecutor,
    TrialCapabilityDeniedError,
    TrialEntitlementUnavailableError,
    TrialExpiredError,
)
from skill_resolver import (
    CrystallizerConfig,
    SessionSkillContext,
    SkillAssignment,
    SkillResolutionError,
    SkillResolver,
    _merge_into_context,
)

# ─── Shared fixture helpers ──────────────────────────────────────────────────

CONTENT_PUBLISH_DEFINITION: dict[str, Any] = {
    "skill_id": "content_publish",
    "version": "1.0.0",
    "display_name": "Content Publishing",
    "tools": ["meta.post_content", "meta.post_story", "instagram.post_reel"],
    "required_providers": ["meta"],
    "default_dcm_category": "DETERMINISTIC_REQUIRED",
    "intent_crystallizer": {
        "enabled": True,
        "prompt_template": "skills/content_publish/crystallizer_v1.md",
        "requires_customer_approval": True,
        "locked_artifact_schema": "schemas/campaign_brief_v1.json",
    },
    "default_autonomy_level": "APPROVAL_REQUIRED",
}

BP_SKILL_RESPONSE: dict[str, Any] = {
    "skillId": "content_publish",
    "version": "1.0.0",
    "displayName": "Content Publishing",
    "definition": CONTENT_PUBLISH_DEFINITION,
    "cctSuite": ["CCT-SKILL-CP-01", "CCT-SKILL-CP-02", "CCT-SKILL-CP-03"],
    "status": "PUBLISHED",
    "publishedAt": "2026-08-07T00:00:00Z",
}


# ─── CCT-SKILL-UNKNOWN-01 ────────────────────────────────────────────────────
# session open with unknown skill → SkillResolutionError → session fails to open


class TestCCT_SKILL_UNKNOWN_01:
    """CCT-SKILL-UNKNOWN-01: Unknown skill on session open raises SkillResolutionError.

    ADR-043 §3: session fails to open — no tool calls permitted.
    C-036: skills are constitutional units — unresolvable skills block session start.
    """

    @pytest.mark.asyncio
    async def test_unknown_skill_id_raises_resolution_error(self) -> None:
        """Skill not in BP catalog (404) → SkillResolutionError."""
        with respx.mock(base_url="http://bp-test") as mock:
            mock.get("/api/v1/skills/unknown_skill/1.0.0").mock(
                return_value=httpx.Response(404, json={"error": "SKILL_NOT_FOUND"})
            )
            async with httpx.AsyncClient(base_url="http://bp-test") as client:
                resolver = SkillResolver(bp_base_url="http://bp-test", http_client=client)
                with pytest.raises(SkillResolutionError) as exc_info:
                    await resolver.resolve_skills(
                        contract_id="con-test-001",
                        skills=[SkillAssignment("unknown_skill", "1.0.0")],
                    )
        assert exc_info.value.skill_id == "unknown_skill"
        assert exc_info.value.version == "1.0.0"
        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bp_unavailable_raises_resolution_error(self) -> None:
        """BP connection failure → SkillResolutionError (session fails to open)."""
        async with httpx.AsyncClient(base_url="http://bp-unreachable") as client:
            resolver = SkillResolver(bp_base_url="http://bp-unreachable", http_client=client)
            with pytest.raises(SkillResolutionError) as exc_info:
                await resolver.resolve_skills(
                    contract_id="con-test-002",
                    skills=[SkillAssignment("content_publish", "1.0.0")],
                )
        assert exc_info.value.skill_id == "content_publish"

    @pytest.mark.asyncio
    async def test_known_skill_resolves_successfully(self) -> None:
        """Known skill returns SessionSkillContext with correct authorized_tools."""
        with respx.mock(base_url="http://bp-test") as mock:
            mock.get("/api/v1/skills/content_publish/1.0.0").mock(
                return_value=httpx.Response(200, json=BP_SKILL_RESPONSE)
            )
            async with httpx.AsyncClient(base_url="http://bp-test") as client:
                resolver = SkillResolver(bp_base_url="http://bp-test", http_client=client)
                ctx = await resolver.resolve_skills(
                    contract_id="con-test-003",
                    skills=[SkillAssignment("content_publish", "1.0.0")],
                )

        assert "meta.post_content" in ctx.authorized_tools
        assert "meta.post_story" in ctx.authorized_tools
        assert "instagram.post_reel" in ctx.authorized_tools
        assert "meta" in ctx.required_providers
        assert "content_publish" in ctx.crystallizer_configs
        assert ctx.crystallizer_configs["content_publish"].enabled is True
        assert ctx.dcm_categories["meta.post_content"] == "DETERMINISTIC_REQUIRED"


# ─── CCT-SKILL-CP-01 ─────────────────────────────────────────────────────────
# Intent Crystallizer is called before the first publish tool in content_publish skill


class TestCCT_SKILL_CP_01:
    """CCT-SKILL-CP-01: IntentCrystallizer called before any content_publish tool.

    ADR-043 §3: crystallizer runs at session open for skills with enabled=true.
    C-023: customer approval writes a CE evidence record (approval_evidence_id set).
    """

    @pytest.mark.asyncio
    async def test_crystallizer_produces_locked_artifact(self) -> None:
        """Crystallizer generates artifact and records CE approval evidence."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = {
            "campaign_objective": "Brand awareness",
            "target_audience": "Tech professionals",
            "approved": True,
        }

        mock_ce = AsyncMock()
        mock_ce.record_approval.return_value = "evidence-cp-01-approval"

        crystallizer = IntentCrystallizer(llm_client=mock_llm, ce_client=mock_ce)
        config = CrystallizerConfig(
            enabled=True,
            prompt_template="skills/content_publish/crystallizer_v1.md",
            requires_customer_approval=True,
            locked_artifact_schema="schemas/campaign_brief_v1.json",
        )
        artifact = await crystallizer.crystallize(
            skill_id="content_publish",
            config=config,
        )

        assert isinstance(artifact, LockedArtifact)
        assert artifact.skill_id == "content_publish"
        assert artifact.approval_evidence_id == "evidence-cp-01-approval"
        assert artifact.content["campaign_objective"] == "Brand awareness"
        assert artifact.artifact_type == "campaign_brief"  # GAP-002 fix: derived from locked_artifact_schema
        mock_llm.generate.assert_called_once()
        mock_ce.record_approval.assert_called_once_with(
            "content_publish", artifact.content
        )

    @pytest.mark.asyncio
    async def test_crystallizer_ce_called_before_tool_dispatch_allowed(self) -> None:
        """After crystallization, tool dispatch proceeds without CrystallizerRequiredError."""
        with respx.mock(base_url="http://bp-test") as mock:
            mock.get("/api/v1/skills/content_publish/1.0.0").mock(
                return_value=httpx.Response(200, json=BP_SKILL_RESPONSE)
            )
            async with httpx.AsyncClient(base_url="http://bp-test") as client:
                resolver = SkillResolver(bp_base_url="http://bp-test", http_client=client)
                ctx = await resolver.resolve_skills(
                    "con-test-cp01",
                    [SkillAssignment("content_publish", "1.0.0")],
                )

        executor = SessionExecutor(session_ctx=ctx)

        # Before crystallization — blocked
        with pytest.raises(CrystallizerRequiredError):
            await executor.check_and_dispatch("meta.post_content", {})

        # After crystallization — allowed
        artifact = LockedArtifact(
            skill_id="content_publish",
            artifact_type="campaign_brief",
            content={"approved": True},
            approval_evidence_id="evidence-cp01",
        )
        executor.add_locked_artifact("content_publish", artifact)

        result = await executor.check_and_dispatch("meta.post_content", {"text": "Hello"})
        assert result is not None


# ─── CCT-SKILL-CP-02 ─────────────────────────────────────────────────────────
# Tool call without LockedArtifact → CrystallizerRequiredError → CONSTITUTIONAL_BLOCKED


class TestCCT_SKILL_CP_02:
    """CCT-SKILL-CP-02: Tool call without LockedArtifact raises CrystallizerRequiredError.

    ADR-043 §3: any tool call in a crystallizer-enabled skill's tool set is blocked
    until IntentCrystallizer completes and customer approves.
    Maps to MCPToolError(CONSTITUTIONAL_BLOCKED) in the caller.
    """

    @pytest.fixture
    def content_publish_ctx(self) -> SessionSkillContext:
        ctx = SessionSkillContext()
        for tool in ["meta.post_content", "meta.post_story", "instagram.post_reel"]:
            ctx.authorized_tools.add(tool)
            ctx.dcm_categories[tool] = "DETERMINISTIC_REQUIRED"
            ctx.tool_skill_index[tool] = "content_publish"
        ctx.crystallizer_configs["content_publish"] = CrystallizerConfig(
            enabled=True,
            prompt_template="skills/content_publish/crystallizer_v1.md",
            requires_customer_approval=True,
        )
        ctx.autonomy_levels["content_publish"] = "APPROVAL_REQUIRED"
        return ctx

    @pytest.mark.asyncio
    async def test_publish_tool_blocked_without_locked_artifact(
        self, content_publish_ctx: SessionSkillContext
    ) -> None:
        """meta.post_content blocked → CrystallizerRequiredError (no artifact yet)."""
        executor = SessionExecutor(session_ctx=content_publish_ctx)

        with pytest.raises(CrystallizerRequiredError) as exc_info:
            await executor.check_and_dispatch("meta.post_content", {})

        assert exc_info.value.skill_id == "content_publish"
        assert exc_info.value.tool_name == "meta.post_content"

    @pytest.mark.asyncio
    async def test_all_content_publish_tools_blocked_without_artifact(
        self, content_publish_ctx: SessionSkillContext
    ) -> None:
        """All three content_publish tools blocked before crystallization."""
        executor = SessionExecutor(session_ctx=content_publish_ctx)

        for tool in ["meta.post_content", "meta.post_story", "instagram.post_reel"]:
            with pytest.raises(CrystallizerRequiredError):
                await executor.check_and_dispatch(tool, {})

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_authorization_error_not_crystallizer_error(
        self, content_publish_ctx: SessionSkillContext
    ) -> None:
        """Tool not in authorized_tools → C041ToolAuthorizationError (not crystallizer error)."""
        executor = SessionExecutor(session_ctx=content_publish_ctx)

        with pytest.raises(C041ToolAuthorizationError):
            await executor.check_and_dispatch("youtube.upload_video", {})


# ─── CCT-SKILL-CP-03 ─────────────────────────────────────────────────────────
# CE.ValidateAction called for every tool call with correct dcm_category


class TestCCT_SKILL_CP_03:
    """CCT-SKILL-CP-03: CE.ValidateAction called with skill's declared dcm_category.

    ADR-043 §3: SessionExecutor passes dcm_category from SessionSkillContext.dcm_categories
    to the downstream dispatcher. The dispatcher (CTG in production) forwards it to CE.
    ADR-042: CE uses dcm_category to apply the correct constitutional enforcement rules.
    """

    @pytest.fixture
    def crystallized_ctx(self) -> SessionSkillContext:
        ctx = SessionSkillContext()
        for tool in ["meta.post_content", "meta.post_story", "instagram.post_reel"]:
            ctx.authorized_tools.add(tool)
            ctx.dcm_categories[tool] = "DETERMINISTIC_REQUIRED"
            ctx.tool_skill_index[tool] = "content_publish"
        # No crystallizer config → tools are unblocked (Gate 2 skipped)
        return ctx

    @pytest.mark.asyncio
    async def test_dispatcher_receives_correct_dcm_category(
        self, crystallized_ctx: SessionSkillContext
    ) -> None:
        """Dispatcher called with dcm_category=DETERMINISTIC_REQUIRED from skill definition."""
        calls: list[dict[str, Any]] = []

        class RecordingDispatcher:
            async def dispatch(
                self, tool_name: str, params: dict, dcm_category: str, skill_id: str
            ) -> dict:
                calls.append({
                    "tool_name": tool_name,
                    "dcm_category": dcm_category,
                    "skill_id": skill_id,
                })
                return {"status": "ok"}

        executor = SessionExecutor(
            session_ctx=crystallized_ctx,
            dispatcher=RecordingDispatcher(),
        )

        await executor.check_and_dispatch("meta.post_content", {"text": "Hello"})

        assert len(calls) == 1
        assert calls[0]["tool_name"] == "meta.post_content"
        assert calls[0]["dcm_category"] == "DETERMINISTIC_REQUIRED", (
            "CCT-SKILL-CP-03: dcm_category must be passed from skill definition to dispatcher "
            "so CE applies DETERMINISTIC_REQUIRED enforcement rules"
        )
        assert calls[0]["skill_id"] == "content_publish"

    @pytest.mark.asyncio
    async def test_every_tool_call_dispatches_with_dcm_category(
        self, crystallized_ctx: SessionSkillContext
    ) -> None:
        """All three tools in content_publish dispatch with DETERMINISTIC_REQUIRED."""
        calls: list[str] = []

        class RecordingDispatcher:
            async def dispatch(
                self, tool_name: str, params: dict, dcm_category: str, skill_id: str
            ) -> dict:
                calls.append(dcm_category)
                return {}

        executor = SessionExecutor(session_ctx=crystallized_ctx, dispatcher=RecordingDispatcher())

        for tool in ["meta.post_content", "meta.post_story", "instagram.post_reel"]:
            await executor.check_and_dispatch(tool, {})

        assert all(c == "DETERMINISTIC_REQUIRED" for c in calls), (
            "CCT-SKILL-CP-03: every tool in content_publish must carry DETERMINISTIC_REQUIRED"
        )
        assert len(calls) == 3


class TestTrialCapabilities:
    @pytest.mark.asyncio
    async def test_trial_denies_authorized_tool_not_explicitly_trial_safe(self) -> None:
        context = SessionSkillContext(
            authorized_tools={"provider.publish", "local.simulate"},
            trial_safe_tools={"local.simulate"},
            dcm_categories={
                "provider.publish": "DETERMINISTIC_REQUIRED",
                "local.simulate": "DETERMINISTIC_REQUIRED",
            },
        )
        executor = SessionExecutor(
            context,
            trial_mode=True,
            trial_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

        with pytest.raises(TrialCapabilityDeniedError):
            await executor.check_and_dispatch("provider.publish", {})
        result = await executor.check_and_dispatch("local.simulate", {})
        assert result["status"] == "dispatched"

    @pytest.mark.asyncio
    async def test_expired_trial_blocks_new_work_and_preserves_approved_artifact(self) -> None:
        context = SessionSkillContext(
            authorized_tools={"local.simulate"},
            trial_safe_tools={"local.simulate"},
        )
        executor = SessionExecutor(
            context,
            trial_mode=True,
            trial_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        artifact = LockedArtifact(
            skill_id="fixture",
            artifact_type="trial_plan",
            content={"approved": True},
            approval_evidence_id="evidence-1",
        )
        executor.add_locked_artifact("fixture", artifact)

        with pytest.raises(TrialExpiredError):
            await executor.check_and_dispatch("local.simulate", {})

        assert executor.get_locked_artifact("fixture") is artifact

    @pytest.mark.asyncio
    async def test_trial_without_owner_confirmed_expiry_fails_closed(self) -> None:
        context = SessionSkillContext(
            authorized_tools={"local.simulate"},
            trial_safe_tools={"local.simulate"},
        )
        executor = SessionExecutor(context, trial_mode=True)

        with pytest.raises(TrialEntitlementUnavailableError):
            await executor.check_and_dispatch("local.simulate", {})

    @pytest.mark.asyncio
    async def test_manifest_trial_tools_must_also_be_authorized(self) -> None:
        context = SessionSkillContext()
        _merge_into_context(context, "fixture", {
            "tools": ["local.simulate"],
            "trial_safe_tools": ["local.simulate", "provider.mutate"],
        })
        assert context.trial_safe_tools == {"local.simulate"}
