#!/usr/bin/env python3
# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§9-10
# Constitutional basis: C-023, C-059, C-063, C-080

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


OUTCOMES = (
    "CONFIGURATION_READY",
    "PROVIDER_REDIRECT_READY",
    "PROVIDER_LOGIN_ACCEPTED",
    "DATA_CONTINUITY_READY",
)


def evaluate(rendered: dict[str, Any], evidence: dict[str, Any]) -> dict[str, str]:
    expected_bindings = {binding["id"] for binding in rendered["secretBindings"]}
    valid_metadata = {
        item["id"] for item in evidence.get("secretMetadata", [])
        if item.get("enabled") is True and item.get("expired") is False
    }
    configuration_ready = (
        evidence.get("renderDigest") == rendered["renderDigest"]
        and expected_bindings.issubset(valid_metadata)
    )
    generations = evidence.get("demoGenerations", [])
    data_ready = (
        rendered["environment"] == "demo"
        and len(generations) >= 2
        and len({item.get("generationId") for item in generations}) == len(generations)
        and len({item.get("fixtureDigest") for item in generations}) == 1
        and all(item.get("priorGenerationReachable") is False for item in generations)
    )
    redirect_ready = evidence.get("providerRedirect", {}).get("verified") is True
    login_accepted = evidence.get("providerLogin", {}).get("humanAccepted") is True
    return {
        "CONFIGURATION_READY": "PASS" if configuration_ready else "NOT_PROVEN",
        "PROVIDER_REDIRECT_READY": "PASS" if redirect_ready else "NOT_PROVEN",
        "PROVIDER_LOGIN_ACCEPTED": "PASS" if login_accepted else "NOT_PROVEN",
        "DATA_CONTINUITY_READY": "PASS" if data_ready else "NOT_PROVEN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate independent WC-091 readiness outcomes")
    parser.add_argument("rendered", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    result = evaluate(
        json.loads(args.rendered.read_text(encoding="utf-8")),
        json.loads(args.evidence.read_text(encoding="utf-8")),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(value == "PASS" for value in result.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())