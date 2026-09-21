"""Build and validate canonical WC-104 validation-runner supply metadata."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1-4.4
# Constitutional basis: C-023, C-059, C-071, C-080, C-086

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from validation_control.identity import resolve_runner_manifest, runner_identity


def load_supply_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema") != "waooaw.runner-supply/v1" or not isinstance(config.get("runners"), dict):
        raise ValueError("invalid runner supply configuration")
    return config


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def runner_specification(config: dict[str, Any], repository: Path, runner_id: str) -> dict[str, Any]:
    runner = config["runners"].get(runner_id)
    if not isinstance(runner, dict):
        raise ValueError(f"unknown runner: {runner_id}")
    context_inputs = runner.get("context_inputs")
    if not isinstance(context_inputs, list) or not context_inputs:
        raise ValueError(f"runner {runner_id} has no context inputs")
    context_manifest: dict[str, str] = {}
    for relative in context_inputs:
        path = repository / relative
        if not path.is_file():
            raise ValueError(f"runner {runner_id} required input is missing: {relative}")
        context_manifest[relative] = file_digest(path)
    dockerfile = runner.get("dockerfile")
    if dockerfile not in context_manifest:
        raise ValueError(f"runner {runner_id} Dockerfile is absent from its context manifest")
    inputs = {
        "dockerfile_digest": context_manifest[dockerfile],
        "base_image_digest": runner["base_image_digest"],
        "system_packages": runner["system_packages"],
        "dependency_manifests": {path: digest for path, digest in context_manifest.items() if path != dockerfile},
        "build_arguments": runner.get("build_arguments", {}),
        "platform": runner["platform"],
        "context_manifest": context_manifest,
        "runner_schema_version": config["schema"],
    }
    return {
        "runner_id": runner_id,
        "dockerfile": dockerfile,
        "identity": runner_identity(inputs),
        "identity_inputs": inputs,
    }


def create_context(repository: Path, destination: Path, specification: dict[str, Any]) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    context_manifest = specification["identity_inputs"]["context_manifest"]
    for relative, expected_digest in context_manifest.items():
        source = repository / relative
        if file_digest(source) != expected_digest:
            raise ValueError(f"runner context input changed during creation: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def build_supply_manifest(
    specification: dict[str, Any],
    *,
    image_repository: str,
    oci_digest: str,
    provenance_reference: str,
    producer_run: str,
    cache_outcome: str,
    build_count: int,
    supply_duration_ms: int,
) -> dict[str, Any]:
    if build_count not in {0, 1}:
        raise ValueError("runner supply build_count must be zero or one")
    cache_hits = {"registry-hit", "trusted-identity-hit", "candidate-identity-hit"}
    if cache_outcome not in {*cache_hits, "built"} or (cache_outcome in cache_hits) != (build_count == 0):
        raise ValueError("runner supply cache outcome does not match build count")
    if supply_duration_ms < 0:
        raise ValueError("runner supply duration must be non-negative")
    record = {
        "runner_identity": specification["identity"],
        "oci_digest": oci_digest,
        "platform": specification["identity_inputs"]["platform"],
        "provenance": {"reference": provenance_reference, "verified": True},
    }
    resolved = resolve_runner_manifest(
        specification["identity"],
        specification["identity_inputs"]["platform"],
        record,
        lambda provenance: bool(provenance.get("verified") and provenance.get("reference")),
    )
    if resolved is None:
        raise ValueError("runner supply manifest is not immutable and provenance-bound")
    return {
        "schema": "waooaw.runner-manifest/v1",
        "runner_id": specification["runner_id"],
        "runner_identity": specification["identity"],
        "image_repository": image_repository,
        "oci_digest": oci_digest,
        "platform": resolved["platform"],
        "provenance_reference": provenance_reference,
        "producer_run": producer_run,
        "cache_outcome": cache_outcome,
        "build_count": build_count,
        "supply_duration_ms": supply_duration_ms,
    }


def validate_supply_manifest(manifest: dict[str, Any], specification: dict[str, Any]) -> str:
    if manifest.get("schema") != "waooaw.runner-manifest/v1":
        raise ValueError("runner manifest schema is not trusted")
    if manifest.get("runner_id") != specification["runner_id"]:
        raise ValueError("runner manifest names the wrong runner")
    record = {
        "runner_identity": manifest.get("runner_identity"),
        "oci_digest": manifest.get("oci_digest"),
        "platform": manifest.get("platform"),
        "provenance": {
            "reference": manifest.get("provenance_reference"),
            "verified": bool(manifest.get("provenance_reference")),
        },
    }
    resolved = resolve_runner_manifest(
        specification["identity"],
        specification["identity_inputs"]["platform"],
        record,
        lambda provenance: bool(provenance.get("verified") and provenance.get("reference")),
    )
    if resolved is None:
        raise ValueError("runner manifest identity, platform, digest or provenance mismatch")
    build_count = manifest.get("build_count")
    if build_count not in {0, 1}:
        raise ValueError("runner manifest has an invalid producer count")
    cache_outcome = manifest.get("cache_outcome")
    cache_hits = {"registry-hit", "trusted-identity-hit", "candidate-identity-hit"}
    if cache_outcome not in {*cache_hits, "built"} or (cache_outcome in cache_hits) != (build_count == 0):
        raise ValueError("runner manifest cache outcome does not match producer count")
    supply_duration_ms = manifest.get("supply_duration_ms")
    if not isinstance(supply_duration_ms, int) or isinstance(supply_duration_ms, bool) or supply_duration_ms < 0:
        raise ValueError("runner manifest has an invalid supply duration")
    repository = manifest.get("image_repository")
    if not isinstance(repository, str) or ":" in repository.rsplit("/", maxsplit=1)[-1]:
        raise ValueError("runner manifest repository must not contain a mutable tag")
    return f"{repository}@{resolved['oci_digest']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "context", "manifest", "validate"))
    parser.add_argument("--config", type=Path, default=Path("validation/runner-supply.json"))
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--runner")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image-repository")
    parser.add_argument("--oci-digest")
    parser.add_argument("--provenance-reference")
    parser.add_argument("--producer-run")
    parser.add_argument(
        "--cache-outcome",
        choices=("registry-hit", "trusted-identity-hit", "candidate-identity-hit", "built"),
    )
    parser.add_argument("--build-count", type=int)
    parser.add_argument("--supply-duration-ms", type=int)
    arguments = parser.parse_args()

    config = load_supply_config(arguments.config)
    if arguments.command == "plan":
        result = {"include": [runner_specification(config, arguments.repository, runner_id) for runner_id in config["runners"]]}
    else:
        if not arguments.runner:
            raise ValueError("--runner is required")
        specification = runner_specification(config, arguments.repository, arguments.runner)
        if arguments.command == "context":
            if arguments.output is None:
                raise ValueError("--output is required")
            create_context(arguments.repository, arguments.output, specification)
            result = specification
        elif arguments.command == "manifest":
            required = (
                arguments.image_repository,
                arguments.oci_digest,
                arguments.provenance_reference,
                arguments.producer_run,
                arguments.cache_outcome,
                arguments.build_count,
                arguments.supply_duration_ms,
            )
            if any(value is None for value in required):
                raise ValueError("manifest arguments are required")
            result = build_supply_manifest(
                specification,
                image_repository=arguments.image_repository,
                oci_digest=arguments.oci_digest,
                provenance_reference=arguments.provenance_reference,
                producer_run=arguments.producer_run,
                cache_outcome=arguments.cache_outcome,
                build_count=arguments.build_count,
                supply_duration_ms=arguments.supply_duration_ms,
            )
        else:
            if arguments.output is None:
                raise ValueError("--output must name the manifest to validate")
            manifest = json.loads(arguments.output.read_text(encoding="utf-8"))
            result = {"image": validate_supply_manifest(manifest, specification)}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
