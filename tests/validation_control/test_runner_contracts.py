"""WC102-01/02 runner boundary tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §4.3-4.12
# Constitutional basis: C-059, C-071, C-080

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
RUNNERS = ("test-runner-python", "test-runner-dotnet", "test-runner-ts")


def test_stack_runners_are_non_root_bounded_and_source_mounted() -> None:
    for runner_name in RUNNERS:
        runner = COMPOSE["services"][runner_name]
        assert runner["read_only"] is True
        assert runner["cap_drop"] == ["ALL"]
        assert runner["security_opt"] == ["no-new-privileges:true"]
        assert runner["cpus"] == 2.0
        assert runner["mem_limit"] == "4g"
        assert runner["pids_limit"] == 512

    assert ".:/workspace:ro" in COMPOSE["services"]["test-runner-python"]["volumes"]
    assert ".:/workspace:ro" in COMPOSE["services"]["test-runner-dotnet"]["volumes"]
    typescript_volumes = COMPOSE["services"]["test-runner-ts"]["volumes"]
    assert "./web:/workspace/web:ro" in typescript_volumes
    assert "./coverage:/workspace/coverage" in typescript_volumes
    assert all(":/workspace/web/" not in volume for volume in typescript_volumes)
    assert all(":/workspace/web/" not in volume for volume in COMPOSE["services"]["test-runner"]["volumes"])


def test_socket_is_absent_from_typescript_runner_and_bounded_elsewhere() -> None:
    assert all("docker.sock" not in volume for volume in COMPOSE["services"]["test-runner-ts"]["volumes"])
    for runner_name in ("test-runner-python", "test-runner-dotnet", "test-runner"):
        runner = COMPOSE["services"][runner_name]
        assert "/var/run/docker.sock:/var/run/docker.sock" in runner["volumes"]
        assert runner["group_add"] == ["${DOCKER_GID:-0}"]


def test_runner_images_exclude_application_source() -> None:
    dockerfiles = [
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-python",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-ts",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner",
    ]

    for dockerfile in dockerfiles:
        source = dockerfile.read_text(encoding="utf-8")
        assert "COPY . /workspace" not in source
        assert "COPY --chown=waooaw:waooaw . /workspace" not in source
        assert "USER root" not in source


def test_dotnet_cache_path_is_aligned() -> None:
    dockerfile = (ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet").read_text(encoding="utf-8")
    volumes = COMPOSE["services"]["test-runner-dotnet"]["volumes"]

    assert "NUGET_PACKAGES=/opt/nuget/packages" in dockerfile
    assert "wc102_nuget_cache:/opt/nuget/packages" in volumes
    assert "/tmp/nuget" not in str(COMPOSE["services"]["test-runner-dotnet"])