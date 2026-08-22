#!/usr/bin/env python3
"""Start and clean up one correlated GOAL-006 ephemeral GitHub runner."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

GITHUB_API = "https://api.github.com"
MANAGEMENT_RESOURCE = "https://management.azure.com/"
KEY_VAULT_RESOURCE = "https://vault.azure.net"
TERMINAL_CONCLUSIONS = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "neutral",
    "stale",
}
ENVIRONMENT = re.compile(r"^(demo|uat|prod)$")
RUN_NUMBER = re.compile(r"^[1-9][0-9]*$")


class LifecycleError(RuntimeError):
    """Fail-closed lifecycle contract violation."""


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def correlation_id(environment: str, run_id: str, run_attempt: str) -> str:
    if ENVIRONMENT.fullmatch(environment) is None:
        raise LifecycleError("environment is invalid")
    if RUN_NUMBER.fullmatch(run_id) is None or RUN_NUMBER.fullmatch(run_attempt) is None:
        raise LifecycleError("workflow run identity is invalid")
    return f"goal006:{environment}:{run_id}:{run_attempt}"


def runner_name(environment: str, run_id: str, run_attempt: str) -> str:
    correlation_id(environment, run_id, run_attempt)
    return f"goal006-{environment}-{run_id}-{run_attempt}"


def create_app_jwt(
    app_id: str,
    key_id: str,
    sign_digest: Callable[[str, bytes], bytes],
    *,
    now: int | None = None,
) -> str:
    if RUN_NUMBER.fullmatch(app_id) is None:
        raise LifecycleError("GitHub App ID is invalid")
    issued_at = int(time.time() if now is None else now) - 30
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(
        json.dumps(
            {"iat": issued_at, "exp": issued_at + 570, "iss": app_id},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    digest = hashlib.sha256(signing_input.encode("ascii")).digest()
    signature = _b64url(sign_digest(key_id, digest))
    return f"{signing_input}.{signature}"


@dataclass(frozen=True)
class RunnerContext:
    environment: str
    repository: str
    run_id: str
    run_attempt: str
    subscription_id: str
    resource_group: str
    job_name: str
    vault_url: str
    token_secret_name: str
    app_id: str
    installation_id: str
    app_key_id: str
    runner_group: str
    runner_label: str
    activation_state: str

    @classmethod
    def from_environment(cls) -> RunnerContext:
        names = {
            "environment": "RUNNER_ENVIRONMENT",
            "repository": "GITHUB_REPOSITORY",
            "run_id": "GITHUB_RUN_ID",
            "run_attempt": "GITHUB_RUN_ATTEMPT",
            "subscription_id": "AZURE_SUBSCRIPTION_ID",
            "resource_group": "RUNNER_RESOURCE_GROUP",
            "job_name": "RUNNER_JOB_NAME",
            "vault_url": "RUNNER_VAULT_URL",
            "token_secret_name": "RUNNER_TOKEN_SECRET_NAME",
            "app_id": "GITHUB_APP_ID",
            "installation_id": "GITHUB_APP_INSTALLATION_ID",
            "app_key_id": "GITHUB_APP_KEY_ID",
            "runner_group": "RUNNER_GROUP",
            "runner_label": "RUNNER_LABEL",
            "activation_state": "RUNNER_ACTIVATION_STATE",
        }
        values = {field: os.environ.get(variable, "").strip() for field, variable in names.items()}
        missing = sorted(variable for field, variable in names.items() if not values[field])
        if missing:
            raise LifecycleError("required environment is missing: " + ", ".join(missing))
        context = cls(**values)
        correlation_id(context.environment, context.run_id, context.run_attempt)
        if context.activation_state != "ACTIVE":
            raise LifecycleError("runner lifecycle is not ACTIVE")
        if context.repository.count("/") != 1:
            raise LifecycleError("GitHub repository is invalid")
        if not context.vault_url.startswith("https://"):
            raise LifecycleError("runner vault URL is invalid")
        return context

    @property
    def organization(self) -> str:
        return self.repository.split("/", 1)[0]

    @property
    def correlation(self) -> str:
        return correlation_id(self.environment, self.run_id, self.run_attempt)

    @property
    def runner_name(self) -> str:
        return runner_name(self.environment, self.run_id, self.run_attempt)

    @property
    def job_resource_id(self) -> str:
        return (
            f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.App/jobs/{self.job_name}"
        )


class JsonApi:
    def __init__(self, access_token: Callable[[str], str]) -> None:
        self._access_token = access_token

    def request(
        self,
        method: str,
        url: str,
        *,
        resource: str,
        body: Mapping[str, Any] | None = None,
        github_token: str | None = None,
    ) -> Any:
        token = github_token or self._access_token(resource)
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if url.startswith(GITHUB_API):
            headers.update(
                {
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(  # noqa: S310
            url, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                payload = response.read()
        except urllib.error.HTTPError as error:
            raise LifecycleError(f"{method} {url} failed with HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise LifecycleError(f"{method} {url} failed") from error
        return json.loads(payload) if payload else None


def azure_access_token(resource: str) -> str:
    identity_endpoint = os.environ.get("IDENTITY_ENDPOINT")
    identity_header = os.environ.get("IDENTITY_HEADER")
    if identity_endpoint and identity_header:
        query = urllib.parse.urlencode(
            {
                "api-version": "2019-08-01",
                "resource": resource,
                "client_id": os.environ.get("AZURE_CLIENT_ID", ""),
            }
        )
        request = urllib.request.Request(  # noqa: S310
            f"{identity_endpoint}?{query}", headers={"X-IDENTITY-HEADER": identity_header}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                token = json.loads(response.read()).get("access_token", "")
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise LifecycleError("managed identity token acquisition failed") from error
    else:
        result = subprocess.run(  # noqa: S603
            ["/usr/bin/az", "account", "get-access-token", "--resource", resource, "-o", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise LifecycleError("Azure OIDC token acquisition failed")
        token = json.loads(result.stdout).get("accessToken", "")
    if not token:
        raise LifecycleError("Azure access token is empty")
    return str(token)


def key_vault_sign(api: JsonApi, key_id: str, digest: bytes) -> bytes:
    response = api.request(
        "POST",
        f"{key_id.rstrip('/')}/sign?api-version=7.4",
        resource=KEY_VAULT_RESOURCE,
        body={"alg": "RS256", "value": _b64url(digest)},
    )
    try:
        value = str(response["value"])
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (KeyError, TypeError, ValueError) as error:
        raise LifecycleError("Key Vault signing response is invalid") from error


def _github(api: JsonApi, method: str, path: str, token: str, body=None) -> Any:
    return api.request(
        method,
        f"{GITHUB_API}{path}",
        resource="github",
        body=body,
        github_token=token,
    )


def validate_installation(
    api: JsonApi,
    manifest: Mapping[str, Any],
    installation_id: str,
    app_jwt: str,
) -> str:
    installation = _github(api, "GET", f"/app/installations/{installation_id}", app_jwt)
    expected_permissions = {
        **manifest["organization_permissions"],
        **manifest["repository_permissions"],
    }
    if installation.get("target_type") != "Organization":
        raise LifecycleError("GitHub App installation target is not Organization")
    if installation.get("account", {}).get("login") != manifest["organization"]:
        raise LifecycleError("GitHub App organization differs from manifest")
    if installation.get("permissions") != expected_permissions:
        raise LifecycleError("GitHub App permissions differ from manifest")
    token_response = _github(
        api,
        "POST",
        f"/app/installations/{installation_id}/access_tokens",
        app_jwt,
        {"repositories": manifest["repositories"]},
    )
    installation_token = str(token_response.get("token", ""))
    if not installation_token:
        raise LifecycleError("GitHub installation token is missing")
    repositories = _github(api, "GET", "/installation/repositories?per_page=100", installation_token)
    observed = sorted(item["name"] for item in repositories.get("repositories", []))
    if observed != sorted(manifest["repositories"]):
        raise LifecycleError("GitHub App repositories differ from manifest")
    groups = _github(
        api,
        "GET",
        f"/orgs/{manifest['organization']}/actions/runner-groups?per_page=100",
        installation_token,
    )
    observed_groups = {item["name"] for item in groups.get("runner_groups", [])}
    missing_groups = sorted(set(manifest["runner_groups"].values()) - observed_groups)
    if missing_groups:
        raise LifecycleError("GitHub runner groups missing: " + ", ".join(missing_groups))
    return installation_token


def select_correlated_runner(
    runners: list[Mapping[str, Any]],
    *,
    expected_name: str,
    required_labels: set[str],
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in runners
        if item.get("name") == expected_name
        and required_labels.issubset(
            {str(label.get("name")) for label in item.get("labels", [])}
        )
    ]
    if len(matches) > 1:
        raise LifecycleError("runner cleanup selector is ambiguous")
    return matches[0] if matches else None


def deployment_job_is_terminal(jobs: list[Mapping[str, Any]], expected_name: str) -> bool:
    matches = [item for item in jobs if item.get("name") == expected_name]
    if len(matches) != 1:
        raise LifecycleError("private deployment job selector is ambiguous")
    return (
        matches[0].get("status") == "completed"
        and matches[0].get("conclusion") in TERMINAL_CONCLUSIONS
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0":
        raise LifecycleError("GitHub App manifest schema is invalid")
    return manifest


def _runner_group_id(
    api: JsonApi, organization: str, group_name: str, installation_token: str
) -> int:
    response = _github(
        api,
        "GET",
        f"/orgs/{organization}/actions/runner-groups?per_page=100",
        installation_token,
    )
    matches = [
        item for item in response.get("runner_groups", []) if item.get("name") == group_name
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("id"), int):
        raise LifecycleError("runner group selector is ambiguous")
    return int(matches[0]["id"])


def _execution_environment(execution: Mapping[str, Any]) -> dict[str, str]:
    containers = execution.get("properties", {}).get("template", {}).get("containers", [])
    if len(containers) != 1 or containers[0].get("name") != "runner":
        raise LifecycleError("ACA execution template is invalid")
    return {
        str(item.get("name")): str(item.get("value", ""))
        for item in containers[0].get("env", [])
    }


def _put_runner_secret(api: JsonApi, context: RunnerContext, token: str) -> None:
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    api.request(
        "PUT",
        f"{context.vault_url.rstrip('/')}/secrets/{context.token_secret_name}?api-version=7.4",
        resource=KEY_VAULT_RESOURCE,
        body={
            "value": token,
            "attributes": {"exp": int(expires.timestamp()), "enabled": True},
            "contentType": "application/vnd.waooaw.github-runner-registration-token",
            "tags": {"correlation": context.correlation, "environment": context.environment},
        },
    )


def read_runner_token(
    api: JsonApi,
    *,
    vault_url: str,
    secret_name: str,
    expected_correlation: str,
    now: int | None = None,
) -> str:
    response = api.request(
        "GET",
        f"{vault_url.rstrip('/')}/secrets/{secret_name}?api-version=7.4",
        resource=KEY_VAULT_RESOURCE,
    )
    attributes = response.get("attributes", {})
    expires = attributes.get("exp")
    observed_correlation = response.get("tags", {}).get("correlation")
    current_time = int(time.time() if now is None else now)
    if attributes.get("enabled") is not True or not isinstance(expires, int):
        raise LifecycleError("runner token secret attributes are invalid")
    if expires <= current_time or expires > current_time + 15 * 60:
        raise LifecycleError("runner token secret expiry is invalid")
    if observed_correlation != expected_correlation:
        raise LifecycleError("runner token secret correlation is invalid")
    token = str(response.get("value", ""))
    if not token:
        raise LifecycleError("runner token secret value is empty")
    return token


def _start_execution(api: JsonApi, context: RunnerContext) -> str:
    job_url = f"https://management.azure.com{context.job_resource_id}?api-version=2024-03-01"
    job = api.request("GET", job_url, resource=MANAGEMENT_RESOURCE)
    template = job.get("properties", {}).get("template", {})
    containers = template.get("containers", [])
    if len(containers) != 1 or containers[0].get("name") != "runner":
        raise LifecycleError("runner job template is invalid")
    override = json.loads(json.dumps(template))
    environment = {
        str(item["name"]): item
        for item in override["containers"][0].get("env", [])
    }
    for name, value in {
        "RUNNER_CORRELATION_ID": context.correlation,
        "RUNNER_NAME": context.runner_name,
        "RUNNER_GROUP": context.runner_group,
        "RUNNER_LABEL": context.runner_label,
        "GITHUB_ORGANIZATION": context.organization,
        "GITHUB_WORKFLOW_RUN_ID": context.run_id,
        "GITHUB_WORKFLOW_RUN_ATTEMPT": context.run_attempt,
    }.items():
        environment[name] = {"name": name, "value": value}
    override["containers"][0]["env"] = list(environment.values())
    execution = api.request(
        "POST",
        f"https://management.azure.com{context.job_resource_id}/start?api-version=2024-03-01",
        resource=MANAGEMENT_RESOURCE,
        body={"template": override},
    )
    execution_name = str((execution or {}).get("name", ""))
    if not execution_name:
        raise LifecycleError("ACA runner execution name is missing")
    return execution_name


def _assert_zero_active_executions(api: JsonApi, context: RunnerContext) -> None:
    response = api.request(
        "GET",
        (
            f"https://management.azure.com{context.job_resource_id}/executions"
            "?api-version=2024-03-01"
        ),
        resource=MANAGEMENT_RESOURCE,
    )
    active = [
        item.get("name")
        for item in response.get("value", [])
        if item.get("properties", {}).get("status") not in {"Succeeded", "Failed", "Stopped"}
    ]
    if active:
        raise LifecycleError("active ACA runner execution already exists")


def _find_correlated_execution(api: JsonApi, context: RunnerContext) -> str:
    response = api.request(
        "GET",
        (
            f"https://management.azure.com{context.job_resource_id}/executions"
            "?api-version=2024-03-01"
        ),
        resource=MANAGEMENT_RESOURCE,
    )
    matches: list[str] = []
    for item in response.get("value", []):
        execution_name = str(item.get("name", ""))
        if not execution_name:
            continue
        execution = api.request(
            "GET",
            (
                f"https://management.azure.com{context.job_resource_id}/executions/"
                f"{execution_name}?api-version=2024-03-01"
            ),
            resource=MANAGEMENT_RESOURCE,
        )
        if _execution_environment(execution).get("RUNNER_CORRELATION_ID") == context.correlation:
            matches.append(execution_name)
    if len(matches) != 1:
        raise LifecycleError("correlated ACA execution selector is ambiguous")
    return matches[0]


def start_runner(api: JsonApi, context: RunnerContext, manifest_path: Path) -> dict[str, Any]:
    manifest = _read_manifest(manifest_path)
    if manifest["organization"] != context.organization:
        raise LifecycleError("repository organization differs from App manifest")
    if manifest["runner_groups"].get(context.environment) != context.runner_group:
        raise LifecycleError("runner group differs from App manifest")
    app_jwt = create_app_jwt(
        context.app_id,
        context.app_key_id,
        lambda key_id, digest: key_vault_sign(api, key_id, digest),
    )
    installation_token = validate_installation(
        api, manifest, context.installation_id, app_jwt
    )
    group_id = _runner_group_id(
        api, context.organization, context.runner_group, installation_token
    )
    runners = _github(
        api,
        "GET",
        f"/orgs/{context.organization}/actions/runner-groups/{group_id}/runners?per_page=100",
        installation_token,
    ).get("runners", [])
    stale = [
        item.get("name")
        for item in runners
        if str(item.get("name", "")).startswith(f"goal006-{context.environment}-")
        or context.runner_label
        in {str(label.get("name")) for label in item.get("labels", [])}
    ]
    if stale:
        raise LifecycleError("environment runner registration already exists")
    _assert_zero_active_executions(api, context)
    registration = _github(
        api,
        "POST",
        f"/orgs/{context.organization}/actions/runners/registration-token",
        installation_token,
    )
    registration_token = str(registration.get("token", ""))
    if not registration_token:
        raise LifecycleError("runner registration token is missing")
    _put_runner_secret(api, context, registration_token)
    execution_name = _start_execution(api, context)
    return {
        "schema": "waooaw.goal006-runner-lifecycle/v1",
        "environment": context.environment,
        "correlation_id": context.correlation,
        "runner_name": context.runner_name,
        "runner_group": context.runner_group,
        "runner_label": context.runner_label,
        "workflow_run_id": context.run_id,
        "workflow_run_attempt": context.run_attempt,
        "aca_execution_name": execution_name,
        "token_secret_name": context.token_secret_name,
        "token_expires_within_minutes": 15,
    }


def cleanup_runner(
    api: JsonApi,
    context: RunnerContext,
    manifest_path: Path,
    lifecycle_record: Mapping[str, Any],
    private_job_conclusion: str,
) -> dict[str, Any]:
    expected = {
        "environment": context.environment,
        "correlation_id": context.correlation,
        "runner_name": context.runner_name,
        "runner_group": context.runner_group,
        "runner_label": context.runner_label,
        "workflow_run_id": context.run_id,
        "workflow_run_attempt": context.run_attempt,
        "token_secret_name": context.token_secret_name,
    }
    if any(lifecycle_record.get(name) != value for name, value in expected.items()):
        raise LifecycleError("lifecycle record differs from cleanup context")
    execution_name = str(lifecycle_record.get("aca_execution_name", ""))
    if not execution_name.startswith(f"{context.job_name}-"):
        raise LifecycleError("ACA execution name differs from runner job")

    manifest = _read_manifest(manifest_path)
    app_jwt = create_app_jwt(
        context.app_id,
        context.app_key_id,
        lambda key_id, digest: key_vault_sign(api, key_id, digest),
    )
    installation_token = validate_installation(
        api, manifest, context.installation_id, app_jwt
    )
    if private_job_conclusion not in TERMINAL_CONCLUSIONS:
        raise LifecycleError("private deployment job is not terminal")

    group_id = _runner_group_id(
        api, context.organization, context.runner_group, installation_token
    )
    runners_path = (
        f"/orgs/{context.organization}/actions/runner-groups/{group_id}/runners?per_page=100"
    )
    runners = _github(api, "GET", runners_path, installation_token).get("runners", [])
    runner = select_correlated_runner(
        runners,
        expected_name=context.runner_name,
        required_labels={
            context.runner_label,
            context.correlation,
            f"github-run-{context.run_id}",
        },
    )
    if runner is not None and runner.get("busy") is not False:
        raise LifecycleError("correlated runner still has a non-terminal job")

    execution_url = (
        f"https://management.azure.com{context.job_resource_id}/executions/"
        f"{execution_name}?api-version=2024-03-01"
    )
    execution = api.request("GET", execution_url, resource=MANAGEMENT_RESOURCE)
    if _execution_environment(execution).get("RUNNER_CORRELATION_ID") != context.correlation:
        raise LifecycleError("ACA execution correlation differs from lifecycle record")

    if runner is not None:
        _github(
            api,
            "DELETE",
            f"/orgs/{context.organization}/actions/runners/{runner['id']}",
            installation_token,
        )
    execution_status = str(execution.get("properties", {}).get("status", ""))
    if execution_status not in {"Succeeded", "Failed", "Stopped"}:
        api.request(
            "POST",
            execution_url.replace("?api-version", "/stop?api-version"),
            resource=MANAGEMENT_RESOURCE,
            body={},
        )
    api.request(
        "DELETE",
        f"{context.vault_url.rstrip('/')}/secrets/{context.token_secret_name}?api-version=7.4",
        resource=KEY_VAULT_RESOURCE,
    )

    remaining = _github(api, "GET", runners_path, installation_token).get("runners", [])
    if select_correlated_runner(
        remaining,
        expected_name=context.runner_name,
        required_labels={context.runner_label, context.correlation},
    ) is not None:
        raise LifecycleError("correlated runner registration remains after cleanup")
    refreshed_execution = api.request("GET", execution_url, resource=MANAGEMENT_RESOURCE)
    if str(refreshed_execution.get("properties", {}).get("status", "")) not in {
        "Succeeded",
        "Failed",
        "Stopped",
    }:
        raise LifecycleError("ACA runner execution remains active after cleanup")
    return {
        **expected,
        "schema": "waooaw.goal006-runner-cleanup/v1",
        "aca_execution_name": execution_name,
        "registration_absent": True,
        "execution_terminal": True,
        "token_secret_deleted": True,
    }


def cleanup_correlated_runner(
    api: JsonApi,
    context: RunnerContext,
    manifest_path: Path,
    private_job_conclusion: str,
) -> dict[str, Any]:
    lifecycle_record = {
        "environment": context.environment,
        "correlation_id": context.correlation,
        "runner_name": context.runner_name,
        "runner_group": context.runner_group,
        "runner_label": context.runner_label,
        "workflow_run_id": context.run_id,
        "workflow_run_attempt": context.run_attempt,
        "aca_execution_name": _find_correlated_execution(api, context),
        "token_secret_name": context.token_secret_name,
    }
    return cleanup_runner(
        api,
        context,
        manifest_path,
        lifecycle_record,
        private_job_conclusion,
    )


def _write_record(path: Path, record: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--app-manifest", type=Path, required=True)
    start_parser.add_argument("--output", type=Path, required=True)
    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--app-manifest", type=Path, required=True)
    cleanup_parser.add_argument("--lifecycle-record", type=Path, required=True)
    cleanup_parser.add_argument("--private-job-conclusion", required=True)
    cleanup_parser.add_argument("--output", type=Path, required=True)
    cleanup_correlated_parser = subparsers.add_parser("cleanup-correlated")
    cleanup_correlated_parser.add_argument("--app-manifest", type=Path, required=True)
    cleanup_correlated_parser.add_argument("--private-job-conclusion", required=True)
    cleanup_correlated_parser.add_argument("--output", type=Path, required=True)
    read_secret_parser = subparsers.add_parser("read-secret")
    read_secret_parser.add_argument("--vault-url", required=True)
    read_secret_parser.add_argument("--secret-name", required=True)
    read_secret_parser.add_argument("--correlation", required=True)
    args = parser.parse_args()
    if args.command == "start":
        context = RunnerContext.from_environment()
        record = start_runner(JsonApi(azure_access_token), context, args.app_manifest)
        _write_record(args.output, record)
        print(json.dumps({"started": True, "execution": record["aca_execution_name"]}))
    elif args.command == "cleanup":
        context = RunnerContext.from_environment()
        record = cleanup_runner(
            JsonApi(azure_access_token),
            context,
            args.app_manifest,
            json.loads(args.lifecycle_record.read_text(encoding="utf-8")),
            args.private_job_conclusion,
        )
        _write_record(args.output, record)
        print(json.dumps({"cleaned": True, "execution": record["aca_execution_name"]}))
    elif args.command == "cleanup-correlated":
        context = RunnerContext.from_environment()
        record = cleanup_correlated_runner(
            JsonApi(azure_access_token),
            context,
            args.app_manifest,
            args.private_job_conclusion,
        )
        _write_record(args.output, record)
        print(json.dumps({"cleaned": True, "execution": record["aca_execution_name"]}))
    elif args.command == "read-secret":
        print(
            read_runner_token(
                JsonApi(azure_access_token),
                vault_url=args.vault_url,
                secret_name=args.secret_name,
                expected_correlation=args.correlation,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())