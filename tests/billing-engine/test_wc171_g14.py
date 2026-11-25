"""WC-171 C4: the two billing-engine faults found in the Demo log scan (WC-169 G14)."""

# Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R012
# Constitutional basis: C-007, C-023, C-059, C-076

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from meter.router import get_meter_service
from reconciliation.scheduler import _trigger_meter_daily_scan

ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "infrastructure" / "postgres" / "init" / "99zzzzzzzz-wc171-01-audit-evidence-log.sql"


def _request(**state: object) -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


@pytest.mark.asyncio
async def test_the_meter_service_composed_at_startup_is_the_one_the_daily_scan_uses() -> None:
    service = object()

    assert await get_meter_service(_request(meter_service=service)) is service


@pytest.mark.asyncio
async def test_an_uncomposed_meter_service_is_still_an_honest_503() -> None:
    with pytest.raises(HTTPException) as refused:
        await get_meter_service(_request())

    assert refused.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("base", ["http://wbe.internal", "http://wbe.internal/"])
async def test_the_scheduler_never_posts_to_a_double_slash_path(base: str) -> None:
    client = MagicMock()
    client.post = AsyncMock(return_value=MagicMock(status_code=200, raise_for_status=MagicMock()))
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)

    with patch("reconciliation.scheduler.httpx.AsyncClient", return_value=manager):
        await _trigger_meter_daily_scan(SimpleNamespace(WBE_INTERNAL_BASE_URL=base))

    client.post.assert_awaited_once_with("http://wbe.internal/meter/daily-scan")


def test_the_init_chain_creates_the_audit_log_the_reconciliation_inserts_into() -> None:
    sql = INIT.read_text(encoding="utf-8")
    service = (ROOT / "src" / "billing-engine" / "reconciliation" / "service.py").read_text(encoding="utf-8")
    bound = re.search(
        r"INSERT INTO audit_evidence_log\s*\((.*?)\)\s*VALUES", service, re.DOTALL
    )
    assert bound is not None
    for column in (name.strip() for name in bound.group(1).split(",")):
        assert re.search(rf"^\s+{column}\s", sql, re.MULTILINE), column


def test_the_audit_log_is_append_only_for_the_runtime_roles() -> None:
    sql = INIT.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS institutional.audit_evidence_log" in sql
    assert "GRANT SELECT, INSERT ON institutional.audit_evidence_log" in sql
    assert not re.search(r"GRANT[^;]*\b(UPDATE|DELETE)\b", sql)
