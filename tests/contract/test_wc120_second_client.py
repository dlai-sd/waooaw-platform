from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml"
CLIENT_ROOT = ROOT / "src/professional-runtime/clients/generated/conversation_compatibility"
TYPESCRIPT_ROOT = ROOT / "web/lib/api/generated/conversation-v1"


def test_ce_fit_15_second_generated_client_preserves_public_semantics_and_bp_authority() -> None:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((CLIENT_ROOT / "generation-manifest.json").read_text(encoding="utf-8"))
    package = CLIENT_ROOT / "conversation_compatibility_client"

    assert manifest["generatorImage"] == "openapitools/openapi-generator-cli:v7.17.0"
    assert manifest["specVersion"] == spec["info"]["version"]
    assert package.is_dir()
    assert (package / "api").is_dir()
    assert (package / "models").is_dir()

    operation_ids = {
        operation["operationId"]
        for item in spec["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    generated_api_text = "\n".join(path.read_text(encoding="utf-8") for path in (package / "api").glob("*.py"))
    for operation_id in operation_ids:
        snake_name = "".join(f"_{character.lower()}" if character.isupper() else character for character in operation_id).lstrip(
            "_"
        )
        assert f"def {snake_name}(" in generated_api_text

    assert "/api/v1/employment/relationships/" in generated_api_text
    assert "professional-runtime" not in spec["servers"][0]["url"].lower()

    employment_spec = yaml.safe_load(
        (SPEC_PATH.parent / "conversational-employment-business-platform.openapi.yaml").read_text(encoding="utf-8")
    )
    mapping = employment_spec["components"]["schemas"]["EmploymentCommandRequestV1"]["discriminator"]["mapping"]
    command_models = sorted(reference.rsplit("/", 1)[1] for reference in mapping.values())
    assert len(command_models) == 9

    typescript_union = (TYPESCRIPT_ROOT / "src/models/EmploymentCommandRequestV1.ts").read_text(encoding="utf-8")
    python_union = (package / "models/employment_command_request_v1.py").read_text(encoding="utf-8")
    for model in command_models:
        assert (TYPESCRIPT_ROOT / f"src/models/{model}.ts").is_file()
        assert f"import type {{ {model} }} from './{model}';" in typescript_union
        python_name = "".join(f"_{character.lower()}" if character.isupper() else character for character in model).lstrip("_")
        assert (package / f"models/{python_name}.py").is_file()
    assert python_union.count("oneof_schema_") >= 9


def test_wc120_python_client_source_imports_without_network_or_provider_configuration() -> None:
    init_file = CLIENT_ROOT / "conversation_compatibility_client" / "__init__.py"
    assert importlib.util.spec_from_file_location("wc120_generated_client", init_file) is not None
