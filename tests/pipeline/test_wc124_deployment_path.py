"""Execute deployment workflow commands through their downstream evidence consumers."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from wc124_db_provisioner import REQUIRED_IDENTITY_RELATIONS, expected_identity_policy_digest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/environment-deployment.yaml").read_text())
STEPS = WORKFLOW["jobs"]["terraform"]["steps"]


def step(name: str) -> str:
    body = next(item["run"] for item in STEPS if item.get("name") == name)
    values = {"environment": "demo", "release_sha": "a" * 40, "release_run_id": "12"}
    return re.sub(r"\$\{\{ inputs\.(\w+) \}\}", lambda match: values[match[1]], body)


@pytest.fixture
def path_context(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    (tmp_path / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    commands = tmp_path / "bin"
    commands.mkdir()
    az = commands / "az"
    az.write_text(
        f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path("commands.jsonl").open("a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:3] == ["containerapp", "job", "show"]:
    print(json.dumps({{"properties": {{"environmentId": "/subscriptions/fixture/environments/demo"}}}}))
elif args[:2] == ["resource", "show"]:
    if os.environ.get("WORKSPACE_ERROR"):
        sys.exit(3)
    print(json.dumps("8604586b-f914-46ab-8403-398b43186c0a"))
elif args[:3] == ["containerapp", "job", "start"]:
    print("job-demo-temporal-startup-fixture")
elif args[:4] == ["containerapp", "job", "execution", "show"]:
    if "--query" in args:
        print("Succeeded")
    else:
        print(json.dumps({{"name": "job-demo-temporal-startup-fixture", "properties": {{
            "status": "Succeeded", "startTime": "2026-10-28T12:00:00Z", "endTime": "2026-10-28T12:02:00Z"
        }}}}))
elif args[:4] == ["containerapp", "job", "logs", "show"]:
    print('2026-10-28T12:02:00Z stdout F ' + json.dumps({{
        "schema": "waooaw.wc124-temporal-startup/v1", "status": "passed",
        "qualification_seconds": 60, "max_waiting_clients": 0, "max_wait_seconds": 0,
        "minimum_postgresql_headroom": 18
    }}, separators=(",", ":")))
elif args[:3] == ["monitor", "log-analytics", "query"]:
    if os.environ.get("QUERY_ERROR"):
        sys.exit(7)
    print(os.environ.get("QUERY_ROWS", '[{{"timeout_events": "0", "latest_log": "2026-10-28T12:02:01Z", "TableName": "PrimaryResult"}}]'))
elif args[:3] == ["postgres", "flexible-server", "show"]:
    server_id = "/subscriptions/fixture/postgres/demo"
    print(server_id if "--query" in args else json.dumps({{"id": server_id}}))
elif args[:2] == ["containerapp", "show"]:
    print("fixture-latest" if "--query" in args else "{{}}")
elif args[:3] == ["containerapp", "revision", "list"]:
    pass
elif args[:4] == ["postgres", "flexible-server", "parameter", "show"]:
    print({{"max_connections": 50, "superuser_reserved_connections": 10, "reserved_connections": 5}}[
        args[args.index("--name") + 1]])
elif args[:3] == ["monitor", "metrics", "list"]:
    if os.environ.get("METRIC_ERROR"):
        sys.exit(9)
    print(os.environ.get("METRIC", "11"))
else:
    raise SystemExit("Unexpected Azure command: " + repr(args))
"""
    )
    az.chmod(0o755)
    for name, body in {
        "sleep": "#!/bin/sh\nexit 0\n",
        "terraform": f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if args[0] == "plan":
    Path("workload-activation.tfplan").write_bytes(b"fixture plan")
    sys.exit(int(os.environ.get("PLAN_EXIT", "2")))
elif args[0] == "show":
    print(json.dumps({{"resource_changes": []}}))
elif args[:2] == ["state", "pull"]:
    print(json.dumps({{"lineage": "fixture", "serial": int(os.environ.get("STATE_SERIAL", "1"))}}))
elif args[0] == "apply":
    Path("applied").touch()
elif args[0] == "output":
    print("https://cp.demo.waooaw.com")
else:
    raise SystemExit("Unexpected Terraform command: " + repr(args))
""",
        "curl": '#!/bin/sh\nprintf \'%s\\n\' \'{"object":{"sha":"' + "a" * 40 + "\"}}'\n",
    }.items():
        target = commands / name
        target.write_text(body)
        target.chmod(0o755)
    return tmp_path, {
        **os.environ,
        "PATH": f"{commands}:{os.environ['PATH']}",
        "RESOURCE_GROUP": "waooaw-demo-rg",
        "TARGET_ENVIRONMENT": "demo",
        "POSTGRESQL_SERVER_FQDN": "postgres.example.invalid",
        "RELEASE_SHA": "a" * 40,
        "RELEASE_RUN_ID": "12",
        "GITHUB_WORKSPACE": str(ROOT),
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REPOSITORY": "dlai-sd/waooaw-platform",
        "GH_TOKEN": "fixture-only",
        "GITHUB_OUTPUT": str(tmp_path / "github-output"),
    }


def execute(context: tuple[Path, dict[str, str]], name: str) -> subprocess.CompletedProcess[str]:
    directory, environment = context
    if name == "Vendor group headroom":
        body = step("Run vendor schema migrations against private PostgreSQL").split("\nstart_migration() {", 1)[0]
        body += "\nrequire_group_headroom temporal\n"
    else:
        body = step(name)
    return subprocess.run(["bash", "-c", body], cwd=directory, env=environment, capture_output=True, text=True, timeout=30)


def test_qualification_reaches_actual_migration_acceptance(path_context):
    directory, _ = path_context
    result = execute(path_context, "Qualify exact Temporal startup through PgBouncer")
    assert result.returncode == 0, result.stderr
    identity = {
        "execution": "identity-fixture",
        "identity_schema": {
            "status": "passed",
            "required_relations": list(REQUIRED_IDENTITY_RELATIONS),
            "relations": {
                name: {
                    "exists": True,
                    "rls": True,
                    "forced_rls": True,
                    "actor_scope_policy": True,
                    "policy_definition_sha256": expected_identity_policy_digest(name),
                }
                for name in REQUIRED_IDENTITY_RELATIONS
            },
        },
    }
    inputs = {
        "wc124-db-provisioner-result.json": identity,
        "wc124-db-provisioner-execution.json": {"name": "identity-fixture", "properties": {"status": "Succeeded"}},
        "wc124-pgbouncer-preflight-execution.json": {"name": "preflight", "properties": {"status": "Succeeded"}},
        "wc124-billing-migration-execution.json": {"name": "billing", "properties": {"status": "Succeeded"}},
        "wc124-reconciliation-authority.json": {"status": "temporary-authority-revoked"},
        "wc124-vendor-migrations.json": {
            "environment": "demo",
            "executions": [{"component": component, "status": "Succeeded"} for component in ("keycloak", "temporal")],
        },
    }
    for name, content in inputs.items():
        (directory / name).write_text(json.dumps(content))
    result = execute(path_context, "Verify migration evidence before application activation")
    assert result.returncode == 0, result.stderr
    assert json.loads((directory / "wc124-migration-acceptance.json").read_text())["status"] == "accepted-for-activation"
    calls = [json.loads(line) for line in (directory / "commands.jsonl").read_text().splitlines()]
    assert next(i for i, args in enumerate(calls) if args[:2] == ["resource", "show"]) < next(
        i for i, args in enumerate(calls) if args[:3] == ["containerapp", "job", "start"]
    )
    assert not any("workspace" in args and "show" in args for args in calls)


@pytest.mark.parametrize(
    "overrides",
    [
        {"WORKSPACE_ERROR": "1"},
        {"QUERY_ERROR": "1"},
        {"QUERY_ROWS": '[{"timeout_events": "2"}]'},
        {"QUERY_ROWS": "[]"},
        {"QUERY_ROWS": '{"tables": []}'},
        {"QUERY_ROWS": '[{"timeout_events": null}]'},
        {"QUERY_ROWS": '[{"timeout_events": "bad"}]'},
        {"QUERY_ROWS": '[{"timeout_events": "0", "latest_log": ""}]'},
        {"QUERY_ROWS": '[{"timeout_events": "0", "latest_log": null}]'},
        {"QUERY_ROWS": '[{"timeout_events": "0", "latest_log": "2026-10-28T12:00:00Z"}]'},
        {"QUERY_ROWS": '[{"timeout_events": "0", "latest_log": "bad-date"}]'},
    ],
)
def test_qualification_rejects_missing_malformed_or_failed_evidence(path_context, overrides):
    directory, environment = path_context
    environment.update(overrides)
    result = execute(path_context, "Qualify exact Temporal startup through PgBouncer")
    assert result.returncode != 0
    assert not (directory / "wc124-temporal-pool-evidence.json").exists()
    if "WORKSPACE_ERROR" in overrides:
        assert '"start"' not in (directory / "commands.jsonl").read_text()


@pytest.mark.parametrize("plan_exit", ["0", "2"])
@pytest.mark.parametrize("changed_state", [False, True])
def test_actual_activation_plan_and_apply_bind_same_state(path_context, plan_exit, changed_state):
    directory, environment = path_context
    environment["PLAN_EXIT"] = plan_exit
    (directory / "workload.auto.tfvars.json").write_text('{"application_activation_enabled": false}')
    result = execute(path_context, "Plan application activation after migration")
    assert result.returncode == 0, result.stderr
    assert json.loads((directory / "workload.auto.tfvars.json").read_text())["application_activation_enabled"] is True
    if changed_state:
        environment["STATE_SERIAL"] = "2"
    result = execute(path_context, "Apply application activation")
    assert (result.returncode == 0) is not changed_state, result.stderr
    assert (directory / "applied").exists() is not changed_state


@pytest.mark.parametrize(
    "stage",
    [
        "Reclaim PostgreSQL connection budget before vendor migrations",
        "Vendor group headroom",
        "Measure PostgreSQL connection budget after activation",
    ],
)
@pytest.mark.parametrize("metric", ["0", "11", "11.1", "", "None", "null", "-1", "bad", "36"])
def test_all_actual_budget_consumers_reject_missing_or_insufficient_metrics(path_context, metric, stage):
    directory, environment = path_context
    environment["METRIC"] = metric
    if stage == "Vendor group headroom":
        (directory / "wc124-connection-budget.json").write_text(
            json.dumps(
                {
                    "server_id": "fixture",
                    "usable_connections": 35,
                    "required_headroom_per_group": 4,
                }
            )
        )
    result = execute(path_context, stage)
    valid = metric in {"0", "11", "11.1"}
    assert (result.returncode == 0) is valid, result.stderr
    evidence_file = {
        "Reclaim PostgreSQL connection budget before vendor migrations": "wc124-connection-budget.json",
        "Vendor group headroom": "wc124-vendor-migrations.json",
        "Measure PostgreSQL connection budget after activation": "wc124-connection-budget-post-activation.json",
    }[stage]
    evidence = directory / evidence_file
    if valid:
        record = json.loads(evidence.read_text())
        if stage == "Vendor group headroom":
            record = record["groups"][0]
        assert record["active_connections_latest_1m"] == {"0": 0, "11": 11, "11.1": 12}[metric]
    elif metric == "36" and stage == "Measure PostgreSQL connection budget after activation":
        assert json.loads(evidence.read_text())["status"] == "failed"
    elif stage != "Vendor group headroom":
        assert not evidence.exists()


@pytest.mark.parametrize(
    "stage",
    [
        "Reclaim PostgreSQL connection budget before vendor migrations",
        "Vendor group headroom",
        "Measure PostgreSQL connection budget after activation",
    ],
)
def test_metric_cli_error_is_not_zero_connections(path_context, stage):
    directory, environment = path_context
    environment["METRIC_ERROR"] = "1"
    (directory / "wc124-connection-budget.json").write_text(
        json.dumps(
            {
                "server_id": "fixture",
                "usable_connections": 35,
                "required_headroom_per_group": 4,
            }
        )
    )
    assert execute(path_context, stage).returncode != 0
    assert not (directory / "wc124-connection-budget-post-activation.json").exists()


def test_temporal_bounds_cover_both_stores_and_both_launch_surfaces():
    workload = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    for name in ("SQL_MAX_CONNS", "SQL_MAX_IDLE_CONNS", "SQL_VIS_MAX_CONNS", "SQL_VIS_MAX_IDLE_CONNS"):
        assert len(re.findall(rf'name\s+= "{name}"\s+value = "1"', workload)) == 2
        for harness in ("wc124_temporal_startup_local.sh", "wc124_application_activation_local.sh"):
            assert f"-e {name}=1" in (ROOT / "scripts" / harness).read_text()
