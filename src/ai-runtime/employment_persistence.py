# Implements: architecture/reference/components/conversational-employment-ai-runtime-solution.md §Persistence
"""Tenant-scoped PostgreSQL persistence for AIR employment proposals."""

from __future__ import annotations

import json
import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import asyncpg


class DatabaseConnection(Protocol):
    async def execute(self, query: str, *args: Any) -> str: ...

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None: ...

    async def fetchval(self, query: str, *args: Any) -> Any: ...


class EmploymentDispatchStoppedError(RuntimeError):
    """The durable relationship Stop barrier prohibits dispatch or result release."""


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

    @property
    def pool(self) -> asyncpg.Pool:
        return self._pool

    @classmethod
    async def connect(cls, database_url: str) -> EmploymentPatchRepository:
        dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return cls(await asyncpg.create_pool(dsn, min_size=1, max_size=5))

    async def close(self) -> None:
        await self._pool.close()

    @asynccontextmanager
    async def serialize_proposal(
        self, tenant_id: str, relationship_ref: str, idempotency_key: UUID
    ) -> AsyncIterator[EmploymentPatchTransaction]:
        identity = json.dumps(
            [str(UUID(tenant_id)), relationship_ref, str(idempotency_key)], separators=(",", ":"), ensure_ascii=False
        ).encode()
        lock_key = int.from_bytes(hashlib.sha256(identity).digest()[:8], "big", signed=True)
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute("SELECT set_config('app.current_tenant_id', $1, true)", tenant_id)
            await connection.execute("SELECT ai_runtime.lock_employment_dispatch($1::uuid, $2)", tenant_id, relationship_ref)
            await EmploymentPatchTransaction(connection).ensure_not_stopped(tenant_id, relationship_ref)
            await connection.execute("SELECT pg_advisory_xact_lock($1::bigint)", lock_key)
            yield EmploymentPatchTransaction(connection)

    async def find_by_idempotency(
        self,
        tenant_id: str,
        relationship_ref: str,
        idempotency_key: UUID,
    ) -> StoredProposal | None:
        async with self.serialize_proposal(tenant_id, relationship_ref, idempotency_key) as transaction:
            return await transaction.find_by_idempotency(tenant_id, relationship_ref, idempotency_key)

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
            if row is not None:
                await connection.execute(
                    "SELECT ai_runtime.lock_employment_dispatch($1::uuid, $2)",
                    tenant_id,
                    row["relationship_ref"],
                )
                await EmploymentPatchTransaction(connection).ensure_not_stopped(tenant_id, row["relationship_ref"])
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
        async with self.serialize_proposal(tenant_id, relationship_ref, idempotency_key) as transaction:
            await transaction.save(tenant_id, relationship_ref, idempotency_key, request_digest, receipt, proposal)

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


class EmploymentPatchTransaction:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def ensure_not_stopped(self, tenant_id: str, relationship_ref: str) -> None:
        row = await self._connection.fetchrow(
            """SELECT relationship_ref FROM constitutional.employment_dispatch_stops
               WHERE tenant_id = $1::uuid
                 AND relationship_ref = ai_runtime.employment_dispatch_relationship_key($2)""",
            tenant_id,
            relationship_ref,
        )
        if row is not None:
            raise EmploymentDispatchStoppedError("Employment dispatch is stopped")

    async def find_by_idempotency(self, tenant_id: str, relationship_ref: str, idempotency_key: UUID) -> StoredProposal | None:
        row = await self._connection.fetchrow(
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
        return EmploymentPatchRepository._stored(row) if row is not None else None

    async def claim_dispatch(
        self, tenant_id: str, relationship_ref: str, idempotency_key: UUID, request_digest: str, recovery_mode: str
    ) -> tuple[bool, str, str]:
        row = await self._connection.fetchrow(
            """
            INSERT INTO ai_runtime.employment_patch_dispatch_claims
                (tenant_id, relationship_ref, idempotency_key, request_digest, recovery_mode)
            VALUES ($1::uuid, $2, $3, $4, $5)
            ON CONFLICT (tenant_id, relationship_ref, idempotency_key) DO NOTHING
            RETURNING request_digest, recovery_mode
            """,
            tenant_id,
            relationship_ref,
            idempotency_key,
            request_digest,
            recovery_mode,
        )
        if row is not None:
            return True, str(row["request_digest"]), str(row["recovery_mode"])
        existing = await self._connection.fetchrow(
            """
            SELECT request_digest, recovery_mode FROM ai_runtime.employment_patch_dispatch_claims
            WHERE tenant_id = $1::uuid AND relationship_ref = $2 AND idempotency_key = $3
            """,
            tenant_id,
            relationship_ref,
            idempotency_key,
        )
        if existing is None:
            raise RuntimeError("Dispatch claim disappeared during serialization")
        return False, str(existing["request_digest"]), str(existing["recovery_mode"])

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
        await self._connection.execute(
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
        await self._connection.execute(
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
