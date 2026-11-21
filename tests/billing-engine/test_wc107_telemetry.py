# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-063, C-088
import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from telemetry import _server_request_hook, _server_response_hook
from wallet import spend_events
from wallet.entity_models import ReservationIdentity, WalletError
from wallet.ledger import WalletLedger


class RecordingSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, str] = {}

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, name: str, value: str) -> None:
        self.attributes[name] = value

    def get_span_context(self) -> SimpleNamespace:
        return SimpleNamespace(trace_id=int("12" * 16, 16))


def test_hire_bind_span_contains_only_privacy_safe_journey_values() -> None:
    span = RecordingSpan()

    _server_request_hook(span, {"path": "/payments/hire-checkout/bind"})  # type: ignore[arg-type]
    _server_response_hook(span, {"type": "http.response.start", "status": 200})  # type: ignore[arg-type]

    assert span.attributes == {
        "waooaw.journey.operation": "hire.relationship.bind",
        "waooaw.correlation_id": "12" * 16,
        "waooaw.journey.status_class": "2xx",
        "waooaw.journey.outcome": "COMMERCIAL_OUTCOME_BOUND",
    }
    serialized = repr(span.attributes)
    for prohibited in ("customer_id", "relationship_id", "payment_id", "checkout_intent_id", "coupon"):
        assert prohibited not in serialized


def test_unknown_path_adds_no_custom_journey_values() -> None:
    span = RecordingSpan()

    _server_request_hook(span, {"path": "/payments/hire-checkout/private-value"})  # type: ignore[arg-type]
    _server_response_hook(span, {"type": "http.response.start", "status": 200})  # type: ignore[arg-type]

    assert span.attributes == {}


# --- WC-136 C4-11: spend events and metrics --------------------------------------------------------

_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
_TENANT = UUID("11111111-1111-4111-8111-111111111111")
_RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
_FIELDS = {"event", "accountClass", "tenantId", "paise", "reasonCode"}


def test_spend_event_carries_only_the_contract_fields() -> None:
    fields = spend_events.emit_spend_event(
        spend_events.SPEND_RESERVED,
        account_class="ACQUISITION",
        tenant_id=_TENANT,
        paise=125,
        relationship_id=_RELATIONSHIP,
        skill_id="skill-1",
        component_id="llm_cloud",
        campaign_ref="camp-1",
        lead_ref="lead-9f3a",
    )

    assert fields == {
        "event": "spend_reserved",
        "accountClass": "ACQUISITION",
        "tenantId": str(_TENANT),
        "paise": 125,
        "reasonCode": "OK",
        "relationshipId": str(_RELATIONSHIP),
        "skillId": "skill-1",
        "componentId": "llm_cloud",
        "campaignRef": "camp-1",
        "leadRef": "lead-9f3a",
    }
    assert spend_events.SPEND_EVENTS == {"spend_reserved", "spend_settled", "spend_released", "spend_denied"}


def test_no_personal_data_reaches_a_log_line_in_any_outcome(caplog) -> None:
    personal = {
        "lead_ref": "+919876543210",
        "campaign_ref": "owner@example.com",
        "skill_id": "Priya Sharma wants a quote",
        "component_id": "9876543210",
    }
    with caplog.at_level(logging.INFO, logger="waooaw.spend"):
        for event in sorted(spend_events.SPEND_EVENTS):
            fields = spend_events.emit_spend_event(
                event, account_class="ACQUISITION", tenant_id=_TENANT, paise=10, reason_code="NOT A CODE", **personal
            )
            assert set(fields) == _FIELDS

    assert len(caplog.records) == 4
    for value in personal.values():
        assert value not in caplog.text
    assert all(json.loads(record.getMessage())["reasonCode"] == "UNSPECIFIED" for record in caplog.records)


@pytest.fixture
def recorded(monkeypatch):
    calls: list[tuple[str, int, dict]] = []
    monkeypatch.setattr(spend_events.metrics, "count", lambda name, amount=1, **attrs: calls.append((name, amount, attrs)))
    return calls


@pytest.mark.asyncio
async def test_metrics_count_once_per_operation_and_not_on_replay(wallet_db, recorded) -> None:
    async with wallet_db() as session:
        ledger = WalletLedger(session, now=lambda: _T0)
        account = await ledger.open_account(_TENANT, "SUBSCRIPTION", owner_ref=uuid4(), relationship_id=_RELATIONSHIP)
        await ledger.credit(
            account, "PERIOD_CREDIT", 1000, _T0, _T0 + timedelta(days=30), "p1", {"package": "p1"}, uuid4()
        )
        key = uuid4()
        args = (account, "llm_cloud", 400, _T0 + timedelta(hours=1), ReservationIdentity(pinned_versions={}), key)
        await ledger.reserve(*args)
        await ledger.reserve(*args)
        evidence = uuid4()
        await ledger.settle(_TENANT, key, 300, evidence)
        await ledger.settle(_TENANT, key, 300, evidence)

    assert [call for call in recorded if call[0] == spend_events.SPEND_PAISE_METRIC] == [
        (spend_events.SPEND_PAISE_METRIC, 300, {"class": "SUBSCRIPTION"})
    ]


@pytest.mark.asyncio
async def test_a_denied_reserve_counts_the_class_and_reason_and_a_release_counts_no_spend(wallet_db, recorded, caplog) -> None:
    async with wallet_db() as session:
        ledger = WalletLedger(session, now=lambda: _T0)
        account = await ledger.open_account(_TENANT, "SUBSCRIPTION", owner_ref=uuid4(), relationship_id=_RELATIONSHIP)
        await ledger.credit(
            account, "PERIOD_CREDIT", 500, _T0, _T0 + timedelta(days=30), "p1", {"package": "p1"}, uuid4()
        )
        with caplog.at_level(logging.INFO, logger="waooaw.spend"):
            with pytest.raises(WalletError):
                await ledger.reserve(
                    account, "llm_cloud", 900, _T0 + timedelta(hours=1), ReservationIdentity(pinned_versions={}), uuid4()
                )
            held = uuid4()
            await ledger.reserve(
                account, "llm_cloud", 200, _T0 + timedelta(hours=1), ReservationIdentity(pinned_versions={}), held
            )
            await ledger.release(_TENANT, held, uuid4())

    assert (
        spend_events.SPEND_DENIED_METRIC,
        1,
        {"class": "SUBSCRIPTION", "reason": "WALLET_INSUFFICIENT_BALANCE"},
    ) in recorded
    assert not [call for call in recorded if call[0] == spend_events.SPEND_PAISE_METRIC]
    events = [json.loads(record.getMessage())["event"] for record in caplog.records]
    assert events == ["spend_denied", "spend_reserved", "spend_released"]


@pytest.mark.asyncio
async def test_settle_and_release_events_carry_the_relationship_of_the_account(wallet_db, caplog) -> None:
    async with wallet_db() as session:
        ledger = WalletLedger(session, now=lambda: _T0)
        account = await ledger.open_account(_TENANT, "SUBSCRIPTION", owner_ref=uuid4(), relationship_id=_RELATIONSHIP)
        await ledger.credit(
            account, "PERIOD_CREDIT", 1000, _T0, _T0 + timedelta(days=30), "p1", {"package": "p1"}, uuid4()
        )
        identity = ReservationIdentity(pinned_versions={})
        settled, released = uuid4(), uuid4()
        with caplog.at_level(logging.INFO, logger="waooaw.spend"):
            await ledger.reserve(account, "llm_cloud", 300, _T0 + timedelta(hours=1), identity, settled)
            await ledger.reserve(account, "llm_cloud", 200, _T0 + timedelta(hours=1), identity, released)
            await ledger.settle(_TENANT, settled, 300, uuid4())
            await ledger.release(_TENANT, released, uuid4())

    events = {entry["event"]: entry for entry in (json.loads(record.getMessage()) for record in caplog.records)}
    assert events["spend_settled"]["relationshipId"] == str(_RELATIONSHIP)
    assert events["spend_released"]["relationshipId"] == str(_RELATIONSHIP)


def test_parity_and_margin_metrics_are_named_by_the_contract(recorded) -> None:
    spend_events.record_parity_difference(0)
    spend_events.record_parity_difference(2)
    spend_events.record_live_margin_floor_breach(1)

    assert recorded == [("waooaw_wallet_parity_difference", 2, {}), ("waooaw_live_margin_floor_breach", 1, {})]