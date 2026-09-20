#!/usr/bin/env python3
"""Run applicable PR prechecks as a bounded, evidence-producing DAG."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.6
# Constitutional basis: C-023, C-059, C-065, C-071, C-080

from __future__ import annotations

import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_ARTIFACT_BYTES = 64 * 1024
INFRASTRUCTURE_MARKERS = (
    "docker daemon",
    "connection reset",
    "connection refused",
    "no space left",
    "temporary failure",
    "timed out",
)
ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
ACTIVE_PROCESSES_LOCK = threading.Lock()
DEFAULT_PROGRESS_INTERVAL_SECONDS = 30.0
EVIDENCE_FILE_NAME = "precheck-manifest.json"
EVIDENCE_SCHEMA = "waooaw.pr-prechecks/v4"


@dataclass(frozen=True)
class PrecheckNode:
    """One deterministic node in the precheck graph."""

    name: str
    command: tuple[str, ...]
    heavy: bool = False
    dependencies: tuple[str, ...] = ()
    transient_retries: int = 0
    catalog_version: str = ""
    gate_id: str = ""
    command_id: str = ""
    gate_implementation_digest: str = ""
    runner_digest: str = ""
    environment_digest: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resource_preflight() -> tuple[bool, list[str]]:
    """Return whether bounded parallel execution is safe on this host."""
    reasons: list[str] = []
    if shutil.which("docker") is None:
        reasons.append("docker_unavailable")
    free_disk = shutil.disk_usage(Path.cwd()).free
    minimum_disk = int(os.environ.get("WC100_MIN_FREE_DISK_BYTES", str(5 * 1024**3)))
    if free_disk < minimum_disk:
        reasons.append("low_disk")
    memory_available = 0
    memory_info = Path("/proc/meminfo")
    if memory_info.is_file():
        for line in memory_info.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                memory_available = int(line.split()[1]) * 1024
                break
    minimum_memory = int(os.environ.get("WC100_MIN_AVAILABLE_MEMORY_BYTES", str(4 * 1024**3)))
    if memory_available and memory_available < minimum_memory:
        reasons.append("low_memory")
    current_process = os.getpid()
    for command_line in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            process_id = int(command_line.parent.name)
            command = command_line.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ValueError):
            continue
        if process_id != current_process and any(
            marker in command for marker in ("run_release_qualification.sh", "run_goal006_local_rehearsal.sh")
        ):
            reasons.append("conflicting_qualification_process")
            break
    return not reasons, reasons


def classify_failure(return_code: int, output: str) -> str:
    normalized = output.lower()
    if return_code in {130, -2, -15}:
        return "cancelled"
    if any(marker in normalized for marker in INFRASTRUCTURE_MARKERS):
        return "infrastructure"
    if "coverage" in normalized:
        return "coverage"
    if "gitleaks" in normalized or "secret" in normalized or "vulnerab" in normalized:
        return "security"
    if "manifest" in normalized or "metadata" in normalized or "schema" in normalized:
        return "metadata"
    return "assertion"


def _write_bounded(path: Path, chunks: list[str]) -> None:
    encoded = "\n".join(chunks).encode()
    if len(encoded) > MAX_ARTIFACT_BYTES:
        encoded = encoded[:MAX_ARTIFACT_BYTES] + b"\n[artifact truncated]\n"
    path.write_bytes(encoded)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _node_identity(node: PrecheckNode, identity_inputs: dict[str, str]) -> str:
    payload = {
        "evidence_schema": EVIDENCE_SCHEMA,
        "base_sha": identity_inputs["base_sha"],
        "head_sha": identity_inputs["head_sha"],
        "changed_file_digest": identity_inputs["changed_file_digest"],
        "name": node.name,
        "command": node.command,
        "heavy": node.heavy,
        "dependencies": node.dependencies,
        "transient_retries": node.transient_retries,
        "catalog_version": node.catalog_version,
        "gate_id": node.gate_id,
        "command_id": node.command_id,
        "gate_implementation_digest": node.gate_implementation_digest,
        "runner_digest": node.runner_digest,
        "environment_digest": node.environment_digest,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _node_authority(node: PrecheckNode) -> dict[str, str]:
    return {
        "catalog_version": node.catalog_version,
        "gate_id": node.gate_id,
        "command_id": node.command_id,
        "gate_implementation_digest": node.gate_implementation_digest,
        "runner_digest": node.runner_digest,
        "environment_digest": node.environment_digest,
        "evidence_schema": EVIDENCE_SCHEMA,
    }


def _load_reusable_results(
    evidence_path: Path,
    artifact_dir: Path,
    nodes: list[PrecheckNode],
    identity_inputs: dict[str, str],
) -> dict[str, dict[str, object]]:
    if not evidence_path.is_file():
        return {}
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    reusable: dict[str, dict[str, object]] = {}
    prior_nodes = evidence.get("nodes")
    if not isinstance(prior_nodes, list):
        return {}
    prior_by_name = {item.get("name"): item for item in prior_nodes if isinstance(item, dict)}
    for node in nodes:
        prior = prior_by_name.get(node.name)
        if not isinstance(prior, dict) or prior.get("status") != "PASS":
            continue
        if prior.get("evidence_identity") != _node_identity(node, identity_inputs):
            continue
        artifact_digests = prior.get("artifact_digests")
        if not isinstance(artifact_digests, dict) or not artifact_digests:
            continue
        verified = True
        for path_text, expected_digest in artifact_digests.items():
            path = Path(path_text)
            if not path.is_relative_to(artifact_dir) or not path.is_file() or _sha256_file(path) != expected_digest:
                verified = False
                break
        if verified:
            reusable[node.name] = {
                **prior,
                "attempts": 0,
                "reuse": {
                    "reused": True,
                    "trust_source": "local-exact-candidate",
                    "invalidation_reason": None,
                },
            }
    return reusable


def _write_manifest_atomically(path: Path, manifest: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_command(
    command: tuple[str, ...],
    environment: dict[str, str],
    node_name: str,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(  # noqa: S603
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    with ACTIVE_PROCESSES_LOCK:
        ACTIVE_PROCESSES.add(process)
    try:
        progress_interval = float(environment.get("WC100_PROGRESS_INTERVAL_SECONDS", str(DEFAULT_PROGRESS_INTERVAL_SECONDS)))
        if progress_interval <= 0:
            raise ValueError("WC100_PROGRESS_INTERVAL_SECONDS must be greater than zero")
        while True:
            try:
                stdout, stderr = process.communicate(timeout=progress_interval)
                break
            except subprocess.TimeoutExpired:
                print(
                    f"[{utc_now()}] WC-100 precheck still running: {node_name} (pid={process.pid})",
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        with ACTIVE_PROCESSES_LOCK:
            ACTIVE_PROCESSES.discard(process)
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _terminate_active_processes() -> None:
    with ACTIVE_PROCESSES_LOCK:
        processes = tuple(ACTIVE_PROCESSES)
    for process in processes:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue


class _BlockedInterrupts:
    def __enter__(self) -> None:
        self.previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})

    def __exit__(self, *unused: object) -> None:
        signal.pthread_sigmask(signal.SIG_SETMASK, self.previous_mask)


def _cleanup_compose_projects(nodes: list[PrecheckNode]) -> None:
    docker = shutil.which("docker")
    if docker is None:
        return
    for node in nodes:
        subprocess.run(  # noqa: S603
            [docker, "compose", "-p", f"wc100-{node.name}-{os.getpid()}", "down", "--remove-orphans"],
            check=False,
            capture_output=True,
            text=True,
        )


def _run_node(
    node: PrecheckNode,
    artifact_dir: Path,
    heavy_slots: threading.Semaphore,
    evidence_identity: str,
) -> dict[str, object]:
    node_dir = artifact_dir / f"{node.name}.tmp"
    node_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = artifact_dir / f"{node.name}.stdout.log"
    stderr_path = artifact_dir / f"{node.name}.stderr.log"
    environment = os.environ.copy()
    environment.update(
        {
            "WC100_NODE": node.name,
            "TMPDIR": str(node_dir),
            "COVERAGE_FILE": str(node_dir / ".coverage"),
            "COMPOSE_PROJECT_NAME": f"wc100-{node.name}-{os.getpid()}",
        }
    )
    docker_socket = Path("/var/run/docker.sock")
    if docker_socket.exists():
        environment["DOCKER_GID"] = str(docker_socket.stat().st_gid)
    started_at = utc_now()
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    attempts = 0
    return_code = 1
    classification = "assertion"
    with heavy_slots if node.heavy else _NullContext():
        while attempts <= node.transient_retries:
            attempts += 1
            completed = _run_command(node.command, environment, node.name)
            stdout_chunks.append(completed.stdout)
            stderr_chunks.append(completed.stderr)
            return_code = completed.returncode
            if return_code == 0:
                classification = "none"
                break
            classification = classify_failure(return_code, f"{completed.stdout}\n{completed.stderr}")
            if classification != "infrastructure":
                break
    _write_bounded(stdout_path, stdout_chunks)
    _write_bounded(stderr_path, stderr_chunks)
    return {
        "name": node.name,
        "status": "PASS" if return_code == 0 else "FAIL",
        "classification": classification,
        "exit_code": return_code,
        "attempts": attempts,
        "started_at": started_at,
        "completed_at": utc_now(),
        "stdout_artifact": str(stdout_path),
        "stderr_artifact": str(stderr_path),
        "artifact_digests": {
            str(stdout_path): _sha256_file(stdout_path),
            str(stderr_path): _sha256_file(stderr_path),
        },
        "authority": _node_authority(node),
        "evidence_identity": evidence_identity,
        "reuse": {
            "reused": False,
            "trust_source": "original-run",
            "invalidation_reason": "not-reused",
        },
    }


class _NullContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *unused: object) -> None:
        return None


def run_prechecks(
    nodes: list[PrecheckNode],
    *,
    base_sha: str,
    head_sha: str,
    changed_file_digest: str,
    graph_version: str,
    configuration_digest: str,
    runner_digest: str,
    artifact_dir: Path,
    max_heavy: int | None = None,
    force_serial: bool = False,
    disable_reuse: bool = False,
    preflight: Callable[[], tuple[bool, list[str]]] = resource_preflight,
) -> dict[str, object]:
    """Execute a dependency graph and return complete immutable node evidence."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    max_heavy = max_heavy or int(os.environ.get("WC100_MAX_HEAVY_PRECHECKS", "2"))
    if max_heavy < 1:
        raise ValueError("max_heavy must be at least one")
    resources_ok, fallback_reasons = preflight()
    force_serial = force_serial or os.environ.get("WC100_PRECHECK_MODE") == "serial"
    mode = "parallel" if resources_ok and not force_serial else "serial"
    if force_serial and "configured_serial" not in fallback_reasons:
        fallback_reasons = [*fallback_reasons, "configured_serial"]
    reuse_enabled = not disable_reuse and os.environ.get("WC100_DISABLE_REUSE") != "1"

    names = [node.name for node in nodes]
    if len(names) != len(set(names)):
        raise ValueError("precheck node names must be unique")
    node_by_name = {node.name: node for node in nodes}
    identity_inputs = {
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_file_digest": changed_file_digest,
        "graph_version": graph_version,
        "configuration_digest": configuration_digest,
        "runner_digest": runner_digest,
    }
    evidence_path = artifact_dir / EVIDENCE_FILE_NAME
    results = _load_reusable_results(evidence_path, artifact_dir, nodes, identity_inputs) if reuse_enabled else {}
    pending = set(names) - results.keys()
    heavy_slots = threading.Semaphore(max_heavy if mode == "parallel" else 1)
    while pending:
        ready = [
            name
            for name in names
            if name in pending and all(dependency in results for dependency in node_by_name[name].dependencies)
        ]
        if not ready:
            for name in names:
                if name in pending:
                    results[name] = {
                        "name": name,
                        "status": "FAIL",
                        "classification": "metadata",
                        "exit_code": None,
                        "attempts": 0,
                        "started_at": None,
                        "completed_at": utc_now(),
                        "stdout_artifact": None,
                        "stderr_artifact": None,
                        "reason": "dependency cycle or unknown dependency",
                    }
            break
        runnable: list[PrecheckNode] = []
        for name in ready:
            node = node_by_name[name]
            failed_dependencies = [dependency for dependency in node.dependencies if results[dependency]["status"] != "PASS"]
            if failed_dependencies:
                results[name] = {
                    "name": name,
                    "status": "SKIPPED_DEPENDENCY",
                    "classification": "dependency",
                    "exit_code": None,
                    "attempts": 0,
                    "started_at": None,
                    "completed_at": utc_now(),
                    "stdout_artifact": None,
                    "stderr_artifact": None,
                    "reason": f"failed dependencies: {','.join(failed_dependencies)}",
                }
            else:
                runnable.append(node)
            pending.remove(name)
        if mode == "parallel" and len(runnable) > 1:
            executor = ThreadPoolExecutor(max_workers=len(runnable), thread_name_prefix="wc100-precheck")
            try:
                futures = {
                    node.name: executor.submit(
                        _run_node,
                        node,
                        artifact_dir,
                        heavy_slots,
                        _node_identity(node, identity_inputs),
                    )
                    for node in runnable
                }
                for name in ready:
                    if name in futures:
                        results[name] = futures[name].result()
            except (KeyboardInterrupt, SystemExit):
                with _BlockedInterrupts():
                    _terminate_active_processes()
                    _cleanup_compose_projects(runnable)
                    executor.shutdown(wait=True, cancel_futures=True)
                raise
            else:
                executor.shutdown(wait=True)
        else:
            for node in runnable:
                results[node.name] = _run_node(
                    node,
                    artifact_dir,
                    heavy_slots,
                    _node_identity(node, identity_inputs),
                )

    ordered_results = [results[name] for name in names]
    failures = [result for result in ordered_results if result["status"] != "PASS"]
    manifest = {
        "schema": EVIDENCE_SCHEMA,
        "passed": not failures,
        "base_sha": base_sha,
        "commit_sha": head_sha,
        "changed_file_digest": changed_file_digest,
        "graph_version": graph_version,
        "configuration_digest": configuration_digest,
        "runner_digest": runner_digest,
        "mode": mode,
        "max_heavy": max_heavy,
        "reuse_enabled": reuse_enabled,
        "executed_count": sum(result.get("reuse", {}).get("reused") is not True for result in ordered_results),
        "reused_count": sum(result.get("reuse", {}).get("reused") is True for result in ordered_results),
        "fallback_reasons": fallback_reasons,
        "first_causal_failure": failures[0]["name"] if failures else None,
        "nodes": ordered_results,
    }
    _write_manifest_atomically(evidence_path, manifest)
    return manifest
