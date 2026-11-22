"""Supervise the WBE public listener and, when ADR-046 cloud delivery is on, the private mTLS listener."""

# Implements: ADR-046 sections 3.1, 5.1, and 12 (D5); workload-identity-cloud-issuance-contract.md section 3
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

logger = logging.getLogger("entrypoint")

PUBLIC_PORT = "8140"


def private_listener_enabled(environ: Mapping[str, str]) -> bool:
    return environ.get("WAOOAW_WID_SOURCE", "").strip() == "keyvault" or environ.get("WBE_PRIVATE_LISTENER", "").strip() == "1"


def child_commands(environ: Mapping[str, str]) -> list[list[str]]:
    commands = [[sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", PUBLIC_PORT]]  # noqa: S104
    if private_listener_enabled(environ):
        commands.append([sys.executable, "private_server.py"])
    return commands


class Supervisor:
    def __init__(
        self,
        commands: Sequence[Sequence[str]],
        spawn: Callable[[Sequence[str]], Any] = subprocess.Popen,
        sleep: Callable[[float], None] = time.sleep,
        grace_seconds: float = 10.0,
        poll_seconds: float = 0.5,
    ) -> None:
        self._commands = commands
        self._spawn = spawn
        self._sleep = sleep
        self._grace = grace_seconds
        self._poll = poll_seconds
        self._children: list[Any] = []
        self._stop_requested = False

    def forward(self, signum: int, _frame: object = None) -> None:
        self._stop_requested = True
        for child in self._children:
            if child.poll() is None:
                child.send_signal(signum)

    def _stop_remaining(self) -> None:
        for child in self._children:
            if child.poll() is None:
                child.terminate()
        waited = 0.0
        while waited < self._grace and any(child.poll() is None for child in self._children):
            self._sleep(self._poll)
            waited += self._poll
        for child in self._children:
            if child.poll() is None:
                child.kill()

    def run(self) -> int:
        self._children = [self._spawn(command) for command in self._commands]
        while all(child.poll() is None for child in self._children):
            self._sleep(self._poll)
        codes = [child.poll() for child in self._children]
        logger.warning("entrypoint child_exit codes=%s stop_requested=%s", codes, self._stop_requested)
        self._stop_remaining()
        if self._stop_requested:
            return 0
        return next((code for code in codes if code), 1)


def main() -> int:
    supervisor = Supervisor(child_commands(os.environ))
    signal.signal(signal.SIGTERM, supervisor.forward)
    signal.signal(signal.SIGINT, supervisor.forward)
    return supervisor.run()


if __name__ == "__main__":
    sys.exit(main())
