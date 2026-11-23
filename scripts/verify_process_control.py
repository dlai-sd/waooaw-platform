#!/usr/bin/env python3
# Implements: validation/process-control.yaml (process-control currency)
# Constitutional basis: C-023, C-059, C-065, C-071, C-080
"""Verify or refresh the process-control manifest so inherited controls never go stale.

The manifest pins a SHA-256 for every source named by a required control. `--check` fails when a
pinned source changed without a refresh, when the version is not the revision plus the content
hash, or (with `--base`) when sources changed against the base branch without a higher revision.
`--refresh` recomputes digests and increments the revision only when a digest changed.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path("validation/process-control.yaml")
SCHEMA = "waooaw.process-control/v2"
HASH_LENGTH = 12


def control_sources(manifest: dict[str, Any]) -> list[str]:
    controls = manifest.get("required_controls")
    if not isinstance(controls, dict) or not controls:
        raise ValueError("required_controls must be a non-empty mapping")
    sources: set[str] = set()
    for name, control in controls.items():
        listed = control.get("sources") if isinstance(control, dict) else None
        if not isinstance(listed, list) or not listed or not all(isinstance(item, str) for item in listed):
            raise ValueError(f"required control {name} must list its sources")
        sources.update(listed)
    return sorted(sources)


def file_digest(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def content_hash(source_digests: dict[str, str]) -> str:
    joined = "\n".join(f"{path}={source_digests[path]}" for path in sorted(source_digests))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def expected_version(revision: int, source_digests: dict[str, str]) -> str:
    return f"r{revision:03d}-{content_hash(source_digests)[:HASH_LENGTH]}"


def load_manifest(root: Path) -> dict[str, Any]:
    loaded = yaml.safe_load((root / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("process-control manifest root must be a mapping")
    return loaded


def violations(root: Path, manifest: dict[str, Any]) -> list[str]:
    found: list[str] = []
    if manifest.get("schema") != SCHEMA:
        found.append(f"schema must be {SCHEMA}")
    revision = manifest.get("revision")
    if not isinstance(revision, int) or revision < 1:
        found.append("revision must be a positive integer")
        revision = 0
    try:
        sources = control_sources(manifest)
    except ValueError as error:
        return [*found, str(error)]
    recorded = manifest.get("source_digests")
    if not isinstance(recorded, dict):
        return [*found, "source_digests must be a mapping"]
    if sorted(recorded) != sources:
        found.append("source_digests must pin exactly the sources named by required_controls")
    for path in sources:
        if not (root / path).is_file():
            found.append(f"declared process source is missing: {path}")
        elif recorded.get(path) != file_digest(root, path):
            found.append(f"stale digest for {path}; run scripts/run_platform_state_refresh.sh")
    if not found and manifest.get("version") != expected_version(revision, recorded):
        found.append("version must equal revision and content hash; run scripts/run_platform_state_refresh.sh")
    return found


def base_manifest(root: Path, base: str) -> dict[str, Any]:
    result = subprocess.run(  # noqa: S603
        ["git", "-c", f"safe.directory={root.resolve()}", "show", f"{base}:{MANIFEST.as_posix()}"],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"cannot read the process-control manifest at {base}: {result.stderr.strip()}")
    loaded = yaml.safe_load(result.stdout)
    return loaded if isinstance(loaded, dict) else {}


def revision_violations(root: Path, manifest: dict[str, Any], base: str) -> list[str]:
    previous = base_manifest(root, base)
    previous_revision = previous.get("revision") if isinstance(previous.get("revision"), int) else 0
    previous_digests = previous.get("source_digests") if isinstance(previous.get("source_digests"), dict) else {}
    current = manifest.get("source_digests", {})
    if current == previous_digests:
        return []
    if manifest.get("revision", 0) <= previous_revision:
        return [
            f"process sources changed against {base} but revision {manifest.get('revision')} does not exceed "
            f"{previous_revision}; run scripts/run_platform_state_refresh.sh"
        ]
    return []


def refresh(root: Path) -> bool:
    manifest = load_manifest(root)
    sources = control_sources(manifest)
    digests = {path: file_digest(root, path) for path in sources}
    revision = manifest.get("revision") if isinstance(manifest.get("revision"), int) else 0
    if manifest.get("source_digests") != digests or manifest.get("schema") != SCHEMA:
        revision += 1
    revision = max(revision, 1)
    updated = {**manifest, "schema": SCHEMA, "revision": revision, "source_digests": digests}
    updated["version"] = expected_version(revision, digests)
    ordered = {
        key: updated[key]
        for key in (
            "schema",
            "revision",
            "version",
            "authoritative_ref",
            "bootstrap_first",
            "source_digests",
            "required_controls",
        )
        if key in updated
    }
    ordered.update({key: value for key, value in updated.items() if key not in ordered})
    rendered = yaml.safe_dump(ordered, sort_keys=False, width=120)
    path = root / MANIFEST
    if path.read_text(encoding="utf-8") == rendered:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when the manifest is stale")
    mode.add_argument("--refresh", action="store_true", help="recompute digests, revision and version")
    parser.add_argument("--base", help="also require a higher revision when sources changed against this ref")
    args = parser.parse_args()
    if args.refresh:
        print(f"{'updated' if refresh(REPO_ROOT) else 'unchanged'} {MANIFEST}")
        return 0
    manifest = load_manifest(REPO_ROOT)
    found = violations(REPO_ROOT, manifest)
    if args.base and not found:
        found = revision_violations(REPO_ROOT, manifest, args.base)
    for item in found:
        print(f"process-control: {item}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
