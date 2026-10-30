#!/usr/bin/env python3
"""Mirror immutable GHCR images into an environment ACR and select the deployment image home (WC-127).

Images are copied client-side with ``docker buildx imagetools create`` from a GitHub-hosted runner,
which reads GHCR quickly and preserves the exact index digest. A copy only counts once ACR serves the
index digest and every child manifest, because Azure Container Apps resolves the platform manifest when
an app or job is created or updated.

Image homes:
  github  pull from GHCR; no registry calls are made.
  azure   every image must be present in ACR (copying any that are missing); otherwise fail.
  both    as azure, but any registry or copy failure falls back to GHCR with a warning.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

IMAGE_HOMES = ("github", "azure", "both")
GHCR_IMAGE = re.compile(r"^ghcr[.]io/(?P<repository>[a-z0-9]+(?:[._/-][a-z0-9]+)*)@(?P<digest>sha256:[0-9a-f]{64})$")
LOGIN_SERVER = re.compile(r"^acrwaooaw(?P<environment>demo|uat|prod)[0-9a-f]{6}[.]azurecr[.]io$")
PULL_IDENTITY = re.compile(
    r"^/subscriptions/[0-9a-f-]{36}/resourceGroups/waooaw-(?P<rg>demo|uat|prod)-rg/providers/"
    r"Microsoft[.]ManagedIdentity/userAssignedIdentities/id-waooaw-(?P<name>demo|uat|prod)-image-pull$",
    re.IGNORECASE,
)
INDEX_MEDIA_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}

Runner = Callable[..., subprocess.CompletedProcess[str]]
TokenSource = Callable[[], str]
MIRROR_CONFIG_SCHEMA = "waooaw.acr-mirrors/v1"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ACR_TOKEN_USER = "00000000-0000-0000-0000-000000000000"  # noqa: S105 - fixed ACR token username


class MirrorError(RuntimeError):
    pass


def run_command(arguments: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(arguments), input=input_text, capture_output=True, text=True, check=False, timeout=600)  # noqa: S603


def parse_source(image: str) -> tuple[str, str]:
    match = GHCR_IMAGE.fullmatch(image)
    if match is None:
        raise ValueError(f"image must be an immutable GHCR digest reference: {image}")
    return match["repository"], match["digest"]


def target_reference(login_server: str, image: str) -> str:
    repository, digest = parse_source(image)
    return f"{login_server}/{repository}@{digest}"


def _last_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    return lines[-1][:300] if lines else f"exit {result.returncode}"


def _raw_manifest(reference: str, run: Runner) -> dict[str, Any] | None:
    result = run(["docker", "buildx", "imagetools", "inspect", "--raw", reference])
    if result.returncode != 0:
        return None
    try:
        manifest = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return manifest if isinstance(manifest, dict) else None


def is_complete(login_server: str, image: str, run: Runner) -> bool:
    """Return True only when ACR serves the index digest and every child manifest it references."""
    repository, digest = parse_source(image)
    base = f"{login_server}/{repository}"
    manifest = _raw_manifest(f"{base}@{digest}", run)
    if manifest is None:
        return False
    if manifest.get("mediaType") not in INDEX_MEDIA_TYPES:
        return True
    children = manifest.get("manifests")
    if not isinstance(children, list) or not children:
        return False
    for child in children:
        child_digest = child.get("digest") if isinstance(child, dict) else None
        if not isinstance(child_digest, str) or _raw_manifest(f"{base}@{child_digest}", run) is None:
            return False
    return True


def copy_image(
    login_server: str,
    image: str,
    run: Runner,
    *,
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    repository, digest = parse_source(image)
    started = clock()
    if is_complete(login_server, image, run):
        return {"source": image, "target": target_reference(login_server, image), "copied": False, "seconds": 0.0}
    tag = f"{login_server}/{repository}:{digest.replace(':', '-')}"
    last_error = ""
    for attempt in range(1, attempts + 1):
        result = run(["docker", "buildx", "imagetools", "create", "--tag", tag, image])
        if result.returncode == 0 and is_complete(login_server, image, run):
            return {
                "source": image,
                "target": target_reference(login_server, image),
                "copied": True,
                "seconds": round(clock() - started, 1),
            }
        last_error = _last_line(result) if result.returncode != 0 else "copied index is incomplete in the registry"
        if attempt < attempts:
            sleep(10 * attempt)
    raise MirrorError(f"{repository}@{digest} could not be mirrored to {login_server}: {last_error}")


def mirror_images(
    login_server: str,
    images: Mapping[str, str],
    run: Runner = run_command,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    if LOGIN_SERVER.fullmatch(login_server) is None:
        raise ValueError("login server must be an environment WAOOAW ACR")
    for image in images.values():
        parse_source(image)
    records = []
    for name in sorted(images):
        record = copy_image(login_server, images[name], run, sleep=sleep)
        record["member"] = name
        records.append(record)
    return records


def select_image_home(
    *,
    image_home: str,
    images: Mapping[str, str],
    login_server: str,
    pull_identity_id: str,
    registry_ready: bool,
    run: Runner = run_command,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    if image_home not in IMAGE_HOMES:
        raise ValueError("image_home must be github, azure, or both")
    for image in images.values():
        parse_source(image)
    evidence: dict[str, Any] = {
        "requested_image_home": image_home,
        "effective_image_home": "github",
        "registry_server": "",
        "pull_identity_id": "",
        "fallback_reason": "",
        "mirrored": [],
        "references": dict(images),
        "started_at": now().isoformat(),
    }
    if image_home == "github":
        evidence["completed_at"] = now().isoformat()
        return evidence
    try:
        if not registry_ready:
            raise MirrorError(
                "environment ACR or image-pull identity does not exist yet; "
                "run once with image_home=github or both so the foundation creates them"
            )
        server = LOGIN_SERVER.fullmatch(login_server)
        if server is None:
            raise ValueError("login server must be an environment WAOOAW ACR")
        identity = PULL_IDENTITY.fullmatch(pull_identity_id)
        environment = server["environment"]
        if identity is None or identity["rg"].lower() != environment or identity["name"].lower() != environment:
            raise ValueError("pull identity must be the environment image-pull managed identity")
        evidence["mirrored"] = mirror_images(login_server, images, run, sleep=sleep)
    except (MirrorError, ValueError, subprocess.TimeoutExpired) as error:
        if image_home == "azure":
            raise MirrorError(str(error)) from error
        evidence["fallback_reason"] = str(error)
        evidence["completed_at"] = now().isoformat()
        return evidence
    evidence.update(
        {
            "effective_image_home": "azure",
            "registry_server": login_server,
            "pull_identity_id": pull_identity_id,
            "references": {name: target_reference(login_server, image) for name, image in images.items()},
            "completed_at": now().isoformat(),
        }
    )
    return evidence


def load_mirror_targets(config: Mapping[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """Return the tenant and every environment ACR that has a recorded CI publish identity."""
    if config.get("schema") != MIRROR_CONFIG_SCHEMA:
        raise ValueError(f"mirror configuration schema must be {MIRROR_CONFIG_SCHEMA}")
    tenant_id = config.get("tenant_id")
    environments = config.get("environments")
    if not isinstance(tenant_id, str) or UUID.fullmatch(tenant_id) is None or not isinstance(environments, dict):
        raise ValueError("mirror configuration requires tenant_id and environments")
    targets = []
    for environment in sorted(environments):
        record = environments[environment]
        if environment not in {"demo", "uat", "prod"} or not isinstance(record, dict):
            raise ValueError(f"unknown mirror environment {environment}")
        login_server = record.get("login_server")
        server = LOGIN_SERVER.fullmatch(login_server) if isinstance(login_server, str) else None
        if server is None or server["environment"] != environment:
            raise ValueError(f"{environment} login_server must be that environment's WAOOAW ACR")
        client_id = record.get("publish_client_id")
        if client_id is None:
            continue
        if not isinstance(client_id, str) or UUID.fullmatch(client_id) is None:
            raise ValueError(f"{environment} publish_client_id must be a client ID or null")
        targets.append({"environment": environment, "login_server": login_server, "client_id": client_id})
    return tenant_id, targets


def github_oidc_token() -> str:
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    bearer = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not bearer or not url.startswith("https://"):
        raise MirrorError("GitHub OIDC is unavailable; the job needs id-token: write")
    request = Request(f"{url}&audience=api://AzureADTokenExchange", headers={"Authorization": f"bearer {bearer}"})  # noqa: S310
    with urlopen(request, timeout=30) as response:  # noqa: S310 - GitHub Actions OIDC endpoint
        token = json.load(response).get("value")
    if not isinstance(token, str) or not token:
        raise MirrorError("GitHub OIDC returned no token")
    return token


def _checked(result: subprocess.CompletedProcess[str], action: str) -> subprocess.CompletedProcess[str]:
    if result.returncode != 0:
        raise MirrorError(f"{action} failed: {_last_line(result)}")
    return result


def login_registry(target: Mapping[str, str], tenant_id: str, run: Runner, token_source: TokenSource) -> None:
    _checked(
        run(
            [
                "az",
                "login",
                "--service-principal",
                "--username",
                target["client_id"],
                "--tenant",
                tenant_id,
                "--federated-token",
                token_source(),
                "--allow-no-subscriptions",
                "--output",
                "none",
            ]
        ),
        "Azure login with the image publish identity",
    )
    registry_name = target["login_server"].split(".", 1)[0]
    token = _checked(
        run(["az", "acr", "login", "--name", registry_name, "--expose-token", "--output", "tsv", "--query", "accessToken"]),
        "ACR token exchange",
    ).stdout.strip()
    if not token:
        raise MirrorError("ACR token exchange returned no token")
    _checked(
        run(["docker", "login", target["login_server"], "--username", ACR_TOKEN_USER, "--password-stdin"], token),
        "docker login to ACR",
    )


def publish_to_mirrors(
    config: Mapping[str, Any],
    images: Mapping[str, str],
    run: Runner = run_command,
    *,
    token_source: TokenSource = github_oidc_token,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Copy freshly published GHCR images to every configured environment ACR; failures never raise."""
    tenant_id, targets = load_mirror_targets(config)
    for image in images.values():
        parse_source(image)
    results = []
    for target in targets:
        record: dict[str, Any] = {"environment": target["environment"], "login_server": target["login_server"]}
        try:
            login_registry(target, tenant_id, run, token_source)
            record["mirrored"] = mirror_images(target["login_server"], images, run, sleep=sleep)
            record["status"] = "succeeded"
        except (MirrorError, subprocess.TimeoutExpired, OSError) as error:
            record["status"] = "failed"
            record["error"] = str(error)
        finally:
            run(["docker", "logout", target["login_server"]])
            run(["az", "logout"])
        results.append(record)
    return {"targets": results}


def _named_images(values: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        name, separator, image = value.partition("=")
        if not separator or not name or name in parsed:
            raise ValueError("--image must be NAME=IMAGE with unique names")
        parsed[name] = image
    return parsed


def _load_images(arguments: argparse.Namespace) -> dict[str, str]:
    images: dict[str, str] = {}
    if arguments.manifest:
        manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
        images.update(manifest["images"])
    for name, image in _named_images(arguments.image).items():
        if name in images:
            raise ValueError(f"duplicate image name {name}")
        images[name] = image
    if not images:
        raise ValueError("at least one image is required")
    return images


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_mirrored(records: Sequence[Mapping[str, Any]]) -> None:
    for record in records:
        state = "copied" if record["copied"] else "already present"
        print(f"{record['member']}: {state} {record['target']} ({record['seconds']}s)")


def _publish(arguments: argparse.Namespace, images: Mapping[str, str]) -> int:
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    evidence = publish_to_mirrors(config, images)
    _write(arguments.output, evidence)
    if not evidence["targets"]:
        print("::notice title=ACR mirror skipped::No environment has a recorded image publish identity yet.")
        return 0
    failed = False
    for target in evidence["targets"]:
        if target["status"] == "succeeded":
            print(f"{target['environment']} ({target['login_server']}):")
            _print_mirrored(target["mirrored"])
        else:
            failed = True
            print(
                f"::warning title=ACR mirror failed for {target['environment']}::{target['error']}. "
                "Deployments with image_home=both fall back to GHCR; image_home=azure copies again at deploy time.",
                file=sys.stderr,
            )
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("copy", "select", "publish"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path)
        command.add_argument("--image", action="append", default=[])
        command.add_argument("--output", type=Path, required=True)
        if name != "publish":
            command.add_argument("--login-server", default="")
    commands.choices["select"].add_argument("--image-home", required=True, choices=IMAGE_HOMES)
    commands.choices["select"].add_argument("--pull-identity-id", default="")
    commands.choices["select"].add_argument("--registry-ready", choices=("true", "false"), default="false")
    commands.choices["publish"].add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        images = _load_images(arguments)
        if arguments.command == "publish":
            return _publish(arguments, images)
        if arguments.command == "copy":
            evidence: dict[str, Any] = {"mirrored": mirror_images(arguments.login_server, images)}
        else:
            evidence = select_image_home(
                image_home=arguments.image_home,
                images=images,
                login_server=arguments.login_server,
                pull_identity_id=arguments.pull_identity_id,
                registry_ready=arguments.registry_ready == "true",
            )
    except (MirrorError, ValueError, KeyError, json.JSONDecodeError, OSError) as error:
        print(f"::error title=Image mirror failed::{error}", file=sys.stderr)
        _write(arguments.output, {"error": str(error)})
        return 1
    _write(arguments.output, evidence)
    if evidence.get("fallback_reason"):
        print(f"::warning title=Image home fell back to GitHub::{evidence['fallback_reason']}", file=sys.stderr)
    _print_mirrored(evidence["mirrored"])
    if arguments.command == "select":
        print(
            f"image_home requested={evidence['requested_image_home']} effective={evidence['effective_image_home']} "
            f"registry={evidence['registry_server'] or 'ghcr.io'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
