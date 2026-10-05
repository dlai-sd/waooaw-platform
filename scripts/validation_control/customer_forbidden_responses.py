#!/usr/bin/env python3
"""Enforce customer-membership 403 responses in the Business Platform OpenAPI spec."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
FORBIDDEN_RESPONSE = '"403": { $ref: "#/components/responses/IdentityForbidden" }'
RELATIONSHIP_SERVICE_ONLY = re.compile(r"^/api/v1/employment/relationships/[^/]+/(?:transitions|offerability)(?:/|$)")


def is_customer_path(path: str) -> bool:
    return (
        path.startswith("/api/v1/acquisition/continuations")
        or path.startswith("/api/v1/customer-portal/interactions/portal/messages")
        or path.startswith("/api/v1/professionals/marketplace")
        or (path.startswith("/api/v1/employment/relationships") and RELATIONSHIP_SERVICE_ONLY.match(path) is None)
    )


def missing_operations(specification: dict[str, object]) -> set[tuple[str, str]]:
    paths = specification.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("OpenAPI paths must be a mapping")
    missing: set[tuple[str, str]] = set()
    for path, path_item in paths.items():
        if not isinstance(path, str) or not is_customer_path(path) or not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                raise ValueError(f"OpenAPI operation has no response mapping: {method.upper()} {path}")
            if "403" not in responses:
                missing.add((path, method))
    return missing


def insert_missing_responses(source: str, missing: set[tuple[str, str]]) -> str:
    output: list[str] = []
    current_path: str | None = None
    current_method: str | None = None
    inserted: set[tuple[str, str]] = set()
    for line in source.splitlines():
        path_match = re.match(r"^  (/[^:]+):\s*$", line)
        method_match = re.match(r"^    (get|post|put|patch|delete):\s*$", line)
        if path_match:
            current_path = path_match.group(1)
            current_method = None
        elif method_match:
            current_method = method_match.group(1)
        operation = (current_path, current_method)
        if operation in missing and line.startswith("      responses:"):
            if line.strip() == "responses:":
                output.append(line)
                output.append(f"        {FORBIDDEN_RESPONSE}")
            elif "responses: {" in line:
                output.append(line.replace("responses: {", f"responses: {{ {FORBIDDEN_RESPONSE},", 1))
            else:
                raise ValueError(f"unsupported responses layout: {current_method.upper()} {current_path}")
            inserted.add((current_path, current_method))
            continue
        output.append(line)
    not_inserted = missing - inserted
    if not_inserted:
        operations = ", ".join(f"{method.upper()} {path}" for path, method in sorted(not_inserted))
        raise ValueError(f"could not locate response blocks for: {operations}")
    return "\n".join(output) + "\n"


def load_specification(path: Path) -> dict[str, object]:
    specification = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(specification, dict):
        raise ValueError("OpenAPI document root must be a mapping")
    return specification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    missing = missing_operations(load_specification(arguments.spec))
    if not missing:
        print("Customer forbidden-response contract passed.")
        return 0
    if not arguments.write:
        for path, method in sorted(missing):
            print(f"missing 403 response: {method.upper()} {path}")
        return 1

    updated = insert_missing_responses(arguments.spec.read_text(encoding="utf-8"), missing)
    arguments.spec.write_text(updated, encoding="utf-8")
    remaining = missing_operations(load_specification(arguments.spec))
    if remaining:
        raise ValueError("customer forbidden-response update was incomplete")
    print(f"Added customer forbidden responses to {len(missing)} operations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
