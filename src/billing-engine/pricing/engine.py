# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Pricing version state machine (WC-136 Appendix A.2).

``DRAFT -> SIMULATED -> SUBMITTED -> AUTHORIZED -> EFFECTIVE -> SUPERSEDED``, with ``DISCARDED`` from
any state before authorization. Every change goes through the repository, whose implementation calls only
the owner-defined database functions, so a version has no in-place update path (DP-005): editing a draft
creates no new row but returns it to ``DRAFT`` and drops its simulation, and every other transition appends
an event row. The engine does no authorization and no commit; ``PricingService`` owns both.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from pricing.models import (
    PricingEvent,
    PricingIllegalTransition,
    PricingKind,
    PricingVersion,
    PricingVersionNotFound,
    VersionState,
    body_digest,
)

Clock = Callable[[], datetime]
Direction = Literal["NORMAL", "SAFETY"]

LEGAL_TRANSITIONS: Mapping[VersionState, frozenset[VersionState]] = {
    VersionState.DRAFT: frozenset({VersionState.SIMULATED, VersionState.DISCARDED}),
    VersionState.SIMULATED: frozenset({VersionState.SUBMITTED, VersionState.DRAFT, VersionState.DISCARDED}),
    VersionState.SUBMITTED: frozenset({VersionState.AUTHORIZED, VersionState.DRAFT, VersionState.DISCARDED}),
    VersionState.AUTHORIZED: frozenset({VersionState.EFFECTIVE}),
    VersionState.EFFECTIVE: frozenset({VersionState.SUPERSEDED}),
    VersionState.SUPERSEDED: frozenset(),
    VersionState.DISCARDED: frozenset(),
}
EDITABLE_STATES = frozenset({VersionState.DRAFT, VersionState.SIMULATED})
OPEN_STATES = frozenset({VersionState.DRAFT, VersionState.SIMULATED, VersionState.SUBMITTED})
IN_FORCE_STATES = (VersionState.EFFECTIVE, VersionState.AUTHORIZED)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class PricingRepository(Protocol):
    """Persistence port. Writes use only the owner database functions; the transaction belongs to the caller."""

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
    ) -> PricingVersion: ...

    async def edit_draft(
        self,
        *,
        version_id: UUID,
        body: Mapping[str, Any],
        digest: str,
        actor_id: str,
        needs_second_confirmation: bool,
        at: datetime,
    ) -> PricingVersion: ...

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
    ) -> PricingVersion: ...

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
    ) -> PricingVersion: ...

    async def project_package_profile(
        self,
        *,
        version_id: UUID,
        thread_rations: Mapping[str, int],
        cost_floor_paise: int,
        infrastructure_share_paise: int,
        minimum_margin_pct: float | None,
        display_name: str,
    ) -> UUID: ...

    async def set_package_sale_state(
        self,
        *,
        version_id: UUID,
        for_sale: bool,
        direction: Direction,
        actor_id: str,
        reason: str | None,
        at: datetime,
    ) -> bool: ...

    async def get(self, version_id: UUID) -> PricingVersion | None: ...

    async def list_versions(
        self,
        *,
        kind: PricingKind | None = None,
        subject_key: str | None = None,
        state: VersionState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PricingVersion]: ...

    async def list_events(self, version_id: UUID) -> list[PricingEvent]: ...

    async def effective_at(self, kind: PricingKind, subject_key: str, at: datetime) -> PricingVersion | None: ...

    async def list_in_force(self, kind: PricingKind, at: datetime) -> list[PricingVersion]: ...

    async def list_due_authorized(self, at: datetime) -> list[PricingVersion]: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class PricingEngine:
    """The Appendix A.2 state machine over a repository; Python checks first, the database trigger is the backstop."""

    def __init__(self, repository: PricingRepository, clock: Clock = utc_now) -> None:
        self._repository = repository
        self._clock = clock

    def now(self) -> datetime:
        return self._clock()

    async def load(self, version_id: UUID) -> PricingVersion:
        version = await self._repository.get(version_id)
        if version is None:
            raise PricingVersionNotFound("The pricing version does not exist.", details={"versionId": str(version_id)})
        return version

    @staticmethod
    def assert_transition(version: PricingVersion, to_state: VersionState) -> None:
        if to_state not in LEGAL_TRANSITIONS[version.state]:
            raise PricingIllegalTransition(
                f"{version.state.value} to {to_state.value} is not allowed.",
                details={"versionId": str(version.version_id), "from": version.state.value, "to": to_state.value},
            )

    async def create_draft(
        self,
        *,
        kind: PricingKind,
        subject_key: str,
        body: Mapping[str, Any],
        actor_id: str,
        needs_second_confirmation: bool,
    ) -> PricingVersion:
        return await self._repository.create_draft(
            version_id=uuid4(),
            kind=kind,
            subject_key=subject_key,
            body=body,
            digest=body_digest(body),
            actor_id=actor_id,
            needs_second_confirmation=needs_second_confirmation,
            at=self._clock(),
        )

    async def edit_draft(
        self, version_id: UUID, *, body: Mapping[str, Any], actor_id: str, needs_second_confirmation: bool
    ) -> PricingVersion:
        """Replace the body of a draft; the version returns to DRAFT and loses its simulation."""
        version = await self.load(version_id)
        if version.state not in EDITABLE_STATES:
            raise PricingIllegalTransition(
                f"A {version.state.value} version cannot be edited.",
                details={"versionId": str(version_id), "from": version.state.value},
            )
        return await self._repository.edit_draft(
            version_id=version_id,
            body=body,
            digest=body_digest(body),
            actor_id=actor_id,
            needs_second_confirmation=needs_second_confirmation,
            at=self._clock(),
        )

    async def mark_simulated(self, version_id: UUID, *, actor_id: str, needs_second_confirmation: bool) -> PricingVersion:
        version = await self.load(version_id)
        self.assert_transition(version, VersionState.SIMULATED)
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.SIMULATED,
            actor_id=actor_id,
            reason=None,
            at=self._clock(),
            needs_second_confirmation=needs_second_confirmation,
        )

    async def submit(self, version_id: UUID, *, actor_id: str, second_confirmed_by: str | None) -> PricingVersion:
        version = await self.load(version_id)
        self.assert_transition(version, VersionState.SUBMITTED)
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.SUBMITTED,
            actor_id=actor_id,
            reason=None,
            at=self._clock(),
            second_confirmed_by=second_confirmed_by,
        )

    async def withdraw(self, version_id: UUID, *, actor_id: str, reason: str | None) -> PricingVersion:
        """Return a submitted version to DRAFT."""
        version = await self.load(version_id)
        if version.state is not VersionState.SUBMITTED:
            raise PricingIllegalTransition(
                f"A {version.state.value} version cannot be withdrawn.",
                details={"versionId": str(version_id), "from": version.state.value},
            )
        self.assert_transition(version, VersionState.DRAFT)
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.DRAFT,
            actor_id=actor_id,
            reason=reason,
            at=self._clock(),
        )

    async def authorize(
        self, version_id: UUID, *, authorized_by: str, evidence_id: UUID, effective_from: datetime | None
    ) -> PricingVersion:
        """SUBMITTED to AUTHORIZED; ``effective_from`` defaults to now and may be a later instant."""
        version = await self.load(version_id)
        self.assert_transition(version, VersionState.AUTHORIZED)
        now = self._clock()
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.AUTHORIZED,
            actor_id=authorized_by,
            reason=None,
            at=now,
            authorized_by=authorized_by,
            evidence_id=evidence_id,
            effective_from=effective_from or now,
        )

    async def make_effective(self, version_id: UUID, *, actor_id: str) -> PricingVersion:
        """AUTHORIZED to EFFECTIVE at its effective-from instant; the previous effective version is superseded."""
        version = await self.load(version_id)
        self.assert_transition(version, VersionState.EFFECTIVE)
        now = self._clock()
        if version.effective_from is None or version.effective_from > now:
            due = None if version.effective_from is None else version.effective_from.isoformat()
            raise PricingIllegalTransition(
                "The version is not yet due.", details={"versionId": str(version_id), "effectiveFrom": due}
            )
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.EFFECTIVE,
            actor_id=actor_id,
            reason=None,
            at=now,
        )

    async def discard(self, version_id: UUID, *, actor_id: str, reason: str | None) -> PricingVersion:
        version = await self.load(version_id)
        self.assert_transition(version, VersionState.DISCARDED)
        return await self._repository.transition(
            version_id=version_id,
            to_state=VersionState.DISCARDED,
            actor_id=actor_id,
            reason=reason,
            at=self._clock(),
        )

    async def apply_safety_successor(
        self,
        *,
        kind: PricingKind,
        subject_key: str,
        body: Mapping[str, Any],
        actor_id: str,
        reason: str,
    ) -> tuple[PricingVersion, UUID]:
        """Immediately replace the effective BUDGET or GRANT version; returns the new version and its event id."""
        event_id = uuid4()
        version = await self._repository.apply_safety_successor(
            event_id=event_id,
            kind=kind,
            subject_key=subject_key,
            body=body,
            digest=body_digest(body),
            actor_id=actor_id,
            reason=reason,
            at=self._clock(),
        )
        return version, event_id

    async def effective_version(
        self, kind: PricingKind, subject_key: str, at: datetime | None = None
    ) -> PricingVersion | None:
        return await self._repository.effective_at(kind, subject_key, at or self._clock())

    async def effective_versions(self, kind: PricingKind, at: datetime | None = None) -> Sequence[PricingVersion]:
        return await self._repository.list_in_force(kind, at or self._clock())

    async def due_versions(self) -> Sequence[PricingVersion]:
        return await self._repository.list_due_authorized(self._clock())
