#!/usr/bin/env python3
"""Create WC-120 selector evidence and the immutable candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
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


def _source_commit(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise SystemExit("WC-120 candidate must be an exact 40-character commit.")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_selector(arguments: argparse.Namespace) -> None:
    evidence = ROOT / "test-results" / "wc120" / arguments.ce_fit_id
    if arguments.supporting:
        evidence /= "browser"
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = Path(arguments.log).resolve()
    report_path = Path(arguments.report).resolve()
    counts = report_counts(report_path)
    if arguments.exit_status == 0 and (counts["passed"] == 0 or counts["failed"] or counts["skipped"]):
        raise SystemExit("A qualifying WC-120 selector must execute tests without failures or skips.")
    result = {
        "ce_fit_id": arguments.ce_fit_id,
        "command": arguments.command,
        "node": arguments.node,
        "started_at_utc": arguments.started_at,
        "completed_at_utc": _utc_now(),
        "source_commit": _source_commit(arguments.source_commit),
        "exit_status": arguments.exit_status,
        "pass_fail_skip_counts": counts,
        "candidate_manifest_digest": None,
        "test_report": str(report_path.relative_to(ROOT)),
        "artifact_digests": {
            str(log_path.relative_to(ROOT)): _sha256(log_path),
            str(report_path.relative_to(ROOT)): _sha256(report_path),
        },
    }
    (evidence / "selector-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (evidence / "runner-image-digest.txt").write_text(arguments.runner_image_digest + "\n", encoding="utf-8")


class _ReportTreeBuilder(ET.TreeBuilder):
    def doctype(self, name: str, public_id: str | None, system_id: str | None) -> None:
        raise ValueError("DTD and entity declarations are prohibited in WC-120 reports.")


def report_counts(path: Path) -> dict[str, int]:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("WC-120 test report exceeds the evidence size bound.")
    parser = ET.XMLParser(target=_ReportTreeBuilder())  # noqa: S314 -- target rejects DTDs before entity declarations
    parser.feed(path.read_bytes())
    root = parser.close()
    counters = root.find(".//{http://microsoft.com/schemas/VisualStudio/TeamTest/2010}Counters")
    if counters is not None:
        total, passed, failed = (int(counters.attrib[key]) for key in ("total", "passed", "failed"))
        counts = {"passed": passed, "failed": failed, "skipped": total - passed - failed}
    else:
        cases = list(root.iter("testcase"))
        failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
        skipped = sum(case.find("skipped") is not None for case in cases)
        counts = {"passed": len(cases) - failed - skipped, "failed": failed, "skipped": skipped}
    if any(value < 0 for value in counts.values()):
        raise ValueError("Invalid WC-120 test report counters.")
    return counts


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
        "source_commit": _source_commit(arguments.source_commit),
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _required_digest(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing WC-120 candidate input: {path}")
    return _sha256(path)


def _load_result(path_value: str, source_commit: str) -> Any:
    path = Path(path_value).resolve()
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("source_commit") != source_commit or result.get("exit_status") != 0:
        raise SystemExit("WC-120 summary must pass on the exact candidate.")
    if result.get("log_digest") != _sha256(ROOT / result["log"]):
        raise SystemExit("WC-120 summary log changed after execution.")
    return {
        "path": str(path.relative_to(ROOT)),
        "digest": _sha256(path),
        "result": result,
    }


def _candidate(arguments: argparse.Namespace) -> None:
    source_commit = _source_commit(arguments.source_commit)
    image_digests = json.loads(Path(arguments.image_digests).read_text(encoding="utf-8"))
    if not all(
        re.fullmatch(r"sha256:[a-f0-9]{64}", digest)
        for digest in [image_digests["business_platform"], *image_digests["test_runners"].values()]
    ):
        raise SystemExit("WC-120 image identities must be exact immutable digests.")

    result_root = ROOT / "test-results" / "wc120"
    selectors: dict[str, Any] = {}
    for number in range(1, 17):
        ce_fit_id = f"CE-FIT-{number:02d}"
        result_path = result_root / ce_fit_id / "selector-result.json"
        if not result_path.is_file():
            raise SystemExit(f"Missing selector evidence: {result_path}")
        runner = "python" if number in (12, 15, 16) else "dotnet"
        result = _qualified_selector(result_path, source_commit, image_digests["test_runners"][runner])
        if result["ce_fit_id"] != ce_fit_id:
            raise SystemExit("WC-120 selector identity differs from its required evidence location.")
        selectors[ce_fit_id] = {
            "result": str(result_path.relative_to(ROOT)),
            "exit_status": result["exit_status"],
            "passed": result["pass_fail_skip_counts"]["passed"],
            "failed": result["pass_fail_skip_counts"]["failed"],
            "skipped": result["pass_fail_skip_counts"]["skipped"],
        }
        if number in (10, 11, 13):
            supporting_path = result_path.parent / "browser/selector-result.json"
            supporting = _qualified_selector(supporting_path, source_commit, image_digests["test_runners"]["browser"])
            selectors[ce_fit_id]["supporting_results"] = [
                {
                    "result": str(supporting_path.relative_to(ROOT)),
                    **supporting["pass_fail_skip_counts"],
                }
            ]

    manifest = {
        "schema": "waooaw.wc120-candidate-manifest/v1",
        "source_commit": source_commit,
        "work_contract_digest": _required_digest(ROOT / "work-contracts/WC-120-conversation-engine-whatsapp-implementation.md"),
        "requirements_ledger_digest": _required_digest(ROOT / "work-contracts/WC-120-requirements.yaml"),
        "solution_package_digest": _required_digest(
            ROOT / "architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md"
        ),
        "api_contract_digest": _required_digest(
            ROOT / "architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml"
        ),
        "product_matrix_digest": _required_digest(ROOT / "work-contracts/WC-120-product-acceptance-matrix.yaml"),
        "fitness_matrix_digest": _required_digest(ROOT / "work-contracts/WC-120-fitness-evidence-matrix.yaml"),
        "image_digest": image_digests["business_platform"],
        "test_runner_image_digests": image_digests["test_runners"],
        "schema_version_and_migration_watermark": {
            "schema": "36-wc120-conversation-whatsapp.sql",
            "schema_digest": _required_digest(ROOT / "infrastructure/postgres/init/36-wc120-conversation-whatsapp.sql"),
            "traffic_reservation_schema_digest": _required_digest(
                ROOT / "infrastructure/postgres/init/61-wc120-whatsapp-traffic-reservations.sql"
            ),
            "backfill": "wc120-conversation-environment-v1",
        },
        "configuration_and_feature_flag_versions": {
            "configuration": "wc120-candidate-1",
            "feature_flags": "wc120-default-off-1",
            "environments": ["demo", "uat", "production"],
        },
        "targeted_test_results": _load_result(arguments.targeted_results, source_commit),
        "recovery_test_results": _load_result(arguments.recovery_results, source_commit),
        "ce_fitness_results": selectors,
        "final_docker_qualification": _load_result(arguments.final_qualification, source_commit),
        "release_qualification": {
            "state": "PENDING_SEPARATE_RELEASE_QUALIFICATION",
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
        for supporting in selectors[ce_fit_id].get("supporting_results", []):
            supporting_path = ROOT / supporting["result"]
            result = json.loads(supporting_path.read_text(encoding="utf-8"))
            result["candidate_manifest_digest"] = manifest_digest
            supporting_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _qualified_selector(path: Path, source_commit: str, runner_digest: str) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    counts = result["pass_fail_skip_counts"]
    if (
        result.get("source_commit") != source_commit
        or result.get("exit_status") != 0
        or counts["passed"] <= 0
        or counts["failed"] != 0
        or counts["skipped"] != 0
    ):
        raise SystemExit("WC-120 selector must pass without skips on the exact candidate.")
    if counts != report_counts(ROOT / result["test_report"]):
        raise SystemExit("WC-120 selector counts differ from the actual test report.")
    if (path.parent / "runner-image-digest.txt").read_text().strip() != runner_digest:
        raise SystemExit("WC-120 selector runner differs from the immutable candidate runner.")
    for artifact, digest in result["artifact_digests"].items():
        if _sha256(ROOT / artifact) != digest:
            raise SystemExit("WC-120 selector artifact changed after execution.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="operation", required=True)
    selector = subparsers.add_parser("selector")
    selector.add_argument("--source-commit", required=True)
    selector.add_argument("--ce-fit-id", required=True)
    selector.add_argument("--command", required=True)
    selector.add_argument("--node", required=True)
    selector.add_argument("--started-at", required=True)
    selector.add_argument("--exit-status", required=True, type=int)
    selector.add_argument("--runner-image-digest", required=True)
    selector.add_argument("--log", required=True)
    selector.add_argument("--report", required=True)
    selector.add_argument("--supporting", action="store_true")
    selector.set_defaults(handler=_record_selector)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--source-commit", required=True)
    summary.add_argument("--name", required=True)
    summary.add_argument("--command", required=True)
    summary.add_argument("--started-at", required=True)
    summary.add_argument("--exit-status", required=True, type=int)
    summary.add_argument("--log", required=True)
    summary.add_argument("--output", required=True)
    summary.set_defaults(handler=_record_summary)

    candidate = subparsers.add_parser("candidate")
    candidate.add_argument("--source-commit", required=True)
    candidate.add_argument("--image-digests", required=True)
    candidate.add_argument("--targeted-results", required=True)
    candidate.add_argument("--recovery-results", required=True)
    candidate.add_argument("--final-qualification", required=True)
    candidate.set_defaults(handler=_candidate)
    arguments = parser.parse_args()
    arguments.handler(arguments)


if __name__ == "__main__":
    main()
