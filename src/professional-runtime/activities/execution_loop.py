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
    C-059: Evidence of retrieval logged for audit trail.
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
                "decision_space_id": retrieve_input.decision_space_id,
                "error_type": type(e).__name__
            }
        )
        raise


# ─── REASON Activity (Step 3: Reasoning) ────────────────────────────────────


@activity.defn
async def reason(reason_input: ReasonInput) -> ReasonOutput:
    """
    REASON activity: Reason over retrieved information to propose an action.

    Stub implementation: returns placeholder proposed action.
    Real implementation: calls AI Runtime LLM for reasoning.
    ⛔ NO LLM CALLS HERE — that is AI Runtime's responsibility (WC015).

    C-047: Step 3 of 5 in execution sequence.
    C-063: No PII in logs.
    """
    try:
        reasoning_id = str(uuid.uuid4())
        logger.info(
            "REASON activity started",
            extra={
                "reasoning_id": reasoning_id,
                "observation_id": reason_input.observation_id,
                "retrieval_id": reason_input.retrieval_id,
                "decision_space_id": reason_input.decision_space_id
            }
        )

        # Stub: simulate reasoning
        await asyncio.sleep(0.03)
        proposed_action = {
            "action_type": "send_communication",
            "target": "placeholder_recipient",
            "content_template": "sample_template_id",
            "parameters": {}
        }

        result = ReasonOutput(
            reasoning_id=reasoning_id,
            proposed_action=proposed_action,
            confidence=0.85,
            status="reasoned"
        )

        logger.info(
            "REASON activity completed",
            extra={
                "reasoning_id": reasoning_id,
                "proposed_action_type": proposed_action.get("action_type"),
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
                "decision_space_id": reason_input.decision_space_id,
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
    Real implementation: calls AI Runtime to execute action (dispatch, store, etc.).
    ⛔ NO EXTERNAL API CALLS HERE YET — that is AI Runtime's responsibility (WC015).

    C-047: Step 4 of 5 in execution sequence.
    C-023: Every action execution must be preceded by Constitutional Engine validation.
    """
    try:
        execution_id = str(uuid.uuid4())
        logger.info(
            "ACT activity started",
            extra={
                "execution_id": execution_id,
                "reasoning_id": act_input.reasoning_id,
                "session_id": act_input.session_id,
                "decision_space_id": act_input.decision_space_id
            }
        )

        # Stub: simulate action execution
        await asyncio.sleep(0.04)
        action_result = {
            "status": "success",
            "execution_timestamp": activity.info().started_at.isoformat() if activity.info().started_at else None,
            "resource_id": str(uuid.uuid4()),
            "details": {}
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
                "action_status": action_result.get("status"),
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
                "session_id": act_input.session_id,
                "decision_space_id": act_input.decision_space_id,
                "error_type": type(e).__name__
            }
        )
        raise


# ─── RECORD Activity (Step 5: Evidence Recording) ──────────────────────────


@activity.defn
async def record(record_input: RecordInput) -> RecordOutput:
    """
    RECORD activity: Record evidence of the action execution via Constitutional Engine.

    Stub implementation: returns placeholder evidence record.
    Real implementation: calls Constitutional Engine gRPC RecordEvidence endpoint.

    C-023: RECORD must always execute (Evidence First principle).
         This activity should be called in a try/finally block by the workflow.
    C-047: Step 5 of 5 in execution sequence.
    C-059: Every exception caught must produce an evidence record (C-059 compliance).
    C-063: No PII in logs.

    This activity simulates calling CE.RecordEvidence(EvaluationContext) → ValidateActionResponse
    with decision (Allow/Deny/Escalate) and evidence_record_id persisted to Constitutional schema.
    """
    try:
        evidence_record_id = str(uuid.uuid4())
        logger.info(
            "RECORD activity started",
            extra={
                "evidence_record_id": evidence_record_id,
                "execution_id": record_input.execution_id,
                "session_id": record_input.session_id,
                "evidence_type": record_input.evidence_type,
                "has_error": record_input.error is not None
            }
        )

        # Stub: simulate Constitutional Engine gRPC call and evidence persistence
        await asyncio.sleep(0.05)  # Simulate RPC latency (~50-80ms per spec)
        persisted_at = activity.info().started_at.isoformat() if activity.info().started_at else None

        result = RecordOutput(
            evidence_record_id=evidence_record_id,
            persisted_at=persisted_at,
            status="recorded"
        )

        logger.info(
            "RECORD activity completed",
            extra={
                "evidence_record_id": evidence_record_id,
                "execution_id": record_input.execution_id,
                "status": result.status,
                "persisted_at": persisted_at
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
                "evidence_record_id": str(uuid.uuid4()),
                "execution_id": record_input.execution_id,
                "session_id": record_input.session_id,
                "evidence_type": record_input.evidence_type,
                "error_type": type(e).__name__
            }
        )
        raise