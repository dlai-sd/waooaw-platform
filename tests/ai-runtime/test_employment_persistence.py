from __future__ import annotations

import json
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import UUID

import pytest

from employment_persistence import EmploymentDispatchStoppedError, EmploymentPatchRepository

TENANT_ID = "00000000-0000-0000-0000-000000000001"
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000002")
IDEMPOTENCY_KEY = UUID("00000000-0000-0000-0000-000000000003")


class _Context(AbstractAsyncContextManager[Any]):
    def __init__(self, value: Any) -> None:
        self.value = value

    async def __aenter__(self) -> Any:
        return self.value

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeConnection:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self.row = row
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> _Context:
        return _Context(self)

    async def execute(self, statement: str, *values: object) -> str:
        self.executions.append((statement, values))
        return "INSERT 0 1"

    async def fetchrow(self, statement: str, *values: object) -> dict[str, Any] | None:
        self.executions.append((statement, values))
        if "employment_dispatch_stops" in statement:
            return None
        return self.row


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.closed = False

    def acquire(self) -> _Context:
        return _Context(self.connection)

    async def close(self) -> None:
        self.closed = True


def _proposal() -> dict[str, Any]:
    reference = {"ref": "policy", "version": "1", "digest": "a" * 64}
    return {
        "proposalId": str(PROPOSAL_ID),
        "protocolVersion": "1.0-candidate",
        "semanticCatalogue": reference,
        "promptPolicy": reference,
        "modelPolicy": reference,
        "state": "PROPOSED",
    }


def _row(proposal: dict[str, Any] | str) -> dict[str, Any]:
    return {
        "tenant_id": UUID(TENANT_ID),
        "relationship_ref": "relationship-1",
        "proposal_id": PROPOSAL_ID,
        "idempotency_key": IDEMPOTENCY_KEY,
        "request_digest": "b" * 64,
        "proposal_json": proposal,
    }


@pytest.mark.asyncio
async def test_repository_reads_restart_state_under_transaction_tenant_context() -> None:
    connection = FakeConnection(_row(_proposal()))
    repository = EmploymentPatchRepository(FakePool(connection))

    by_key = await repository.find_by_idempotency(
        TENANT_ID,
        "relationship-1",
        IDEMPOTENCY_KEY,
    )
    by_id = await repository.get(TENANT_ID, PROPOSAL_ID)

    assert by_key is not None
    assert by_id == by_key
    assert by_key.proposal_json["state"] == "PROPOSED"
    assert sum("set_config" in statement for statement, _ in connection.executions) == 2


@pytest.mark.asyncio
async def test_repository_writes_identity_and_terminal_event_atomically() -> None:
    connection = FakeConnection()
    pool = FakePool(connection)
    repository = EmploymentPatchRepository(pool)
    receipt = {"proposalId": str(PROPOSAL_ID), "state": "PENDING"}

    await repository.save(
        TENANT_ID,
        "relationship-1",
        IDEMPOTENCY_KEY,
        "b" * 64,
        receipt,
        _proposal(),
    )
    await repository.close()

    statements = [statement for statement, _ in connection.executions]
    assert any("employment_patch_proposals" in statement for statement in statements)
    assert any("employment_patch_proposal_events" in statement for statement in statements)
    assert pool.closed is True


@pytest.mark.asyncio
async def test_serialized_proposal_holds_tenant_scoped_lock_for_read_and_write() -> None:
    connection = FakeConnection(_row(_proposal()))
    repository = EmploymentPatchRepository(FakePool(connection))

    async with repository.serialize_proposal(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY) as transaction:
        found = await transaction.find_by_idempotency(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY)
        assert found is not None
        await transaction.save(
            TENANT_ID,
            "relationship-1",
            IDEMPOTENCY_KEY,
            "b" * 64,
            {"proposalId": str(PROPOSAL_ID)},
            _proposal(),
        )

    statements = [statement for statement, _ in connection.executions]
    assert "set_config" in statements[0]
    assert "lock_employment_dispatch" in statements[1]
    assert "employment_dispatch_stops" in statements[2]
    assert "pg_advisory_xact_lock" in statements[3]
    assert "SELECT tenant_id" in statements[4]
    assert "employment_patch_proposals" in statements[5]
    assert "employment_patch_proposal_events" in statements[6]


@pytest.mark.asyncio
async def test_dispatch_claim_uses_tenant_relationship_and_key() -> None:
    connection = FakeConnection({"request_digest": "b" * 64, "recovery_mode": "UNKNOWN"})
    repository = EmploymentPatchRepository(FakePool(connection))
    async with repository.serialize_proposal(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY) as transaction:
        claimed, digest, mode = await transaction.claim_dispatch(
            TENANT_ID, "relationship-1", IDEMPOTENCY_KEY, "b" * 64, "UNKNOWN"
        )
    assert claimed
    assert digest == "b" * 64
    assert mode == "UNKNOWN"
    statement, values = connection.executions[-1]
    assert "employment_patch_dispatch_claims" in statement
    assert "ON CONFLICT" in statement
    assert values == (TENANT_ID, "relationship-1", IDEMPOTENCY_KEY, "b" * 64, "UNKNOWN")


@pytest.mark.asyncio
async def test_dispatch_claim_recovers_exact_conflict_and_rejects_missing_claim() -> None:
    class ConflictingConnection(FakeConnection):
        def __init__(self, existing: dict[str, Any] | None) -> None:
            super().__init__()
            self.existing = existing

        async def fetchrow(self, statement: str, *values: object) -> dict[str, Any] | None:
            self.executions.append((statement, values))
            return self.existing if "SELECT request_digest" in statement else None

    existing = {"request_digest": "b" * 64, "recovery_mode": "UNKNOWN"}
    repository = EmploymentPatchRepository(FakePool(ConflictingConnection(existing)))
    async with repository.serialize_proposal(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY) as transaction:
        claimed, digest, mode = await transaction.claim_dispatch(
            TENANT_ID, "relationship-1", IDEMPOTENCY_KEY, "b" * 64, "UNKNOWN"
        )
    assert not claimed
    assert (digest, mode) == ("b" * 64, "UNKNOWN")

    repository = EmploymentPatchRepository(FakePool(ConflictingConnection(None)))
    with pytest.raises(RuntimeError, match="disappeared during serialization"):
        async with repository.serialize_proposal(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY) as transaction:
            await transaction.claim_dispatch(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY, "b" * 64, "UNKNOWN")


@pytest.mark.asyncio
async def test_stop_is_checked_under_shared_lock_before_claim_or_save() -> None:
    class StoppedConnection(FakeConnection):
        async def fetchrow(self, statement, *values):
            if "employment_dispatch_stops" in statement:
                self.executions.append((statement, values))
                return {"relationship_ref": "relationship-1"}
            return await super().fetchrow(statement, *values)

    connection = StoppedConnection()
    repository = EmploymentPatchRepository(FakePool(connection))
    with pytest.raises(EmploymentDispatchStoppedError):
        await repository.save(TENANT_ID, "relationship-1", IDEMPOTENCY_KEY, "b" * 64, {}, _proposal())
    statements = [statement for statement, _ in connection.executions]
    assert "lock_employment_dispatch" in statements[1]
    assert "employment_dispatch_stops" in statements[2]
    assert not any("INSERT" in statement for statement in statements)


@pytest.mark.asyncio
async def test_repository_handles_missing_and_serialized_rows() -> None:
    connection = FakeConnection()
    repository = EmploymentPatchRepository(FakePool(connection))
    assert await repository.get(TENANT_ID, PROPOSAL_ID) is None

    connection.row = _row(json.dumps(_proposal()))
    stored = await repository.get(TENANT_ID, PROPOSAL_ID)
    assert stored is not None
    assert stored.proposal_id == PROPOSAL_ID


@pytest.mark.asyncio
async def test_repository_connect_normalizes_sqlalchemy_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    pool = FakePool(FakeConnection())

    async def create_pool(dsn: str, **options: object) -> FakePool:
        observed.update(dsn=dsn, options=options)
        return pool

    monkeypatch.setattr("employment_persistence.asyncpg.create_pool", create_pool)
    database_url = (
        # Exercise the SQLAlchemy-to-asyncpg DSN normalization.
        "postgresql+asyncpg://air:test@postgres/waooaw"
    )
    repository = await EmploymentPatchRepository.connect(database_url)
    assert observed["dsn"] == "postgresql://air:test@postgres/waooaw"
    assert observed["options"] == {"min_size": 1, "max_size": 5}
    await repository.close()
