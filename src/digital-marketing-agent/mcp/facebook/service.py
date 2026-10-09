"""Facebook provider translation behind the closed social tool contract."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §8.2, §8.2.1
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-078, ADR-020, ADR-021

from __future__ import annotations

from mcp.common import CeValidator, PurposeBoundTokenBroker, SocialToolContext, require_ready_credential


class FacebookMcp:
    operations = frozenset({"facebook.post_content", "facebook.get_publish_status", "facebook.delete_content"})

    def __init__(self, ce: CeValidator, tokens: PurposeBoundTokenBroker) -> None:
        self._ce = ce
        self._tokens = tokens

    def call(self, operation: str, context: SocialToolContext) -> dict[str, str]:
        if operation not in self.operations:
            raise ValueError("INVALID_REQUEST")
        self._ce.validate(operation, context)
        require_ready_credential(
            self._tokens,
            context,
            purpose=operation,
            required_scopes=frozenset({"pages_manage_posts"}),
        )
        self._tokens.consume(
            tenant_ref=context.tenant_authority_ref,
            relationship_ref=context.relationship_ref,
            account_ref=context.channel_account_ref,
            purpose=operation,
            operation_id=context.operation_id,
        )
        return {
            "state": "PUBLISHED" if operation.endswith("post_content") else "NOT_FOUND_UNPROVEN",
            "correlation": f"facebook-emulator:{context.intent_id}",
            "receiptDigest": context.canonical_request_digest,
            "capabilityProfileVersion": context.capability_profile_version,
        }
