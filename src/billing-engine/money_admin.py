# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006, WC172-R010, WC172-R011
# Constitutional basis: C-007, C-059, C-063, C-066, C-088, ADR-046
"""Private WBE money controls for the Founder: the real-money gate, money discrepancies and every tax document.

Reachable only through the workload-identity path of the pricing administration (mutually authenticated peer
certificate plus a delegated context bound to the route, operation, method and body digest). Turning real money on
needs the Founder's step-up context; every other write is a Founder act with a reason or evidence.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from config import Settings
from database import get_session_factory
from invoicing.hooks import service_for
from payment.money_gate import MoneyGate, MoneyGateError
from payment.money_reconciliation import MoneyReconciliationError, list_discrepancies, resolve_discrepancy
from pricing.models import EffectiveRole
from pricing_admin import (
    ADMIN_PURPOSE,
    SCHEMA_VERSION,
    STEP_UP_PURPOSE,
    Caller,
    ProblemError,
    OperationRoute,
    _field,
    _json_body,
    _problem_response,
    _role_of,
    _uuid,
    _verify,
)
from pricing.models import ActorContext
from workload_identity import DelegatedContext, ServiceAuthError

logger = logging.getLogger(__name__)

MONEY_PREFIX = "/internal/v1/money"
ROLES_OPERATOR = frozenset({EffectiveRole.PRICING_ADMIN, EffectiveRole.FOUNDER})
ROLES_FOUNDER = frozenset({EffectiveRole.FOUNDER})

OPERATIONS: dict[str, OperationRoute] = {
    item.operation: item
    for item in (
        OperationRoute("GET", f"{MONEY_PREFIX}/tax-documents", "wbeFounderListTaxDocuments", ROLES_FOUNDER, False),
        OperationRoute("GET", f"{MONEY_PREFIX}/tax-documents/{{documentId}}", "wbeFounderGetTaxDocument", ROLES_FOUNDER, False),
        OperationRoute("GET", f"{MONEY_PREFIX}/gate", "wbeGetMoneyGate", ROLES_OPERATOR, False),
        OperationRoute("POST", f"{MONEY_PREFIX}/gate", "wbeSetMoneyGate", ROLES_FOUNDER, True),
        OperationRoute("GET", f"{MONEY_PREFIX}/discrepancies", "wbeListMoneyDiscrepancies", ROLES_OPERATOR, False),
        OperationRoute("POST", f"{MONEY_PREFIX}/discrepancies/{{discrepancyId}}/resolve", "wbeResolveMoneyDiscrepancy", ROLES_FOUNDER, True),
    )
}

router = APIRouter(prefix=MONEY_PREFIX, tags=["Money Controls Private"])


async def _enter(request: Request, operation: str) -> Caller:
    spec = OPERATIONS[operation]
    correlation_id = request.headers.get("X-Correlation-ID", "")
    idempotency_key = request.headers.get("Idempotency-Key", "")
    raw = await request.body()
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
            operation, getattr(error, "code", "INVALID_PEER"),
        )
        raise ProblemError(401, "MONEY_FORBIDDEN", "Unauthorized", "The service assertion was refused.") from None
    role = _role_of(context)
    if role is None or role not in spec.roles:
        raise ProblemError(403, "MONEY_FORBIDDEN", "Forbidden", "The delegated role may not perform this operation.")
    actor = ActorContext(context.actor_subject, role, step_up=context.purpose == STEP_UP_PURPOSE)
    return Caller(context, actor, correlation_id or context.correlation_id, digest, raw)


async def _run(
    request: Request, operation: str, handler: Callable[[Caller, Any], Awaitable[Response]]
) -> Response:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        caller = await _enter(request, operation)
        try:
            async with get_session_factory()() as session:
                return await handler(caller, session)
        except ProblemError:
            raise
        except Exception as error:
            logger.exception("money_admin_failed", extra={"operation": operation})
            raise ProblemError(503, "MONEY_UNAVAILABLE", "Unavailable", "The request can be retried.") from error
    except ProblemError as error:
        return _problem_response(error, correlation_id)


def _clock() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/tax-documents")
async def wbe_founder_list_tax_documents(request: Request, limit: int = 50) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        documents = await service_for(session, Settings()).list_documents(limit=max(1, min(limit, 200)))
        return JSONResponse({"schemaVersion": SCHEMA_VERSION, "documents": [item.as_public() for item in documents]})

    return await _run(request, "wbeFounderListTaxDocuments", handler)


@router.get("/tax-documents/{document_id}")
async def wbe_founder_get_tax_document(document_id: str, request: Request) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        document = await service_for(session, Settings()).get(_uuid(document_id, "documentId"))
        if document is None:
            raise ProblemError(404, "MONEY_NOT_FOUND", "Not found", "The tax document does not exist.")
        return JSONResponse({"schemaVersion": SCHEMA_VERSION, "document": document.as_public()})

    return await _run(request, "wbeFounderGetTaxDocument", handler)


@router.get("/gate")
async def wbe_get_money_gate(request: Request) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        settings = Settings()
        state = await MoneyGate(session, settings.WAOOAW_ENVIRONMENT, settings.RAZORPAY_PAYMENT_MODE).state()
        return JSONResponse({"schemaVersion": SCHEMA_VERSION, **state.as_public()})

    return await _run(request, "wbeGetMoneyGate", handler)


@router.post("/gate")
async def wbe_set_money_gate(request: Request) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        body = _json_body(caller)
        enabled = _field(body, "enabled", bool)
        reason = _field(body, "reason", str)
        settings = Settings()
        gate = MoneyGate(session, settings.WAOOAW_ENVIRONMENT, settings.RAZORPAY_PAYMENT_MODE, now=_clock)
        try:
            state = await gate.set(enabled, caller.actor.actor_id, caller.actor.step_up, reason)
        except MoneyGateError as error:
            status = 403 if error.code == "MONEY_GATE_STEP_UP_REQUIRED" else 409
            raise ProblemError(status, error.code, "Refused", error.code) from None
        await session.commit()
        logger.warning("money_gate changed enabled=%s environment=%s actor=%s", enabled, settings.WAOOAW_ENVIRONMENT, caller.actor.actor_id)
        return JSONResponse({"schemaVersion": SCHEMA_VERSION, **state.as_public()})

    return await _run(request, "wbeSetMoneyGate", handler)


@router.get("/discrepancies")
async def wbe_list_money_discrepancies(request: Request) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        return JSONResponse(
            {"schemaVersion": SCHEMA_VERSION, "discrepancies": await list_discrepancies(session, open_only=False)}
        )

    return await _run(request, "wbeListMoneyDiscrepancies", handler)


@router.post("/discrepancies/{discrepancy_id}/resolve")
async def wbe_resolve_money_discrepancy(discrepancy_id: str, request: Request) -> Response:
    async def handler(caller: Caller, session: Any) -> Response:
        body = _json_body(caller)
        evidence = _uuid(_field(body, "evidenceId", str), "evidenceId")
        try:
            await resolve_discrepancy(session, _uuid(discrepancy_id, "discrepancyId"), caller.actor.actor_id, evidence, _clock())
        except MoneyReconciliationError as error:
            raise ProblemError(409, error.code, "Refused", error.code) from None
        await session.commit()
        return JSONResponse({"schemaVersion": SCHEMA_VERSION, "resolved": True})

    return await _run(request, "wbeResolveMoneyDiscrepancy", handler)
