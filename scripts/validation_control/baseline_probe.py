"""Capture the WC-102 validation control-plane baseline."""

# Implements: architecture/reference/docker-only-validation-strategy.md §3
# Constitutional basis: C-059, C-080, C-086

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


HOST_TEST_PATTERN = re.compile(r"^\s*(pytest|dotnet test|pnpm (?:test|lint)|npx |python scripts/)", re.MULTILINE)


def collect_baseline(repository: Path) -> dict[str, Any]:
    compose = (repository / "docker-compose.yml").read_text()
    ci = (repository / ".github/workflows/ci.yaml").read_text()
    integration = (repository / ".github/workflows/integration-tests.yaml").read_text()
    dotnet_runner = (repository / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet").read_text()

    workflow_text = "\n".join(
        path.read_text() for path in sorted((repository / ".github/workflows").glob("*.y*ml"))
    )
    host_invocations = HOST_TEST_PATTERN.findall(integration)

    return {
        "schema_version": 1,
        "base_head": "latest-main-before-wc102",
        "defects": {
            "duplicate_runner_builds": workflow_text.count("docker compose --profile") > 1
            and workflow_text.count(" build test-runner") > 1,
            "business_platform_uses_deprecated_runner": "profile: test\n            runner: test-runner" in ci,
            "dotnet_nuget_path_mismatch": "target=/root/.nuget/packages" in dotnet_runner
            and "NUGET_PACKAGES: /tmp/nuget" in compose,
            "typescript_source_mount_missing": "test-runner-ts:\n" in compose
            and "test-runner-ts:\n    build:" in compose
            and "test-runner-ts:\n    build:\n" in compose
            and "dockerfile: architecture/reference/dockerfiles/Dockerfile.test-runner-ts\n    profiles:" in compose,
            "integration_host_test_invocations": len(host_invocations),
            "advisory_contract_checks": "continue-on-error: true  # Advisory until service is deployed in CI" in integration,
            "single_machine_catalog_missing": not (repository / "validation/engineering-validation.yaml").exists(),
            "wc102_catalog_contract_missing": not (repository / "validation/catalog.schema.json").exists(),
            "common_result_schema_missing": not (repository / "validation/result.schema.json").exists(),
        },
        "runner_build_invocations": workflow_text.count(" build test-runner"),
        "root_runner_overrides": workflow_text.count("--user root"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = collect_baseline(args.repository.resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())