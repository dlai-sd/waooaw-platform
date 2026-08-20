"""Run an Azure REST request with bounded retries for transient responses."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

TRANSIENT_RESPONSE = re.compile(
    r"Too Many Requests|(?:status|status code)[^\n]*(?:429|5\d\d)|"
    r'"code"\s*:\s*"?(?:429|5\d\d)|'
    r"InternalServerError|ServiceUnavailable|BadGateway|GatewayTimeout",
    re.IGNORECASE,
)


def run_azure_rest(
    label: str,
    output_path: Path,
    rest_arguments: list[str],
    *,
    attempts: int = 5,
    base_delay_seconds: float = 5,
) -> int:
    output_path.unlink(missing_ok=True)
    for attempt in range(1, attempts + 1):
        print(f"Azure REST {label}: attempt {attempt}/{attempts}", file=sys.stderr)
        result = subprocess.run(  # noqa: S603
            ["az", "rest", "--only-show-errors", *rest_arguments],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
            temporary_path.write_text(result.stdout, encoding="utf-8")
            temporary_path.replace(output_path)
            return 0

        response = "\n".join(part for part in (result.stderr, result.stdout) if part)
        if attempt == attempts or not TRANSIENT_RESPONSE.search(response):
            print(f"Azure REST {label}: terminal failure\n{response}", file=sys.stderr)
            return result.returncode or 1

        delay = base_delay_seconds * (2 ** (attempt - 1))
        print(
            f"Azure REST {label}: transient response; retrying in {delay:g}s\n{response}",
            file=sys.stderr,
        )
        time.sleep(delay)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--base-delay-seconds", type=float, default=5)
    parser.add_argument("rest_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    rest_arguments = arguments.rest_arguments
    if rest_arguments[:1] == ["--"]:
        rest_arguments = rest_arguments[1:]
    if not rest_arguments or arguments.attempts < 1 or arguments.base_delay_seconds < 0:
        parser.error("Azure REST arguments, positive attempts, and non-negative delay are required")
    return run_azure_rest(
        arguments.label,
        arguments.output,
        rest_arguments,
        attempts=arguments.attempts,
        base_delay_seconds=arguments.base_delay_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())