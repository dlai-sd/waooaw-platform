"""Instagram provider translation behind the closed social tool contract."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §8.2, §8.2.1
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-078, ADR-020, ADR-021

from __future__ import annotations

from mcp.common import CeValidator, PurposeBoundTokenBroker, SocialToolContext, require_ready_credential


class InstagramMcp:
    operations = frozenset({"instagram.post_content", "instagram.get_publish_status", "instagram.delete_content"})

    def __init__(self, ce: CeValidator, tokens: PurposeBoundTokenBroker) -> None:
        self._ce = ce
        self._tokens = tokens

    def call(self, operation: str, context: SocialToolContext) -> dict[str, str]:
        if operation not in self.operations:
            raise ValueError("INVALID_REQUEST")
        self._ce.validate(operation, context)
        purpose = operation
        require_ready_credential(
            self._tokens,
            context,
            purpose=purpose,
            required_scopes=frozenset({"instagram_content_publish"}),
        )
        self._tokens.consume(
            tenant_ref=context.tenant_authority_ref,
            relationship_ref=context.relationship_ref,
            account_ref=context.channel_account_ref,
            purpose=purpose,
            operation_id=context.operation_id,
        )
        return {
            "state": "PROCESSING" if operation.endswith("post_content") else "NOT_FOUND_UNPROVEN",
            "correlation": f"instagram-emulator:{context.intent_id}",
            "capabilityProfileVersion": context.capability_profile_version,
        }
