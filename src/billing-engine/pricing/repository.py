# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""PostgreSQL repository for pricing versions (WC-136 C4-05, C5-01).

Reads select from ``institutional.pricing_versions`` and its events; every write calls one of the
owner-defined SECURITY DEFINER functions, because the application role has SELECT only on the tables.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from pricing.engine import Direction
from pricing.models import (
    PricingDraftInvalid,
    PricingError,
    PricingEvent,
    PricingIllegalTransition,
    PricingKind,
    PricingNeedsSecondConfirmation,
    PricingUnavailable,
    PricingVersion,
    PricingVersionNotFound,
    VersionState,
    Violation,
)

logger = logging.getLogger(__name__)

_VERSION_COLUMNS = """
    version_id, kind, subject_key, version_no, state, body, body_digest, seed, effective_from, supersedes,
    created_by, created_at, authorized_by, authorized_at, evidence_id, needs_second_confirmation,
    second_confirmed_by
"""
_GET_SQL = f"""
    SELECT {_VERSION_COLUMNS} FROM institutional.pricing_versions WHERE version_id = CAST(:version_id AS uuid)
"""
_LIST_SQL = f"""
    SELECT {_VERSION_COLUMNS} FROM institutional.pricing_versions
    WHERE (CAST(:kind AS TEXT) IS NULL OR kind = :kind)
      AND (CAST(:subject_key AS TEXT) IS NULL OR subject_key = :subject_key)
      AND (CAST(:state AS TEXT) IS NULL OR state = :state)
    ORDER BY created_at DESC, version_no DESC
    LIMIT :limit OFFSET :offset
"""
_EFFECTIVE_AT_SQL = f"""
    SELECT {_VERSION_COLUMNS} FROM institutional.pricing_versions
    WHERE kind = :kind AND subject_key = :subject_key
      AND state IN ('EFFECTIVE', 'AUTHORIZED') AND effective_from <= :at
    ORDER BY effective_from DESC, version_no DESC
    LIMIT 1
"""
_IN_FORCE_SQL = f"""
    SELECT DISTINCT ON (subject_key) {_VERSION_COLUMNS} FROM institutional.pricing_versions
    WHERE kind = :kind AND state IN ('EFFECTIVE', 'AUTHORIZED') AND effective_from <= :at
    ORDER BY subject_key, effective_from DESC, version_no DESC
"""
_DUE_SQL = f"""
    SELECT {_VERSION_COLUMNS} FROM institutional.pricing_versions
    WHERE state = 'AUTHORIZED' AND effective_from <= :at
    ORDER BY effective_from, version_no
"""


def translate_database_error(error: DBAPIError) -> PricingError:
    """Map an owner-function or trigger failure to the Appendix B.5 error; anything else is unavailable."""
    message = str(getattr(error, "orig", None) or error)
    if "PRICING_VERSION_NOT_FOUND" in message:
        return PricingVersionNotFound("The pricing version does not exist.")
    if "PRICING_NEEDS_SECOND_CONFIRMATION" in message:
        return PricingNeedsSecondConfirmation("A second confirmation is required before submitting.")
    if "PRICING_DRAFT_INVALID" in message:
        return PricingDraftInvalid(
            [Violation(code="PRICING_DRAFT_INVALID", field="body", message="The draft cannot be applied.")]
        )
    if "PRICING_ILLEGAL_TRANSITION" in message or "immutable" in message or "append-only" in message:
        return PricingIllegalTransition("The requested change is not allowed for this version.")
    logger.error("pricing_repository_failure", extra={"context": "pricing_repository"})
    return PricingUnavailable("The pricing store is unavailable.")


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _to_version(row: Any) -> PricingVersion:
    return PricingVersion(
        version_id=UUID(str(row.version_id)),
        kind=PricingKind(row.kind),
        subject_key=row.subject_key,
        version_no=int(row.version_no),
        state=VersionState(row.state),
        body=dict(_json(row.body)),
        body_digest=row.body_digest,
        seed=bool(row.seed),
        effective_from=row.effective_from,
        supersedes=None if row.supersedes is None else UUID(str(row.supersedes)),
        created_by=row.created_by,
        created_at=row.created_at,
        authorized_by=row.authorized_by,
        authorized_at=row.authorized_at,
        evidence_id=None if row.evidence_id is None else UUID(str(row.evidence_id)),
        needs_second_confirmation=bool(row.needs_second_confirmation),
        second_confirmed_by=row.second_confirmed_by,
    )


def _to_event(row: Any) -> PricingEvent:
    return PricingEvent(
        event_id=UUID(str(row.event_id)),
        version_id=UUID(str(row.version_id)),
        from_state=None if row.from_state is None else VersionState(row.from_state),
        to_state=VersionState(row.to_state),
        direction=row.direction,
        actor=row.actor,
        occurred_at=row.occurred_at,
        reason=row.reason,
    )


class SqlPricingRepository:
    """Implements ``pricing.engine.PricingRepository`` over one AsyncSession (one transaction)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _execute(self, statement: str, params: Mapping[str, Any]) -> Any:
        try:
            return await self._session.execute(text(statement), dict(params))
        except DBAPIError as error:
            raise translate_database_error(error) from error

    async def _version_from_function(self, statement: str, params: Mapping[str, Any]) -> PricingVersion:
        result = await self._execute(statement, params)
        return _to_version(result.fetchone())

    async def create_draft(
        self,
        *,
        version_id: UUID,
        kind: PricingKind,
        subject_key: str,
        body: Mapping[str, Any],
        digest: str,
        actor_id: str,
        needs_second_confirmation: bool,
        at: datetime,
    ) -> PricingVersion:
        return await self._version_from_function(
            """
            SELECT * FROM institutional.create_pricing_draft(
                CAST(:version_id AS uuid), :kind, :subject_key, CAST(:body AS jsonb), :digest,
                :actor_id, :needs_second, :at)
            """,
            {
                "version_id": str(version_id),
                "kind": kind.value,
                "subject_key": subject_key,
                "body": json.dumps(body, sort_keys=True),
                "digest": digest,
                "actor_id": actor_id,
                "needs_second": needs_second_confirmation,
                "at": at,
            },
        )

    async def edit_draft(
        self,
        *,
        version_id: UUID,
        body: Mapping[str, Any],
        digest: str,
        actor_id: str,
        needs_second_confirmation: bool,
        at: datetime,
    ) -> PricingVersion:
        return await self._version_from_function(
            """
            SELECT * FROM institutional.edit_pricing_draft(
                CAST(:version_id AS uuid), CAST(:body AS jsonb), :digest, :actor_id, :needs_second, :at)
            """,
            {
                "version_id": str(version_id),
                "body": json.dumps(body, sort_keys=True),
                "digest": digest,
                "actor_id": actor_id,
                "needs_second": needs_second_confirmation,
                "at": at,
            },
        )

    async def transition(
        self,
        *,
        version_id: UUID,
        to_state: VersionState,
        actor_id: str,
        reason: str | None,
        at: datetime,
        authorized_by: str | None = None,
        evidence_id: UUID | None = None,
        effective_from: datetime | None = None,
        needs_second_confirmation: bool | None = None,
        second_confirmed_by: str | None = None,
    ) -> PricingVersion:
        return await self._version_from_function(
            """
            SELECT * FROM institutional.transition_pricing_version(
                CAST(:version_id AS uuid), :to_state, :actor_id, :reason, :at, :authorized_by,
                CAST(:evidence_id AS uuid), :effective_from, :needs_second, :second_confirmed_by)
            """,
            {
                "version_id": str(version_id),
                "to_state": to_state.value,
                "actor_id": actor_id,
                "reason": reason,
                "at": at,
                "authorized_by": authorized_by,
                "evidence_id": None if evidence_id is None else str(evidence_id),
                "effective_from": effective_from,
                "needs_second": needs_second_confirmation,
                "second_confirmed_by": second_confirmed_by,
            },
        )

    async def apply_safety_successor(
        self,
        *,
        event_id: UUID,
        kind: PricingKind,
        subject_key: str,
        body: Mapping[str, Any],
        digest: str,
        actor_id: str,
        reason: str,
        at: datetime,
    ) -> PricingVersion:
        return await self._version_from_function(
            """
            SELECT * FROM institutional.apply_pricing_safety_successor(
                CAST(:event_id AS uuid), :kind, :subject_key, CAST(:body AS jsonb), :digest,
                :actor_id, :reason, :at)
            """,
            {
                "event_id": str(event_id),
                "kind": kind.value,
                "subject_key": subject_key,
                "body": json.dumps(body, sort_keys=True),
                "digest": digest,
                "actor_id": actor_id,
                "reason": reason,
                "at": at,
            },
        )

    async def project_package_profile(
        self,
        *,
        version_id: UUID,
        thread_rations: Mapping[str, int],
        cost_floor_paise: int,
        infrastructure_share_paise: int,
        minimum_margin_pct: float | None,
        display_name: str,
    ) -> UUID:
        result = await self._execute(
            """
            SELECT institutional.project_package_profile(
                CAST(:version_id AS uuid), CAST(:thread_rations AS jsonb), :cost_floor,
                :infrastructure_share, :minimum_margin_pct, :display_name)
            """,
            {
                "version_id": str(version_id),
                "thread_rations": json.dumps(dict(thread_rations), sort_keys=True),
                "cost_floor": cost_floor_paise,
                "infrastructure_share": infrastructure_share_paise,
                "minimum_margin_pct": None if minimum_margin_pct is None else Decimal(str(minimum_margin_pct)),
                "display_name": display_name,
            },
        )
        return UUID(str(result.scalar_one()))

    async def set_package_sale_state(
        self,
        *,
        version_id: UUID,
        for_sale: bool,
        direction: Direction,
        actor_id: str,
        reason: str | None,
        at: datetime,
    ) -> bool:
        result = await self._execute(
            """
            SELECT institutional.set_package_sale_state(
                CAST(:version_id AS uuid), :for_sale, :direction, :actor_id, :reason, :at)
            """,
            {
                "version_id": str(version_id),
                "for_sale": for_sale,
                "direction": direction,
                "actor_id": actor_id,
                "reason": reason,
                "at": at,
            },
        )
        return bool(result.scalar_one())

    async def get(self, version_id: UUID) -> PricingVersion | None:
        result = await self._execute(
            _GET_SQL,
            {"version_id": str(version_id)},
        )
        row = result.fetchone()
        return None if row is None else _to_version(row)

    async def list_versions(
        self,
        *,
        kind: PricingKind | None = None,
        subject_key: str | None = None,
        state: VersionState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PricingVersion]:
        result = await self._execute(
            _LIST_SQL,
            {
                "kind": None if kind is None else kind.value,
                "subject_key": subject_key,
                "state": None if state is None else state.value,
                "limit": limit,
                "offset": offset,
            },
        )
        return [_to_version(row) for row in result.fetchall()]

    async def list_events(self, version_id: UUID) -> list[PricingEvent]:
        result = await self._execute(
            """
            SELECT event_id, version_id, from_state, to_state, direction, actor, occurred_at, reason
            FROM institutional.pricing_version_events
            WHERE version_id = CAST(:version_id AS uuid)
            ORDER BY occurred_at, event_id
            """,
            {"version_id": str(version_id)},
        )
        return [_to_event(row) for row in result.fetchall()]

    async def effective_at(self, kind: PricingKind, subject_key: str, at: datetime) -> PricingVersion | None:
        result = await self._execute(
            _EFFECTIVE_AT_SQL,
            {"kind": kind.value, "subject_key": subject_key, "at": at},
        )
        row = result.fetchone()
        return None if row is None else _to_version(row)

    async def list_in_force(self, kind: PricingKind, at: datetime) -> list[PricingVersion]:
        result = await self._execute(
            _IN_FORCE_SQL,
            {"kind": kind.value, "at": at},
        )
        return [_to_version(row) for row in result.fetchall()]

    async def list_due_authorized(self, at: datetime) -> list[PricingVersion]:
        result = await self._execute(
            _DUE_SQL,
            {"at": at},
        )
        return [_to_version(row) for row in result.fetchall()]

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
