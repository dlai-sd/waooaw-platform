# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-04, C1-05
# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Runs every persona K times against a visitor API base URL and aggregates the judged results."""

import json
import logging
import statistics
import time
import urllib.parse
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from visitor_simulation.client import (
    VisitorApiError,
    VisitorClient,
    VisitorTimeoutError,
    VisitorTransportError,
    VisitorUnauthorizedError,
)
from visitor_simulation.customer import (
    CostCapExceeded,
    CustomerSimulator,
    HttpModelClient,
    ModelClient,
    RunBudget,
    ScriptedModel,
    stable_index,
)
from visitor_simulation.judge import CRITERIA, POLICY_VIOLATIONS, Judge, JudgeResult, load_rubric
from visitor_simulation.models import Conversation, TurnRecord
from visitor_simulation.personas import Persona, load_default_k, select_personas
from visitor_simulation.policy import ProtocolPolicy, load_protocol_policy

logger = logging.getLogger(__name__)

INJECTIONS = ("media", "stop-mid", "slow", "unknown-language")
MODELS = ("scripted", "none", "http")
REPORT_SCHEMA = "visitor-simulation-report/1.1"
LEGACY_REPORT_SCHEMA = "visitor-simulation-report/1"
COMPATIBLE_REPORT_SCHEMAS = (LEGACY_REPORT_SCHEMA, REPORT_SCHEMA)
SLOW_TURN = 3
TRIAL_SEED_STRIDE = 1_000_000_000
DEFAULT_OUTPUT = "test-results/visitor_simulation"
KEY_NAMESPACE = uuid.UUID("5b0f2f0e-3a5b-4f7e-9d1c-2b6f6a0d7c11")


def parse_inject(values: list[str] | None) -> tuple[str, ...]:
    """Accepts repeated and comma-separated values; rejects unknown injection names."""
    names: list[str] = []
    for value in values or []:
        names.extend(part.strip() for part in value.split(",") if part.strip())
    unknown = [n for n in names if n not in INJECTIONS]
    if unknown:
        raise ValueError(f"unknown injection(s): {', '.join(unknown)}; choose from {', '.join(INJECTIONS)}")
    return tuple(dict.fromkeys(names))


@dataclass
class RunConfig:
    base_url: str
    secret: str = field(repr=False)
    runs: int = 20
    seed: int = 1
    personas: list[Persona] = field(default_factory=lambda: select_personas(None))
    inject: tuple[str, ...] = ()
    model: str = "scripted"
    max_turns: int = 30
    max_model_calls: int = 5000
    timeout: float = 10.0
    judge_repeats: int = 1
    forbidden_claims: tuple[str, ...] = ()
    k: int = field(default_factory=load_default_k)
    content_path: str | None = None


@dataclass
class SuiteResult:
    items: list[tuple[Conversation, JudgeResult]]
    report: dict[str, Any]


def _model_for(kind: str, seed: int) -> ModelClient | None:
    if kind == "scripted":
        return ScriptedModel(seed)
    if kind == "http":
        return HttpModelClient()
    return None


def run_conversation(
    client: VisitorClient,
    persona: Persona,
    *,
    mode: str,
    seed: int,
    subject_key: str,
    inject: tuple[str, ...] = (),
    budget: RunBudget | None = None,
    model: ModelClient | None = None,
) -> Conversation:
    budget = budget or RunBudget()
    budget.start_conversation()
    sim = CustomerSimulator(persona, mode=mode, seed=seed, model=model, budget=budget, inject=inject)
    conv = Conversation(
        persona_id=persona.id,
        mode=mode,
        seed=seed,
        subject_key=subject_key,
        injections=inject,
        goal=replace(persona.goal, patience=sim.patience),
        business_terms=persona.business_terms,
    )
    session = client.open_session(subject_key)
    conv.session_id = session.session_id
    conv.resumed = not session.created
    conv.states_visited.append(session.state)
    conv.turns.append(
        TurnRecord(
            index=0, visitor_turn=0, visitor_kind="OPEN", reply=session.reply, state=session.state, outcome=session.outcome
        )
    )
    last_reply = session.reply
    if last_reply is None:
        conv.ended_reason = "no_opening_reply"
    visitor_turn = 0
    while last_reply is not None:
        action = sim.next_action(last_reply)
        if action.kind == "END":
            conv.ended_reason = action.reason
            break
        index = len(conv.turns)
        if action.kind == "TAP":
            recorded = client.tap_handoff(action.reference)
            sim.record_tap(recorded)
            conv.turns.append(
                TurnRecord(
                    index=index,
                    visitor_turn=visitor_turn,
                    visitor_kind="TAP",
                    state=conv.states_visited[-1],
                    outcome=conv.turns[-1].outcome,
                    note="tap",
                    tap_recorded=recorded,
                )
            )
            continue
        visitor_turn += 1
        key = str(uuid.uuid5(KEY_NAMESPACE, f"{subject_key}:{visitor_turn}"))
        if "slow" in inject and visitor_turn == SLOW_TURN:
            client.drop_next_response()
        started = time.monotonic()
        try:
            turn = _send_with_replay(client, conv, session.session_id, action.kind, action.text, action.choice_id, key)
        except (VisitorTransportError, VisitorApiError) as exc:
            if isinstance(exc, VisitorUnauthorizedError):
                raise
            conv.ended_reason = f"error:{type(exc).__name__}"
            break
        latency = (time.monotonic() - started) * 1000
        conv.turns.append(
            TurnRecord(
                index=index,
                visitor_turn=visitor_turn,
                visitor_kind=action.kind,
                visitor_text=action.text,
                choice_id=action.choice_id,
                reply=turn.reply,
                state=turn.state,
                outcome=turn.outcome,
                latency_ms=latency,
                note=action.note,
            )
        )
        conv.states_visited.append(turn.state)
        last_reply = turn.reply
    _finish(client, conv, sim)
    return conv


def _send_with_replay(
    client: VisitorClient, conv: Conversation, session_id: str, kind: str, text: str, choice_id: str, key: str
) -> Any:
    """Send once; after a client-side timeout, retry with the same Idempotency-Key so the server replays its reply."""
    for attempt in range(2):
        try:
            if kind == "CHOICE":
                return client.send_message(session_id, choice_id=choice_id, idempotency_key=key)
            return client.send_message(session_id, text=text, idempotency_key=key)
        except VisitorTimeoutError:
            conv.timeouts += 1
            if attempt == 1:
                raise
    raise VisitorTimeoutError("unreachable")


def _finish(client: VisitorClient, conv: Conversation, sim: CustomerSimulator) -> None:
    try:
        final = client.get_session(conv.session_id)
        conv.final_state, conv.final_outcome, conv.captured = final.state, final.outcome, final.captured
        page = client.list_messages(conv.session_id, limit=100)
        conv.server_transcript_items = len(page.items)
    except (VisitorTransportError, VisitorApiError) as exc:
        logger.warning("could not read final session state: %s", type(exc).__name__)
        last = conv.turns[-1]
        conv.final_state, conv.final_outcome = last.state, last.outcome
    conv.goal = replace(conv.goal, patience=sim.patience)
    conv.tapped = sim.tapped
    conv.interest_expressed = sim.interest_expressed
    conv.stop_sent = sim.stop_sent


def run_suite(
    config: RunConfig,
    *,
    sleep: Callable[[float], None] = time.sleep,
    judge: Judge | None = None,
) -> SuiteResult:
    if config.k < 1:
        raise ValueError("k must be at least 1")
    if judge is None:
        rubric = load_rubric(policy=load_protocol_policy(config.content_path))
        judge = Judge(rubric=rubric, repeats=config.judge_repeats, extra_forbidden_claims=config.forbidden_claims)
    client = VisitorClient(config.base_url, config.secret, timeout=config.timeout, sleep=sleep)
    budget = RunBudget(
        max_model_calls=config.max_model_calls,
        max_total_turns=config.runs * config.k * len(config.personas) * config.max_turns,
        max_turns_per_conversation=config.max_turns,
    )
    items: list[tuple[Conversation, JudgeResult]] = []
    cap_exceeded = ""
    for p_index, persona in enumerate(config.personas):
        for run in range(config.runs):
            run_seed = config.seed * 1_000_000 + p_index * 1_000 + run
            mode = persona.modes[stable_index(run_seed, "mode", len(persona.modes))]
            for trial in range(config.k):
                trial_seed = run_seed + trial * TRIAL_SEED_STRIDE
                subject_key = f"{persona.subject_prefix}-{config.seed:03d}-{run:03d}"
                if trial:
                    subject_key = f"{subject_key}-k{trial:02d}"
                try:
                    conv = run_conversation(
                        client,
                        persona,
                        mode=mode,
                        seed=trial_seed,
                        subject_key=subject_key,
                        inject=config.inject,
                        budget=budget,
                        model=_model_for(config.model, trial_seed),
                    )
                except CostCapExceeded as exc:
                    cap_exceeded = str(exc)
                    logger.error("run stopped: %s", cap_exceeded)
                    break
                conv.seed_group, conv.trial = run_seed, trial
                items.append((conv, judge.evaluate(conv)))
            if cap_exceeded:
                break
        if cap_exceeded:
            break
    report = build_report(config, items, budget, client, cap_exceeded, judge.rubric.policy)
    return SuiteResult(items, report)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]


def reliability_stats(items: list[tuple[Conversation, JudgeResult]], k: int) -> dict[str, Any]:
    """pass^k: the fraction of seeds whose k independent runs all succeed, with the spread of that per-seed pass.

    A seed counts only when all k of its runs were completed (a run stopped by a cap leaves a partial seed out).
    ``runVariance`` is the standard deviation of the per-seed pass indicator, the noise estimate the compare gate uses.
    """
    by_seed: dict[int, list[bool]] = {}
    for conv, result in items:
        by_seed.setdefault(conv.seed_key, []).append(result.task.success)
    passes = [1.0 if all(runs) else 0.0 for runs in by_seed.values() if len(runs) == k]
    return {
        "k": k,
        "seeds": len(passes),
        "passK": round(statistics.fmean(passes), 4) if passes else None,
        "runVariance": round(statistics.pstdev(passes), 4) if passes else None,
    }


def _group_stats(items: list[tuple[Conversation, JudgeResult]], k: int = 1) -> dict[str, Any]:
    n = len(items)
    if n == 0:
        return {"runs": 0}
    successes = [1.0 if r.task.success else 0.0 for _, r in items]
    outcomes = {
        o: sum(1 for c, _ in items if c.final_outcome == o) for o in ("NONE", "LEAD", "INTENT", "FULL_SUCCESS", "OPT_OUT")
    }
    violations = {name: 0 for name in POLICY_VIOLATIONS}
    for _, result in items:
        for name, count in result.policy.counts().items():
            violations[name] += count
    first_value = [float(v) for c, _ in items if (v := c.first_value_turn) is not None]
    dropoff: dict[str, int] = {}
    for conv, result in items:
        if not result.task.success:
            dropoff[conv.final_state] = dropoff.get(conv.final_state, 0) + 1
    latencies = [t.latency_ms for c, _ in items for t in c.turns if t.latency_ms > 0]
    return {
        "runs": n,
        "failures": sum(1 for _, r in items if r.failed),
        "failureRate": round(sum(1 for _, r in items if r.failed) / n, 4),
        "taskSuccessRate": round(statistics.fmean(successes), 4),
        "taskSuccessStd": round(statistics.pstdev(successes), 4),
        "pass1": round(statistics.fmean(successes), 4),
        **reliability_stats(items, k),
        "outcomes": outcomes,
        "leadRate": round((outcomes["FULL_SUCCESS"] + outcomes["LEAD"]) / n, 4),
        "optOutRate": round(outcomes["OPT_OUT"] / n, 4),
        "policyViolations": violations,
        "policyViolationTotal": sum(violations.values()),
        "runsWithPolicyViolation": sum(1 for _, r in items if not r.policy.compliant),
        "criterionMeans": {c: round(statistics.fmean(r.criteria[c].score for _, r in items), 3) for c in CRITERIA},
        "meanScore": round(statistics.fmean(r.mean_score for _, r in items), 3),
        "turnsToFirstValue": {
            "reachedRate": round(len(first_value) / n, 4),
            "mean": round(statistics.fmean(first_value), 3) if first_value else None,
            "median": statistics.median(first_value) if first_value else None,
        },
        "stateDropoff": {state: {"count": c, "rate": round(c / n, 4)} for state, c in sorted(dropoff.items())},
        "latencyMs": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0.0,
            "p95": round(_p95(latencies), 2),
        },
    }


def build_report(
    config: RunConfig,
    items: list[tuple[Conversation, JudgeResult]],
    budget: RunBudget,
    client: VisitorClient,
    cap_exceeded: str = "",
    policy: ProtocolPolicy | None = None,
) -> dict[str, Any]:
    policy = policy or load_protocol_policy(config.content_path)
    parts = urllib.parse.urlsplit(config.base_url)
    hosts = sorted({urllib.parse.urlsplit(url).netloc for _, url in client.request_log})
    personas: dict[str, Any] = {}
    for persona in config.personas:
        subset = [(c, r) for c, r in items if c.persona_id == persona.id]
        stats = _group_stats(subset, config.k)
        stats["displayName"] = persona.display_name
        personas[persona.id] = stats
    return {
        "schema": REPORT_SCHEMA,
        "policyVersion": policy.version,
        "policyFingerprint": policy.fingerprint,
        "config": {
            "k": config.k,
            "policyVersion": policy.version,
            "baseUrl": f"{parts.scheme}://{parts.hostname}{f':{parts.port}' if parts.port else ''}{parts.path.rstrip('/')}",
            "runsPerPersona": config.runs,
            "seed": config.seed,
            "personas": [p.id for p in config.personas],
            "inject": list(config.inject),
            "model": config.model,
            "judgeRepeats": config.judge_repeats,
        },
        "budget": budget.usage(),
        "capExceeded": cap_exceeded,
        "hostsCalled": hosts,
        "resumedSessions": sum(1 for c, _ in items if c.resumed),
        "overall": _group_stats(items, config.k),
        "personas": personas,
    }


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def render_markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    config = report["config"]
    lines = [
        "# Simulated-customer evaluation",
        "",
        f"Base URL: `{config['baseUrl']}`; seed {config['seed']}; {config['runsPerPersona']} runs per persona; "
        f"injections: {', '.join(config['inject']) or 'none'}.",
        "",
    ]
    if report.get("capExceeded"):
        lines += [f"**Run stopped early: {report['capExceeded']}**", ""]
    if report.get("resumedSessions"):
        lines += [f"**Warning: {report['resumedSessions']} session(s) were resumed; use a fresh seed.**", ""]
    if not overall.get("runs"):
        return "\n".join([*lines, "No conversations completed.", ""])
    lines += [
        f"- Runs: {overall['runs']}; failure rate: {overall['failureRate']:.1%}; task success: {overall['taskSuccessRate']:.1%}",
        f"- Reliability pass^{overall.get('k', 1)}: {_percent(overall.get('passK'))} over {overall.get('seeds', 0)} seed(s)"
        f"; policy version {report.get('policyVersion', 'unknown')}",
        f"- Lead rate (full success + lead): {overall['leadRate']:.1%}; opt-out rate: {overall['optOutRate']:.1%}",
        f"- Policy violations: {overall['policyViolationTotal']} in {overall['runsWithPolicyViolation']} run(s)",
        f"- Turns to first value: mean {overall['turnsToFirstValue']['mean']}, reached in "
        f"{overall['turnsToFirstValue']['reachedRate']:.1%} of runs",
        "",
        "## Per persona",
        "",
        "| Persona | Runs | Failure rate | Task success | Pass^k | Lead rate | Opt-out | Violations | Mean score |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pid, stats in report["personas"].items():
        if not stats.get("runs"):
            continue
        lines.append(
            f"| {pid} | {stats['runs']} | {stats['failureRate']:.1%} | {stats['taskSuccessRate']:.1%} | "
            f"{_percent(stats.get('passK'))} | {stats['leadRate']:.1%} | {stats['optOutRate']:.1%} | "
            f"{stats['policyViolationTotal']} | {stats['meanScore']} |"
        )
    lines += ["", "## Criterion means (0-5)", "", "| Criterion | Mean |", "|---|---:|"]
    lines += [f"| {name} | {score} |" for name, score in overall["criterionMeans"].items()]
    lines += ["", "## Drop-off by state", ""]
    dropoff = overall["stateDropoff"]
    lines += [f"- {state}: {d['count']} ({d['rate']:.1%})" for state, d in dropoff.items()] or ["- none"]
    lines += ["", "## Policy violations", ""]
    lines += [f"- {name}: {count}" for name, count in overall["policyViolations"].items()]
    return "\n".join([*lines, ""])


def write_outputs(result: SuiteResult, output_dir: str | Path) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "report.json"
    summary_path = out / "summary.md"
    transcripts_path = out / "transcripts.json"
    report_path.write_text(json.dumps(result.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(render_markdown(result.report), encoding="utf-8")
    transcripts = [{**conv.to_json(), "judge": judged.to_json()} for conv, judged in result.items]
    transcripts_path.write_text(json.dumps(transcripts, indent=2) + "\n", encoding="utf-8")
    return [report_path, summary_path, transcripts_path]
