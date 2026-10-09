"""Read-only deterministic social observation MCP."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §8.2, §9
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-078, ADR-020, ADR-021

from __future__ import annotations

from mcp.common import CeValidator, PurposeBoundTokenBroker, SocialToolContext, require_ready_credential


class PlatformAnalyticsMcp:
    operations = frozenset(
        {"platform_analytics.get_instagram_insights", "platform_analytics.get_facebook_insights"}
    )

    def __init__(self, ce: CeValidator, tokens: PurposeBoundTokenBroker) -> None:
        self._ce = ce
        self._tokens = tokens

    def call(self, operation: str, context: SocialToolContext) -> dict[str, object]:
        if operation not in self.operations:
            raise ValueError("INVALID_REQUEST")
        self._ce.validate(operation, context)
        scopes = (
            frozenset({"instagram_manage_insights"})
            if "instagram" in operation
            else frozenset({"read_insights"})
        )
        require_ready_credential(self._tokens, context, purpose=operation, required_scopes=scopes)
        self._tokens.consume(
            tenant_ref=context.tenant_authority_ref,
            relationship_ref=context.relationship_ref,
            account_ref=context.channel_account_ref,
            purpose=operation,
            operation_id=context.operation_id,
        )
        return {
            "state": "AVAILABLE",
            "observations": [],
            "limitations": ["Deterministic emulator contains no live analytics."],
            "capabilityProfileVersion": context.capability_profile_version,
        }
