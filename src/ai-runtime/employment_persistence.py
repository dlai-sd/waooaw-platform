"""Tenant-scoped PostgreSQL persistence for AIR employment proposals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import asyncpg


@dataclass(frozen=True)
class StoredProposal:
    tenant_id: str
    relationship_ref: str
    proposal_id: UUID
    idempotency_key: UUID
    request_digest: str
    proposal_json: dict[str, Any]


class EmploymentPatchRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> EmploymentPatchRepository:
        dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return cls(await asyncpg.create_pool(dsn, min_size=1, max_size=5))

    async def close(self) -> None:
        await self._pool.close()

    async def find_by_idempotency(
        self,
        tenant_id: str,
        relationship_ref: str,
        idempotency_key: UUID,
    ) -> StoredProposal | None:
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)",
                tenant_id,
            )
            row = await connection.fetchrow(
                """
                SELECT tenant_id, relationship_ref, proposal_id, idempotency_key,
                       request_digest, proposal_json
                FROM ai_runtime.employment_patch_proposals
                WHERE tenant_id = $1::uuid
                  AND relationship_ref = $2
                  AND idempotency_key = $3
                """,
                tenant_id,
                relationship_ref,
                idempotency_key,
            )
        return self._stored(row) if row is not None else None

    async def get(
        self,
        tenant_id: str,
        proposal_id: UUID,
    ) -> StoredProposal | None:
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)",
                tenant_id,
            )
            row = await connection.fetchrow(
                """
                SELECT tenant_id, relationship_ref, proposal_id, idempotency_key,
                       request_digest, proposal_json
                FROM ai_runtime.employment_patch_proposals
                WHERE tenant_id = $1::uuid AND proposal_id = $2
                """,
                tenant_id,
                proposal_id,
            )
        return self._stored(row) if row is not None else None

    async def save(
        self,
        tenant_id: str,
        relationship_ref: str,
        idempotency_key: UUID,
        request_digest: str,
        receipt: dict[str, Any],
        proposal: dict[str, Any],
    ) -> None:
        proposal_id = UUID(proposal["proposalId"])
        state = proposal["state"]
        result = proposal if state == "PROPOSED" else None
        reason_code = proposal.get("reasonCode")
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)",
                tenant_id,
            )
            await connection.execute(
                """
                INSERT INTO ai_runtime.employment_patch_proposals (
                    tenant_id, relationship_ref, proposal_id, idempotency_key,
                    request_digest, protocol_version,
                    semantic_catalogue_version, semantic_catalogue_digest,
                    prompt_policy_version, prompt_policy_digest,
                    model_policy_version, model_policy_digest,
                    receipt_json, proposal_json
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12, $13::jsonb, $14::jsonb
                )
                """,
                tenant_id,
                relationship_ref,
                proposal_id,
                idempotency_key,
                request_digest,
                proposal["protocolVersion"],
                proposal["semanticCatalogue"]["version"],
                proposal["semanticCatalogue"]["digest"],
                proposal["promptPolicy"]["version"],
                proposal["promptPolicy"]["digest"],
                proposal["modelPolicy"]["version"],
                proposal["modelPolicy"]["digest"],
                json.dumps(receipt),
                json.dumps(proposal),
            )
            await connection.execute(
                """
                INSERT INTO ai_runtime.employment_patch_proposal_events (
                    tenant_id, relationship_ref, proposal_id, event_sequence,
                    state, result_json, reason_code
                ) VALUES ($1::uuid, $2, $3, 1, $4, $5::jsonb, $6)
                """,
                tenant_id,
                relationship_ref,
                proposal_id,
                state,
                json.dumps(result) if result is not None else None,
                reason_code,
            )

    @staticmethod
    def _stored(row: asyncpg.Record) -> StoredProposal:
        raw = row["proposal_json"]
        proposal_json = json.loads(raw) if isinstance(raw, str) else dict(raw)
        return StoredProposal(
            tenant_id=str(row["tenant_id"]),
            relationship_ref=row["relationship_ref"],
            proposal_id=row["proposal_id"],
            idempotency_key=row["idempotency_key"],
            request_digest=row["request_digest"],
            proposal_json=proposal_json,
        )
