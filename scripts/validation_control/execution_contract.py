"""Deterministic WC-106 execution readiness and retry controls."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from threading import get_ident
from typing import Any

from validation_control.identity import MANIFEST_SCHEMAS, digest_identity


SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9_.-]+")


class UnchangedExecutionFailureError(ValueError):
    """Raised before execution when the same environment already failed."""


def safe_segment(value: str) -> str:
    segment = SAFE_SEGMENT.sub("-", value).strip("-.")
    if not segment:
        raise ValueError("execution identity segment is empty")
    return segment


def _path_identity(path: Path) -> dict[str, object]:
    try:
        status = path.stat()
    except FileNotFoundError:
        return {"exists": False, "path": str(path.resolve())}
    return {
        "exists": True,
        "gid": status.st_gid,
        "mode": status.st_mode & 0o7777,
        "path": str(path.resolve()),
        "uid": status.st_uid,
    }


def orchestration_preflight(
    repository: Path,
    docker_socket: Path = Path("/var/run/docker.sock"),
) -> None:
    """Prove cheap host/outer-runner requirements before runner resolution or build."""
    home_value = os.environ.get("HOME", "")
    home = Path(home_value)
    if not home.is_absolute():
        raise ValueError("execution preflight: HOME must be an absolute path")
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(f"execution preflight: HOME cannot be created: {home}") from error
    if not os.access(home, os.W_OK):
        raise ValueError(f"execution preflight: HOME is not writable: {home}")
    if not docker_socket.is_socket() or not os.access(docker_socket, os.R_OK | os.W_OK):
        raise ValueError(f"execution preflight: Docker socket is unavailable: {docker_socket}")

    probe = repository / f"test-results/wc106/.orchestration-probe-{os.getpid()}-{get_ident()}"
    temporary = probe.with_suffix(f".tmp-{os.getpid()}")
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text("wc106-orchestration\n", encoding="utf-8")
        os.replace(temporary, probe)
        if probe.read_text(encoding="utf-8") != "wc106-orchestration\n":
            raise ValueError("execution preflight: host-visible output cannot be read after atomic replacement")
    except OSError as error:
        raise ValueError("execution preflight: host-visible output is not writable") from error
    finally:
        temporary.unlink(missing_ok=True)
        probe.unlink(missing_ok=True)


def static_preflight(manifests: list[dict[str, Any]], execution: dict[str, Any]) -> dict[str, Any]:
    """Reject deterministic execution defects without building or executing a gate."""
    violations: list[str] = []
    by_type = {manifest.get("identity_type"): manifest for manifest in manifests}
    for identity_type, schema in MANIFEST_SCHEMAS.items():
        manifest = by_type.get(identity_type)
        if not isinstance(manifest, dict) or manifest.get("schema") != schema:
            violations.append(f"manifest:{identity_type}")
            continue
        inputs = manifest.get("inputs")
        if not isinstance(inputs, dict) or manifest.get("digest") != digest_identity(identity_type, inputs):
            violations.append(f"manifest-digest:{identity_type}")

    checks = (
        (execution.get("catalog_valid") is True, "catalog"),
        (execution.get("syntax_valid") is True, "syntax"),
        (execution.get("uid") not in (None, 0), "uid"),
        (execution.get("gid") not in (None, 0), "gid"),
        (isinstance(execution.get("mounts"), list) and bool(execution["mounts"]), "mount"),
        (execution.get("permissions_valid") is True, "permission"),
        (execution.get("output_writable") is True, "output"),
        (
            execution.get("docker_socket_requested") is not True or execution.get("docker_socket_allowed") is True,
            "socket",
        ),
        (execution.get("workflow_placement") == "container", "workflow-placement"),
    )
    violations.extend(label for passed, label in checks if not passed)
    return {
        "schema": "waooaw.static-preflight-result/v1",
        "result": "PASS" if not violations else "FAIL",
        "first_cause": violations[0] if violations else None,
        "violations": violations,
        "build_events": 0,
        "execution_events": 0,
    }


def execution_binding(
    plan: dict[str, Any],
    node: dict[str, Any],
    image_id: str,
    repository: Path,
    docker_socket: Path = Path("/var/run/docker.sock"),
) -> dict[str, object]:
    environment = node.get("environment", [])
    if not isinstance(environment, list) or not all(isinstance(name, str) for name in environment):
        raise ValueError("validation plan node has invalid environment allowlist")
    environment_values = {name: os.environ.get(name) for name in sorted(environment)}
    environment_digest = hashlib.sha256(
        json.dumps(environment_values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    implementation_digest = hashlib.sha256()
    for relative in (
        "docker-compose.yml",
        "validation/engineering-validation.yaml",
        "scripts/validation_control/catalog_execution.py",
        "scripts/validation_control/execution_contract.py",
        "scripts/validation_control/run_execution_contract.sh",
    ):
        path = repository / relative
        implementation_digest.update(relative.encode())
        implementation_digest.update(b"\0")
        implementation_digest.update(path.read_bytes() if path.is_file() else b"MISSING")
        implementation_digest.update(b"\0")
    return {
        "compose_service": node["compose_service"],
        "contract_implementation_digest": implementation_digest.hexdigest(),
        "docker_socket": _path_identity(docker_socket),
        "docker_socket_required": bool(node.get("resources", {}).get("docker_socket", False)),
        "environment_digest": environment_digest,
        "gate_id": node["gate_id"],
        "head_sha": plan.get("head_sha"),
        "image_id": image_id,
        "orchestration_home": _path_identity(Path(os.environ.get("HOME", ""))),
        "profile": node["profile"],
        "repository": _path_identity(repository),
        "test_results": _path_identity(repository / "test-results"),
    }


def binding_digest(binding: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def failure_path(repository: Path, gate_id: str) -> Path:
    return repository / "test-results/wc106/execution-failures" / f"{safe_segment(gate_id)}.json"


def evidence_path(repository: Path, namespace: str, gate_id: str) -> Path:
    return repository / "test-results/wc106/execution-contract" / safe_segment(namespace) / f"{safe_segment(gate_id)}.proof"


def assert_retry_allowed(repository: Path, gate_id: str, digest: str) -> None:
    path = failure_path(repository, gate_id)
    if not path.is_file():
        return
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UnchangedExecutionFailureError(
            f"execution-contract failure record for {gate_id} is unreadable; remove or repair that bound evidence"
        ) from error
    if record.get("binding_digest") == digest:
        raise UnchangedExecutionFailureError(
            f"unchanged execution-contract failure for {gate_id}; change a bound runner or environment input before retry"
        )


def _atomic_json(path: Path, content: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def record_failure(repository: Path, gate_id: str, digest: str, reason: str) -> None:
    _atomic_json(
        failure_path(repository, gate_id),
        {
            "binding_digest": digest,
            "failure_fingerprint": hashlib.sha256(f"{digest}:{reason}".encode()).hexdigest(),
            "gate_id": gate_id,
            "reason": reason,
            "schema": "waooaw.execution-contract-failure/v1",
        },
    )


def clear_failure(repository: Path, gate_id: str) -> None:
    failure_path(repository, gate_id).unlink(missing_ok=True)


def prepare_evidence(repository: Path, namespace: str, gate_id: str, digest: str) -> tuple[Path, str]:
    path = evidence_path(repository, namespace, gate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o777)
    path.unlink(missing_ok=True)
    token = hashlib.sha256(f"{namespace}:{gate_id}:{digest}".encode()).hexdigest()
    return path, token


def evidence_is_current(path: Path, token: str) -> bool:
    host_temporary = path.with_suffix(path.suffix + f".host-{os.getpid()}")
    try:
        if not path.is_file() or path.read_text(encoding="utf-8") != token + "\n":
            return False
        host_temporary.write_text(token + "\n", encoding="utf-8")
        os.replace(host_temporary, path)
        return os.access(path, os.R_OK | os.W_OK) and path.read_text(encoding="utf-8") == token + "\n"
    except OSError:
        return False
    finally:
        host_temporary.unlink(missing_ok=True)
