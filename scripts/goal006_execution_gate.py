"""Fail-closed execution decisions for GOAL-006 deployment workflows."""

from __future__ import annotations

import argparse


def state_adoption_required(*, execution: str, state_adopted: bool) -> bool:
    """Return whether apply mode may adopt the existing Demo resource group."""
    if execution not in {"true", "false"}:
        raise ValueError("execution must be the GitHub boolean string true or false")
    if state_adopted:
        return False
    if execution == "false":
        raise ValueError("plan mode is read-only; foundation state adoption requires explicit apply mode")
    return True


def parse_boolean(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("value must be true or false")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", required=True, choices=("true", "false"))
    parser.add_argument("--state-adopted", required=True, type=parse_boolean)
    arguments = parser.parse_args()
    required = False
    try:
        required = state_adoption_required(
            execution=arguments.execution,
            state_adopted=arguments.state_adopted,
        )
    except ValueError as error:
        parser.error(str(error))
    print(str(required).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())