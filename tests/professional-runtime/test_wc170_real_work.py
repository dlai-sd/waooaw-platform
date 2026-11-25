"""WC-170 real agent work: vocabulary resolution, locked-artifact binding and the PR execution stream."""

# Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R004, WC170-R005, WC170-R007, WC170-R010
# Constitutional basis: C-001, C-023, C-042, C-049, C-059, C-076

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from domain_vocabulary import (
    DomainVocabulary,
    VocabularyDigestMismatch,
    VocabularyNotBound,
    VocabularyRegistry,
)
from execution_timeline import (
    EXECUTE_STEP_ACTION,
    ArtifactBinding,
    ArtifactBindingRefused,
    BlindRetryRefused,
    ExecutionTimeline,
    ProviderResult,
    ProviderStatus,
    ReasonCode,
    TimelineEvent,
    WorkItem,
    WorkItemState,
)
from intent_crystallizer import LockedArtifact, StubApprovalRefused
from session_executor import SessionExecutor
from skill_resolver import SessionSkillContext

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json").read_text())
TUTOR = ROOT / "tests/fixtures/wc170/tutor-domain-vocabulary.v1.json"


def _dma() -> DomainVocabulary:
    return DomainVocabulary.from_reference(ROOT, MANIFEST["experience"]["vocabularyRef"])


def _tutor() -> DomainVocabulary:
    reference = {
        "contractRef": str(TUTOR.relative_to(ROOT)),
        "contractVersion": "1.0",
        "contractDigest": hashlib.sha256(TUTOR.read_bytes()).hexdigest(),
    }
    return DomainVocabulary.from_reference(ROOT, reference)


def test_the_manifest_names_the_real_vocabulary_and_its_exact_digest() -> None:
    reference = MANIFEST["experience"]["vocabularyRef"]
    assert reference["contractRef"].endswith("domain-vocabulary.v1.json")
    assert _dma().digest == reference["contractDigest"]


def test_a_digest_mismatch_fails_closed() -> None:
    reference = dict(MANIFEST["experience"]["vocabularyRef"], contractDigest="0" * 64)
    with pytest.raises(VocabularyDigestMismatch):
        DomainVocabulary.from_reference(ROOT, reference)


def test_two_businesses_on_one_agent_resolve_different_wording_from_their_selector() -> None:
    dma = _dma()
    sentence = "Remind each {DVE.CUSTOMER_SINGULAR} before the {DVE.VISIT_NOUN}."

    dental = dma.resolve(sentence, "dental_clinic")
    fitness = dma.resolve(sentence, "fitness_studio")

    assert dental.text == "Remind each patient before the appointment."
    assert fitness.text == "Remind each member before the session."
    assert dental.vocabulary_digest == dma.digest and dental.vocabulary_version == "3.1"


def test_two_professions_resolve_through_the_same_code_with_no_agent_branch() -> None:
    registry = VocabularyRegistry()
    registry.bind("digital-marketing", "1.0.0", _dma())
    registry.bind("private-tutor", "1.0.0", _tutor())
    sentence = "Book the {DVE.VISIT_NOUN} for each {DVE.CUSTOMER_SINGULAR}."

    marketing = registry.resolve("digital-marketing", "1.0.0", sentence, "dental_clinic")
    tutor = registry.resolve("private-tutor", "1.0.0", sentence, "primary_school")

    assert marketing.text == "Book the appointment for each patient."
    assert tutor.text == "Book the lesson for each pupil."
    assert marketing.vocabulary_digest != tutor.vocabulary_digest
    with pytest.raises(VocabularyNotBound):
        registry.resolve("trading", "1.0.0", sentence, None)


def test_an_unknown_token_is_a_named_gap_with_a_limitation_never_blank() -> None:
    result = _dma().resolve("Hello {DVE.NOT_A_TOKEN}!", "dental_clinic")

    assert result.text == "Hello [missing wording: NOT_A_TOKEN]!"
    assert [gap.token for gap in result.gaps] == ["NOT_A_TOKEN"]
    assert any("NOT_A_TOKEN" in item for item in result.limitations)


def test_an_unknown_business_domain_uses_general_wording_and_says_so() -> None:
    result = _dma().resolve("A {DVE.CUSTOMER_SINGULAR}.", "plumbing")

    assert result.text == "A customer."
    assert result.limitations and "plumbing" in result.limitations[0]


def test_stub_or_empty_approval_never_locks_an_artifact() -> None:
    executor = SessionExecutor(session_ctx=SessionSkillContext())
    stub = LockedArtifact("skill", "campaign_brief", {"a": 1}, "evidence-skill-approval-stub")
    empty = LockedArtifact("skill", "campaign_brief", {"a": 1}, "")
    genuine = LockedArtifact("skill", "campaign_brief", {"a": 1}, "evidence-123")

    assert not stub.has_genuine_approval()
    assert not empty.has_genuine_approval()
    assert genuine.has_genuine_approval()
    with pytest.raises(StubApprovalRefused):
        executor.add_locked_artifact("skill", stub)
    with pytest.raises(StubApprovalRefused):
        executor.add_locked_artifact("skill", empty)
    assert not executor.is_crystallization_complete("skill")
    executor.add_locked_artifact("skill", genuine)
    assert executor.is_crystallization_complete("skill")


def test_the_local_content_digest_ignores_property_order() -> None:
    first = LockedArtifact("s", "brief", {"a": 1, "b": [1, 2]}, "e-1")
    second = LockedArtifact("s", "brief", {"b": [1, 2], "a": 1}, "e-1")

    assert first.content_digest() == second.content_digest()


class Sink:
    def __init__(self) -> None:
        self.events: list[TimelineEvent] = []

    async def deliver(self, event: TimelineEvent) -> None:
        self.events.append(event)


class Gate:
    def __init__(self, *, deny: bool = False) -> None:
        self.deny = deny
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def validate(self, action_type: str, parameters: dict[str, str]) -> None:
        self.calls.append((action_type, parameters))
        if self.deny:
            raise PermissionError("denied")


def _item(*, relationship=None, proof=False, produces=False, binding=True) -> WorkItem:
    return WorkItem(
        tenant_id=uuid4(),
        relationship_id=relationship or uuid4(),
        work_item_id=uuid4(),
        work_item_type="SOCIAL_POST",
        binding=ArtifactBinding(uuid4(), "a" * 64, "LOCKED", uuid4(), uuid4()) if binding else None,
        produces_artifact=produces,
        requires_provider_proof=proof,
    )


def _timeline(gate: Gate | None = None) -> tuple[ExecutionTimeline, Sink, Gate]:
    sink, gate = Sink(), gate or Gate()
    return ExecutionTimeline(sink=sink, gate=gate), sink, gate


async def _confirmed() -> ProviderResult:
    return ProviderResult(ProviderStatus.CONFIRMED, "page_1_post_2", ("provider:ok",))


@pytest.mark.asyncio
async def test_a_step_walks_the_states_and_names_its_artifact_to_the_constitutional_gate() -> None:
    timeline, sink, gate = _timeline()
    item = _item()

    final = await timeline.dispatch(item, _confirmed)

    assert [event.state for event in sink.events] == [
        WorkItemState.APPROVED,
        WorkItemState.EXECUTING,
        WorkItemState.COMPLETED,
    ]
    assert final.provider_reference == "page_1_post_2"
    assert gate.calls[0][0] == EXECUTE_STEP_ACTION
    assert gate.calls[0][1]["artifactDigest"] == "a" * 64
    assert all(event.artifact_digest == "a" * 64 for event in sink.events)


@pytest.mark.asyncio
async def test_a_step_without_a_binding_or_with_a_denied_gate_is_refused_before_any_provider_call() -> None:
    calls = 0

    async def provider() -> ProviderResult:
        nonlocal calls
        calls += 1
        return await _confirmed()

    timeline, sink, _ = _timeline()
    with pytest.raises(ArtifactBindingRefused):
        await timeline.dispatch(_item(binding=False), provider)
    denied, denied_sink, _ = _timeline(Gate(deny=True))
    with pytest.raises(ArtifactBindingRefused):
        await denied.dispatch(_item(), provider)

    assert calls == 0
    assert sink.events[-1].reason_code is ReasonCode.POLICY_BLOCKED
    assert denied_sink.events[-1].state is WorkItemState.FAILED


@pytest.mark.asyncio
async def test_an_artifact_creating_step_needs_no_binding() -> None:
    timeline, sink, gate = _timeline()

    await timeline.dispatch(_item(produces=True, binding=False), _confirmed)

    assert gate.calls == []
    assert sink.events[-1].state is WorkItemState.COMPLETED


@pytest.mark.asyncio
async def test_a_receipt_without_the_providers_reference_stays_in_progress() -> None:
    async def receipt() -> ProviderResult:
        return ProviderResult(ProviderStatus.ACCEPTED, None, ("receipt:1",))

    timeline, _, _ = _timeline()

    final = await timeline.dispatch(_item(proof=True), receipt)

    assert final.state is WorkItemState.EXECUTING
    assert final.reason_code is ReasonCode.AWAITING_PROVIDER_PROOF


@pytest.mark.asyncio
async def test_a_rejection_fails_with_a_reason() -> None:
    async def rejected() -> ProviderResult:
        return ProviderResult(ProviderStatus.REJECTED, None, ("provider:400",))

    timeline, _, _ = _timeline()

    final = await timeline.dispatch(_item(), rejected)

    assert (final.state, final.reason_code) == (WorkItemState.FAILED, ReasonCode.PROVIDER_REJECTED)


@pytest.mark.asyncio
async def test_an_unknown_outcome_is_reconciled_and_never_dispatched_again_blindly() -> None:
    calls = 0

    async def flaky() -> ProviderResult:
        nonlocal calls
        calls += 1
        raise TimeoutError("no answer")

    timeline, _, _ = _timeline()
    item = _item(proof=True)

    unknown = await timeline.dispatch(item, flaky)
    with pytest.raises(BlindRetryRefused):
        await timeline.dispatch(item, flaky)
    reconciled = await timeline.reconcile(item, ProviderResult(ProviderStatus.CONFIRMED, "post_9", ("provider:status",)))

    assert calls == 1
    assert unknown.reason_code is ReasonCode.UNKNOWN_OUTCOME
    assert (reconciled.state, reconciled.reason_code) == (WorkItemState.COMPLETED, ReasonCode.RECONCILED)
    assert reconciled.provider_reference == "post_9"


@pytest.mark.asyncio
async def test_emergency_stop_fences_dispatch_before_any_provider_call_and_spares_other_relationships() -> None:
    calls = 0

    async def provider() -> ProviderResult:
        nonlocal calls
        calls += 1
        return await _confirmed()

    timeline, _, _ = _timeline()
    stopped, other = _item(), _item()

    marker = await timeline.emergency_stop(stopped.tenant_id, stopped.relationship_id)
    halted = await timeline.dispatch(stopped, provider)
    fine = await timeline.dispatch(other, provider)

    assert (marker.state, marker.reason_code) == (WorkItemState.HALTED, ReasonCode.EMERGENCY_STOP)
    assert (halted.state, halted.reason_code) == (WorkItemState.HALTED, ReasonCode.EMERGENCY_STOP)
    assert fine.state is WorkItemState.COMPLETED
    assert calls == 1


@pytest.mark.asyncio
async def test_a_result_that_arrives_after_the_stop_is_halted_evidence_never_success() -> None:
    timeline, sink, _ = _timeline()
    item = _item()

    async def stop_during_call() -> ProviderResult:
        await timeline.emergency_stop(item.tenant_id, item.relationship_id)
        return await _confirmed()

    final = await timeline.dispatch(item, stop_during_call)

    assert (final.state, final.reason_code) == (WorkItemState.HALTED, ReasonCode.EMERGENCY_STOP)
    assert "late-result:confirmed" in final.evidence_refs
    assert not any(event.state is WorkItemState.COMPLETED for event in sink.events)


@pytest.mark.asyncio
async def test_a_stop_recorded_while_the_step_is_being_announced_still_fences_the_provider_call() -> None:
    calls = 0

    async def provider() -> ProviderResult:
        nonlocal calls
        calls += 1
        return await _confirmed()

    class StoppingSink(Sink):
        timeline: ExecutionTimeline

        async def deliver(self, event: TimelineEvent) -> None:
            await super().deliver(event)
            if event.state is WorkItemState.EXECUTING:
                await self.timeline.emergency_stop(event.tenant_id, event.relationship_id)

    sink = StoppingSink()
    timeline = ExecutionTimeline(sink=sink, gate=Gate())
    sink.timeline = timeline

    final = await timeline.dispatch(_item(), provider)

    assert calls == 0
    assert (final.state, final.reason_code) == (WorkItemState.HALTED, ReasonCode.EMERGENCY_STOP)


def test_an_artifact_creating_step_cannot_carry_a_binding_or_need_provider_proof() -> None:
    with pytest.raises(ValueError):
        _item(produces=True)
    with pytest.raises(ValueError):
        _item(produces=True, proof=True, binding=False)


def test_a_credential_looking_value_cannot_enter_the_stream() -> None:
    event = TimelineEvent(
        event_id=uuid4(),
        tenant_id=uuid4(),
        relationship_id=uuid4(),
        work_item_id=uuid4(),
        work_item_type="SOCIAL_POST",
        state=WorkItemState.COMPLETED,
        occurred_at=datetime.now(timezone.utc),
        evidence_refs=("Bearer abc.def",),
    )

    with pytest.raises(ValueError):
        event.to_payload()
