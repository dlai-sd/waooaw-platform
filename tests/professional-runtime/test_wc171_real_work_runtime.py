"""WC-171 carry-ins: durable stop barrier, spend hook, executor wiring, signed spend client."""

# Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R011
# Constitutional basis: C-001, C-005, C-023, C-059, C-063, C-076, ADR-046

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from execution_timeline import (
    ArtifactBinding,
    BarrierDecision,
    BlindRetryRefused,
    ExecutionTimeline,
    ProviderResult,
    ProviderStatus,
    ReasonCode,
    SpendRefused,
    StepBlocked,
    TimelineEvent,
    WorkItem,
    WorkItemState,
)
from real_work_gateway import BusinessPlatformRealWorkGateway
from real_work_runtime import CeStepGate, CeStopBarrier, RunContext, timeline_for_run
from routers.conversation_execution import ConstitutionalDecision
from session_executor import C041ToolAuthorizationError, SessionExecutor
from skill_resolver import SessionSkillContext
from spend_client import ChainSpendHook, WbeSpendClient


class Sink:
    def __init__(self) -> None:
        self.events: list[TimelineEvent] = []

    async def deliver(self, event: TimelineEvent) -> None:
        self.events.append(event)


class Gate:
    async def validate(self, action_type: str, parameters: dict[str, str]) -> None:
        return None


class Barrier:
    def __init__(self, *answers: BarrierDecision | Exception) -> None:
        self._answers = list(answers)
        self.asked = 0

    async def decide(self, tenant_id, relationship_id) -> BarrierDecision:
        self.asked += 1
        answer = self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


class Spend:
    def __init__(self, *, refuse: bool = False, fail_charge: bool = False) -> None:
        self.refuse, self.fail_charge = refuse, fail_charge
        self.calls: list[str] = []

    async def reserve(self, item: WorkItem) -> None:
        self.calls.append("reserve")
        if self.refuse:
            raise SpendRefused("over the ceiling")

    async def charge(self, item: WorkItem, result: ProviderResult) -> None:
        self.calls.append("charge")
        if self.fail_charge:
            raise SpendRefused("billing engine unreachable")


def _item(*, paise: int | None = None) -> WorkItem:
    return WorkItem(
        tenant_id=uuid4(),
        relationship_id=uuid4(),
        work_item_id=uuid4(),
        work_item_type="SOCIAL_POST",
        binding=ArtifactBinding(uuid4(), "a" * 64, "LOCKED", uuid4(), uuid4()),
        spend_paise=paise,
    )


class Provider:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> ProviderResult:
        self.calls += 1
        return ProviderResult(ProviderStatus.CONFIRMED, "page_1_post_2", ("provider:ok",))


def _timeline(barrier=None, spend=None) -> tuple[ExecutionTimeline, Sink]:
    sink = Sink()
    return ExecutionTimeline(sink=sink, gate=Gate(), barrier=barrier, spend=spend), sink


@pytest.mark.asyncio
async def test_a_fresh_replica_obeys_a_stop_recorded_elsewhere_because_the_barrier_is_durable() -> None:
    provider = Provider()
    replica, sink = _timeline(Barrier(BarrierDecision.STOPPED))

    final = await replica.dispatch(_item(), provider)

    assert provider.calls == 0
    assert final.state is WorkItemState.HALTED and final.reason_code is ReasonCode.EMERGENCY_STOP
    assert [event.state for event in sink.events] == [WorkItemState.HALTED]


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [RuntimeError("ce down"), BarrierDecision.BLOCKED])
async def test_a_barrier_that_cannot_confirm_the_step_refuses_it_and_never_calls_the_provider(answer) -> None:
    provider = Provider()
    timeline, sink = _timeline(Barrier(answer))

    with pytest.raises(StepBlocked):
        await timeline.dispatch(_item(), provider)

    assert provider.calls == 0
    assert sink.events[-1].state is WorkItemState.FAILED and sink.events[-1].reason_code is ReasonCode.POLICY_BLOCKED


@pytest.mark.asyncio
async def test_a_stop_that_lands_while_the_provider_runs_makes_the_late_result_halted_evidence() -> None:
    timeline, sink = _timeline(Barrier(BarrierDecision.CLEAR, BarrierDecision.CLEAR, BarrierDecision.STOPPED))

    final = await timeline.dispatch(_item(), Provider())

    assert final.state is WorkItemState.HALTED
    assert "late-result:confirmed" in final.evidence_refs


@pytest.mark.asyncio
async def test_a_barrier_that_goes_quiet_after_the_provider_acted_does_not_turn_real_work_into_a_failure() -> None:
    timeline, _ = _timeline(Barrier(BarrierDecision.CLEAR, BarrierDecision.CLEAR, RuntimeError("ce down")))

    final = await timeline.dispatch(_item(), Provider())

    assert final.state is WorkItemState.COMPLETED


@pytest.mark.asyncio
async def test_reconcile_after_a_stop_is_halted_never_completed() -> None:
    timeline, _ = _timeline(Barrier(BarrierDecision.STOPPED))

    final = await timeline.reconcile(_item(), ProviderResult(ProviderStatus.CONFIRMED, "page_1_post_2"))

    assert final.state is WorkItemState.HALTED


@pytest.mark.asyncio
async def test_spend_is_reserved_before_the_call_and_charged_only_with_the_providers_proof() -> None:
    spend = Spend()
    timeline, sink = _timeline(spend=spend)

    final = await timeline.dispatch(_item(paise=500), Provider())

    assert spend.calls == ["reserve", "charge"]
    assert final.state is WorkItemState.COMPLETED and "spend-charge-pending" not in final.evidence_refs


@pytest.mark.asyncio
async def test_a_refused_reservation_stops_the_step_before_the_provider() -> None:
    provider = Provider()
    timeline, sink = _timeline(spend=Spend(refuse=True))

    with pytest.raises(SpendRefused):
        await timeline.dispatch(_item(paise=500), provider)

    assert provider.calls == 0
    assert sink.events[-1].reason_code is ReasonCode.POLICY_BLOCKED


@pytest.mark.asyncio
async def test_a_step_that_costs_money_without_a_spend_chain_does_not_run() -> None:
    provider = Provider()
    timeline, _ = _timeline()

    with pytest.raises(SpendRefused):
        await timeline.dispatch(_item(paise=500), provider)

    assert provider.calls == 0


@pytest.mark.asyncio
async def test_a_charge_that_fails_after_the_provider_acted_is_recorded_not_hidden() -> None:
    timeline, _ = _timeline(spend=Spend(fail_charge=True))

    final = await timeline.dispatch(_item(paise=500), Provider())

    assert final.state is WorkItemState.COMPLETED and "spend-charge-pending" in final.evidence_refs


class Validator:
    def __init__(self, decision: ConstitutionalDecision) -> None:
        self.decision = decision
        self.calls: list[dict] = []

    async def validate_action(self, **kwargs) -> ConstitutionalDecision:
        self.calls.append(kwargs)
        return self.decision


def _run() -> RunContext:
    return RunContext("contract-1", uuid4(), 3, "actor-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ConstitutionalDecision.ALLOW, BarrierDecision.CLEAR),
        (ConstitutionalDecision.STOPPED, BarrierDecision.STOPPED),
        (ConstitutionalDecision.DENY, BarrierDecision.BLOCKED),
        (ConstitutionalDecision.STALE, BarrierDecision.BLOCKED),
    ],
)
async def test_the_ce_barrier_maps_the_engines_answer(decision, expected) -> None:
    run = _run()
    barrier = CeStopBarrier(Validator(decision), run)

    assert await barrier.decide(run.tenant_id, uuid4()) is expected


@pytest.mark.asyncio
async def test_the_ce_barrier_refuses_another_tenants_step_without_asking_the_engine() -> None:
    validator = Validator(ConstitutionalDecision.ALLOW)

    assert await CeStopBarrier(validator, _run()).decide(uuid4(), uuid4()) is BarrierDecision.BLOCKED
    assert validator.calls == []


@pytest.mark.asyncio
async def test_the_ce_step_gate_passes_the_binding_and_denies_anything_but_allow() -> None:
    run = _run()
    allow = Validator(ConstitutionalDecision.ALLOW)
    await CeStepGate(allow, run).validate("REAL_WORK_EXECUTE_STEP", {"artifactId": "x"})
    assert allow.calls[0]["parameters"] == {"artifactId": "x"} and allow.calls[0]["contract_id"] == "contract-1"

    with pytest.raises(PermissionError):
        await CeStepGate(Validator(ConstitutionalDecision.STOPPED), run).validate("REAL_WORK_EXECUTE_STEP", {})


@pytest.mark.asyncio
async def test_a_run_timeline_is_wired_to_the_engine_for_both_gate_and_barrier() -> None:
    run = _run()
    validator = Validator(ConstitutionalDecision.ALLOW)
    sink = Sink()
    item = WorkItem(
        run.tenant_id,
        uuid4(),
        uuid4(),
        "SOCIAL_POST",
        ArtifactBinding(uuid4(), "a" * 64, "LOCKED", uuid4(), uuid4()),
    )

    final = await timeline_for_run(validator, sink, run).dispatch(item, Provider())

    assert final.state is WorkItemState.COMPLETED
    assert {call["action_type"] for call in validator.calls} == {"CONVERSATION_EXECUTION", "REAL_WORK_EXECUTE_STEP"}


class Dispatcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def dispatch(self, *, tool_name, params, dcm_category, skill_id):
        self.calls.append(tool_name)
        return {"id": "page_1_post_2"}


def _to_result(raw) -> ProviderResult:
    return ProviderResult(ProviderStatus.CONFIRMED, raw["id"])


@pytest.mark.asyncio
async def test_the_session_executor_runs_a_consequential_tool_only_through_the_stream() -> None:
    dispatcher, (timeline, sink) = Dispatcher(), _timeline()
    executor = SessionExecutor(
        SessionSkillContext(authorized_tools={"post_content"}), dispatcher=dispatcher, timeline=timeline
    )

    final = await executor.execute_work_item("post_content", {}, _item(), _to_result)

    assert dispatcher.calls == ["post_content"]
    assert final.provider_reference == "page_1_post_2"
    assert [event.state for event in sink.events][-1] is WorkItemState.COMPLETED


@pytest.mark.asyncio
async def test_the_session_executor_keeps_its_pre_flight_gates_and_refuses_without_a_stream() -> None:
    dispatcher = Dispatcher()
    context = SessionSkillContext(authorized_tools={"post_content"})

    with pytest.raises(C041ToolAuthorizationError):
        await SessionExecutor(context, dispatcher=dispatcher, timeline=_timeline()[0]).execute_work_item(
            "delete_page", {}, _item(), _to_result
        )
    with pytest.raises(RuntimeError, match="Execution stream"):
        await SessionExecutor(context, dispatcher=dispatcher).execute_work_item("post_content", {}, _item(), _to_result)
    assert dispatcher.calls == []


@pytest.mark.asyncio
async def test_a_missing_dispatcher_is_an_unknown_outcome_not_a_silent_success() -> None:
    timeline, sink = _timeline()
    executor = SessionExecutor(SessionSkillContext(authorized_tools={"post_content"}), timeline=timeline)

    final = await executor.execute_work_item("post_content", {}, _item(), _to_result)

    assert final.reason_code is ReasonCode.UNKNOWN_OUTCOME


@pytest.mark.asyncio
async def test_bp_holding_an_unknown_outcome_is_the_durable_blind_retry_refusal() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(409, json={"code": "REAL_WORK_BLIND_RETRY"}))
    )
    gateway = BusinessPlatformRealWorkGateway(
        "http://bp", client, "spiffe://demo/workload/professional-runtime", "key-1", "urn:bp", ec.generate_private_key(ec.SECP256R1())
    )
    provider = Provider()
    timeline = ExecutionTimeline(sink=gateway, gate=Gate())

    with pytest.raises(BlindRetryRefused):
        await timeline.dispatch(_item(), provider)

    assert provider.calls == 0


def _spend_client(handler) -> WbeSpendClient:
    return WbeSpendClient(
        "http://wbe/",
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        "spiffe://demo/workload/professional-runtime",
        "key-1",
        "urn:wbe",
        ec.generate_private_key(ec.SECP256R1()),
    )


@pytest.mark.asyncio
async def test_the_spend_client_posts_a_signed_idempotent_reserve_and_charge() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    client, item, authorization = _spend_client(handler), _item(paise=500), uuid4()
    hook = ChainSpendHook(client, lambda _: authorization, "social_post", "demo", lambda *_: uuid4())

    await hook.reserve(item)
    await hook.reserve(item)
    await hook.charge(item, ProviderResult(ProviderStatus.CONFIRMED, "page_1_post_2"))

    assert [str(request.url) for request in seen] == [
        "http://wbe/internal/v1/real-work/spend/reserve",
        "http://wbe/internal/v1/real-work/spend/reserve",
        "http://wbe/internal/v1/real-work/spend/charge",
    ]
    assert seen[0].headers["Idempotency-Key"] == seen[1].headers["Idempotency-Key"] != seen[2].headers["Idempotency-Key"]
    assert json.loads(seen[0].content)["paise"] == 500
    assert json.loads(seen[2].content)["verified"] is True
    assert seen[0].headers["Authorization"].startswith("Bearer ")


@pytest.mark.asyncio
async def test_the_spend_client_refuses_instead_of_assuming_money_moved() -> None:
    refused = _spend_client(lambda request: httpx.Response(409, json={"code": "SPEND_CEILING"}))
    item = _item(paise=500)
    hook = ChainSpendHook(refused, lambda _: uuid4(), "social_post", "demo", lambda *_: uuid4())

    with pytest.raises(SpendRefused, match="409"):
        await hook.reserve(item)

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    down = ChainSpendHook(_spend_client(unreachable), lambda _: uuid4(), "social_post", "demo", lambda *_: uuid4())
    with pytest.raises(SpendRefused, match="unreachable"):
        await down.reserve(item)


@pytest.mark.asyncio
async def test_the_spend_hook_will_not_reserve_or_charge_without_authorization_or_evidence() -> None:
    client = _spend_client(lambda request: httpx.Response(200, json={}))
    item = _item(paise=500)

    with pytest.raises(SpendRefused):
        await ChainSpendHook(client, lambda _: None, "c", "demo", lambda *_: uuid4()).reserve(item)
    with pytest.raises(SpendRefused):
        await ChainSpendHook(client, lambda _: uuid4(), "c", "demo", lambda *_: None).charge(
            item, ProviderResult(ProviderStatus.CONFIRMED, "page_1_post_2")
        )
    with pytest.raises(SpendRefused):
        await ChainSpendHook(client, lambda _: uuid4(), "c", "demo", lambda *_: uuid4()).charge(
            item, ProviderResult(ProviderStatus.ACCEPTED, None)
        )
