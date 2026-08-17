# Implements: architecture/reference/product/ae01-solution-contract.md § Evaluation Workflow
# constitutional_basis: C-023, C-059, C-062, C-063
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Protocol
from urllib.parse import urlparse


class EvaluationState(StrEnum):
    DISCLOSING = "DISCLOSING"
    INTERVIEWING = "INTERVIEWING"
    CONTEXT_ENRICHMENT = "CONTEXT_ENRICHMENT"
    TRIAL_PLANNING = "TRIAL_PLANNING"
    TRIAL_DEMONSTRATING = "TRIAL_DEMONSTRATING"
    CONFIGURING = "CONFIGURING"
    COMPLETE = "COMPLETE"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    STOPPED = "STOPPED"


class AnswerTag(StrEnum):
    CUSTOMER_CONFIRMED_FACT = "CUSTOMER_CONFIRMED_FACT"
    PUBLIC_EVIDENCE = "PUBLIC_EVIDENCE"
    INFERENCE = "INFERENCE"
    RECOMMENDATION = "RECOMMENDATION"
    LIMITATION = "LIMITATION"


@dataclass(frozen=True)
class EvaluationMessage:
    payload_reference: str
    text: str


@dataclass(frozen=True)
class AdapterAnswerProposal:
    proposed_tag: str
    content: str
    source_uri: str | None = None
    source_observed_at: datetime | None = None
    confidence: float | None = None
    basis: str | None = None
    evidence_reference: str | None = None


@dataclass(frozen=True)
class TypedAnswerSegment:
    tag: AnswerTag
    content: str
    source_uri: str | None = None
    source_observed_at: datetime | None = None
    confidence: float | None = None
    basis: str | None = None
    evidence_reference: str | None = None


@dataclass(frozen=True)
class TypedAnswerEnvelope:
    schema_version: str
    relationship_id: str
    payload_reference: str
    segments: tuple[TypedAnswerSegment, ...]


@dataclass(frozen=True)
class TrialCapability:
    capability_id: str
    source_type: str
    paid: bool = False
    external_mutation: bool = False


@dataclass(frozen=True)
class TrialDemonstrationRequest:
    skill_id: str
    goal: str
    context: Mapping[str, str]
    capabilities: tuple[TrialCapability, ...]


@dataclass(frozen=True)
class TrialDemonstration:
    skill_id: str
    applicable: bool
    artifact_type: str | None
    artifact: Mapping[str, object] | None
    capability_ids: tuple[str, ...]
    external_actions: tuple[str, ...] = ()
    reason: str | None = None
    activation_condition: str | None = None


class ProfessionalEvaluationAdapter(Protocol):
    async def describe_suitability(
        self,
        outcome: str,
        confirmed_context: Mapping[str, str],
    ) -> Mapping[str, object]: ...

    async def answer_interview(
        self,
        question: str,
        evidence_context: tuple[str, ...],
    ) -> tuple[AdapterAnswerProposal, ...]: ...

    async def demonstrate(
        self,
        request: TrialDemonstrationRequest,
    ) -> TrialDemonstration: ...

    async def plan_trial(
        self,
        days: int,
        applicable_skills: tuple[str, ...],
    ) -> tuple[Mapping[str, object], ...]: ...

    async def propose_configuration(
        self,
        goals: tuple[str, ...],
        measures: tuple[str, ...],
        skills: tuple[str, ...],
    ) -> Mapping[str, object]: ...


class TextSafetyGate(Protocol):
    def scan(self, text: str) -> bool: ...


_FORWARD_TRANSITIONS: dict[EvaluationState, EvaluationState] = {
    EvaluationState.DISCLOSING: EvaluationState.INTERVIEWING,
    EvaluationState.INTERVIEWING: EvaluationState.CONTEXT_ENRICHMENT,
    EvaluationState.CONTEXT_ENRICHMENT: EvaluationState.TRIAL_PLANNING,
    EvaluationState.TRIAL_PLANNING: EvaluationState.TRIAL_DEMONSTRATING,
    EvaluationState.TRIAL_DEMONSTRATING: EvaluationState.CONFIGURING,
    EvaluationState.CONFIGURING: EvaluationState.COMPLETE,
}
_EXIT_STATES = {
    EvaluationState.DECLINED,
    EvaluationState.EXPIRED,
    EvaluationState.STOPPED,
}
_TERMINAL_STATES = _EXIT_STATES | {EvaluationState.COMPLETE}


class EvaluationTransitionError(ValueError):
    pass


class EvaluationWorkflow:
    def __init__(self) -> None:
        self._state = EvaluationState.DISCLOSING

    @property
    def state(self) -> EvaluationState:
        return self._state

    def transition(self, target: EvaluationState) -> None:
        if self._state in _TERMINAL_STATES:
            raise EvaluationTransitionError(f"Cannot transition from terminal state {self._state}")
        if target not in _EXIT_STATES and _FORWARD_TRANSITIONS.get(self._state) != target:
            raise EvaluationTransitionError(f"Invalid evaluation transition {self._state} -> {target}")
        self._state = target


class InterviewAnswerService:
    def __init__(
        self,
        adapter: ProfessionalEvaluationAdapter,
        injection_gate: TextSafetyGate,
        pii_gate: TextSafetyGate,
    ) -> None:
        self._adapter = adapter
        self._injection_gate = injection_gate
        self._pii_gate = pii_gate

    async def answer(
        self,
        relationship_id: str,
        message: EvaluationMessage,
        evidence_context: tuple[str, ...] = (),
    ) -> TypedAnswerEnvelope:
        if not message.payload_reference.strip():
            return self._limitation(relationship_id, message.payload_reference, "Customer payload is unavailable.")
        if not self._injection_gate.scan(message.text):
            return self._limitation(relationship_id, message.payload_reference, "The request could not be processed safely.")
        if not self._pii_gate.scan(message.text):
            return self._limitation(
                relationship_id, message.payload_reference, "Sensitive information must be removed before continuing."
            )

        try:
            proposals = await self._adapter.answer_interview(message.text, evidence_context)
            segments = tuple(self._validate(proposal) for proposal in proposals)
        except (TypeError, ValueError):
            return self._limitation(
                relationship_id, message.payload_reference, "The available evidence does not support an answer."
            )

        if not segments:
            return self._limitation(
                relationship_id, message.payload_reference, "The available evidence does not support an answer."
            )
        return TypedAnswerEnvelope("1.0", relationship_id, message.payload_reference, segments)

    @staticmethod
    def _validate(proposal: AdapterAnswerProposal) -> TypedAnswerSegment:
        content = proposal.content.strip()
        if not content:
            raise ValueError("Answer content is required")
        try:
            tag = AnswerTag(proposal.proposed_tag)
        except ValueError as exc:
            raise ValueError("Unknown answer tag") from exc

        if tag is AnswerTag.CUSTOMER_CONFIRMED_FACT:
            raise ValueError("Adapters cannot assign customer-confirmed status")
        if tag is AnswerTag.PUBLIC_EVIDENCE:
            if not _is_public_uri(proposal.source_uri) or proposal.source_observed_at is None:
                raise ValueError("Public evidence requires source URI and observation time")
            if not proposal.evidence_reference:
                raise ValueError("Public evidence requires an evidence reference")
        elif tag is AnswerTag.INFERENCE:
            if proposal.confidence is None or not 0 <= proposal.confidence <= 1:
                raise ValueError("Inference requires bounded confidence")
        elif tag is AnswerTag.RECOMMENDATION and not proposal.basis:
            raise ValueError("Recommendation requires a basis")

        return TypedAnswerSegment(
            tag=tag,
            content=content,
            source_uri=proposal.source_uri,
            source_observed_at=proposal.source_observed_at,
            confidence=proposal.confidence,
            basis=proposal.basis,
            evidence_reference=proposal.evidence_reference,
        )

    @staticmethod
    def _limitation(
        relationship_id: str,
        payload_reference: str,
        content: str,
    ) -> TypedAnswerEnvelope:
        return TypedAnswerEnvelope(
            "1.0",
            relationship_id,
            payload_reference,
            (TypedAnswerSegment(AnswerTag.LIMITATION, content),),
        )


class TrialDemonstrationService:
    _ALLOWED_SOURCE_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "LOCAL_INFERENCE",
            "DETERMINISTIC_TOOL",
            "PUBLIC_FREE_SOURCE",
            "APPROVED_TEMPLATE",
            "SYNTHETIC_FIXTURE",
            "PREGENERATED_ASSET",
            "CUSTOMER_APPROVED_ASSET",
        }
    )

    def __init__(self, adapter: ProfessionalEvaluationAdapter) -> None:
        self._adapter = adapter

    async def demonstrate(self, request: TrialDemonstrationRequest) -> TrialDemonstration:
        if not request.skill_id.strip() or not request.goal.strip():
            raise ValueError("Trial demonstration requires a skill and goal")
        if not request.capabilities:
            raise ValueError("Trial capabilities are required")
        capability_index = {capability.capability_id: capability for capability in request.capabilities}
        if len(capability_index) != len(request.capabilities):
            raise ValueError("Trial capability identifiers must be unique")
        if any(
            capability.paid or capability.external_mutation or capability.source_type not in self._ALLOWED_SOURCE_TYPES
            for capability in request.capabilities
        ):
            raise ValueError("Trial capabilities must be local, free, approved, or synthetic and non-mutating")

        result = await self._adapter.demonstrate(request)
        if result.skill_id != request.skill_id:
            raise ValueError("Adapter returned a demonstration for a different skill")
        if result.external_actions:
            raise ValueError("Trial demonstrations cannot cause external actions")
        if any(capability_id not in capability_index for capability_id in result.capability_ids):
            raise ValueError("Adapter used an undeclared trial capability")
        if result.applicable:
            if not result.artifact_type or result.artifact is None or not result.capability_ids:
                raise ValueError("Applicable skills require a simulated artifact and capability provenance")
            if result.reason or result.activation_condition:
                raise ValueError("Applicable skills cannot carry non-applicability fields")
        elif (
            result.artifact_type is not None
            or result.artifact is not None
            or result.capability_ids
            or not result.reason
            or not result.activation_condition
        ):
            raise ValueError("Non-applicable skills require reason and activation condition only")
        return result


def _is_public_uri(value: str | None) -> bool:
    if value is None:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
