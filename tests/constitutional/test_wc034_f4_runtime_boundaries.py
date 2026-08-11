# Implements: ADR-046 sections 3.4, 5.2, 5.3, 7.1, and 10
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-076, C-080

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_service_authentication_has_no_constitutional_engine_dependency() -> None:
    files = [
        "src/professional-runtime/workload_identity.py",
        "src/professional-runtime/mtls_protocol.py",
        "src/billing-engine/workload_identity.py",
        "src/billing-engine/mtls_protocol.py",
        "src/business-platform/Services/WorkloadIdentityClient.cs",
    ]
    for path in files:
        text = source(path).lower()
        assert "validateaction" not in text
        assert "recordevidence" not in text
        assert "constitutional_engine" not in text


def test_emergency_stop_path_is_not_routed_through_workspace_owners() -> None:
    stop_sources = "\n".join(
        source(path) for path in [
            "src/professional-runtime/routers/emergency_stop.py",
        ] if (ROOT / path).exists()
    ).lower()
    assert "relationship_workspace" not in stop_sources
    assert "billing-engine" not in stop_sources
    assert "domain-adapter" not in stop_sources
    assert "delegated_context" not in stop_sources


def test_auth_telemetry_excludes_protected_values_and_identity_material() -> None:
    for path in [
        "src/professional-runtime/relationship_workspace.py",
        "src/billing-engine/relationship_workspace.py",
    ]:
        log_lines = [line.lower() for line in source(path).splitlines() if "logger." in line]
        auth_lines = [line for line in log_lines if "service_auth" in line]
        assert auth_lines
        for line in auth_lines:
            assert not any(value in line for value in [
                "actor_subject", "tenant_id", "relationship_id", "certificate", "signature",
                "authorization", "correlation_id", "idempotency_key",
            ])


def test_dma_family_remains_explicitly_unavailable_without_owner_runtime() -> None:
    controller = source("src/business-platform/Controllers/RelationshipWorkspaceController.cs")
    assert 'UnavailableSectionAsync(relationshipId, "RESULTS", "outcomes"' in controller
    assert 'sectionType == "WORK" ? "PR" : "DMA"' in controller