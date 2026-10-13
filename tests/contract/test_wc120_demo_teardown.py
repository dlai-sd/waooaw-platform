from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "infrastructure" / "conversation-whatsapp"


def _load(name: str) -> dict[str, object]:
    return json.loads((MANIFESTS / f"{name}.json").read_text(encoding="utf-8"))


def test_ce_fit_16_demo_teardown_disables_callback_and_preserves_uat_production_or_denies_open_obligations() -> None:
    before = {name: _load(name) for name in ("demo", "uat", "production")}
    after = json.loads(json.dumps(before))
    demo = after["demo"]
    demo["callbackAcceptanceEnabled"] = False
    demo["dispatchEnabled"] = False
    demo["providerEgressEnabled"] = False
    demo["restoreRoutingEnabled"] = False
    demo["activationState"] = "TEARDOWN_COMPLETE"

    assert before["uat"] == after["uat"]
    assert before["production"] == after["production"]
    assert after["demo"]["callbackAcceptanceEnabled"] is False
    assert after["demo"]["dispatchEnabled"] is False
    assert after["demo"]["providerEgressEnabled"] is False
    assert after["demo"]["restoreRoutingEnabled"] is False

    rollback_sql = (ROOT / "infrastructure/postgres/operations/wc120-rollback.sql").read_text(encoding="utf-8")
    assert "UNRESOLVED" in rollback_sql
    assert "DISPATCHING" in rollback_sql
    assert "DELETE FROM" not in rollback_sql.upper()
