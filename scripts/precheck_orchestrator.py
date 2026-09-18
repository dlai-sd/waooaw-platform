#!/usr/bin/env python3
"""Run applicable PR prechecks as a bounded, evidence-producing DAG."""

from __future__ import annotations

import os
import signal
import shutil
import subprocess
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


@dataclass(frozen=True)
class PrecheckNode:
    """One deterministic node in the precheck graph."""

    name: str
    command: tuple[str, ...]
    heavy: bool = False
    dependencies: tuple[str, ...] = ()
    transient_retries: int = 0


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


def _run_command(command: tuple[str, ...], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
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
        stdout, stderr = process.communicate()
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


def _run_node(node: PrecheckNode, artifact_dir: Path, heavy_slots: threading.Semaphore) -> dict[str, object]:
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
    started_at = utc_now()
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    attempts = 0
    return_code = 1
    classification = "assertion"
    with heavy_slots if node.heavy else _NullContext():
        while attempts <= node.transient_retries:
            attempts += 1
            completed = _run_command(node.command, environment)
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
    results: dict[str, dict[str, object]] = {}
    pending = set(names)
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
                futures = {node.name: executor.submit(_run_node, node, artifact_dir, heavy_slots) for node in runnable}
                for name in ready:
                    if name in futures:
                        results[name] = futures[name].result()
            except (KeyboardInterrupt, SystemExit):
                _terminate_active_processes()
                _cleanup_compose_projects(runnable)
                executor.shutdown(wait=True, cancel_futures=True)
                raise
            else:
                executor.shutdown(wait=True)
        else:
            for node in runnable:
                results[node.name] = _run_node(node, artifact_dir, heavy_slots)

    ordered_results = [results[name] for name in names]
    failures = [result for result in ordered_results if result["status"] != "PASS"]
    return {
        "schema": "waooaw.pr-prechecks/v2",
        "passed": not failures,
        "base_sha": base_sha,
        "commit_sha": head_sha,
        "changed_file_digest": changed_file_digest,
        "graph_version": graph_version,
        "mode": mode,
        "max_heavy": max_heavy,
        "reuse_enabled": reuse_enabled,
        "fallback_reasons": fallback_reasons,
        "first_causal_failure": failures[0]["name"] if failures else None,
        "nodes": ordered_results,
    }
