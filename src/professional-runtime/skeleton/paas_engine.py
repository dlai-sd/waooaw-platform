# Implements: architecture/reference/components/manifest/pr.yaml §surface.endpoints
# Constitutional basis: C-001 (Human Override), C-023 (Evidence First), C-059
# EA-PRODUCED SKELETON — DO NOT change signatures. Raise SPEC_GAP if change needed.

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional


class IPAASEngine(ABC):
    """
    Professional Autonomous Agent Session (PAAS) runtime.
    Manages agent session lifecycle under constitutional governance.
    Constitutional: C-001 (Emergency Stop always reachable), C-023 (Evidence First).
    """

    @abstractmethod
    async def create_session(self, contract_id: UUID, tenant_id: str, agent_type: str) -> PAASSession:
        # Raises: SessionCreationError if CE cannot be reached (ADR-031)
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID, tenant_id: str) -> PAASSession:
        # Raises: SessionNotFoundError
        ...

    @abstractmethod
    async def emergency_stop(self, session_ids: list[UUID], initiated_by: str) -> EmergencyStopResult:
        # Constitutional: C-001 — NEVER fails. NEVER blocks.
        # SLA: ≤250ms p99
        # Must record evidence BEFORE returning success (C-023)
        ...


@dataclass(frozen=True)
class PAASSession:
    session_id: UUID
    contract_id: UUID
    tenant_id: str
    agent_type: str
    status: str  # ACTIVE | STOPPED | PAUSED
    created_at: datetime
    temporal_workflow_id: str | None


@dataclass(frozen=True)
class EmergencyStopResult:
    sessions_stopped: list[UUID]
    evidence_record_id: UUID
    stopped_at: datetime
    latency_ms: float


class SessionNotFoundError(Exception):
    """Raised when session_id does not exist for given tenant."""


class SessionCreationError(Exception):
    """Raised when CE is unavailable and session cannot be constitutionally created."""
