"""Contracts for complete private-runner Container Apps execution templates."""

import base64
import json
from copy import deepcopy

import pytest

from scripts.goal006_runner_execution import (
    BROKER_ARGS,
    CLEANUP_ARGS,
    CLEANUP_COMMAND,
    CLEANUP_REQUIRED_ENVIRONMENT,
    COMMAND,
    ExecutionTemplateError,
    REQUIRED_ENVIRONMENT,
    build_cleanup_evidence_pointer,
    build_execution_template,
    extract_cleanup_evidence,
)

IMAGE = "ghcr.io/dlai-sd/runner@sha256:" + "a" * 64


def job(name: str, arguments: list[str], environment_name: str = "demo") -> dict:
    environment = [
        {"name": key, "value": f"value-{key.lower()}"}
        for key in sorted(REQUIRED_ENVIRONMENT | CLEANUP_REQUIRED_ENVIRONMENT)
    ]
    values = {item["name"]: item for item in environment}
    values["RUNNER_ACTIVATION_STATE"]["value"] = "ACTIVE"
    values["RUNNER_ENVIRONMENT"]["value"] = environment_name
    values["GITHUB_REPOSITORY"]["value"] = "dlai-sd/waooaw-platform"
    values["RUNNER_RESOURCE_GROUP"]["value"] = f"waooaw-{environment_name}-runner-rg"
    values["RUNNER_JOB_NAME"]["value"] = f"goal006-{environment_name}-runner-job"
    values["RUNNER_LABEL"]["value"] = f"goal006-{environment_name}-private"
    values["GITHUB_RUN_ID"]["value"] = "PENDING_EXECUTION_OVERRIDE"
    values["GITHUB_RUN_ATTEMPT"]["value"] = "PENDING_EXECUTION_OVERRIDE"
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "configuration": {"triggerType": "Manual"},
            "template": {
                "containers": [
                    {
                        "name": name,
                        "image": IMAGE,
                        "command": CLEANUP_COMMAND if name == "cleanup-broker" else COMMAND,
                        "args": arguments,
                        "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                        "env": environment,
                    }
                ],
                "volumes": None,
            },
        }
    }


def test_broker_template_preserves_complete_container_and_binds_correlation() -> None:
    source = job("broker", BROKER_ARGS)
    result = build_execution_template(
        source,
        mode="broker",
        expected_image=IMAGE,
        run_id="123",
        run_attempt="2",
    )

    container = result["containers"][0]
    assert container["image"] == IMAGE
    assert container["command"] == COMMAND
    assert container["args"] == BROKER_ARGS
    assert container["resources"] == {"cpu": 0.25, "memory": "0.5Gi"}
    environment = {item["name"]: item["value"] for item in container["env"]}
    assert environment["GITHUB_RUN_ID"] == "123"
    assert environment["GITHUB_RUN_ATTEMPT"] == "2"
    source_environment = {
        item["name"]: item["value"]
        for item in source["properties"]["template"]["containers"][0]["env"]
    }
    assert source_environment["GITHUB_RUN_ID"] == "PENDING_EXECUTION_OVERRIDE"


def test_uat_broker_template_accepts_empty_azure_ephemeral_storage() -> None:
    source = job("broker", BROKER_ARGS, "uat")
    source["properties"]["template"]["containers"][0]["resources"][
        "ephemeralStorage"
    ] = ""

    result = build_execution_template(
        source,
        mode="broker",
        expected_image=IMAGE,
        run_id="123",
        run_attempt="2",
    )

    environment = {
        item["name"]: item["value"] for item in result["containers"][0]["env"]
    }
    assert environment["RUNNER_ENVIRONMENT"] == "uat"
    assert environment["RUNNER_LABEL"] == "goal006-uat-private"


def test_cleanup_template_binds_terminal_conclusion() -> None:
    result = build_execution_template(
        job("cleanup-broker", CLEANUP_ARGS),
        mode="cleanup",
        expected_image=IMAGE,
        run_id="123",
        run_attempt="1",
        private_job_conclusion="failure",
    )
    arguments = result["containers"][0]["args"]
    assert result["containers"][0]["command"] == CLEANUP_COMMAND
    assert "def write_cleanup_evidence(" in arguments[0]
    assert arguments[arguments.index("--private-job-conclusion") + 1] == "failure"


def test_cleanup_template_replaces_stale_live_source_with_trusted_source() -> None:
    stale_arguments = ["stale deployed lifecycle source", *CLEANUP_ARGS[1:]]

    result = build_execution_template(
        job("cleanup-broker", stale_arguments),
        mode="cleanup",
        expected_image=IMAGE,
        run_id="33388459246",
        run_attempt="1",
        private_job_conclusion="success",
    )

    arguments = result["containers"][0]["args"]
    assert arguments[0] == CLEANUP_ARGS[0]
    assert arguments[1:] == [
        "cleanup-correlated",
        "--app-manifest",
        "/opt/waooaw/github-runner-app-manifest.json",
        "--private-job-conclusion",
        "success",
        "--output",
        "/home/runner/cleanup-record.json",
    ]


def test_cleanup_template_rejects_live_argument_tail_drift() -> None:
    drifted_arguments = ["stale deployed lifecycle source", *CLEANUP_ARGS[1:]]
    drifted_arguments[-1] = "/tmp/unapproved-cleanup-record.json"

    with pytest.raises(ExecutionTemplateError, match="arguments"):
        build_execution_template(
            job("cleanup-broker", drifted_arguments),
            mode="cleanup",
            expected_image=IMAGE,
            run_id="33388459246",
            run_attempt="1",
            private_job_conclusion="success",
        )


def test_cleanup_evidence_is_correlation_bound_and_complete() -> None:
    record = {
        "schema": "waooaw.goal006-runner-cleanup/v1",
        "environment": "demo",
        "correlation_id": "goal006:demo:123:2",
        "runner_name": "goal006-demo-123-2",
        "runner_label": "goal006-demo-private",
        "workflow_run_id": "123",
        "workflow_run_attempt": "2",
        "private_job_conclusion": "success",
        "token_secret_name": "runner-registration-token-demo-123-2",
        "aca_execution_name": "runner-execution",
        "registration_absent": True,
        "execution_terminal": True,
        "token_secret_deleted": True,
    }
    encoded = base64.b64encode(json.dumps(record).encode()).decode()
    result = extract_cleanup_evidence(
        f"2026-08-23T00:00:00Z GOAL006_CLEANUP_RECORD_B64={encoded}\n",
        environment="demo",
        run_id="123",
        run_attempt="2",
        private_job_conclusion="success",
    )
    assert result == record


def test_cleanup_evidence_rejects_false_outcome() -> None:
    record = {
        "schema": "waooaw.goal006-runner-cleanup/v1",
        "environment": "demo",
        "correlation_id": "goal006:demo:123:2",
        "runner_name": "goal006-demo-123-2",
        "runner_label": "goal006-demo-private",
        "workflow_run_id": "123",
        "workflow_run_attempt": "2",
        "private_job_conclusion": "failure",
        "token_secret_name": "runner-registration-token-demo-123-2",
        "aca_execution_name": "runner-execution",
        "registration_absent": True,
        "execution_terminal": True,
        "token_secret_deleted": False,
    }
    encoded = base64.b64encode(json.dumps(record).encode()).decode()
    with pytest.raises(ExecutionTemplateError, match="outcome"):
        extract_cleanup_evidence(
            f"GOAL006_CLEANUP_RECORD_B64={encoded}",
            environment="demo",
            run_id="123",
            run_attempt="2",
            private_job_conclusion="failure",
        )


def test_cleanup_evidence_pointer_is_correlation_bound() -> None:
    assert build_cleanup_evidence_pointer(
        environment="demo",
        run_id="123",
        run_attempt="2",
        private_job_conclusion="success",
        cleanup_execution_name="goal006-demo-runner-cleanup-abc123",
        evidence_container_url="https://storage.example/goal006-runner-evidence",
    ) == {
        "schema": "waooaw.goal006-runner-cleanup-pointer/v1",
        "evidence_schema": "waooaw.goal006-runner-cleanup/v1",
        "environment": "demo",
        "correlation_id": "goal006:demo:123:2",
        "workflow_run_id": "123",
        "workflow_run_attempt": "2",
        "private_job_conclusion": "success",
        "cleanup_execution_name": "goal006-demo-runner-cleanup-abc123",
        "evidence_blob_url": (
            "https://storage.example/goal006-runner-evidence/cleanup/demo/123/2.json"
        ),
        "producer_status": "Succeeded",
    }


def test_uat_cleanup_evidence_pointer_is_environment_bound() -> None:
    result = build_cleanup_evidence_pointer(
        environment="uat",
        run_id="123",
        run_attempt="2",
        private_job_conclusion="success",
        cleanup_execution_name="goal006-uat-runner-cleanup-abc123",
        evidence_container_url="https://storage.example/goal006-uat-runner-evidence",
    )

    assert result["correlation_id"] == "goal006:uat:123:2"
    assert result["evidence_blob_url"].endswith("/cleanup/uat/123/2.json")


def test_cleanup_evidence_pointer_rejects_cross_environment_execution() -> None:
    with pytest.raises(ExecutionTemplateError, match="execution name"):
        build_cleanup_evidence_pointer(
            environment="uat",
            run_id="123",
            run_attempt="2",
            private_job_conclusion="success",
            cleanup_execution_name="goal006-demo-runner-cleanup-abc123",
            evidence_container_url="https://storage.example/goal006-uat-runner-evidence",
        )


def test_execution_template_rejects_cross_environment_resources() -> None:
    source = job("broker", BROKER_ARGS, "uat")
    values = {
        item["name"]: item
        for item in source["properties"]["template"]["containers"][0]["env"]
    }
    values["RUNNER_JOB_NAME"]["value"] = "goal006-demo-runner-job"

    with pytest.raises(ExecutionTemplateError, match="approved blueprint"):
        build_execution_template(
            source,
            mode="broker",
            expected_image=IMAGE,
            run_id="123",
            run_attempt="2",
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["properties"].update(provisioningState="Failed"), "provisioning"),
        (lambda value: value["properties"]["configuration"].update(triggerType="Schedule"), "trigger"),
        (lambda value: value["properties"]["template"]["containers"][0].update(image="runner:latest"), "image"),
        (lambda value: value["properties"]["template"]["containers"][0].update(command=["/bin/sh"]), "command"),
        (lambda value: value["properties"]["template"]["containers"][0].update(resources={}), "resources"),
        (lambda value: value["properties"]["template"]["containers"][0]["env"].pop(), "environment"),
    ],
)
def test_execution_template_rejects_live_blueprint_drift(mutation, message: str) -> None:
    source = job("broker", deepcopy(BROKER_ARGS))
    mutation(source)
    with pytest.raises(ExecutionTemplateError, match=message):
        build_execution_template(
            source,
            mode="broker",
            expected_image=IMAGE,
            run_id="123",
            run_attempt="1",
        )


@pytest.mark.parametrize("conclusion", [None, "queued", "PENDING_EXECUTION_OVERRIDE"])
def test_cleanup_rejects_nonterminal_conclusion(conclusion: str | None) -> None:
    with pytest.raises(ExecutionTemplateError, match="conclusion"):
        build_execution_template(
            job("cleanup-broker", CLEANUP_ARGS),
            mode="cleanup",
            expected_image=IMAGE,
            run_id="123",
            run_attempt="1",
            private_job_conclusion=conclusion,
        )