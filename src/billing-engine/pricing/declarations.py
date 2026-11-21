# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Constitutional basis: C-059, C-088, C-089, C-091
"""Agent declaration source built from the admitted employment-interface manifests.

A package may sell only the components an agent version declares, and only once they are AVAILABLE
(architecture 6.11). The declarations are read from the ``experience.components`` block of each
``employment-interface-manifest.v1.json`` found under the contracts directory; an agent version
without a manifest, or a manifest without an experience block, has no declaration and the package
validators refuse it with ``PACKAGE_DECLARATION_UNAVAILABLE``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from markup.package_engine import AgentDeclaration, DeclaredComponent, ThreadRate

logger = logging.getLogger(__name__)

MANIFEST_NAME = "employment-interface-manifest.v1.json"
# The agent type a manifest declares, mapped to the billing-profile registry id that authorizes it (C-088).
BILLING_PROFILE_REGISTRY_IDS: Mapping[str, str] = {"DIGITAL_MARKETING_LOCAL_SERVICE": "dma_v3"}


def _components(experience: Mapping[str, object]) -> dict[str, DeclaredComponent]:
    declared: dict[str, DeclaredComponent] = {}
    entries = experience.get("components")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        component_id, kind, availability = entry.get("componentId"), entry.get("kind"), entry.get("availability")
        if isinstance(component_id, str) and isinstance(kind, str) and isinstance(availability, str):
            declared[component_id] = DeclaredComponent(component_id, kind, availability)
    return declared


def load_declarations(contracts_root: Path) -> list[AgentDeclaration]:
    """Every declaration found in the manifests below ``contracts_root`` (a directory per agent)."""
    declarations: list[AgentDeclaration] = []
    for manifest_path in sorted(contracts_root.glob(f"**/{MANIFEST_NAME}")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.error("pricing_agent_manifest_unreadable", extra={"manifest": manifest_path.parent.name})
            continue
        experience = manifest.get("experience")
        agent_type, agent_version = manifest.get("agentType"), manifest.get("agentVersion")
        if not isinstance(experience, dict) or not isinstance(agent_type, str) or not isinstance(agent_version, str):
            continue
        declarations.append(AgentDeclaration(agent_type, agent_version, _components(experience)))
    return declarations


class ManifestDeclarationSource:
    """``AgentDeclarationSource`` over manifests read once at construction."""

    def __init__(self, declarations: Sequence[AgentDeclaration]) -> None:
        self._declarations = {(item.agent_type, item.agent_version): item for item in declarations}

    @classmethod
    def from_directory(cls, contracts_root: Path) -> ManifestDeclarationSource:
        return cls(load_declarations(contracts_root))

    async def declaration(self, agent_type: str, agent_version: str) -> AgentDeclaration | None:
        return self._declarations.get((agent_type, agent_version))


class RegistryAliasedReference:
    """Package reference data that authorizes an agent type through its billing-profile registry id."""

    def __init__(self, inner, registry_ids: Mapping[str, str] = BILLING_PROFILE_REGISTRY_IDS) -> None:
        self._inner = inner
        self._registry_ids = registry_ids

    async def thread_rates(self, thread_ids: Sequence[str]) -> dict[str, ThreadRate]:
        return await self._inner.thread_rates(thread_ids)

    async def billing_profile_authorized(self, agent_type: str) -> bool:
        return await self._inner.billing_profile_authorized(self._registry_ids.get(agent_type, agent_type))
