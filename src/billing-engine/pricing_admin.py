# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
# Constitutional basis: C-059, C-063, C-088, C-089, C-091
"""Private WBE pricing admin routes (wbe-pricing-admin.openapi.yaml, 18 operations).

Reachable only through the workload-identity path: a mutually authenticated Business Platform peer
certificate plus a delegated context (ADR-046) bound to route, operation, method, body digest,
correlation id and idempotency key. The pricing role travels in ``effective_role`` (pricing_admin or
founder) and the Founder step-up in the signed ``purpose`` (PRICING_ADMIN_STEP_UP). The body digest is
the SHA-256 of the exact bytes received, so no JSON re-serialization can disagree with the signer.
Rules live in ``pricing.service.PricingService``; this module only authenticates, adapts bodies and
maps every failure to an RFC 7807 problem with the published codes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from database import get_session_factory
from pricing import dashboard as dashboard_reports
from pricing.body_adapter import tax_treatment, to_internal, to_public
from pricing.declarations import ManifestDeclarationSource, RegistryAliasedReference
from pricing.export_import import BundleSigner, export_bundle, import_bundle
from pricing.models import (
    ActorContext,
    EffectiveRole,
    PricingDraftInvalid,
    PricingError,
    PricingKind,
    PricingBelowFloor,
    PricingVersion,
    PricingVersionNotFound,
    VersionState,
)
from pricing.service import PricingService
from pricing.simulator import BEST_CASE, TYPICAL, WORST_CASE, PersonaProfile, SimulationReport
from pricing.validators import _BODY_MODELS, subject_key_for
from workload_identity import (
    PEER_CERTIFICATE_STATE_KEY,
    DelegatedContext,
    ServiceAuthError,
    extract_peer_identity,
)

logger = logging.getLogger(__name__)

PRICING_PREFIX = "/internal/v1/pricing"
SCHEMA_VERSION = "1.0"
PROBLEM_MEDIA_TYPE = "application/problem+json"
STEP_UP_PURPOSE = "PRICING_ADMIN_STEP_UP"
ADMIN_PURPOSE = "PRICING_ADMIN"
DEFAULT_PAGE_SIZE = 25
MAXIMUM_PAGE_SIZE = 100
MAXIMUM_BODY_BYTES = 262_144
IDEMPOTENCY_TTL_SECONDS = 86_400
IDEMPOTENCY_CAPACITY = 2048
PENDING_STATES = (VersionState.DRAFT, VersionState.SIMULATED, VersionState.SUBMITTED, VersionState.AUTHORIZED)
ROLES_OPERATOR = frozenset({EffectiveRole.PRICING_ADMIN, EffectiveRole.FOUNDER})
ROLES_FOUNDER = frozenset({EffectiveRole.FOUNDER})
_PUBLIC_CODES: Mapping[str, str] = {"PRICING_VERSION_NOT_FOUND": "PRICING_NOT_FOUND"}
_EVIDENCE_REASON = re.compile(r"^ACTIVATE_FOR_SALE evidence=(?P<evidence>[0-9a-fA-F-]{36})$")
_SAFETY_SUBJECT = re.compile(r"^budget:[A-Z_]+\|.+$")

router = APIRouter(prefix=PRICING_PREFIX, tags=["Pricing Admin Private"])


class OperationRoute:
    def __init__(self, method: str, route: str, operation: str, roles: frozenset[EffectiveRole], writes: bool) -> None:
        self.method, self.route, self.operation, self.roles, self.writes = method, route, operation, roles, writes


OPERATIONS: dict[str, OperationRoute] = {
    item.operation: item
    for item in (
        OperationRoute("GET", f"{PRICING_PREFIX}/drafts", "wbeListPricingDrafts", ROLES_OPERATOR, False),
        OperationRoute("POST", f"{PRICING_PREFIX}/drafts", "wbeCreatePricingDraft", ROLES_OPERATOR, True),
        OperationRoute("GET", f"{PRICING_PREFIX}/drafts/{{draftId}}", "wbeGetPricingDraft", ROLES_OPERATOR, False),
        OperationRoute("PUT", f"{PRICING_PREFIX}/drafts/{{draftId}}", "wbeUpdatePricingDraft", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/drafts/{{draftId}}/simulate", "wbeSimulatePricingDraft", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/drafts/{{draftId}}/submit", "wbeSubmitPricingDraft", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/drafts/{{draftId}}/authorize", "wbeAuthorizePricingDraft", ROLES_FOUNDER, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/drafts/{{draftId}}/discard", "wbeDiscardPricingDraft", ROLES_OPERATOR, True),
        OperationRoute("GET", f"{PRICING_PREFIX}/versions", "wbeListPricingVersions", ROLES_OPERATOR, False),
        OperationRoute("GET", f"{PRICING_PREFIX}/versions/export", "wbeExportPricingVersions", ROLES_OPERATOR, False),
        OperationRoute("POST", f"{PRICING_PREFIX}/versions/import", "wbeImportPricingVersions", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/packages/{{packageId}}/activate-for-sale", "wbeActivatePackageForSale", ROLES_FOUNDER, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/safety/lower-ceiling", "wbeLowerPricingCeiling", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/safety/close-package", "wbeClosePackageToNewCustomers", ROLES_OPERATOR, True),
        OperationRoute("POST", f"{PRICING_PREFIX}/safety/disable-grant", "wbeDisablePricingGrant", ROLES_OPERATOR, True),
        OperationRoute("GET", f"{PRICING_PREFIX}/live-margin", "wbeGetPricingLiveMargin", ROLES_OPERATOR, False),
        OperationRoute("GET", f"{PRICING_PREFIX}/dashboard/funding", "wbeGetPricingFundingDashboard", ROLES_OPERATOR, False),
        OperationRoute("GET", f"{PRICING_PREFIX}/dashboard/margin", "wbeGetPricingMarginDashboard", ROLES_OPERATOR, False),
    )
}


# --------------------------------------------------------------------------------------- problems


class ProblemError(Exception):
    """A published problem; ``extra`` holds the optional problem members (violations, blockingPaise, ...)."""

    def __init__(self, status: int, code: str, title: str, detail: str | None = None, **extra: Any) -> None:
        super().__init__(title)
        self.status, self.code, self.title, self.detail, self.extra = status, code, title, detail, extra


def _violation_payload(violations: Sequence[Any]) -> list[dict[str, str]]:
    return [
        {"code": item.code, "path": item.field or "body", "message": (item.message or item.code)[:500]}
        for item in violations
    ][:100]


def problem_for(error: PricingError) -> ProblemError:
    code = _PUBLIC_CODES.get(error.code, error.code)
    extra: dict[str, Any] = {}
    if isinstance(error, PricingDraftInvalid):
        extra["violations"] = _violation_payload(error.violations)
        if isinstance(error, PricingBelowFloor) and error.minimum_compliant_price_paise is not None:
            extra["minimumCompliantPricePaise"] = error.minimum_compliant_price_paise
        if code == "PACKAGE_COMPONENT_NOT_AVAILABLE":
            component = next((item.details.get("componentId") for item in error.violations if item.details), None)
            if component:
                extra["componentId"] = component
    return ProblemError(error.status_code, code, code.replace("_", " ").capitalize(), error.message[:500], **extra)


def _problem_response(error: ProblemError, correlation_id: str) -> JSONResponse:
    content: dict[str, Any] = {
        "type": f"https://waooaw.com/problems/{error.code.lower().replace('_', '-')}",
        "title": error.title[:240],
        "status": error.status,
        "code": error.code,
        "correlationId": (correlation_id or str(uuid.uuid4()))[:64],
    }
    if error.detail:
        content["detail"] = error.detail[:500]
    content.update(error.extra)
    return JSONResponse(content, status_code=error.status, media_type=PROBLEM_MEDIA_TYPE)


# --------------------------------------------------------------------------------------- idempotency


class IdempotencyStore:
    """In-memory replay store per (actor, operation, key); a replay with another body digest conflicts.

    Process-local and bounded: it exists for unit doubles and single-process runs. The service uses
    ``SqlIdempotencyStore`` so a retry is replayed identically by any replica.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: OrderedDict[tuple[str, str, str], tuple[float, str, int, dict[str, Any]]] = OrderedDict()

    async def lookup(self, actor: str, operation: str, key: str, digest: str) -> tuple[int, dict[str, Any]] | None:
        entry = self._entries.get((actor, operation, key))
        if entry is None:
            return None
        stored_at, stored_digest, status, payload = entry
        if self._clock() - stored_at > IDEMPOTENCY_TTL_SECONDS:
            del self._entries[(actor, operation, key)]
            return None
        if stored_digest != digest:
            raise _idempotency_conflict()
        return status, payload

    async def remember(self, actor: str, operation: str, key: str, digest: str, status: int, payload: dict[str, Any]) -> None:
        self._entries[(actor, operation, key)] = (self._clock(), digest, status, payload)
        while len(self._entries) > IDEMPOTENCY_CAPACITY:
            self._entries.popitem(last=False)


def _idempotency_conflict() -> ProblemError:
    return ProblemError(
        409, "PRICING_IDEMPOTENCY_CONFLICT", "Idempotency key reused", "The key was used with another request body."
    )


class SqlIdempotencyStore:
    """Replay store in ``business.pricing_admin_idempotency`` (SQL 99zzzzzzzz-wc136-16).

    Shared by every replica and surviving restarts: a retry that lands anywhere gets the stored response
    for 24 hours, and a key reused with another body digest is a conflict. Entries are stored only after
    the write succeeded, in their own transaction; state changes remain guarded by the version state
    machine and ``expectedVersion``, so a crash between the two is refused on retry, never applied twice.
    """

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def _bounds(self, key: str) -> datetime:
        if not 1 <= len(key) <= 128:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "Idempotency-Key must be 1-128 characters.")
        return self._clock() - timedelta(seconds=IDEMPOTENCY_TTL_SECONDS)

    async def lookup(self, actor: str, operation: str, key: str, digest: str) -> tuple[int, dict[str, Any]] | None:
        expiry = self._bounds(key)
        async with get_session_factory()() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT request_digest, status_code, payload FROM business.pricing_admin_idempotency
                        WHERE actor_id = :actor AND operation = :operation AND idempotency_key = :key
                          AND stored_at >= :expiry
                        """
                    ),
                    {"actor": actor, "operation": operation, "key": key, "expiry": expiry},
                )
            ).first()
        if row is None:
            return None
        if row[0] != digest:
            raise _idempotency_conflict()
        payload = json.loads(row[2]) if isinstance(row[2], (str, bytes)) else row[2]
        return int(row[1]), payload

    async def remember(self, actor: str, operation: str, key: str, digest: str, status: int, payload: dict[str, Any]) -> None:
        expiry = self._bounds(key)
        async with get_session_factory()() as session:
            await session.execute(
                text("DELETE FROM business.pricing_admin_idempotency WHERE stored_at < :expiry"), {"expiry": expiry}
            )
            await session.execute(
                text(
                    """
                    INSERT INTO business.pricing_admin_idempotency
                    (actor_id, operation, idempotency_key, request_digest, status_code, payload, stored_at)
                    VALUES (:actor, :operation, :key, :digest, :status, CAST(:payload AS JSONB), :now)
                    ON CONFLICT (actor_id, operation, idempotency_key) DO NOTHING
                    """
                ),
                {
                    "actor": actor,
                    "operation": operation,
                    "key": key,
                    "digest": digest,
                    "status": status,
                    "payload": json.dumps(payload),
                    "now": self._clock(),
                },
            )
            await session.commit()


# --------------------------------------------------------------------------------------- caller


@dataclass(frozen=True)
class Caller:
    context: DelegatedContext
    actor: ActorContext
    correlation_id: str
    digest: str
    raw: bytes


def _role_of(context: DelegatedContext) -> EffectiveRole | None:
    try:
        return EffectiveRole(context.effective_role.strip().upper())
    except ValueError:
        return None


def _verify(request: Request, route: str, operation: str, digest: str, predicate: Callable[[DelegatedContext], bool]) -> DelegatedContext:
    auth = getattr(request.app.state, "relationship_workload_auth", None)
    certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
    authorization = request.headers.get("Authorization", "")
    if auth is None or certificate_der is None or not authorization.startswith("Bearer "):
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    peer_identity = extract_peer_identity(x509.load_der_x509_certificate(certificate_der), auth.trust_domain)
    return auth.verifier.verify(
        authorization.removeprefix("Bearer "),
        peer_identity,
        auth.audience,
        request.method,
        route,
        operation,
        1,
        digest,
        predicate,
    )


async def _enter(request: Request, operation: str) -> Caller:
    spec = OPERATIONS[operation]
    correlation_id = request.headers.get("X-Correlation-ID", "")
    idempotency_key = request.headers.get("Idempotency-Key", "")
    raw = await request.body()
    if len(raw) > MAXIMUM_BODY_BYTES:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Request too large")
    digest = hashlib.sha256(raw).hexdigest()

    def rebind(context: DelegatedContext) -> bool:
        return (
            bool(context.actor_subject)
            and _role_of(context) is not None
            and context.purpose in (ADMIN_PURPOSE, STEP_UP_PURPOSE)
            and (not correlation_id or context.correlation_id == correlation_id)
            and (not spec.writes or (bool(correlation_id) and context.idempotency_key == idempotency_key and bool(idempotency_key)))
        )

    try:
        context = _verify(request, spec.route, operation, digest, rebind)
    except (ServiceAuthError, ValueError) as error:
        logger.warning(
            "service_auth decision=deny target=billing-engine operation=%s reason_class=%s",
            operation,
            getattr(error, "code", "INVALID_PEER"),
        )
        raise ProblemError(401, "PRICING_FORBIDDEN", "Unauthorized", "The service assertion was refused.") from None
    logger.info("service_auth decision=allow target=billing-engine operation=%s policy_version=1.0", operation)
    role = _role_of(context)
    if role is None or role not in spec.roles:
        raise ProblemError(403, "PRICING_FORBIDDEN", "Forbidden", "The delegated role may not perform this operation.")
    actor = ActorContext(context.actor_subject, role, step_up=context.purpose == STEP_UP_PURPOSE)
    return Caller(context, actor, correlation_id or context.correlation_id, digest, raw)


def _json_body(caller: Caller) -> dict[str, Any]:
    try:
        body = json.loads(caller.raw or b"null")
    except ValueError:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "The body is not valid JSON.") from None
    if not isinstance(body, dict):
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "The body must be a JSON object.")
    if body.get("schemaVersion") != SCHEMA_VERSION:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "schemaVersion must be 1.0.")
    return body


def _field(body: Mapping[str, Any], name: str, kind: type | tuple[type, ...], *, required: bool = True) -> Any:
    value = body.get(name)
    if value is None:
        if required:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", f"{name} is required.")
        return None
    if isinstance(value, bool) and kind is not bool or not isinstance(value, kind):
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", f"{name} has the wrong type.")
    return value


def _uuid(value: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", f"{name} must be a UUID.") from None


def _deploy_maximum(body: Mapping[str, Any]) -> int | None:
    value = _field(body, "deployTimeMaximumPaise", int, required=False)
    if value is not None and value < 0:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "deployTimeMaximumPaise must not be negative.")
    return value


def _instant(value: Any, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", f"{name} must be a date-time.") from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------------------- mappers


def etag_of(version: PricingVersion) -> str:
    return f"{version.version_no}:{version.state.value}:{version.body_digest[:16]}"


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def version_payload(version: PricingVersion) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "versionId": str(version.version_id),
        "kind": version.kind.value,
        "subjectKey": version.subject_key,
        "versionNo": version.version_no,
        "state": version.state.value,
        "body": to_public(version.kind, version.body),
        "bodyDigest": version.body_digest,
        "seed": version.seed,
        "effectiveFrom": _iso(version.effective_from),
        "supersedes": None if version.supersedes is None else str(version.supersedes),
        "authorizedBy": version.authorized_by,
        "authorizedAt": _iso(version.authorized_at),
        "evidenceId": None if version.evidence_id is None else str(version.evidence_id),
        "needsSecondConfirmation": version.needs_second_confirmation,
        "secondConfirmedBy": version.second_confirmed_by,
        "createdBy": version.created_by,
        "createdAt": _iso(version.created_at),
    }
    treatment = tax_treatment(version.kind)
    if treatment is not None:
        payload["taxTreatment"] = treatment
    return payload


def _percent(value: float | None) -> float:
    return 0.0 if value is None else float(value)


def simulation_payload(
    version: PricingVersion,
    report: SimulationReport,
    now: datetime,
    effective_id: str | None,
    package_prices: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    projection = report.projection
    profiles: list[dict[str, Any]] = []
    for item in report.profiles:
        entry: dict[str, Any] = {
            "profile": item.profile if item.profile in (BEST_CASE, TYPICAL) else "CUSTOM",
            "expectedMonthlyCostPaise": item.total_cost_paise,
            "marginPercent": _percent(item.margin_pct),
        }
        if entry["profile"] == "CUSTOM":
            entry["personaName"] = item.profile
        profiles.append(entry)
    worst = report.worst_case
    if worst is not None:
        retained = worst.retained_base_paise
        profiles.append(
            {
                "profile": WORST_CASE,
                "expectedMonthlyCostPaise": worst.attempted_cost_paise,
                "marginPercent": round(100 * worst.margin_after_refund_paise / retained, 2) if retained > 0 else 0.0,
                "dayOneExposurePaise": worst.day_one_exposure_paise,
                "proRataRefundPaise": worst.refund_paise,
            }
        )
    warnings = [
        {"code": item.code, "message": item.message[:500], **_component(item)}
        for item in report.warnings
        if item.code in ("NEEDS_SECOND_CONFIRMATION", "PACKAGE_COMPONENT_NOT_AVAILABLE")
    ]
    if report.needs_second_confirmation and not any(item["code"] == "NEEDS_SECOND_CONFIRMATION" for item in warnings):
        warnings.append(
            {"code": "NEEDS_SECOND_CONFIRMATION", "message": "The change is larger than the change-size guard."}
        )
    diff: dict[str, Any] = {
        "changes": [
            {key: value for key, value in (("path", item.field), ("before", _text(item.before)), ("after", _text(item.after))) if value is not None}
            for item in [*report.changes, *report.projection_changes]
        ][:500]
    }
    if effective_id is not None:
        diff["effectiveVersionId"] = effective_id
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "draftId": str(version.version_id),
        "kind": version.kind.value,
        "state": version.state.value,
        "simulatedAt": _iso(now),
        "diff": diff,
        "profiles": profiles[:20],
        "warnings": warnings[:100],
        "affectedPackages": [
            {
                "packageVersionId": item.version_id,
                "subjectKey": item.subject_key,
                "currentFloorPaise": item.cost_floor_before_paise,
                "newFloorPaise": item.cost_floor_after_paise,
                "priceInclGstPaise": (package_prices or {}).get(item.version_id, 0),
                "belowFloor": item.breaches_cost_floor or item.breaches_minimum_margin,
            }
            for item in report.affected_packages
        ][:200],
    }
    if projection is not None:
        payload.update(
            {
                "costFloorPaise": projection.cost_floor_paise,
                "basePricePaise": projection.base_price_paise,
                "gstPaise": projection.gst_paise,
                "priceInclGstPaise": projection.price_incl_gst_paise,
                "taxTreatment": "GST_INCLUSIVE",
                "marginPercent": _percent(projection.margin_pct),
            }
        )
        if projection.minimum_compliant_price_paise is not None:
            payload["minimumCompliantPricePaise"] = projection.minimum_compliant_price_paise
    return payload


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return (value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str))[:500]


def _component(violation: Any) -> dict[str, str]:
    component = (violation.details or {}).get("componentId")
    return {"componentId": component} if isinstance(component, str) and component else {}


def live_margin_payload(breaches: Sequence[Any], packages_checked: int, now: datetime) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "computedAt": _iso(now),
        "packagesChecked": packages_checked,
        "breaches": [
            {
                "packageVersionId": item.version_id,
                "subjectKey": item.subject_key,
                "floorPaise": item.cost_floor_paise,
                "priceInclGstPaise": item.price_incl_gst_paise,
                "marginPercent": _percent(item.margin_pct),
                "minimumMarginPercent": _percent(item.minimum_margin_pct),
                "reason": "BELOW_FLOOR" if item.reason == "BELOW_COST_FLOOR" else item.reason,
            }
            for item in breaches
        ][:500],
    }


# --------------------------------------------------------------------------------------- service composition


@dataclass
class PricingRuntime:
    """Per-process dependencies; ``unit`` yields a service bound to one database session."""

    declarations: ManifestDeclarationSource
    signer: BundleSigner
    store: IdempotencyStore | SqlIdempotencyStore
    clock: Callable[[], datetime]

    def service_for(self, session: Any) -> PricingService:
        from ce_validator import CE  # imported lazily: the validator reads settings at import time
        from pricing.margin_watch import LoggingBreachReporter
        from pricing.repository import SqlPricingRepository
        from pricing.service import CeEvidenceRecorder
        from markup.package_engine import SqlPackageReferenceData

        return PricingService(
            repository=SqlPricingRepository(session),
            reference=RegistryAliasedReference(SqlPackageReferenceData(session)),
            declarations=self.declarations,
            evidence=CeEvidenceRecorder(CE.validate_action),
            clock=self.clock,
            breach_reporter=LoggingBreachReporter(),
        )


def configure_pricing_admin(application: FastAPI) -> None:
    contracts = Path(os.getenv("WBE_AGENT_CONTRACTS_ROOT", "agent-contracts"))
    def clock() -> datetime:
        return datetime.now(timezone.utc)

    application.state.pricing_runtime = PricingRuntime(
        declarations=ManifestDeclarationSource.from_directory(contracts),
        signer=BundleSigner.from_environment(),
        store=SqlIdempotencyStore(clock),
        clock=clock,
    )


def _runtime(request: Request) -> PricingRuntime:
    runtime = getattr(request.app.state, "pricing_runtime", None)
    if runtime is None:
        raise ProblemError(503, "PRICING_UNAVAILABLE", "Pricing unavailable", "Pricing administration is not configured.")
    return runtime


async def _run(request: Request, operation: str, handler: Callable[[Caller, PricingRuntime, PricingService, Any], Awaitable[Response]]) -> Response:
    """Authenticate, replay or execute ``handler`` with one service/session, and map every failure."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        caller = await _enter(request, operation)
        runtime = _runtime(request)
        spec = OPERATIONS[operation]
        key = request.headers.get("Idempotency-Key", "")
        if spec.writes:
            try:
                stored = await runtime.store.lookup(caller.actor.actor_id, operation, key, caller.digest)
            except ProblemError:
                raise
            except Exception as error:
                logger.exception("pricing_admin_idempotency_lookup_failed", extra={"operation": operation})
                raise ProblemError(503, "PRICING_UNAVAILABLE", "Pricing unavailable", "The request can be retried.") from error
            if stored is not None:
                status = 200 if stored[0] == 201 else stored[0]
                return JSONResponse(stored[1], status_code=status, headers=_etag_header(stored[1]))
        try:
            async with get_session_factory()() as session:
                response = await handler(caller, runtime, runtime.service_for(session), session)
        except PricingError as error:
            raise problem_for(error) from error
        except ProblemError:
            raise
        except Exception as error:
            logger.exception("pricing_admin_failed", extra={"operation": operation})
            raise ProblemError(503, "PRICING_UNAVAILABLE", "Pricing unavailable", "The request can be retried.") from error
        if spec.writes and isinstance(response, JSONResponse) and response.status_code < 300:
            try:
                await runtime.store.remember(
                    caller.actor.actor_id, operation, key, caller.digest, response.status_code, json.loads(response.body)
                )
            except Exception:
                # The write is committed; a retry is refused by the version guard instead of being applied twice.
                logger.exception("pricing_admin_idempotency_store_failed", extra={"operation": operation})
        return response
    except ProblemError as error:
        return _problem_response(error, correlation_id)


def _etag_header(payload: Mapping[str, Any]) -> dict[str, str]:
    version_no, state, digest = payload.get("versionNo"), payload.get("state"), payload.get("bodyDigest")
    if isinstance(version_no, int) and isinstance(state, str) and isinstance(digest, str):
        return {"ETag": f'"{version_no}:{state}:{digest[:16]}"'}
    return {}


def _ok(payload: Mapping[str, Any], status: int = 200) -> JSONResponse:
    return JSONResponse(dict(payload), status_code=status, headers=_etag_header(payload))


def _check_expected(version: PricingVersion, body: Mapping[str, Any]) -> None:
    expected = _field(body, "expectedVersion", str)
    if expected.strip('"') != etag_of(version):
        raise ProblemError(
            409, "PRICING_VERSION_CONFLICT", "Version conflict", "The version changed since it was read; reload it."
        )


def _kind(value: Any) -> PricingKind:
    try:
        return PricingKind(value)
    except ValueError:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "kind is not a pricing kind.") from None


def _state(value: str | None) -> VersionState | None:
    if value is None:
        return None
    try:
        return VersionState(value)
    except ValueError:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "state is not a version state.") from None


def _page(request: Request) -> tuple[int, int]:
    raw_limit = request.query_params.get("limit")
    limit = DEFAULT_PAGE_SIZE
    if raw_limit is not None:
        if not raw_limit.isdigit() or not 1 <= int(raw_limit) <= MAXIMUM_PAGE_SIZE:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "limit must be 1 to 100.")
        limit = int(raw_limit)
    cursor = request.query_params.get("cursor")
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except (ValueError, UnicodeError):
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "cursor is invalid.") from None
        if offset < 0:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "cursor is invalid.")
    return limit, offset


def _listing(versions: Sequence[PricingVersion], limit: int, offset: int) -> dict[str, Any]:
    window = list(versions[offset : offset + limit])
    payload: dict[str, Any] = {"schemaVersion": SCHEMA_VERSION, "items": [version_payload(item) for item in window]}
    if len(versions) > offset + limit:
        payload["nextCursor"] = base64.urlsafe_b64encode(str(offset + limit).encode()).decode()
    return payload


def _period(request: Request) -> tuple[date | None, date | None]:
    values: list[date | None] = []
    for name in ("from", "to"):
        raw = request.query_params.get(name)
        try:
            values.append(None if raw is None else date.fromisoformat(raw))
        except ValueError:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", f"{name} must be a date.") from None
    if values[0] and values[1] and values[0] > values[1]:
        raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "from must not be after to.")
    return values[0], values[1]


# --------------------------------------------------------------------------------------- routes: drafts


@router.get("/drafts")
async def wbe_list_pricing_drafts(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        limit, offset = _page(request)
        kind = request.query_params.get("kind")
        subject = request.query_params.get("subjectKey")
        requested = _state(request.query_params.get("state"))
        states = (requested,) if requested else PENDING_STATES
        found: list[PricingVersion] = []
        for state in states:
            found.extend(
                await service.list_versions(
                    kind=None if kind is None else _kind(kind),
                    subject_key=subject,
                    state=state,
                    limit=offset + limit + 1,
                )
            )
        found.sort(key=lambda item: (item.created_at, str(item.version_id)), reverse=True)
        return _ok(_listing(found, limit, offset))

    return await _run(request, "wbeListPricingDrafts", handler)


@router.post("/drafts")
async def wbe_create_pricing_draft(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        kind = _kind(body.get("kind"))
        subject = _field(body, "subjectKey", str)
        draft_body = _field(body, "body", dict)
        internal = to_internal(kind, draft_body)
        try:
            derived = subject_key_for(kind, _BODY_MODELS[kind].model_validate(internal))
        except Exception:  # a body that does not fit its kind is refused with full violations by the service
            derived = None
        if derived is not None and derived != subject:
            raise ProblemError(
                422,
                "PRICING_DRAFT_INVALID",
                "Pricing draft invalid",
                "The subject key does not match the body.",
                violations=[{"code": "PRICING_SUBJECT_MISMATCH", "path": "subjectKey", "message": f"The body belongs to {derived}."}],
            )
        result = await service.create_draft(caller.actor, kind, internal, deploy_maximum_paise=_deploy_maximum(body))
        return _ok(version_payload(result.version), 201)

    return await _run(request, "wbeCreatePricingDraft", handler)


@router.get("/drafts/{draft_id}")
async def wbe_get_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        return _ok(version_payload(await _load(service, draft_id)))

    return await _run(request, "wbeGetPricingDraft", handler)


async def _load(service: PricingService, identifier: str) -> PricingVersion:
    try:
        return await service.get_version(_uuid(identifier, "draftId"))
    except PricingVersionNotFound as error:
        raise problem_for(error) from error


@router.put("/drafts/{draft_id}")
async def wbe_update_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, draft_id)
        _check_expected(existing, body)
        internal = to_internal(existing.kind, _field(body, "body", dict))
        result = await service.update_draft(
            caller.actor, existing.version_id, internal, deploy_maximum_paise=_deploy_maximum(body)
        )
        return _ok(version_payload(result.version))

    return await _run(request, "wbeUpdatePricingDraft", handler)


@router.post("/drafts/{draft_id}/simulate")
async def wbe_simulate_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, draft_id)
        _check_expected(existing, body)
        personas = [
            PersonaProfile(
                name=str(_field(item, "name", str)),
                default_usage_percent=round(100 * float(_field(item, "quantityFraction", (int, float)))),
            )
            for item in _field(body, "usageProfiles", list, required=False) or []
            if isinstance(item, dict)
        ]
        result = await service.simulate(
            caller.actor, existing.version_id, personas=personas, deploy_maximum_paise=_deploy_maximum(body)
        )
        effective = await service.effective_version(existing.kind, existing.subject_key, runtime.clock())
        prices = {
            str(item.version_id): int(item.body.get("priceInclGstPaise", 0))
            for item in await service.effective_versions(PricingKind.PACKAGE, runtime.clock())
        }
        return _ok(
            simulation_payload(
                result.version,
                result.report,
                runtime.clock(),
                None if effective is None else str(effective.version_id),
                prices,
            )
        )

    return await _run(request, "wbeSimulatePricingDraft", handler)


@router.post("/drafts/{draft_id}/submit")
async def wbe_submit_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, draft_id)
        _check_expected(existing, body)
        version = await service.submit(
            caller.actor,
            existing.version_id,
            second_confirmation=bool(body.get("secondConfirmation", False)),
            deploy_maximum_paise=_deploy_maximum(body),
        )
        return _ok(version_payload(version))

    return await _run(request, "wbeSubmitPricingDraft", handler)


@router.post("/drafts/{draft_id}/authorize")
async def wbe_authorize_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, draft_id)
        _check_expected(existing, body)
        effective_from = body.get("effectiveFrom")
        version = await service.authorize(
            caller.actor,
            existing.version_id,
            effective_from=None if effective_from is None else _instant(effective_from, "effectiveFrom"),
            deploy_maximum_paise=_deploy_maximum(body),
        )
        return _ok(version_payload(version))

    return await _run(request, "wbeAuthorizePricingDraft", handler)


@router.post("/drafts/{draft_id}/discard")
async def wbe_discard_pricing_draft(draft_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, draft_id)
        _check_expected(existing, body)
        reason = _field(body, "reason", str)
        version = (
            await service.withdraw(caller.actor, existing.version_id, reason)
            if existing.state is VersionState.SUBMITTED
            else await service.discard(caller.actor, existing.version_id, reason)
        )
        return _ok(version_payload(version))

    return await _run(request, "wbeDiscardPricingDraft", handler)


# --------------------------------------------------------------------------------------- routes: versions


@router.get("/versions")
async def wbe_list_pricing_versions(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        limit, offset = _page(request)
        kind = request.query_params.get("kind")
        found = await service.list_versions(
            kind=None if kind is None else _kind(kind),
            subject_key=request.query_params.get("subjectKey"),
            state=_state(request.query_params.get("state")),
            limit=offset + limit + 1,
        )
        return _ok(_listing(found, limit, offset))

    return await _run(request, "wbeListPricingVersions", handler)


@router.get("/versions/export")
async def wbe_export_pricing_versions(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        return _ok(await export_bundle(service, caller.actor.actor_id, runtime.signer, runtime.clock()))

    return await _run(request, "wbeExportPricingVersions", handler)


@router.post("/versions/import")
async def wbe_import_pricing_versions(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        bundle = _field(body, "bundle", dict)
        result = await import_bundle(
            service, caller.actor, bundle, runtime.signer, deploy_maximum_paise=_deploy_maximum(body)
        )
        return _ok({"schemaVersion": SCHEMA_VERSION, **result})

    return await _run(request, "wbeImportPricingVersions", handler)


@router.post("/packages/{package_id}/activate-for-sale")
async def wbe_activate_package_for_sale(package_id: str, request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        existing = await _load(service, package_id)
        _check_expected(existing, body)
        version = await service.activate_for_sale(caller.actor, existing.version_id)
        evidence = version.evidence_id
        for event in reversed(await service.list_events(version.version_id)):
            matched = _EVIDENCE_REASON.match(event.reason or "")
            if matched:
                evidence = uuid.UUID(matched.group("evidence"))
                break
        return _ok(
            {
                "schemaVersion": SCHEMA_VERSION,
                "packageId": str(version.version_id),
                "forSale": True,
                "activatedBy": caller.actor.actor_id,
                "activatedAt": _iso(runtime.clock()),
                "evidenceId": None if evidence is None else str(evidence),
            }
        )

    return await _run(request, "wbeActivatePackageForSale", handler)


# --------------------------------------------------------------------------------------- routes: safety


def _safety_payload(version: PricingVersion, now: datetime, notified: bool = True) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "direction": "SAFETY",
        "versionId": str(version.version_id),
        "state": version.state.value,
        "appliedAt": _iso(now),
        "founderNotified": notified,
    }


@router.post("/safety/lower-ceiling")
async def wbe_lower_pricing_ceiling(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        scope = _field(body, "scope", str)
        reference = _field(body, "ref", str)
        maximum = _field(body, "newMaximumPaise", int)
        subject = f"budget:{scope}|{reference}"
        if not _SAFETY_SUBJECT.match(subject) or maximum < 0:
            raise ProblemError(400, "PRICING_REQUEST_INVALID", "Malformed request", "The budget subject is invalid.")
        version = await service.lower_ceiling(caller.actor, subject, maximum, _field(body, "reason", str))
        return _ok(_safety_payload(version, runtime.clock()))

    return await _run(request, "wbeLowerPricingCeiling", handler)


@router.post("/safety/close-package")
async def wbe_close_package(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        package = _uuid(_field(body, "packageId", str), "packageId")
        version = await service.close_package(caller.actor, package, _field(body, "reason", str))
        return _ok(_safety_payload(version, runtime.clock()))

    return await _run(request, "wbeClosePackageToNewCustomers", handler)


@router.post("/safety/disable-grant")
async def wbe_disable_grant(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        body = _json_body(caller)
        version = await service.disable_grant(
            caller.actor, _field(body, "subjectKey", str), _field(body, "reason", str)
        )
        return _ok(_safety_payload(version, runtime.clock()))

    return await _run(request, "wbeDisablePricingGrant", handler)


# --------------------------------------------------------------------------------------- routes: reports


@router.get("/live-margin")
async def wbe_get_pricing_live_margin(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        now = runtime.clock()
        breaches = await service.live_margin(now)
        checked = len(await service.effective_versions(PricingKind.PACKAGE, now))
        return _ok(live_margin_payload(breaches, checked, now))

    return await _run(request, "wbeGetPricingLiveMargin", handler)


@router.get("/dashboard/funding")
async def wbe_get_pricing_funding_dashboard(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        start, end = _period(request)
        now = runtime.clock()
        return _ok(
            await dashboard_reports.funding_dashboard(
                session, service, period_from=start, period_to=end, now=now
            )
        )

    return await _run(request, "wbeGetPricingFundingDashboard", handler)


@router.get("/dashboard/margin")
async def wbe_get_pricing_margin_dashboard(request: Request) -> Response:
    async def handler(caller: Caller, runtime: PricingRuntime, service: PricingService, session: Any) -> Response:
        start, end = _period(request)
        now = runtime.clock()
        return _ok(
            await dashboard_reports.margin_dashboard(session, service, period_from=start, period_to=end, now=now)
        )

    return await _run(request, "wbeGetPricingMarginDashboard", handler)
