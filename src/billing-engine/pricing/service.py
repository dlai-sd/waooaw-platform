# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01, C5-02
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Pricing service: authorization rules over the pricing engine (WC-136 C5-01).

This is the surface the WBE admin API calls. It decides who may do what independently of any HTTP role
check: an administrator creates, edits, simulates, submits, discards and runs safety operations; only a
Founder holding step-up authorizes or activates a package for sale. Every authorization records
Constitutional Engine evidence before the transition commits and fails closed when CE is unavailable.
Each public method is one transaction: committed on success, rolled back on any failure.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4

from pydantic import ValidationError

from markup.package_engine import AgentDeclarationSource, PackageReferenceData, marked_up_rate_paise, parse_package_body
from markup.package_models import PackageBody
from pricing.engine import Clock, PricingEngine, PricingRepository, utc_now
from pricing.margin_watch import BreachReporter, MarginBreach, recompute
from pricing.models import (
    ActorContext,
    EffectiveRole,
    PricingDraftInvalid,
    PricingEvent,
    PricingForbidden,
    PricingIllegalTransition,
    PricingKind,
    PricingNeedsSecondConfirmation,
    PricingStepUpRequired,
    PricingUnavailable,
    PricingVersion,
    PricingVersionNotFound,
    VersionState,
    Violation,
    error_for_violations,
)
from pricing.simulator import (
    NEEDS_SECOND_CONFIRMATION_WARNING,
    PersonaProfile,
    SimulationContext,
    SimulationReport,
    simulate_draft,
)
from pricing.validators import ValidationContext, ValidationOutcome, minimum_margin_of, validate_body

logger = logging.getLogger(__name__)

ACTION_AUTHORIZE = "pricing.version.authorize.write"
ACTION_ACTIVATE_FOR_SALE = "pricing.package.activate_for_sale.write"
POLICY_SUBJECT_KEY = "policy:platform"
SYSTEM_ACTOR = "system:pricing-scheduler"
SYSTEM_ROLE = "SYSTEM"
GUARDED_KINDS = frozenset({PricingKind.RATE, PricingKind.PACKAGE, PricingKind.BUDGET})
_OPERATOR_ROLES = (EffectiveRole.PRICING_ADMIN, EffectiveRole.FOUNDER)

T = TypeVar("T")
RateHook = Callable[[PricingVersion], Awaitable[None]]


class EvidenceRecorder(Protocol):
    """Records Constitutional Engine evidence for an action and returns its evidence id."""

    async def record(self, *, action: str, actor_id: str, subject_key: str) -> UUID: ...


class CeEvidenceRecorder:
    """Evidence from the existing CE validator (``ce_validator.CE.validate_action``); denial or outage fails closed."""

    def __init__(self, validate_action: Callable[[str], Awaitable[None]], new_id: Callable[[], UUID] = uuid4) -> None:
        self._validate_action = validate_action
        self._new_id = new_id

    async def record(self, *, action: str, actor_id: str, subject_key: str) -> UUID:
        try:
            await self._validate_action(action)
        except Exception as error:
            logger.error("pricing_ce_evidence_unavailable", extra={"pricing_action": action})
            raise PricingUnavailable("Constitutional evidence could not be recorded; the action was not taken.") from error
        return self._new_id()


@dataclass(frozen=True)
class SafetyNotification:
    operation: str
    kind: PricingKind
    subject_key: str
    version_id: UUID
    actor_id: str
    actor_role: str
    reason: str
    occurred_at: datetime


class FounderNotifier(Protocol):
    async def notify(self, notification: SafetyNotification) -> None: ...


class LoggingFounderNotifier:
    """Default notifier: a structured ``pricing_founder_notification`` event."""

    async def notify(self, notification: SafetyNotification) -> None:
        logger.warning(
            "pricing_founder_notification",
            extra={
                "pricing_operation": notification.operation,
                "pricing_kind": notification.kind.value,
                "pricing_subject": notification.subject_key,
                "pricing_version_id": str(notification.version_id),
                "actor_role": notification.actor_role,
            },
        )


@dataclass(frozen=True)
class DraftResult:
    version: PricingVersion
    violations: list[Violation]
    warnings: list[Violation]


@dataclass(frozen=True)
class SimulationResult:
    version: PricingVersion
    report: SimulationReport


def _number(body: Mapping[str, Any] | None, key: str) -> Fraction | None:
    if body is None:
        return None
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return Fraction(str(value))


def _moved_beyond_guard(old: Fraction | None, new: Fraction | None, guard_percent: Fraction) -> bool:
    if old is None or new is None or old == new:
        return False
    if old == 0:
        return True
    return abs(new - old) * 100 > old * guard_percent


def _rate_cost(body: Mapping[str, Any] | None) -> Fraction | None:
    if body is None:
        return None
    try:
        return Fraction(
            marked_up_rate_paise(
                int(body["rawCostPaise"]), body["fxBufferPct"], body["opsOverheadPct"], body["riskPremiumPct"]
            )
        )
    except (KeyError, TypeError, ValueError):
        return None


def requires_second_confirmation(
    kind: PricingKind,
    body: Mapping[str, Any],
    *,
    effective_body: Mapping[str, Any] | None,
    policy_body: Mapping[str, Any] | None,
    cost_floor_paise: int | None,
) -> bool:
    """Change-size guard: a move beyond ``changeSizeGuardPercent`` or a price above ``priceMultipleGuard`` x floor.

    Without a readable guard policy the answer is yes (fail closed).
    """
    if kind not in GUARDED_KINDS:
        return False
    guard = _number(policy_body, "changeSizeGuardPercent")
    multiple = _number(policy_body, "priceMultipleGuard")
    if guard is None or multiple is None:
        return True
    if kind is PricingKind.RATE:
        return _moved_beyond_guard(_rate_cost(effective_body), _rate_cost(body), guard)
    if kind is PricingKind.BUDGET:
        return _moved_beyond_guard(_number(effective_body, "maximumPaise"), _number(body, "maximumPaise"), guard)
    price = _number(body, "priceInclGstPaise")
    if _moved_beyond_guard(_number(effective_body, "priceInclGstPaise"), price, guard):
        return True
    return price is not None and cost_floor_paise is not None and price > multiple * cost_floor_paise


@dataclass(frozen=True)
class _Prepared:
    outcome: ValidationOutcome
    body: dict[str, Any]
    subject_key: str
    needs_second: bool


class PricingService:
    """Public surface for creating, simulating, authorizing and operating pricing versions."""

    def __init__(
        self,
        *,
        repository: PricingRepository,
        reference: PackageReferenceData,
        declarations: AgentDeclarationSource,
        evidence: EvidenceRecorder,
        notifier: FounderNotifier | None = None,
        clock: Clock = utc_now,
        on_rate_effective: RateHook | None = None,
        personas: Sequence[PersonaProfile] = (),
        breach_reporter: BreachReporter | None = None,
    ) -> None:
        self._repository = repository
        self._reference = reference
        self._declarations = declarations
        self._evidence = evidence
        self._notifier: FounderNotifier = notifier or LoggingFounderNotifier()
        self._clock = clock
        self._engine = PricingEngine(repository, clock)
        self._on_rate_effective = on_rate_effective
        self._personas = tuple(personas)
        self._breach_reporter = breach_reporter

    # ------------------------------------------------------------------ authorization helpers

    @staticmethod
    def _require_operator(actor: ActorContext) -> None:
        if actor.effective_role not in _OPERATOR_ROLES:
            raise PricingForbidden("The pricing role is required.")

    @staticmethod
    def _require_founder_step_up(actor: ActorContext) -> None:
        if actor.effective_role != EffectiveRole.FOUNDER:
            raise PricingForbidden("Only the Founder may do this.")
        if not actor.step_up:
            raise PricingStepUpRequired("Step-up authentication is required.")

    async def _unit(self, operation: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await operation()
            await self._repository.commit()
        except BaseException:
            await self._repository.rollback()
            raise
        return result

    @staticmethod
    def _log_transition(
        version: PricingVersion, from_state: VersionState | None, direction: str, actor_role: str
    ) -> None:
        logger.info(
            "pricing_version_transition",
            extra={
                "pricing_kind": version.kind.value,
                "pricing_subject": version.subject_key,
                "from_state": None if from_state is None else from_state.value,
                "to_state": version.state.value,
                "direction": direction,
                "actor_role": actor_role,
            },
        )

    # ------------------------------------------------------------------ reference lookups

    async def _policy_body(self, at: datetime) -> dict[str, Any] | None:
        policy = await self._engine.effective_version(PricingKind.POLICY, POLICY_SUBJECT_KEY, at)
        return None if policy is None else policy.body

    async def _validation_context(
        self,
        kind: PricingKind,
        raw_body: Mapping[str, Any],
        *,
        at: datetime,
        deploy_maximum_paise: int | None,
        require_availability: bool,
        policy_body: Mapping[str, Any] | None,
    ) -> ValidationContext:
        coupon_packages: list[PackageBody] = []
        if kind is PricingKind.COUPON:
            for package in await self._engine.effective_versions(PricingKind.PACKAGE, at):
                try:
                    coupon_packages.append(parse_package_body(package.body))
                except ValidationError:
                    logger.error("pricing_package_body_unreadable", extra={"pricing_subject": package.subject_key})
        return ValidationContext(
            reference=self._reference,
            declarations=self._declarations,
            minimum_margin_pct=minimum_margin_of(policy_body),
            deploy_maximum_paise=deploy_maximum_paise,
            require_availability=require_availability,
            coupon_packages=coupon_packages,
            now=at,
        )

    async def _validate(
        self,
        kind: PricingKind,
        raw_body: Mapping[str, Any],
        *,
        at: datetime,
        deploy_maximum_paise: int | None,
        require_availability: bool = False,
    ) -> tuple[ValidationOutcome, Mapping[str, Any] | None]:
        policy_body = await self._policy_body(at)
        context = await self._validation_context(
            kind,
            raw_body,
            at=at,
            deploy_maximum_paise=deploy_maximum_paise,
            require_availability=require_availability,
            policy_body=policy_body,
        )
        return await validate_body(kind, raw_body, context), policy_body

    async def _needs_second(
        self, kind: PricingKind, outcome: ValidationOutcome, policy_body: Mapping[str, Any] | None, at: datetime
    ) -> bool:
        if outcome.body is None or outcome.subject_key is None:
            return False
        effective = await self._engine.effective_version(kind, outcome.subject_key, at)
        floor = None if outcome.evaluation is None else outcome.evaluation.projection.cost_floor_paise
        return requires_second_confirmation(
            kind,
            outcome.body,
            effective_body=None if effective is None else effective.body,
            policy_body=policy_body,
            cost_floor_paise=floor,
        )

    async def _prepare(
        self,
        actor: ActorContext,
        kind: PricingKind,
        raw_body: Mapping[str, Any],
        *,
        deploy_maximum_paise: int | None,
        expected_subject: str | None,
    ) -> _Prepared:
        at = self._clock()
        outcome, policy_body = await self._validate(kind, raw_body, at=at, deploy_maximum_paise=deploy_maximum_paise)
        if outcome.body is None or outcome.subject_key is None:
            raise PricingDraftInvalid(outcome.violations)
        if expected_subject is not None and outcome.subject_key != expected_subject:
            raise PricingDraftInvalid(
                [
                    Violation(
                        code="PRICING_SUBJECT_IMMUTABLE",
                        field="body",
                        message="The subject of a draft cannot change; create a new draft instead.",
                        details={"subjectKey": expected_subject},
                    )
                ]
            )
        self._require_margin_authority(actor, kind, outcome.body, policy_body)
        needs_second = await self._needs_second(kind, outcome, policy_body, at)
        return _Prepared(outcome=outcome, body=outcome.body, subject_key=outcome.subject_key, needs_second=needs_second)

    @staticmethod
    def _require_margin_authority(
        actor: ActorContext, kind: PricingKind, body: Mapping[str, Any], policy_body: Mapping[str, Any] | None
    ) -> None:
        """The minimum margin is a Founder decision (C-089): only the Founder may change it."""
        if kind is not PricingKind.POLICY or actor.effective_role == EffectiveRole.FOUNDER:
            return
        current = minimum_margin_of(policy_body)
        if current is None or minimum_margin_of(body) != current:
            raise PricingForbidden("Only the Founder may change the minimum margin.")

    @staticmethod
    def _warnings(needs_second: bool) -> list[Violation]:
        if not needs_second:
            return []
        return [
            Violation(
                code=NEEDS_SECOND_CONFIRMATION_WARNING,
                field="body",
                message="The change is larger than the change-size guard; submitting needs a second confirmation.",
            )
        ]

    # ------------------------------------------------------------------ drafts

    async def create_draft(
        self,
        actor: ActorContext,
        kind: PricingKind,
        body: Mapping[str, Any],
        *,
        deploy_maximum_paise: int | None = None,
    ) -> DraftResult:
        """Create a DRAFT. A body that does not fit its kind is refused; rule violations are returned with the draft."""
        self._require_operator(actor)

        async def operation() -> DraftResult:
            prepared = await self._prepare(
                actor, kind, body, deploy_maximum_paise=deploy_maximum_paise, expected_subject=None
            )
            version = await self._engine.create_draft(
                kind=kind,
                subject_key=prepared.subject_key,
                body=prepared.body,
                actor_id=actor.actor_id,
                needs_second_confirmation=prepared.needs_second,
            )
            self._log_transition(version, None, "NORMAL", actor.effective_role.value)
            return DraftResult(version, prepared.outcome.violations, self._warnings(prepared.needs_second))

        return await self._unit(operation)

    async def update_draft(
        self,
        actor: ActorContext,
        version_id: UUID,
        body: Mapping[str, Any],
        *,
        deploy_maximum_paise: int | None = None,
    ) -> DraftResult:
        """Replace the body of a DRAFT or SIMULATED version; it returns to DRAFT and loses its simulation."""
        self._require_operator(actor)

        async def operation() -> DraftResult:
            existing = await self._engine.load(version_id)
            prepared = await self._prepare(
                actor,
                existing.kind,
                body,
                deploy_maximum_paise=deploy_maximum_paise,
                expected_subject=existing.subject_key,
            )
            version = await self._engine.edit_draft(
                version_id,
                body=prepared.body,
                actor_id=actor.actor_id,
                needs_second_confirmation=prepared.needs_second,
            )
            self._log_transition(version, existing.state, "NORMAL", actor.effective_role.value)
            return DraftResult(version, prepared.outcome.violations, self._warnings(prepared.needs_second))

        return await self._unit(operation)

    async def simulate(
        self,
        actor: ActorContext,
        version_id: UUID,
        *,
        personas: Sequence[PersonaProfile] = (),
        deploy_maximum_paise: int | None = None,
    ) -> SimulationResult:
        """Simulate a draft and mark it SIMULATED. The simulator itself writes nothing."""
        self._require_operator(actor)

        async def operation() -> SimulationResult:
            version = await self._engine.load(version_id)
            if version.state not in (VersionState.DRAFT, VersionState.SIMULATED):
                raise PricingIllegalTransition(
                    f"A {version.state.value} version cannot be simulated.",
                    details={"versionId": str(version_id), "from": version.state.value},
                )
            at = self._clock()
            outcome, policy_body = await self._validate(
                version.kind, version.body, at=at, deploy_maximum_paise=deploy_maximum_paise
            )
            needs_second = await self._needs_second(version.kind, outcome, policy_body, at)
            effective = await self._engine.effective_version(version.kind, version.subject_key, at)
            validation = await self._validation_context(
                version.kind,
                version.body,
                at=at,
                deploy_maximum_paise=deploy_maximum_paise,
                require_availability=False,
                policy_body=policy_body,
            )
            effective_packages: Sequence[PricingVersion] = ()
            if version.kind is PricingKind.RATE:
                effective_packages = await self._engine.effective_versions(PricingKind.PACKAGE, at)
            report = await simulate_draft(
                version,
                SimulationContext(
                    validation=validation,
                    effective_version=effective,
                    effective_packages=effective_packages,
                    needs_second_confirmation=needs_second,
                    personas=(*self._personas, *personas),
                ),
            )
            if version.state is VersionState.SIMULATED and version.needs_second_confirmation != needs_second:
                version = await self._engine.edit_draft(
                    version_id, body=version.body, actor_id=actor.actor_id, needs_second_confirmation=needs_second
                )
            if version.state is VersionState.DRAFT:
                previous = version.state
                version = await self._engine.mark_simulated(
                    version_id, actor_id=actor.actor_id, needs_second_confirmation=needs_second
                )
                self._log_transition(version, previous, "NORMAL", actor.effective_role.value)
            return SimulationResult(version, report)

        return await self._unit(operation)

    async def submit(
        self,
        actor: ActorContext,
        version_id: UUID,
        *,
        second_confirmation: bool = False,
        deploy_maximum_paise: int | None = None,
    ) -> PricingVersion:
        """SIMULATED to SUBMITTED. The draft is validated in full; a guarded change needs ``second_confirmation``."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            version = await self._engine.load(version_id)
            self._engine.assert_transition(version, VersionState.SUBMITTED)
            at = self._clock()
            outcome, policy_body = await self._validate(
                version.kind, version.body, at=at, deploy_maximum_paise=deploy_maximum_paise
            )
            if outcome.body is None or outcome.violations:
                raise error_for_violations(outcome.violations)
            self._require_margin_authority(actor, version.kind, version.body, policy_body)
            now_needs_second = await self._needs_second(version.kind, outcome, policy_body, at)
            if (version.needs_second_confirmation or now_needs_second) and not second_confirmation:
                raise PricingNeedsSecondConfirmation(
                    "The change is larger than the change-size guard; confirm it explicitly.",
                    details={"versionId": str(version_id)},
                )
            if now_needs_second and not version.needs_second_confirmation:
                raise PricingNeedsSecondConfirmation(
                    "The change now exceeds the guard; simulate the draft again before submitting.",
                    details={"versionId": str(version_id)},
                )
            submitted = await self._engine.submit(
                version_id,
                actor_id=actor.actor_id,
                second_confirmed_by=actor.actor_id if version.needs_second_confirmation else None,
            )
            self._log_transition(submitted, version.state, "NORMAL", actor.effective_role.value)
            return submitted

        return await self._unit(operation)

    async def withdraw(self, actor: ActorContext, version_id: UUID, reason: str | None = None) -> PricingVersion:
        """Return a SUBMITTED version to DRAFT."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            version = await self._engine.withdraw(version_id, actor_id=actor.actor_id, reason=reason)
            self._log_transition(version, VersionState.SUBMITTED, "NORMAL", actor.effective_role.value)
            return version

        return await self._unit(operation)

    async def discard(self, actor: ActorContext, version_id: UUID, reason: str | None = None) -> PricingVersion:
        """Discard a version that is not yet authorized."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            existing = await self._engine.load(version_id)
            version = await self._engine.discard(version_id, actor_id=actor.actor_id, reason=reason)
            self._log_transition(version, existing.state, "NORMAL", actor.effective_role.value)
            return version

        return await self._unit(operation)

    # ------------------------------------------------------------------ authorization

    async def authorize(
        self,
        actor: ActorContext,
        version_id: UUID,
        *,
        effective_from: datetime | None = None,
        deploy_maximum_paise: int | None = None,
    ) -> PricingVersion:
        """SUBMITTED to AUTHORIZED (Founder with step-up only), then EFFECTIVE when ``effective_from`` is due.

        The draft is validated again at current rates; CE evidence is recorded before the transition and CE
        unavailability fails the authorization closed. A PACKAGE is projected into ``bundle_profiles`` but is
        not for sale until ``activate_for_sale``.
        """
        self._require_founder_step_up(actor)

        async def operation() -> PricingVersion:
            version = await self._engine.load(version_id)
            self._engine.assert_transition(version, VersionState.AUTHORIZED)
            at = self._clock()
            if effective_from is not None and (effective_from.tzinfo is None or effective_from < at):
                raise PricingDraftInvalid(
                    [
                        Violation(
                            code="PRICING_EFFECTIVE_FROM_INVALID",
                            field="effectiveFrom",
                            message="effectiveFrom must be a UTC instant that is not in the past.",
                        )
                    ]
                )
            outcome, _ = await self._validate(version.kind, version.body, at=at, deploy_maximum_paise=deploy_maximum_paise)
            if outcome.body is None or outcome.violations:
                raise error_for_violations(outcome.violations)
            evidence_id = await self._evidence.record(
                action=ACTION_AUTHORIZE, actor_id=actor.actor_id, subject_key=version.subject_key
            )
            authorized = await self._engine.authorize(
                version_id, authorized_by=actor.actor_id, evidence_id=evidence_id, effective_from=effective_from
            )
            self._log_transition(authorized, version.state, "NORMAL", actor.effective_role.value)
            if version.kind is PricingKind.PACKAGE and outcome.evaluation is not None:
                projection = outcome.evaluation.projection
                await self._repository.project_package_profile(
                    version_id=version_id,
                    thread_rations=projection.thread_rations,
                    cost_floor_paise=projection.cost_floor_paise,
                    infrastructure_share_paise=projection.infrastructure_share_paise,
                    minimum_margin_pct=projection.minimum_margin_pct,
                    display_name=str(version.body["displayName"]),
                )
            if authorized.effective_from is not None and authorized.effective_from <= self._clock():
                effective = await self._engine.make_effective(version_id, actor_id=actor.actor_id)
                self._log_transition(effective, VersionState.AUTHORIZED, "NORMAL", actor.effective_role.value)
                return effective
            return authorized

        result = await self._unit(operation)
        await self._after_effective(result)
        return result

    async def activate_due(self, actor_id: str = SYSTEM_ACTOR) -> list[PricingVersion]:
        """Promote every AUTHORIZED version whose effective-from instant has arrived (oldest first)."""
        activated: list[PricingVersion] = []
        for due in await self._engine.due_versions():

            async def operation(due_id: UUID = due.version_id) -> PricingVersion:
                version = await self._engine.make_effective(due_id, actor_id=actor_id)
                self._log_transition(version, VersionState.AUTHORIZED, "NORMAL", SYSTEM_ROLE)
                return version

            try:
                version = await self._unit(operation)
            except (PricingIllegalTransition, PricingUnavailable, PricingVersionNotFound):
                logger.error("pricing_activation_failed", extra={"pricing_subject": due.subject_key})
                continue
            await self._after_effective(version)
            activated.append(version)
        return activated

    async def _after_effective(self, version: PricingVersion) -> None:
        if version.state is not VersionState.EFFECTIVE or version.kind is not PricingKind.RATE:
            return
        if self._on_rate_effective is not None:
            try:
                await self._on_rate_effective(version)
            except Exception:
                logger.error("pricing_rate_hook_failed", extra={"pricing_subject": version.subject_key})
        try:
            await self.live_margin()
        except Exception:
            logger.error("pricing_live_margin_failed", extra={"pricing_subject": version.subject_key})

    async def activate_for_sale(self, actor: ActorContext, version_id: UUID) -> PricingVersion:
        """Open an EFFECTIVE package to new customers (Founder with step-up); every component must be AVAILABLE."""
        self._require_founder_step_up(actor)

        async def operation() -> PricingVersion:
            version = await self._engine.load(version_id)
            if version.kind is not PricingKind.PACKAGE or version.state is not VersionState.EFFECTIVE:
                raise PricingIllegalTransition(
                    "Only an effective package can be opened for sale.",
                    details={"versionId": str(version_id), "from": version.state.value},
                )
            at = self._clock()
            outcome, _ = await self._validate(
                version.kind, version.body, at=at, deploy_maximum_paise=None, require_availability=True
            )
            if outcome.body is None or outcome.violations:
                raise error_for_violations(outcome.violations)
            evidence_id = await self._evidence.record(
                action=ACTION_ACTIVATE_FOR_SALE, actor_id=actor.actor_id, subject_key=version.subject_key
            )
            await self._repository.set_package_sale_state(
                version_id=version_id,
                for_sale=True,
                direction="NORMAL",
                actor_id=actor.actor_id,
                reason=f"ACTIVATE_FOR_SALE evidence={evidence_id}",
                at=at,
            )
            self._log_transition(version, VersionState.EFFECTIVE, "NORMAL", actor.effective_role.value)
            return version

        return await self._unit(operation)

    # ------------------------------------------------------------------ safety operations

    async def lower_ceiling(
        self, actor: ActorContext, subject_key: str, new_maximum_paise: int, reason: str
    ) -> PricingVersion:
        """Immediately lower an effective BUDGET ceiling (PRICING_ADMIN or FOUNDER); never raises one."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            current = await self._in_force_or_missing(PricingKind.BUDGET, subject_key)
            current_maximum = current.body.get("maximumPaise")
            if new_maximum_paise < 0 or not isinstance(current_maximum, int) or new_maximum_paise >= current_maximum:
                raise PricingDraftInvalid(
                    [
                        Violation(
                            code="SAFETY_NOT_A_REDUCTION",
                            field="maximumPaise",
                            message="A safety change must lower the ceiling.",
                            details={"currentMaximumPaise": current_maximum},
                        )
                    ]
                )
            return await self._apply_safety(
                actor, "LOWER_CEILING", current, {**current.body, "maximumPaise": new_maximum_paise}, reason
            )

        version = await self._unit(operation)
        await self._notify(actor, "LOWER_CEILING", version, reason)
        return version

    async def disable_grant(self, actor: ActorContext, subject_key: str, reason: str) -> PricingVersion:
        """Immediately disable an effective GRANT (PRICING_ADMIN or FOUNDER)."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            current = await self._in_force_or_missing(PricingKind.GRANT, subject_key)
            if current.body.get("disabled") is True:
                return current
            return await self._apply_safety(actor, "DISABLE_GRANT", current, {**current.body, "disabled": True}, reason)

        version = await self._unit(operation)
        await self._notify(actor, "DISABLE_GRANT", version, reason)
        return version

    async def close_package(self, actor: ActorContext, version_id: UUID, reason: str) -> PricingVersion:
        """Immediately close an effective package to new customers (PRICING_ADMIN or FOUNDER)."""
        self._require_operator(actor)

        async def operation() -> PricingVersion:
            version = await self._engine.load(version_id)
            if version.kind is not PricingKind.PACKAGE or version.state is not VersionState.EFFECTIVE:
                raise PricingIllegalTransition(
                    "Only an effective package can be closed to new customers.",
                    details={"versionId": str(version_id), "from": version.state.value},
                )
            await self._repository.set_package_sale_state(
                version_id=version_id,
                for_sale=False,
                direction="SAFETY",
                actor_id=actor.actor_id,
                reason=self._safety_reason("CLOSE_PACKAGE", reason),
                at=self._clock(),
            )
            self._log_transition(version, VersionState.EFFECTIVE, "SAFETY", actor.effective_role.value)
            return version

        version = await self._unit(operation)
        await self._notify(actor, "CLOSE_PACKAGE", version, reason)
        return version

    @staticmethod
    def _safety_reason(operation: str, reason: str) -> str:
        return f"{operation}: {reason.strip() or 'no reason given'}"

    async def _in_force_or_missing(self, kind: PricingKind, subject_key: str) -> PricingVersion:
        current = await self._engine.effective_version(kind, subject_key)
        if current is None:
            raise PricingVersionNotFound("No effective version exists for the subject.", details={"subjectKey": subject_key})
        if current.state is VersionState.AUTHORIZED:
            current = await self._engine.make_effective(current.version_id, actor_id=SYSTEM_ACTOR)
        return current

    async def _apply_safety(
        self, actor: ActorContext, operation: str, current: PricingVersion, body: Mapping[str, Any], reason: str
    ) -> PricingVersion:
        version, _event_id = await self._engine.apply_safety_successor(
            kind=current.kind,
            subject_key=current.subject_key,
            body=body,
            actor_id=actor.actor_id,
            reason=self._safety_reason(operation, reason),
        )
        self._log_transition(version, VersionState.EFFECTIVE, "SAFETY", actor.effective_role.value)
        return version

    async def _notify(self, actor: ActorContext, operation: str, version: PricingVersion, reason: str) -> None:
        notification = SafetyNotification(
            operation=operation,
            kind=version.kind,
            subject_key=version.subject_key,
            version_id=version.version_id,
            actor_id=actor.actor_id,
            actor_role=actor.effective_role.value,
            reason=reason,
            occurred_at=self._clock(),
        )
        try:
            await self._notifier.notify(notification)
        except Exception:
            logger.error("pricing_founder_notification_failed", extra={"pricing_operation": operation})

    # ------------------------------------------------------------------ reads

    async def get_version(self, version_id: UUID) -> PricingVersion:
        return await self._engine.load(version_id)

    async def list_versions(
        self,
        *,
        kind: PricingKind | None = None,
        subject_key: str | None = None,
        state: VersionState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PricingVersion]:
        return await self._repository.list_versions(
            kind=kind, subject_key=subject_key, state=state, limit=limit, offset=offset
        )

    async def list_events(self, version_id: UUID) -> list[PricingEvent]:
        await self._engine.load(version_id)
        return await self._repository.list_events(version_id)

    async def effective_version(
        self, kind: PricingKind, subject_key: str, at: datetime | None = None
    ) -> PricingVersion | None:
        """The version in force for a subject at ``at`` (default now), or None."""
        return await self._engine.effective_version(kind, subject_key, at)

    async def effective_versions(self, kind: PricingKind, at: datetime | None = None) -> Sequence[PricingVersion]:
        """One in-force version per subject of ``kind`` at ``at`` (default now)."""
        return await self._engine.effective_versions(kind, at)

    async def live_margin(self, at: datetime | None = None) -> list[MarginBreach]:
        """Recompute every in-force package at current rates; returns the packages in breach."""
        return await recompute(
            repository=self._repository,
            reference=self._reference,
            at=at or self._clock(),
            reporter=self._breach_reporter,
        )
