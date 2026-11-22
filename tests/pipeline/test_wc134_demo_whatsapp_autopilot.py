from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from goal006_deployment_inputs import WHATSAPP_PUBLIC_SUBJECT_KEY_NAME, WHATSAPP_SECRET_NAMES, whatsapp_provider_inputs
from wc120_whatsapp_activation import activation_settings, assemble_activation_bundle
from wc134_demo_whatsapp_autopilot import (
    RECEIPTS,
    TRAFFIC_FLAGS,
    Autopilot,
    AutopilotError,
    HEARTBEAT_POLL_SECONDS,
    activation_window,
    binding_digests,
    build_receipts,
    digest,
    load_policy,
    provider_failure_summary,
    render_alert_query,
    spend_arguments,
    unique_query,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "release/wc134/demo-whatsapp-activation-policy.json"
KQL = ROOT / "infrastructure/operations/wc134-whatsapp-monitor.kql"
NOW = datetime(2026, 11, 16, 12, 0, 30, tzinfo=timezone.utc)
RUN = "43900000000-1"


def policy_bytes(**changes: Any) -> bytes:
    value = json.loads(POLICY.read_bytes())
    for dotted, replacement in changes.items():
        target = value
        *parents, leaf = dotted.split("__")
        for key in parents:
            target = target[key]
        target[leaf] = replacement
    return json.dumps(value).encode()


def deployment() -> dict[str, Any]:
    release = "sha256:" + "a" * 64
    config = {
        "key_vault_secret_uris": {"business-platform": "https://kv-waooaw-demo.vault.azure.net/secrets/business-platform"},
        "key_vault_secret_resource_ids": {
            "business-platform": (
                "/subscriptions/test/resourceGroups/demo/providers/Microsoft.KeyVault"
                "/vaults/kv-waooaw-demo/secrets/business-platform"
            )
        },
        "image_digests": {"business-platform": "ghcr.io/dlai-sd/business-platform@" + release},
        "whatsapp_provider": {
            "callback_host": "whatsapp-demo.example.com",
            "secret_versions": {name: "b" * 32 for name in WHATSAPP_SECRET_NAMES | {WHATSAPP_PUBLIC_SUBJECT_KEY_NAME}},
            "authority_reference": "FA:provider",
            "verification_enabled": True,
        },
    }
    return {**config, **whatsapp_provider_inputs("demo", config, {"images": config["image_digests"]})}


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class Harness:
    def __init__(self, *, tamper: Any = None, health: int = 200, beat: bool = True, broken: bool = False) -> None:
        self.calls: list[str] = []
        self.rule_puts: list[dict[str, Any]] = []
        self.clock = Clock()
        self.tamper = tamper
        self.health = health
        self.beat = beat
        self.broken = broken
        self.activated: dict[str, str] | None = None
        self.provider = deployment()["whatsapp_provider"]

    def operation(self, name: str, document: bytes, approved: str, run: str) -> dict[str, Any]:
        self.calls.append(name)
        off = {flag: "false" for flag in TRAFFIC_FLAGS}
        if name == "status":
            return {
                "status": "PASS",
                "registration_runtime_matches": True,
                "credential_metadata": "READY",
                "registration": {
                    "release_digest": self.provider["release_digest"],
                    "configuration_digest": self.provider["configuration_digest"],
                    "catalog_digest": self.provider["catalog_digest"],
                },
                "provider": self.provider,
                "traffic_flags": off,
                "verification_enabled": "true",
            }
        if name == "stop":
            return {"status": "PASS", "operation": "stop", "traffic_flags": off}
        if name == "assemble":
            bundle = assemble_activation_bundle(document, deployment(), self.clock())
            if self.tamper:
                value = json.loads(bundle)
                self.tamper(value)
                bundle = json.dumps(value).encode()
            return {"status": "PASS", "bundle": bundle}
        assert name == "activate"
        # The real validator accepts only the exact approved digest of a valid bundle.
        raw = self.candidate_bytes
        self.activated = activation_settings(raw, approved, deployment(), self.clock())
        return {"status": "PASS"}

    def az(self, *args: str) -> Any:
        if args[:3] == ("keyvault", "secret", "show"):
            return json.dumps(
                {
                    "AppId": "123456789012345",
                    "WabaId": "2074566849816683",
                    "PhoneNumberId": "1280841155113912",
                    "RecipientBindingDigest": "c" * 64,
                }
            )
        if args[:2] == ("identity", "show"):
            return "principal"
        if args[:2] == ("account", "show"):
            return "sub"
        if args[:3] == ("role", "assignment", "list"):
            scope = args[args.index("--scope") + 1]
            return [{"roleDefinitionName": "Key Vault Secrets User", "scope": scope}]
        if args[:3] == ("monitor", "action-group", "show"):
            return "group"
        if args[:2] == ("rest", "--method"):
            body = json.loads(args[args.index("--body") + 1])
            self.rule_puts.append(body)
            return body
        raise AssertionError(args)

    def http(self, url: str) -> int:
        return 401 if "hub.verify_token" in url else self.health

    def logs(self, kql: str) -> list[Any]:
        if "42501" in kql:
            return [{"Count": 1 if self.broken else 0}]
        return [{"Count": 1 if self.beat else 0}]

    def pilot(self, raw: bytes | None = None, **overrides: Any) -> Autopilot:
        pilot = Autopilot(
            policy_bytes=raw or POLICY.read_bytes(),
            alert_template=KQL.read_text(),
            consent_files={"consent.cs": b"consent"},
            operation=self.operation,
            az=self.az,
            http_status=self.http,
            log_query=self.logs,
            clock=self.clock,
            sleep=self.clock.sleep,
            run=RUN,
            release_run_id="43840552524",
            release_sha="a" * 40,
            heartbeat_timeout=120,
            **overrides,
        )
        original = pilot.operation

        def capture(name: str, document: bytes, approved: str, run: str) -> dict[str, Any]:
            result = original(name, document, approved, run)
            if name == "assemble":
                self.candidate_bytes = result["bundle"]
            return result

        pilot.operation = capture
        return pilot


def test_committed_policy_matches_the_approved_demo_limits() -> None:
    policy = load_policy(POLICY.read_bytes())

    assert policy["limits"] == {
        "maximum_messages": 200,
        "maximum_messages_per_minute": 6,
        "maximum_spend_inr": 500,
        "maximum_cost_per_message_inr": 5,
    }
    assert policy["window_days"] == 7
    assert policy["cohort"] == {"allow_public_admission": True, "allow_provisional_onboarding": True}


@pytest.mark.parametrize(
    "change",
    [
        {"approval__approved_by": "someone-else"},
        {"window_days": 15},
        {"limits__maximum_spend_inr": 501},
        {"limits__maximum_spend_inr": 0.001},
        {"limits__maximum_cost_per_message_inr": 600},
        {"limits__maximum_messages_per_minute": 201},
        {"cohort__allow_provisional_onboarding": False},
        {"tenant_id": "00000000-0000-0000-0000-000000000000"},
        {"schema": "other"},
    ],
)
def test_policy_outside_the_founder_ceiling_is_refused(change: dict[str, Any]) -> None:
    with pytest.raises(AutopilotError):
        load_policy(policy_bytes(**change))


def test_unknown_policy_fields_are_refused() -> None:
    value = json.loads(POLICY.read_bytes())
    value["extra"] = True
    with pytest.raises(AutopilotError):
        load_policy(json.dumps(value).encode())


def test_spend_arguments_are_derived_from_the_policy_and_stable() -> None:
    first = spend_arguments(POLICY.read_bytes())

    assert first["paise"] == 50000
    assert first == spend_arguments(POLICY.read_bytes())
    assert first["evidence_id"] != spend_arguments(policy_bytes(window_days=3))["evidence_id"]


def test_activation_window_opens_a_minute_early_and_lasts_the_policy_days() -> None:
    assert activation_window(NOW, 7) == ("2026-11-16T11:59:00Z", "2026-11-23T11:59:00Z")


def test_binding_digests_are_one_way_and_keep_no_raw_identifier() -> None:
    raw = {"AppId": "123456789012345", "WabaId": "2074566849816683", "PhoneNumberId": "1280841155113912"}
    result = binding_digests({**raw, "RecipientBindingDigest": "c" * 64})

    assert set(result) == {"AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest", "ContactDigest"}
    assert all(identifier not in json.dumps(result) for identifier in raw.values())
    assert all(len(result[key]) == 64 for key in ("AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest"))
    with pytest.raises(AutopilotError):
        binding_digests({"AppId": "1"})


def test_alert_query_renders_every_placeholder_and_rejects_leftovers() -> None:
    query = render_alert_query(
        KQL.read_text(), starts_at="s", expires_at="e", activation_digest="a", release="r", configuration="c"
    )

    assert "${" not in query and '"a"' in query
    with pytest.raises(AutopilotError):
        render_alert_query(
            KQL.read_text() + "${unknown}", starts_at="s", expires_at="e", activation_digest="a", release="r", configuration="c"
        )


def test_receipts_cover_all_nine_requirements_and_outlive_the_window() -> None:
    facts = {
        "release_run_id": "1",
        "release_sha": "a" * 40,
        "release_digest": "sha256:" + "a" * 64,
        "traffic_flags_before": {},
        "status": {},
        "business_identity": "id",
        "role_assignments": [],
        "consent_implementation": {},
        "stop": {},
        "alert_rule": {},
        "policy_digest": "sha256:" + "b" * 64,
        "limits": {},
    }
    documents, prerequisites = build_receipts(facts, "2026-11-23T11:59:00Z", RUN)

    assert set(prerequisites) == set(RECEIPTS) == set(documents)
    for name, receipt in prerequisites.items():
        assert receipt["digest"] == digest(documents[name])
        assert receipt["expires_at"] == "2026-11-23T11:59:00Z"


def test_successful_activation_is_accepted_by_the_real_validator_and_stays_inside_policy() -> None:
    harness = Harness()

    evidence = harness.pilot().activate()

    assert harness.calls == ["status", "stop", "assemble", "activate"]
    assert harness.activated is not None
    assert harness.activated["WhatsAppCapability__Authority__MaximumMessages"] == "200"
    assert harness.activated["WhatsAppCapability__Authority__AllowPublicAdmission"] == "true"
    assert evidence["window"] == {"starts_at": "2026-11-16T11:59:00Z", "expires_at": "2026-11-23T11:59:00Z"}
    # The alert rule is created disabled, bound to this activation, then enabled once active.
    assert [put["properties"]["enabled"] for put in harness.rule_puts] == [False, True]
    assert harness.rule_puts[0]["properties"]["evaluationFrequency"] == "PT5M"
    assert set(evidence["receipts"]) == set(RECEIPTS)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: value["authority"].update(MaximumMessages=201),
        lambda value: value["authority"].update(MaximumSpendInr=501),
        lambda value: value["authority"].update(ExpiresAt="2026-12-30T00:00:00Z"),
        lambda value: value["authority"].update(AllowRegistrationVerification=True),
        lambda value: value["templates"][0].update(Body="changed"),
    ],
)
def test_a_candidate_outside_the_policy_is_never_activated(tamper: Any) -> None:
    harness = Harness(tamper=tamper)

    with pytest.raises(AutopilotError):
        harness.pilot().activate()

    assert "activate" not in harness.calls
    assert harness.calls[-1] == "stop"
    assert harness.rule_puts[-1]["properties"]["enabled"] is False


@pytest.mark.parametrize(
    "harness",
    [Harness(health=503), Harness(beat=False), Harness(broken=True)],
    ids=["unhealthy", "no-heartbeat", "permission-errors"],
)
def test_failed_proof_stops_whatsapp_and_disables_the_alert(harness: Harness) -> None:
    with pytest.raises(AutopilotError):
        harness.pilot().activate()

    assert harness.calls[-2:] == ["activate", "stop"]
    assert harness.rule_puts[-1]["properties"]["enabled"] is False


def test_heartbeat_is_polled_quickly_with_a_distinct_query_each_time() -> None:
    harness = Harness(beat=False)
    sleeps: list[float] = []
    queries: list[str] = []
    clock_sleep, logs = harness.clock.sleep, harness.logs
    harness.clock.sleep = lambda seconds: (sleeps.append(seconds), clock_sleep(seconds))[1]  # type: ignore[method-assign]
    harness.logs = lambda kql: (queries.append(kql), logs(kql))[1]  # type: ignore[method-assign]

    with pytest.raises(AutopilotError, match="no operations heartbeat"):
        harness.pilot().activate()

    assert set(sleeps) == {HEARTBEAT_POLL_SECONDS}
    assert len(queries) > 4
    assert len(set(queries)) == len(queries)
    assert unique_query("q").startswith("q\n// ")
    assert unique_query("q") != unique_query("q")


def test_unready_registration_stops_before_any_activation_work() -> None:
    harness = Harness()
    original = harness.operation

    def unready(name: str, document: bytes, approved: str, run: str) -> dict[str, Any]:
        result = original(name, document, approved, run)
        if name == "status":
            result = {**copy.deepcopy(result), "registration_runtime_matches": False}
        return result

    harness.operation = unready  # type: ignore[method-assign]

    with pytest.raises(AutopilotError, match="registration"):
        harness.pilot().activate()

    assert "assemble" not in harness.calls


def _workflow(name: str) -> dict[str, Any]:
    import yaml

    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def test_database_reset_is_opt_in_and_only_for_a_demo_apply() -> None:
    deploy = _workflow("deploy.yaml")
    reset = deploy[True]["workflow_dispatch"]["inputs"]["reset_demo_database"]
    steps = deploy["jobs"]["authorize"]["steps"]
    validate = next(step for step in steps if step.get("id") == "dispatch")

    assert reset["type"] == "boolean" and reset["default"] is False
    assert 'test "$TARGET_ENVIRONMENT:$EXECUTION_MODE" = demo:apply' in validate["run"]
    assert (
        deploy["jobs"]["deploy"]["with"]["reset_demo_database"] == "${{ needs.authorize.outputs.reset_demo_database == 'true' }}"
    )
    called = _workflow("environment-deployment.yaml")[True]["workflow_call"]["inputs"]["reset_demo_database"]
    assert called["default"] is False and called["type"] == "boolean"


def test_provisioner_resets_only_on_request_and_always_sets_the_policy_spend_authority() -> None:
    text = (ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    create = text.split("      - name: Create WC-124 database provisioner", 1)[1].split(
        "      - name: Run WC-124 database provisioner", 1
    )[0]
    run = text.split("      - name: Run WC-124 database provisioner", 1)[1].split(
        "      - name: Apply reviewed PostgreSQL Plan B compatibility", 1
    )[0]

    assert '(if $reset_demo_database then ["--reset-demo-databases"] else [] end)' in create
    assert '"--demo-spend-authority-paise"' in create and "wc134_demo_whatsapp_autopilot.py spend-args" in create
    assert "if $reset" in run and ".database_reset == null" in run
    assert ".spend_authority.maximum_paise == $spend_paise" in run


def test_activation_step_runs_after_tls_binding_inside_the_apply_job_and_publishes_evidence() -> None:
    steps = _workflow("environment-deployment.yaml")["jobs"]["terraform"]["steps"]
    names = [step.get("name") for step in steps]
    step = steps[names.index("Activate Demo WhatsApp under the standing Founder policy")]

    assert names.index("Bind Demo Azure-managed TLS certificates") < names.index(step["name"])
    assert names.index(step["name"]) < names.index("Preserve workload state after apply failure")
    assert step["if"] == "inputs.apply && inputs.environment == 'demo'"
    assert "release/wc134/demo-whatsapp-activation-policy.json" in step["run"]
    upload = next(item for item in steps if item.get("name") == "Upload plans and evidence")
    assert "whatsapp-autopilot/*.json" in upload["with"]["path"]


def test_activation_step_gets_a_fresh_login_and_caches_the_storage_token_first() -> None:
    steps = _workflow("environment-deployment.yaml")["jobs"]["terraform"]["steps"]
    names = [step.get("name") for step in steps]
    activate = steps[names.index("Activate Demo WhatsApp under the standing Founder policy")]
    login = steps[names.index("Refresh Azure login before Demo WhatsApp activation")]

    assert names.index(login["name"]) == names.index(activate["name"]) - 1
    assert login["if"] == activate["if"]
    assert login["with"]["client-id"] == "${{ steps.foundation.outputs.deployment_client_id }}"
    first = activate["run"].index("https://storage.azure.com/")
    assert first < activate["run"].index("wc134_demo_whatsapp_autopilot.py run")


def test_failed_provider_phase_reports_the_classified_command_failure(tmp_path: Path) -> None:
    failure = {"tool": "azure", "stage": "BLOB_SHOW", "exit_code": 1, "reason": "AUTHORIZATION_DENIED"}
    stdout = json.dumps({"provider_command_failure": failure}) + "\nProvider operation denied or failed (X).\n"
    evidence = tmp_path / "evidence-prepare.json"
    evidence.write_text(json.dumps({"command_failure": failure, "failure_location": {"line": 1}, "reason": "ignored"}))

    for path in (evidence, tmp_path / "missing.json"):
        summary = provider_failure_summary(stdout, "", path)
        assert summary.startswith("Provider operation denied or failed (X).")
        assert '"stage": "BLOB_SHOW"' in summary and '"reason": "AUTHORIZATION_DENIED"' in summary
        assert "ignored" not in summary
