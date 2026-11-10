# Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.2
"""AIR-only durable generation claims, with the existing constitutional Stop barrier."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg

from conversation_generation import GenerationRequest, GenerationResult
from employment_persistence import DatabaseConnection, EmploymentDispatchStoppedError


class ConversationGenerationStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def _lock(self, connection: DatabaseConnection, tenant: str, relationship: UUID) -> None:
        await connection.execute("SELECT set_config('app.current_tenant_id', $1, true)", tenant)
        await connection.execute("SELECT ai_runtime.lock_employment_dispatch($1::uuid, $2)", tenant, str(relationship))
        if await connection.fetchval(
            "SELECT EXISTS(SELECT 1 FROM constitutional.employment_dispatch_stops WHERE tenant_id = $1::uuid "
            "AND relationship_ref = ai_runtime.employment_dispatch_relationship_key($2))",
            tenant,
            str(relationship),
        ):
            raise EmploymentDispatchStoppedError("Generation stopped")

    @staticmethod
    def _result(row: asyncpg.Record, request: GenerationRequest) -> GenerationResult | None:
        if row["request_digest"] != request.request_digest or row["execution_id"] != request.execution_id:
            raise ValueError("Generation idempotency binding conflict")
        raw = row["result_json"]
        return GenerationResult.model_validate(json.loads(raw) if isinstance(raw, str) else raw) if raw is not None else None

    async def lookup(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> GenerationResult | None:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            row = await connection.fetchrow(
                "SELECT execution_id, request_digest, result_json, dispatch_claimed FROM ai_runtime.conversation_generations "
                "WHERE tenant_id = $1::uuid AND relationship_id = $2 AND idempotency_key = $3",
                tenant,
                relationship,
                key,
            )
            return self._result(row, request) if row is not None else None

    async def lookup_retained(
        self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest
    ) -> tuple[GenerationResult | None, datetime | None]:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            row = await connection.fetchrow(
                "SELECT execution_id, request_digest, result_json, completed_at FROM ai_runtime.conversation_generations "
                "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3",
                tenant,
                relationship,
                key,
            )
            return (self._result(row, request), row["completed_at"]) if row is not None else (None, None)

    async def claim(
        self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest
    ) -> tuple[bool, GenerationResult | None]:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            row = await connection.fetchrow(
                "INSERT INTO ai_runtime.conversation_generations(tenant_id, relationship_id, idempotency_key, execution_id, request_digest, admission_claimed) "
                "VALUES ($1::uuid,$2,$3,$4,$5,true) ON CONFLICT DO NOTHING RETURNING execution_id",
                tenant,
                relationship,
                key,
                request.execution_id,
                request.request_digest,
            )
            if row is not None:
                return True, None
            retained = await connection.fetchrow(
                "SELECT execution_id, request_digest, result_json, dispatch_claimed FROM ai_runtime.conversation_generations "
                "WHERE tenant_id = $1::uuid AND relationship_id = $2 AND idempotency_key = $3",
                tenant,
                relationship,
                key,
            )
            if retained is None:
                raise ValueError("Generation claim conflicts with another original execution")
            result = self._result(retained, request)
            acquired = await connection.fetchval(
                "UPDATE ai_runtime.conversation_generations SET admission_claimed=true "
                "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3 "
                "AND execution_id=$4 AND request_digest=$5 AND NOT admission_claimed "
                "AND NOT dispatch_claimed AND result_json IS NULL RETURNING true",
                tenant,
                relationship,
                key,
                request.execution_id,
                request.request_digest,
            )
            return acquired is True, result

    async def release_queue_claim(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> None:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            released = await connection.fetchval(
                "UPDATE ai_runtime.conversation_generations SET admission_claimed=false "
                "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3 "
                "AND execution_id=$4 AND request_digest=$5 AND admission_claimed "
                "AND NOT dispatch_claimed AND result_json IS NULL RETURNING true",
                tenant,
                relationship,
                key,
                request.execution_id,
                request.request_digest,
            )
            if released is not True:
                raise ValueError("Queued generation has no exact pre-dispatch admission claim")

    async def begin_dispatch(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> bool:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            return (
                await connection.fetchval(
                    "UPDATE ai_runtime.conversation_generations SET dispatch_claimed=true "
                    "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3 "
                    "AND execution_id=$4 AND request_digest=$5 AND admission_claimed AND NOT dispatch_claimed AND result_json IS NULL RETURNING true",
                    tenant,
                    relationship,
                    key,
                    request.execution_id,
                    request.request_digest,
                )
                is True
            )

    async def save(self, tenant: str, relationship: UUID, key: UUID, result: GenerationResult) -> None:
        async with self.pool.acquire() as connection, connection.transaction():
            await self._lock(connection, tenant, relationship)
            row = await connection.fetchrow(
                "SELECT execution_id, request_digest, result_json FROM ai_runtime.conversation_generations "
                "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3 FOR UPDATE",
                tenant,
                relationship,
                key,
            )
            if row is None or row["execution_id"] != result.execution_id or row["request_digest"] != result.request_digest:
                raise ValueError("Generation result has no exact original claim")
            if row["result_json"] is not None:
                prior = json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"]
                if prior != result.model_dump(by_alias=True, mode="json"):
                    raise ValueError("Generation result cannot replace an earlier outcome")
                return
            await connection.execute(
                "UPDATE ai_runtime.conversation_generations SET result_json=$4::jsonb, completed_at=clock_timestamp() "
                "WHERE tenant_id=$1::uuid AND relationship_id=$2 AND idempotency_key=$3",
                tenant,
                relationship,
                key,
                result.model_dump_json(by_alias=True),
            )
