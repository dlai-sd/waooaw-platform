from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


def _load(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"OpenAPI document is not an object: {path}")
    return document


def _rewrite_external_refs(value: Any, external_name: str) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith(f"./{external_name}#"):
            value["$ref"] = f"#{reference.split('#', 1)[1]}"
        for child in value.values():
            _rewrite_external_refs(child, external_name)
    elif isinstance(value, list):
        for child in value:
            _rewrite_external_refs(child, external_name)


def bundle(source: Path, output: Path) -> None:
    document = _load(source)
    external_name = "conversational-employment-business-platform.openapi.yaml"
    external = _load(source.parent / external_name)
    local_schemas = document.setdefault("components", {}).setdefault("schemas", {})
    external_schemas = external.get("components", {}).get("schemas", {})
    if not isinstance(local_schemas, dict) or not isinstance(external_schemas, dict):
        raise ValueError("OpenAPI components.schemas must be objects")

    command_union = external_schemas.get("EmploymentCommandRequestV1")
    if not isinstance(command_union, dict) or len(command_union.get("oneOf", [])) != 9:
        raise ValueError("Employment command union must contain exactly nine branches")
    command_union.pop("discriminator", None)
    for branch in command_union["oneOf"]:
        name = branch["$ref"].rsplit("/", 1)[1]
        kind = external_schemas[name]["properties"]["kind"]
        constant = kind.pop("const")
        kind["enum"] = [constant]

    for name, schema in external_schemas.items():
        if name in local_schemas and local_schemas[name] != schema:
            raise ValueError(f"Schema collision while bundling: {name}")
        local_schemas.setdefault(name, schema)

    _rewrite_external_refs(document, external_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
