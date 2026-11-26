#!/usr/bin/env python3
"""Create and remove throwaway Demo customers for manual and automated testing.

The public identity edge denies the Keycloak admin API, so a throwaway customer can only be created from
inside the Demo network. This utility runs a short-lived Container Apps job there (as the existing Demo
deployment identity), registers each customer as synthetic through the platform's marker route, and writes
the sign-in details to a private file outside the repository. Nothing is printed except usernames and ids.

    python3 scripts/demo_synthetic_customer.py create --count 2
    python3 scripts/demo_synthetic_customer.py list
    python3 scripts/demo_synthetic_customer.py delete --run-id acc1126a   (or: delete --all)

Users are named ``acc-<run>-<label>`` in the Keycloak group ``synthetic`` and carry only the synthetic email
domain. Deletion touches only users with that prefix that are also in that group. Demo only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REALM = "waooaw"
GROUP = "synthetic"
PREFIX = "acc-"
EMAIL_DOMAIN = "synthetic.waooaw.test"
CLIENT_ID = "waooaw-acceptance-provisioner"
IDENTITY_ORIGIN = "https://auth.demo.waooaw.com"
API_ORIGIN = "https://api.demo.waooaw.com"
SUBSCRIPTION = "2ed11839-6a0f-4eaa-bd94-44ca96ff5d84"
RESOURCE_GROUP = "waooaw-demo-rg"
ENVIRONMENT = "cae-waooaw-demo"
ACCEPTANCE_VAULT = "kv-waooaw-demo-acc"
PROVISIONER_SECRET = "acceptance-keycloak-provisioner-client-secret"  # noqa: S105 - Key Vault secret name, not a value
DEPLOYMENT_IDENTITY = "id-waooaw-demo-deployment"
LOG_WORKSPACE = "8604586b-f914-46ab-8403-398b43186c0a"
JOB = "job-demo-synthetic-customers"
# The platform marker route accepts run ids of 8 to 64 characters (AcceptanceSyntheticController.RunIdPattern).
RUN_ID = re.compile(r"^[a-z0-9]{8,12}$")
LABEL = re.compile(r"^[a-z]{1,4}$")
PRIVATE_DIRECTORY = Path(os.environ.get("SYNTHETIC_CUSTOMER_DIRECTORY", "/workspaces/.synthetic-customers"))

# Runs inside the Demo network. Container Apps routes on the Host header, so only X-Forwarded-* are sent;
# Keycloak (KC_PROXY_HEADERS=xforwarded) then validates the token against the public identity hostname.
JOB_SCRIPT = r"""
import json, os, urllib.error, urllib.parse, urllib.request
spec = json.loads(os.environ["SPEC"])
realm, group, prefix = spec["realm"], spec["group"], spec["prefix"]
base = "http://ca-demo-keycloak"
forwarded = {"X-Forwarded-Host": "auth.demo.waooaw.com", "X-Forwarded-Proto": "https"}
# The provisioning token lives only 60 seconds, so the job fetches its own when it starts.
form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": spec["client_id"],
                               "client_secret": os.environ["CLIENT_SECRET"]}).encode()
with urllib.request.urlopen(urllib.request.Request(
        f"{base}/realms/{realm}/protocol/openid-connect/token", data=form, headers=forwarded), timeout=30) as response:
    token = json.loads(response.read())["access_token"]
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json", **forwarded}

def call(method, path, body=None):
    request = urllib.request.Request(base + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:200]

def synthetic_members():
    status, text = call("GET", f"/admin/realms/{realm}/groups?search={group}&exact=true")
    match = [g for g in (json.loads(text) if status == 200 else []) if g["name"] == group]
    if not match:
        return []
    status, text = call("GET", f"/admin/realms/{realm}/groups/{match[0]['id']}/members?first=0&max=500")
    return [u for u in (json.loads(text) if status == 200 else []) if u["username"].startswith(prefix)]

if spec["action"] == "create":
    for label, user in spec["users"].items():
        if not user["username"].startswith(prefix):
            raise SystemExit("refusing a username outside the synthetic prefix")
        created, body = call("POST", f"/admin/realms/{realm}/users", {
            "username": user["username"], "email": user["email"], "emailVerified": True, "enabled": True,
            "firstName": "Synthetic", "lastName": label.upper(), "groups": ["/" + group],
            "credentials": [
                {"type": "password", "value": user["password"], "temporary": False},
                {"type": "otp", "secretData": json.dumps({"value": user["otpSecret"]}),
                 "credentialData": json.dumps({"subType": "totp", "digits": 6, "period": 30,
                                               "algorithm": "HmacSHA1", "counter": 0})}]})
        if created != 201:
            print("SYN ERROR", user["username"], body.replace("\n", " ")[:160], flush=True)
        status, text = call("GET", f"/admin/realms/{realm}/users?username={user['username']}&exact=true")
        found = json.loads(text) if status == 200 and text.startswith("[") else []
        print("SYN USER", label, user["username"], "created", created, "id", found[0]["id"] if found else "", flush=True)
elif spec["action"] == "list":
    for user in synthetic_members():
        print("SYN USER", user["username"], "id", user["id"], flush=True)
elif spec["action"] == "delete":
    wanted = spec.get("run_prefix")
    for user in synthetic_members():
        if wanted and not user["username"].startswith(wanted):
            continue
        status, _ = call("DELETE", f"/admin/realms/{realm}/users/{user['id']}")
        print("SYN DELETED", user["username"], status, flush=True)
print("SYN COMPLETE", flush=True)
"""


class UtilityError(RuntimeError):
    """A refusal or failure that should be reported without a traceback."""


def b32(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode().rstrip("=")


def new_run_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%m%d")
    return f"s{stamp}{secrets.token_hex(2)}"


def synthetic_username(run_id: str, label: str) -> str:
    if RUN_ID.fullmatch(run_id) is None or LABEL.fullmatch(label) is None:
        raise UtilityError("run id must be 8 to 12 lowercase letters or digits and a label 1 to 4 letters")
    return f"{PREFIX}{run_id}-{label}"


def realm_password() -> str:
    """A random password that satisfies the realm policy: 12+ characters, an upper-case letter, a digit and a special."""
    return f"{secrets.token_urlsafe(18)}-Aa{secrets.randbelow(10)}!"


def make_customers(run_id: str, labels: list[str]) -> dict[str, dict[str, str]]:
    customers = {}
    for label in labels:
        username = synthetic_username(run_id, label)
        customers[label.upper()] = {
            "username": username,
            "email": f"{username}@{EMAIL_DOMAIN}",
            "password": realm_password(),
            "otpSecret": b32(),
        }
    return customers


def job_spec(action: str, **extra: Any) -> dict[str, Any]:
    return {"action": action, "realm": REALM, "group": GROUP, "prefix": PREFIX, "client_id": CLIENT_ID, **extra}


def parse_job_lines(lines: list[str]) -> list[list[str]]:
    return [
        line.split() for line in lines if line.startswith("SYN ") and line.split()[1] in ("USER", "DELETED", "COMPLETE", "ERROR")
    ]


def private_write(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)


def harness_state(run_id: str, customers: dict[str, dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    """The run-state file the journey-acceptance harness reads, so it adopts these customers instead of creating its own."""
    return {
        "runId": run_id,
        "startedAt": (now or datetime.now(timezone.utc)).isoformat(),
        "customers": {
            label: {key: customer[key] for key in ("userId", "username", "email", "password", "otpSecret")}
            for label, customer in customers.items()
        },
        "values": {},
    }


def az_json(*args: str) -> Any:
    result = subprocess.run(  # noqa: S603 - fixed CLI, argument vector, no shell
        ["az", *args, "--only-show-errors", "--output", "json"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise UtilityError(f"az {' '.join(args[:3])} failed")
    return json.loads(result.stdout) if result.stdout.strip() else None


def az_text(*args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed CLI, argument vector, no shell
        ["az", *args, "--only-show-errors", "--output", "tsv"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise UtilityError(f"az {' '.join(args[:3])} failed")
    return result.stdout.strip()


def az_quiet(*args: str) -> None:
    """Runs az and ignores the outcome; used only to remove a leftover job that may not exist."""
    subprocess.run(["az", *args, "--only-show-errors"], capture_output=True, check=False)  # noqa: S603, S607 - fixed CLI, argument vector


def http(method: str, url: str, token: str, body: dict[str, Any] | None = None) -> int:
    request = urllib.request.Request(  # noqa: S310 - fixed first-party HTTPS origins
        url,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=None if body is None else json.dumps(body).encode(),
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def provisioner_client_secret() -> str:
    return az_text(
        "keyvault", "secret", "show", "--vault-name", ACCEPTANCE_VAULT, "--name", PROVISIONER_SECRET, "--query", "value"
    )


def provisioner_token() -> str:
    """A provisioning-client token; it lives only 60 seconds, so fetch one immediately before each use."""
    client_secret = provisioner_client_secret()
    form = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": client_secret}
    ).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed first-party HTTPS origin
        f"{IDENTITY_ORIGIN}/realms/{REALM}/protocol/openid-connect/token", data=form, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read())["access_token"]
    except urllib.error.HTTPError as error:
        error.close()
        raise UtilityError(f"the provisioning client could not authenticate (HTTP {error.code})") from None


def run_in_network(spec: dict[str, Any], client_secret: str, *, sleep: Callable[[float], None] = time.sleep) -> list[list[str]]:
    """Runs JOB_SCRIPT as a one-off job in the Demo Container Apps environment and returns its SYN lines."""
    parameters = json.loads(Path("infrastructure/deployment-stacks/goal006-runner/demo.parameters.json").read_text())[
        "parameters"
    ]
    image = parameters["runnerImage"]["value"]
    identity = (
        f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{DEPLOYMENT_IDENTITY}"
    )
    job_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.App/jobs/{JOB}?api-version=2024-03-01"
    )
    az_quiet("containerapp", "job", "delete", "-n", JOB, "-g", RESOURCE_GROUP, "--yes")
    az_json(
        "containerapp",
        "job",
        "create",
        "--name",
        JOB,
        "--resource-group",
        RESOURCE_GROUP,
        "--environment",
        ENVIRONMENT,
        "--trigger-type",
        "Manual",
        "--replica-timeout",
        "300",
        "--replica-retry-limit",
        "0",
        "--replica-completion-count",
        "1",
        "--parallelism",
        "1",
        "--image",
        image,
        "--cpu",
        "0.5",
        "--memory",
        "1Gi",
        "--mi-user-assigned",
        identity,
        "--command",
        "/bin/true",
        "--secrets",
        f"client={client_secret}",
        f"spec={json.dumps(spec)}",
        "--env-vars",
        "CLIENT_SECRET=secretref:client",
        "SPEC=secretref:spec",
    )
    try:
        # The CLI drops a "-c" argument, so the script is set through the management API.
        template = az_json("rest", "--method", "get", "--url", job_url)["properties"]["template"]
        template["containers"][0]["command"] = ["/usr/bin/python3"]
        template["containers"][0]["args"] = ["-c", JOB_SCRIPT]
        az_json("rest", "--method", "patch", "--url", job_url, "--body", json.dumps({"properties": {"template": template}}))
        execution = az_text("containerapp", "job", "start", "-n", JOB, "-g", RESOURCE_GROUP, "--query", "name")
        status = ""
        for _ in range(36):
            status = az_text(
                "containerapp",
                "job",
                "execution",
                "show",
                "-n",
                JOB,
                "-g",
                RESOURCE_GROUP,
                "--job-execution-name",
                execution,
                "--query",
                "properties.status",
            )
            if status in ("Succeeded", "Failed", "Stopped"):
                break
            sleep(10)
        if status != "Succeeded":
            raise UtilityError(f"the in-network job ended {status or 'without finishing'}")
        # Console logs reach Log Analytics a few seconds late.
        for attempt in range(12):
            rows = (
                az_json(
                    "monitor",
                    "log-analytics",
                    "query",
                    "--workspace",
                    LOG_WORKSPACE,
                    "--timespan",
                    "PT30M",
                    "--analytics-query",
                    f"// poll {attempt}-{time.time_ns()}\nContainerAppConsoleLogs_CL"
                    f" | where ContainerGroupName_s startswith '{execution}' | project Log_s",
                )
                or []
            )
            lines = [row["Log_s"] for row in rows]
            if any(line.startswith("SYN COMPLETE") for line in lines):
                return parse_job_lines(lines)
            sleep(10)
        raise UtilityError("the in-network job finished but its output was not found in the logs")
    finally:
        az_quiet("containerapp", "job", "delete", "-n", JOB, "-g", RESOURCE_GROUP, "--yes")


def create(count: int, run_id: str, harness_private: Path | None) -> Path:
    labels = [chr(ord("a") + index) for index in range(count)]
    customers = make_customers(run_id, labels)
    lines = run_in_network(job_spec("create", users=customers), provisioner_client_secret())
    # Create lines read: SYN USER <label> <username> created <status> id <id>
    created = {line[3]: (line[5], line[7]) for line in lines if line[:2] == ["SYN", "USER"] and len(line) >= 8}
    for customer in customers.values():
        status, user_id = created.get(customer["username"], ("", ""))
        if not user_id:
            seen = " | ".join(" ".join(line) for line in lines if customer["username"] in line)
            raise UtilityError(
                f"customer {customer['username']} was not created (status {status or 'unknown'}; job said: {seen or 'nothing'})"
            )
        customer["userId"] = user_id
    # The marker lets the platform label what these customers create as synthetic; it grants no authority.
    token = provisioner_token()
    for customer in customers.values():
        marker = f"{API_ORIGIN}/internal/v1/acceptance/runs/{run_id}/synthetic-subjects"
        code = http("POST", marker, token, {"subject": customer["userId"]})
        if code not in (201, 204):
            raise UtilityError(
                f"the synthetic marker was not registered for {customer['username']} (HTTP {code}); delete the run"
            )
    path = PRIVATE_DIRECTORY / f"{run_id}.json"
    private_write(
        path,
        {
            "runId": run_id,
            "customers": customers,
            "signIn": "https://cp.demo.waooaw.com/login (username, password, then authenticator code)",
        },
    )
    if harness_private is not None:
        private_write(harness_private / "run-state.json", harness_state(run_id, customers))
    return path


def delete(run_id: str | None) -> list[list[str]]:
    spec = job_spec("delete", **({"run_prefix": f"{PREFIX}{run_id}-"} if run_id else {}))
    lines = run_in_network(spec, provisioner_client_secret())
    token = provisioner_token()
    if run_id:
        http("DELETE", f"{API_ORIGIN}/internal/v1/acceptance/runs/{run_id}", token)
        (PRIVATE_DIRECTORY / f"{run_id}.json").unlink(missing_ok=True)
    else:
        for file in PRIVATE_DIRECTORY.glob("*.json"):
            http("DELETE", f"{API_ORIGIN}/internal/v1/acceptance/runs/{file.stem}", token)
            file.unlink()
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("create", help="create throwaway customers")
    make.add_argument("--count", type=int, default=2, choices=range(1, 5))
    make.add_argument("--run-id")
    make.add_argument("--harness-private", type=Path, help="also write run-state.json for the journey-acceptance harness")
    sub.add_parser("list", help="list synthetic customers that exist")
    remove = sub.add_parser("delete", help="delete throwaway customers")
    group = remove.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id")
    group.add_argument("--all", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "create":
            run_id = arguments.run_id or new_run_id()
            if RUN_ID.fullmatch(run_id) is None:
                raise UtilityError("run id must be 8 to 12 lowercase letters or digits")
            path = create(arguments.count, run_id, arguments.harness_private)
            print(f"created run {run_id}; sign-in details (private, mode 600): {path}")
        elif arguments.command == "list":
            for line in run_in_network(job_spec("list"), provisioner_client_secret()):
                if line[:2] == ["SYN", "USER"]:
                    print(line[2])
        else:
            for line in delete(None if arguments.all else arguments.run_id):
                if line[:2] == ["SYN", "DELETED"]:
                    print("deleted", line[2], line[3])
    except UtilityError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
