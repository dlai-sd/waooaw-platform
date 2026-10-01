"""WC-109 hosted workflow policy contracts."""

from pathlib import Path

import pytest

from validation_control.hosted_policy import GOVERNED_PATHS, validate_hosted_policy


ROOT = Path(__file__).resolve().parents[2]


def test_governed_hosted_validation_paths_pass_policy() -> None:
    assert validate_hosted_policy(ROOT) == []


@pytest.mark.parametrize(
    ("command", "policy_id"),
    (
        ("pytest -q tests", "host-pytest"),
        ("dotnet test tests/project.csproj", "host-dotnet-test"),
        ("npx jest --runInBand", "host-jest"),
        ("npx playwright test", "host-playwright"),
        ("python3 -m venv .venv", "host-virtual-environment"),
        ("pip install -r requirements-test.txt", "host-package-install"),
    ),
)
def test_hosted_policy_rejects_host_test_and_install_commands(
    tmp_path: Path,
    command: str,
    policy_id: str,
) -> None:
    relative = ".github/workflows/fixture.yaml"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(
        f"name: Fixture\non: workflow_dispatch\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: {command}\n",
        encoding="utf-8",
    )

    violations = validate_hosted_policy(tmp_path, (relative,))

    assert violations == [f"HOSTED_COMMAND_PROHIBITED:{relative}:{policy_id}"]


def test_hosted_policy_does_not_treat_catalog_metadata_as_host_test_execution(tmp_path: Path) -> None:
    relative = ".github/workflows/fixture.yaml"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(
        "name: Fixture\non: workflow_dispatch\njobs:\n  evidence:\n    runs-on: ubuntu-latest\n"
        '    steps:\n      - run: scripts/record_build_evidence.sh \'["pytest","jest"]\'\n',
        encoding="utf-8",
    )

    assert validate_hosted_policy(tmp_path, (relative,)) == []


def test_hosted_policy_inventory_covers_validation_workflows_and_actions() -> None:
    assert set(GOVERNED_PATHS) == {
        ".github/workflows/validation-plan.yaml",
        ".github/workflows/ci.yaml",
        ".github/workflows/code-quality.yaml",
        ".github/workflows/integration-tests.yaml",
        ".github/workflows/e2e-acceptance-tests.yaml",
        ".github/actions/run-validation-gate/action.yml",
        ".github/actions/record-shadow-comparison/action.yml",
    }
