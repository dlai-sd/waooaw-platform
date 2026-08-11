# Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-02
# constitutional_basis: C-023, C-059, C-062, C-063, C-076
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from evaluation_workflow import (
    AdapterAnswerProposal,
    AnswerTag,
    EvaluationMessage,
    EvaluationState,
    EvaluationTransitionError,
    EvaluationWorkflow,
    InterviewAnswerService,
)
from session_executor import SessionExecutor
from skill_resolver import SessionSkillContext


class StaticGate:
    def __init__(self, safe: bool = True) -> None:
        self.safe = safe

    def scan(self, text: str) -> bool:
        return self.safe


class RecordingAdapter:
    def __init__(self, proposals: tuple[AdapterAnswerProposal, ...]) -> None:
        self.proposals = proposals
        self.calls: list[str] = []

    async def answer_interview(
        self,
        question: str,
        evidence_context: tuple[str, ...],
    ) -> tuple[AdapterAnswerProposal, ...]:
        self.calls.append(question)
        return self.proposals


def make_service(
    adapter: RecordingAdapter,
    injection_safe: bool = True,
    pii_safe: bool = True,
) -> InterviewAnswerService:
    return InterviewAnswerService(adapter, StaticGate(injection_safe), StaticGate(pii_safe))


def test_state_machine_allows_only_normative_progression_and_exits() -> None:
    workflow = EvaluationWorkflow()
    for state in (
        EvaluationState.INTERVIEWING,
        EvaluationState.CONTEXT_ENRICHMENT,
        EvaluationState.TRIAL_PLANNING,
        EvaluationState.TRIAL_DEMONSTRATING,
        EvaluationState.CONFIGURING,
        EvaluationState.COMPLETE,
    ):
        workflow.transition(state)
    assert workflow.state is EvaluationState.COMPLETE
    with pytest.raises(EvaluationTransitionError):
        workflow.transition(EvaluationState.STOPPED)

    declined = EvaluationWorkflow()
    declined.transition(EvaluationState.DECLINED)
    assert declined.state is EvaluationState.DECLINED


def test_state_machine_rejects_skipped_phase() -> None:
    workflow = EvaluationWorkflow()
    with pytest.raises(EvaluationTransitionError):
        workflow.transition(EvaluationState.TRIAL_PLANNING)


@pytest.mark.asyncio
async def test_public_evidence_is_server_validated_and_keeps_payload_separate() -> None:
    observed_at = datetime(2026, 8, 11, tzinfo=UTC)
    adapter = RecordingAdapter((AdapterAnswerProposal(
        proposed_tag="PUBLIC_EVIDENCE",
        content="The public directory lists weekend opening hours.",
        source_uri="https://example.test/directory",
        source_observed_at=observed_at,
        evidence_reference="evidence-ref-1",
    ),))
    result = await make_service(adapter).answer(
        "relationship-1",
        EvaluationMessage("payload-ref-1", "What are our opening hours?"),
    )

    assert result.payload_reference == "payload-ref-1"
    assert result.segments[0].tag is AnswerTag.PUBLIC_EVIDENCE
    assert result.segments[0].source_observed_at == observed_at
    assert "What are our opening hours?" not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposal",
    [
        AdapterAnswerProposal("CUSTOMER_CONFIRMED_FACT", "The customer approved it."),
        AdapterAnswerProposal("PUBLIC_EVIDENCE", "Unsupported public claim."),
        AdapterAnswerProposal("INFERENCE", "Unbounded inference.", confidence=1.5),
        AdapterAnswerProposal("RECOMMENDATION", "Unsupported recommendation."),
    ],
)
async def test_invalid_or_forged_adapter_tags_fall_back_to_limitation(
    proposal: AdapterAnswerProposal,
) -> None:
    result = await make_service(RecordingAdapter((proposal,))).answer(
        "relationship-1",
        EvaluationMessage("payload-ref-1", "Customer question"),
    )
    assert result.segments == (
        result.segments[0],
    )
    assert result.segments[0].tag is AnswerTag.LIMITATION


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_safe,pii_safe", [(False, True), (True, False)])
async def test_safety_gate_denial_never_invokes_adapter(
    injection_safe: bool,
    pii_safe: bool,
) -> None:
    adapter = RecordingAdapter((AdapterAnswerProposal("LIMITATION", "No answer."),))
    result = await make_service(adapter, injection_safe, pii_safe).answer(
        "relationship-1",
        EvaluationMessage("payload-ref-1", "Untrusted customer text"),
    )
    assert result.segments[0].tag is AnswerTag.LIMITATION
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_skill_runtime_routes_interview_through_validated_adapter_boundary() -> None:
    adapter = RecordingAdapter((AdapterAnswerProposal(
        "INFERENCE",
        "Weekend availability may improve booking fit.",
        confidence=0.7,
    ),))
    executor = SessionExecutor(
        SessionSkillContext(),
        interview_service=make_service(adapter),
    )

    result = await executor.answer_interview(
        "relationship-1",
        EvaluationMessage("payload-ref-1", "Would weekend hours help?"),
        ("evidence-ref-1",),
    )

    assert result.segments[0].tag is AnswerTag.INFERENCE
    assert result.segments[0].confidence == 0.7
    assert adapter.calls == ["Would weekend hours help?"]


@pytest.mark.asyncio
async def test_skill_runtime_fails_closed_without_evaluation_adapter() -> None:
    executor = SessionExecutor(SessionSkillContext())
    with pytest.raises(RuntimeError, match="not configured"):
        await executor.answer_interview(
            "relationship-1",
            EvaluationMessage("payload-ref-1", "Customer question"),
        )