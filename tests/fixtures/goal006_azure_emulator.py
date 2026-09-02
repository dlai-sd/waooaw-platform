#!/usr/bin/env python3
"""Deterministic Azure control-plane emulator for GOAL-006 Docker rehearsals."""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from goal006_live_inventory import DEMO_TEMPORAL_IMAGE, IDENTITY_EDGE_IMAGE, KEYCLOAK_IMAGE
from goal006_registry_manifest import RELEASE_MEMBERS
from goal006_runner_execution import CLEANUP_ARGS, CLEANUP_COMMAND, CLEANUP_REQUIRED_ENVIRONMENT, REQUIRED_ENVIRONMENT

SUBSCRIPTION_ID = "00000000-0000-0000-0000-000000000006"
TENANT_ID = "00000000-0000-0000-0000-000000000007"
ENVIRONMENT = "demo"
EVIDENCE_DIR = Path(os.environ.get("EVIDENCE_DIR", "/evidence"))
RUNNER_IMAGE = "ghcr.io/dlai-sd/goal006-private-runner@sha256:" + "f" * 64


def release_manifest() -> dict[str, object]:
    images = {
        member: f"ghcr.io/dlai-sd/{member}@sha256:{index:064x}" for index, member in enumerate(sorted(RELEASE_MEMBERS), start=1)
    }
    return {
        "schema": "waooaw.registry-release/v1",
        "immutable": True,
        "source_commit": "a" * 40,
        "builder_workflow": ".github/workflows/ci.yaml",
        "qualification": {"status": "pass", "github_run_id": "393"},
        "images": images,
        "evidence": {
            member: {
                kind: {
                    "artifact": (f"goal006-scan-{member}" if kind == "scan" else f"goal006-attestation-{member}"),
                    "sha256": {"scan": "b", "sbom": "c", "provenance": "d", "signature": "e"}[kind] * 64,
                    **(
                        {"policy": "fixable-high-critical"}
                        if kind == "scan"
                        else {"oci_subject": images[member], "format": "spdx"}
                        if kind == "sbom"
                        else {"oci_subject": images[member], "mode": "max"}
                        if kind == "provenance"
                        else {"oci_subject": images[member], "issuer": "github-oidc"}
                    ),
                }
                for kind in ("scan", "sbom", "provenance", "signature")
            }
            for member in RELEASE_MEMBERS
        },
    }


def container_apps(manifest: dict[str, object]) -> list[dict[str, object]]:
    images = manifest["images"]
    assert isinstance(images, dict)
    dependencies = {
        "keycloak": KEYCLOAK_IMAGE,
        "identity-edge": IDENTITY_EDGE_IMAGE,
        "temporal": DEMO_TEMPORAL_IMAGE,
    }
    return [
        {
            "name": f"ca-{ENVIRONMENT}-{name}",
            "properties": {
                "provisioningState": "Succeeded",
                "template": {"containers": [{"image": image}]},
            },
        }
        for name, image in {**images, **dependencies}.items()
    ]


def cleanup_job() -> dict[str, object]:
    environment = [
        {"name": name, "value": f"local-{name.lower()}"} for name in sorted(REQUIRED_ENVIRONMENT | CLEANUP_REQUIRED_ENVIRONMENT)
    ]
    values = {item["name"]: item for item in environment}
    values["RUNNER_ACTIVATION_STATE"]["value"] = "ACTIVE"
    values["RUNNER_ENVIRONMENT"]["value"] = ENVIRONMENT
    values["GITHUB_REPOSITORY"]["value"] = "dlai-sd/waooaw-platform"
    values["RUNNER_RESOURCE_GROUP"]["value"] = "waooaw-demo-runner-rg"
    values["RUNNER_JOB_NAME"]["value"] = "goal006-demo-runner-job"
    values["RUNNER_LABEL"]["value"] = "goal006-demo-private"
    values["GITHUB_RUN_ID"]["value"] = "PENDING_EXECUTION_OVERRIDE"
    values["GITHUB_RUN_ATTEMPT"]["value"] = "PENDING_EXECUTION_OVERRIDE"
    return {
        "name": "goal006-demo-runner-cleanup-broker",
        "properties": {
            "provisioningState": "Succeeded",
            "configuration": {"triggerType": "Manual"},
            "template": {
                "containers": [
                    {
                        "name": "cleanup-broker",
                        "image": RUNNER_IMAGE,
                        "command": CLEANUP_COMMAND,
                        "args": ["stale deployed lifecycle source", *CLEANUP_ARGS[1:]],
                        "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                        "env": environment,
                    }
                ],
                "volumes": None,
            },
        },
    }


class AzureHandler(BaseHTTPRequestHandler):
    manifest = release_manifest()
    apps = container_apps(manifest)
    revision_show_counts: ClassVar[dict[str, int]] = {}

    def log_message(self, message: str, *args: object) -> None:
        record = {"method": self.command, "path": self.path, "message": message % args}
        with (EVIDENCE_DIR / "azure-request-log.jsonl").open("a", encoding="utf-8") as request_log:
            request_log.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record), flush=True)

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status: int, payload: str) -> None:
        body = payload.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if path == "/healthz":
            self.send_json(200, {"status": "ready"})
            return
        if path == "/metadata/identity/oauth2/token":
            self.send_json(
                200,
                {
                    "access_token": "local-emulator-token",
                    "expires_in": "3600",
                    "resource": "http://goal006-azure-emulator:8080/",
                    "token_type": "Bearer",
                },
            )
            return
        if path.endswith("/providers/Microsoft.App/containerApps"):
            self.send_json(200, {"value": self.apps})
            return
        if "/providers/Microsoft.App/containerApps/" in path and "/revisions/" in path:
            revision = path.rsplit("/", 1)[-1]
            unhealthy = "ca-demo-professional-runtime" in path and (EVIDENCE_DIR / "force-professional-runtime-unready").exists()
            self.send_json(
                200,
                {
                    "name": revision,
                    "properties": {
                        "active": True,
                        "provisioningState": "Provisioning" if unhealthy else "Provisioned",
                        "healthState": "Unhealthy" if unhealthy else "Healthy",
                        "runningState": "ActivationFailed" if unhealthy else "RunningAtMaxScale",
                        "replicas": 0 if unhealthy else 1,
                    },
                },
            )
            return
        if "/providers/Microsoft.App/containerApps/" in path:
            name = path.rsplit("/", 1)[-1]
            app = next((candidate for candidate in self.apps if candidate["name"] == name), None)
            if app is None:
                self.send_json(404, {"error": {"code": "ContainerAppNotFound", "message": name}})
                return
            properties = dict(app["properties"])
            show_count = self.revision_show_counts.get(name, 0) + 1
            self.revision_show_counts[name] = show_count
            latest_revision = f"{name}--0000002"
            latest_ready_revision = latest_revision
            force_unready = (EVIDENCE_DIR / "force-professional-runtime-unready").exists()
            if name == "ca-demo-professional-runtime" and (show_count <= 2 or force_unready):
                latest_ready_revision = f"{name}--0000001"
            properties.update(
                {
                    "latestRevisionName": latest_revision,
                    "latestReadyRevisionName": latest_ready_revision,
                    "configuration": {
                        "ingress": {
                            "fqdn": f"{name}.local.waooaw.test",
                            "ipSecurityRestrictions": [{"name": "founder-review", "ipAddressRange": "203.0.113.10/32"}],
                        }
                    },
                }
            )
            self.send_json(200, {"name": name, "properties": properties})
            return
        if "/jobs/" in path and "/replicas/" in path and path.endswith("/logstream"):
            container = path.rsplit("/containers/", 1)[1].split("/", 1)[0]
            self.send_text(200, f"{container}: all required runtime probes passed\n")
            return
        if "/providers/Microsoft.App/jobs/" in path and path.endswith("/replicas"):
            self.send_json(200, {"value": [{"name": "local-replica-0001"}]})
            return
        if "/providers/Microsoft.App/jobs/" in path and "/executions/" in path:
            execution = path.rsplit("/", 1)[-1]
            self.send_json(200, {"name": execution, "properties": {"status": "Succeeded"}})
            return
        if "/providers/Microsoft.App/jobs/" in path and path.endswith("/executions"):
            self.send_json(200, {"value": []})
            return
        if "/providers/Microsoft.App/jobs/" in path:
            name = path.rsplit("/", 1)[-1]
            if name == "goal006-demo-runner-cleanup-broker":
                self.send_json(200, cleanup_job())
            else:
                self.send_json(
                    200,
                    {
                        "name": name,
                        "properties": {
                            "provisioningState": "Succeeded",
                            "eventStreamEndpoint": (
                                "http://goal006-azure-emulator:8080/subscriptions/"
                                f"{SUBSCRIPTION_ID}/resourceGroups/waooaw-demo-rg"
                            ),
                        },
                    },
                )
            return
        self.send_json(404, {"error": {"code": "EmulatorRouteMissing", "message": path}})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if "/providers/Microsoft.App/jobs/" in path and path.endswith("/getAuthToken"):
            self.send_json(200, {"properties": {"token": "local-log-stream-token"}})
            return
        if "/providers/Microsoft.App/jobs/" in path and path.endswith("/start"):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b"{}"
            job_name = path.split("/jobs/", 1)[1].split("/", 1)[0]
            if job_name == "goal006-demo-runner-cleanup-broker":
                (EVIDENCE_DIR / "cleanup-start-request.json").write_bytes(body)
                execution_name = "goal006-demo-runner-cleanup-local-0001"
            else:
                execution_name = "job-demo-deployment-verification-local-0001"
            self.send_json(200, {"name": execution_name})
            return
        self.send_json(404, {"error": {"code": "EmulatorRouteMissing", "message": path}})


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "registry-release-manifest.json").write_text(
        json.dumps(AzureHandler.manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    server = ThreadingHTTPServer(("0.0.0.0", 8080), AzureHandler)
    print(json.dumps({"event": "ready", "port": 8080, "time": int(time.time())}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
