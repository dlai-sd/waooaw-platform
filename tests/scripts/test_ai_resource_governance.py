"""Author regression tests for WC-125 resource-governance contracts."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from ai_resource_governance import REQUIRED_ENTRY_POINTS, ROOT, main, validate_record, validate_repository


@pytest.fixture
def record():
    return {
        "execution_id": "fixture-attempt-1",
        "office": "INST-004",
        "work_contract": "WC-125",
        "task_class": "architecture",
        "route": "PAID",
        "model": "synthetic-qualified-model-v1",
        "selection_reason": "No authorized free route passes this task-class baseline",
        "qualification_ref": "synthetic-quality-baseline@sha256:abc",
        "escalation_reason": None,
        "limitations": [],
        "input_tokens": 100,
        "output_tokens": 50,
        "cached_tokens": 0,
        "cost": 0.01,
        "currency": "USD",
        "cost_basis": "METERED",
        "elapsed_seconds": 1,
        "repair_count": 0,
        "accepted": True,
        "validation_refs": ["synthetic-acceptance-evidence@sha256:def"],
        "escaped_defects": 0,
    }


def test_valid_record(record):
    assert validate_record(record) == []


@pytest.mark.parametrize("route", ["FREE", "PAID", "CLIENT_CONTROLLED", "DETERMINISTIC", "REUSE"])
def test_valid_routes(record, route):
    record["route"] = route
    if route in {"DETERMINISTIC", "REUSE"}:
        record["model"] = None
    if route == "CLIENT_CONTROLLED":
        record["limitations"] = ["Client controls routing"]
    assert validate_record(record) == []


@pytest.mark.parametrize(
    "field", ["input_tokens", "output_tokens", "cached_tokens", "cost", "elapsed_seconds", "escaped_defects"]
)
def test_unknown_measurements_require_disclosure(record, field):
    record[field] = None
    if field == "cost":
        record.update(cost_basis="UNKNOWN", currency=None)
    assert any("limitations" in error for error in validate_record(record))
    record["limitations"] = ["Measurement is unavailable"]
    assert validate_record(record) == []


@pytest.mark.parametrize("field", ["cost", "elapsed_seconds"])
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_values_rejected(record, field, value):
    record[field] = value
    assert validate_record(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_tokens", -1),
        ("output_tokens", True),
        ("cost", -1),
        ("elapsed_seconds", -1),
        ("office", "invented-office"),
        ("work_contract", ""),
        ("route", "cheap-ish"),
        ("selection_reason", " "),
        ("repair_count", -1),
        ("accepted", "yes"),
        ("currency", "rupees"),
    ],
)
def test_schema_rejects_invalid_fields(record, field, value):
    record[field] = value
    assert validate_record(record)


def test_required_and_unknown_fields_rejected(record):
    for field in tuple(record):
        incomplete = copy.deepcopy(record)
        del incomplete[field]
        assert validate_record(incomplete)
    record["unexpected"] = "do-not-log-this-sensitive-input"
    errors = validate_record(record)
    assert errors
    assert all("do-not-log-this-sensitive-input" not in error for error in errors)


@pytest.mark.parametrize("route", ["FREE", "PAID"])
def test_model_required_for_inference(record, route):
    record.update(route=route, model=None)
    assert any("model:" in error for error in validate_record(record))


def test_free_route_requires_qualification(record):
    record.update(route="FREE", qualification_ref=None, limitations=["Qualification missing"])
    assert any("qualification_ref:" in error for error in validate_record(record))


def test_unqualified_paid_route_disclosed_not_certified(record):
    record["qualification_ref"] = None
    assert validate_record(record)
    record["limitations"] = ["Qualification unavailable: no claim of full compliance"]
    assert validate_record(record) == []


@pytest.mark.parametrize("route", ["DETERMINISTIC", "REUSE"])
def test_deterministic_and_reuse_do_not_claim_model_calls(record, route):
    record["route"] = route
    assert any("model:" in error for error in validate_record(record))


def test_acceptance_requires_evidence_but_failed_attempts_are_valid(record):
    record["validation_refs"] = []
    assert any("validation_refs:" in error for error in validate_record(record))
    record["accepted"] = False
    assert validate_record(record) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"cost": None},
        {"cost": 0, "cost_basis": "UNKNOWN"},
        {"cost": 0, "currency": None},
        {"cost": None, "cost_basis": "UNKNOWN", "currency": "USD"},
    ],
)
def test_cost_is_not_silently_zero_or_unlabelled(record, changes):
    record.update(changes)
    record["limitations"] = ["Cost measurement unavailable"]
    assert any("cost:" in error for error in validate_record(record))


def test_repairs_require_escalation_after_one(record):
    record["repair_count"] = 2
    assert any("escalation_reason:" in error for error in validate_record(record))
    record["escalation_reason"] = "Escalated to stronger qualified route after failed repair"
    assert validate_record(record) == []


def test_client_controlled_disclosure(record):
    record["route"] = "CLIENT_CONTROLLED"
    assert any("limitations" in error for error in validate_record(record))


def test_live_repository_inherits_standard():
    assert validate_repository(ROOT) == []


@pytest.fixture
def repository(tmp_path):
    standard = tmp_path / "standards/AI-RESOURCE-GOVERNANCE.md"
    standard.parent.mkdir()
    standard.write_text("# Synthetic standard")
    paths = (*REQUIRED_ENTRY_POINTS, ".github/agent-context/office-fixture.md", "tests/AGENTS.md")
    import os

    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        target = Path(os.path.relpath(standard, path.parent)).as_posix()
        path.write_text(f"[Resource]({target})")
    return tmp_path


def test_repository_valid_and_cli(repository, capsys):
    assert main(["--repository", str(repository)]) == 0
    assert "not provider-routing or billing assurance" in capsys.readouterr().out


def test_repository_missing_standard_and_entry_point(repository):
    (repository / "standards/AI-RESOURCE-GOVERNANCE.md").unlink()
    (repository / REQUIRED_ENTRY_POINTS[0]).unlink()
    errors = validate_repository(repository)
    assert any("missing standard" in error for error in errors)
    assert any("missing entry point" in error for error in errors)


def test_repository_new_office_and_nested_agent_fail_closed(repository):
    office = repository / ".github/agent-context/office-new.md"
    office.write_text("# New office without inherited rules")
    nested = repository / "src/new-service/AGENTS.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Overrides without inherited rules")
    errors = validate_repository(repository)
    assert any("office-new.md" in error for error in errors)
    assert any("new-service/AGENTS.md" in error for error in errors)


def test_repository_future_custom_agents_and_web_guidance_cannot_omit_inheritance(repository):
    custom = repository / ".github/agents/new.agent.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("# Uninherited custom agent")
    web = repository / "web/AGENTS.md"
    web.parent.mkdir()
    web.write_text("# Uninherited web guidance")
    ignored = repository / "node_modules/vendor/AGENTS.md"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("# Third-party guidance is outside WAOOAW policy")
    errors = validate_repository(repository)
    assert any("new.agent.md" in error for error in errors)
    assert any("web/AGENTS.md" in error for error in errors)
    assert all("node_modules" not in error for error in errors)


def test_repository_wrong_link_and_missing_cards(repository):
    (repository / ".github/agent-context/office-fixture.md").unlink()
    (repository / REQUIRED_ENTRY_POINTS[0]).write_text("[Rules](missing/AI-RESOURCE-GOVERNANCE.md)")
    errors = validate_repository(repository)
    assert any("no office cards" in error for error in errors)
    assert any("invalid resource standard link" in error for error in errors)


def test_cli_record_success_failure_and_io(tmp_path, record, capsys):
    path = tmp_path / "execution.json"
    path.write_text(json.dumps(record))
    assert main(["--record", str(path)]) == 0
    record["input_tokens"] = -1
    path.write_text(json.dumps(record))
    assert main(["--record", str(path)]) == 1
    assert "BLOCKED" in capsys.readouterr().err
    path.write_text("{")
    assert main(["--record", str(path)]) == 1
    path.unlink()
    assert main(["--record", str(path)]) == 1


@pytest.mark.parametrize("invalid", [None, [], "not an object", False])
def test_non_objects_rejected(invalid):
    assert validate_record(invalid)


def test_global_quality_gate_checks_contract_and_regressions():
    catalog = yaml.safe_load((ROOT / "validation/engineering-validation.yaml").read_text())
    assert catalog["gates"]["quality:scripts"]["global_trigger"] is True
    command = catalog["commands"]["quality-scripts"]["shell"]
    assert "python scripts/ai_resource_governance.py --repository /workspace" in command
    assert "pytest tests/scripts/test_ai_resource_governance.py" in command


def test_customer_prompt_retry_preserves_declared_floor():
    spec = (ROOT / "architecture/reference/components/token-economy.md").read_text()
    assert 'minimum_tier = "MID_TIER"  # Downgrade' not in spec
    assert "Retrying this prompt never lowers its declared minimum" in spec


def test_index_matches_ratified_claim_type():
    claim = (ROOT / "knowledge/claims/C-051.md").read_text()
    index = (ROOT / "knowledge/index.md").read_text()
    assert "Type:            LAW" in claim
    assert "| C-051 | LAW |" in index


@pytest.mark.parametrize("category", ["CODE_GENERATION", "GOAL_UNDERSTANDING"])
def test_magic_llm_prompt_inherits_governance_for_each_route(category):
    from magic_llm.pipeline import MagicLLMPipeline
    from magic_llm.types import MagicLLMRequest, TaskCategory

    request = MagicLLMRequest(
        goal_id="GOAL-FIXTURE",
        institution_id="INST-004",
        go_authorization_id="synthetic-authorization",
        task_category=TaskCategory[category],
        task_description="Synthetic task",
        context_sections=[],
        ptr_snapshot={},
        expected_output_format="json",
        execution_plan_reference="synthetic-plan",
    )
    prompt = MagicLLMPipeline()._build_prompt(request)
    assert "standards/AI-RESOURCE-GOVERNANCE.md" in prompt
    assert "preserve all quality and authority floors" in prompt
