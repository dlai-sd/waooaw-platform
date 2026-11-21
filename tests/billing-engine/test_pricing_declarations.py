# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Constitutional basis: C-059, C-088, C-089, C-091
"""Agent declaration source read from the admitted employment-interface manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pricing.declarations import (  # noqa: E402
    MANIFEST_NAME,
    ManifestDeclarationSource,
    RegistryAliasedReference,
    load_declarations,
)
from pricing_support import FakeReference  # noqa: E402

CONTRACTS = Path(__file__).resolve().parents[2] / "src" / "digital-marketing-agent" / "contracts"


async def test_the_dma_manifest_declares_its_components_with_kind_and_availability():
    source = ManifestDeclarationSource.from_directory(CONTRACTS)

    declaration = await source.declaration("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0")

    assert declaration is not None
    components = declaration.components
    assert components["SOCIAL_OBSERVATION"].kind == "SELECTED"
    assert components["AD_BOOST"].availability == "UNAVAILABLE"
    assert components["PROACTIVE_MESSAGE"].availability == "DEFAULT_OFF"
    assert {"CONTENT_PLAN", "CONTENT_DRAFT", "CONTENT_ASSET", "SOCIAL_PUBLICATION"} <= set(components)


async def test_an_unknown_agent_version_has_no_declaration():
    source = ManifestDeclarationSource.from_directory(CONTRACTS)

    assert await source.declaration("DIGITAL_MARKETING_LOCAL_SERVICE", "9.9.9") is None
    assert await source.declaration("NO_SUCH_AGENT", "1.0.0") is None


def test_unreadable_and_experience_less_manifests_are_skipped(tmp_path):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / MANIFEST_NAME).write_text("{not json", encoding="utf-8")
    (tmp_path / "plain").mkdir()
    (tmp_path / "plain" / MANIFEST_NAME).write_text(
        json.dumps({"agentType": "PLAIN", "agentVersion": "1.0.0"}), encoding="utf-8"
    )
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / MANIFEST_NAME).write_text(
        json.dumps(
            {
                "agentType": "OK",
                "agentVersion": "2.0.0",
                "experience": {
                    "components": [
                        {"componentId": "A", "kind": "COUNTED", "availability": "AVAILABLE"},
                        {"componentId": 7, "kind": "COUNTED", "availability": "AVAILABLE"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    declarations = load_declarations(tmp_path)

    assert [(item.agent_type, item.agent_version, sorted(item.components)) for item in declarations] == [
        ("OK", "2.0.0", ["A"])
    ]


async def test_the_manifest_agent_type_is_authorized_through_its_billing_profile_registry_id():
    inner = FakeReference(authorized_agents=("dma_v3",))
    reference = RegistryAliasedReference(inner)

    assert await reference.billing_profile_authorized("DIGITAL_MARKETING_LOCAL_SERVICE") is True
    assert await reference.billing_profile_authorized("OTHER_AGENT") is False
    assert "llm_pro" in await reference.thread_rates(["llm_pro"])
