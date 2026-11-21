# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-01, C7-02
# Constitutional basis: C-048, C-049, C-059, C-063
"""Scripted funding and pricing scenario packs for the simulated-customer harness.

A pack is a YAML file of scenarios; each step names the actor, channel, relationship state and purpose, the call to make
and what must come back: the account class read from the test-only ``X-Spend-Account-Class`` response header, the wallet
movement and the customer-visible outcome (funding) or the status, outcome code and fields (pricing). The runner talks to
a target over HTTP and defaults to the loopback fakes; it never targets a non-loopback host unless explicitly allowed.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from visitor_simulation.funding_fake import CLASS_HEADER, ROLES_HEADER, SIMULATOR_ROLE, FundingFake
from visitor_simulation.pricing_fake import PricingFake
from visitor_simulation.scenario_server import ScenarioServer

SCENARIOS_DIR = Path(__file__).with_name("scenarios")
PACK_SCHEMA = "wc136-scenario-pack/1.0"
REPORT_SCHEMA = "wc136-scenario-report/1.0"
PACKS = ("funding", "pricing")
CHANNELS = ("WHATSAPP", "WEB", "SIMULATION")
RELATIONSHIP_STATES = ("NONE", "TRIAL", "HIRED", "ENDED")
PURPOSES = ("AGENT_WORK", "ONBOARDING", "PRESALES_OR_MARKETPLACE", "PLATFORM_SUPPORT", "SAFETY_FLOOR", "SIMULATION", "NONE")
MOVEMENT_ACCOUNTS = ("ACQUISITION", "SETUP_GRANT", "TRIAL", "SUBSCRIPTION", "PLATFORM_FLOOR", "SIMULATION")
ACCOUNT_CLASSES = (*MOVEMENT_ACCOUNTS, "NONE")
MOVEMENT_UNITS = ("PAISE", "MESSAGES", "UNITS")
FUNDING_ACTORS = ("VISITOR", "CUSTOMER", "BENEFICIARY", "OPERATOR", "SUPPORT", "PLATFORM", "FOUNDER")
PRICING_ACTORS = ("PRICING_ADMIN", "FOUNDER", "CUSTOMER", "SYSTEM")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
MISSING = object()


class ScenarioError(ValueError):
    """The scenario file is malformed or names something the harness does not know."""


class ScenarioTransportError(RuntimeError):
    """The target could not be reached; the run is aborted rather than failed."""


@dataclass(frozen=True)
class Step:
    id: str
    actor: str
    action: str
    params: dict[str, Any]
    expect: dict[str, Any]
    channel: str | None = None
    relationship_state: str | None = None
    purpose: str | None = None


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    source: str
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Pack:
    name: str
    seed: int
    scenarios: tuple[Scenario, ...]


def _mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioError(f"{where} must be a mapping")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where} must be a non-empty string")
    return value


def _choice(value: Any, allowed: tuple[str, ...], where: str) -> str:
    if value not in allowed:
        raise ScenarioError(f"{where} must be one of {', '.join(allowed)}")
    return str(value)


def _strict(data: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = sorted(required - data.keys())
    unknown = sorted(data.keys() - required - optional)
    if missing:
        raise ScenarioError(f"{where}: missing {', '.join(missing)}")
    if unknown:
        raise ScenarioError(f"{where}: unknown {', '.join(unknown)}")


def _integer(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(f"{where} must be an integer")
    return value


def _string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ScenarioError(f"{where} must be a list of non-empty strings")
    return value


def _check_fields(value: Any, where: str) -> None:
    fields = _mapping(value, where)
    if not fields:
        raise ScenarioError(f"{where} must not be empty")
    for path, wanted in fields.items():
        _text(path, f"{where} path")
        if isinstance(wanted, dict) and wanted not in ({"$absent": True}, {"$regex": wanted.get("$regex")}):
            raise ScenarioError(f"{where}.{path} may only use $absent: true or $regex")
        if isinstance(wanted, dict) and "$regex" in wanted:
            _text(wanted["$regex"], f"{where}.{path}.$regex")


def _check_expect(pack: str, raw: Any, where: str) -> dict[str, Any]:
    expect = _mapping(raw, where)
    if pack == "funding":
        _strict(expect, {"accountClass", "walletMovement", "customerVisible"}, {"status", "fields"}, where)
        _choice(expect["accountClass"], ACCOUNT_CLASSES, f"{where}.accountClass")
        movement = expect["walletMovement"]
        if movement != "NONE":
            movement = _mapping(movement, f"{where}.walletMovement")
            _strict(movement, {"account", "unit", "delta"}, set(), f"{where}.walletMovement")
            _choice(movement["account"], MOVEMENT_ACCOUNTS, f"{where}.walletMovement.account")
            _choice(movement["unit"], MOVEMENT_UNITS, f"{where}.walletMovement.unit")
            if _integer(movement["delta"], f"{where}.walletMovement.delta") == 0:
                raise ScenarioError(f"{where}.walletMovement.delta must not be zero; use NONE")
        visible = _mapping(expect["customerVisible"], f"{where}.customerVisible")
        _strict(visible, {"outcome"}, {"contains", "excludes", "silent"}, f"{where}.customerVisible")
        _text(visible["outcome"], f"{where}.customerVisible.outcome")
        for key in ("contains", "excludes"):
            if key in visible:
                _string_list(visible[key], f"{where}.customerVisible.{key}")
        if "silent" in visible and not isinstance(visible["silent"], bool):
            raise ScenarioError(f"{where}.customerVisible.silent must be true or false")
    else:
        _strict(expect, {"outcome"}, {"status", "fields"}, where)
        _text(expect["outcome"], f"{where}.outcome")
    if "status" in expect and not 100 <= _integer(expect["status"], f"{where}.status") <= 599:
        raise ScenarioError(f"{where}.status must be an HTTP status")
    if "fields" in expect:
        _check_fields(expect["fields"], f"{where}.fields")
    return expect


def _parse_step(pack: str, raw: Any, where: str) -> Step:
    data = _mapping(raw, where)
    funding_only = {"channel", "relationshipState", "purpose"}
    _strict(data, {"id", "actor", "action", "expect"}, {"params"} | funding_only, where)
    step_id = _text(data["id"], f"{where}.id")
    where = f"{where} ({step_id})"
    if pack == "funding":
        _strict(data, {"id", "actor", "action", "expect", *funding_only}, {"params"}, where)
        actor = _choice(data["actor"], FUNDING_ACTORS, f"{where}.actor")
        action = _choice(data["action"], FundingFake.action_names(), f"{where}.action")
        channel = _choice(data["channel"], CHANNELS, f"{where}.channel")
        state = _choice(data["relationshipState"], RELATIONSHIP_STATES, f"{where}.relationshipState")
        purpose = _choice(data["purpose"], PURPOSES, f"{where}.purpose")
    else:
        if funding_only & data.keys():
            raise ScenarioError(f"{where}: channel, relationshipState and purpose belong to funding steps")
        actor = _choice(data["actor"], PRICING_ACTORS, f"{where}.actor")
        action = _choice(data["action"], PricingFake.action_names(), f"{where}.action")
        channel = state = purpose = None
    params = _mapping(data.get("params", {}), f"{where}.params")
    return Step(step_id, actor, action, params, _check_expect(pack, data["expect"], f"{where}.expect"), channel, state, purpose)


def parse_pack(raw: Any) -> Pack:
    root = _mapping(raw, "scenario pack")
    _strict(root, {"schema", "pack", "seed", "scenarios"}, set(), "scenario pack")
    if root["schema"] != PACK_SCHEMA:
        raise ScenarioError(f"schema must be {PACK_SCHEMA}")
    name = _choice(root["pack"], PACKS, "pack")
    seed = _integer(root["seed"], "seed")
    entries = root["scenarios"]
    if not isinstance(entries, list) or not entries:
        raise ScenarioError("scenarios must be a non-empty list")
    scenarios: list[Scenario] = []
    for index, entry in enumerate(entries):
        where = f"scenarios[{index}]"
        data = _mapping(entry, where)
        _strict(data, {"id", "title", "source", "steps"}, set(), where)
        scenario_id = _text(data["id"], f"{where}.id")
        if any(s.id == scenario_id for s in scenarios):
            raise ScenarioError(f"duplicate scenario id {scenario_id}")
        steps_raw = data["steps"]
        if not isinstance(steps_raw, list) or not steps_raw:
            raise ScenarioError(f"scenario {scenario_id}: steps must be a non-empty list")
        steps = tuple(_parse_step(name, step, f"scenario {scenario_id} step {i + 1}") for i, step in enumerate(steps_raw))
        if len({step.id for step in steps}) != len(steps):
            raise ScenarioError(f"scenario {scenario_id}: duplicate step id")
        title, source = _text(data["title"], f"{where}.title"), _text(data["source"], f"{where}.source")
        scenarios.append(Scenario(scenario_id, title, source, steps))
    return Pack(name, seed, tuple(scenarios))


def pack_path(name: str) -> Path:
    """``scenarios/<name>.yaml`` when it exists, otherwise ``<name>_scenarios.yaml`` beside this module."""
    pack = _choice(name, PACKS, "pack")
    nested = SCENARIOS_DIR / f"{pack}.yaml"
    return nested if nested.exists() else SCENARIOS_DIR.parent / f"{pack}_scenarios.yaml"


def load_pack(path: str | Path) -> Pack:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"cannot read scenario pack {path}: {type(exc).__name__}") from exc
    return parse_pack(raw)


def start_fake(pack_name: str, *, simulator_headers_enabled: bool = True) -> ScenarioServer:
    """Starts the loopback fake for a pack; the caller stops it (it is a context manager)."""
    if pack_name == "funding":
        return ScenarioServer(FundingFake(simulator_headers_enabled=simulator_headers_enabled).handle).start()
    return ScenarioServer(PricingFake().handle).start()


def is_loopback(base_url: str) -> bool:
    return urllib.parse.urlsplit(base_url).hostname in LOOPBACK_HOSTS


def _post(
    base_url: str, path: str, body: dict[str, Any], headers: dict[str, str], timeout: float
) -> tuple[int, dict[str, str], Any]:
    request = urllib.request.Request(  # noqa: S310 - scheme is checked by the caller; loopback by default
        base_url.rstrip("/") + path,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status, raw, received = response.status, response.read(), response.headers
    except urllib.error.HTTPError as exc:
        status, raw, received = exc.code, exc.read(), exc.headers
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ScenarioTransportError(f"scenario target unreachable: {type(exc).__name__}") from exc
    try:
        payload: Any = json.loads(raw) if raw else {}
    except ValueError:
        payload = {}
    return status, {name.lower(): value for name, value in received.items()}, payload


def _lookup(body: Any, path: str) -> Any:
    current = body
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return MISSING
    return current


def _same(actual: Any, wanted: Any) -> bool:
    return type(actual) is type(wanted) and actual == wanted


def _check_fields_against(fields: dict[str, Any], body: Any) -> list[str]:
    failures = []
    for path, wanted in fields.items():
        actual = _lookup(body, path)
        if isinstance(wanted, dict) and wanted.get("$absent"):
            if actual is not MISSING:
                failures.append(f"{path}: expected absent")
        elif isinstance(wanted, dict):
            text = str(actual) if isinstance(actual, int) and not isinstance(actual, bool) else actual
            if not isinstance(text, str) or not re.fullmatch(wanted["$regex"], text):
                failures.append(f"{path}: {actual!r} does not match {wanted['$regex']!r}")
        elif actual is MISSING or not _same(actual, wanted):
            failures.append(f"{path}: expected {wanted!r}, got {None if actual is MISSING else actual!r}")
    return failures


def check_step(pack: str, step: Step, status: int, headers: dict[str, str], body: Any) -> list[str]:
    """Compares one response with the step's expectation and returns the failures (empty when it passed)."""
    body = body if isinstance(body, dict) else {}
    expect = step.expect
    failures = []
    if status != expect.get("status", 200):
        failures.append(f"status: expected {expect.get('status', 200)}, got {status}")
    if pack == "pricing":
        if body.get("outcome") != expect["outcome"]:
            failures.append(f"outcome: expected {expect['outcome']}, got {body.get('outcome')}")
    else:
        failures.extend(_check_funding(expect, headers, body))
    return failures + _check_fields_against(expect.get("fields", {}), body)


def _check_funding(expect: dict[str, Any], headers: dict[str, str], body: dict[str, Any]) -> list[str]:
    failures = []
    actual_class = headers.get(CLASS_HEADER.lower())
    if expect["accountClass"] == "NONE":
        if actual_class is not None:
            failures.append(f"accountClass: expected no {CLASS_HEADER} header, got {actual_class}")
    elif actual_class != expect["accountClass"]:
        failures.append(f"accountClass: expected {expect['accountClass']}, got {actual_class}")
    movement = body.get("movement")
    if expect["walletMovement"] == "NONE":
        if movement is not None:
            failures.append(f"walletMovement: expected none, got {movement}")
    elif movement != expect["walletMovement"]:
        failures.append(f"walletMovement: expected {expect['walletMovement']}, got {movement}")
    visible = expect["customerVisible"]
    message = str(body.get("message", ""))
    if body.get("outcome") != visible["outcome"]:
        failures.append(f"customerVisible.outcome: expected {visible['outcome']}, got {body.get('outcome')}")
    lowered = message.lower()
    wanted_words = visible.get("contains", [])
    failures.extend(f"customerVisible.contains: {text!r} missing" for text in wanted_words if text.lower() not in lowered)
    unwanted_words = visible.get("excludes", [])
    failures.extend(f"customerVisible.excludes: {text!r} present" for text in unwanted_words if text.lower() in lowered)
    if "silent" in visible and (message == "") != visible["silent"]:
        shown = "empty" if message == "" else "present"
        failures.append(f"customerVisible.silent: expected {visible['silent']}, message was {shown}")
    return failures


def _step_body(step: Step) -> dict[str, Any]:
    body: dict[str, Any] = {"action": step.action, "actor": step.actor, "params": step.params}
    if step.channel is not None:
        body.update(channel=step.channel, relationshipState=step.relationship_state, purpose=step.purpose)
    return body


def run_pack(
    pack: Pack,
    base_url: str,
    *,
    roles: tuple[str, ...] = (SIMULATOR_ROLE,),
    timeout: float = 10.0,
    seed: int | None = None,
    only: tuple[str, ...] = (),
    target_label: str = "target",
) -> dict[str, Any]:
    """Runs the pack against ``base_url``; every scenario starts from a reset target and a deterministic seed."""
    unknown = sorted(set(only) - {s.id for s in pack.scenarios})
    if unknown:
        raise ScenarioError(f"unknown scenario ids: {', '.join(unknown)}")
    base_seed = pack.seed if seed is None else seed
    headers = {ROLES_HEADER: ",".join(roles)} if roles else {}
    results = []
    for index, scenario in enumerate(pack.scenarios):
        if only and scenario.id not in only:
            continue
        scenario_seed = base_seed + index
        _post(base_url, "/scenario/reset", {"seed": scenario_seed}, headers, timeout)
        step_results = []
        for step in scenario.steps:
            status, received, body = _post(base_url, "/scenario/step", _step_body(step), headers, timeout)
            failures = check_step(pack.name, step, status, received, body)
            step_results.append({"id": step.id, "passed": not failures, "failures": failures})
            if failures:
                break
        results.append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "source": scenario.source,
                "seed": scenario_seed,
                "passed": all(result["passed"] for result in step_results) and len(step_results) == len(scenario.steps),
                "stepsRun": len(step_results),
                "stepsTotal": len(scenario.steps),
                "steps": step_results,
            }
        )
    failed = [result for result in results if not result["passed"]]
    return {
        "schema": REPORT_SCHEMA,
        "pack": pack.name,
        "seed": base_seed,
        "target": target_label,
        "roles": list(roles),
        "scenarios": results,
        "summary": {
            "scenarios": len(results),
            "scenariosPassed": len(results) - len(failed),
            "scenariosFailed": len(failed),
            "steps": sum(result["stepsRun"] for result in results),
            "stepsFailed": sum(1 for result in results for step in result["steps"] if not step["passed"]),
            "passed": bool(results) and not failed,
        },
    }


def write_report(report: dict[str, Any], output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"scenarios-{report['pack']}-report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
