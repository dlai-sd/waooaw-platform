"""WC-174 R001, R004, R033: the modes declaration is one additive contract, and the platform never learns an agent's name."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R001, R004, R033, R034
# Constitutional basis: C-023, C-059, C-063, ADR-049, ADR-051

from __future__ import annotations

import ast
import copy
import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/agent-adapters"))

from runtime_contract.employment import EmploymentInterfaceManifest  # noqa: E402

API = ROOT / "architecture/reference/api-specs"
SCHEMA = json.loads((API / "schemas/agent-experience-contract.v1.schema.json").read_text(encoding="utf-8"))
ADAPTER = yaml.safe_load((API / "conversational-employment-domain-adapter.openapi.yaml").read_text(encoding="utf-8"))
RUNTIME = yaml.safe_load((API / "agent-runtime-adapter-v1.openapi.yaml").read_text(encoding="utf-8"))
MANIFESTS = {
    "dma": ROOT / "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json",
    "fixture": ROOT / "src/agent-adapters/fixture_orchard/contracts/employment-interface-manifest.v1.json",
}
VALIDATOR = Draft202012Validator(SCHEMA)


def _load(name: str) -> dict:
    return json.loads(MANIFESTS[name].read_text(encoding="utf-8"))


def _errors(experience: dict) -> list[str]:
    return [error.message for error in VALIDATOR.iter_errors(experience)]


@pytest.mark.parametrize("name", ["dma", "fixture"])
def test_both_declarations_satisfy_the_schema_and_the_adapter_models(name: str) -> None:
    manifest = _load(name)

    assert _errors(manifest["experience"]) == []
    model = EmploymentInterfaceManifest.model_validate(manifest)
    assert [mode.mode_id for mode in model.experience.modes] == ["INDUCT", "GOALS", "OPERATIONS"]


def test_a_declaration_without_modes_still_validates_and_shows_the_wc171_menu() -> None:
    manifest = _load("dma")
    for name in ("modes", "eventLayers", "planLevels", "platforms", "views"):
        manifest["experience"].pop(name)

    assert _errors(manifest["experience"]) == []
    model = EmploymentInterfaceManifest.model_validate(manifest)
    assert model.experience.modes is None and model.experience.navigation


def _break(mutate) -> dict:
    manifest = _load("dma")
    mutate(manifest["experience"])
    return manifest


@pytest.mark.parametrize(
    "mutate",
    [
        lambda experience: experience["modes"].append({**experience["modes"][0], "modeId": "EXTRA"}),
        lambda experience: experience["modes"][0].update(label="<b>Bold</b>"),
        lambda experience: experience["modes"][0].update(readinessSource="ANYTHING"),
        lambda experience: experience["modes"][1]["toolGroups"][0]["tools"][0].update(command="DELETE_EVERYTHING"),
        lambda experience: experience["modes"][1]["gates"][0].update(action="SEND_MONEY"),
        lambda experience: experience["platforms"][0].update(connector="CUSTOM_KEYS"),
        lambda experience: experience["views"].append("TIMELINE"),
        lambda experience: experience["planLevels"].extend([experience["planLevels"][0]] * 3),
        lambda experience: experience["modes"][0].update(unexpected="field"),
    ],
)
def test_schema_and_models_refuse_what_the_contract_forbids(mutate) -> None:
    manifest = _break(mutate)

    assert _errors(manifest["experience"]) != []
    with pytest.raises(ValidationError):
        EmploymentInterfaceManifest.model_validate(manifest)


def test_a_sensitive_layer_cannot_start_on() -> None:
    manifest = _break(lambda experience: experience["eventLayers"][5].update(defaultOn=True))

    with pytest.raises(ValidationError):
        EmploymentInterfaceManifest.model_validate(manifest)


def test_models_refuse_duplicate_ids_and_undeclared_plan_levels() -> None:
    duplicate = _break(lambda experience: experience["modes"].__setitem__(2, copy.deepcopy(experience["modes"][0])))
    level = _break(lambda experience: experience["modes"][1]["toolGroups"][1]["tools"][0].update(planLevel="NOT_A_LEVEL"))
    platform = _break(lambda experience: experience["platforms"].append(copy.deepcopy(experience["platforms"][0])))

    for manifest in (duplicate, level, platform):
        with pytest.raises(ValidationError):
            EmploymentInterfaceManifest.model_validate(manifest)


PAIRS = {
    "ModeDeclaration": "EmploymentExperienceModeV1",
    "ToolGroup": "EmploymentExperienceToolGroupV1",
    "Tool": "EmploymentExperienceToolV1",
    "FlyoutOption": "EmploymentExperienceFlyoutOptionV1",
    "ModeGate": "EmploymentExperienceModeGateV1",
    "EventLayer": "EmploymentExperienceEventLayerV1",
    "PlanLevel": "EmploymentExperiencePlanLevelV1",
    "PlatformDeclaration": "EmploymentExperiencePlatformV1",
}


@pytest.mark.parametrize(("schema_name", "spec_name"), PAIRS.items())
def test_the_adapter_specification_mirrors_the_schema_field_for_field(schema_name: str, spec_name: str) -> None:
    schema = SCHEMA["$defs"][schema_name]
    spec = ADAPTER["components"]["schemas"][spec_name]

    assert set(schema["properties"]) == set(spec["properties"])
    assert set(schema["required"]) == set(spec["required"])
    for field, definition in schema["properties"].items():
        if "enum" in definition:
            assert definition["enum"] == spec["properties"][field]["enum"], field
        if "pattern" in definition:
            assert definition["pattern"] == spec["properties"][field]["pattern"], field
    assert spec["additionalProperties"] is False


def test_the_experience_block_gains_only_the_five_additive_optional_fields() -> None:
    spec = ADAPTER["components"]["schemas"]["EmploymentExperienceManifestV1"]["properties"]
    for field in ("modes", "eventLayers", "planLevels", "platforms", "views"):
        assert field in spec and field in SCHEMA["properties"]
        assert field not in SCHEMA["required"]
    assert SCHEMA["properties"]["modes"]["maxItems"] == 3 and spec["modes"]["maxItems"] == 3


def test_no_port_operation_was_added_for_any_agent() -> None:
    assert sorted(ADAPTER["paths"]) == sorted(
        [
            "/internal/v1/employment-interface/manifest",
            "/internal/v1/relationships/{relationshipId}/employment/induction-requirements",
            "/internal/v1/relationships/{relationshipId}/employment/plan-validation",
            "/internal/v1/relationships/{relationshipId}/employment/material-change-classification",
            "/internal/v1/relationships/{relationshipId}/employment/dependency-isolation",
            "/internal/v1/relationships/{relationshipId}/employment/performance-assessments/{reviewPeriodRef}",
        ]
    )
    assert len(RUNTIME["paths"]) == 12


# ───────────────────────── the platform never learns an agent's name ─────────────────────────

AGENT_NAME = re.compile(
    r"\bDMA\b|DIGITAL_MARKETING|DigitalMarketing|digital[-_]marketing|FIXTURE_ORCHARD|fixture[-_]orchard|orchard", re.IGNORECASE
)
EXCLUDED_PARTS = {"bin", "obj", "node_modules", "generated", "Generated", ".next", "__tests__", "tests", "e2e", "__pycache__"}
# Files that named an agent before WC-174 (catalogue data, the public marketplace, readiness copy and the runtime's
# real-work wiring). WC-174 adds none: this set may only shrink.
BASELINE = {
    "src/business-platform/Catalog/Visitor/waooaw-demo.v1.json",
    "src/business-platform/Controllers/RelationshipWorkspaceController.cs",
    "src/business-platform/Services/EmploymentReadinessService.cs",
    "src/business-platform/Services/WorkloadCredentialVerifier.cs",
    "src/business-platform/Services/WorkloadIdentityClient.cs",
    "src/professional-runtime/real_work_gateway.py",
    "web/components/founder/OfferabilityWorkbench.tsx",
    "web/components/public/ProfessionalJourneyShowcase.tsx",
    "web/lib/pricing-admin-test-data.ts",
    "web/config/blogs.ts",
    "web/config/professionals.ts",
    "web/lib/professional-journey-content.ts",
}


def _content(path: Path) -> str:
    """Source text without the traceability header, which cites contract file names."""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(line for line in lines if not re.match(r"\s*(//|#|--)\s*(Implements|Constitutional basis):", line))


def _shared_sources() -> list[Path]:
    files: list[Path] = []
    for base, suffixes in (
        ("src/business-platform", {".cs", ".json", ".sql"}),
        ("src/professional-runtime", {".py"}),
        ("web", {".ts", ".tsx", ".mjs", ".css"}),
    ):
        for path in (ROOT / base).rglob("*"):
            relative = path.relative_to(ROOT)
            if (
                path.is_file()
                and path.suffix in suffixes
                and not (EXCLUDED_PARTS & set(relative.parts))
                and not re.search(r"\.(test|spec)\.", path.name)
            ):
                files.append(path)
    return files


def test_no_shared_platform_file_names_an_agent_beyond_the_pre_existing_baseline() -> None:
    offenders = {str(path.relative_to(ROOT)) for path in _shared_sources() if AGENT_NAME.search(_content(path))}

    assert offenders - BASELINE == set()


def test_the_wc174_platform_parts_contain_no_agent_name_endpoint_table_or_screen() -> None:
    owned = [
        *(ROOT / "src/business-platform/Services/AgentOperation").glob("*.cs"),
        *(ROOT / "src/business-platform/Controllers").glob("AgentOperation*.cs"),
        ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc174-01-agent-operation.sql",
    ]
    web = [path for path in _shared_sources() if "operation" in str(path.relative_to(ROOT)).lower()]

    assert len(owned) >= 5
    for path in [*owned, *web]:
        assert not AGENT_NAME.search(_content(path)), path


# ───────────────────────── the image boundary ─────────────────────────

FORBIDDEN_IMPORTS = {
    "httpx",
    "requests",
    "aiohttp",
    "urllib3",
    "socket",
    "subprocess",
    "sqlite3",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
    "redis",
    "openai",
    "anthropic",
    "azure",
    "boto3",
    "google",
    "keyring",
    "smtplib",
    "ftplib",
    "shelve",
    "dbm",
}
IMAGE_SOURCES = [
    ROOT / "src/digital-marketing-agent/digital_marketing/operation.py",
    ROOT / "src/agent-adapters/runtime_contract/declarative.py",
    *(ROOT / "src/agent-adapters/fixture_orchard").glob("*.py"),
]


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", IMAGE_SOURCES, ids=lambda path: path.name)
def test_agent_image_code_calls_no_provider_model_or_store_and_keeps_no_durable_state(path: Path) -> None:
    assert _imported_roots(path) & FORBIDDEN_IMPORTS == set()
    source = path.read_text(encoding="utf-8")
    assert not re.search(r"open\([^)]*['\"][wax]\+?b?['\"]", source)
    assert "write_text" not in source and "write_bytes" not in source
    assert not re.search(r"os\.environ\[['\"][A-Z_]*(KEY|TOKEN|PASSWORD|SECRET)", source)


@pytest.mark.parametrize(
    "dockerfile",
    ["src/digital-marketing-agent/Dockerfile", "src/agent-adapters/fixture_orchard/Dockerfile"],
)
def test_each_agent_image_is_pinned_non_root_and_exposes_one_private_port(dockerfile: str) -> None:
    text = (ROOT / dockerfile).read_text(encoding="utf-8")

    assert re.search(r"^FROM python:3\.12-alpine@sha256:[0-9a-f]{64}$", text, re.MULTILINE)
    assert re.search(r"^USER adapter$", text, re.MULTILINE)
    assert re.findall(r"^EXPOSE (\d+)$", text, re.MULTILINE) == ["8443"]
    assert not re.search(r"^ENV .*(KEY|TOKEN|PASSWORD|SECRET)", text, re.MULTILINE | re.IGNORECASE)
    assert "COPY . " not in text


def test_each_agent_image_runs_as_one_isolated_private_service_with_no_public_port_or_key() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    adapters = {name: service for name, service in compose["services"].items() if name.startswith("agent-runtime-adapter-")}

    assert set(adapters) == {
        "agent-runtime-adapter-digital-marketing",
        "agent-runtime-adapter-trading",
        "agent-runtime-adapter-fixture-orchard",
    }
    assert compose["networks"]["agent-runtime-private"]["internal"] is True
    for name, service in adapters.items():
        assert "ports" not in service, name
        assert service["networks"] == ["agent-runtime-private"], name
        assert service["read_only"] is True and service["cap_drop"] == ["ALL"], name
        assert "no-new-privileges:true" in service["security_opt"], name
        assert not [key for key in service.get("environment", {}) if re.search(r"KEY|TOKEN|PASSWORD|SECRET", key)], name


def test_the_publication_contract_is_marked_for_reconciliation_with_the_connection_custody_note() -> None:
    text = (ROOT / "architecture/reference/components/dma-content-and-social-publication-solution-contract.md").read_text(
        encoding="utf-8"
    )

    assert "WC-174 reconciliation" in text
    assert "customer-connection-custody-decision-2026-11-26.md" in text
    note = (ROOT / "architecture/reference/security/customer-connection-custody-decision-2026-11-26.md").read_text(
        encoding="utf-8"
    )
    for required in ("FD7", "experiment", "ADR-021", "one connection interface", "exit"):
        assert required.lower() in note.lower()
