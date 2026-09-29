"""WC-109 candidate context, freeze, supply-chain, and qualification boundaries."""

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from validation_control.candidate_controller import (
    bind_candidate_supply,
    catalog_candidate_inputs,
    effective_context_manifest,
    freeze_candidate,
    inspect_oci_candidate,
    qualify_candidate,
)


DIGESTS = ["sha256:" + character * 64 for character in "12345678"]
HEAD = "a" * 40


def repository_fixture(tmp_path: Path) -> Path:
    (tmp_path / ".dockerignore").write_text("ignored/\n*.log\n!retained.log\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("print('candidate')\n", encoding="utf-8")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored/input.txt").write_text("excluded\n", encoding="utf-8")
    (tmp_path / "discard.log").write_text("excluded\n", encoding="utf-8")
    (tmp_path / "retained.log").write_text("included\n", encoding="utf-8")
    (tmp_path / "link.py").symlink_to("src/app.py")
    return tmp_path


def catalog_fixture(repository: Path) -> dict[str, object]:
    (repository / "Dockerfile").write_text(f"FROM python:3.12-alpine@{DIGESTS[0]}\n", encoding="utf-8")
    return {
        "full_gates": ["test-api"],
        "components": {
            "api": {
                "service_image": "api",
                "service_dockerfile": "Dockerfile",
                "generated_artifacts": ["src/*.py"],
            }
        },
    }


def write_oci_fixture(path: Path, *, tamper_image: bool = False) -> None:
    blobs: dict[str, bytes] = {}

    def descriptor(value: dict[str, object]) -> dict[str, object]:
        content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        blobs[digest] = content
        return {"digest": digest, "size": len(content)}

    image = descriptor({"schemaVersion": 2})
    sbom_statement = descriptor(
        {
            "_type": "https://in-toto.io/Statement/v0.1",
            "predicateType": "https://spdx.dev/Document",
            "subject": [],
            "predicate": {"spdxVersion": "SPDX-2.3"},
        }
    )
    provenance_statement = descriptor(
        {
            "_type": "https://in-toto.io/Statement/v0.1",
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [],
            "predicate": {
                "buildDefinition": {
                    "buildType": "buildkit-v1",
                    "externalParameters": {"request": {"frontend": "dockerfile.v0"}},
                    "internalParameters": {"builderPlatform": "linux/amd64"},
                    "resolvedDependencies": [{"digest": {"sha256": DIGESTS[0].removeprefix("sha256:")}}],
                },
                "runDetails": {"metadata": {"buildkit_metadata": {"vcs": {"revision": HEAD}}}},
            },
        }
    )
    attestation = descriptor(
        {
            "schemaVersion": 2,
            "layers": [
                {
                    **sbom_statement,
                    "annotations": {"in-toto.io/predicate-type": "https://spdx.dev/Document"},
                },
                {
                    **provenance_statement,
                    "annotations": {"in-toto.io/predicate-type": "https://slsa.dev/provenance/v1"},
                },
            ],
        }
    )
    candidate_index = descriptor(
        {
            "schemaVersion": 2,
            "manifests": [
                {**image, "platform": {"architecture": "amd64", "os": "linux"}},
                {
                    **attestation,
                    "annotations": {
                        "vnd.docker.reference.type": "attestation-manifest",
                        "vnd.docker.reference.digest": image["digest"],
                    },
                },
            ],
        }
    )
    root = json.dumps({"schemaVersion": 2, "manifests": [candidate_index]}, separators=(",", ":")).encode()
    if tamper_image:
        blobs[image["digest"]] = b'{"schemaVersion":1}'
    with tarfile.open(path, "w") as archive:
        for name, content in {"index.json": root, **{f"blobs/sha256/{key[7:]}": value for key, value in blobs.items()}}.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))


def freeze(tmp_path: Path) -> dict[str, object]:
    return freeze_candidate(
        repository_fixture(tmp_path),
        source_sha=HEAD,
        observed_sha=HEAD,
        clean=True,
        generated_artifacts={"openapi.json": DIGESTS[0]},
        dockerfile_frontend_digest=DIGESTS[1],
        build_arguments={"VERSION": "1"},
        base_image_digests={"runtime": DIGESTS[2]},
        architecture="amd64",
        platform="linux",
    )


def supply(candidate_freeze: dict[str, object]) -> dict[str, object]:
    images = {"web": DIGESTS[3], "api": DIGESTS[4]}
    sboms = {
        name: {"format": "spdx-json-2.3", "subject_digest": digest, "artifact_digest": DIGESTS[5]}
        for name, digest in images.items()
    }
    provenances = {
        name: {
            "format": "slsa-provenance-v1",
            "subject_digest": digest,
            "candidate_identity": candidate_freeze["candidate_manifest"]["digest"],
            "builder_identity": "waooaw-buildkit-v1",
            "artifact_digest": DIGESTS[6],
        }
        for name, digest in images.items()
    }
    return bind_candidate_supply(
        candidate_freeze,
        required_images=set(images),
        images=images,
        sboms=sboms,
        provenances=provenances,
        required_gates=["test-web", "test-api"],
    )


def test_effective_context_honors_exclusions_negation_modes_and_symlinks(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)

    manifest = effective_context_manifest(repository)
    by_path = {entry["path"]: entry for entry in manifest}

    assert "src/app.py" in by_path
    assert "retained.log" in by_path
    assert "discard.log" not in by_path
    assert "ignored/input.txt" not in by_path
    assert by_path["link.py"]["type"] == "symlink"
    assert by_path["link.py"]["digest"] != by_path["src/app.py"]["digest"]


def test_catalog_derives_complete_pinned_build_and_generated_artifact_inventory(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)

    inputs = catalog_candidate_inputs(repository, catalog_fixture(repository))

    assert inputs["required_images"] == {"api"}
    assert inputs["required_gates"] == ["test-api"]
    assert set(inputs["generated_artifacts"]) == {"src/app.py"}
    assert set(inputs["base_image_digests"].values()) == {DIGESTS[0]}
    assert inputs["dockerfile_frontend_digest"].startswith("sha256:")


def test_catalog_rejects_mutable_base_or_missing_generated_artifact(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)
    catalog = catalog_fixture(repository)
    (repository / "Dockerfile").write_text("FROM python:3.12-alpine\n", encoding="utf-8")

    with pytest.raises(ValueError, match="base image is not pinned"):
        catalog_candidate_inputs(repository, catalog)

    (repository / "Dockerfile").write_text(f"FROM python:3.12-alpine@{DIGESTS[0]}\n", encoding="utf-8")
    catalog["components"]["api"]["generated_artifacts"] = ["missing/**"]
    with pytest.raises(ValueError, match="generated artifact pattern is empty"):
        catalog_candidate_inputs(repository, catalog)


def test_oci_attestations_bind_exact_source_platform_materials_and_reject_tampering(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar"
    write_oci_fixture(archive)

    result = inspect_oci_candidate(
        archive,
        source_sha=HEAD,
        candidate_identity=DIGESTS[1],
        architecture="amd64",
        platform="linux",
        expected_base_digests={DIGESTS[0]},
    )

    assert result["sbom"]["subject_digest"] == result["image_digest"]
    assert result["provenance"]["source_sha"] == HEAD
    write_oci_fixture(archive, tamper_image=True)
    with pytest.raises(ValueError, match="descriptor integrity failed"):
        inspect_oci_candidate(
            archive,
            source_sha=HEAD,
            candidate_identity=DIGESTS[1],
            architecture="amd64",
            platform="linux",
            expected_base_digests={DIGESTS[0]},
        )


@pytest.mark.parametrize(
    ("observed_sha", "clean", "message"),
    (("b" * 40, True, "CANDIDATE_HEAD_MOVED"), (HEAD, False, "CANDIDATE_WORKTREE_DIRTY")),
)
def test_freeze_rejects_moved_or_dirty_source(tmp_path: Path, observed_sha: str, clean: bool, message: str) -> None:
    repository = repository_fixture(tmp_path)

    with pytest.raises(ValueError, match=message):
        freeze_candidate(
            repository,
            source_sha=HEAD,
            observed_sha=observed_sha,
            clean=clean,
            generated_artifacts={},
            dockerfile_frontend_digest=DIGESTS[1],
            build_arguments={},
            base_image_digests={"runtime": DIGESTS[2]},
            architecture="amd64",
            platform="linux",
        )


def test_every_effective_candidate_input_changes_identity(tmp_path: Path) -> None:
    candidate = freeze(tmp_path)
    original = candidate["candidate_manifest"]["digest"]
    repository = tmp_path
    (repository / "src/app.py").write_text("print('changed')\n", encoding="utf-8")
    source_changed = freeze_candidate(
        repository,
        source_sha=HEAD,
        observed_sha=HEAD,
        clean=True,
        generated_artifacts={"openapi.json": DIGESTS[0]},
        dockerfile_frontend_digest=DIGESTS[1],
        build_arguments={"VERSION": "1"},
        base_image_digests={"runtime": DIGESTS[2]},
        architecture="amd64",
        platform="linux",
    )
    assert source_changed["candidate_manifest"]["digest"] != original

    input_mutations = (
        {"generated_artifacts": {"openapi.json": DIGESTS[7]}},
        {"dockerfile_frontend_digest": DIGESTS[7]},
        {"build_arguments": {"VERSION": "2"}},
        {"base_image_digests": {"runtime": DIGESTS[7]}},
        {"architecture": "arm64"},
        {"platform": "darwin"},
    )
    for mutation in input_mutations:
        arguments = {
            "generated_artifacts": {"openapi.json": DIGESTS[0]},
            "dockerfile_frontend_digest": DIGESTS[1],
            "build_arguments": {"VERSION": "1"},
            "base_image_digests": {"runtime": DIGESTS[2]},
            "architecture": "amd64",
            "platform": "linux",
            **mutation,
        }
        mutated = freeze_candidate(repository, source_sha=HEAD, observed_sha=HEAD, clean=True, **arguments)
        assert mutated["candidate_manifest"]["digest"] != source_changed["candidate_manifest"]["digest"]


@pytest.mark.parametrize("missing", ["images", "sboms", "provenances"])
def test_supply_binding_requires_exact_image_sbom_and_provenance_inventory(tmp_path: Path, missing: str) -> None:
    candidate = freeze(tmp_path)
    images = {"web": DIGESTS[3]}
    sboms = {"web": {"format": "spdx-json-2.3", "subject_digest": DIGESTS[3], "artifact_digest": DIGESTS[5]}}
    provenances = {
        "web": {
            "format": "slsa-provenance-v1",
            "subject_digest": DIGESTS[3],
            "candidate_identity": candidate["candidate_manifest"]["digest"],
            "builder_identity": "waooaw-buildkit-v1",
            "artifact_digest": DIGESTS[6],
        }
    }
    values = {"images": images, "sboms": sboms, "provenances": provenances}
    values[missing] = {}

    with pytest.raises(ValueError, match="exact required image inventory"):
        bind_candidate_supply(
            candidate,
            required_images={"web"},
            required_gates=["test-web"],
            **values,
        )


def test_exact_candidate_consumes_complete_inventory_and_post_freeze_change_invalidates_evidence(tmp_path: Path) -> None:
    candidate = freeze(tmp_path)
    binding = supply(candidate)
    identity = binding["candidate_identity"]
    evidence = {gate: {"candidate_identity": identity, "result": "PASS"} for gate in binding["required_gates"]}

    result = qualify_candidate(binding, observed_candidate_identity=identity, gate_evidence=evidence)

    assert result["result"] == "PASS"
    assert result["executed_gates"] == binding["required_gates"]
    with pytest.raises(ValueError, match="INVENTORY_INCOMPLETE"):
        qualify_candidate(binding, observed_candidate_identity=identity, gate_evidence={"test-web": evidence["test-web"]})
    with pytest.raises(ValueError, match="CANDIDATE_CHANGED"):
        qualify_candidate(binding, observed_candidate_identity=DIGESTS[7], gate_evidence=evidence)

    changed = deepcopy(candidate)
    changed["candidate_manifest"]["digest"] = DIGESTS[7]
    changed_binding = supply(changed)
    with pytest.raises(ValueError, match="CANDIDATE_CHANGED"):
        qualify_candidate(changed_binding, observed_candidate_identity=identity, gate_evidence=evidence)
