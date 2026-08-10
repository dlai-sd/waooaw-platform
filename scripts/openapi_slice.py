#!/usr/bin/env python3
"""Build a deterministic, dependency-closed OpenAPI slice selected by tag."""

# Implements: architecture/reference/components/conversation-core.md §3 Public Business Platform Contract
# Constitutional basis: C-032 (Spec Is Truth), C-059 (Implementation Traceability)

from __future__ import annotations

import argparse
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
PATH_ITEM_FIELDS = {"summary", "description", "servers", "parameters", "$ref"}


def write_dependency_closed_openapi_slice(
    source_path: Path,
    output_path: Path,
    tags: Iterable[str],
    schema_roots: Iterable[str] = (),
) -> None:
    """Write operations matching tags and every recursively referenced component."""
    selected_tags = tuple(dict.fromkeys(tags))
    if not selected_tags:
        raise ValueError("At least one OpenAPI tag must be selected")

    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    paths: dict[str, dict[str, Any]] = {}
    for path, path_item in source.get("paths", {}).items():
        selected = {
            key: deepcopy(value)
            for key, value in path_item.items()
            if key in PATH_ITEM_FIELDS
        }
        for method, operation in path_item.items():
            if (
                method.lower() in HTTP_METHODS
                and isinstance(operation, dict)
                and set(operation.get("tags", [])).intersection(selected_tags)
            ):
                selected[method] = deepcopy(operation)
        if any(key.lower() in HTTP_METHODS for key in selected):
            paths[path] = selected

    if not paths:
        raise ValueError(f"No OpenAPI operations found for tags: {', '.join(selected_tags)}")

    source_components = source.get("components", {})
    required_components: dict[str, set[str]] = {}
    pending_refs: list[str] = []
    pending_security_schemes: set[str] = set()

    def collect_dependencies(node: object) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/"):
                pending_refs.append(ref)
            security = node.get("security")
            if isinstance(security, list):
                for requirement in security:
                    if isinstance(requirement, dict):
                        pending_security_schemes.update(requirement)
            for value in node.values():
                collect_dependencies(value)
        elif isinstance(node, list):
            for value in node:
                collect_dependencies(value)

    collect_dependencies(paths)
    collect_dependencies({"security": source.get("security", [])})
    for name in dict.fromkeys(schema_roots):
        schema = source_components.get("schemas", {}).get(name)
        if schema is None:
            raise ValueError(f"OpenAPI slice has unresolved schema root: {name}")
        required_components.setdefault("schemas", set()).add(name)
        collect_dependencies(schema)

    seen_refs: set[str] = set()
    seen_security_schemes: set[str] = set()
    while pending_refs or pending_security_schemes:
        while pending_security_schemes:
            name = pending_security_schemes.pop()
            if name in seen_security_schemes:
                continue
            seen_security_schemes.add(name)
            scheme = source_components.get("securitySchemes", {}).get(name)
            if scheme is None:
                raise ValueError(f"OpenAPI slice has unresolved security scheme: {name}")
            required_components.setdefault("securitySchemes", set()).add(name)
            collect_dependencies(scheme)

        while pending_refs:
            ref = pending_refs.pop()
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            parts = ref.split("/")
            if len(parts) != 4:
                raise ValueError(f"Unsupported local OpenAPI component reference: {ref}")
            category, name = parts[2], parts[3]
            component = source_components.get(category, {}).get(name)
            if component is None:
                raise ValueError(f"OpenAPI slice has unresolved component: {ref}")
            required_components.setdefault(category, set()).add(name)
            collect_dependencies(component)

    selected_components: dict[str, dict[str, Any]] = {}
    for category, components in source_components.items():
        required_names = required_components.get(category, set())
        selected = {
            name: deepcopy(component)
            for name, component in components.items()
            if name in required_names
        }
        if selected:
            selected_components[category] = selected

    sliced: dict[str, Any] = {
        "openapi": source["openapi"],
        "info": deepcopy(source["info"]),
        "tags": [
            deepcopy(tag)
            for tag in source.get("tags", [])
            if tag.get("name") in selected_tags
        ],
        "paths": paths,
        "components": selected_components,
    }
    for field in ("servers", "security"):
        if source.get(field):
            sliced[field] = deepcopy(source[field])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(sliced, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Canonical OpenAPI source")
    parser.add_argument("--output", type=Path, required=True, help="Slice output path")
    parser.add_argument("--tag", action="append", required=True, dest="tags", help="Operation tag to include")
    parser.add_argument("--schema", action="append", default=[], dest="schemas", help="Additional root schema to include")
    arguments = parser.parse_args()
    write_dependency_closed_openapi_slice(
        arguments.input,
        arguments.output,
        arguments.tags,
        arguments.schemas,
    )


if __name__ == "__main__":
    main()