# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# Constitutional basis: C-059, C-063, C-088, C-089
"""Private wallet routes: platform-account reserve, setup-grant open and draw, settle and release."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import DateTime, bindparam, text

from wallet import private_routes
from wallet.private_routes import (
    AccountReserveRequest,
    ReservationReleaseRequest,
    ReservationSettleRequest,
    SetupGrantRequest,
    SetupGrantReserveRequest,
)

TENANT = UUID("11111111-1111-4111-8111-111111111111")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
CORRELATION = "corr-1"


def _request(auth=None):
    return SimpleNamespace(
        headers={"X-Correlation-ID": CORRELATION},
        method="POST",
        scope={},
        app=SimpleNamespace(state=SimpleNamespace(relationship_workload_auth=auth)),
    )


@pytest_asyncio.fixture
async def harness(wallet_db, monkeypatch):
    seen: list[tuple[str, str, object]] = []

    def factory():
        return wallet_db()

    def verified(request, route, operation, body, predicate):
        context = SimpleNamespace(
            tenant_id=str(TENANT),
            relationship_id=str(RELATIONSHIP),
            actor_subject="actor-1",
            correlation_id=CORRELATION,
            idempotency_key=harness_state["key"],
            subject_reference=harness_state["subject"],
        )
        assert predicate(context)
        seen.append((route, operation, body))
        return context

    harness_state = {"key": "", "subject": ""}
    monkeypatch.setattr(private_routes, "get_session_factory", lambda: factory)
    monkeypatch.setattr(private_routes, "_verify", verified)
    yield SimpleNamespace(factory=wallet_db, seen=seen, state=harness_state)


async def _seed(harness, kind: str, subject: str, body: dict) -> None:
    async with harness.factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO institutional.pricing_versions "
                "(version_id, kind, subject_key, version_no, state, body, effective_from) "
                "VALUES (:id, :kind, :subject, 1, 'EFFECTIVE', :body, :effective)"
            ).bindparams(bindparam("effective", type_=DateTime(timezone=True))),
            {
                "id": str(uuid4()),
                "kind": kind,
                "subject": subject,
                "body": json.dumps(body),
                "effective": datetime.now(timezone.utc) - timedelta(days=1),
            },
        )


async def _count(harness, table: str) -> int:
    async with harness.factory() as session:
        return (await session.execute(text(f"SELECT COUNT(*) FROM business.{table}"))).scalar_one()


def _reserve_body(**overrides) -> AccountReserveRequest:
    values = {
        "accountClass": "ACQUISITION",
        "componentId": "llm_cloud",
        "maximumPaise": 120,
        "invocationId": str(uuid4()),
        "ownerEvidenceId": str(uuid4()),
    }
    values.update(overrides)
    return AccountReserveRequest.model_validate(values)


async def _reserve(harness, body: AccountReserveRequest, key: UUID | None = None):
    key = key or uuid4()
    harness.state["key"] = str(key)
    return await private_routes.reserve_platform_account(body, _request(), str(key))


async def test_acquisition_reserve_replays_and_names_the_exhausted_level(harness):
    await _seed(
        harness,
        "BUDGET",
        f"budget:ACQUISITION_TENANT|{TENANT}",
        {"scope": "ACQUISITION_TENANT", "reference": str(TENANT), "maximumPaise": 200},
    )
    key = uuid4()
    body = _reserve_body(leadRef="lead-1")

    first = await _reserve(harness, body, key)
    replay = await _reserve(harness, body, key)
    with pytest.raises(HTTPException) as exhausted:
        await _reserve(harness, _reserve_body(maximumPaise=100))

    assert (first.account_class, first.state, first.reserved_paise, first.replayed) == (
        "ACQUISITION",
        "RESERVED",
        120,
        False,
    )
    assert (replay.replayed, replay.reservation_id) == (True, first.reservation_id)
    assert exhausted.value.status_code == 409
    assert exhausted.value.detail == {"code": "ACQUISITION_BUDGET_EXHAUSTED", "level": "TENANT"}
    assert await _count(harness, "wallet_reservations") == 1


async def test_the_signed_digest_is_computed_over_the_body_without_absent_fields(harness):
    await _seed(
        harness,
        "BUDGET",
        f"budget:ACQUISITION_TENANT|{TENANT}",
        {"scope": "ACQUISITION_TENANT", "reference": str(TENANT), "maximumPaise": 500},
    )

    await _reserve(harness, _reserve_body())

    route, operation, signed = harness.seen[-1]
    assert (route, operation) == ("/internal/v1/wallet/accounts/reserve", "wbeReserveWalletAccount")
    assert set(signed) == {"accountClass", "componentId", "invocationId", "maximumPaise", "ownerEvidenceId"}


async def test_simulation_reserve_uses_its_own_cap_and_the_environment(harness):
    await _seed(
        harness,
        "BUDGET",
        "budget:SIMULATION|demo",
        {"scope": "SIMULATION", "reference": "demo", "maximumPaise": 150},
    )

    simulated = await _reserve(harness, _reserve_body(accountClass="SIMULATION", environment="demo"))
    with pytest.raises(HTTPException) as capped:
        await _reserve(harness, _reserve_body(accountClass="SIMULATION", environment="demo"))

    assert (simulated.account_class, simulated.state) == ("SIMULATION", "RESERVED")
    assert capped.value.detail == {"code": "SIMULATION_BUDGET_EXHAUSTED", "level": "SIMULATION"}


async def test_platform_floor_is_recorded_without_a_balance_and_once_per_key(harness):
    key = uuid4()
    body = _reserve_body(
        accountClass="PLATFORM_FLOOR", environment="demo", purpose="STOP_ACK", maximumPaise=25
    )

    first = await _reserve(harness, body, key)
    replay = await _reserve(harness, body, key)

    assert (first.state, first.reserved_paise, first.replayed) == ("RECORDED", 25, False)
    assert (replay.replayed, replay.reservation_id) == (True, key)
    assert await _count(harness, "wallet_floor_uses") == 1
    assert await _count(harness, "wallet_reservations") == 0


@pytest.mark.parametrize(
    "overrides,detail",
    [
        ({"accountClass": "SIMULATION"}, "WBE_WALLET_ENVIRONMENT_REQUIRED"),
        ({"accountClass": "PLATFORM_FLOOR", "environment": "demo"}, "WBE_WALLET_PURPOSE_REQUIRED"),
    ],
)
async def test_environment_and_purpose_are_required_where_the_class_needs_them(
    harness, overrides, detail
):
    with pytest.raises(HTTPException) as refused:
        await _reserve(harness, _reserve_body(**overrides))

    assert (refused.value.status_code, refused.value.detail) == (422, detail)


async def test_a_wallet_validation_error_is_unprocessable_and_not_a_conflict(harness):
    await _seed(
        harness,
        "BUDGET",
        f"budget:ACQUISITION_TENANT|{TENANT}",
        {"scope": "ACQUISITION_TENANT", "reference": str(TENANT), "maximumPaise": 500},
    )

    with pytest.raises(HTTPException) as refused:
        await _reserve(harness, _reserve_body(leadRef="not a pseudonym!"))

    assert refused.value.status_code == 422
    assert refused.value.detail["code"] == "WALLET_ACCOUNT_INVALID"
    assert await _count(harness, "wallet_reservations") == 0


async def test_a_malformed_idempotency_key_is_refused_before_authorization(harness):
    with pytest.raises(HTTPException) as refused:
        await private_routes.reserve_platform_account(_reserve_body(), _request(), "not-a-uuid")

    assert (refused.value.status_code, refused.value.detail) == (
        422,
        "WBE_WALLET_IDEMPOTENCY_KEY_INVALID",
    )
    assert harness.seen == []


async def test_setup_grant_route_credits_once_and_reports_no_grant_honestly(harness):
    key = uuid4()
    harness.state["key"] = str(key)
    body = SetupGrantRequest.model_validate({"agentType": "DMA", "agentVersion": "1.0.0"})

    none = await private_routes.open_setup_grant(RELATIONSHIP, body, _request(), str(key))
    await _seed(
        harness,
        "GRANT",
        "grant:SETUP|DMA|1.0.0",
        {
            "grantKind": "SETUP",
            "agentType": "DMA",
            "agentVersion": "1.0.0",
            "durationDays": 7,
            "amountPaise": 500,
        },
    )
    first = await private_routes.open_setup_grant(RELATIONSHIP, body, _request(), str(key))
    replay = await private_routes.open_setup_grant(RELATIONSHIP, body, _request(), str(key))

    assert (none.status, none.credited_paise, none.lot_id) == ("NO_GRANT", 0, None)
    assert (first.status, first.credited_paise, first.created) == ("GRANTED", 500, True)
    assert (replay.status, replay.created, replay.lot_id) == ("GRANTED", False, first.lot_id)
    assert first.account_id == none.account_id == replay.account_id
    assert await _count(harness, "wallet_lots") == 1


async def _seed_setup_grant(harness, amount: int) -> None:
    await _seed(
        harness,
        "GRANT",
        "grant:SETUP|DMA|1.0.0",
        {
            "grantKind": "SETUP",
            "agentType": "DMA",
            "agentVersion": "1.0.0",
            "durationDays": 7,
            "amountPaise": amount,
        },
    )


def _draw_body(paise: int, **overrides) -> SetupGrantReserveRequest:
    values = {
        "agentType": "DMA",
        "agentVersion": "1.0.0",
        "componentId": "llm_cloud",
        "maximumPaise": paise,
        "invocationId": str(uuid4()),
        "ownerEvidenceId": str(uuid4()),
    }
    values.update(overrides)
    return SetupGrantReserveRequest.model_validate(values)


async def _draw(harness, body: SetupGrantReserveRequest, key: UUID | None = None):
    key = key or uuid4()
    harness.state["key"] = str(key)
    return await private_routes.reserve_setup_grant(RELATIONSHIP, body, _request(), str(key))


async def test_setup_grant_draw_reports_exhaustion_as_a_result_and_replays(harness):
    await _seed_setup_grant(harness, 300)
    key = uuid4()
    body = _draw_body(200)

    first = await _draw(harness, body, key)
    replay = await _draw(harness, body, key)
    exhausted = await _draw(harness, _draw_body(200))

    assert (first.status, first.reserved_paise, first.replayed) == ("RESERVED", 200, False)
    assert (replay.replayed, replay.reservation_id) == (True, first.reservation_id)
    assert (exhausted.status, exhausted.reservation_id, exhausted.reserved_paise) == (
        "SETUP_GRANT_EXHAUSTED",
        None,
        0,
    )
    assert await _count(harness, "wallet_reservations") == 1


async def _settle(harness, reservation_id, paise: int, evidence: UUID | None = None, key: UUID | None = None):
    key = key or uuid4()
    harness.state["key"] = str(key)
    harness.state["subject"] = str(reservation_id)
    body = ReservationSettleRequest.model_validate(
        {"reservationId": str(reservation_id), "actualPaise": paise, "evidenceId": str(evidence or uuid4())}
    )
    return await private_routes.settle_wallet_reservation(body, _request(), str(key))


async def test_settle_records_the_actual_cost_once_and_replays_with_the_same_evidence(harness):
    await _seed_setup_grant(harness, 300)
    drawn = await _draw(harness, _draw_body(200))
    evidence = uuid4()

    settled = await _settle(harness, drawn.reservation_id, 150, evidence)
    replay = await _settle(harness, drawn.reservation_id, 150, evidence)

    assert (settled.state, settled.actual_paise, settled.overrun_paise, settled.replayed) == (
        "SETTLED",
        150,
        0,
        False,
    )
    assert replay.replayed is True
    assert harness.seen[-1][1] == "wbeSettleWalletReservation"


async def test_release_returns_the_hold_and_an_unknown_reservation_is_not_found(harness):
    await _seed_setup_grant(harness, 300)
    drawn = await _draw(harness, _draw_body(200))
    harness.state["key"] = str(uuid4())
    harness.state["subject"] = str(drawn.reservation_id)
    body = ReservationReleaseRequest.model_validate(
        {"reservationId": str(drawn.reservation_id), "nonDispatchEvidenceId": str(uuid4())}
    )

    released = await private_routes.release_wallet_reservation(body, _request(), harness.state["key"])
    retry = await _draw(harness, _draw_body(300))
    with pytest.raises(HTTPException) as unknown:
        await _settle(harness, uuid4(), 10)

    assert released.state == "RELEASED"
    assert retry.status == "RESERVED"
    assert unknown.value.status_code == 404
    assert unknown.value.detail == {"code": "WALLET_RESERVATION_UNKNOWN"}


async def test_settle_refuses_a_subject_that_is_not_the_reservation(harness):
    body = ReservationSettleRequest.model_validate(
        {"reservationId": str(uuid4()), "actualPaise": 10, "evidenceId": str(uuid4())}
    )
    harness.state["key"] = str(uuid4())
    harness.state["subject"] = "someone-else"

    with pytest.raises(AssertionError):
        await private_routes.settle_wallet_reservation(body, _request(), harness.state["key"])


@pytest.mark.parametrize("call", ["reserve", "setup", "parity", "settle", "release", "draw", "packages"])
async def test_every_route_denies_a_request_without_workload_identity(call):
    request = _request(auth=None)
    with pytest.raises(HTTPException) as denied:
        if call == "reserve":
            await private_routes.reserve_platform_account(_reserve_body(), request, str(uuid4()))
        elif call == "setup":
            body = SetupGrantRequest.model_validate({"agentType": "DMA", "agentVersion": "1.0.0"})
            await private_routes.open_setup_grant(RELATIONSHIP, body, request, str(uuid4()))
        elif call == "settle":
            body = ReservationSettleRequest.model_validate(
                {"reservationId": str(uuid4()), "actualPaise": 5, "evidenceId": str(uuid4())}
            )
            await private_routes.settle_wallet_reservation(body, request, str(uuid4()))
        elif call == "release":
            body = ReservationReleaseRequest.model_validate(
                {"reservationId": str(uuid4()), "nonDispatchEvidenceId": str(uuid4())}
            )
            await private_routes.release_wallet_reservation(body, request, str(uuid4()))
        elif call == "draw":
            await private_routes.reserve_setup_grant(RELATIONSHIP, _draw_body(10), request, str(uuid4()))
        elif call == "packages":
            await private_routes.list_for_sale_packages("DMA", "1.0.0", request, None, 25)
        else:
            await private_routes.get_wallet_parity(request, TENANT, None, 10)

    assert (denied.value.status_code, denied.value.detail) == (401, "WBE_WALLET_UNAUTHORIZED")
