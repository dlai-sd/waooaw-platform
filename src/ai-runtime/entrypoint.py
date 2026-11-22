"""Supervise the AIR public listener and, when cloud credentials are enabled, the ADR-046 private listener."""

# Implements: ADR-046 Amendment 1 (private listener inside the Container Apps environment)
# constitutional_basis: C-001, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from types import FrameType
from typing import Protocol

logger = logging.getLogger("entrypoint")

POLL_SECONDS = 0.5
TERMINATE_GRACE_SECONDS = 10.0


class Child(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


Spawn = Callable[[Sequence[str]], Child]


def child_commands(environ: Mapping[str, str]) -> list[list[str]]:
    public = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5004"]  # noqa: S104
    commands = [public]
    source = environ.get("WAOOAW_WID_SOURCE", "directory").strip().lower()
    if source == "keyvault" or environ.get("AIR_PRIVATE_LISTENER") == "1" or environ.get("WAOOAW_WORKLOAD_CREDENTIALS"):
        commands.append([sys.executable, "private_server.py"])
    return commands


def _spawn(command: Sequence[str]) -> Child:
    return subprocess.Popen(command)  # noqa: S603


def _stop(children: Sequence[Child]) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
    for child in children:
        try:
            child.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def supervise(
    environ: Mapping[str, str] | None = None,
    spawn: Spawn = _spawn,
    sleep: Callable[[float], None] = time.sleep,
    terminated: Callable[[], bool] = lambda: False,
) -> int:
    """Run all children; the first exit (or a termination request) stops the rest and yields a non-zero status."""
    env = os.environ if environ is None else environ
    children = [spawn(command) for command in child_commands(env)]
    try:
        while True:
            if terminated():
                logger.info("entrypoint termination_requested")
                return 143
            exited = [status for status in (child.poll() for child in children) if status is not None]
            if exited:
                logger.error("entrypoint child_exited status=%s", exited[0])
                return exited[0] or 1
            sleep(POLL_SECONDS)
    finally:
        _stop(children)


def main() -> None:
    requested: list[bool] = []

    def request_termination(_signum: int, _frame: FrameType | None) -> None:
        requested.append(True)

    signal.signal(signal.SIGTERM, request_termination)
    signal.signal(signal.SIGINT, request_termination)
    sys.exit(supervise(terminated=lambda: bool(requested)))


if __name__ == "__main__":
    main()
