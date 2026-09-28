import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPENDENCY_GATE = ROOT / "scripts/validation_control/run_dependency_scan_gate.sh"


def write_fake_pip_audit(tmp_path: Path, body: str) -> Path:
    executable = tmp_path / "pip-audit"
    executable.write_text(f"#!/bin/sh\nset -eu\n{body}\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


def run_python_dependency_gate(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "PIP_AUDIT_RETRY_DELAY_SECONDS": "0",
        "PIP_AUDIT_TEST_COUNT": str(tmp_path / "count"),
    }
    return subprocess.run(
        ["sh", str(DEPENDENCY_GATE), "python"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_python_dependency_scan_retries_transient_transport_failure(tmp_path: Path) -> None:
    write_fake_pip_audit(
        tmp_path,
        """
count=$(cat "$PIP_AUDIT_TEST_COUNT" 2>/dev/null || printf 0)
count=$((count + 1))
printf '%s\n' "$count" > "$PIP_AUDIT_TEST_COUNT"
if [ "$count" -eq 1 ]; then
    echo "requests.exceptions.ConnectionError: Connection reset by peer" >&2
    exit 1
fi
echo "No known vulnerabilities found"
""".strip(),
    )

    completed = run_python_dependency_gate(tmp_path)

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "count").read_text(encoding="utf-8").strip() == "4"
    assert "transient transport failure; retrying" in completed.stderr


def test_python_dependency_scan_does_not_retry_vulnerability_result(tmp_path: Path) -> None:
    write_fake_pip_audit(
        tmp_path,
        """
count=$(cat "$PIP_AUDIT_TEST_COUNT" 2>/dev/null || printf 0)
count=$((count + 1))
printf '%s\n' "$count" > "$PIP_AUDIT_TEST_COUNT"
echo "Found 1 known vulnerability in 1 package"
exit 1
""".strip(),
    )

    completed = run_python_dependency_gate(tmp_path)

    assert completed.returncode == 1
    assert (tmp_path / "count").read_text(encoding="utf-8").strip() == "1"
    assert "retrying" not in completed.stderr
