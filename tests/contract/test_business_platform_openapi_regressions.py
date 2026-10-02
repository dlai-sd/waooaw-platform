from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml").read_text(encoding="utf-8"))


def _accepts(schema: dict[str, Any], value: str) -> bool:
    return (
        len(value) >= schema.get("minLength", 0)
        and len(value) <= schema.get("maxLength", len(value))
        and ("pattern" not in schema or re.search(schema["pattern"], value) is not None)
    )


@pytest.mark.parametrize(
    ("schema", "invalid", "valid"),
    [
        (SPEC["components"]["schemas"]["ConversationTextBlockV1"]["properties"]["text"], "\u0085", "hello"),
        (SPEC["components"]["schemas"]["SendConversationMessageRequestV1"]["properties"]["skillId"], " ", "skill-1"),
        (
            SPEC["paths"]["/api/v1/notifications/alerts"]["get"]["parameters"][0]["schema"],
            "",
            "0123456789abcdef",
        ),
        (
            SPEC["components"]["schemas"]["CustomerAlertMutationRequestV1"]["properties"]["expectedAlertVersion"],
            "0",
            "alert-1",
        ),
    ],
)
def test_fuzz_discovered_string_constraints_are_deterministic(schema: dict[str, Any], invalid: str, valid: str) -> None:
    assert not _accepts(schema, invalid)
    assert _accepts(schema, valid)
