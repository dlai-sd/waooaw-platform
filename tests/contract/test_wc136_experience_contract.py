"""WC-136 C2 contract suite: experience contract, block vocabulary v2 and the three OpenAPI slices."""

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-01
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-04
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-05
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-07
# Constitutional basis: C-059, C-063, C-065, ADR-051, ADR-052

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/agent-adapters"))

from runtime_contract.employment import EmploymentInterfaceManifest, ExperienceManifest  # noqa: E402

API = ROOT / "architecture/reference/api-specs"
DMA_CONTRACTS = ROOT / "src/digital-marketing-agent/contracts"
REGISTRY_PATH = ROOT / "infrastructure/workload-identity/registry.yaml"
CATALOG_PATH = ROOT / "validation/engineering-validation.yaml"

WORKBENCH = "agent-experience-workbench.openapi.yaml"
PRICING = "pricing-admin-business-platform.openapi.yaml"
WBE_PRICING = "wbe-pricing-admin.openapi.yaml"
VISITOR = "visitor-conversation-business-platform.openapi.yaml"
FIXTURES = "agent-experience-negative-fixtures.yaml"
OPENAPI_SPECS = [WORKBENCH, PRICING, WBE_PRICING]
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
MUTATING_METHODS = ("post", "put", "patch", "delete")
V1_BLOCK_TYPES = {"TEXT", "CHOICES", "LIST", "LINK"}
ALL_BLOCK_TYPES = V1_BLOCK_TYPES | {"STATUS", "METRIC", "PLAN", "DECISION", "FORM", "EVIDENCE", "DOMAIN"}
PROBLEM_SCHEMA = {
    WORKBENCH: "WorkbenchProblemDetailV1",
    PRICING: "PricingProblemDetailV1",
    WBE_PRICING: "PricingProblemDetailV1",
}
EXPECTED_TAG_COUNTS = {
    WORKBENCH: {"Workbench": 23, "Subscription": 1, "Marketplace Packages": 1},
    PRICING: {"Pricing Drafts": 8, "Pricing Versions": 4, "Pricing Safety": 3, "Pricing Reports": 3},
    WBE_PRICING: {"Pricing Drafts": 8, "Pricing Versions": 4, "Pricing Safety": 3, "Pricing Reports": 3},
}
WORKBENCH_CAPABILITIES = {"1.7", "2.5", "2.7", "4.5", "5.3", "5.4", "5.5", "6.5", "6.6", "9.1", "9.2"}
CUSTOMER_FORBIDDEN_PROPERTIES = {
    "rawCostPaise",
    "costPaise",
    "unitCostPaise",
    "costFloorPaise",
    "recipe",
    "marginPercent",
    "minimumMarginPct",
    "infrastructureSharePaise",
    "priceAllocationPaise",
    "fxBufferPct",
    "opsOverheadPct",
    "riskPremiumPct",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _spec(name: str) -> Any:
    return yaml.safe_load((API / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _spec_fixtures() -> Any:
    return yaml.safe_load((API / FIXTURES).read_text(encoding="utf-8"))


def _resolve_pointer(document: Any, pointer: str) -> Any:
    node = document
    for part in (item for item in pointer.split("/") if item):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _iter_refs(node: Any):
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str):
            yield reference
        for value in node.values():
            yield from _iter_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_refs(value)


def _inline_external_refs(node: Any) -> Any:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str) and not reference.startswith("#"):
            file_name, pointer = reference.split("#", maxsplit=1)
            return copy.deepcopy(_resolve_pointer(_spec(file_name.removeprefix("./")), pointer))
        return {key: _inline_external_refs(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline_external_refs(item) for item in node]
    return node


def _schema_validator(spec_name: str, schema_ref: str) -> Draft202012Validator:
    spec = _spec(spec_name)
    wrapper = {"$ref": schema_ref, "components": _inline_external_refs(spec["components"])}
    return Draft202012Validator(wrapper)


def _operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (route, method, operation)
        for route, item in spec["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]


def _resolve_local(spec: dict[str, Any], node: Any) -> Any:
    if isinstance(node, dict) and isinstance(node.get("$ref"), str):
        return _resolve_pointer(spec, node["$ref"].split("#", maxsplit=1)[1])
    return node


def _parameters(spec: dict[str, Any], route: str, operation: dict[str, Any]) -> list[dict[str, Any]]:
    declared = [*spec["paths"][route].get("parameters", []), *operation.get("parameters", [])]
    return [_resolve_local(spec, parameter) for parameter in declared]


def _reachable_property_names(spec: dict[str, Any], schema_name: str) -> set[str]:
    names: set[str] = set()
    visited: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/") and reference not in visited:
                visited.add(reference)
                visit(_resolve_pointer(spec, reference[1:]))
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(properties)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(spec["components"]["schemas"][schema_name])
    return names


def _set(document: Any, path: tuple[Any, ...], value: Any) -> None:
    node = document
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value


def _delete(document: Any, path: tuple[Any, ...]) -> None:
    node = document
    for part in path[:-1]:
        node = node[part]
    del node[path[-1]]


MANIFEST = _json(DMA_CONTRACTS / "employment-interface-manifest.v1.json")
CATALOGUE = _json(DMA_CONTRACTS / "experience-components.v1.json")
CONTENT_SOCIAL = _json(DMA_CONTRACTS / "content-social-manifest.v1.json")
AEC_SCHEMA = _json(API / "schemas/agent-experience-contract.v1.schema.json")
BLOCKS_SCHEMA = _json(API / "schemas/experience-blocks.v2.schema.json")
AEC_VALIDATOR = Draft202012Validator(AEC_SCHEMA)
BLOCKS_VALIDATOR = Draft202012Validator(BLOCKS_SCHEMA)


def _experience() -> dict[str, Any]:
    return copy.deepcopy(MANIFEST["experience"])


def _component(experience: dict[str, Any], component_id: str) -> dict[str, Any]:
    return next(item for item in experience["components"] if item["componentId"] == component_id)


# --- C2-01 Agent Experience Contract schema and model -------------------------------------------


def test_wc136_r006_the_aec_schema_is_a_valid_closed_json_schema() -> None:
    Draft202012Validator.check_schema(AEC_SCHEMA)
    Draft202012Validator.check_schema(BLOCKS_SCHEMA)

    assert AEC_SCHEMA["additionalProperties"] is False
    assert set(AEC_SCHEMA["required"]) == {
        "contractVersion",
        "vocabularyRef",
        "goalTypes",
        "plan",
        "operate",
        "monitor",
        "domainBlocks",
        "components",
        "audiences",
        "modalities",
        "channelSupport",
        "conformanceScenarios",
    }


def test_wc136_r006_the_dma_experience_declaration_validates_against_the_schema() -> None:
    assert list(AEC_VALIDATOR.iter_errors(MANIFEST["experience"])) == []


@pytest.mark.parametrize("field", AEC_SCHEMA["required"])
def test_wc136_r006_removing_any_required_field_fails(field: str) -> None:
    experience = _experience()
    del experience[field]

    assert not AEC_VALIDATOR.is_valid(experience)


@pytest.mark.parametrize(
    "path",
    [
        ("plan", "milestoneTypes"),
        ("operate", "cadence"),
        ("operate", "approvalModes"),
        ("monitor", "tiles"),
        ("goalTypes", 0, "measures"),
        ("goalTypes", 0, "measures", 0, "freshnessSeconds"),
        ("components", 0, "countedOn"),
        ("components", 0, "availability"),
        ("channelSupport", "mobile"),
        ("domainBlocks", 0, "fallbackBlocks"),
        ("vocabularyRef", "contractDigest"),
    ],
    ids=lambda path: ".".join(str(part) for part in path),
)
def test_wc136_r006_removing_a_nested_required_field_fails(path: tuple[Any, ...]) -> None:
    experience = _experience()
    _delete(experience, path)

    assert not AEC_VALIDATOR.is_valid(experience)


@pytest.mark.parametrize(
    "path",
    [(), ("plan",), ("components", 0), ("monitor", "alerts", 0), ("channelSupport",), ("vocabularyRef",)],
    ids=lambda path: ".".join(str(part) for part in path) or "root",
)
def test_wc136_r006_an_unknown_field_fails(path: tuple[Any, ...]) -> None:
    experience = _experience()
    node: Any = experience
    for part in path:
        node = node[part]
    node["unexpectedField"] = "x"

    assert not AEC_VALIDATOR.is_valid(experience)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("audiences", 0), "admin"),
        (("modalities", 0), "braille"),
        (("channelSupport", "web", 0), "WIDGET"),
        (("components", 0, "kind"), "FREE"),
        (("components", 0, "availability"), "MAYBE"),
        (("monitor", "alerts", 0, "severity"), "FATAL"),
        (("monitor", "tiles", 0, "blockType"), "TEXT"),
        (("domainBlocks", 0, "fallbackBlocks", 0), "STATUS"),
        (("domainBlocks", 0, "version"), 0),
        (("goalTypes", 0, "measures", 0, "freshnessSeconds"), 0),
        (("vocabularyRef", "contractDigest"), "not-a-digest"),
    ],
    ids=lambda value: ".".join(str(part) for part in value) if isinstance(value, tuple) else None,
)
def test_wc136_r006_enum_and_range_violations_fail(path: tuple[Any, ...], value: Any) -> None:
    experience = _experience()
    _set(experience, path, value)

    assert not AEC_VALIDATOR.is_valid(experience)


def test_wc136_r006_a_selected_component_without_a_selectable_dimension_fails_schema_and_model() -> None:
    experience = _experience()
    del _component(experience, "SOCIAL_OBSERVATION")["selectableDimension"]

    assert not AEC_VALIDATOR.is_valid(experience)
    with pytest.raises(ValidationError):
        ExperienceManifest.model_validate(experience)


def test_wc136_r006_the_pydantic_model_accepts_the_dma_declaration_and_the_full_manifest() -> None:
    model = ExperienceManifest.model_validate(MANIFEST["experience"])
    manifest = EmploymentInterfaceManifest.model_validate(MANIFEST)

    assert len(model.components) == 7
    assert manifest.experience is not None
    assert manifest.experience.contract_version == MANIFEST["experience"]["contractVersion"]
    assert manifest.manifest_version == "1.1.0"


def test_wc136_r006_the_model_rejects_duplicate_component_ids() -> None:
    experience = _experience()
    experience["components"][1]["componentId"] = experience["components"][0]["componentId"]

    with pytest.raises(ValidationError):
        ExperienceManifest.model_validate(experience)


def test_wc136_r006_the_model_rejects_a_component_whose_skill_is_not_operated() -> None:
    experience = _experience()
    _component(experience, "CONTENT_PLAN")["skillId"] = "SKILL_THAT_IS_NOT_OPERATED"

    with pytest.raises(ValidationError):
        ExperienceManifest.model_validate(experience)


def test_wc136_r006_the_model_rejects_unknown_fields() -> None:
    experience = _experience()
    experience["unexpectedField"] = "x"

    with pytest.raises(ValidationError):
        ExperienceManifest.model_validate(experience)


def test_wc136_r006_the_manifest_without_an_experience_block_still_validates_as_before() -> None:
    manifest = copy.deepcopy(MANIFEST)
    del manifest["experience"]

    assert EmploymentInterfaceManifest.model_validate(manifest).experience is None


# --- C2-02 DMA experience declaration -----------------------------------------------------------


def test_wc136_r006_the_manifest_is_version_1_1_0_and_keeps_the_wc116_qualification_record() -> None:
    assert MANIFEST["manifestVersion"] == "1.1.0"
    qualification = MANIFEST["conformanceScenarios"][0]
    assert qualification["scenarioId"] == "WC116-PACKAGE-A-QUALIFICATION"
    assert qualification["validatedManifestVersion"] == "1.0.0"


def test_wc136_r006_component_ids_equal_the_content_social_cost_units() -> None:
    cost_units = {skill["costUnit"] for skill in CONTENT_SOCIAL["skills"] if "costUnit" in skill}
    package_components = {item for items in CATALOGUE["packageComponents"].values() for item in items}
    declared = {item["componentId"] for item in MANIFEST["experience"]["components"]}

    assert cost_units <= declared
    assert package_components == cost_units
    for skill in CONTENT_SOCIAL["skills"]:
        if "costUnit" in skill:
            assert skill["costUnit"] in CATALOGUE["packageComponents"][skill["package"]]


def test_wc136_r006_unavailable_and_default_off_components_are_declared_honestly() -> None:
    experience = _experience()

    assert _component(experience, "AD_BOOST")["availability"] == "UNAVAILABLE"
    assert _component(experience, "PROACTIVE_MESSAGE")["availability"] == "DEFAULT_OFF"
    assert not [item for item in experience["components"] if item["availability"] == "AVAILABLE"]
    assert CATALOGUE["excludedPackages"] == ["C", "D", "E"]


def test_wc136_r006_inline_components_equal_the_referenced_catalogue() -> None:
    inline = {item["componentId"]: item for item in MANIFEST["experience"]["components"]}
    catalogue = {item["componentId"]: item for item in CATALOGUE["components"]}

    assert inline == catalogue


def test_wc136_r006_the_declaration_binds_components_to_operated_skills_and_scenarios() -> None:
    experience = MANIFEST["experience"]
    operated = {entry["skillId"] for entry in experience["operate"]["cadence"]}

    for component in experience["components"]:
        if "skillId" in component:
            assert component["skillId"] in operated
    assert all(re.fullmatch(r"WC136-(DMA|PRICING)-[A-Z][0-9]{2}", item) for item in experience["conformanceScenarios"])
    assert len(experience["conformanceScenarios"]) == len(set(experience["conformanceScenarios"]))


def test_wc136_r006_whatsapp_never_declares_a_block_type_that_needs_a_larger_surface() -> None:
    support = MANIFEST["experience"]["channelSupport"]

    assert set(support["whatsapp"]) <= set(support["web"])
    assert {"PLAN", "FORM", "EVIDENCE", "DOMAIN"}.isdisjoint(support["whatsapp"])


def test_wc136_r006_every_contract_digest_reference_resolves_to_its_file() -> None:
    experience = MANIFEST["experience"]
    references = [
        *MANIFEST["governance"].values(),
        MANIFEST["induction"]["domainSummaryAdapter"],
        MANIFEST["planning"]["planAdapter"],
        MANIFEST["operations"]["outcomeAdapter"],
        MANIFEST["operations"]["billingProfile"],
        MANIFEST["operations"]["degradationProfile"],
        experience["vocabularyRef"],
        experience["componentCatalogueRef"],
    ]

    for reference in references:
        path = ROOT / reference["contractRef"].split("#", maxsplit=1)[0]
        assert path.is_file(), reference["contractRef"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["contractDigest"], reference["contractRef"]


# --- C2-03 Experience block vocabulary v2 -------------------------------------------------------


def _reply(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"schemaVersion": "2.0", "state": "WORKBENCH", "cursor": "cursor-000001", "blocks": list(blocks)}


def _block(block_id: str, block_type: str, data: dict[str, Any], **extra: Any) -> dict[str, Any]:
    fallback = extra.pop("fallback", [] if block_type in V1_BLOCK_TYPES else [_text_fallback()])
    block = {
        "id": block_id,
        "type": block_type,
        "version": 1,
        "sensitivity": "CUSTOMER",
        "data": data,
        "fallback": fallback,
    }
    block.update(extra)
    return block


def _text_fallback() -> dict[str, Any]:
    return {"type": "TEXT", "data": {"text": "Open the workbench to see this."}}


def _sample_blocks() -> dict[str, dict[str, Any]]:
    data = {
        "TEXT": {"text": "Your plan is on track."},
        "CHOICES": {"choices": [{"choiceId": "c1", "label": "Yes"}, {"choiceId": "c2", "label": "No"}]},
        "LIST": {"rows": [{"rowId": "r1", "title": "Profile", "description": "Confirmed"}]},
        "LINK": {"label": "Open workbench", "destinationRef": "handoff:abcdef12"},
        "STATUS": {"itemRef": "item-1", "state": "IN_PROGRESS", "owner": "Agent", "freshness": "CURRENT"},
        "METRIC": {
            "measureId": "PROFILE_COVERAGE",
            "value": 80,
            "unit": "PERCENT",
            "target": 100,
            "trend": "UP",
            "freshness": "CURRENT",
        },
        "PLAN": {
            "planVersion": "plan-1",
            "milestones": [{"milestoneId": "m1", "title": "Profile confirmed", "dueMeaning": "Before the first plan"}],
            "calendar": [{"date": "2026-07-31", "title": "Month-end review"}],
        },
        "DECISION": {
            "decisionId": "d1",
            "effect": "Approve the content plan",
            "authority": "Account owner",
            "confirmLabel": "Approve",
            "cancelLabel": "Not now",
        },
        "FORM": {"formId": "f1", "fields": [{"fieldId": "city", "label": "City", "type": "TEXT", "required": True}]},
        "EVIDENCE": {"evidenceRef": "ev-1", "summary": "Plan accepted", "producedAt": "2026-05-01T10:00:00Z"},
        "DOMAIN": {"domainBlockId": "MARKETING_MATURITY_SUMMARY", "payload": {"score": 3}},
    }
    return {block_type: _block(f"b-{block_type.lower()}", block_type, payload) for block_type, payload in data.items()}


SAMPLE_BLOCKS = _sample_blocks()


def render_with_fallback(block: dict[str, Any], supported: dict[str, int]) -> list[dict[str, Any]]:
    """Reference behaviour: a renderer shows a block it knows at a version it knows, otherwise the fallback."""
    if block["type"] in supported and block["version"] <= supported[block["type"]]:
        return [block]
    return list(block["fallback"])


def _has_unique_choice_labels(reply: dict[str, Any]) -> bool:
    for block in reply["blocks"]:
        groups = [block, *block["fallback"]]
        for group in groups:
            if group["type"] == "CHOICES":
                labels = [choice["label"] for choice in group["data"]["choices"]]
                if len(labels) != len(set(labels)):
                    return False
    return True


def test_wc136_r007_the_samples_cover_exactly_the_eleven_block_types() -> None:
    declared = set(BLOCKS_SCHEMA["$defs"]["Block"]["properties"]["type"]["enum"])

    assert declared == ALL_BLOCK_TYPES
    assert set(SAMPLE_BLOCKS) == ALL_BLOCK_TYPES


@pytest.mark.parametrize("block_type", sorted(ALL_BLOCK_TYPES))
def test_wc136_r007_every_block_type_validates_with_a_minimal_example(block_type: str) -> None:
    reply = _reply(SAMPLE_BLOCKS[block_type])

    assert list(BLOCKS_VALIDATOR.iter_errors(reply)) == []


def test_wc136_r007_spoken_and_label_forms_are_accepted_and_bounded() -> None:
    block = _block("b1", "TEXT", {"text": "Hello"}, spoken="Hello there", label="Greeting")

    assert BLOCKS_VALIDATOR.is_valid(_reply(block))
    assert not BLOCKS_VALIDATOR.is_valid(_reply({**block, "spoken": "x" * 1025}))
    assert not BLOCKS_VALIDATOR.is_valid(_reply({**block, "label": "x" * 121}))


def test_wc136_r007_a_reply_may_carry_six_blocks_and_one_link() -> None:
    six = [_block(f"b{index}", "TEXT", {"text": "Hello"}) for index in range(6)]
    six[5] = _block("link", "LINK", SAMPLE_BLOCKS["LINK"]["data"])

    assert BLOCKS_VALIDATOR.is_valid(_reply(*six))


def _limit_violations() -> dict[str, dict[str, Any]]:
    text = _block("t", "TEXT", {"text": "Hello"})
    link = SAMPLE_BLOCKS["LINK"]
    choices = lambda count: {  # noqa: E731
        "choices": [{"choiceId": f"c{index}", "label": f"Label {index}"} for index in range(count)]
    }
    return {
        "seven blocks": _reply(*[{**text, "id": f"b{index}"} for index in range(7)]),
        "two links": _reply(link, {**link, "id": "other-link"}),
        "four choices": _reply(_block("c", "CHOICES", choices(4))),
        "no choices": _reply(_block("c", "CHOICES", choices(0))),
        "eleven rows": _reply(
            _block("l", "LIST", {"rows": [{"rowId": f"r{index}", "title": "Row"} for index in range(11)]})
        ),
        "choice label over twenty characters": _reply(
            _block("c", "CHOICES", {"choices": [{"choiceId": "c1", "label": "L" * 21}]})
        ),
        "list title over twenty four characters": _reply(
            _block("l", "LIST", {"rows": [{"rowId": "r1", "title": "T" * 25}]})
        ),
        "text over 1024 characters": _reply(_block("t", "TEXT", {"text": "x" * 1025})),
        "link carries a URL": _reply(
            _block("k", "LINK", {"label": "Open", "destinationRef": "https://example.test/path"})
        ),
        "fallback holds a non v1 type": _reply(
            _block("t", "TEXT", {"text": "Hello"}, fallback=[{"type": "STATUS", "data": SAMPLE_BLOCKS["STATUS"]["data"]}])
        ),
        "fallback text without text": _reply(_block("s", "STATUS", SAMPLE_BLOCKS["STATUS"]["data"], fallback=[{"type": "TEXT", "data": {}}])),
        "five fallback blocks": _reply(_block("t", "TEXT", {"text": "Hello"}, fallback=[_text_fallback()] * 5)),
        "unknown sensitivity": _reply(_block("t", "TEXT", {"text": "Hello"}, sensitivity="SECRET")),
        "unknown block type": _reply(_block("t", "HOLOGRAM", {"text": "Hello"})),
        "domain without fallback": _reply(_block("d", "DOMAIN", SAMPLE_BLOCKS["DOMAIN"]["data"], fallback=[])),
        "domain without block id": _reply(_block("d", "DOMAIN", {"payload": {"score": 3}})),
        "block with an authority field": _reply({**SAMPLE_BLOCKS["TEXT"], "authority": "FOUNDER"}),
        "decision data with an approval flag": _reply(
            _block("d", "DECISION", {**SAMPLE_BLOCKS["DECISION"]["data"], "approved": True})
        ),
        "status with an unknown item state": _reply(
            _block("s", "STATUS", {**SAMPLE_BLOCKS["STATUS"]["data"], "state": "DONE_AND_DUSTED"})
        ),
        "version one reply schema": {**_reply(), "schemaVersion": "1.0"},
        "reply without cursor": {key: value for key, value in _reply().items() if key != "cursor"},
        "reply with an extra field": {**_reply(), "layout": "grid"},
    }


@pytest.mark.parametrize("name", sorted(_limit_violations()))
def test_wc136_r007_each_limit_violation_fails(name: str) -> None:
    assert not BLOCKS_VALIDATOR.is_valid(_limit_violations()[name]), name


def test_wc136_r007_unique_choice_labels_are_enforced_by_the_reference_helper() -> None:
    unique = _reply(SAMPLE_BLOCKS["CHOICES"])
    duplicate = _reply(
        _block("c", "CHOICES", {"choices": [{"choiceId": "c1", "label": "Yes"}, {"choiceId": "c2", "label": "Yes"}]})
    )
    duplicate_in_fallback = _reply(
        _block(
            "s",
            "STATUS",
            SAMPLE_BLOCKS["STATUS"]["data"],
            fallback=[
                {
                    "type": "CHOICES",
                    "data": {"choices": [{"choiceId": "c1", "label": "Same"}, {"choiceId": "c2", "label": "Same"}]},
                }
            ],
        )
    )

    assert _has_unique_choice_labels(unique)
    assert not _has_unique_choice_labels(duplicate)
    assert not _has_unique_choice_labels(duplicate_in_fallback)


def test_wc136_r007_a_v1_reply_still_validates_as_v1_and_is_not_a_v2_reply() -> None:
    v1_reply = {
        "schemaVersion": "1.0",
        "state": "DISCOVER",
        "contentVersion": "2026-05-01",
        "blocks": [
            {"type": "TEXT", "text": "Hello"},
            {"type": "CHOICES", "choices": [{"id": "c1", "label": "Yes"}]},
            {"type": "LIST", "listTitle": "Options", "rows": [{"id": "r1", "title": "One", "description": "First"}]},
            {"type": "LINK", "label": "Open", "url": "https://example.test/x"},
        ],
    }
    v1_validator = _schema_validator(VISITOR, "#/components/schemas/VisitorReplyV1")

    assert list(v1_validator.iter_errors(v1_reply)) == []
    assert not BLOCKS_VALIDATOR.is_valid(v1_reply)
    assert not v1_validator.is_valid(_reply(SAMPLE_BLOCKS["TEXT"]))


def test_wc136_r007_v2_text_choices_list_and_link_keep_their_v1_limits() -> None:
    v1 = _spec(VISITOR)["components"]["schemas"]
    v2 = BLOCKS_SCHEMA["$defs"]

    assert v2["TextData"]["properties"]["text"]["maxLength"] == v1["VisitorReplyBlockV1"]["properties"]["text"]["maxLength"]
    assert v2["ChoicesData"]["properties"]["choices"]["maxItems"] == v1["VisitorReplyBlockV1"]["properties"]["choices"]["maxItems"]
    assert v2["ListData"]["properties"]["rows"]["maxItems"] == v1["VisitorReplyBlockV1"]["properties"]["rows"]["maxItems"]
    assert v2["LinkData"]["properties"]["label"]["maxLength"] == v1["VisitorReplyBlockV1"]["properties"]["label"]["maxLength"]
    assert BLOCKS_SCHEMA["properties"]["blocks"]["maxItems"] == v1["VisitorReplyV1"]["properties"]["blocks"]["maxItems"]


def test_wc136_r007_render_with_fallback_shows_known_blocks_and_degrades_the_rest() -> None:
    known = {block_type: 1 for block_type in ALL_BLOCK_TYPES}
    v1_only = {block_type: 1 for block_type in V1_BLOCK_TYPES}
    status = SAMPLE_BLOCKS["STATUS"]
    newer = {**status, "version": 2}
    future = {**status, "type": "HOLOGRAM"}

    assert render_with_fallback(status, known) == [status]
    assert render_with_fallback(status, v1_only) == status["fallback"]
    assert render_with_fallback(newer, known) == status["fallback"]
    assert render_with_fallback(future, known) == status["fallback"]
    assert render_with_fallback({**future, "fallback": []}, known) == []


@pytest.mark.parametrize("channel", ["web", "whatsapp", "mobile"])
def test_wc136_r007_every_channel_renders_every_block_type_through_its_declared_support(channel: str) -> None:
    supported = {block_type: 1 for block_type in MANIFEST["experience"]["channelSupport"][channel]}

    for block_type, block in SAMPLE_BLOCKS.items():
        rendered = render_with_fallback(block, supported)
        assert rendered, block_type
        if block_type in supported:
            assert rendered == [block]
        else:
            assert {item["type"] for item in rendered} <= V1_BLOCK_TYPES


# --- C2-04, C2-05 OpenAPI structure ---------------------------------------------------------------


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_openapi_documents_are_31_and_their_schemas_are_valid_json_schema(spec_name: str) -> None:
    spec = _spec(spec_name)

    assert str(spec["openapi"]).startswith("3.1")
    assert spec["info"]["version"] == "1.0.0"
    assert spec["servers"]
    for schema in _inline_external_refs(spec["components"]["schemas"]).values():
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_operation_ids_are_unique_and_generator_safe(spec_name: str) -> None:
    ids = [operation["operationId"] for _, _, operation in _operations(_spec(spec_name))]

    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z][A-Za-z0-9]*", item) for item in ids)


def test_wc136_r008_operation_ids_are_unique_across_the_three_slices() -> None:
    ids = [operation["operationId"] for name in OPENAPI_SPECS for _, _, operation in _operations(_spec(name))]

    assert len(ids) == len(set(ids))
    assert len(_operations(_spec(WORKBENCH))) == 26
    assert len(_operations(_spec(PRICING))) == 18
    assert len(_operations(_spec(WBE_PRICING))) == 18


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_every_operation_has_exactly_one_declared_tag_mapping_to_an_api_class(spec_name: str) -> None:
    spec = _spec(spec_name)
    declared = {item["name"] for item in spec["tags"]}
    counts: dict[str, int] = {}
    for _, _, operation in _operations(spec):
        assert len(operation["tags"]) == 1
        assert operation["tags"][0] in declared
        assert operation["summary"]
        counts[operation["tags"][0]] = counts.get(operation["tags"][0], 0) + 1

    assert counts == EXPECTED_TAG_COUNTS[spec_name]
    assert declared == set(EXPECTED_TAG_COUNTS[spec_name])


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_every_ref_resolves_locally_and_across_files(spec_name: str) -> None:
    spec = _spec(spec_name)
    external = set()

    for reference in _iter_refs(spec):
        if reference.startswith("#"):
            assert _resolve_pointer(spec, reference[1:]) is not None, reference
        else:
            file_name, pointer = reference.split("#", maxsplit=1)
            assert (API / file_name.removeprefix("./")).is_file(), reference
            assert _resolve_pointer(_spec(file_name.removeprefix("./")), pointer) is not None, reference
            external.add(file_name.removeprefix("./"))

    if spec_name == WORKBENCH:
        assert external == {
            "conversational-employment-business-platform.openapi.yaml",
            "customer-engagement-workspace-business-platform.openapi.yaml",
        }
    else:
        assert not external


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_every_path_parameter_is_declared_and_required(spec_name: str) -> None:
    spec = _spec(spec_name)

    for route, _, operation in _operations(spec):
        declared = {item["name"]: item for item in _parameters(spec, route, operation) if item["in"] == "path"}
        for name in re.findall(r"{([A-Za-z]+)}", route):
            assert declared[name]["required"] is True, (route, name)
        assert set(declared) == set(re.findall(r"{([A-Za-z]+)}", route)), route


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_mutating_operations_require_idempotency_and_correlation_headers(spec_name: str) -> None:
    spec = _spec(spec_name)

    for route, method, operation in _operations(spec):
        headers = {
            item["name"].lower(): item.get("required", False)
            for item in _parameters(spec, route, operation)
            if item["in"] == "header"
        }
        if method in MUTATING_METHODS:
            assert headers.get("idempotency-key") is True, operation["operationId"]
            assert headers.get("x-correlation-id") is True, operation["operationId"]
        else:
            assert "idempotency-key" not in headers, operation["operationId"]


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_every_operation_documents_problem_json_errors(spec_name: str) -> None:
    spec = _spec(spec_name)

    for _, _, operation in _operations(spec):
        errors = {
            str(code): _resolve_local(spec, response)
            for code, response in operation["responses"].items()
            if str(code)[0] in "45"
        }
        assert errors, operation["operationId"]
        for response in errors.values():
            schema = response["content"]["application/problem+json"]["schema"]
            assert schema["$ref"] == f"#/components/schemas/{PROBLEM_SCHEMA[spec_name]}"
        assert any(str(code)[0] == "2" for code in operation["responses"]), operation["operationId"]


@pytest.mark.parametrize("spec_name", OPENAPI_SPECS)
def test_wc136_r008_money_fields_are_integer_paise(spec_name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                for name, schema in properties.items():
                    if re.search(r"paise$", name, re.IGNORECASE):
                        assert schema.get("type") == "integer", name
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(_spec(spec_name)["components"]["schemas"])


# --- C2-04 Workbench ------------------------------------------------------------------------------


def test_wc136_r008_every_workbench_operation_is_capability_traced_bearer_secured_and_public() -> None:
    spec = _spec(WORKBENCH)

    assert spec["security"] == [{"bearerAuth": []}]
    assert spec["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    seen: set[str] = set()
    for route, _, operation in _operations(spec):
        capabilities = operation["x-capability"]
        assert isinstance(capabilities, list) and capabilities, operation["operationId"]
        assert set(capabilities) <= WORKBENCH_CAPABILITIES, operation["operationId"]
        assert "x-internal" not in operation
        assert route.startswith(("/api/v1/employment/relationships/", "/api/v1/marketplace/agents/"))
        seen.update(capabilities)

    assert seen == WORKBENCH_CAPABILITIES


def test_wc136_r008_the_workbench_covers_the_operations_the_later_tracks_implement() -> None:
    ids = {operation["operationId"] for _, _, operation in _operations(_spec(WORKBENCH))}

    assert ids == {
        "getWorkbench",
        "listWorkbenchGoals",
        "createWorkbenchGoal",
        "getWorkbenchGoal",
        "reviseWorkbenchGoal",
        "listWorkbenchGoalVersions",
        "getCurrentWorkbenchPlan",
        "proposeWorkbenchPlan",
        "acceptWorkbenchPlan",
        "listWorkbenchCapabilities",
        "commandWorkbenchCapability",
        "listWorkbenchWorkItems",
        "listWorkbenchDecisions",
        "resolveWorkbenchDecision",
        "getWorkbenchMonitor",
        "listWorkbenchNarratives",
        "getWorkbenchWallet",
        "createWorkbenchTopup",
        "listWorkbenchEvidence",
        "exportWorkbenchEvidence",
        "stopWorkbenchRelationship",
        "pauseWorkbenchRelationship",
        "createWorkbenchHandoff",
        "consumeWorkbenchHandoff",
        "changeSubscription",
        "listMarketplaceAgentPackages",
    }


def test_wc136_r008_the_workbench_problem_codes_include_every_spend_and_wallet_code() -> None:
    codes = set(_spec(WORKBENCH)["components"]["schemas"]["WorkbenchProblemCodeV1"]["enum"])

    assert {
        "WORKBENCH_DISABLED",
        "WORKBENCH_REQUEST_INVALID",
        "WORKBENCH_VERSION_CONFLICT",
        "WORKBENCH_IDEMPOTENCY_CONFLICT",
        "WORKBENCH_UNAVAILABLE",
        "SPEND_PURPOSE_UNMAPPED",
        "SPEND_AUTHORITY_UNAVAILABLE",
        "SPEND_COMMERCIAL_UNAVAILABLE",
        "WALLET_INSUFFICIENT",
        "WALLET_IDEMPOTENCY_CONFLICT",
        "COMPONENT_NOT_YET_RELEASED",
        "PROACTIVE_ALLOWANCE_EXHAUSTED",
        "TRIAL_ALREADY_USED",
        "TRIAL_ALREADY_USED_BY_IDENTITY",
        "PACKAGE_COMPONENT_NOT_AVAILABLE",
    } <= codes


def test_wc136_r008_customer_facing_schemas_never_expose_cost_recipe_or_margin() -> None:
    spec = _spec(WORKBENCH)

    for schema_name in (
        "WorkbenchWalletV1",
        "WorkbenchProjectionV1",
        "WorkbenchTopupReceiptV1",
        "MarketplacePackageListV1",
        "SubscriptionChangeReceiptV1",
    ):
        names = _reachable_property_names(spec, schema_name)
        assert names, schema_name
        assert names.isdisjoint(CUSTOMER_FORBIDDEN_PROPERTIES), (schema_name, names & CUSTOMER_FORBIDDEN_PROPERTIES)

    wallet = _reachable_property_names(spec, "WorkbenchWalletV1")
    assert not {name for name in wallet if re.search(r"price|paise", name, re.IGNORECASE)}


def test_wc136_r008_the_workbench_experience_block_matches_the_v2_vocabulary() -> None:
    block = _spec(WORKBENCH)["components"]["schemas"]["ExperienceBlockV2"]
    vocabulary = BLOCKS_SCHEMA["$defs"]["Block"]

    assert set(block["properties"]["type"]["enum"]) == set(vocabulary["properties"]["type"]["enum"])
    assert set(block["properties"]["sensitivity"]["enum"]) == set(vocabulary["properties"]["sensitivity"]["enum"])
    assert set(block["required"]) == set(vocabulary["required"])
    assert set(block["properties"]) == set(vocabulary["properties"])
    assert _spec(WORKBENCH)["components"]["schemas"]["WorkbenchProjectionV1"]["properties"]["blocks"]["maxItems"] == 6


def test_wc136_r008_a_workbench_projection_is_valid_once_its_defect_is_repaired() -> None:
    cases = {case["id"]: case for case in _spec_fixtures()["cases"]}
    validator = _schema_validator(WORKBENCH, "#/components/schemas/WorkbenchProjectionV1")

    missing_readiness = copy.deepcopy(cases["AEW-NEG-001"]["instance"])
    missing_readiness["readiness"] = {"induction": "READY", "plan": "AGREED", "operations": "ACTIVE", "performance": "CURRENT"}
    too_many_blocks = copy.deepcopy(cases["AEW-NEG-004"]["instance"])
    del too_many_blocks["blocks"][6]

    assert list(validator.iter_errors(missing_readiness)) == []
    assert list(validator.iter_errors(too_many_blocks)) == []


def test_wc136_r008_the_negative_fixture_file_declares_at_least_ten_unique_cases() -> None:
    fixtures = _spec_fixtures()
    ids = [case["id"] for case in fixtures["cases"]]

    assert fixtures["schema"] == "waooaw.spec-negative-fixtures/v1"
    assert len(ids) >= 10
    assert len(ids) == len(set(ids))
    for case in fixtures["cases"]:
        assert case["expected_invalid_reason"]
        assert case["contract"] in OPENAPI_SPECS
        assert _resolve_pointer(_spec(case["contract"]), case["schema_ref"][1:]) is not None


@pytest.mark.parametrize("case", _spec_fixtures()["cases"], ids=lambda case: case["id"])
def test_wc136_r008_each_negative_fixture_is_rejected_by_its_schema(case: dict[str, Any]) -> None:
    validator = _schema_validator(case["contract"], case["schema_ref"])

    assert list(validator.iter_errors(case["instance"])), case["id"]


# --- C2-05 Pricing Admin and WBE internal slices ----------------------------------------------------


def test_wc136_r009_every_pricing_operation_declares_roles_and_step_up_only_for_founder_actions() -> None:
    spec = _spec(PRICING)
    founder_only = {"authorizePricingDraft", "activatePackageForSale"}

    assert spec["security"] == [{"bearerAuth": []}]
    for route, _, operation in _operations(spec):
        assert route.startswith("/api/v1/admin/pricing/")
        assert "x-internal" not in operation
        roles = operation["x-required-roles"]
        if operation["operationId"] in founder_only:
            assert roles == ["founder"]
            assert operation["x-step-up"] is True
        else:
            assert roles == ["pricing_admin", "founder"]
            assert "x-step-up" not in operation


def test_wc136_r009_the_wbe_slice_is_private_bearer_secured_and_role_checked() -> None:
    spec = _spec(WBE_PRICING)
    founder_only = {"wbeAuthorizePricingDraft", "wbeActivatePackageForSale"}

    assert spec["security"] == [{"ServiceBearerAuth": []}]
    assert spec["components"]["securitySchemes"]["ServiceBearerAuth"]["scheme"] == "bearer"
    assert "internal" in spec["servers"][0]["url"]
    for route, _, operation in _operations(spec):
        assert route.startswith("/internal/v1/pricing/")
        assert operation["x-internal"] is True
        if operation["operationId"] in founder_only:
            assert operation["x-required-roles"] == ["FOUNDER"]
            assert operation["x-step-up"] is True
        else:
            assert operation["x-required-roles"] == ["PRICING_ADMIN", "FOUNDER"]
            assert "x-step-up" not in operation


def test_wc136_r009_the_wbe_slice_mirrors_the_public_slice_operation_for_operation() -> None:
    public = {
        operation["operationId"]: (method, route, operation) for route, method, operation in _operations(_spec(PRICING))
    }
    private = {operation["operationId"]: (method, route, operation) for route, method, operation in _operations(_spec(WBE_PRICING))}

    assert set(private) == {"wbe" + name[0].upper() + name[1:] for name in public}
    for name, (method, route, operation) in public.items():
        private_method, private_route, private_operation = private["wbe" + name[0].upper() + name[1:]]
        assert private_method == method
        assert private_route == route.replace("/api/v1/admin/pricing", "/internal/v1/pricing")
        assert private_operation["tags"] == operation["tags"]
        assert private_operation["x-required-roles"] == [role.upper() for role in operation["x-required-roles"]]
        assert private_operation.get("x-step-up") == operation.get("x-step-up")


def test_wc136_r009_the_wbe_schemas_equal_the_public_schemas_except_the_deploy_time_maximum() -> None:
    public = _spec(PRICING)["components"]["schemas"]
    private = copy.deepcopy(_spec(WBE_PRICING)["components"]["schemas"])
    carriers = {name for name, schema in private.items() if "deployTimeMaximumPaise" in schema.get("properties", {})}

    assert carriers == {
        "CreatePricingDraftRequestV1",
        "UpdatePricingDraftRequestV1",
        "SimulatePricingDraftRequestV1",
        "SubmitPricingDraftRequestV1",
        "AuthorizePricingDraftRequestV1",
        "LowerCeilingRequestV1",
        "ImportPricingBundleRequestV1",
    }
    for name in carriers:
        assert private[name]["properties"].pop("deployTimeMaximumPaise")["type"] == "integer"
    assert private == public


def test_wc136_r009_the_public_slice_never_accepts_the_deploy_time_maximum_from_a_browser() -> None:
    request = {
        "schemaVersion": "1.0",
        "kind": "BUDGET",
        "subjectKey": "budget:ENVIRONMENT_CEILING|demo",
        "body": {"scope": "ENVIRONMENT_CEILING", "ref": "demo", "maximumPaise": 100000},
    }
    public = _schema_validator(PRICING, "#/components/schemas/CreatePricingDraftRequestV1")
    private = _schema_validator(WBE_PRICING, "#/components/schemas/CreatePricingDraftRequestV1")

    assert public.is_valid(request)
    assert not public.is_valid({**request, "deployTimeMaximumPaise": 500000})
    assert private.is_valid({**request, "deployTimeMaximumPaise": 500000})


def test_wc136_r009_the_pricing_problem_codes_include_every_contract_code() -> None:
    codes = set(_spec(PRICING)["components"]["schemas"]["PricingProblemCodeV1"]["enum"])

    assert {
        "PRICING_FORBIDDEN",
        "PRICING_STEP_UP_REQUIRED",
        "PRICING_DRAFT_INVALID",
        "PRICING_BELOW_FLOOR",
        "PRICING_NEEDS_SECOND_CONFIRMATION",
        "PRICING_ILLEGAL_TRANSITION",
        "PRICING_CEILING_ABOVE_MAXIMUM",
        "PRICING_CEILING_BELOW_OPEN_RESERVATIONS",
        "PACKAGE_COMPONENT_NOT_AVAILABLE",
        "RECIPE_THREAD_NOT_AUTHORIZED",
    } <= codes


def _create_requests() -> dict[str, dict[str, Any]]:
    agent = "DIGITAL_MARKETING_LOCAL_SERVICE"
    return {
        "RATE": {
            "kind": "RATE",
            "subjectKey": "thread:openai-gpt4o-input",
            "body": {
                "threadId": "openai-gpt4o-input",
                "provider": "openai",
                "unit": "1k_tokens",
                "rawCostPaise": 50,
                "fxBufferPct": 5,
                "opsOverheadPct": 10,
                "riskPremiumPct": 2,
            },
        },
        "PACKAGE": {
            "kind": "PACKAGE",
            "subjectKey": f"package:{agent}|1.0.0|B1",
            "body": {
                "agentType": agent,
                "agentVersion": "1.0.0",
                "packageCode": "B1",
                "displayName": "Content Starter",
                "billingPeriodDays": 30,
                "priceInclGstPaise": 99900,
                "gstRatePercent": 18,
                "infrastructureSharePaise": 10000,
                "components": [
                    {
                        "componentId": "CONTENT_PLAN",
                        "kind": "COUNTED",
                        "quantity": 4,
                        "cadence": "MONTHLY",
                        "priceAllocationPaise": 20000,
                        "recipe": [{"threadId": "openai-gpt4o-input", "unitsPerUnit": 2.5}],
                        "topupAllowed": True,
                    }
                ],
            },
        },
        "POLICY": {
            "kind": "POLICY",
            "subjectKey": "policy:platform",
            "body": {
                "minimumMarginPct": 30,
                "paymentGraceDays": 7,
                "sunsetNoticeDays": 30,
                "costToleranceFraction": 0.1,
                "costAlertFraction": 0.2,
                "upgradeTiming": "IMMEDIATE",
                "downgradeTiming": "AT_RENEWAL",
                "changeSizeGuardPercent": 25,
                "priceMultipleGuard": 3,
            },
        },
        "GRANT": {
            "kind": "GRANT",
            "subjectKey": f"grant:TRIAL|{agent}|1.0.0",
            "body": {"kind": "TRIAL", "agentType": agent, "agentVersion": "1.0.0", "paise": 5000, "durationDays": 7},
        },
        "BUDGET": {
            "kind": "BUDGET",
            "subjectKey": "budget:ENVIRONMENT_CEILING|demo",
            "body": {"scope": "ENVIRONMENT_CEILING", "ref": "demo", "maximumPaise": 100000},
        },
        "COUPON": {
            "kind": "COUPON",
            "subjectKey": "coupon:LAUNCH10",
            "body": {
                "code": "LAUNCH10",
                "agentType": agent,
                "agentVersion": "1.0.0",
                "percent": 10,
                "capPaise": 50000,
                "expiresAt": "2026-12-31T00:00:00Z",
                "reason": "Launch offer",
                "maxRedemptions": 100,
            },
        },
    }


@pytest.mark.parametrize("spec_name", [PRICING, WBE_PRICING])
@pytest.mark.parametrize("kind", ["RATE", "PACKAGE", "POLICY", "GRANT", "BUDGET", "COUPON"])
def test_wc136_r009_a_create_draft_request_validates_per_kind(spec_name: str, kind: str) -> None:
    validator = _schema_validator(spec_name, "#/components/schemas/CreatePricingDraftRequestV1")
    request = {"schemaVersion": "1.0", **_create_requests()[kind]}

    assert list(validator.iter_errors(request)) == []


def _invalid_create_requests() -> dict[str, dict[str, Any]]:
    requests = {kind: {"schemaVersion": "1.0", **request} for kind, request in _create_requests().items()}
    rate_with_coupon_body = {**requests["RATE"], "body": requests["COUPON"]["body"]}
    package_without_recipe = copy.deepcopy(requests["PACKAGE"])
    del package_without_recipe["body"]["components"][0]["recipe"]
    package_fractional_price = copy.deepcopy(requests["PACKAGE"])
    package_fractional_price["body"]["priceInclGstPaise"] = 99900.5
    package_with_cost_field = copy.deepcopy(requests["PACKAGE"])
    package_with_cost_field["body"]["marginPercent"] = 40
    grant_with_units_and_paise = copy.deepcopy(requests["GRANT"])
    grant_with_units_and_paise["body"]["units"] = {"openai-gpt4o-input": 10}
    grant_without_duration = copy.deepcopy(requests["GRANT"])
    del grant_without_duration["body"]["durationDays"]
    coupon_with_both = copy.deepcopy(requests["COUPON"])
    coupon_with_both["body"]["amountPaise"] = 5000
    budget_with_extra = copy.deepcopy(requests["BUDGET"])
    budget_with_extra["body"]["leadName"] = "A. Customer"
    return {
        "unknown kind": {**requests["RATE"], "kind": "REFUND"},
        "rate with a coupon body": rate_with_coupon_body,
        "rate with a package subject key": {**requests["RATE"], "subjectKey": requests["PACKAGE"]["subjectKey"]},
        "policy with another subject key": {**requests["POLICY"], "subjectKey": "policy:tenant"},
        "package without a recipe": package_without_recipe,
        "package with a fractional price": package_fractional_price,
        "package with a margin field": package_with_cost_field,
        "grant with units and paise": grant_with_units_and_paise,
        "grant without a duration": grant_without_duration,
        "coupon with percent and amount": coupon_with_both,
        "budget with a personal field": budget_with_extra,
        "missing schema version": {key: value for key, value in requests["RATE"].items() if key != "schemaVersion"},
    }


@pytest.mark.parametrize("name", sorted(_invalid_create_requests()))
def test_wc136_r009_an_invalid_create_draft_request_fails(name: str) -> None:
    for spec_name in (PRICING, WBE_PRICING):
        validator = _schema_validator(spec_name, "#/components/schemas/CreatePricingDraftRequestV1")

        assert not validator.is_valid(_invalid_create_requests()[name]), (spec_name, name)


def test_wc136_r009_pricing_versions_carry_the_required_nullable_lifecycle_fields() -> None:
    version = _spec(PRICING)["components"]["schemas"]["PricingVersionV1"]

    for field in ("effectiveFrom", "supersedes", "authorizedBy", "evidenceId"):
        assert field in version["required"]
        assert "null" in version["properties"][field]["type"]
    validator = _schema_validator(PRICING, "#/components/schemas/PricingVersionV1")
    instance = {
        "schemaVersion": "1.0",
        "versionId": "00000000-0000-4000-8000-000000000010",
        "kind": "RATE",
        "subjectKey": "thread:openai-gpt4o-input",
        "versionNo": 1,
        "state": "DRAFT",
        "body": {"threadId": "openai-gpt4o-input"},
        "bodyDigest": "a" * 64,
        "seed": False,
        "effectiveFrom": None,
        "supersedes": None,
        "authorizedBy": None,
        "evidenceId": None,
        "needsSecondConfirmation": False,
        "createdBy": "founder",
        "createdAt": "2026-05-01T10:00:00Z",
    }

    assert list(validator.iter_errors(instance)) == []
    assert not validator.is_valid({**instance, "state": "PUBLISHED"})


def test_wc136_r009_every_wbe_route_has_exactly_one_business_platform_grant() -> None:
    spec = _spec(WBE_PRICING)
    major = int(spec["info"]["version"].split(".", maxsplit=1)[0])
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    operations = {
        (method.upper(), route, operation["operationId"], major) for route, method, operation in _operations(spec)
    }
    grants = [
        grant
        for grant in registry["route_grants"]
        if grant["target"] == "billing-engine" and grant["route"].startswith("/internal/v1/pricing/")
    ]
    keys = [(grant["method"], grant["route"], grant["operation"], grant["contract_major"]) for grant in grants]

    assert len(operations) == 18
    assert len(keys) == len(set(keys))
    assert set(keys) == operations
    assert {grant["caller"] for grant in grants} == {"business-platform"}


# --- C2-07 Catalog wiring -------------------------------------------------------------------------


def test_wc136_r011_the_validation_catalog_wires_the_experience_contract_gate() -> None:
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    command = catalog["commands"]["wc136-experience-contract"]
    gate = catalog["gates"]["wc136:experience-contract"]
    reference = catalog["gates"]["wc123:identity-contract"]

    assert command["shell"] == (
        "pytest tests/contract/test_wc136_experience_contract.py tests/contract/test_wc136_generated_clients.py "
        "tests/contract/test_wc136_dma_experience_scenarios.py -q"
    )
    assert gate["gate_id"] == "wc136:experience-contract"
    assert gate["command_id"] == "wc136-experience-contract"
    assert {key: value for key, value in gate.items() if key not in {"gate_id", "command_id"}} == {
        key: value for key, value in reference.items() if key not in {"gate_id", "command_id"}
    }
    assert (ROOT / "tests/contract/test_wc136_experience_contract.py").is_file()
