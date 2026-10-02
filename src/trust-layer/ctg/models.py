# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §2
# constitutional_basis: C-041 (every tool call governed), C-059 (traceability)
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class SessionContext:
    """Identifies the constitutional context for a single gateway call."""

    tenant_id: UUID
    agent_id: str
    contract_id: str
    skill_id: str
    decision_space: str


@dataclass
class MCPToolError:
    """Sanitized error returned to callers — no credential content permitted (ADR-042 §4)."""

    code: Literal["CONSTITUTIONAL_BLOCKED", "PROVIDER_ERROR", "TOKEN_DEGRADED", "TIMEOUT"]
    message: str
    retry_eligible: bool


@dataclass
class GatewayResult:
    """Return value from ConstitutionalToolGateway.call()."""

    decision_id: str
    result: dict | None = None
    error: MCPToolError | None = None


@dataclass(frozen=True)
class ProviderConfig:
    """Row from BP provider_configs table, fetched by ProviderRegistryClient."""

    provider_name: str
    auth_method: str  # OAUTH2 | API_KEY | INTERNAL_JWT
    mcp_server_url: str | None
    vault_path_key: str
    scope_set: list[str] = field(default_factory=list)


class ConstitutionalBlockError(Exception):
    """Raised when CE.ValidateAction returns DENY or ESCALATE. No external call is made."""

    def __init__(self, decision_id: str, reason: str) -> None:
        self.decision_id = decision_id
        self.reason = reason
        super().__init__(f"CE DENY decision_id={decision_id} reason={reason}")
