"""WC-109 evidence, freshness, routing, retry, secrecy and publication boundaries."""

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from validation_control.evidence_controller import (
    catalog_invocation_signature,
    failure_fingerprint,
    publish_envelope,
    repair_transition,
    retry_allowed,
    route_failure,
    validate_envelope,
)


CONTROL_KEY = b"wc109-fixture-control-key-material-32-bytes"
DIGESTS = ["sha256:" + character * 64 for character in "12345678"]


def envelope(disposition: str = "executed") -> dict[str, object]:
    head_sha = "b" * 40
    claim = {
        "namespace": "wc109-fixture",
        "gate_id": "test-web",
        "command_id": "test-web",
        "head_sha": head_sha,
    }
    proofs = {
        "executed": {"execution_fresh": True},
        "exact-candidate-reuse": {
            "candidate_identity": DIGESTS[2],
            "test_execution_identity": DIGESTS[1],
            "source_evidence_identity": DIGESTS[4],
            "freshness_current": True,
        },
        "verified-carry-forward": {
            "source_head": "a" * 40,
            "target_head": head_sha,
            "commit_range": f"{'a' * 40}..{head_sha}",
            "changed_path_digest": DIGESTS[5],
            "non_impact_proven": True,
            "execution_fresh": False,
        },
        "BLOCKED-DEFERRED": {
            "founder_scope_amendment": ("2026-10-01_AS001_AS003_AS005_BLOCKED_DEFERRED_AND_SINGLE_IMPLEMENTATION_PR_PILOT"),
            "release_blocking": True,
        },
    }
    return {
        "schema": "waooaw.validation-evidence-envelope/v1",
        "base_sha": "a" * 40,
        "head_sha": head_sha,
        "identities": {
            "runner": DIGESTS[0],
            "test_execution": DIGESTS[1],
            "candidate": DIGESTS[2],
            "subject": DIGESTS[3],
            "evidence": DIGESTS[4],
        },
        "component": "web",
        "gate_id": "test-web",
        "command_id": "test-web",
        "started_at": "2026-09-29T12:00:00Z",
        "duration_ms": 123,
        "result": "PASS",
        "routing_class": "NONE",
        "first_cause": "none",
        "artifacts": [{"path": "coverage/web/coverage.json", "digest": DIGESTS[6]}],
        "disposition": disposition,
        "disposition_proof": proofs[disposition],
        "invocation": {
            "source": "catalog",
            "namespace": claim["namespace"],
            "signature": catalog_invocation_signature(claim, CONTROL_KEY),
        },
        "trust_source": "local-diagnostic",
    }


def blocked_deferred_envelope() -> dict[str, object]:
    record = envelope("BLOCKED-DEFERRED")
    record.update(
        {
            "gate_id": "acceptance:as-001",
            "command_id": "acceptance-as-001",
            "result": "BLOCKED",
            "routing_class": "EXTERNAL",
            "first_cause": "Founder-approved product acceptance deferral",
        }
    )
    claim = {
        "namespace": record["invocation"]["namespace"],
        "gate_id": record["gate_id"],
        "command_id": record["command_id"],
        "head_sha": record["head_sha"],
    }
    record["invocation"]["signature"] = catalog_invocation_signature(claim, CONTROL_KEY)
    return record


@pytest.mark.parametrize("disposition", ["executed", "exact-candidate-reuse", "verified-carry-forward"])
def test_all_three_evidence_dispositions_are_explicit_and_accepted(disposition: str) -> None:
    assert validate_envelope(envelope(disposition), CONTROL_KEY, required_trust_source="local-diagnostic") == []


def test_founder_approved_blocked_deferred_evidence_is_accepted() -> None:
    assert validate_envelope(blocked_deferred_envelope(), CONTROL_KEY, required_trust_source="local-diagnostic") == []


@pytest.mark.parametrize(
    "mutation",
    (
        {"gate_id": "acceptance:pse-failover"},
        {"result": "PASS"},
        {"disposition_proof": {"release_blocking": False}},
    ),
)
def test_blocked_deferred_evidence_fails_closed_outside_exact_amendment(mutation: dict[str, object]) -> None:
    record = {**blocked_deferred_envelope(), **mutation}

    assert "BLOCKED_DEFERRED_PROOF_INVALID" in validate_envelope(record, CONTROL_KEY, required_trust_source="local-diagnostic")


@pytest.mark.parametrize(
    ("mutation", "violation"),
    (
        ({"head_sha": "wrong"}, "COMMIT_BINDING_INVALID"),
        ({"duration_ms": -1}, "DURATION_INVALID"),
        ({"result": "UNKNOWN"}, "RESULT_INVALID"),
        ({"routing_class": "OTHER"}, "ROUTING_CLASS_INVALID"),
        ({"first_cause": "x" * 513}, "FIRST_CAUSE_INVALID"),
        ({"artifacts": []}, "ARTIFACT_REFERENCE_INVALID"),
    ),
)
def test_malformed_or_unbound_evidence_fails_closed(mutation: dict[str, object], violation: str | None) -> None:
    record = {**envelope(), **mutation}
    violations = validate_envelope(record, CONTROL_KEY, required_trust_source="local-diagnostic")

    if violation is None:
        assert violations == []
    else:
        assert violation in violations


def test_direct_docker_diagnostic_cannot_publish_accepted_pass(tmp_path: Path) -> None:
    direct = envelope()
    direct["invocation"] = {"source": "direct", "namespace": "wc109-fixture"}

    with pytest.raises(ValueError, match="INVOCATION_UNTRUSTED"):
        publish_envelope(tmp_path / "direct.json", direct, CONTROL_KEY, required_trust_source="local-diagnostic")
    assert not (tmp_path / "direct.json").exists()


def test_signature_and_trust_source_are_independently_required() -> None:
    wrong_signature = deepcopy(envelope())
    wrong_signature["invocation"]["signature"] = DIGESTS[7]
    wrong_trust = deepcopy(envelope())
    wrong_trust["trust_source"] = "forged-hosted"

    assert "INVOCATION_SIGNATURE_INVALID" in validate_envelope(
        wrong_signature, CONTROL_KEY, required_trust_source="local-diagnostic"
    )
    assert "TRUST_SOURCE_INVALID" in validate_envelope(wrong_trust, CONTROL_KEY, required_trust_source="local-diagnostic")


def test_secret_canaries_and_classified_fields_are_rejected() -> None:
    canary = "wc109-provider-canary"
    value_leak = deepcopy(envelope())
    value_leak["first_cause"] = f"provider returned {canary}"
    field_leak = deepcopy(envelope())
    field_leak["provider_token"] = "redacted-or-not-this-field-is-prohibited"

    assert "PROHIBITED_VALUE" in validate_envelope(
        value_leak,
        CONTROL_KEY,
        required_trust_source="local-diagnostic",
        prohibited_values=(canary,),
    )
    assert any(
        violation.startswith("PROHIBITED_FIELD")
        for violation in validate_envelope(field_leak, CONTROL_KEY, required_trust_source="local-diagnostic")
    )


def test_terminal_publication_is_atomic_and_collision_fails(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    record = envelope()
    artifact = tmp_path / record["artifacts"][0]["path"]
    artifact.parent.mkdir(parents=True)
    artifact.write_text("native evidence\n", encoding="utf-8")
    record["artifacts"][0]["digest"] = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()

    publish_envelope(path, record, CONTROL_KEY, required_trust_source="local-diagnostic", artifact_root=tmp_path)
    first = path.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        publish_envelope(path, record, CONTROL_KEY, required_trust_source="local-diagnostic", artifact_root=tmp_path)

    assert path.read_bytes() == first
    assert not list(tmp_path.glob("*.tmp-*"))


@pytest.mark.parametrize(("defect", "message"), (("missing", "is missing"), ("corrupt", "digest mismatch")))
def test_missing_or_corrupt_native_output_never_publishes_pass(tmp_path: Path, defect: str, message: str) -> None:
    record = envelope()
    artifact = tmp_path / record["artifacts"][0]["path"]
    if defect == "corrupt":
        artifact.parent.mkdir(parents=True)
        artifact.write_text("not the bound bytes\n", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        publish_envelope(
            tmp_path / "evidence.json",
            record,
            CONTROL_KEY,
            required_trust_source="local-diagnostic",
            artifact_root=tmp_path,
        )
    assert not (tmp_path / "evidence.json").exists()


@pytest.mark.parametrize(
    ("origin", "routing_class"),
    (
        ("image", "RUNNER"),
        ("orchestration", "WORKFLOW"),
        ("assertion", "PRODUCT"),
        ("registry", "EXTERNAL"),
        ("stale-evidence", "EVIDENCE"),
    ),
)
def test_failure_routes_to_exactly_one_owner_without_changing_result(origin: str, routing_class: str) -> None:
    assert route_failure(origin) == routing_class


def test_retry_is_bounded_to_changed_transient_infrastructure_fingerprint() -> None:
    fingerprint = failure_fingerprint("EXTERNAL", "test-web", "registry timeout", DIGESTS[0])

    assert retry_allowed(
        routing_class="EXTERNAL",
        transient=True,
        retry_policy="transient-infrastructure-once",
        attempt=1,
        fingerprint=fingerprint,
        previous_fingerprint=None,
    )
    assert not retry_allowed(
        routing_class="EXTERNAL",
        transient=True,
        retry_policy="transient-infrastructure-once",
        attempt=1,
        fingerprint=fingerprint,
        previous_fingerprint=fingerprint,
    )
    assert not retry_allowed(
        routing_class="PRODUCT",
        transient=False,
        retry_policy="transient-infrastructure-once",
        attempt=1,
        fingerprint=failure_fingerprint("PRODUCT", "test-web", "assertion", DIGESTS[0]),
        previous_fingerprint=None,
    )


def test_repair_transition_blocks_unchanged_failure_fingerprint() -> None:
    failure = {
        "routing_class": "PRODUCT",
        "gate_id": "test-web",
        "first_cause": "assertion",
        "binding_digest": DIGESTS[0],
    }

    outcome = repair_transition(
        failure,
        current_binding_digest=DIGESTS[0],
        affected_gates=["e2e:accessibility"],
        focused_evidence=[],
    )

    assert outcome["result"] == "BLOCKED"
    assert outcome["blockers"] == [f"unchanged-failure:{outcome['failure_fingerprint']}"]
    assert outcome["restitch_eligible"] is False


@pytest.mark.parametrize(
    "evidence",
    (
        {"gate_id": "test-web", "result": "FAIL", "mode": "focused", "binding_digest": DIGESTS[1]},
        {"gate_id": "test-web", "result": "PASS", "mode": "qualification", "binding_digest": DIGESTS[1]},
        {"gate_id": "test-web", "result": "PASS", "mode": "focused", "binding_digest": DIGESTS[2]},
    ),
)
def test_repair_transition_rejects_incompatible_focused_evidence(evidence: dict[str, str]) -> None:
    outcome = repair_transition(
        {
            "routing_class": "PRODUCT",
            "gate_id": "test-web",
            "first_cause": "assertion",
            "binding_digest": DIGESTS[0],
        },
        current_binding_digest=DIGESTS[1],
        affected_gates=[],
        focused_evidence=[evidence],
    )

    assert outcome["blockers"] == ["incompatible-focused-pass:test-web"]
    assert outcome["restitch_eligible"] is False


def test_repair_transition_requires_every_invalidated_gate_before_restitch() -> None:
    failure = {
        "routing_class": "PRODUCT",
        "gate_id": "test-web",
        "first_cause": "assertion",
        "binding_digest": DIGESTS[0],
    }
    repaired_gate = {
        "gate_id": "test-web",
        "result": "PASS",
        "mode": "focused",
        "binding_digest": DIGESTS[1],
        "trust_source": "catalog-controlled",
        "evidence_identity": DIGESTS[3],
    }

    incomplete = repair_transition(
        failure,
        current_binding_digest=DIGESTS[1],
        affected_gates=["e2e:accessibility", "e2e:accessibility"],
        focused_evidence=[repaired_gate],
    )
    complete = repair_transition(
        failure,
        current_binding_digest=DIGESTS[1],
        affected_gates=["e2e:accessibility"],
        focused_evidence=[
            repaired_gate,
            {
                "gate_id": "e2e:accessibility",
                "result": "PASS",
                "mode": "focused",
                "binding_digest": DIGESTS[1],
                "trust_source": "catalog-controlled",
                "evidence_identity": DIGESTS[4],
            },
        ],
    )

    assert incomplete["invalidated_gates"] == ["test-web", "e2e:accessibility"]
    assert incomplete["blockers"] == ["missing-focused-pass:e2e:accessibility"]
    assert complete["result"] == "PASS"
    assert complete["blockers"] == []
    assert complete["restitch_eligible"] is True
