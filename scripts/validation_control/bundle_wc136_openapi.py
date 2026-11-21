# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-06
# Constitutional basis: C-023, C-059, C-065
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

import yaml

SCHEMA_PREFIX = "#/components/schemas/"


def _load(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"OpenAPI document is not an object: {path}")
    return document


def _collect_refs(value: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("$ref"), str):
            found.append(value)
        for child in value.values():
            _collect_refs(child, found)
    elif isinstance(value, list):
        for child in value:
            _collect_refs(child, found)


class _Bundler:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.document = _load(source)
        self.schemas: dict[str, Any] = self.document.setdefault("components", {}).setdefault("schemas", {})
        self.external_cache: dict[str, dict[str, Any]] = {}

    def _external_schemas(self, file_name: str) -> dict[str, Any]:
        if file_name not in self.external_cache:
            document = _load(self.source.parent / file_name)
            self.external_cache[file_name] = document.get("components", {}).get("schemas", {})
        return self.external_cache[file_name]

    def _import(self, file_name: str, name: str) -> None:
        external = self._external_schemas(file_name)
        if name not in external:
            raise ValueError(f"External schema not found: {file_name}#{name}")
        schema = copy.deepcopy(external[name])
        if name in self.schemas:
            if self.schemas[name] != schema:
                raise ValueError(f"Schema collision while bundling: {name}")
            return
        self.schemas[name] = schema
        self._rewrite(schema, file_name)

    def _rewrite(self, value: Any, owner_file: str | None) -> None:
        refs: list[dict[str, Any]] = []
        _collect_refs(value, refs)
        for node in refs:
            reference = node["$ref"]
            if reference.startswith("./") and "#" in reference:
                file_name, pointer = reference[2:].split("#", 1)
                pointer = "#" + pointer
                if not pointer.startswith(SCHEMA_PREFIX):
                    raise ValueError(f"Only schema references can be bundled: {reference}")
                name = pointer[len(SCHEMA_PREFIX) :]
                self._import(file_name, name)
                node["$ref"] = pointer
            elif reference.startswith(SCHEMA_PREFIX) and owner_file is not None:
                self._import(owner_file, reference[len(SCHEMA_PREFIX) :])

    def run(self) -> dict[str, Any]:
        self._rewrite(self.document, None)
        return self.document


def bundle(source: Path, output: Path) -> None:
    document = _Bundler(source).run()
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
