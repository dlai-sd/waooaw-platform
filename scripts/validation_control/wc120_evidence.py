#!/usr/bin/env python3
"""Create WC-120 selector evidence and the immutable candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    return subprocess.check_output(  # noqa: S603 - arguments come only from internal callers
        ["/usr/bin/git", "-C", str(ROOT), *arguments], text=True
    ).strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_selector(arguments: argparse.Namespace) -> None:
    evidence = ROOT / "test-results" / "wc120" / arguments.ce_fit_id
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = Path(arguments.log).resolve()
    result = {
        "ce_fit_id": arguments.ce_fit_id,
        "command": arguments.command,
        "node": arguments.node,
        "started_at_utc": arguments.started_at,
        "completed_at_utc": _utc_now(),
        "exit_status": arguments.exit_status,
        "pass_fail_skip_counts": {
            "passed": 1 if arguments.exit_status == 0 else 0,
            "failed": 0 if arguments.exit_status == 0 else 1,
            "skipped": 0,
        },
        "candidate_manifest_digest": None,
        "artifact_digests": {
            str(log_path.relative_to(ROOT)): _sha256(log_path),
        },
    }
    (evidence / "selector-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (evidence / "runner-image-digest.txt").write_text(arguments.runner_image_digest + "\n", encoding="utf-8")


def _record_summary(arguments: argparse.Namespace) -> None:
    log_path = Path(arguments.log).resolve()
    output_path = Path(arguments.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "name": arguments.name,
        "command": arguments.command,
        "started_at_utc": arguments.started_at,
        "completed_at_utc": _utc_now(),
        "exit_status": arguments.exit_status,
        "log": str(log_path.relative_to(ROOT)),
        "log_digest": _sha256(log_path),
        "source_commit": _git("rev-parse", "HEAD"),
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _digest_or_absent(path: Path) -> str:
    return _sha256(path) if path.is_file() else "ABSENT"


def _load_result(path_value: str) -> Any:
    path = Path(path_value).resolve()
    return {
        "path": str(path.relative_to(ROOT)),
        "digest": _sha256(path),
        "result": json.loads(path.read_text(encoding="utf-8")),
    }


def _candidate(arguments: argparse.Namespace) -> None:
    source_commit = _git("rev-parse", "HEAD")
    source_changes = [line for line in _git("status", "--porcelain").splitlines() if "test-results/wc120/" not in line]
    if len(source_commit) != 40 or source_changes:
        raise SystemExit("WC-120 candidate must be an exact clean 40-character commit.")

    result_root = ROOT / "test-results" / "wc120"
    selectors: dict[str, Any] = {}
    for number in range(1, 17):
        ce_fit_id = f"CE-FIT-{number:02d}"
        result_path = result_root / ce_fit_id / "selector-result.json"
        if not result_path.is_file():
            raise SystemExit(f"Missing selector evidence: {result_path}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        selectors[ce_fit_id] = {
            "result": str(result_path.relative_to(ROOT)),
            "exit_status": result["exit_status"],
            "passed": result["pass_fail_skip_counts"]["passed"],
            "failed": result["pass_fail_skip_counts"]["failed"],
            "skipped": result["pass_fail_skip_counts"]["skipped"],
        }

    image_digests = json.loads(Path(arguments.image_digests).read_text(encoding="utf-8"))
    manifest = {
        "schema": "waooaw.wc120-candidate-manifest/v1",
        "source_commit": source_commit,
        "work_contract_digest": _digest_or_absent(ROOT / "work-contracts/WC-120-conversation-engine-whatsapp-implementation.md"),
        "requirements_ledger_digest": _digest_or_absent(ROOT / "work-contracts/WC-120-requirements.yaml"),
        "solution_package_digest": _digest_or_absent(
            ROOT / "architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md"
        ),
        "api_contract_digest": _digest_or_absent(
            ROOT / "architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml"
        ),
        "product_matrix_digest": _digest_or_absent(ROOT / "work-contracts/WC-120-product-acceptance-matrix.yaml"),
        "fitness_matrix_digest": _digest_or_absent(ROOT / "work-contracts/WC-120-fitness-evidence-matrix.yaml"),
        "image_digest": image_digests["business_platform"],
        "test_runner_image_digests": image_digests["test_runners"],
        "schema_version_and_migration_watermark": {
            "schema": "36-wc120-conversation-whatsapp.sql",
            "schema_digest": _digest_or_absent(ROOT / "infrastructure/postgres/init/36-wc120-conversation-whatsapp.sql"),
            "backfill": "wc120-conversation-environment-v1",
        },
        "configuration_and_feature_flag_versions": {
            "configuration": "wc120-candidate-1",
            "feature_flags": "wc120-default-off-1",
            "environments": ["demo", "uat", "production"],
        },
        "targeted_test_results": _load_result(arguments.targeted_results),
        "recovery_test_results": _load_result(arguments.recovery_results),
        "ce_fitness_results": selectors,
        "final_docker_qualification": _load_result(arguments.final_qualification),
        "release_qualification": {
            "state": "OFF_SKIPPED",
            "authority": "Founder authorization in the current WC-120 implementation session",
        },
        "created_at_utc": _utc_now(),
    }
    manifest_path = result_root / "candidate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_digest = _sha256(manifest_path)
    for ce_fit_id in selectors:
        evidence = result_root / ce_fit_id
        result_path = evidence / "selector-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["candidate_manifest_digest"] = manifest_digest
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (evidence / "candidate-manifest-digest.txt").write_text(manifest_digest + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="operation", required=True)
    selector = subparsers.add_parser("selector")
    selector.add_argument("--ce-fit-id", required=True)
    selector.add_argument("--command", required=True)
    selector.add_argument("--node", required=True)
    selector.add_argument("--started-at", required=True)
    selector.add_argument("--exit-status", required=True, type=int)
    selector.add_argument("--runner-image-digest", required=True)
    selector.add_argument("--log", required=True)
    selector.set_defaults(handler=_record_selector)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--name", required=True)
    summary.add_argument("--command", required=True)
    summary.add_argument("--started-at", required=True)
    summary.add_argument("--exit-status", required=True, type=int)
    summary.add_argument("--log", required=True)
    summary.add_argument("--output", required=True)
    summary.set_defaults(handler=_record_summary)

    candidate = subparsers.add_parser("candidate")
    candidate.add_argument("--image-digests", required=True)
    candidate.add_argument("--targeted-results", required=True)
    candidate.add_argument("--recovery-results", required=True)
    candidate.add_argument("--final-qualification", required=True)
    candidate.set_defaults(handler=_candidate)
    arguments = parser.parse_args()
    arguments.handler(arguments)


if __name__ == "__main__":
    main()
