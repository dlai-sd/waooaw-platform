"""Validate and canonicalize Azure resource IDs used by Terraform imports."""

from __future__ import annotations

import argparse


def canonical_container_app_id(
    resource_id: str, *, expected_resource_group: str, expected_name: str
) -> str:
    """Return the AzureRM-canonical ID for a top-level Container App."""
    segments = resource_id.split("/")
    if len(segments) != 9 or segments[0] != "":
        raise ValueError("Container App resource ID must contain exactly eight segments")

    expected_segments = {
        1: "subscriptions",
        3: "resourceGroups",
        5: "providers",
        6: "Microsoft.App",
        7: "containerApps",
    }
    for position, expected in expected_segments.items():
        if segments[position].casefold() != expected.casefold():
            raise ValueError(
                f"Container App resource ID segment {position} must be {expected}"
            )

    for position in (2, 4, 8):
        if not segments[position]:
            raise ValueError(
                f"Container App resource ID segment {position} must not be empty"
            )

    if segments[4].casefold() != expected_resource_group.casefold():
        raise ValueError("Container App resource group does not match the expected resource group")
    if segments[8].casefold() != expected_name.casefold():
        raise ValueError("Container App name does not match the expected name")

    return (
        f"/subscriptions/{segments[2]}"
        f"/resourceGroups/{segments[4]}"
        f"/providers/Microsoft.App/containerApps/{segments[8]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container-app-id", required=True)
    parser.add_argument("--expected-resource-group", required=True)
    parser.add_argument("--expected-name", required=True)
    arguments = parser.parse_args()
    try:
        canonical_id = canonical_container_app_id(
            arguments.container_app_id,
            expected_resource_group=arguments.expected_resource_group,
            expected_name=arguments.expected_name,
        )
    except ValueError as error:
        parser.error(str(error))
    print(canonical_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())