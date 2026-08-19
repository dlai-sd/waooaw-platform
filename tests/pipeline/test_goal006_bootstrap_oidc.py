"""Offline contracts for constrained Phase 3 bootstrap OIDC evidence."""

from __future__ import annotations

from copy import deepcopy

from scripts.goal006_bootstrap_oidc import STATE_ROLE, validate_bootstrap_oidc

PRINCIPAL_ID = "00000000-0000-0000-0000-000000000010"
STATE_SCOPE = "/subscriptions/sub/resourceGroups/state/providers/Microsoft.Storage/storageAccounts/state"
SUBSCRIPTION_SCOPE = "/subscriptions/sub"
SUBJECTS = {
    "repo:dlai-sd/waooaw-platform:environment:demo",
    "repo:dlai-sd/waooaw-platform:environment:uat",
    "repo:dlai-sd/waooaw-platform:environment:prod",
}
ROLES = {
    ("Contributor", SUBSCRIPTION_SCOPE),
    ("Role Based Access Control Administrator", SUBSCRIPTION_SCOPE),
    (STATE_ROLE, STATE_SCOPE),
}


def evidence() -> tuple[dict[str, str], list[object], list[dict[str, object]], list[dict[str, str]]]:
    service_principal = {"id": PRINCIPAL_ID}
    credentials: list[object] = []
    federation = [
        {
            "issuer": "https://token.actions.githubusercontent.com",
            "audiences": ["api://AzureADTokenExchange"],
            "subject": subject,
        }
        for subject in sorted(SUBJECTS)
    ]
    assignments = [
        {"principalId": PRINCIPAL_ID, "roleDefinitionName": role, "scope": scope}
        for role, scope in sorted(ROLES)
    ]
    return service_principal, credentials, federation, assignments


def validate(
    service_principal: dict[str, str],
    credentials: list[object],
    federation: list[dict[str, object]],
    assignments: list[dict[str, str]],
) -> list[str]:
    return validate_bootstrap_oidc(
        service_principal,
        credentials,
        federation,
        assignments,
        principal_id=PRINCIPAL_ID,
        expected_subjects=SUBJECTS,
        expected_roles=ROLES,
        state_scope=STATE_SCOPE,
    )


def test_exact_bootstrap_oidc_evidence_passes() -> None:
    assert validate(*evidence()) == []


def test_subject_or_audience_drift_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    federation[0]["subject"] = "repo:fork/waooaw-platform:environment:demo"
    federation[1]["audiences"] = ["unexpected"]
    assert validate(service_principal, credentials, federation, assignments) == [
        "OIDC_AUDIENCE_INVALID",
        "OIDC_SUBJECT_SET_MISMATCH",
    ]


def test_client_secret_or_owner_role_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    credentials.append({"displayName": "forbidden-secret"})
    assignments.append({"principalId": PRINCIPAL_ID, "roleDefinitionName": "Owner", "scope": SUBSCRIPTION_SCOPE})
    assert validate(service_principal, credentials, federation, assignments) == [
        "CLIENT_SECRET_PRESENT",
        "PROHIBITED_ROLE_ASSIGNED",
        "ROLE_ASSIGNMENT_SET_MISMATCH",
    ]


def test_missing_state_access_or_unexpected_role_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    assignments = [assignment for assignment in assignments if assignment["roleDefinitionName"] != STATE_ROLE]
    assignments.append({"principalId": PRINCIPAL_ID, "roleDefinitionName": "Reader", "scope": STATE_SCOPE})
    assert validate(service_principal, credentials, federation, assignments) == [
        "ROLE_ASSIGNMENT_SET_MISMATCH",
        "STATE_ACCESS_MISSING",
    ]