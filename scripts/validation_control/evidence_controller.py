"""WC-109 evidence acceptance, publication, failure routing, and retry control."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any


SCHEMA = "waooaw.validation-evidence-envelope/v1"
MAX_ENVELOPE_BYTES = 64 * 1024
MAX_FIRST_CAUSE_BYTES = 512
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
RESULTS = {"PASS", "FAIL", "BLOCKED", "CANCELLED"}
ROUTING_CLASSES = {"RUNNER", "WORKFLOW", "PRODUCT", "EXTERNAL", "EVIDENCE"}
ENVELOPE_ROUTING_CLASSES = {*ROUTING_CLASSES, "NONE"}
DISPOSITIONS = {"executed", "exact-candidate-reuse", "verified-carry-forward", "BLOCKED-DEFERRED"}
BLOCKED_DEFERRED_GATES = {"acceptance:as-001", "acceptance:as-003", "acceptance:as-005"}
BLOCKED_DEFERRED_AMENDMENT = "2026-10-01_AS001_AS003_AS005_BLOCKED_DEFERRED_AND_SINGLE_IMPLEMENTATION_PR_PILOT"
PROHIBITED_KEYS = {
    "authorization",
    "conversation",
    "customer_data",
    "password",
    "provider_token",
    "secret",
    "token",
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def catalog_invocation_signature(claim: dict[str, str], control_key: bytes) -> str:
    if len(control_key) < 32:
        raise ValueError("evidence control key must contain at least 32 bytes")
    required = {"namespace", "gate_id", "command_id", "head_sha"}
    if set(claim) != required or not COMMIT.fullmatch(claim["head_sha"]):
        raise ValueError("catalog invocation claim is incomplete")
    return "sha256:" + hmac.new(control_key, _canonical(claim), hashlib.sha256).hexdigest()


def failure_fingerprint(routing_class: str, gate_id: str, first_cause: str, binding_digest: str) -> str:
    if routing_class not in ROUTING_CLASSES or not SHA256.fullmatch(binding_digest):
        raise ValueError("failure fingerprint inputs are invalid")
    return (
        "sha256:"
        + hashlib.sha256(
            _canonical(
                {
                    "binding_digest": binding_digest,
                    "first_cause": first_cause,
                    "gate_id": gate_id,
                    "routing_class": routing_class,
                }
            )
        ).hexdigest()
    )


def route_failure(origin: str) -> str:
    routes = {
        "cache": "RUNNER",
        "container-runtime": "RUNNER",
        "image": "RUNNER",
        "mount": "RUNNER",
        "socket": "RUNNER",
        "toolchain": "RUNNER",
        "uid-gid": "RUNNER",
        "hosted-job": "WORKFLOW",
        "lifecycle-placement": "WORKFLOW",
        "orchestration": "WORKFLOW",
        "permission": "WORKFLOW",
        "application": "PRODUCT",
        "assertion": "PRODUCT",
        "compilation": "PRODUCT",
        "contract": "PRODUCT",
        "coverage": "PRODUCT",
        "generated-client": "PRODUCT",
        "security": "PRODUCT",
        "cloud": "EXTERNAL",
        "network": "EXTERNAL",
        "package-service": "EXTERNAL",
        "provider": "EXTERNAL",
        "registry": "EXTERNAL",
        "malformed-evidence": "EVIDENCE",
        "missing-evidence": "EVIDENCE",
        "stale-evidence": "EVIDENCE",
        "unpublished-evidence": "EVIDENCE",
        "untrusted-evidence": "EVIDENCE",
    }
    if origin not in routes:
        raise ValueError(f"failure origin is not classified: {origin}")
    return routes[origin]


def retry_allowed(
    *,
    routing_class: str,
    transient: bool,
    retry_policy: str,
    attempt: int,
    fingerprint: str,
    previous_fingerprint: str | None,
) -> bool:
    if routing_class not in ROUTING_CLASSES or not SHA256.fullmatch(fingerprint):
        raise ValueError("retry inputs are invalid")
    return (
        retry_policy == "transient-infrastructure-once"
        and transient
        and routing_class in {"RUNNER", "WORKFLOW", "EXTERNAL"}
        and attempt == 1
        and fingerprint != previous_fingerprint
    )


def repair_transition(
    failure: dict[str, str],
    *,
    current_binding_digest: str,
    affected_gates: list[str],
    focused_evidence: list[dict[str, str]],
) -> dict[str, Any]:
    required = {"routing_class", "gate_id", "first_cause", "binding_digest"}
    if set(failure) != required or not SHA256.fullmatch(current_binding_digest):
        raise ValueError("repair transition inputs are invalid")
    original_fingerprint = failure_fingerprint(
        failure["routing_class"],
        failure["gate_id"],
        failure["first_cause"],
        failure["binding_digest"],
    )
    invalidated_gates = list(dict.fromkeys([failure["gate_id"], *affected_gates]))
    blockers: list[str] = []
    if current_binding_digest == failure["binding_digest"]:
        blockers.append(f"unchanged-failure:{original_fingerprint}")
    by_gate = {item.get("gate_id"): item for item in focused_evidence if isinstance(item, dict)}
    if not blockers:
        for gate_id in invalidated_gates:
            evidence = by_gate.get(gate_id)
            if evidence is None:
                blockers.append(f"missing-focused-pass:{gate_id}")
            elif (
                evidence.get("result") != "PASS"
                or evidence.get("mode") != "focused"
                or evidence.get("binding_digest") != current_binding_digest
                or evidence.get("trust_source") != "catalog-controlled"
                or not SHA256.fullmatch(str(evidence.get("evidence_identity", "")))
            ):
                blockers.append(f"incompatible-focused-pass:{gate_id}")
    return {
        "schema": "waooaw.repair-transition/v1",
        "result": "PASS" if not blockers else "BLOCKED",
        "failure_fingerprint": original_fingerprint,
        "original_binding_digest": failure["binding_digest"],
        "current_binding_digest": current_binding_digest,
        "invalidated_gates": invalidated_gates,
        "blockers": blockers,
        "restitch_eligible": not blockers,
    }


def _prohibited_path(value: object, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in PROHIBITED_KEYS or normalized.endswith(("_secret", "_token", "_password")):
                return f"{path}.{key}"
            prohibited = _prohibited_path(child, f"{path}.{key}")
            if prohibited:
                return prohibited
    elif isinstance(value, list):
        for index, child in enumerate(value):
            prohibited = _prohibited_path(child, f"{path}[{index}]")
            if prohibited:
                return prohibited
    return None


def _validate_disposition(envelope: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    disposition = envelope.get("disposition")
    proof = envelope.get("disposition_proof")
    identities = envelope.get("identities", {})
    if disposition not in DISPOSITIONS or not isinstance(proof, dict):
        return ["DISPOSITION_INVALID"]
    if disposition == "BLOCKED-DEFERRED":
        if (
            envelope.get("gate_id") not in BLOCKED_DEFERRED_GATES
            or envelope.get("result") != "BLOCKED"
            or proof
            != {
                "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                "release_blocking": True,
            }
        ):
            violations.append("BLOCKED_DEFERRED_PROOF_INVALID")
    elif disposition == "executed":
        if proof != {"execution_fresh": True}:
            violations.append("EXECUTED_PROOF_INVALID")
    elif disposition == "exact-candidate-reuse":
        if (
            proof.get("candidate_identity") != identities.get("candidate")
            or proof.get("test_execution_identity") != identities.get("test_execution")
            or proof.get("freshness_current") is not True
            or not SHA256.fullmatch(str(proof.get("source_evidence_identity", "")))
        ):
            violations.append("EXACT_REUSE_PROOF_INVALID")
    else:
        source_head = proof.get("source_head")
        if (
            not isinstance(source_head, str)
            or not COMMIT.fullmatch(source_head)
            or proof.get("target_head") != envelope.get("head_sha")
            or proof.get("commit_range") != f"{source_head}..{envelope.get('head_sha')}"
            or proof.get("non_impact_proven") is not True
            or proof.get("execution_fresh") is not False
            or not SHA256.fullmatch(str(proof.get("changed_path_digest", "")))
        ):
            violations.append("CARRY_FORWARD_PROOF_INVALID")
    return violations


def validate_envelope(
    envelope: dict[str, Any],
    control_key: bytes,
    *,
    required_trust_source: str,
    prohibited_values: tuple[str, ...] = (),
) -> list[str]:
    violations: list[str] = []
    if envelope.get("schema") != SCHEMA:
        violations.append("SCHEMA_INVALID")
    if not COMMIT.fullmatch(str(envelope.get("base_sha", ""))) or not COMMIT.fullmatch(str(envelope.get("head_sha", ""))):
        violations.append("COMMIT_BINDING_INVALID")
    identities = envelope.get("identities")
    required_identities = {"runner", "test_execution", "subject", "evidence"}
    if (
        not isinstance(identities, dict)
        or set(identities) < required_identities
        or any(not SHA256.fullmatch(str(identities.get(identity, ""))) for identity in required_identities)
    ):
        violations.append("IDENTITY_BINDING_INVALID")
    for field in ("component", "gate_id", "command_id", "started_at"):
        if not isinstance(envelope.get(field), str) or not envelope[field]:
            violations.append(f"{field.upper()}_INVALID")
    duration = envelope.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
        violations.append("DURATION_INVALID")
    if envelope.get("result") not in RESULTS:
        violations.append("RESULT_INVALID")
    routing_class = envelope.get("routing_class")
    if routing_class not in ENVELOPE_ROUTING_CLASSES or (routing_class == "NONE") != (envelope.get("result") == "PASS"):
        violations.append("ROUTING_CLASS_INVALID")
    first_cause = envelope.get("first_cause")
    if not isinstance(first_cause, str) or len(first_cause.encode()) > MAX_FIRST_CAUSE_BYTES:
        violations.append("FIRST_CAUSE_INVALID")
    artifacts = envelope.get("artifacts")
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or any(
            not isinstance(artifact, dict)
            or not isinstance(artifact.get("path"), str)
            or not SHA256.fullmatch(str(artifact.get("digest", "")))
            for artifact in artifacts
        )
    ):
        violations.append("ARTIFACT_REFERENCE_INVALID")
    violations.extend(_validate_disposition(envelope))
    invocation = envelope.get("invocation")
    if not isinstance(invocation, dict) or invocation.get("source") != "catalog":
        violations.append("INVOCATION_UNTRUSTED")
    else:
        claim = {
            "namespace": invocation.get("namespace"),
            "gate_id": envelope.get("gate_id"),
            "command_id": envelope.get("command_id"),
            "head_sha": envelope.get("head_sha"),
        }
        try:
            expected = catalog_invocation_signature(claim, control_key)
        except ValueError:
            violations.append("INVOCATION_CLAIM_INVALID")
        else:
            if not hmac.compare_digest(str(invocation.get("signature", "")), expected):
                violations.append("INVOCATION_SIGNATURE_INVALID")
    if envelope.get("trust_source") != required_trust_source:
        violations.append("TRUST_SOURCE_INVALID")
    prohibited = _prohibited_path(envelope)
    if prohibited:
        violations.append(f"PROHIBITED_FIELD:{prohibited}")
    encoded = _canonical(envelope)
    if len(encoded) > MAX_ENVELOPE_BYTES:
        violations.append("ENVELOPE_TOO_LARGE")
    for value in prohibited_values:
        if value and value.encode() in encoded:
            violations.append("PROHIBITED_VALUE")
            break
    return violations


def publish_envelope(
    path: Path,
    envelope: dict[str, Any],
    control_key: bytes,
    *,
    required_trust_source: str,
    artifact_root: Path | None = None,
) -> None:
    violations = validate_envelope(envelope, control_key, required_trust_source=required_trust_source)
    if violations:
        raise ValueError("evidence envelope rejected: " + ",".join(violations))
    if artifact_root is not None:
        for artifact in envelope["artifacts"]:
            relative = Path(artifact["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"artifact reference escapes evidence root: {relative}")
            artifact_path = artifact_root / relative
            if not artifact_path.is_file():
                raise ValueError(f"evidence artifact is missing: {relative}")
            digest = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if not hmac.compare_digest(digest, artifact["digest"]):
                raise ValueError(f"evidence artifact digest mismatch: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(json.dumps(envelope, indent=2, sort_keys=True).encode() + b"\n")
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ValueError(f"terminal evidence already exists: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
