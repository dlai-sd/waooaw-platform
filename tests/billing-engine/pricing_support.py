# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-06, C5-01, C5-02
# Constitutional basis: C-059, C-088, C-089, C-091
"""Shared fixtures for the WC-136 pricing tests: the DMA package illustration, fake reference data,
an in-memory pricing repository that mirrors the owner database functions, and fake evidence and notifier.

The illustration prices a DMA STARTER package at INR 2,000 including GST. Its cost floor is 19,628 paise
while the proactive-message thread is pending (cost 0), its base price is 169,492 paise.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from markup.package_engine import AgentDeclaration, DeclaredComponent, StaticDeclarationSource, ThreadRate
from pricing.engine import IN_FORCE_STATES, LEGAL_TRANSITIONS
from pricing.models import (
    PricingEvent,
    PricingKind,
    PricingUnavailable,
    PricingVersion,
    PricingVersionNotFound,
    VersionState,
    body_digest,
)
from pricing.service import PricingService, SafetyNotification

AGENT_TYPE = "DMA"
AGENT_VERSION = "1.0.0"
PACKAGE_CODE = "STARTER"
PROACTIVE_THREAD = "whatsapp_template_utility"
PACKAGE_SUBJECT = f"package:{AGENT_TYPE}|{AGENT_VERSION}|{PACKAGE_CODE}"
POLICY_SUBJECT = "policy:platform"
START = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)

DMA_PRICE = 200000
DMA_INFRASTRUCTURE = 5000
DMA_FLOOR_PENDING = 19628
DMA_BASE = 169492


def dma_package_body(*, price: int = DMA_PRICE, package_code: str = PACKAGE_CODE) -> dict[str, Any]:
    return {
        "agentType": AGENT_TYPE,
        "agentVersion": AGENT_VERSION,
        "packageCode": package_code,
        "displayName": "Digital Marketing Agent Starter",
        "billingPeriodDays": 30,
        "priceInclGstPaise": price,
        "gstRatePercent": 18,
        "infrastructureSharePaise": DMA_INFRASTRUCTURE,
        "components": [
            {
                "componentId": "PROACTIVE_MESSAGE",
                "kind": "COUNTED",
                "quantity": 30,
                "cadence": "SPREAD",
                "priceAllocationPaise": 30000,
                "recipe": [{"threadId": PROACTIVE_THREAD, "unitsPerUnit": 1}],
            },
            {
                "componentId": "CONTENT_POST",
                "kind": "COUNTED",
                "quantity": 30,
                "cadence": "DAILY",
                "priceAllocationPaise": price - 80000,
                "recipe": [{"threadId": "llm_pro", "unitsPerUnit": 1}],
            },
            {
                "componentId": "CHAT_REPLY",
                "kind": "COUNTED",
                "quantity": 30,
                "cadence": "SPREAD",
                "priceAllocationPaise": 30000,
                "recipe": [{"threadId": "whatsapp_window", "unitsPerUnit": 1}],
            },
            {
                "componentId": "CHANNEL",
                "kind": "SELECTED",
                "quantity": 12,
                "cadence": "SPREAD",
                "selectableMaximum": 3,
                "priceAllocationPaise": 20000,
                "recipe": [{"threadId": "llm_mid_gemini", "unitsPerUnit": 1}],
            },
        ],
    }


def dma_rates(*, proactive_authorized: bool = False, proactive_cost: int = 0) -> dict[str, ThreadRate]:
    return {
        "llm_pro": ThreadRate("llm_pro", 400, True),
        "whatsapp_window": ThreadRate("whatsapp_window", 70, True),
        "llm_mid_gemini": ThreadRate("llm_mid_gemini", 44, True),
        PROACTIVE_THREAD: ThreadRate(PROACTIVE_THREAD, proactive_cost, proactive_authorized),
    }


def dma_declaration(*, availability: str = "AVAILABLE", overrides: dict[str, str] | None = None) -> AgentDeclaration:
    kinds = {"PROACTIVE_MESSAGE": "COUNTED", "CONTENT_POST": "COUNTED", "CHAT_REPLY": "COUNTED", "CHANNEL": "SELECTED"}
    states = {name: availability for name in kinds}
    states.update(overrides or {})
    return AgentDeclaration(
        AGENT_TYPE,
        AGENT_VERSION,
        {name: DeclaredComponent(name, kind, states[name]) for name, kind in kinds.items()},
    )


def policy_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "minimumMarginPct": 55,
        "paymentGraceDays": 7,
        "sunsetNoticeDays": 30,
        "costToleranceFraction": 0.2,
        "costAlertFraction": 0.1,
        "upgradeTiming": "IMMEDIATE",
        "downgradeTiming": "AT_RENEWAL",
        "changeSizeGuardPercent": 30,
        "priceMultipleGuard": 20,
        "minimumMarginNote": "SEED_UNCONFIRMED",
    }
    body.update(changes)
    return body


def rate_body(thread_id: str = "llm_pro", *, raw: int = 300, fx: float = 10, ops: float = 15, risk: float = 8) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "provider": "Provider",
        "unit": "per call",
        "rawCostPaise": raw,
        "fxBufferPct": fx,
        "opsOverheadPct": ops,
        "riskPremiumPct": risk,
    }


def budget_body(maximum: int = 50000, *, scope: str = "ENVIRONMENT_CEILING", reference: str = "demo") -> dict[str, Any]:
    return {"scope": scope, "reference": reference, "maximumPaise": maximum}


def grant_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "grantKind": "TRIAL",
        "agentType": AGENT_TYPE,
        "agentVersion": AGENT_VERSION,
        "threadUnits": {"llm_mid_gemini": 50},
        "durationDays": 14,
    }
    body.update(changes)
    return body


class FakeReference:
    """Thread rates and billing-profile authority held in memory; ``rates`` may be mutated by a test."""

    def __init__(self, rates: dict[str, ThreadRate] | None = None, authorized_agents: tuple[str, ...] = (AGENT_TYPE,)) -> None:
        self.rates = dict(dma_rates(proactive_authorized=True, proactive_cost=5) if rates is None else rates)
        self.authorized_agents = set(authorized_agents)

    async def thread_rates(self, thread_ids):
        return {thread_id: self.rates[thread_id] for thread_id in thread_ids if thread_id in self.rates}

    async def billing_profile_authorized(self, agent_type):
        return agent_type in self.authorized_agents


def dma_declarations(**kwargs: Any) -> StaticDeclarationSource:
    return StaticDeclarationSource([dma_declaration(**kwargs)])


class FixedClock:
    def __init__(self, now: datetime = START) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: int) -> None:
        self.now = self.now + timedelta(**delta)


class InMemoryPricingRepository:
    """Mirrors the owner functions of 99zzzzzzzz-wc136-07: numbering, transitions, supersession, events."""

    def __init__(self) -> None:
        self.versions: dict[UUID, PricingVersion] = {}
        self.events: list[PricingEvent] = []
        self.profiles: dict[UUID, dict[str, Any]] = {}
        self.sale_state: dict[UUID, bool] = {}
        self.sale_calls: list[dict[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0
        self._snapshot = self._copy()

    def _copy(self):
        return dict(self.versions), list(self.events), dict(self.profiles), dict(self.sale_state)

    def _event(self, version_id, from_state, to_state, direction, actor, at, reason):
        self.events.append(PricingEvent(uuid4(), version_id, from_state, to_state, direction, actor, at, reason))

    def seed(
        self,
        kind: PricingKind,
        subject_key: str,
        body: dict[str, Any],
        *,
        state: VersionState = VersionState.EFFECTIVE,
        effective_from: datetime = START - timedelta(days=1),
    ) -> PricingVersion:
        number = 1 + max((v.version_no for v in self.versions.values() if v.kind is kind and v.subject_key == subject_key), default=0)
        version = PricingVersion(
            version_id=uuid4(),
            kind=kind,
            subject_key=subject_key,
            version_no=number,
            state=state,
            body=body,
            body_digest=body_digest(body),
            seed=False,
            effective_from=effective_from,
            supersedes=None,
            created_by="seed",
            created_at=START - timedelta(days=2),
            authorized_by="founder-1",
            authorized_at=START - timedelta(days=2),
            evidence_id=uuid4(),
            needs_second_confirmation=False,
            second_confirmed_by=None,
        )
        self.versions[version.version_id] = version
        self._snapshot = self._copy()
        return version

    def _swap(self, version_id: UUID, **changes: Any) -> PricingVersion:
        updated = replace(self.versions[version_id], **changes)
        self.versions[version_id] = updated
        return updated

    async def create_draft(self, *, version_id, kind, subject_key, body, digest, actor_id, needs_second_confirmation, at):
        number = 1 + max((v.version_no for v in self.versions.values() if v.kind is kind and v.subject_key == subject_key), default=0)
        version = PricingVersion(
            version_id, kind, subject_key, number, VersionState.DRAFT, dict(body), digest, False, None, None,
            actor_id, at, None, None, None, needs_second_confirmation, None,
        )
        self.versions[version_id] = version
        self._event(version_id, None, VersionState.DRAFT, "NORMAL", actor_id, at, "CREATE")
        return version

    async def edit_draft(self, *, version_id, body, digest, actor_id, needs_second_confirmation, at):
        current = self._require(version_id)
        self._event(version_id, current.state, VersionState.DRAFT, "NORMAL", actor_id, at, "EDIT")
        return self._swap(
            version_id,
            body=dict(body),
            body_digest=digest,
            state=VersionState.DRAFT,
            needs_second_confirmation=needs_second_confirmation,
            second_confirmed_by=None,
        )

    def _require(self, version_id: UUID) -> PricingVersion:
        if version_id not in self.versions:
            raise PricingVersionNotFound("missing")
        return self.versions[version_id]

    async def transition(
        self,
        *,
        version_id,
        to_state,
        actor_id,
        reason,
        at,
        authorized_by=None,
        evidence_id=None,
        effective_from=None,
        needs_second_confirmation=None,
        second_confirmed_by=None,
    ):
        current = self._require(version_id)
        assert to_state in LEGAL_TRANSITIONS[current.state], "the engine must refuse illegal transitions first"
        changes: dict[str, Any] = {"state": to_state}
        if to_state is VersionState.SIMULATED and needs_second_confirmation is not None:
            changes["needs_second_confirmation"] = needs_second_confirmation
        if to_state is VersionState.SUBMITTED:
            changes["second_confirmed_by"] = second_confirmed_by
        if to_state is VersionState.DRAFT:
            changes["second_confirmed_by"] = None
        if to_state is VersionState.AUTHORIZED:
            changes.update(
                authorized_by=authorized_by, authorized_at=at, evidence_id=evidence_id, effective_from=effective_from or at
            )
        if to_state is VersionState.EFFECTIVE:
            previous = next(
                (
                    v
                    for v in self.versions.values()
                    if v.kind is current.kind
                    and v.subject_key == current.subject_key
                    and v.state is VersionState.EFFECTIVE
                    and v.version_id != version_id
                ),
                None,
            )
            if previous is not None:
                self._swap(previous.version_id, state=VersionState.SUPERSEDED)
                self._event(previous.version_id, VersionState.EFFECTIVE, VersionState.SUPERSEDED, "NORMAL", actor_id, at, "SUPERSEDED")
                changes["supersedes"] = previous.version_id
        self._event(version_id, current.state, to_state, "NORMAL", actor_id, at, reason)
        return self._swap(version_id, **changes)

    async def apply_safety_successor(self, *, event_id, kind, subject_key, body, digest, actor_id, reason, at):
        previous = next(
            (
                v
                for v in self.versions.values()
                if v.kind is kind and v.subject_key == subject_key and v.state is VersionState.EFFECTIVE
            ),
            None,
        )
        if previous is None:
            raise PricingVersionNotFound("missing")
        self._swap(previous.version_id, state=VersionState.SUPERSEDED)
        number = 1 + max(v.version_no for v in self.versions.values() if v.kind is kind and v.subject_key == subject_key)
        version = PricingVersion(
            uuid4(), kind, subject_key, number, VersionState.EFFECTIVE, dict(body), digest, False, at,
            previous.version_id, actor_id, at, actor_id, at, event_id, False, None,
        )
        self.versions[version.version_id] = version
        self._event(previous.version_id, VersionState.EFFECTIVE, VersionState.SUPERSEDED, "SAFETY", actor_id, at, reason)
        self._event(version.version_id, None, VersionState.EFFECTIVE, "SAFETY", actor_id, at, reason)
        return version

    async def project_package_profile(
        self, *, version_id, thread_rations, cost_floor_paise, infrastructure_share_paise, minimum_margin_pct, display_name
    ):
        assert self._require(version_id).state in IN_FORCE_STATES
        profile_id = uuid4()
        self.profiles[version_id] = {
            "profileId": profile_id,
            "threadRations": dict(thread_rations),
            "costFloorPaise": cost_floor_paise,
            "infrastructureSharePaise": infrastructure_share_paise,
            "minimumMarginPct": minimum_margin_pct,
            "displayName": display_name,
        }
        return profile_id

    async def set_package_sale_state(self, *, version_id, for_sale, direction, actor_id, reason, at):
        self._require(version_id)
        self.sale_state[version_id] = for_sale
        self.sale_calls.append({"versionId": version_id, "forSale": for_sale, "direction": direction, "reason": reason})
        return for_sale

    async def get(self, version_id):
        return self.versions.get(version_id)

    async def list_versions(self, *, kind=None, subject_key=None, state=None, limit=100, offset=0):
        rows = [
            v
            for v in self.versions.values()
            if (kind is None or v.kind is kind)
            and (subject_key is None or v.subject_key == subject_key)
            and (state is None or v.state is state)
        ]
        rows.sort(key=lambda v: (v.created_at, v.version_no), reverse=True)
        return rows[offset : offset + limit]

    async def list_events(self, version_id):
        return [e for e in self.events if e.version_id == version_id]

    async def effective_at(self, kind, subject_key, at):
        rows = [
            v
            for v in self.versions.values()
            if v.kind is kind
            and v.subject_key == subject_key
            and v.state in IN_FORCE_STATES
            and v.effective_from is not None
            and v.effective_from <= at
        ]
        rows.sort(key=lambda v: (v.effective_from, v.version_no), reverse=True)
        return rows[0] if rows else None

    async def list_in_force(self, kind, at):
        subjects = sorted({v.subject_key for v in self.versions.values() if v.kind is kind})
        found = [await self.effective_at(kind, subject, at) for subject in subjects]
        return [v for v in found if v is not None]

    async def list_due_authorized(self, at):
        rows = [
            v
            for v in self.versions.values()
            if v.state is VersionState.AUTHORIZED and v.effective_from is not None and v.effective_from <= at
        ]
        rows.sort(key=lambda v: (v.effective_from, v.version_no))
        return rows

    async def commit(self):
        self.commits += 1
        self._snapshot = self._copy()

    async def rollback(self):
        self.rollbacks += 1
        self.versions, self.events, self.profiles, self.sale_state = (
            dict(self._snapshot[0]),
            list(self._snapshot[1]),
            dict(self._snapshot[2]),
            dict(self._snapshot[3]),
        )


class FakeEvidence:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, str]] = []

    async def record(self, *, action, actor_id, subject_key):
        if self.fail:
            raise PricingUnavailable("CE is down")
        self.calls.append({"action": action, "actor": actor_id, "subject": subject_key})
        return uuid4()


class FakeNotifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[SafetyNotification] = []

    async def notify(self, notification):
        if self.fail:
            raise RuntimeError("channel down")
        self.sent.append(notification)


@dataclass
class Harness:
    service: PricingService
    repository: InMemoryPricingRepository
    reference: FakeReference
    evidence: FakeEvidence
    notifier: FakeNotifier
    clock: FixedClock
    rate_hook_calls: list[PricingVersion] = field(default_factory=list)


def make_harness(
    *,
    with_policy: bool = True,
    declaration_availability: str = "AVAILABLE",
    evidence_fails: bool = False,
    reference: FakeReference | None = None,
) -> Harness:
    repository = InMemoryPricingRepository()
    if with_policy:
        repository.seed(PricingKind.POLICY, POLICY_SUBJECT, policy_body())
    ref = reference or FakeReference()
    evidence = FakeEvidence(fail=evidence_fails)
    notifier = FakeNotifier()
    clock = FixedClock()
    calls: list[PricingVersion] = []

    async def hook(version: PricingVersion) -> None:
        calls.append(version)

    service = PricingService(
        repository=repository,
        reference=ref,
        declarations=dma_declarations(availability=declaration_availability),
        evidence=evidence,
        notifier=notifier,
        clock=clock,
        on_rate_effective=hook,
    )
    return Harness(service, repository, ref, evidence, notifier, clock, calls)
