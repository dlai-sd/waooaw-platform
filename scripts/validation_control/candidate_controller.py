"""Freeze, bind, and qualify one immutable WC-109 candidate."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path
import stat
from typing import Any

from validation_control.identity import candidate_manifest


SHA256_PREFIX = "sha256:"


def _sha256(content: bytes) -> str:
    return SHA256_PREFIX + hashlib.sha256(content).hexdigest()


def _require_digest(name: str, value: object) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith(SHA256_PREFIX):
        raise ValueError(f"{name} must be an immutable sha256 digest")
    if any(character not in "0123456789abcdef" for character in value.removeprefix(SHA256_PREFIX)):
        raise ValueError(f"{name} must be an immutable sha256 digest")
    return value


def dockerignore_patterns(repository: Path) -> list[str]:
    path = repository / ".dockerignore"
    if not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _pattern_matches(relative: str, pattern: str) -> bool:
    normalized = pattern.lstrip("/")
    directory_pattern = normalized.endswith("/")
    normalized = normalized.rstrip("/")
    parts = relative.split("/")
    candidates = [relative, Path(relative).name, *("/".join(parts[:index]) for index in range(1, len(parts)))]
    if directory_pattern:
        candidates.extend("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    return any(fnmatch.fnmatchcase(candidate, normalized) for candidate in candidates)


def docker_context_included(relative: str, patterns: list[str]) -> bool:
    included = True
    for pattern in patterns:
        negate = pattern.startswith("!")
        candidate = pattern[1:] if negate else pattern
        if _pattern_matches(relative, candidate):
            included = negate
    return included


def effective_context_manifest(repository: Path) -> list[dict[str, object]]:
    patterns = dockerignore_patterns(repository)
    entries: list[dict[str, object]] = []
    for root, directories, files in os.walk(repository, topdown=True, followlinks=False):
        root_path = Path(root)
        retained_directories: list[str] = []
        for directory in sorted(directories):
            path = root_path / directory
            relative = path.relative_to(repository).as_posix()
            if path.is_symlink():
                if docker_context_included(relative, patterns):
                    entries.append(
                        {
                            "path": relative,
                            "digest": _sha256(os.readlink(path).encode()),
                            "mode": stat.S_IMODE(path.lstat().st_mode),
                            "type": "symlink",
                        }
                    )
            elif docker_context_included(relative + "/", patterns):
                retained_directories.append(directory)
        directories[:] = retained_directories
        for filename in sorted(files):
            path = root_path / filename
            relative = path.relative_to(repository).as_posix()
            if not docker_context_included(relative, patterns):
                continue
            status = path.lstat()
            entry_type = "symlink" if path.is_symlink() else "file"
            content = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            entries.append(
                {
                    "path": relative,
                    "digest": _sha256(content),
                    "mode": stat.S_IMODE(status.st_mode),
                    "type": entry_type,
                }
            )
    return sorted(entries, key=lambda entry: str(entry["path"]))


def freeze_candidate(
    repository: Path,
    *,
    source_sha: str,
    observed_sha: str,
    clean: bool,
    generated_artifacts: dict[str, str],
    dockerfile_frontend_digest: str,
    build_arguments: dict[str, str],
    base_image_digests: dict[str, str],
    architecture: str,
    platform: str,
) -> dict[str, Any]:
    if len(source_sha) != 40 or any(character not in "0123456789abcdef" for character in source_sha):
        raise ValueError("candidate source must be a full hexadecimal commit")
    if observed_sha != source_sha:
        raise ValueError("CANDIDATE_HEAD_MOVED")
    if not clean:
        raise ValueError("CANDIDATE_WORKTREE_DIRTY")
    _require_digest("dockerfile frontend", dockerfile_frontend_digest)
    for name, digest in generated_artifacts.items():
        _require_digest(f"generated artifact {name}", digest)
    for name, digest in base_image_digests.items():
        _require_digest(f"base image {name}", digest)
    manifest = candidate_manifest(
        {
            "build_context_manifest": effective_context_manifest(repository),
            "generated_artifacts": generated_artifacts,
            "dockerfile_frontend_digest": dockerfile_frontend_digest,
            "build_arguments": build_arguments,
            "base_image_digests": base_image_digests,
            "architecture": architecture,
            "platform": platform,
            "candidate_schema_version": "v1",
        }
    )
    return {
        "schema": "waooaw.candidate-freeze/v1",
        "source_sha": source_sha,
        "exact_head": True,
        "clean_state": True,
        "candidate_manifest": manifest,
    }


def bind_candidate_supply(
    freeze: dict[str, Any],
    *,
    required_images: set[str],
    images: dict[str, str],
    sboms: dict[str, dict[str, str]],
    provenances: dict[str, dict[str, str]],
    required_gates: list[str],
) -> dict[str, Any]:
    manifest = freeze.get("candidate_manifest")
    if freeze.get("schema") != "waooaw.candidate-freeze/v1" or not isinstance(manifest, dict):
        raise ValueError("candidate freeze is not trusted")
    candidate_digest = _require_digest("candidate identity", manifest.get("digest"))
    if set(images) != required_images or set(sboms) != required_images or set(provenances) != required_images:
        raise ValueError("candidate supply does not cover the exact required image inventory")
    if not required_gates or len(required_gates) != len(set(required_gates)):
        raise ValueError("candidate qualification inventory is invalid")
    for name in sorted(required_images):
        image_digest = _require_digest(f"image {name}", images[name])
        sbom = sboms[name]
        provenance = provenances[name]
        if (
            sbom.get("format") != "spdx-json-2.3"
            or sbom.get("subject_digest") != image_digest
            or not _require_digest(f"SBOM {name}", sbom.get("artifact_digest"))
        ):
            raise ValueError(f"candidate SBOM is not bound: {name}")
        if (
            provenance.get("format") != "slsa-provenance-v1"
            or provenance.get("subject_digest") != image_digest
            or provenance.get("candidate_identity") != candidate_digest
            or not provenance.get("builder_identity")
            or not _require_digest(f"provenance {name}", provenance.get("artifact_digest"))
        ):
            raise ValueError(f"candidate provenance is not bound: {name}")
    return {
        "schema": "waooaw.candidate-supply-binding/v1",
        "source_sha": freeze["source_sha"],
        "candidate_identity": candidate_digest,
        "images": images,
        "sboms": sboms,
        "provenances": provenances,
        "required_gates": required_gates,
    }


def qualify_candidate(
    binding: dict[str, Any],
    *,
    observed_candidate_identity: str,
    gate_evidence: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if binding.get("schema") != "waooaw.candidate-supply-binding/v1":
        raise ValueError("candidate supply binding is not trusted")
    candidate_identity = binding.get("candidate_identity")
    if observed_candidate_identity != candidate_identity:
        raise ValueError("QUALIFICATION_CANDIDATE_CHANGED")
    required_gates = binding.get("required_gates")
    if not isinstance(required_gates, list) or set(gate_evidence) != set(required_gates):
        raise ValueError("QUALIFICATION_INVENTORY_INCOMPLETE")
    failures: list[str] = []
    for gate_id in required_gates:
        evidence = gate_evidence[gate_id]
        if evidence.get("candidate_identity") != candidate_identity or evidence.get("result") != "PASS":
            failures.append(gate_id)
    return {
        "schema": "waooaw.candidate-qualification/v1",
        "source_sha": binding["source_sha"],
        "candidate_identity": candidate_identity,
        "required_gates": required_gates,
        "executed_gates": list(required_gates),
        "result": "PASS" if not failures else "FAIL",
        "failed_gates": failures,
    }
