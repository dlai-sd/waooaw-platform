# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
# Constitutional basis: C-059, C-063, C-088, C-089
"""Private WBE wallet routes: parity read (C4-03), idempotent setup-grant open and reserve on
platform-owned accounts (C4-04), settle and release of any reservation, the setup-grant draw (C4-09)
and the customer-safe package catalogue (C4-13).

All routes are reachable only through the workload-identity path used by the relationship
workspace router: mutually authenticated peer certificate plus a delegated context bound to the
route, operation and (for the POSTs) the idempotency key and body digest.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from cryptography import x509
from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from database import get_session_factory
from package_catalog import CatalogCursorError, PackageCatalog
from relationship_workspace import _digest
from wallet.entity_models import ReservationIdentity, WalletError
from wallet.ledger import WalletLedger
from wallet.parity import DEFAULT_PARITY_LIMIT, ParityRow, report_parity
from wallet.platform_accounts import PlatformAccounts
from workload_identity import (
    PEER_CERTIFICATE_STATE_KEY,
    DelegatedContext,
    ServiceAuthError,
    extract_peer_identity,
)

logger = logging.getLogger(__name__)

PARITY_ROUTE = "/internal/v1/wallet/parity"
PARITY_OPERATION = "wbeGetWalletParity"
SETUP_GRANT_ROUTE = "/internal/v1/relationships/{relationshipId}/setup-grant"
SETUP_GRANT_OPERATION = "wbeOpenSetupGrant"
ACCOUNT_RESERVE_ROUTE = "/internal/v1/wallet/accounts/reserve"
ACCOUNT_RESERVE_OPERATION = "wbeReserveWalletAccount"
SETUP_GRANT_RESERVE_ROUTE = "/internal/v1/relationships/{relationshipId}/setup-grant/reserve"
SETUP_GRANT_RESERVE_OPERATION = "wbeReserveSetupGrant"
RESERVATION_SETTLE_ROUTE = "/internal/v1/wallet/reservations/settle"
RESERVATION_SETTLE_OPERATION = "wbeSettleWalletReservation"
RESERVATION_RELEASE_ROUTE = "/internal/v1/wallet/reservations/release"
RESERVATION_RELEASE_OPERATION = "wbeReleaseWalletReservation"
PACKAGES_ROUTE = "/internal/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages"
PACKAGES_OPERATION = "wbeListForSalePackages"
_VERSION_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"
_HOLD_SECONDS = 900
_UNPROCESSABLE_CODES = frozenset({"WALLET_AMOUNT_INVALID", "WALLET_ACCOUNT_INVALID"})

router = APIRouter(prefix="/internal/v1", tags=["Wallet Private"])


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SetupGrantRequest(_Strict):
    agent_type: str = Field(alias="agentType", min_length=1, max_length=100)
    agent_version: str = Field(alias="agentVersion", pattern=_VERSION_PATTERN)


class SetupGrantResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    status: str
    account_id: uuid.UUID = Field(alias="accountId")
    lot_id: uuid.UUID | None = Field(default=None, alias="lotId")
    credited_paise: int = Field(alias="creditedPaise")
    created: bool


class AccountReserveRequest(_Strict):
    account_class: Literal["ACQUISITION", "SIMULATION", "PLATFORM_FLOOR"] = Field(alias="accountClass")
    environment: str | None = Field(default=None, min_length=1, max_length=64)
    campaign_ref: str | None = Field(default=None, alias="campaignRef", min_length=1, max_length=64)
    lead_ref: str | None = Field(default=None, alias="leadRef", min_length=1, max_length=64)
    component_id: str = Field(alias="componentId", min_length=1, max_length=100)
    maximum_paise: int = Field(alias="maximumPaise", ge=0, le=100_000_000)
    purpose: str | None = Field(default=None, min_length=1, max_length=64)
    invocation_id: uuid.UUID = Field(alias="invocationId")
    owner_evidence_id: uuid.UUID = Field(alias="ownerEvidenceId")


class AccountReserveResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    account_class: str = Field(alias="accountClass")
    reservation_id: uuid.UUID = Field(alias="reservationId")
    account_id: uuid.UUID = Field(alias="accountId")
    state: str
    reserved_paise: int = Field(alias="reservedPaise")
    replayed: bool


class ParityRowResponse(_Strict):
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    component_id: str = Field(alias="componentId")
    allowance_open_paise: int = Field(alias="allowanceOpenPaise")
    allowance_settled_paise: int = Field(alias="allowanceSettledPaise")
    wallet_open_paise: int = Field(alias="walletOpenPaise")
    wallet_settled_paise: int = Field(alias="walletSettledPaise")
    open_difference_paise: int = Field(alias="openDifferencePaise")
    settled_difference_paise: int = Field(alias="settledDifferencePaise")


class ParityResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    checked_at: datetime = Field(alias="checkedAt")
    clean: bool
    compared: int
    truncated: bool
    differences: list[ParityRowResponse]


def _row_response(row: ParityRow) -> ParityRowResponse:
    return ParityRowResponse(
        relationshipId=row.relationship_id,
        componentId=row.component_id,
        allowanceOpenPaise=row.allowance_open_paise,
        allowanceSettledPaise=row.allowance_settled_paise,
        walletOpenPaise=row.wallet_open_paise,
        walletSettledPaise=row.wallet_settled_paise,
        openDifferencePaise=row.open_difference_paise,
        settledDifferencePaise=row.settled_difference_paise,
    )


def _verify(
    request: Request,
    route: str,
    operation: str,
    body: object | None,
    predicate: Any,
) -> DelegatedContext:
    auth = getattr(request.app.state, "relationship_workload_auth", None)
    certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
    authorization = request.headers.get("Authorization", "")
    if auth is None or certificate_der is None or not authorization.startswith("Bearer "):
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    peer_identity = extract_peer_identity(
        x509.load_der_x509_certificate(certificate_der), auth.trust_domain
    )
    return auth.verifier.verify(
        authorization.removeprefix("Bearer "),
        peer_identity,
        auth.audience,
        request.method,
        route,
        operation,
        1,
        _digest(body),
        predicate,
    )


def _unauthorized(operation: str, error: ServiceAuthError) -> HTTPException:
    logger.warning(
        "service_auth decision=deny target=billing-engine operation=%s reason_class=%s",
        operation,
        error.code,
    )
    return HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED")


@router.get("/wallet/parity", response_model=ParityResponse, response_model_by_alias=True)
async def get_wallet_parity(
    request: Request,
    tenant_id: Annotated[uuid.UUID, Query(alias="tenantId")],
    relationship_id: Annotated[uuid.UUID | None, Query(alias="relationshipId")] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = DEFAULT_PARITY_LIMIT,
) -> ParityResponse:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        _verify(
            request,
            PARITY_ROUTE,
            PARITY_OPERATION,
            None,
            lambda context: context.tenant_id == str(tenant_id)
            and bool(context.actor_subject)
            and context.correlation_id == correlation_id,
        )
    except ServiceAuthError as error:
        raise _unauthorized(PARITY_OPERATION, error) from None
    async with get_session_factory()() as session:
        report = await report_parity(session, tenant_id, relationship_id, limit=limit)
    return ParityResponse(
        checkedAt=report.checked_at,
        clean=report.clean,
        compared=report.compared,
        truncated=report.truncated,
        differences=[_row_response(row) for row in report.differences],
    )


@router.post(
    "/relationships/{relationship_id}/setup-grant",
    response_model=SetupGrantResponse,
    response_model_by_alias=True,
)
async def open_setup_grant(
    relationship_id: uuid.UUID,
    body: SetupGrantRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> SetupGrantResponse:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    payload = body.model_dump(by_alias=True, mode="json")
    try:
        context = _verify(
            request,
            SETUP_GRANT_ROUTE,
            SETUP_GRANT_OPERATION,
            payload,
            lambda ctx: ctx.relationship_id == str(relationship_id)
            and bool(ctx.tenant_id)
            and bool(ctx.actor_subject)
            and ctx.correlation_id == correlation_id
            and ctx.idempotency_key == idempotency_key,
        )
        tenant_id = uuid.UUID(context.tenant_id)
    except ServiceAuthError as error:
        raise _unauthorized(SETUP_GRANT_OPERATION, error) from None
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED") from None
    try:
        async with get_session_factory()() as session, session.begin():
            opened = await PlatformAccounts(session).open_setup_grant(
                tenant_id, relationship_id, body.agent_type, body.agent_version
            )
    except WalletError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return SetupGrantResponse(
        status="GRANTED" if opened.lot_id is not None else "NO_GRANT",
        accountId=opened.account.account_id,
        lotId=opened.lot_id,
        creditedPaise=opened.credited_paise,
        created=opened.created,
    )


def _refusal(error: WalletError) -> HTTPException:
    return HTTPException(
        status_code=422 if error.code in _UNPROCESSABLE_CODES else 409,
        detail={"code": error.code, "level": error.detail},
    )


@router.post(
    "/wallet/accounts/reserve",
    response_model=AccountReserveResponse,
    response_model_by_alias=True,
)
async def reserve_platform_account(
    body: AccountReserveRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> AccountReserveResponse:
    """Reserve on a platform-owned account; PLATFORM_FLOOR is recorded and never gated."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    # The signer omits absent optional fields, so the digest is computed over the same shape.
    payload = body.model_dump(by_alias=True, mode="json", exclude_none=True)
    try:
        key = uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(status_code=422, detail="WBE_WALLET_IDEMPOTENCY_KEY_INVALID") from None
    try:
        context = _verify(
            request,
            ACCOUNT_RESERVE_ROUTE,
            ACCOUNT_RESERVE_OPERATION,
            payload,
            lambda ctx: bool(ctx.tenant_id)
            and bool(ctx.actor_subject)
            and ctx.correlation_id == correlation_id
            and ctx.idempotency_key == idempotency_key,
        )
        tenant_id = uuid.UUID(context.tenant_id)
    except ServiceAuthError as error:
        raise _unauthorized(ACCOUNT_RESERVE_OPERATION, error) from None
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED") from None
    if body.account_class != "ACQUISITION" and not body.environment:
        raise HTTPException(status_code=422, detail="WBE_WALLET_ENVIRONMENT_REQUIRED")
    if body.account_class == "PLATFORM_FLOOR" and not body.purpose:
        raise HTTPException(status_code=422, detail="WBE_WALLET_PURPOSE_REQUIRED")
    identity = ReservationIdentity(
        invocation_id=body.invocation_id, evidence_id=body.owner_evidence_id
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_HOLD_SECONDS)
    try:
        async with get_session_factory()() as session, session.begin():
            accounts = PlatformAccounts(session)
            if body.account_class == "PLATFORM_FLOOR":
                floor = await accounts.record_floor_use(
                    tenant_id,
                    body.environment or "",
                    body.purpose or "",
                    body.component_id,
                    body.maximum_paise,
                    body.owner_evidence_id,
                    invocation_id=body.invocation_id,
                    use_id=key,
                )
                return AccountReserveResponse(
                    accountClass=body.account_class,
                    reservationId=floor.use_id,
                    accountId=floor.account_id,
                    state="RECORDED",
                    reservedPaise=body.maximum_paise,
                    replayed=not floor.recorded,
                )
            if body.account_class == "SIMULATION":
                receipt = await accounts.reserve_simulation(
                    tenant_id,
                    body.environment or "",
                    body.component_id,
                    body.maximum_paise,
                    expires_at,
                    identity,
                    key,
                )
            else:
                receipt = await accounts.reserve_acquisition(
                    tenant_id,
                    body.component_id,
                    body.maximum_paise,
                    expires_at,
                    identity,
                    key,
                    campaign_ref=body.campaign_ref,
                    lead_ref=body.lead_ref,
                )
    except WalletError as error:
        raise _refusal(error) from None
    return AccountReserveResponse(
        accountClass=body.account_class,
        reservationId=receipt.reservation_id,
        accountId=receipt.account_id,
        state=receipt.state,
        reservedPaise=receipt.reserved_paise,
        replayed=receipt.replayed,
    )


class SetupGrantReserveRequest(_Strict):
    agent_type: str = Field(alias="agentType", min_length=1, max_length=100)
    agent_version: str = Field(alias="agentVersion", pattern=_VERSION_PATTERN)
    component_id: str = Field(alias="componentId", min_length=1, max_length=100)
    maximum_paise: int = Field(alias="maximumPaise", ge=1, le=100_000_000)
    invocation_id: uuid.UUID = Field(alias="invocationId")
    owner_evidence_id: uuid.UUID = Field(alias="ownerEvidenceId")


class SetupGrantReserveResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    status: Literal["RESERVED", "SETUP_GRANT_EXHAUSTED"]
    account_id: uuid.UUID = Field(alias="accountId")
    reservation_id: uuid.UUID | None = Field(default=None, alias="reservationId")
    reserved_paise: int = Field(alias="reservedPaise")
    replayed: bool


class ReservationSettleRequest(_Strict):
    reservation_id: uuid.UUID = Field(alias="reservationId")
    actual_paise: int = Field(alias="actualPaise", ge=1, le=100_000_000)
    evidence_id: uuid.UUID = Field(alias="evidenceId")


class ReservationReleaseRequest(_Strict):
    reservation_id: uuid.UUID = Field(alias="reservationId")
    non_dispatch_evidence_id: uuid.UUID = Field(alias="nonDispatchEvidenceId")


class ReservationOutcomeResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    reservation_id: uuid.UUID = Field(alias="reservationId")
    account_id: uuid.UUID = Field(alias="accountId")
    state: str
    reserved_paise: int = Field(alias="reservedPaise")
    actual_paise: int | None = Field(default=None, alias="actualPaise")
    overrun_paise: int = Field(alias="overrunPaise")
    fenced: bool
    replayed: bool


class PackageComponentResponse(_Strict):
    component_id: str = Field(alias="componentId")
    quantity: int
    cadence: str
    selectable_maximum: int | None = Field(default=None, alias="selectableMaximum")


class PackageResponse(_Strict):
    package_id: uuid.UUID = Field(alias="packageId")
    package_code: str = Field(alias="packageCode")
    display_name: str = Field(alias="displayName")
    agent_type: str = Field(alias="agentType")
    agent_version: str = Field(alias="agentVersion")
    billing_period_days: int = Field(alias="billingPeriodDays")
    price_incl_gst_paise: int = Field(alias="priceInclGstPaise")
    base_price_paise: int = Field(alias="basePricePaise")
    gst_paise: int = Field(alias="gstPaise")
    gst_rate_percent: int = Field(alias="gstRatePercent")
    components: list[PackageComponentResponse]


class PackageListResponse(_Strict):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    items: list[PackageResponse]
    next_cursor: str | None = Field(default=None, alias="nextCursor")


def _reservation_refusal(error: WalletError) -> HTTPException:
    if error.code == "WALLET_RESERVATION_UNKNOWN":
        return HTTPException(status_code=404, detail={"code": error.code})
    return _refusal(error)


def _outcome_response(receipt: Any) -> ReservationOutcomeResponse:
    return ReservationOutcomeResponse(
        reservationId=receipt.reservation_id,
        accountId=receipt.account_id,
        state=receipt.state,
        reservedPaise=receipt.reserved_paise,
        actualPaise=receipt.actual_paise,
        overrunPaise=receipt.overrun_paise,
        fenced=receipt.fenced,
        replayed=receipt.replayed,
    )


def _reservation_tenant(
    request: Request,
    route: str,
    operation: str,
    payload: dict[str, Any],
    reservation_id: uuid.UUID,
    idempotency_key: str,
) -> uuid.UUID:
    """Verify a settle or release: the delegated subject is the reservation and the key is the caller's."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(status_code=422, detail="WBE_WALLET_IDEMPOTENCY_KEY_INVALID") from None
    try:
        context = _verify(
            request,
            route,
            operation,
            payload,
            lambda ctx: bool(ctx.tenant_id)
            and bool(ctx.actor_subject)
            and ctx.subject_reference == str(reservation_id)
            and ctx.correlation_id == correlation_id
            and ctx.idempotency_key == idempotency_key,
        )
        return uuid.UUID(context.tenant_id)
    except ServiceAuthError as error:
        raise _unauthorized(operation, error) from None
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED") from None


@router.post(
    "/wallet/reservations/settle",
    response_model=ReservationOutcomeResponse,
    response_model_by_alias=True,
)
async def settle_wallet_reservation(
    body: ReservationSettleRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ReservationOutcomeResponse:
    """Record the actual cost of any reservation of the caller's tenant; a repeat is a replay."""
    tenant_id = _reservation_tenant(
        request,
        RESERVATION_SETTLE_ROUTE,
        RESERVATION_SETTLE_OPERATION,
        body.model_dump(by_alias=True, mode="json", exclude_none=True),
        body.reservation_id,
        idempotency_key,
    )
    try:
        async with get_session_factory()() as session, session.begin():
            receipt = await WalletLedger(session).settle(
                tenant_id, body.reservation_id, body.actual_paise, body.evidence_id
            )
    except WalletError as error:
        raise _reservation_refusal(error) from None
    return _outcome_response(receipt)


@router.post(
    "/wallet/reservations/release",
    response_model=ReservationOutcomeResponse,
    response_model_by_alias=True,
)
async def release_wallet_reservation(
    body: ReservationReleaseRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ReservationOutcomeResponse:
    """Return a hold that was provably never dispatched; a repeat is a replay."""
    tenant_id = _reservation_tenant(
        request,
        RESERVATION_RELEASE_ROUTE,
        RESERVATION_RELEASE_OPERATION,
        body.model_dump(by_alias=True, mode="json", exclude_none=True),
        body.reservation_id,
        idempotency_key,
    )
    try:
        async with get_session_factory()() as session, session.begin():
            receipt = await WalletLedger(session).release(
                tenant_id, body.reservation_id, body.non_dispatch_evidence_id
            )
    except WalletError as error:
        raise _reservation_refusal(error) from None
    return _outcome_response(receipt)


@router.post(
    "/relationships/{relationship_id}/setup-grant/reserve",
    response_model=SetupGrantReserveResponse,
    response_model_by_alias=True,
)
async def reserve_setup_grant(
    relationship_id: uuid.UUID,
    body: SetupGrantReserveRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> SetupGrantReserveResponse:
    """Onboarding draw on the relationship's setup grant; exhaustion is a result, not an error."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    payload = body.model_dump(by_alias=True, mode="json")
    try:
        key = uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(status_code=422, detail="WBE_WALLET_IDEMPOTENCY_KEY_INVALID") from None
    try:
        context = _verify(
            request,
            SETUP_GRANT_RESERVE_ROUTE,
            SETUP_GRANT_RESERVE_OPERATION,
            payload,
            lambda ctx: ctx.relationship_id == str(relationship_id)
            and bool(ctx.tenant_id)
            and bool(ctx.actor_subject)
            and ctx.correlation_id == correlation_id
            and ctx.idempotency_key == idempotency_key,
        )
        tenant_id = uuid.UUID(context.tenant_id)
    except ServiceAuthError as error:
        raise _unauthorized(SETUP_GRANT_RESERVE_OPERATION, error) from None
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED") from None
    identity = ReservationIdentity(invocation_id=body.invocation_id, evidence_id=body.owner_evidence_id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_HOLD_SECONDS)
    try:
        async with get_session_factory()() as session, session.begin():
            drawn = await PlatformAccounts(session).reserve_setup_grant(
                tenant_id,
                relationship_id,
                body.agent_type,
                body.agent_version,
                body.component_id,
                body.maximum_paise,
                expires_at,
                identity,
                key,
            )
    except WalletError as error:
        raise _refusal(error) from None
    receipt = drawn.receipt
    return SetupGrantReserveResponse(
        status="RESERVED" if receipt is not None else "SETUP_GRANT_EXHAUSTED",
        accountId=drawn.account.account_id,
        reservationId=None if receipt is None else receipt.reservation_id,
        reservedPaise=0 if receipt is None else receipt.reserved_paise,
        replayed=False if receipt is None else receipt.replayed,
    )


@router.get(
    "/marketplace/agents/{agent_type}/versions/{agent_version}/packages",
    response_model=PackageListResponse,
    response_model_by_alias=True,
)
async def list_for_sale_packages(
    agent_type: str,
    agent_version: str,
    request: Request,
    after: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PackageListResponse:
    """The customer-safe catalogue: EFFECTIVE, for-sale packages only, never costs or recipes."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        _verify(
            request,
            PACKAGES_ROUTE,
            PACKAGES_OPERATION,
            None,
            lambda ctx: bool(ctx.tenant_id)
            and bool(ctx.actor_subject)
            and ctx.subject_reference == f"{agent_type}|{agent_version}"
            and ctx.correlation_id == correlation_id,
        )
    except ServiceAuthError as error:
        raise _unauthorized(PACKAGES_OPERATION, error) from None
    async with get_session_factory()() as session:
        try:
            page = await PackageCatalog(session).list_for_sale(agent_type, agent_version, after=after, limit=limit)
        except CatalogCursorError:
            raise HTTPException(status_code=422, detail="WBE_PACKAGE_CURSOR_INVALID") from None
    return PackageListResponse(
        items=[
            PackageResponse(
                packageId=item.package_id,
                packageCode=item.package_code,
                displayName=item.display_name,
                agentType=item.agent_type,
                agentVersion=item.agent_version,
                billingPeriodDays=item.billing_period_days,
                priceInclGstPaise=item.price_incl_gst_paise,
                basePricePaise=item.base_price_paise,
                gstPaise=item.gst_paise,
                gstRatePercent=item.gst_rate_percent,
                components=[
                    PackageComponentResponse(
                        componentId=component.component_id,
                        quantity=component.quantity,
                        cadence=component.cadence,
                        selectableMaximum=component.selectable_maximum,
                    )
                    for component in item.components
                ],
            )
            for item in page.items
        ],
        nextCursor=page.next_cursor,
    )
