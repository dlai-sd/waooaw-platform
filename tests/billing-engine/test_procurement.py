# Implements: work-contracts/WC-029-wbe-s5-platform-procurement.md §WC029-02
# constitutional_basis: C-059 (Implementation Traceability), C-007 (Append-only ledger),
#                       C-077 (Procurement runway), C-076 (≥90% coverage)
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from procurement.founder_action import FounderActionGenerator
from procurement.models import CostRecordRequest, ProviderRunwayStatus
from procurement.service import ProcurementService
from skeleton.wbe_interfaces import FounderActionCreated

# ---------------------------------------------------------------------------
# FA file fixture — section headers must match _find_section_insertion_point
# pattern (### P{n}) so rows land in the right section.
# ---------------------------------------------------------------------------

_FA_TEMPLATE = (
    "# Founder Actions Log\n\n"
    "### P0\n\n"
    "| FA # | Action | Priority | Basis | SLA | Status |\n"
    "|---|---|---|---|---|---|\n\n"
    "### P1\n\n"
    "| FA # | Action | Priority | Basis | SLA | Status |\n"
    "|---|---|---|---|---|---|\n\n"
    "### P2\n\n"
    "| FA # | Action | Priority | Basis | SLA | Status |\n"
    "|---|---|---|---|---|---|\n"
)


@pytest.fixture
def tmp_fa_file(tmp_path: Path) -> Path:
    p = tmp_path / "FOUNDER-ACTIONS.md"
    p.write_text(_FA_TEMPLATE, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Helper: build an AsyncMock session whose execute() returns a mock result.
# ---------------------------------------------------------------------------

def _mock_session(*execute_side_effects):
    """Return an AsyncMock session with execute() cycling through side effects."""
    session = MagicMock()
    session.execute = AsyncMock(side_effect=list(execute_side_effects))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _scalar_result(value):
    """Return a mock execute result whose .scalar() returns value."""
    r = MagicMock()
    r.scalar = MagicMock(return_value=value)
    return r


def _fetchone_result(row_or_none):
    """Return a mock execute result whose .fetchone() returns row_or_none."""
    r = MagicMock()
    r.fetchone = MagicMock(return_value=row_or_none)
    return r


def _fetchall_result(rows):
    """Return a mock execute result whose .fetchall() returns rows."""
    r = MagicMock()
    r.fetchall = MagicMock(return_value=rows)
    return r


# ===========================================================================
# ProcurementService.record_cost
# ===========================================================================


@pytest.mark.asyncio
async def test_record_cost_single_entry() -> None:
    """record_cost resolves provider_account_id then inserts one ledger row."""
    provider_id = uuid4()
    # execute call 1: provider lookup → returns a row with id
    lookup_row = MagicMock()
    lookup_row.__getitem__ = MagicMock(side_effect=lambda i: provider_id if i == 0 else None)
    lookup_result = _fetchone_result(lookup_row)
    # execute call 2: INSERT
    insert_result = MagicMock()
    session = _mock_session(lookup_result, insert_result)

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    await svc.record_cost(
        provider="anthropic",
        thread_type="DMA_THREAD",
        customer_id=uuid4(),
        agent_type="dma_v1",
        cost_paise=500,
        fx_rate_inr_per_usd=85.0,
    )

    assert session.execute.await_count == 2  # lookup + insert
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_cost_provider_not_found_skips_insert() -> None:
    """record_cost silently skips insert when provider_account not found."""
    lookup_result = _fetchone_result(None)
    session = _mock_session(lookup_result)

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    await svc.record_cost(
        provider="unknown",
        thread_type="X",
        customer_id=uuid4(),
        agent_type="x",
        cost_paise=0,
        fx_rate_inr_per_usd=1.0,
    )

    assert session.execute.await_count == 1  # only lookup, no insert
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_cost_append_only_no_dedup() -> None:
    """Two record_cost calls with same event data produce two INSERT calls (C-007)."""
    provider_id = uuid4()
    lookup_row = MagicMock()
    lookup_row.__getitem__ = MagicMock(return_value=provider_id)
    session = _mock_session(
        _fetchone_result(lookup_row),
        MagicMock(),  # insert 1
        _fetchone_result(lookup_row),
        MagicMock(),  # insert 2
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    cid = uuid4()
    for _ in range(2):
        await svc.record_cost("anthropic", "T", cid, "a", 500, 85.0)

    assert session.execute.await_count == 4  # 2 lookups + 2 inserts
    assert session.commit.await_count == 2


# ===========================================================================
# ProcurementService.project_runway
# ===========================================================================


@pytest.mark.asyncio
async def test_project_runway_formula() -> None:
    """project_runway = balance / (7d_sum / 7). 100000 / (70000/7) = 10 days."""
    balance_row = MagicMock()
    balance_row.__getitem__ = MagicMock(return_value=100000)
    session = _mock_session(
        _scalar_result(70000),         # 7d burn SUM
        _fetchone_result(balance_row), # balance lookup
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    days = await svc.project_runway("anthropic")

    assert days == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_project_runway_returns_infinity_when_no_burn() -> None:
    """project_runway returns float('inf') when 7d burn is zero."""
    session = _mock_session(_scalar_result(0))

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    days = await svc.project_runway("ollama")

    assert days == float("inf")


@pytest.mark.asyncio
async def test_project_runway_returns_infinity_when_account_not_found() -> None:
    """project_runway returns float('inf') when provider_account row is missing."""
    session = _mock_session(
        _scalar_result(10000),          # non-zero burn
        _fetchone_result(None),         # balance lookup: no row
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    days = await svc.project_runway("missing")

    assert days == float("inf")


# ===========================================================================
# ProcurementService.check_and_alert
# ===========================================================================


@pytest.mark.asyncio
async def test_check_and_alert_creates_fa_when_runway_breaches_p0(tmp_fa_file: Path) -> None:
    """check_and_alert fires P0 FA when days_remaining ≤ 7."""
    fa_gen = MagicMock()
    fa_gen.maybe_create = MagicMock(return_value="FA-1")

    balance_row = MagicMock()
    balance_row.__getitem__ = MagicMock(return_value=100000)
    # 7d burn = 100000/7 * 7 = 100000 → avg = 100000/7 → days = 100000/(100000/7) = 7
    # but for a cleaner < 7d: use burn sum = 700000 → avg = 100000 → days = 1
    session = _mock_session(
        _scalar_result(700000),        # 7d SUM → avg = 100000/day
        _fetchone_result(balance_row), # balance = 100000 → days = 1.0
    )

    svc = ProcurementService(session=session, founder_action_generator=fa_gen)
    result = await svc.check_and_alert("anthropic")

    # All thresholds ≤ 30, 14, 7 are breached; RUNWAY_P0 is the highest standard one
    assert any(isinstance(r, FounderActionCreated) for r in result)
    # maybe_create called for P2, P1, P0 (3 times; CRITICAL has no priority map entry)
    assert fa_gen.maybe_create.call_count == 3


@pytest.mark.asyncio
async def test_check_and_alert_returns_empty_when_runway_high() -> None:
    """check_and_alert returns empty list when days_remaining > all thresholds."""
    balance_row = MagicMock()
    balance_row.__getitem__ = MagicMock(return_value=100000)
    # burn = 100 paise/day → days = 100000/100 = 1000 → no threshold breached
    session = _mock_session(
        _scalar_result(700),           # 7d SUM = 700 → avg = 100/day
        _fetchone_result(balance_row),
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    result = await svc.check_and_alert("anthropic")

    assert result == []


# ===========================================================================
# ProcurementService.get_all_runway_statuses
# ===========================================================================


@pytest.mark.asyncio
async def test_get_all_runway_statuses_returns_list() -> None:
    """get_all_runway_statuses returns one ProviderRunwayStatus per active account."""
    accounts_row = MagicMock()
    accounts_row.__getitem__ = MagicMock(side_effect=lambda i: "anthropic" if i == 0 else 100000)
    # execute 1: accounts list
    # execute 2: burn SUM for anthropic
    # execute 3: last_fa_level lookup (may raise — handled gracefully)
    session = _mock_session(
        _fetchall_result([accounts_row]),
        _scalar_result(70000),
        _fetchone_result(None),        # no prior FA
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    statuses = await svc.get_all_runway_statuses()

    assert len(statuses) == 1
    assert statuses[0].provider_name == "anthropic"
    assert statuses[0].days_remaining == pytest.approx(10.0)
    assert statuses[0].last_fa_level_triggered is None


# ===========================================================================
# FounderActionGenerator
# ===========================================================================


def test_fa_maybe_create_appends_entry(tmp_fa_file: Path) -> None:
    """maybe_create appends a new FA entry; returns FA number string."""
    result = FounderActionGenerator.maybe_create(
        provider="anthropic",
        days_remaining=25.0,
        priority="2",
        fa_file_path=tmp_fa_file,
    )

    assert result == "FA-1"
    content = tmp_fa_file.read_text()
    assert "Provider anthropic" in content
    assert "| P2 |" in content


def test_fa_maybe_create_idempotent_no_duplicate(tmp_fa_file: Path) -> None:
    """Second maybe_create with same provider+priority → returns None, no duplicate."""
    FounderActionGenerator.maybe_create("anthropic", 25.0, "2", fa_file_path=tmp_fa_file)
    result = FounderActionGenerator.maybe_create("anthropic", 25.0, "2", fa_file_path=tmp_fa_file)

    assert result is None
    count = tmp_fa_file.read_text().count("Provider anthropic")
    assert count == 1


def test_fa_maybe_create_different_priorities_both_written(tmp_fa_file: Path) -> None:
    """P1 and P2 entries for same provider are distinct (different priority)."""
    r1 = FounderActionGenerator.maybe_create("sarvam", 12.0, "1", fa_file_path=tmp_fa_file)
    r2 = FounderActionGenerator.maybe_create("sarvam", 25.0, "2", fa_file_path=tmp_fa_file)

    assert r1 == "FA-1"
    assert r2 == "FA-2"
    content = tmp_fa_file.read_text()
    assert "| P1 |" in content
    assert "| P2 |" in content


def test_fa_maybe_create_increments_fa_number(tmp_fa_file: Path) -> None:
    """FA numbers increment from existing max: first entry→FA-1, second→FA-2."""
    FounderActionGenerator.maybe_create("anthropic", 5.0, "0", fa_file_path=tmp_fa_file)
    r2 = FounderActionGenerator.maybe_create("sarvam", 5.0, "0", fa_file_path=tmp_fa_file)

    assert r2 == "FA-2"


def test_fa_get_next_number_with_existing_entries(tmp_fa_file: Path) -> None:
    """_get_next_fa_number correctly finds max existing FA number."""
    existing = (
        "| **FA-027** | Some action | P0 | C-077 | 1 hour | OPEN |\n"
        "| **FA-041** | Another | P1 | C-077 | 1 hour | OPEN |\n"
    )
    content = tmp_fa_file.read_text() + existing
    tmp_fa_file.write_text(content)

    next_num = FounderActionGenerator._get_next_fa_number(tmp_fa_file.read_text())
    assert next_num == 42


def test_fa_entry_exists_detects_existing(tmp_fa_file: Path) -> None:
    """_fa_entry_exists returns True when provider+priority row is present."""
    FounderActionGenerator.maybe_create("google", 6.0, "0", fa_file_path=tmp_fa_file)
    content = tmp_fa_file.read_text()

    assert FounderActionGenerator._fa_entry_exists(content, "google", "0") is True
    assert FounderActionGenerator._fa_entry_exists(content, "google", "1") is False
    assert FounderActionGenerator._fa_entry_exists(content, "azure", "0") is False


def test_fa_maybe_create_file_not_found_raises(tmp_path: Path) -> None:
    """maybe_create raises FileNotFoundError when FA file path does not exist."""
    missing = tmp_path / "nonexistent.md"

    with pytest.raises(FileNotFoundError):
        FounderActionGenerator.maybe_create("anthropic", 5.0, "0", fa_file_path=missing)


# ===========================================================================
# Router — GET /platform/procurement/status
# ===========================================================================


@pytest.mark.asyncio
async def test_get_procurement_status_endpoint_returns_200() -> None:
    """GET /platform/procurement/status → 200 with list[ProviderRunwayStatus]."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    mock_svc.get_all_runway_statuses = AsyncMock(
        return_value=[
            ProviderRunwayStatus(
                provider_name="anthropic",
                balance_paise=100000,
                daily_burn_rate_paise=10000.0,
                days_remaining=10.0,
                last_fa_level_triggered=None,
            )
        ]
    )
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/platform/procurement/status")
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["provider_name"] == "anthropic"
    assert data[0]["days_remaining"] == pytest.approx(10.0)


# ===========================================================================
# Router — POST /platform/procurement/record-cost
# ===========================================================================


@pytest.mark.asyncio
async def test_post_record_cost_endpoint_returns_200() -> None:
    """POST /platform/procurement/record-cost → 200 {"status": "recorded"}."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    mock_svc.record_cost = AsyncMock()
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/platform/procurement/record-cost",
                json={
                    "provider": "anthropic",
                    "thread_type": "DMA_THREAD",
                    "customer_id": str(uuid4()),
                    "agent_type": "dma_v1",
                    "cost_paise": 500,
                    "fx_rate_inr_per_usd": 85.0,
                },
            )
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 200
    assert resp.json() == {"status": "recorded"}


# ===========================================================================
# Models — Pydantic validation
# ===========================================================================


def test_cost_record_request_rejects_negative_cost() -> None:
    """CostRecordRequest cost_paise must be ≥ 0."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CostRecordRequest(
            provider="x",
            thread_type="T",
            customer_id=uuid4(),
            agent_type="a",
            cost_paise=-1,
            fx_rate_inr_per_usd=1.0,
        )


def test_cost_record_request_rejects_zero_fx_rate() -> None:
    """CostRecordRequest fx_rate_inr_per_usd must be > 0."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CostRecordRequest(
            provider="x",
            thread_type="T",
            customer_id=uuid4(),
            agent_type="a",
            cost_paise=100,
            fx_rate_inr_per_usd=0.0,
        )


def test_provider_runway_status_model() -> None:
    """ProviderRunwayStatus Pydantic model round-trips through JSON."""
    status = ProviderRunwayStatus(
        provider_name="anthropic",
        balance_paise=100000,
        daily_burn_rate_paise=10000.0,
        days_remaining=10.0,
        last_fa_level_triggered=None,
    )

    d = status.model_dump()
    assert d["provider_name"] == "anthropic"
    assert d["days_remaining"] == 10.0
    assert d["last_fa_level_triggered"] is None


# ===========================================================================
# ProcurementService.record_cost — exception handlers
# ===========================================================================


@pytest.mark.asyncio
async def test_record_cost_db_exception_triggers_rollback() -> None:
    """record_cost Exception on INSERT → session.rollback called, exception re-raised."""
    provider_id = uuid4()
    lookup_row = MagicMock()
    lookup_row.__getitem__ = MagicMock(return_value=provider_id)
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_fetchone_result(lookup_row), RuntimeError("DB down")]
    )
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    with pytest.raises(RuntimeError):
        await svc.record_cost("anthropic", "T", uuid4(), "a", 100, 85.0)

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_cost_value_error_no_rollback() -> None:
    """record_cost ValueError on execute → re-raised without rollback (no rollback on ValErr)."""
    provider_id = uuid4()
    lookup_row = MagicMock()
    lookup_row.__getitem__ = MagicMock(return_value=provider_id)
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_fetchone_result(lookup_row), ValueError("bad value")]
    )
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    with pytest.raises(ValueError):
        await svc.record_cost("anthropic", "T", uuid4(), "a", 100, 85.0)

    session.rollback.assert_not_awaited()


# ===========================================================================
# ProcurementService.project_runway — exception handler
# ===========================================================================


@pytest.mark.asyncio
async def test_project_runway_re_raises_on_db_error() -> None:
    """project_runway re-raises exceptions from session.execute."""
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    with pytest.raises(RuntimeError):
        await svc.project_runway("anthropic")


# ===========================================================================
# ProcurementService.check_and_alert — FA idempotent + exception handler
# ===========================================================================


@pytest.mark.asyncio
async def test_check_and_alert_maybe_create_returns_none_no_fa_event() -> None:
    """When maybe_create returns None (idempotent skip), no FounderActionCreated appended."""
    fa_gen = MagicMock()
    fa_gen.maybe_create = MagicMock(return_value=None)

    balance_row = MagicMock()
    balance_row.__getitem__ = MagicMock(return_value=100000)
    session = _mock_session(
        _scalar_result(700000),
        _fetchone_result(balance_row),
    )

    svc = ProcurementService(session=session, founder_action_generator=fa_gen)
    result = await svc.check_and_alert("anthropic")

    assert result == []


@pytest.mark.asyncio
async def test_check_and_alert_re_raises_on_project_runway_error() -> None:
    """check_and_alert re-raises if project_runway raises."""
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    with pytest.raises(RuntimeError):
        await svc.check_and_alert("anthropic")


# ===========================================================================
# ProcurementService.get_all_runway_statuses — edge cases + exception
# ===========================================================================


@pytest.mark.asyncio
async def test_get_all_runway_statuses_zero_burn_returns_inf() -> None:
    """get_all_runway_statuses returns float('inf') days_remaining when burn is zero."""
    accounts_row = MagicMock()
    accounts_row.__getitem__ = MagicMock(side_effect=lambda i: "ollama" if i == 0 else 50000)
    session = _mock_session(
        _fetchall_result([accounts_row]),
        _scalar_result(0),
        _fetchone_result(None),
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    statuses = await svc.get_all_runway_statuses()

    assert statuses[0].days_remaining == float("inf")


@pytest.mark.asyncio
async def test_get_all_runway_statuses_last_fa_level_from_log() -> None:
    """get_all_runway_statuses returns last_fa_level_triggered from FA log."""
    accounts_row = MagicMock()
    accounts_row.__getitem__ = MagicMock(side_effect=lambda i: "anthropic" if i == 0 else 100000)
    fa_log_row = MagicMock()
    fa_log_row.__getitem__ = MagicMock(return_value="P0")
    session = _mock_session(
        _fetchall_result([accounts_row]),
        _scalar_result(70000),
        _fetchone_result(fa_log_row),
    )

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    statuses = await svc.get_all_runway_statuses()

    assert statuses[0].last_fa_level_triggered == "P0"


@pytest.mark.asyncio
async def test_get_all_runway_statuses_re_raises_on_accounts_error() -> None:
    """get_all_runway_statuses re-raises if accounts query fails."""
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

    svc = ProcurementService(session=session, founder_action_generator=MagicMock())
    with pytest.raises(RuntimeError):
        await svc.get_all_runway_statuses()


# ===========================================================================
# FounderActionGenerator — section not found path + default file path
# ===========================================================================


def test_fa_section_not_found_appends_at_end(tmp_fa_file: Path) -> None:
    """When priority section header not found, FA row appended at end of file."""
    result = FounderActionGenerator.maybe_create(
        provider="unknown_provider",
        days_remaining=5.0,
        priority="9",  # no ### P9 section in template
        fa_file_path=tmp_fa_file,
    )

    assert result == "FA-1"
    content = tmp_fa_file.read_text()
    assert "Provider unknown_provider" in content


def test_fa_default_file_path_is_used_when_none(tmp_path: Path, monkeypatch) -> None:
    """maybe_create uses cls.FA_FILE_PATH when fa_file_path=None."""
    fa_path = tmp_path / "FA.md"
    fa_path.write_text(_FA_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(FounderActionGenerator, "FA_FILE_PATH", fa_path)

    result = FounderActionGenerator.maybe_create(
        provider="anthropic",
        days_remaining=5.0,
        priority="0",
        fa_file_path=None,
    )

    assert result == "FA-1"
    assert "Provider anthropic" in fa_path.read_text()


# ===========================================================================
# Router — additional error paths
# ===========================================================================


@pytest.mark.asyncio
async def test_get_margin_report_returns_501() -> None:
    """GET /platform/procurement/margin/report → 501 Not Implemented."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/platform/procurement/margin/report")
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_get_procurement_status_returns_500_on_service_error() -> None:
    """GET /platform/procurement/status → 500 when get_all_runway_statuses raises."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    mock_svc.get_all_runway_statuses = AsyncMock(side_effect=RuntimeError("DB error"))
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/platform/procurement/status")
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_post_record_cost_returns_400_on_value_error() -> None:
    """POST record-cost → 400 when service.record_cost raises ValueError."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    mock_svc.record_cost = AsyncMock(side_effect=ValueError("bad provider"))
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/platform/procurement/record-cost",
                json={
                    "provider": "unknown",
                    "thread_type": "T",
                    "customer_id": str(uuid4()),
                    "agent_type": "a",
                    "cost_paise": 0,
                    "fx_rate_inr_per_usd": 1.0,
                },
            )
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_post_record_cost_returns_500_on_general_exception() -> None:
    """POST record-cost → 500 when service.record_cost raises general Exception."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    from procurement.router import get_procurement_service

    mock_svc = MagicMock()
    mock_svc.record_cost = AsyncMock(side_effect=RuntimeError("DB down"))
    app.dependency_overrides[get_procurement_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/platform/procurement/record-cost",
                json={
                    "provider": "anthropic",
                    "thread_type": "T",
                    "customer_id": str(uuid4()),
                    "agent_type": "a",
                    "cost_paise": 100,
                    "fx_rate_inr_per_usd": 85.0,
                },
            )
    finally:
        app.dependency_overrides.pop(get_procurement_service, None)

    assert resp.status_code == 500
