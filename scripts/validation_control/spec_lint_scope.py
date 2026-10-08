#!/usr/bin/env python3
"""Select repository OpenAPI contracts for the catalog-owned spec-lint gate."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath

CANONICAL_SPECS = (
    "architecture/reference/api-specs/business-platform.openapi.yaml",
    "architecture/reference/api-specs/professional-runtime.openapi.yaml",
)
SPEC_DIRECTORY = PurePosixPath("architecture/reference/api-specs")
SPEC_SUFFIX = ".openapi.yaml"


def select_specs(repository: Path, changed_files: Path | None) -> list[str]:
    selected = list(CANONICAL_SPECS)
    seen = set(selected)

    if changed_files is None or not changed_files.is_file():
        return selected

    for raw_path in changed_files.read_text(encoding="utf-8").splitlines():
        path_text = raw_path.strip()
        if not path_text:
            continue
        path = PurePosixPath(path_text)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"changed path must be repository-relative: {path_text}")
        if path.parent != SPEC_DIRECTORY or not path.name.endswith(SPEC_SUFFIX):
            continue
        if not (repository / path).is_file():
            raise FileNotFoundError(f"changed OpenAPI contract does not exist: {path_text}")
        if path_text not in seen:
            selected.append(path_text)
            seen.add(path_text)

    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--changed-files", type=Path)
    args = parser.parse_args()

    for path in select_specs(args.repository.resolve(), args.changed_files):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
