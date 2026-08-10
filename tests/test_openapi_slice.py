"""Focused contract tests for deterministic OpenAPI dependency slicing."""

# Implements: architecture/reference/components/conversation-core.md §3 Public Business Platform Contract
# Constitutional basis: C-032 (Spec Is Truth), C-059 (Implementation Traceability)

from pathlib import Path

import yaml

from scripts.openapi_slice import write_dependency_closed_openapi_slice


def test_slice_closes_global_and_referenced_security_dependencies(tmp_path: Path) -> None:
    source_path = tmp_path / "source.yaml"
    output_path = tmp_path / "slice.yaml"
    source_path.write_text(
        yaml.safe_dump(
            {
                "openapi": "3.0.3",
                "info": {"title": "Fixture", "version": "1.0.0"},
                "security": [{"BearerAuth": []}],
                "paths": {
                    "/conversation": {
                        "get": {
                            "tags": ["Conversation"],
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/Conversation"}
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
                "components": {
                    "schemas": {
                        "Conversation": {
                            "type": "object",
                            "security": [{"NestedAuth": []}],
                        }
                    },
                    "securitySchemes": {
                        "BearerAuth": {"type": "http", "scheme": "bearer"},
                        "NestedAuth": {"type": "apiKey", "in": "header", "name": "X-Nested"},
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    write_dependency_closed_openapi_slice(source_path, output_path, ["Conversation"])

    sliced = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert sliced["security"] == [{"BearerAuth": []}]
    assert set(sliced["components"]["securitySchemes"]) == {"BearerAuth", "NestedAuth"}