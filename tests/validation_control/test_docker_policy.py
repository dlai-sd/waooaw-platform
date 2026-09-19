"""WC102-01 Docker-only workflow policy tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §4.1, §4.11
# Constitutional basis: C-059, C-071, C-080

from pathlib import Path

from validation_control.docker_policy import inspect_workflow


def workflow(tmp_path: Path, command: str) -> Path:
    path = tmp_path / "ci.yaml"
    path.write_text(
        "name: fixture\non: push\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - name: command\n        run: |\n" + "\n".join(f"          {line}" for line in command.splitlines()) + "\n",
        encoding="utf-8",
    )
    return path


def test_rejects_host_test_commands_installation_virtualenv_and_root(tmp_path: Path) -> None:
    cases = {
        "pytest tests -q": "HOST_TEST_COMMAND",
        "dotnet test tests/example.csproj": "HOST_TEST_COMMAND",
        "npx playwright test": "HOST_TEST_COMMAND",
        "pip install pytest": "HOST_TEST_INSTALL",
        "python -m venv .venv": "VIRTUAL_ENVIRONMENT",
        "docker compose run --rm --user root runner pytest": "ROOT_RUNNER_OVERRIDE",
    }

    for command, expected in cases.items():
        assert any(expected in violation for violation in inspect_workflow(workflow(tmp_path, command)))


def test_allows_tools_inside_non_root_docker_runner(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        "docker compose --profile test-python run --rm test-runner-python sh -lc '\n"
        "  ruff check scripts tests\n"
        "  pytest tests -q\n'",
    )

    assert inspect_workflow(path) == []


def test_allows_multiline_non_root_container_command(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        "docker compose --profile test-python run --rm \\\n"
        "  -e MODE=check test-runner-python sh -lc '\n"
        "  python scripts/validate_author_review.py\n"
        "  ruff check scripts\n'",
    )

    assert inspect_workflow(path) == []


def test_allows_conditional_non_root_container_command(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        "if docker compose --profile test-python run --rm \\\n"
        "  test-runner-python sh -lc '\n"
        "  python scripts/validate_author_review.py\n"
        "'; then\n"
        "  exit 0\n"
        "fi",
    )

    assert inspect_workflow(path) == []


def test_operational_install_outside_validation_workflow_is_not_c080_test_install(tmp_path: Path) -> None:
    path = workflow(tmp_path, "pip install -r requirements-sprint.txt")
    path = path.rename(tmp_path / "autonomous-sprint.yaml")

    assert inspect_workflow(path) == []


def test_malformed_workflow_fails_closed_without_traceback(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("jobs:\n  check:\n    steps:\n      - run: echo 'bad: scalar'\n", encoding="utf-8")

    assert inspect_workflow(path) == [f"{path}:4: WORKFLOW_YAML_INVALID"]
