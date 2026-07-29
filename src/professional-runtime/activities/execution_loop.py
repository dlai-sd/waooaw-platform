# Implements: architecture/reference/api-specs/emergency-stop-ws.md full
# constitutional_basis: C-023, C-047, C-059, C-063, C-076
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)


# ─── Data Models ────────────────────────────────────────────────────────────


@dataclass
class SenseInput:
    """Input to the SENSE activity."""
    session_id: str
    contract_id: str
    decision_space_id: str


@dataclass
class SenseOutput:
    """Output from the SENSE activity."""
    observation_id: str
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "sensed"


@dataclass
class RetrieveInput:
    """Input to the RETRIEVE activity."""
    observation_id: str
    decision_space_id: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrieveOutput:
    """Output from the RETRIEVE activity."""
    retrieval_id: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    status: str = "retrieved"


@dataclass
class ReasonInput:
    """Input to the REASON activity."""
    observation_id: str
    retrieval_id: str
    decision_space_id: str
    context: dict[str, Any] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReasonOutput:
    """Output from the REASON activity."""
    reasoning_id: str
    proposed_action: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "reasoned"


@dataclass
class ActInput:
    """Input to the ACT activity."""
    reasoning_id: str
    proposed_action: dict[str, Any] = field(default_factory=dict)
    session_id: str
    contract_id: str
    decision_space_id: str


@dataclass
class ActOutput:
    """Output from the ACT activity."""
    execution_id: str
    action_result: dict[str, Any] = field(default_factory=dict)
    status: str = "executed"


@dataclass
class RecordInput:
    """Input to the RECORD activity."""
    execution_id: str
    session_id: str
    contract_id: str
    decision_space_id: str
    proposed_action: dict[str, Any] = field(default_factory=dict)
    action_result: dict[str, Any] = field(default_factory=dict)
    evidence_type: str = "ACTION_EXECUTION"
    error: str | None = None


@dataclass
class RecordOutput:
    """Output from the RECORD activity."""
    evidence_record_id: str
    persisted_at: str
    status: str = "recorded"


# ─── SENSE Activity (Step 1: Perception) ────────────────────────────────────


@activity.defn
async def sense(sense_input: SenseInput) -> SenseOutput:
    """
    SENSE activity: Perceive the current state of the session.
    
    Stub implementation: returns placeholder observation.
    Real implementation: query Professional Runtime state, context from DB.
    
    C-047: Step 1 of 5 in execution sequence.
    C-063: No PII in logs.
    """
    try:
        observation_id = str(uuid.uuid4())
        logger.info(
            "SENSE activity started",
            extra={"observation_id": observation_id, "session_id": sense_input.session_id}
        )

        # Stub: simulate observation collection
        await asyncio.sleep(0.01)  # Minimal latency
        context = {
            "timestamp": activity.info().started_at.isoformat() if activity.info().started_at else None,
            "session_id": sense_input.session_id,
            "decision_space_id": sense_input.decision_space_id,
        }

        result = SenseOutput(
            observation_id=observation_id,
            context=context,
            status="sensed"
        )

        logger.info(
            "SENSE activity completed",
            extra={"observation_id": observation_id, "status": result.status}
        )
        return result

    except asyncio.CancelledError:
        logger.info("SENSE activity cancelled")
        raise
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(
            "SENSE activity failed",
            exc_info=True,
            extra={"session_id": sense_input.session_id, "error_type": type(e).__name__}
        )
        raise


# ─── RETRIEVE Activity (Step 2: Information Retrieval) ──────────────────────


@activity.defn
async def retrieve(retrieve_input: RetrieveInput) -> RetrieveOutput:
    """
    RETRIEVE activity: Fetch relevant information from Decision Space and context.
    
    Stub implementation: returns empty document list.
    Real implementation: calls AI Runtime RAG or Decision Space repository.
    
    C-047: Step 2 of 5 in execution sequence.
    """
    try:
        retrieval_id = str(uuid.uuid4())
        logger.info(
            "RETRIEVE activity started",
            extra={
                "retrieval_id": retrieval_id,
                "observation_id": retrieve_input.observation_id,
                "decision_space_id": retrieve_input.decision_space_id
            }
        )

        # Stub: simulate document retrieval
        await asyncio.sleep(0.02)
        documents = [
            {
                "id": str(uuid.uuid4()),
                "type": "decision_space_constraint",
                "title": "Sample Decision Space Rule",
                "relevance": 0.95
            }
        ]

        result = RetrieveOutput(
            retrieval_id=retrieval_id,
            documents=documents,
            status="retrieved"
        )

        logger.info(
            "RETRIEVE activity completed",
            extra={
                "retrieval_id": retrieval_id,
                "document_count": len(documents),
                "status": result.status
            }
        )
        return result

    except asyncio.CancelledError:
        logger.info("RETRIEVE activity cancelled")
        raise
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(
            "RETRIEVE activity failed",
            exc_info=True,
            extra={
                "observation_id": retrieve_input.observation_id,
                "error_type": type(e).__name__
            }
        )
        raise


# ─── REASON Activity (Step 3: Reasoning & Planning) ────────────────────────


@activity.defn
async def reason(reason_input: ReasonInput) -> ReasonOutput:
    """
    REASON activity: Synthesize observation + retrieval into proposed action.
    
    Stub implementation: returns empty proposed action.
    Real implementation: calls AI Runtime LLM with Decision Space context.
    NOTE: This is a stub only. Real LLM calls happen in WC015 (AI Runtime).
    
    C-047: Step 3 of 5 in execution sequence.
    C-023: Evidence First — proposed action validated before ACT.
    """
    try:
        reasoning_id = str(uuid.uuid4())
        logger.info(
            "REASON activity started",
            extra={
                "reasoning_id": reasoning_id,
                "observation_id": reason_input.observation_id,
                "retrieval_id": reason_input.retrieval_id
            }
        )

        # Stub: simulate reasoning
        await asyncio.sleep(0.03)
        proposed_action = {
            "action_type": "placeholder",
            "description": "Stub action (real reasoning in AI Runtime WC015)",
            "confidence_score": 0.75
        }

        result = ReasonOutput(
            reasoning_id=reasoning_id,
            proposed_action=proposed_action,
            confidence=0.75,
            status="reasoned"
        )

        logger.info(
            "REASON activity completed",
            extra={
                "reasoning_id": reasoning_id,
                "confidence": result.confidence,
                "status": result.status
            }
        )
        return result

    except asyncio.CancelledError:
        logger.info("REASON activity cancelled")
        raise
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(
            "REASON activity failed",
            exc_info=True,
            extra={
                "observation_id": reason_input.observation_id,
                "error_type": type(e).__name__
            }
        )
        raise


# ─── ACT Activity (Step 4: Action Execution) ────────────────────────────────


@activity.defn
async def act(act_input: ActInput) -> ActOutput:
    """
    ACT activity: Execute the proposed action.
    
    Stub implementation: returns placeholder execution result.
    Real implementation: calls AI Runtime or external service.
    NOTE: This executes AFTER Constitutional Engine validates via RecordEvidence.
    
    C-047: Step 4 of 5 in execution sequence.
    C-023: Must be preceded by RECORD evidence call (handled in workflow).
    """
    try:
        execution_id = str(uuid.uuid4())
        logger.info(
            "ACT activity started",
            extra={
                "execution_id": execution_id,
                "reasoning_id": act_input.reasoning_id,
                "session_id": act_input.session_id
            }
        )

        # Stub: simulate action execution
        await asyncio.sleep(0.05)
        action_result = {
            "execution_status": "success",
            "result_id": str(uuid.uuid4()),
            "output": "Stub execution result (real execution in AI Runtime WC015)"
        }

        result = ActOutput(
            execution_id=execution_id,
            action_result=action_result,
            status="executed"
        )

        logger.info(
            "ACT activity completed",
            extra={
                "execution_id": execution_id,
                "result_status": action_result.get("execution_status"),
                "status": result.status
            }
        )
        return result

    except asyncio.CancelledError:
        logger.info("ACT activity cancelled")
        raise
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(
            "ACT activity failed",
            exc_info=True,
            extra={
                "reasoning_id": act_input.reasoning_id,
                "error_type": type(e).__name__
            }
        )
        raise


# ─── RECORD Activity (Step 5: Evidence Recording) ──────────────────────────


@activity.defn
async def record(record_input: RecordInput) -> RecordOutput:
    """
    RECORD activity: Persist evidence to Constitutional Engine (Evidence First).
    
    Stub implementation: returns evidence record ID placeholder.
    Real implementation: calls Constitutional Engine gRPC RecordEvidence endpoint.
    
    C-047: Step 5 of 5 in execution sequence.
    C-023: Evidence First — RECORD must always execute, even on error.
    C-059: Evidence record created for every action (audit trail).
    C-063: No PII in logs.
    
    NOTE: In workflow orchestration, this is called:
      1. BEFORE ACT (to validate and record intent)
      2. ON ERROR (to record abandonment/failure)
    The workflow ensures RECORD is never skipped.
    """
    try:
        evidence_record_id = str(uuid.uuid4())
        logger.info(
            "RECORD activity started",
            extra={
                "evidence_record_id": evidence_record_id,
                "execution_id": record_input.execution_id,
                "session_id": record_input.session_id,
                "evidence_type": record_input.evidence_type
            }
        )

        # Stub: simulate evidence write to Constitutional Engine
        await asyncio.sleep(0.02)

        from datetime import datetime, timezone
        persisted_at = datetime.now(timezone.utc).isoformat()

        result = RecordOutput(
            evidence_record_id=evidence_record_id,
            persisted_at=persisted_at,
            status="recorded"
        )

        logger.info(
            "RECORD activity completed",
            extra={
                "evidence_record_id": evidence_record_id,
                "evidence_type": record_input.evidence_type,
                "persisted_at": persisted_at,
                "status": result.status
            }
        )
        return result

    except asyncio.CancelledError:
        logger.info("RECORD activity cancelled")
        raise
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(
            "RECORD activity failed",
            exc_info=True,
            extra={
                "execution_id": record_input.execution_id,
                "evidence_type": record_input.evidence_type,
                "error_type": type(e).__name__
            }
        )
        raise