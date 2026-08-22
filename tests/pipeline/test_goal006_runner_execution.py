"""Contracts for complete private-runner Container Apps execution templates."""

from copy import deepcopy

import pytest

from scripts.goal006_runner_execution import (
    BROKER_ARGS,
    CLEANUP_ARGS,
    COMMAND,
    ExecutionTemplateError,
    REQUIRED_ENVIRONMENT,
    build_execution_template,
)

IMAGE = "ghcr.io/dlai-sd/runner@sha256:" + "a" * 64


def job(name: str, arguments: list[str]) -> dict:
    environment = [
        {"name": key, "value": f"value-{key.lower()}"}
        for key in sorted(REQUIRED_ENVIRONMENT)
    ]
    values = {item["name"]: item for item in environment}
    values["RUNNER_ACTIVATION_STATE"]["value"] = "ACTIVE"
    values["RUNNER_ENVIRONMENT"]["value"] = "demo"
    values["GITHUB_REPOSITORY"]["value"] = "dlai-sd/waooaw-platform"
    values["RUNNER_RESOURCE_GROUP"]["value"] = "waooaw-demo-runner-rg"
    values["RUNNER_JOB_NAME"]["value"] = "goal006-demo-runner-job"
    values["RUNNER_LABEL"]["value"] = "goal006-demo-private"
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
                        "command": COMMAND,
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
    assert arguments[arguments.index("--private-job-conclusion") + 1] == "failure"


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