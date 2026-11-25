# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R008
# Implements: work-contracts/WC-170-real-agent-work-end-to-end.md gap B5
# Constitutional basis: C-023, C-059, C-063, C-088
"""Spend evidence is verified at its owner, never trusted from the caller.

The Business Platform owns the real-work record store: the locked artifact, the customer's two decisions and the
execution timeline. The billing engine asks the owner whether the evidence a signed caller names really exists and
says what the caller claims it says. The owner answers through functions it owns in the database, so the billing
engine reads no table of the owner directly. Anything the owner cannot confirm is refused, and so is an owner that
cannot be asked.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceOwner(Protocol):
    async def confirm_authorization(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        artifact_id: UUID,
        artifact_digest: str,
        approval_evidence_id: UUID,
        scope_evidence_id: UUID,
    ) -> bool:
        """The artifact is locked at this digest and not superseded, and the two decision records exist for it."""
        raise NotImplementedError

    async def confirm_provider_proof(
        self, tenant_id: UUID, relationship_id: UUID, work_item_id: UUID, provider_reference: str, evidence_id: UUID
    ) -> bool:
        """The evidence is a timeline event of this work item that carries the provider's own reference."""
        raise NotImplementedError


class SqlEvidenceOwner:
    """Asks the owner's verification functions (see 99zzzzzzzz-wc172-02-evidence-owner.sql)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def confirm_authorization(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        artifact_id: UUID,
        artifact_digest: str,
        approval_evidence_id: UUID,
        scope_evidence_id: UUID,
    ) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT business.real_work_authorization_evidence_ok("
                    ":tenant, :relationship, :artifact, :digest, :approval, :scope)"
                ),
                {
                    "tenant": tenant_id, "relationship": relationship_id, "artifact": artifact_id,
                    "digest": artifact_digest, "approval": approval_evidence_id, "scope": scope_evidence_id,
                },
            )
        ).first()
        return bool(row and row[0])

    async def confirm_provider_proof(
        self, tenant_id: UUID, relationship_id: UUID, work_item_id: UUID, provider_reference: str, evidence_id: UUID
    ) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT business.real_work_provider_proof_ok(:tenant, :relationship, :event, :item, :reference)"
                ),
                {
                    "tenant": tenant_id, "relationship": relationship_id, "event": evidence_id,
                    "item": work_item_id, "reference": provider_reference,
                },
            )
        ).first()
        return bool(row and row[0])
