from pathlib import Path

import yaml


CATALOG = Path("infrastructure/operations/wc124-lifecycle-alerts.yaml")
RUNBOOK = Path("architecture/reference/runbooks/demo-uat-persistent-state-lifecycle.md")


def test_lifecycle_alert_catalog_has_closed_signal_ownership_and_retention() -> None:
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    assert catalog["owner"] == "Platform_Operations"
    assert catalog["receiver_authority"] == "observe_alert_escalate_only"
    assert catalog["redaction"] == (
        "no_customer_data_secrets_tokens_connection_strings_or_raw_identifiers"
    )
    signals = {signal["id"]: signal for signal in catalog["signals"]}
    assert set(signals) == {
        "unexpected-postgresql-start",
        "lifecycle-lease-transition-retry-lock",
        "database-start-stop-failure",
        "backup-restore-rpo-rto",
        "pgbouncer-saturation-rejection-route",
        "migration-schema-watermark-drift",
        "public-direct-foreign-route",
        "cost-forecast-actual-drift",
        "evidence-chain-signature-failure",
    }
    assert signals["pgbouncer-saturation-rejection-route"]["retention_days"] == 35
    assert signals["migration-schema-watermark-drift"]["retention_days"] == 90
    assert signals["evidence-chain-signature-failure"]["retention_days"] == 400
    assert all(signal["evidence"] and signal["escalation"] for signal in signals.values())


def test_only_accepted_scheduled_mutation_is_catalogued() -> None:
    mutation = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["scheduled_mutation"]
    assert mutation["sole_action"] == "re_stop_automatically_started_postgresql"
    assert mutation["otherwise"] == "RECOVERY_HOLD"
    assert set(mutation["required_conditions"]) == {
        "original_sleep_lease_unexpired",
        "exact_founder_provider_authority_valid",
        "environment_tuple_exact",
        "no_active_or_uncertain_work",
        "backup_ready",
    }


def test_runbook_preserves_provider_and_hold_release_authority_boundaries() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "does not grant Azure access" in runbook
    assert "Stop PostgreSQL last" in runbook
    assert "Never delete the server" in runbook
    assert "RPO above 5 minutes or RTO above 30 minutes" in runbook
    assert "grants no deployment, data, secret, provider-action, traffic, or" in runbook
