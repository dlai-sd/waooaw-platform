#!/usr/bin/env python3
"""Protected Demo provider operations; never read credentials or send messages."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from goal006_azure_resource_id import canonical_container_app_id
from goal006_deployment_inputs import WHATSAPP_SECRET_NAMES, add_key_vault_references, whatsapp_provider_inputs
from goal006_demo_revision_cleanup import reconcile as reconcile_revisions
from wc120_whatsapp_activation import _read_json, activation_settings

ACCOUNT = "waooawp3tfstate2ed118"
CONTAINER = "deployment-config"
BLOB = "demo/workload-configuration.json"
GROUP = "waooaw-demo-rg"
APP = "ca-demo-business-platform"
HOST = "whatsapp-demo.waooaw.com"
IDENTITY = "id-demo-business-platform"
OPERATIONS = ("register", "activate", "stop", "status", "cleanup-intake")
TRAFFIC = {
    f"{section}__{flag}": "false"
    for section in ("WhatsApp", "Wc120Conversation")
    for flag in ("CallbackAcceptanceEnabled", "DispatchEnabled")
}
STOP = {**TRAFFIC, "WhatsAppCapability__ProviderAvailable": "false", "WhatsAppCapability__Revoked": "true"}


class ProviderCommandError(RuntimeError):
    def __init__(self, tool: str, stage: str, exit_code: int, stderr: str) -> None:
        reason = "COMMAND_FAILED"
        for marker, category in (
            ("staticcontainerapps", "RESOURCE_ID_CASE_MISMATCH"),
            ("authorizationfailed", "AUTHORIZATION_DENIED"),
            ("forbiddenbyrbac", "AUTHORIZATION_DENIED"),
            ("error acquiring the state lock", "STATE_LOCK_FAILED"),
            ("cannot import non-existent remote object", "REMOTE_OBJECT_NOT_FOUND"),
            ("resource already managed by terraform", "RESOURCE_ALREADY_MANAGED"),
            ("invalid for_each argument", "CONFIGURATION_INVALID"),
            ("invalid count argument", "CONFIGURATION_INVALID"),
        ):
            if marker in stderr.lower():
                reason = category
                break
        self.details = {"tool": tool, "stage": stage, "exit_code": exit_code, "reason": reason}
        super().__init__(f"{tool} {stage} failed: {reason} (exit {exit_code})")


def az(*args: str) -> Any:
    executable = shutil.which("az")
    if executable is None:
        raise RuntimeError("Azure CLI is required")
    result = subprocess.run(  # noqa: S603 - fixed CLI, argument vector only; no shell evaluation
        [executable, *args, "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        stage = {
            ("containerapp", "show"): "APP_READ",
            ("identity", "show"): "IDENTITY_READ",
            ("role", "assignment"): "ROLE_ASSIGNMENT",
        }.get(args[:2], "AZURE_OPERATION")
        raise ProviderCommandError("azure", stage, result.returncode, result.stderr)
    return json.loads(result.stdout) if result.stdout.strip() else None


def private_json(path: Path, value: Any) -> None:
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        json.dump(value, stream, sort_keys=True)


def app() -> dict[str, Any]:
    return az("containerapp", "show", "--resource-group", GROUP, "--name", APP)


def bp_container(resource: dict[str, Any]) -> dict[str, Any]:
    containers = resource["properties"]["template"]["containers"]
    if len(containers) != 1:
        raise ValueError("Expected the existing single-container Business Platform")
    image = containers[0]["image"]
    if (
        re.fullmatch(
            r"(?:ghcr.io|acrwaooawdemo[0-9a-f]{6}\.azurecr\.io)/dlai-sd/business-platform@sha256:[0-9a-f]{64}",
            image,
        )
        is None
    ):
        raise ValueError("Business Platform image must be an admitted immutable digest")
    return containers[0]


def environment(resource: dict[str, Any]) -> dict[str, str]:
    return {entry["name"]: entry.get("value", "") for entry in bp_container(resource).get("env", [])}


def registration_settings(provider: dict[str, Any], client_id: str) -> dict[str, str]:
    if provider["callback_host"] != HOST:
        raise ValueError("Provider operation requires the approved dedicated callback")
    return {
        **STOP,
        "WhatsAppProvider__Enabled": "true",
        "WhatsAppProvider__Environment": "demo",
        "WhatsAppProvider__VaultHost": "kv-waooaw-demo.vault.azure.net",
        "WhatsAppProvider__ManagedIdentityClientId": client_id,
        **{
            f"WhatsAppProvider__{key}Version": provider["secret_versions"][name]
            for key, name in (
                ("Binding", "whatsapp-provider-binding"),
                ("VerifyToken", "whatsapp-verify-token"),
                ("AppSecret", "whatsapp-app-secret"),
                ("OutboundAuthority", "whatsapp-outbound-authority"),
            )
        },
        "WhatsApp__CallbackHost": HOST,
        "WhatsApp__VerificationEnabled": str(provider["verification_enabled"]).lower(),
        "WhatsAppCapability__Configured": "true",
        "WhatsAppCapability__Environment": "demo",
        **{
            f"WhatsAppCapability__{key}": provider[field]
            for key, field in (
                ("ReleaseDigest", "release_digest"),
                ("ConfigurationDigest", "configuration_digest"),
                ("CatalogDigest", "catalog_digest"),
            )
        },
    }


def deployment(configuration: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    resource_id = resource["id"]
    match = re.fullmatch(
        rf"(?P<root>/subscriptions/[0-9a-f-]{{36}}/resourceGroups/{GROUP})/providers/Microsoft.App/containerApps/{APP}",
        resource_id,
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Provider references require the existing Demo Business Platform resource")
    root = match["root"]
    vault_id = root + "/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo"
    resolved = add_key_vault_references(configuration, vault_id, "https://kv-waooaw-demo.vault.azure.net/")
    for field in ("key_vault_secret_uris", "key_vault_secret_resource_ids"):
        if field in configuration and configuration[field] != resolved[field]:
            raise ValueError("Stored vault references differ from the Demo foundation")
    images = {"business-platform": bp_container(resource)["image"]}
    return {
        **resolved,
        "image_digests": images,
        **whatsapp_provider_inputs("demo", resolved, {"images": images}),
    }


def planned_settings(
    operation: str,
    document: bytes,
    approved_digest: str,
    configuration: dict[str, Any],
    resource: dict[str, Any],
    client_id: str,
    now: datetime,
) -> tuple[dict[str, Any], dict[str, str]]:
    if operation not in OPERATIONS:
        raise ValueError("Unknown provider operation")
    updated = dict(configuration)
    if operation == "register":
        if approved_digest:
            raise ValueError("Registration does not accept activation approval")
        if any(environment(resource).get(key, "").lower() == "true" for key in TRAFFIC):
            raise ValueError("Stop existing traffic before changing provider registration")
        domains = resource["properties"]["configuration"]["ingress"].get("customDomains", [])
        if not any(value["name"] == HOST and value.get("bindingType") == "SniEnabled" for value in domains):
            raise ValueError("Dedicated callback DNS and managed TLS binding must already be ready")
        updated["whatsapp_provider"] = _read_json(document)
        provider = deployment(updated, resource)["whatsapp_provider"]
        if provider["verification_enabled"] is not True:
            raise ValueError("Registration operation requires verification-only enablement")
        return updated, registration_settings(provider, client_id)
    if operation == "activate":
        return updated, activation_settings(document, approved_digest, deployment(updated, resource), now)
    if document.strip() not in (b"", b"{}") or approved_digest:
        raise ValueError("This operation accepts no configuration document or approval digest")
    return updated, dict(STOP) if operation == "stop" else {}


def blob_args(name: str = BLOB) -> list[str]:
    return ["--account-name", ACCOUNT, "--container-name", CONTAINER, "--name", name, "--auth-mode", "login"]


def prepare(directory: Path, operation: str, document: bytes, approved_digest: str) -> None:
    resource = app()
    before = ""
    configuration: dict[str, Any] = {}
    if operation in ("register", "activate", "status"):
        before = az("storage", "blob", "show", *blob_args())["properties"]["etag"]
        target = directory / "configuration.download.json"
        az("storage", "blob", "download", *blob_args(), "--file", str(target), "--if-match", before)
        target.chmod(0o600)
        _read_json(target.read_bytes())
        configuration = json.loads(target.read_bytes())
    identity = az("identity", "show", "--resource-group", GROUP, "--name", IDENTITY)
    updated, settings = planned_settings(
        operation, document, approved_digest, configuration, resource, identity["clientId"], datetime.now(timezone.utc)
    )
    private_json(directory / "configuration.before.json", configuration)
    private_json(directory / "configuration.after.json", updated)
    private_json(
        directory / "plan.json",
        {
            "operation": operation,
            "etag": before,
            "image": bp_container(resource)["image"],
            "settings": settings,
            "principal_id": identity["principalId"],
            "approved_digest": approved_digest,
        },
    )
    # Persist the complete validated metadata document for exact revalidation at apply.
    (directory / "document.raw").write_bytes(document)
    (directory / "document.raw").chmod(0o600)


def persist(directory: Path, run: str) -> None:
    plan = _read_json((directory / "plan.json").read_bytes())
    if plan["operation"] != "register":
        return
    before = _read_json((directory / "configuration.before.json").read_bytes())
    after = _read_json((directory / "configuration.after.json").read_bytes())
    if before == after:
        if az("storage", "blob", "show", *blob_args())["properties"]["etag"] != plan["etag"]:
            raise RuntimeError("Configuration changed after preparation")
        return
    if re.fullmatch(r"[0-9]+-[0-9]+", run) is None:
        raise ValueError("Operation evidence requires workflow run and attempt")
    az(
        "storage",
        "blob",
        "upload",
        *blob_args(f"demo/whatsapp-operations/{run}/configuration.before.json"),
        "--file",
        str(directory / "configuration.before.json"),
        "--overwrite",
        "false",
    )
    az(
        "storage",
        "blob",
        "upload",
        *blob_args(),
        "--file",
        str(directory / "configuration.after.json"),
        "--overwrite",
        "true",
        "--if-match",
        plan["etag"],
    )
    # An interrupted operation leaves explicit staged registration, never traffic authority.
    actual = az("storage", "blob", "show", *blob_args())["properties"]["etag"]
    target = directory / "configuration.verified.json"
    az("storage", "blob", "download", *blob_args(), "--file", str(target), "--if-match", actual)
    target.chmod(0o600)
    if _read_json(target.read_bytes()) != after:
        raise RuntimeError("Stored configuration differs from the validated registration")


def apply_settings(directory: Path) -> None:
    plan = _read_json((directory / "plan.json").read_bytes())
    resource = app()
    if bp_container(resource)["image"] != plan["image"]:
        raise ValueError("Deployed image changed after provider preparation")
    configuration = _read_json((directory / "configuration.after.json").read_bytes())
    identity = az("identity", "show", "--resource-group", GROUP, "--name", IDENTITY)
    if identity["principalId"] != plan["principal_id"]:
        raise ValueError("Business Platform identity changed after preparation")
    if plan["operation"] in ("register", "activate", "status"):
        etag = az("storage", "blob", "show", *blob_args())["properties"]["etag"]
        target = directory / "configuration.apply.json"
        az("storage", "blob", "download", *blob_args(), "--file", str(target), "--if-match", etag)
        target.chmod(0o600)
        if _read_json(target.read_bytes()) != configuration:
            raise RuntimeError("Authoritative configuration changed before runtime application")
    _, settings = planned_settings(
        plan["operation"],
        (directory / "document.raw").read_bytes(),
        plan["approved_digest"],
        configuration,
        resource,
        identity["clientId"],
        datetime.now(timezone.utc),
    )
    if settings != plan["settings"]:
        raise ValueError("Prepared runtime settings changed")
    if plan["operation"] == "activate":
        registered = registration_settings(deployment(configuration, resource)["whatsapp_provider"], identity["clientId"])
        current = environment(resource)
        for key, expected in registered.items():
            if key not in STOP and current.get(key) != expected:
                raise ValueError("Runtime does not match the registered deployment")
    if plan["operation"] in ("register", "activate") or (plan["operation"] == "status" and "whatsapp_provider" in configuration):
        if plan["operation"] == "status":
            deployment(configuration, resource)
        validate_versions(configuration["whatsapp_provider"]["secret_versions"], datetime.now(timezone.utc))
    if plan["operation"] == "status":
        return
    if plan["operation"] == "register":
        resolved = deployment(configuration, resource)
        scope_root = next(iter(resolved["key_vault_secret_resource_ids"].values())).split("/secrets/", 1)[0]
        for name in sorted(WHATSAPP_SECRET_NAMES):
            scope = f"{scope_root}/secrets/{name}"
            assignments = az(
                "role",
                "assignment",
                "list",
                "--assignee-object-id",
                plan["principal_id"],
                "--fill-principal-name",
                "false",
                "--scope",
                scope,
            )
            if not any(value["roleDefinitionName"] == "Key Vault Secrets User" for value in assignments):
                az(
                    "role",
                    "assignment",
                    "create",
                    "--assignee-object-id",
                    plan["principal_id"],
                    "--assignee-principal-type",
                    "ServicePrincipal",
                    "--role",
                    "Key Vault Secrets User",
                    "--scope",
                    scope,
                )
    if settings:
        current = environment(resource)
        obsolete = [
            key
            for key in current
            if key not in settings
            and key.startswith(
                ("WhatsApp__ApprovedTemplates__", "WhatsApp__TemplateProjections__", "WhatsAppCapability__Authority__")
            )
        ]
        args = [
            "containerapp",
            "update",
            "--resource-group",
            GROUP,
            "--name",
            APP,
            "--set-env-vars",
            *(f"{key}={value}" for key, value in sorted(settings.items())),
        ]
        if obsolete:
            args.extend(["--remove-env-vars", *obsolete])
        az(*args)
        for _ in range(60):
            actual = app()
            if (
                bp_container(actual)["image"] == plan["image"]
                and all(environment(actual).get(key) == value for key, value in settings.items())
                and not any(key in environment(actual) for key in obsolete)
                and actual["properties"]["latestReadyRevisionName"] == actual["properties"]["latestRevisionName"]
            ):
                reconcile_revisions(GROUP, apply=True, selected_apps=[APP], run_az=lambda argv: az(*argv))
                return
            time.sleep(5)
        raise RuntimeError("Provider runtime revision did not become ready with the exact settings")


def validate_versions(versions: dict[str, str], now: datetime) -> None:
    for name, version in sorted(versions.items()):
        url = f"https://kv-waooaw-demo.vault.azure.net/secrets/{name}/versions?api-version=7.4"
        found = None
        for _ in range(64):
            result = az("rest", "--method", "get", "--resource", "https://vault.azure.net", "--url", url)
            found = next((value for value in result["value"] if value["id"].rsplit("/", 1)[-1] == version), None)
            if found is not None or not result.get("nextLink"):
                break
            url = result["nextLink"]
            if not url.startswith(f"https://kv-waooaw-demo.vault.azure.net/secrets/{name}/versions?"):
                raise ValueError("Unexpected credential metadata pagination URL")
        if found is None:
            raise ValueError(f"Exact credential version is absent: {name}")
        attributes = found["attributes"]
        expiry = attributes.get("exp")
        start = attributes.get("nbf")
        if (
            attributes.get("enabled") is not True
            or (start is not None and (type(start) is not int or start > now.timestamp()))
            or (expiry is None and name != "whatsapp-outbound-authority")
            or (expiry is not None and (type(expiry) is not int or expiry <= now.timestamp()))
        ):
            raise ValueError(f"Credential metadata validity denied: {name}")


def probe_callback(operation: str) -> None:
    if operation not in ("register", "status"):
        return
    url = f"https://{HOST}/api/v1/channels/whatsapp/webhook"
    invalid = os.urandom(32).hex()
    request = urllib.request.Request(  # noqa: S310 - fixed first-party HTTPS hostname
        f"{url}?hub.mode=subscribe&hub.challenge=readiness&hub.verify_token={invalid}"
    )
    for attempt in range(30 if operation == "register" else 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed first-party HTTPS hostname
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
        if status == 401:
            break
        if status != 503 or attempt == 29 or operation == "status":
            raise RuntimeError("TLS callback is not rejecting an invalid verification token as expected")
        time.sleep(5)
    if operation == "register":
        request = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed first-party HTTPS hostname
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
        if status != 503:
            raise RuntimeError("Registration callback acceptance is not disabled")


def cleanup_intake() -> None:
    group, name = "waooaw-demo-runner-rg", "goal006-demo-runner-key-import"
    identity = az("identity", "show", "--resource-group", group, "--name", f"{name}-identity")
    vault = az("keyvault", "show", "--resource-group", GROUP, "--name", "kv-waooaw-demo")
    for secret in sorted(WHATSAPP_SECRET_NAMES):
        scope = f"{vault['id']}/secrets/{secret}"
        assignments = az(
            "role",
            "assignment",
            "list",
            "--assignee-object-id",
            identity["principalId"],
            "--fill-principal-name",
            "false",
            "--scope",
            scope,
        )
        for assignment in assignments:
            if (
                assignment["roleDefinitionName"] == "WAOOAW Key Vault Declared Secret Provisioner"
                and assignment["scope"].lower() == scope.lower()
            ):
                az("role", "assignment", "delete", "--ids", assignment["id"])
        remaining = az(
            "role",
            "assignment",
            "list",
            "--assignee-object-id",
            identity["principalId"],
            "--fill-principal-name",
            "false",
            "--scope",
            scope,
        )
        if any(value["roleDefinitionName"] == "WAOOAW Key Vault Declared Secret Provisioner" for value in remaining):
            raise RuntimeError("Intake secret grant revocation was not confirmed")
    az("containerapp", "update", "--resource-group", group, "--name", name, "--min-replicas", "0", "--max-replicas", "1")
    for revision in az("containerapp", "revision", "list", "--resource-group", group, "--name", name, "--all"):
        if revision["properties"]["active"]:
            az(
                "containerapp",
                "revision",
                "deactivate",
                "--resource-group",
                group,
                "--name",
                name,
                "--revision",
                revision["name"],
            )
            deadline = time.monotonic() + 120
            while True:
                observed = az(
                    "containerapp",
                    "revision",
                    "show",
                    "--resource-group",
                    group,
                    "--name",
                    name,
                    "--revision",
                    revision["name"],
                )["properties"]
                if observed.get("active") is False and observed.get("replicas") == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Private intake revision still has active replicas")
                time.sleep(5)
    if any(
        value["properties"]["active"]
        for value in az(
            "containerapp",
            "revision",
            "list",
            "--resource-group",
            group,
            "--name",
            name,
        )
    ):
        raise RuntimeError("Private intake revision shutdown was not confirmed")


def terraform(*args: str) -> str:
    executable = shutil.which("terraform")
    if executable is None:
        raise RuntimeError("Terraform is required for state adoption")
    result = subprocess.run(  # noqa: S603 - fixed Terraform CLI and validated resource addresses, no shell
        [executable, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        command = args[1:] if args[0].startswith("-chdir=") else args
        stage = "STATE_LIST" if command[:2] == ("state", "list") else "IMPORT"
        raise ProviderCommandError("terraform", stage, result.returncode, result.stderr)
    return result.stdout


def adopt(directory: Path) -> None:
    configuration = _read_json((directory / "workload.auto.tfvars.json").read_bytes())
    if configuration.get("whatsapp_provider") is None:
        return
    resource = app()
    registration_keys = ("callback_host", "secret_versions", "authority_reference", "verification_enabled")
    registration = {key: configuration["whatsapp_provider"][key] for key in registration_keys}
    provider = deployment({**configuration, "whatsapp_provider": registration}, resource)["whatsapp_provider"]
    identity = az("identity", "show", "--resource-group", GROUP, "--name", IDENTITY)
    state = set(terraform(f"-chdir={directory}", "state", "list").splitlines())
    imports: dict[str, str] = {}
    if any(
        value["name"] == provider["callback_host"]
        for value in resource["properties"]["configuration"]["ingress"].get("customDomains", [])
    ):
        app_id = canonical_container_app_id(resource["id"], expected_resource_group=GROUP, expected_name=APP)
        imports["module.workload.azurerm_container_app_custom_domain.whatsapp_provider[0]"] = (
            app_id + "/customDomainName/" + provider["callback_host"]
        )
    vault = next(iter(configuration["key_vault_secret_resource_ids"].values())).split("/secrets/", 1)[0]
    for name in sorted(WHATSAPP_SECRET_NAMES):
        scope = f"{vault}/secrets/{name}"
        matches = [
            value
            for value in az(
                "role",
                "assignment",
                "list",
                "--assignee-object-id",
                identity["principalId"],
                "--fill-principal-name",
                "false",
                "--scope",
                scope,
            )
            if value["roleDefinitionName"] == "Key Vault Secrets User"
            and value["scope"].lower() == scope.lower()
            and value["principalId"].lower() == identity["principalId"].lower()
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous existing provider secret role assignments")
        if matches:
            imports[f'module.workload.azurerm_role_assignment.whatsapp_provider_secret["{name}"]'] = matches[0]["id"]
    for address, resource_id in imports.items():
        if address not in state:
            terraform(f"-chdir={directory}", "import", "-input=false", "-lock-timeout=5m", address, resource_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "persist", "apply", "cleanup-intake", "adopt"))
    parser.add_argument("--operation", choices=OPERATIONS, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--approved-digest", default="")
    args = parser.parse_args()
    args.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.umask(0o077)
    evidence = {"schema": "waooaw.whatsapp-operation/v1", "operation": args.operation, "phase": args.phase, "status": "FAILED"}
    try:
        if args.phase == "adopt":
            adopt(args.directory)
        elif args.phase == "cleanup-intake":
            if args.operation != "cleanup-intake":
                raise ValueError("Cleanup requires its own explicit Founder operation")
            if os.environ.get("PROVIDER_DOCUMENT", "{}").strip() not in ("", "{}") or args.approved_digest:
                raise ValueError("Cleanup accepts no configuration document or activation approval")
            cleanup_intake()
        elif args.phase == "prepare":
            prepare(args.directory, args.operation, os.environ.get("PROVIDER_DOCUMENT", "{}").encode(), args.approved_digest)
        elif args.phase == "persist":
            persist(args.directory, args.run)
        else:
            if _read_json((args.directory / "plan.json").read_bytes())["operation"] != args.operation:
                raise ValueError("Apply operation differs from its prepared plan")
            apply_settings(args.directory)
            probe_callback(args.operation)
            current = app()
            evidence["image"] = bp_container(current)["image"]
            evidence["traffic_flags"] = {key: environment(current).get(key, "false") for key in STOP}
            evidence["verification_enabled"] = environment(current).get("WhatsApp__VerificationEnabled", "false")
            if args.operation == "status" and "whatsapp_provider" not in _read_json(
                (args.directory / "configuration.after.json").read_bytes()
            ):
                evidence["credential_metadata"] = "NOT_CONFIGURED"
                evidence["missing_activation_groups"] = ["REGISTRATION"]
                evidence["activation_approval_verified"] = False
            elif args.operation == "status":
                configuration = _read_json((args.directory / "configuration.after.json").read_bytes())
                identity = az("identity", "show", "--resource-group", GROUP, "--name", IDENTITY)
                registered = deployment(configuration, current)["whatsapp_provider"]
                expected = registration_settings(registered, identity["clientId"])
                actual = environment(current)
                evidence["registration"] = {
                    key: registered[key] for key in ("release_digest", "configuration_digest", "catalog_digest")
                }
                evidence["registration_runtime_matches"] = all(
                    actual.get(key) == value
                    for key, value in expected.items()
                    if key not in STOP and key != "WhatsAppCapability__ConfigurationDigest"
                )
                evidence["credential_metadata"] = "READY"
                groups = {
                    "AUTHORITY": any(key.startswith("WhatsAppCapability__Authority__") for key in actual),
                    "POLICIES": all(
                        actual.get(f"Wc120Conversation__{key}")
                        for key in (
                            "PolicyVersion",
                            "InstitutionalPolicyVersion",
                            "InteractionPolicyVersion",
                            "ChannelRenderingPolicyVersion",
                        )
                    ),
                    "TEMPLATES": any(key.startswith("WhatsApp__TemplateProjections__") for key in actual),
                    "ROLLBACK": bool(actual.get("WhatsAppCapability__RollbackDigest")),
                }
                evidence["missing_activation_groups"] = sorted(key for key, present in groups.items() if not present)
                evidence["activation_approval_verified"] = False
        evidence["status"] = "PASS"
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        evidence["error_type"] = type(error).__name__
        trace = error.__traceback__
        while trace is not None:
            if Path(trace.tb_frame.f_code.co_filename).parent == Path(__file__).parent:
                evidence["failure_location"] = {
                    "file": Path(trace.tb_frame.f_code.co_filename).name,
                    "function": trace.tb_frame.f_code.co_name,
                    "line": trace.tb_lineno,
                }
            trace = trace.tb_next
        if isinstance(error, (ValueError, RuntimeError)):
            evidence["reason"] = str(error)
        if isinstance(error, ProviderCommandError):
            evidence["command_failure"] = error.details
            print(json.dumps({"provider_command_failure": error.details}, sort_keys=True))
        if args.operation == "activate" and args.phase == "apply":
            try:
                az(
                    "containerapp",
                    "update",
                    "--resource-group",
                    GROUP,
                    "--name",
                    APP,
                    "--set-env-vars",
                    *(f"{key}={value}" for key, value in sorted(STOP.items())),
                )
                current = app()
                if (
                    any(environment(current).get(key) != value for key, value in STOP.items())
                    or current["properties"]["latestReadyRevisionName"] != current["properties"]["latestRevisionName"]
                ):
                    raise RuntimeError("Traffic closure was not confirmed")
                reconcile_revisions(GROUP, apply=True, selected_apps=[APP], run_az=lambda argv: az(*argv))
                evidence["containment"] = "TRAFFIC_CLOSED"
            except (ValueError, KeyError, OSError, RuntimeError):
                evidence["containment"] = "UNCONFIRMED_REQUIRES_OPERATOR"
                print("CRITICAL: activation failure containment is unconfirmed; explicitly stop the provider.")
        print(f"Provider operation denied or failed ({type(error).__name__}); inspect redacted phase evidence.")
        return_code = 1
    else:
        return_code = 0
    private_json(args.directory / f"evidence-{args.phase}.json", evidence)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
