#!/usr/bin/env python3
"""Create or validate digest-bound GOAL-006 release verification evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def manifest_sha256(manifest: Path) -> str:
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def create_record(release_sha: str, release_run_id: int, manifest: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "release_sha": release_sha,
        "release_run_id": release_run_id,
        "manifest_sha256": manifest_sha256(manifest),
        "attestations_verified": True,
    }


def validate_record(record: dict[str, Any], release_sha: str, release_run_id: int, manifest: Path) -> None:
    if record.get("schema_version") != "1.0":
        raise ValueError("release verification schema_version must be 1.0")
    if record.get("release_sha") != release_sha:
        raise ValueError("release verification SHA does not match")
    if record.get("release_run_id") != release_run_id:
        raise ValueError("release verification run ID does not match")
    if record.get("attestations_verified") is not True:
        raise ValueError("release attestations were not verified")
    if record.get("manifest_sha256") != manifest_sha256(manifest):
        raise ValueError("release manifest digest does not match")


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "validate"))
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--release-run-id", type=int, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    arguments = parser.parse_args()

    if arguments.command == "create":
        record = create_record(arguments.release_sha, arguments.release_run_id, arguments.manifest)
        arguments.record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    record = json.loads(arguments.record.read_text(encoding="utf-8"))
    validate_record(record, arguments.release_sha, arguments.release_run_id, arguments.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())