"""WC-117 deterministic social MCP and credential tests."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §6, §8, §14
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-076, C-078, ADR-020, ADR-021

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from mcp.common import (
    CredentialHealth,
    DeterministicTokenBroker,
    SocialToolContext,
    SocialToolDenied,
    require_configured_reference,
)
from mcp.facebook import FacebookMcp
from mcp.instagram import InstagramMcp
from mcp.platform_analytics import PlatformAnalyticsMcp
from mcp.server import create_app

NOW = datetime.now(timezone.utc)


class Ce:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def validate(self, action: str, context: SocialToolContext) -> None:
        del context
        self.actions.append(action)


def context(channel: str = "FACEBOOK") -> SocialToolContext:
    return SocialToolContext(
        operation_id="operation-1",
        intent_id="intent-1",
        idempotency_key="key-1",
        canonical_request_digest="sha256:" + "a" * 64,
        tenant_authority_ref="tenant-1",
        relationship_ref="relationship-1",
        agent_instance_ref="dma-1",
        channel=channel,
        channel_account_ref="account-1",
        credential_ref_version="oauthref://tenant-1/relationship-1/meta/account-1?v=1",
        decision_space_version="1",
        ce_evidence_ref="ce-1",
        wbe_eligibility_version="1",
        capability_profile_version="meta-emulator-v1",
        requested_at=NOW,
        deadline_at=NOW + timedelta(minutes=1),
        trace_id="trace-1",
    )


@pytest.mark.parametrize(
    "value",
    ("", "CHANGEME", "fixture", "https://provider.invalid/key", "secretref://{environment}/key"),
)
def test_placeholder_references_are_not_configured(value: str) -> None:
    with pytest.raises(SocialToolDenied, match="NOT_CONFIGURED"):
        require_configured_reference(value)


def test_exact_eight_operations_and_ce_before_purpose_bound_token_consumption() -> None:
    ce = Ce()
    token = DeterministicTokenBroker(
        CredentialHealth(
            state="VALID",
            credential_ref="opaque-ref",
            token_version="1",
            scopes=frozenset(
                {
                    "instagram_content_publish",
                    "pages_manage_posts",
                    "instagram_manage_insights",
                    "read_insights",
                }
            ),
            account_ref="account-1",
            expires_at=NOW + timedelta(hours=1),
        )
    )
    instagram = InstagramMcp(ce, token)
    facebook = FacebookMcp(ce, token)
    analytics = PlatformAnalyticsMcp(ce, token)
    operations = instagram.operations | facebook.operations | analytics.operations

    assert len(operations) == 8
    assert instagram.call("instagram.post_content", context("INSTAGRAM"))["state"] == "PROCESSING"
    assert facebook.call("facebook.post_content", context())["state"] == "PUBLISHED"
    assert analytics.call("platform_analytics.get_facebook_insights", context())["state"] == "AVAILABLE"
    assert ce.actions == token.consumed_purposes


def test_wrong_scope_fails_before_token_consumption() -> None:
    ce = Ce()
    token = DeterministicTokenBroker(
        CredentialHealth(
            state="VALID",
            credential_ref="opaque-ref",
            token_version="1",
            scopes=frozenset(),
            account_ref="account-1",
            expires_at=NOW + timedelta(hours=1),
        )
    )

    with pytest.raises(SocialToolDenied, match="SCOPE_INSUFFICIENT"):
        FacebookMcp(ce, token).call("facebook.post_content", context())
    assert ce.actions == ["facebook.post_content"]
    assert token.consumed_purposes == []


def test_emulator_wire_request_is_validated_and_translated() -> None:
    payload = {
        "operation_id": "operation-1",
        "intent_id": "intent-1",
        "idempotency_key": "key-1",
        "canonical_request_digest": "sha256:" + "a" * 64,
        "tenant_authority_ref": "tenant-1",
        "relationship_ref": "relationship-1",
        "agent_instance_ref": "dma-1",
        "channel": "INSTAGRAM",
        "channel_account_ref": "emulator-account",
        "credential_ref_version": "oauthref://tenant-1/relationship-1/meta/emulator-account?v=1",
        "decision_space_version": "1",
        "ce_evidence_ref": "ce-1",
        "wbe_eligibility_version": "1",
        "capability_profile_version": "meta-emulator-v1",
        "requested_at": NOW.isoformat(),
        "deadline_at": (NOW + timedelta(minutes=1)).isoformat(),
        "trace_id": "trace-1",
    }
    client = TestClient(create_app("instagram-mcp"))

    response = client.post("/call/instagram.post_content", json=payload)

    assert response.status_code == 200
    assert response.json()["state"] == "PROCESSING"
    assert client.post("/call/instagram.post_content", json={**payload, "unexpected": True}).status_code == 422
