"""Offline contracts for the GOAL-006 private runner lifecycle."""

from __future__ import annotations

import base64
import json

import pytest

from scripts.goal006_runner_lifecycle import (
    LifecycleError,
    _assert_zero_active_executions,
    _find_correlated_execution,
    create_app_jwt,
    correlation_id,
    deployment_job_is_terminal,
    _execution_environment,
    runner_name,
    read_runner_token,
    select_correlated_runner,
    validate_installation,
)


def _decode_jwt_segment(value: str) -> dict[str, object]:
    return json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))


def test_correlation_and_runner_name_are_environment_scoped() -> None:
    assert correlation_id("demo", "123", "2") == "goal006:demo:123:2"
    assert runner_name("demo", "123", "2") == "goal006-demo-123-2"


@pytest.mark.parametrize(
    ("environment", "run_id", "attempt"),
    [("stage", "123", "1"), ("demo", "0", "1"), ("demo", "123", "first")],
)
def test_invalid_correlation_input_fails_closed(
    environment: str, run_id: str, attempt: str
) -> None:
    with pytest.raises(LifecycleError):
        correlation_id(environment, run_id, attempt)


def test_app_jwt_is_short_lived_and_signs_only_the_digest() -> None:
    observed: dict[str, object] = {}

    def sign(key_id: str, digest: bytes) -> bytes:
        observed.update(key_id=key_id, digest=digest)
        return b"signed"

    token = create_app_jwt("12345", "https://vault/keys/app/version", sign, now=1000)
    header, payload, signature = token.split(".")

    assert _decode_jwt_segment(header) == {"alg": "RS256", "typ": "JWT"}
    assert _decode_jwt_segment(payload) == {"iat": 970, "exp": 1540, "iss": "12345"}
    assert observed["key_id"] == "https://vault/keys/app/version"
    assert len(observed["digest"]) == 32
    assert base64.urlsafe_b64decode(signature + "==") == b"signed"


def test_cleanup_selector_requires_all_labels_and_one_exact_name() -> None:
    runner = {
        "id": 7,
        "name": "goal006-demo-123-2",
        "labels": [
            {"name": "goal006-demo-private"},
            {"name": "goal006:demo:123:2"},
        ],
    }
    selected = select_correlated_runner(
        [runner],
        expected_name="goal006-demo-123-2",
        required_labels={"goal006-demo-private", "goal006:demo:123:2"},
    )
    assert selected == runner
    assert (
        select_correlated_runner(
            [runner],
            expected_name="goal006-demo-123-2",
            required_labels={"goal006-demo-private", "wrong"},
        )
        is None
    )


def test_cleanup_selector_ambiguity_fails_closed() -> None:
    runner = {
        "id": 7,
        "name": "goal006-demo-123-2",
        "labels": [{"name": "goal006-demo-private"}],
    }
    with pytest.raises(LifecycleError, match="ambiguous"):
        select_correlated_runner(
            [runner, runner],
            expected_name="goal006-demo-123-2",
            required_labels={"goal006-demo-private"},
        )


def test_private_job_must_be_uniquely_terminal() -> None:
    assert deployment_job_is_terminal(
        [{"name": "Deploy private qualification", "status": "completed", "conclusion": "success"}],
        "Deploy private qualification",
    )
    with pytest.raises(LifecycleError, match="ambiguous"):
        deployment_job_is_terminal([], "Deploy private qualification")
    assert not deployment_job_is_terminal(
        [{"name": "Deploy private qualification", "status": "in_progress", "conclusion": None}],
        "Deploy private qualification",
    )


def test_app_manifest_does_not_grant_actions_permission() -> None:
    manifest = json.loads(
        __import__("pathlib").Path(
            "architecture/reference/pipeline/github-runner-app-manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert "actions" not in manifest["repository_permissions"]
    assert "actions" in manifest["prohibited_permissions"]
    assert manifest["installation_target"] == "user"
    assert manifest["account"] == "dlai-sd"
    assert manifest["repository_permissions"] == {
        "administration": "write",
        "metadata": "read",
    }


def test_personal_installation_is_repository_scoped() -> None:
    manifest = {
        "installation_target": "user",
        "account": "dlai-sd",
        "repositories": ["waooaw-platform"],
        "repository_permissions": {"administration": "write", "metadata": "read"},
    }

    class InstallationApi:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def request(self, method, url, **kwargs):
            self.urls.append(url)
            if url.endswith("/app/installations/155648751"):
                return {
                    "target_type": "User",
                    "account": {"login": "dlai-sd"},
                    "permissions": manifest["repository_permissions"],
                }
            if url.endswith("/app/installations/155648751/access_tokens"):
                return {"token": "installation-token"}
            if url.endswith("/installation/repositories?per_page=100"):
                return {"repositories": [{"name": "waooaw-platform"}]}
            raise AssertionError(url)

    api = InstallationApi()
    assert validate_installation(api, manifest, "155648751", "app-jwt") == (
        "installation-token"
    )
    assert all("/orgs/" not in url for url in api.urls)


def test_runner_control_uses_repository_endpoints() -> None:
    source = __import__("pathlib").Path(
        "scripts/goal006_runner_lifecycle.py"
    ).read_text(encoding="utf-8")

    assert 'f"/repos/{context.repository}/actions/runners?per_page=100"' in source
    assert (
        'f"/repos/{context.repository}/actions/runners/registration-token"' in source
    )
    assert 'f"/repos/{context.repository}/actions/runners/{runner[' in source
    assert "/orgs/" not in source


def test_lifecycle_source_never_serializes_tokens_into_evidence() -> None:
    source = __import__("pathlib").Path(
        "scripts/goal006_runner_lifecycle.py"
    ).read_text(encoding="utf-8")
    record_block = source.split("return {", 1)[1].split("}\n", 1)[0]
    assert "registration_token" not in record_block
    assert "installation_token" not in record_block


def test_execution_correlation_is_read_from_runner_override() -> None:
    execution = {
        "properties": {
            "template": {
                "containers": [
                    {
                        "name": "runner",
                        "env": [
                            {
                                "name": "RUNNER_CORRELATION_ID",
                                "value": "goal006:demo:123:2",
                            }
                        ],
                    }
                ]
            }
        }
    }
    assert _execution_environment(execution)["RUNNER_CORRELATION_ID"] == (
        "goal006:demo:123:2"
    )


def test_invalid_execution_shape_fails_closed() -> None:
    with pytest.raises(LifecycleError, match="template is invalid"):
        _execution_environment({"properties": {"template": {"containers": []}}})


def test_runner_image_uses_immutable_inputs_and_ephemeral_registration() -> None:
    from pathlib import Path

    dockerfile = Path("infrastructure/runner/Dockerfile").read_text(encoding="utf-8")
    entrypoint = Path("infrastructure/runner/entrypoint.sh").read_text(encoding="utf-8")

    assert "FROM ghcr.io/actions/actions-runner@sha256:" in dockerfile
    assert "AZURE_CLI_SHA256=" in dockerfile
    assert "TERRAFORM_SHA256=" in dockerfile
    assert "sha256sum --check --strict" in dockerfile
    assert "--ephemeral" in entrypoint
    assert "--disableupdate" in entrypoint
    assert '--url "https://github.com/$GITHUB_REPOSITORY"' in entrypoint
    assert "--runnergroup" not in entrypoint
    assert "RUNNER_GROUP" not in entrypoint
    assert "github-run-$GITHUB_WORKFLOW_RUN_ID" in entrypoint
    assert "unset RUNNER_REGISTRATION_TOKEN" in entrypoint
    assert "--replace" not in entrypoint
    assert "github-runner-app-manifest.json /opt/waooaw/github-runner-app-manifest.json" in dockerfile
    assert entrypoint.index('test "$RUNNER_ACTIVATION_STATE" = ACTIVE || exit 0') < entrypoint.index("required_environment=(")


def test_runner_image_ci_blocks_on_fixable_os_vulnerabilities() -> None:
    from pathlib import Path

    workflow = Path(".github/workflows/goal006-runner-image.yaml").read_text(
        encoding="utf-8"
    )
    assert "vuln-type: os" in workflow
    assert "severity: CRITICAL,HIGH" in workflow
    assert "ignore-unfixed: true" in workflow
    assert "exit-code: 1" in workflow


class _SecretApi:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def request(self, *args, **kwargs):
        return self.response


def test_runner_reads_only_live_correlated_token() -> None:
    token = read_runner_token(
        _SecretApi(
            {
                "value": "short-lived-token",
                "attributes": {"enabled": True, "exp": 1500},
                "tags": {"correlation": "goal006:demo:123:2"},
            }
        ),
        vault_url="https://runner.vault.azure.net",
        secret_name="runner-token",
        expected_correlation="goal006:demo:123:2",
        now=1000,
    )
    assert token == "short-lived-token"


@pytest.mark.parametrize(
    "response",
    [
        {"value": "token", "attributes": {"enabled": False, "exp": 1500}, "tags": {"correlation": "goal006:demo:123:2"}},
        {"value": "token", "attributes": {"enabled": True, "exp": 999}, "tags": {"correlation": "goal006:demo:123:2"}},
        {"value": "token", "attributes": {"enabled": True, "exp": 2000}, "tags": {"correlation": "goal006:demo:123:2"}},
        {"value": "token", "attributes": {"enabled": True, "exp": 1500}, "tags": {"correlation": "wrong"}},
    ],
)
def test_runner_rejects_invalid_token_secret(response: dict[str, object]) -> None:
    with pytest.raises(LifecycleError):
        read_runner_token(
            _SecretApi(response),
            vault_url="https://runner.vault.azure.net",
            secret_name="runner-token",
            expected_correlation="goal006:demo:123:2",
            now=1000,
        )


def test_pre_token_gate_rejects_active_execution() -> None:
    class ExecutionApi:
        def request(self, *args, **kwargs):
            return {"value": [{"name": "execution", "properties": {"status": "Running"}}]}

    context = type(
        "Context",
        (),
        {"job_resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/job"},
    )()
    with pytest.raises(LifecycleError, match="already exists"):
        _assert_zero_active_executions(ExecutionApi(), context)


def test_broker_finds_one_correlation_bound_execution() -> None:
    class ExecutionApi:
        def request(self, method, url, **kwargs):
            if url.endswith("/executions?api-version=2024-03-01"):
                return {"value": [{"name": "runner-one"}, {"name": "runner-two"}]}
            correlation = "goal006:demo:123:2" if "runner-two" in url else "other"
            return {
                "properties": {
                    "template": {
                        "containers": [
                            {
                                "name": "runner",
                                "env": [
                                    {"name": "RUNNER_CORRELATION_ID", "value": correlation}
                                ],
                            }
                        ]
                    }
                }
            }

    context = type(
        "Context",
        (),
        {
            "job_resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/job",
            "correlation": "goal006:demo:123:2",
        },
    )()
    assert _find_correlated_execution(ExecutionApi(), context) == "runner-two"


def test_broker_rejects_missing_correlated_execution() -> None:
    class ExecutionApi:
        def request(self, method, url, **kwargs):
            return {"value": []}

    context = type(
        "Context",
        (),
        {
            "job_resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/job",
            "correlation": "goal006:demo:123:2",
        },
    )()
    with pytest.raises(LifecycleError, match="ambiguous"):
        _find_correlated_execution(ExecutionApi(), context)