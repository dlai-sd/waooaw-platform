"""WC-171 contract checks: the navigation declaration, the alert policy contract and the oversight specification."""

# Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R003, WC171-R004, WC171-R005
# Constitutional basis: C-059, C-063, C-076, ADR-051

from __future__ import annotations

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
WORKBENCH = yaml.safe_load((API / "agent-experience-workbench.openapi.yaml").read_text(encoding="utf-8"))
OVERSIGHT = yaml.safe_load((API / "alerts-oversight.openapi.yaml").read_text(encoding="utf-8"))
MANIFEST = json.loads(
    (ROOT / "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA)


def _experience() -> dict:
    return copy.deepcopy(MANIFEST["experience"])


def _entry(**overrides) -> dict:
    entry = {
        "entryId": "LESSON_PLANS",
        "labelKey": "NAV_LESSON_PLANS",
        "label": "Lesson plans",
        "icon": "plan",
        "order": 5,
        "surface": {"kind": "DOMAIN_BLOCK", "target": "CONTENT_CALENDAR_PREVIEW"},
        "audiences": ["customer_owner"],
        "availabilityGate": "ALWAYS",
    }
    entry.update(overrides)
    return entry


def _errors(experience: dict) -> list[str]:
    return [error.message for error in VALIDATOR.iter_errors(experience)]


def test_dma_declares_four_entries_that_the_schema_accepts() -> None:
    experience = _experience()

    assert _errors(experience) == []
    assert [entry["entryId"] for entry in experience["navigation"]] == [
        "PROFILE_AND_MATURITY",
        "CAMPAIGNS_AND_CALENDAR",
        "PLATFORM_ACCOUNTS",
        "BUSINESS_RESULTS",
    ]


def test_a_legacy_declaration_without_navigation_still_validates() -> None:
    experience = _experience()
    del experience["navigation"]

    assert _errors(experience) == []


def test_a_declaration_for_another_profession_validates_through_the_same_schema() -> None:
    experience = _experience()
    experience["navigation"] = [
        _entry(),
        _entry(
            entryId="STUDENT_PROGRESS",
            labelKey="NAV_STUDENT_PROGRESS",
            label="Student progress",
            icon="results",
            order=15,
            surface={"kind": "BLOCK_COMPOSITION", "blocks": ["METRIC", "LIST"]},
        ),
    ]

    assert _errors(experience) == []


@pytest.mark.parametrize(
    "entry",
    [
        _entry(label="<b>Plans</b>"),
        _entry(label="Plans {TOKEN}"),
        _entry(label="x" * 41),
        _entry(entryId="lower_case"),
        _entry(icon="skull"),
        _entry(order=1000),
        _entry(availabilityGate="WHENEVER"),
        _entry(audiences=[]),
        _entry(surface={"kind": "EMBEDDED", "target": "x"}),
        _entry(surface={"kind": "BLOCK_COMPOSITION", "blocks": ["SCRIPT"]}),
        _entry(extra="layout"),
    ],
)
def test_the_schema_refuses_markup_free_text_unknown_kinds_and_layout(entry: dict) -> None:
    experience = _experience()
    experience["navigation"] = [entry]

    assert _errors(experience)


def test_more_than_twelve_entries_are_refused() -> None:
    experience = _experience()
    experience["navigation"] = [_entry(entryId=f"ENTRY_{index:02d}", labelKey=f"NAV_ENTRY_{index:02d}") for index in range(13)]

    assert _errors(experience)


def test_the_adapter_specification_carries_the_same_navigation_contract() -> None:
    schemas = ADAPTER["components"]["schemas"]
    entry = schemas["EmploymentExperienceNavigationEntryV1"]
    canonical = SCHEMA["$defs"]["NavigationEntry"]

    assert "navigation" in schemas["EmploymentExperienceManifestV1"]["properties"]
    assert set(entry["properties"]) == set(canonical["properties"])
    assert entry["properties"]["icon"]["enum"] == canonical["properties"]["icon"]["enum"]
    assert entry["properties"]["availabilityGate"]["enum"] == canonical["properties"]["availabilityGate"]["enum"]
    assert entry["properties"]["label"]["pattern"] == canonical["properties"]["label"]["pattern"]
    assert (
        schemas["EmploymentExperienceNavigationSurfaceV1"]["properties"]["kind"]["enum"]
        == canonical_surface_kinds()
    )


def canonical_surface_kinds() -> list[str]:
    return SCHEMA["$defs"]["NavigationSurface"]["properties"]["kind"]["enum"]


def test_the_workbench_projection_offers_navigation_as_an_optional_field() -> None:
    projection = WORKBENCH["components"]["schemas"]["WorkbenchProjectionV1"]

    assert "navigation" in projection["properties"]
    assert "navigation" not in projection["required"]
    assert WORKBENCH["components"]["schemas"]["WorkbenchNavigationEntryV1"]["properties"]["available"]


def test_the_runtime_contract_model_admits_dma_and_refuses_a_bad_entry() -> None:
    EmploymentInterfaceManifest.model_validate(MANIFEST)
    broken = copy.deepcopy(MANIFEST)
    broken["experience"]["navigation"][0]["label"] = "<script>"

    with pytest.raises(ValidationError):
        EmploymentInterfaceManifest.model_validate(broken)


def _controller_routes(name: str) -> set[tuple[str, str]]:
    text = (ROOT / "src/business-platform/Controllers" / name).read_text(encoding="utf-8")
    prefix = re.search(r'\[Route\("([^"]+)"\)\]', text)
    assert prefix is not None
    routes = set()
    for verb, path in re.findall(r'\[Http(Get|Post|Put)\("([^"]+)"\)\]', text):
        full = f"/{prefix.group(1)}/{path}"
        routes.add((verb.lower(), re.sub(r":guid", "", full)))
    return routes


@pytest.mark.parametrize("controller", ["AlertControlsController.cs", "OperationsController.cs"])
def test_every_new_business_platform_route_is_in_the_oversight_specification(controller: str) -> None:
    documented = {
        (method, path)
        for path, item in OVERSIGHT["paths"].items()
        for method in item
        if method in {"get", "post", "put"}
    }

    missing = _controller_routes(controller) - documented

    assert not missing


def test_the_oversight_specification_names_no_secret_or_recipient_fields() -> None:
    properties = {
        name.lower()
        for schema in OVERSIGHT["components"]["schemas"].values()
        for name in schema.get("properties", {})
    }

    assert not properties & {"recipient", "phone", "accesstoken", "password", "payload", "body", "destinationnumber"}


def test_no_agent_name_appears_in_shared_navigation_or_alert_code() -> None:
    shared = [
        ROOT / "web/lib/navigation-model.ts",
        ROOT / "web/components/workbench/AgentContextMenu.tsx",
        ROOT / "web/components/workbench/DeclaredSurface.tsx",
        ROOT / "web/components/shell/ProtectedAppShell.tsx",
        ROOT / "web/lib/alert-controls-client.ts",
        ROOT / "src/business-platform/Services/Alerts/AlertPolicy.cs",
    ]
    names = re.compile(r"\b(dma|digital[_ -]?marketing|marketing[_ -]?maturity|content[_ -]?calendar)\b", re.IGNORECASE)

    for path in shared:
        assert not names.search(path.read_text(encoding="utf-8")), path.name
