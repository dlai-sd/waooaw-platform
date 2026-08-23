"""Offline contracts for the GOAL-006 private runner lifecycle."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.goal006_runner_lifecycle import (
    HttpStatusError,
    JsonApi,
    LifecycleError,
    ReconcilerContext,
    RunnerContext,
    _assert_zero_active_executions,
    _find_correlated_execution,
    _cleanup_evidence_line,
    _start_execution,
    cleanup_correlated_runner,
    cleanup_evidence_blob_name,
    create_app_jwt,
    correlation_id,
    deployment_job_is_terminal,
    _execution_environment,
    runner_name,
    read_runner_token,
    reconcile_runners,
    select_correlated_runner,
    validate_installation,
    write_cleanup_evidence,
    workflow_run_conclusion,
)


def _decode_jwt_segment(value: str) -> dict[str, object]:
    return json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))


def test_correlation_and_runner_name_are_environment_scoped() -> None:
    assert correlation_id("demo", "123", "2") == "goal006:demo:123:2"
    assert runner_name("demo", "123", "2") == "goal006-demo-123-2"


def test_cleanup_evidence_blob_name_is_correlation_bound() -> None:
    assert cleanup_evidence_blob_name("demo", "123", "2") == (
        "cleanup/demo/123/2.json"
    )


def test_cleanup_evidence_is_written_once_with_canonical_digest() -> None:
    requests: list[tuple[str, str, dict[str, object]]] = []

    class EvidenceApi:
        def request(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return None

    record = {
        "schema": "waooaw.goal006-runner-cleanup/v1",
        "correlation_id": "goal006:demo:123:2",
        "registration_absent": True,
    }
    pointer = write_cleanup_evidence(EvidenceApi(), _runner_context(), record)

    method, url, kwargs = requests[0]
    assert method == "PUT"
    assert url == (
        "https://storage.example/goal006-runner-evidence/cleanup/demo/123/2.json"
    )
    assert kwargs["headers"]["If-None-Match"] == "*"
    assert kwargs["headers"]["x-ms-blob-type"] == "BlockBlob"
    assert kwargs["headers"]["x-ms-date"].endswith(" GMT")
    assert json.loads(kwargs["raw_body"]) == record
    assert pointer == {
        "schema": "waooaw.goal006-runner-cleanup-pointer/v1",
        "correlation_id": "goal006:demo:123:2",
        "evidence_blob_url": url,
        "evidence_sha256": "sha256:08929851925ad1654551c862d6c575923c08a9f5c65456443e626868f5f9af13",
    }


def _runner_context(run_id: str = "123", run_attempt: str = "2") -> RunnerContext:
    return RunnerContext(
        environment="demo",
        repository="dlai-sd/waooaw-platform",
        run_id=run_id,
        run_attempt=run_attempt,
        subscription_id="sub",
        resource_group="rg",
        job_name="runner-job",
        vault_url="https://vault.example",
        token_secret_name="runner-token",
        app_id="4680703",
        installation_id="155648751",
        app_key_id="https://vault.example/keys/app/version",
        runner_label="goal006-demo-private",
        activation_state="ACTIVE",
        evidence_container_url="https://storage.example/goal006-runner-evidence",
        evidence_writer_client_id="11111111-2222-3333-4444-555555555555",
    )


def test_token_secret_name_is_unique_per_workflow_attempt() -> None:
    first = _runner_context(run_attempt="1").correlated_token_secret_name
    second = _runner_context(run_attempt="2").correlated_token_secret_name

    assert first == "runner-token-demo-123-1"
    assert second == "runner-token-demo-123-2"
    assert first != second


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


def test_app_manifest_grants_only_required_read_actions_permission() -> None:
    manifest = json.loads(
        __import__("pathlib").Path(
            "architecture/reference/pipeline/github-runner-app-manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["repository_permissions"]["actions"] == "read"
    assert "actions" not in manifest["prohibited_permissions"]
    assert manifest["installation_target"] == "user"
    assert manifest["account"] == "dlai-sd"
    assert manifest["repository_permissions"] == {
        "actions": "read",
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


def test_cleanup_log_evidence_is_encoded_without_tokens() -> None:
    line = _cleanup_evidence_line(
        {
            "schema": "waooaw.goal006-runner-cleanup/v1",
            "registration_absent": True,
        }
    )
    assert line.startswith("GOAL006_CLEANUP_RECORD_B64=")
    assert "token" not in line.casefold()


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
    importer = Path("infrastructure/runner/import-app-signing-material.sh").read_text(encoding="utf-8")
    operator = Path("scripts/goal006_import_app_signing_material.sh").read_text(encoding="utf-8")

    assert "FROM ghcr.io/actions/actions-runner@sha256:" in dockerfile
    assert "AZURE_CLI_SHA256=" in dockerfile
    assert "TERRAFORM_SHA256=" in dockerfile
    assert "jq openssl unzip" in dockerfile
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
    assert "import-app-signing-material.sh /opt/waooaw/import-app-signing-material.sh" in dockerfile
    assert "stty -echo" in importer
    assert "--pem-file" in importer
    assert "--pem-string" not in importer
    assert "--exportable false" in importer
    assert "--ops sign verify" in importer
    assert "unset" not in operator
    assert "--min-replicas 1" in operator
    assert "--min-replicas 0" in operator
    assert "az containerapp exec" in operator
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


def test_runner_start_clones_complete_template_before_binding_correlation() -> None:
    template = {
        "containers": [
            {
                "name": "runner",
                "image": "runner@sha256:" + "a" * 64,
                "command": ["/opt/waooaw/entrypoint.sh"],
                "resources": {"cpu": 1.0, "memory": "2Gi"},
                "env": [{"name": "RUNNER_ACTIVATION_STATE", "value": "ACTIVE"}],
            }
        ]
    }

    class ExecutionApi:
        def __init__(self) -> None:
            self.body = None

        def request(self, method, url, **kwargs):
            if method == "GET":
                return {"properties": {"template": template}}
            self.body = kwargs["body"]
            return {"name": "runner-execution"}

    context = type(
        "Context",
        (),
        {
            "job_resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/job",
            "correlation": "goal006:demo:123:2",
            "runner_name": "goal006-demo-123-2",
            "runner_label": "goal006-demo-private",
            "correlated_token_secret_name": "runner-token-demo-123-2",
            "repository": "dlai-sd/waooaw-platform",
            "run_id": "123",
            "run_attempt": "2",
        },
    )()
    api = ExecutionApi()

    assert _start_execution(api, context) == "runner-execution"
    assert set(api.body) <= {"containers", "initContainers"}
    assert "template" not in api.body
    container = api.body["containers"][0]
    assert container["image"] == template["containers"][0]["image"]
    assert container["command"] == ["/opt/waooaw/entrypoint.sh"]
    assert container["resources"] == {"cpu": 1.0, "memory": "2Gi"}
    environment = {item["name"]: item["value"] for item in container["env"]}
    assert environment["RUNNER_CORRELATION_ID"] == "goal006:demo:123:2"
    assert environment["RUNNER_TOKEN_SECRET_NAME"] == "runner-token-demo-123-2"
    assert environment["GITHUB_WORKFLOW_RUN_ID"] == "123"


def test_runner_start_serializes_azure_execution_template_at_body_root(monkeypatch) -> None:
    template = {
        "containers": [{"name": "runner", "env": []}],
        "initContainers": [{"name": "prepare"}],
        "volumes": [{"name": "job-template-only"}],
    }
    requests = []

    class Response:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def urlopen(request, timeout):
        requests.append(request)
        if request.get_method() == "GET":
            return Response({"properties": {"template": template}})
        return Response({"name": "runner-execution"})

    monkeypatch.setattr(
        "scripts.goal006_runner_lifecycle.urllib.request.urlopen", urlopen
    )
    context = type(
        "Context",
        (),
        {
            "job_resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/job",
            "correlation": "goal006:demo:123:2",
            "runner_name": "goal006-demo-123-2",
            "runner_label": "goal006-demo-private",
            "correlated_token_secret_name": "runner-token-demo-123-2",
            "repository": "dlai-sd/waooaw-platform",
            "run_id": "123",
            "run_attempt": "2",
        },
    )()

    assert _start_execution(JsonApi(lambda resource: "token"), context) == "runner-execution"
    expected_body = {
        "containers": [
            {
                "name": "runner",
                "env": [
                    {"name": "RUNNER_CORRELATION_ID", "value": "goal006:demo:123:2"},
                    {"name": "RUNNER_NAME", "value": "goal006-demo-123-2"},
                    {"name": "RUNNER_LABEL", "value": "goal006-demo-private"},
                    {"name": "RUNNER_TOKEN_SECRET_NAME", "value": "runner-token-demo-123-2"},
                    {"name": "GITHUB_REPOSITORY", "value": "dlai-sd/waooaw-platform"},
                    {"name": "GITHUB_WORKFLOW_RUN_ID", "value": "123"},
                    {"name": "GITHUB_WORKFLOW_RUN_ATTEMPT", "value": "2"},
                ],
            }
        ],
        "initContainers": [{"name": "prepare"}],
    }
    assert requests[1].get_method() == "POST"
    assert requests[1].full_url.endswith("/start?api-version=2024-03-01")
    assert requests[1].data == json.dumps(expected_body, separators=(",", ":")).encode(
        "utf-8"
    )


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


def _reconciler_context() -> ReconcilerContext:
    return ReconcilerContext(
        environment="demo",
        repository="dlai-sd/waooaw-platform",
        subscription_id="sub",
        resource_group="rg",
        job_name="runner-job",
        vault_url="https://vault.example",
        token_secret_name="runner-token",
        app_id="4680703",
        installation_id="155648751",
        app_key_id="https://vault.example/keys/app/version",
        runner_label="goal006-demo-private",
        activation_state="ACTIVE",
    )


def _active_execution(
    *, correlation: str = "goal006:demo:123:2", status: str = "Running"
) -> dict[str, object]:
    return {
        "name": "runner-job-execution",
        "properties": {
            "status": status,
            "startTime": "2026-08-22T12:30:00Z",
            "template": {
                "containers": [
                    {
                        "name": "runner",
                        "env": [
                            {"name": "RUNNER_CORRELATION_ID", "value": correlation},
                            {"name": "RUNNER_NAME", "value": "goal006-demo-123-2"},
                            {"name": "RUNNER_LABEL", "value": "goal006-demo-private"},
                            {"name": "RUNNER_TOKEN_SECRET_NAME", "value": "runner-token-demo-123-2"},
                            {"name": "GITHUB_REPOSITORY", "value": "dlai-sd/waooaw-platform"},
                            {"name": "GITHUB_WORKFLOW_RUN_ID", "value": "123"},
                            {"name": "GITHUB_WORKFLOW_RUN_ATTEMPT", "value": "2"},
                        ],
                    }
                ]
            },
        },
    }


class _ReconcilerApi:
    def __init__(self, executions: list[dict[str, object]]) -> None:
        self.executions = executions

    def request(self, method, url, **kwargs):
        if url.endswith("/executions?api-version=2024-03-01"):
            return {"value": self.executions}
        if "/executions/" in url:
            return self.executions[0]
        raise AssertionError(url)


def test_reconciler_succeeds_without_active_execution(tmp_path: Path) -> None:
    record = reconcile_runners(
        _ReconcilerApi([]),
        _reconciler_context(),
        tmp_path / "unused.json",
    )
    assert record["decision"] == "NO_ACTIVE_EXECUTIONS"
    assert record["cleaned_executions"] == []


def test_reconciler_rejects_ambiguous_active_executions(tmp_path: Path) -> None:
    execution = _active_execution()
    with pytest.raises(LifecycleError, match="selector is ambiguous"):
        reconcile_runners(
            _ReconcilerApi([execution, execution]),
            _reconciler_context(),
            tmp_path / "unused.json",
        )


def test_reconciler_rejects_correlation_mismatch(tmp_path: Path) -> None:
    with pytest.raises(LifecycleError, match="correlation contract"):
        reconcile_runners(
            _ReconcilerApi([_active_execution(correlation="wrong")]),
            _reconciler_context(),
            tmp_path / "unused.json",
            now=datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ("execution_status", "conclusion", "now", "expected_decision", "predicate", "active_count"),
    [
        ("Running", None, datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc), "ACTIVE_RUN_WITHIN_LIMIT", None, 1),
        ("Running", "cancelled", datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc), "CLEANED_ELIGIBLE_EXECUTION", "cancelled", 1),
        ("Running", "absent", datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc), "CLEANED_ELIGIBLE_EXECUTION", "absent", 1),
        ("Running", None, datetime(2026, 8, 22, 13, 31, tzinfo=timezone.utc), "CLEANED_ELIGIBLE_EXECUTION", "AGE_LIMIT", 1),
        ("Succeeded", None, datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc), "TERMINAL_EXECUTION_AWAITING_RUN", None, 0),
        ("Succeeded", "cancelled", datetime(2026, 8, 22, 12, 35, tzinfo=timezone.utc), "CLEANED_ELIGIBLE_EXECUTION", "cancelled", 0),
    ],
)
def test_reconciler_applies_exact_lifecycle_predicate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execution_status: str,
    conclusion: str | None,
    now: datetime,
    expected_decision: str,
    predicate: str | None,
    active_count: int,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "account": "dlai-sd",
                "repositories": ["waooaw-platform"],
                "repository_permissions": {"actions": "read", "administration": "write", "metadata": "read"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.goal006_runner_lifecycle.create_app_jwt", lambda *args: "jwt")
    monkeypatch.setattr("scripts.goal006_runner_lifecycle.validate_installation", lambda *args: "installation-token")
    monkeypatch.setattr("scripts.goal006_runner_lifecycle.workflow_run_conclusion", lambda *args: conclusion)
    monkeypatch.setattr(
        "scripts.goal006_runner_lifecycle.cleanup_correlated_runner",
        lambda *args: {"aca_execution_name": "runner-job-execution"},
    )

    record = reconcile_runners(
        _ReconcilerApi([_active_execution(status=execution_status)]),
        _reconciler_context(),
        manifest,
        now=now,
    )
    assert record["decision"] == expected_decision
    assert record["observed_active_executions"] == active_count
    if predicate is None:
        assert "lifecycle_predicate" not in record
    else:
        assert record["lifecycle_predicate"] == predicate


def test_missing_workflow_run_is_terminal_for_reconciliation() -> None:
    class MissingRunApi:
        def request(self, method, url, **kwargs):
            raise HttpStatusError(method, url, 404)

    assert workflow_run_conclusion(
        MissingRunApi(),
        _reconciler_context().runner_context("123", "2"),
        "token",
    ) == "absent"


def test_cleanup_is_idempotent_when_broker_created_no_secret_or_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    deleted_urls = []

    class PartialBrokerApi:
        def request(self, method, url, **kwargs):
            if url.endswith("/executions?api-version=2024-03-01"):
                return {"value": []}
            if url.endswith("/actions/runners?per_page=100"):
                return {"runners": []}
            if method == "DELETE" and "/secrets/" in url:
                deleted_urls.append(url)
                raise HttpStatusError(method, url, 404)
            raise AssertionError((method, url))

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "account": "dlai-sd",
                "repositories": ["waooaw-platform"],
                "repository_permissions": {
                    "actions": "read",
                    "administration": "write",
                    "metadata": "read",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.goal006_runner_lifecycle.create_app_jwt", lambda *args: "jwt"
    )
    monkeypatch.setattr(
        "scripts.goal006_runner_lifecycle.validate_installation",
        lambda *args: "installation-token",
    )

    record = cleanup_correlated_runner(
        PartialBrokerApi(), _runner_context(), manifest, "failure"
    )

    assert record["aca_execution_name"] == ""
    assert record["token_secret_name"] == "runner-token-demo-123-2"
    assert record["token_secret_deleted"] is True
    assert record["private_job_conclusion"] == "failure"
    assert deleted_urls == [
        "https://vault.example/secrets/runner-token-demo-123-2?api-version=7.4"
    ]