"""Every generated Azure resource name must fit its provider limit in every environment.

Run 40518989967 reached Terraform workload planning before the azurerm provider rejected
``job-demo-temporal-startup-qualification`` (39 characters) against the 32-character Container
Apps job limit. These checks render each generated name offline so the limit fails in CI instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = REPO_ROOT / "infrastructure" / "terraform" / "phase2" / "modules"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "environment-deployment.yaml"
RUNNER_STACK = REPO_ROOT / "infrastructure" / "deployment-stacks" / "goal006-runner" / "main.bicep"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "goal006_verify_deployment.sh"
ENVIRONMENTS = ("demo", "uat", "prod")
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
# Azure naming rules: Microsoft.App containerApps/jobs 2-32, managedEnvironments 2-60,
# Key Vault 3-24, PostgreSQL flexible server 3-63, Redis 1-63, managed identity 3-128.
TERRAFORM_LIMITS = {
    "azurerm_container_app": 32,
    "azurerm_container_app_job": 32,
    "azurerm_container_app_environment": 60,
    "azurerm_key_vault": 24,
    "azurerm_postgresql_flexible_server": 63,
    "azurerm_redis_cache": 63,
    "azurerm_user_assigned_identity": 128,
}
CONTAINER_APPS_LIMIT = 32
MEMBER_NAMES_RULE = (
    'member => member == "agent-runtime-adapter-digital-marketing" ? "ca-${var.environment}-dma"'
    ' : "ca-${var.environment}-${member}"'
)


def release_members() -> list[str]:
    workload = (MODULES / "workload" / "main.tf").read_text(encoding="utf-8")
    block = re.search(r"release_members\s*=\s*toset\(\[(.*?)\]\)", workload, re.S)
    assert block, "workload release_members not found"
    return re.findall(r'"([a-z0-9-]+)"', block.group(1))


def render(expression: str, environment: str) -> list[str]:
    expression = expression.strip()
    if expression == "local.member_names[each.key]":
        workload = (MODULES / "workload" / "main.tf").read_text(encoding="utf-8")
        assert MEMBER_NAMES_RULE in workload, "member_names rule changed; update this renderer"
        return [
            f"ca-{environment}-dma"
            if member == "agent-runtime-adapter-digital-marketing"
            else f"ca-{environment}-{member}"
            for member in release_members()
        ]
    literal = re.fullmatch(r'"([^"]*)"', expression)
    assert literal, f"unsupported Azure name expression: {expression}"
    names = [literal.group(1).replace("${var.environment}", environment).replace("${local.name}", f"waooaw-{environment}")]
    if "${each.key}" in names[0]:
        names = [names[0].replace("${each.key}", member) for member in release_members()]
    for name in names:
        assert "${" not in name, f"unresolved interpolation in Azure name: {expression}"
    return names


def terraform_names() -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for path in sorted(MODULES.glob("*/*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'^resource "(azurerm_[a-z_]+)" "(\w+)" \{\n(.*?)^\}', text, re.S | re.M):
            resource_type, resource_name, body = match.groups()
            if resource_type not in TERRAFORM_LIMITS:
                continue
            name = re.search(r"^  name\s*=\s*(.+)$", body, re.M)
            assert name, f"{resource_type}.{resource_name} has no top-level name"
            found.append((f"{path.relative_to(REPO_ROOT)}:{resource_type}.{resource_name}", resource_type, name.group(1)))
    return found


def test_audit_covers_every_container_app_and_job_resource() -> None:
    found = {resource_type for _, resource_type, _ in terraform_names()}
    assert {"azurerm_container_app", "azurerm_container_app_job", "azurerm_key_vault"} <= found
    assert any(source.endswith("temporal_startup_qualification") for source, _, _ in terraform_names())


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_terraform_azure_names_fit_provider_limits(environment: str) -> None:
    violations = []
    for source, resource_type, expression in terraform_names():
        for name in render(expression, environment):
            if len(name) > TERRAFORM_LIMITS[resource_type] or not NAME_PATTERN.fullmatch(name):
                violations.append(f"{source}: {name} ({len(name)} > {TERRAFORM_LIMITS[resource_type]})")
    assert violations == []


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_workflow_and_script_container_app_job_names_fit_limit(environment: str) -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    templates = set(re.findall(r'job_name="(job-\$\{TARGET_ENVIRONMENT\}-[a-z0-9-]+)"', workflow))
    templates |= {
        f"job-${{TARGET_ENVIRONMENT}}-{component}-migration"
        for component in re.findall(r"(\w+)\|(\w+)\) job_name=\"job-\$\{TARGET_ENVIRONMENT\}-\$\{component\}-migration\"", workflow)[0]
    }
    seeder = re.search(r"SEEDER_JOB: (goal006-\$\{\{ inputs\.environment \}\}-[a-z0-9-]+)", workflow)
    assert seeder
    verify = re.search(r'job_name="(job-\$TARGET_ENVIRONMENT-[a-z0-9-]+)"', VERIFY_SCRIPT.read_text(encoding="utf-8"))
    assert verify
    assert "job-${TARGET_ENVIRONMENT}-temporal-startup" in templates
    assert len(templates) >= 5

    names = [template.replace("${TARGET_ENVIRONMENT}", environment) for template in templates]
    names.append(seeder.group(1).replace("${{ inputs.environment }}", environment))
    names.append(verify.group(1).replace("$TARGET_ENVIRONMENT", environment))
    violations = [f"{name} ({len(name)})" for name in names if len(name) > CONTAINER_APPS_LIMIT or not NAME_PATTERN.fullmatch(name)]
    assert violations == []


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_private_runner_container_app_names_fit_limit(environment: str) -> None:
    stack = RUNNER_STACK.read_text(encoding="utf-8")
    prefix = re.search(r"^var prefix = '(goal006-\$\{environment\}-runner)'$", stack, re.M)
    assert prefix
    suffixes = re.findall(r"'Microsoft\.App/(?:jobs|containerApps)@[^']+' = \{\n  name: '\$\{prefix\}-([a-z0-9-]+)'", stack)
    assert {"job", "broker", "cleanup", "reconciler", "key-import"} <= set(suffixes)

    names = [f"{prefix.group(1).replace('${environment}', environment)}-{suffix}" for suffix in suffixes]
    violations = [f"{name} ({len(name)})" for name in names if len(name) > CONTAINER_APPS_LIMIT]
    assert violations == []


def test_renderer_rejects_the_observed_overlength_name() -> None:
    [name] = render('"job-${var.environment}-temporal-startup-qualification"', "demo")
    assert len(name) == 39 > TERRAFORM_LIMITS["azurerm_container_app_job"]
