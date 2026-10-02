"""AS-PSE: governed provider failover acceptance."""

# Implements: WC110-R008; ADR-029 PSE-R07 and Dispatch + Outcome Recording
# Constitutional basis: C-041, C-051, C-059, C-063, C-069

from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/ai-runtime"))
sys.path.insert(0, str(ROOT / "src/trust-layer"))

from ctg.models import GatewayResult, MCPToolError  # noqa: E402
from pse.router import route_and_dispatch  # noqa: E402
from pse.tiers import LlmTier  # noqa: E402


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_gemini_rate_limit_falls_back_to_azure_with_evidence() -> None:
    gateway = AsyncMock()
    gateway.call.side_effect = [
        GatewayResult(
            decision_id="DEC-GEMINI",
            error=MCPToolError(
                code="RATE_LIMIT",
                message="Provider rate limit exceeded",
                retry_eligible=True,
            ),
        ),
        GatewayResult(
            decision_id="DEC-AZURE",
            result={
                "tier": LlmTier.FRONTIER.value,
                "provider_id": "azure",
                "model_id": "gpt-4o",
                "response": "Synthetic governed response",
                "done": True,
            },
        ),
    ]
    primary_event_id = UUID("10000000-0000-0000-0000-000000000001")
    fallback_event_id = UUID("20000000-0000-0000-0000-000000000002")
    record = AsyncMock()

    with (
        patch("pse.router._make_gateway", return_value=gateway),
        patch("pse.router.uuid.uuid4", side_effect=[primary_event_id, fallback_event_id]),
        patch("pse.router._record_dispatch_event", record),
    ):
        result = await route_and_dispatch(
            prompt="Synthetic prompt content that must not enter evidence",
            task_complexity="complex",
            language="en",
            async_session_factory=MagicMock(),
            customer_id="30000000-0000-0000-0000-000000000003",
        )

    assert [call.args[1]["provider"] for call in gateway.call.await_args_list] == ["google", "azure"]
    assert [call.args[1]["model"] for call in gateway.call.await_args_list] == ["gemini-2.5-pro", "gpt-4o"]
    assert result == {
        "tier": LlmTier.FRONTIER.value,
        "provider_id": "azure",
        "model_id": "gpt-4o",
        "response": "Synthetic governed response",
        "done": True,
        "event_id": str(fallback_event_id),
    }
    assert record.await_count == 2
    assert record.await_args_list[0].args[1:8] == (
        str(primary_event_id),
        LlmTier.FRONTIER,
        "google",
        "gemini-2.5-pro",
        "complex",
        "en",
        "failed",
    )
    assert record.await_args_list[1].args[1:8] == (
        str(fallback_event_id),
        LlmTier.FRONTIER,
        "azure",
        "gpt-4o",
        "complex",
        "en",
        "success",
    )
    assert all("Synthetic prompt content" not in str(call.args) for call in record.await_args_list)
