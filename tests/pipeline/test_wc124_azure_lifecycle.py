"""WC-124 Azure lifecycle ordering and fail-closed gates."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§10-11
# Constitutional basis: C-023, C-059, C-066, C-080

import pytest

from scripts.wc124_azure_lifecycle import (
    APPLICATIONS,
    AzureLifecycleError,
    SLEEP_GATES,
    commands,
    execute,
)


def test_activation_starts_database_before_terraform_repairs_dependency_scale() -> None:
    planned = commands("demo", "activate")
    assert planned[0][1:4] == ["postgres", "flexible-server", "start"]
    assert len(planned) == 1


def test_sleep_closes_ingress_scales_every_dependency_then_stops_database() -> None:
    planned = commands("demo", "sleep")
    assert all(command[1:3] == ["containerapp", "ingress"] for command in planned[:3])
    assert planned[-1][1:4] == ["postgres", "flexible-server", "stop"]
    names = {
        command[command.index("--name") + 1]
        for command in planned
        if command[1:3] == ["containerapp", "update"]
    }
    assert {f"ca-demo-{member}" for member in (*APPLICATIONS, "keycloak", "temporal", "auth-redis", "pgbouncer")} == names


def test_uat_does_not_mutate_external_temporal() -> None:
    serialized = " ".join(" ".join(command) for command in commands("uat", "sleep"))
    assert "ca-uat-temporal" not in serialized


def test_sleep_denies_missing_or_failed_gate_before_any_provider_command() -> None:
    invoked: list[list[str]] = []

    with pytest.raises(AzureLifecycleError, match="sleep gates"):
        execute(
            "demo",
            "sleep",
            sleep_evidence={field: field != "backup_ready" for field in SLEEP_GATES},
            runner=lambda command: invoked.append(list(command)) or "",
        )
    assert invoked == []


def test_activation_waits_for_database_readiness() -> None:
    invocations: list[list[str]] = []
    states = iter(["Starting", "Ready"])

    def runner(command):
        invocations.append(list(command))
        return next(states) if command[1:4] == ["postgres", "flexible-server", "show"] else ""

    record = execute("demo", "activate", sleep_evidence=None, runner=runner)
    assert record["retained_authoritative_data"] is True
    assert sum(command[1:4] == ["postgres", "flexible-server", "show"] for command in invocations) == 2
