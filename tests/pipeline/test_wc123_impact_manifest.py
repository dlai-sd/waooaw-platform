"""WC-123 AUTH-WC-01 impact-manifest contract."""

# Implements: work-contracts/WC-123-authentication-authorization-implementation.md §7.1 AUTH-WC-01
# Constitutional basis: C-023, C-059, C-080

from hashlib import sha256
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "work-contracts/WC-123-impact-manifest.yaml"
PROFILE_PATH = (
    ROOT
    / "architecture/reference/components/authentication-authorization-capacity-profile.v1.yaml"
)


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_profile() -> dict:
    return yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def canonical_digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{sha256(encoded).hexdigest()}"


def test_accepted_source_digests_are_current() -> None:
    manifest = load_manifest()

    for relative_path, expected_digest in manifest["accepted_sources"].items():
        content = (ROOT / relative_path).read_bytes()
        assert sha256(content).hexdigest() == expected_digest


def test_all_requirements_and_components_are_bound() -> None:
    manifest = load_manifest()
    ledger = yaml.safe_load((ROOT / manifest["requirement_binding"]["ledger"]).read_text(encoding="utf-8"))
    requirement_ids = [row["requirement_id"] for row in ledger["requirements"]]

    assert requirement_ids == [f"WC123-R{number:03d}" for number in range(1, 49)]
    assert manifest["requirement_binding"]["count"] == len(requirement_ids)
    assert manifest["requirement_binding"]["components"] == [
        f"AUTH-WC-{number:02d}" for number in range(1, 8)
    ]


def test_legacy_authority_and_replacement_paths_are_explicit() -> None:
    manifest = load_manifest()
    authority = manifest["current_authority_paths"]

    assert authority["browser_session"]["legacy_creation"]
    assert authority["browser_session"]["removal_or_replacement"]
    assert authority["tenant_and_rls"]["legacy_acceptance"]
    assert authority["tenant_and_rls"]["removal_or_replacement"]
    assert authority["identity_provider"]["lifecycle_writer"]["role"] == "realm-management/manage-users"
    assert authority["identity_provider"]["lifecycle_writer"]["separation"]


def test_capacity_profile_is_complete_and_ready_without_authorizing_implementation() -> None:
    manifest = load_manifest()
    capacity = manifest["capacity_and_timeout_budget"]
    profile = load_profile()

    assert manifest["status"] == "READY_FOR_AUTH_WC_02"
    assert capacity["disposition"] == "ACCEPTED"
    assert capacity["accepted_constraints"]["database_connection_ceiling_percent"] == 80
    assert profile["schema"] == "waooaw.authentication-authorization-capacity-profile/v1"
    assert profile["profile_id"] == capacity["profile"]["id"] == "wc123-auth-capacity-v1"
    assert profile["version"] == capacity["profile"]["version"] == "1.0.0"
    assert profile["status"] == "ACCEPTED"
    assert profile["scope"]["production_authorized"] is False
    assert set(profile["environments"]) == {"demo", "uat"}
    assert "separate Founder implementation authorization" in capacity["readiness_rule"]


def test_environment_manifests_reference_the_exact_profile_and_render_without_drift() -> None:
    schema = load_json("infrastructure/environment-readiness/environment-manifest.schema.json")
    profile = load_profile()

    for environment in ("demo", "uat"):
        source = load_json(f"infrastructure/identity-config/environments/{environment}.json")
        rendered = load_json(f"infrastructure/environment-readiness/{environment}.rendered.json")
        reference = source["capacityProfile"]

        Draft202012Validator(schema).validate(source)
        assert reference == {
            "id": profile["profile_id"],
            "version": profile["version"],
            "source": (
                "architecture/reference/components/"
                "authentication-authorization-capacity-profile.v1.yaml"
            ),
            "environment": environment,
        }
        assert rendered["configuration"] == source
        assert rendered["manifestDigest"] == canonical_digest(source)
        projection = {key: value for key, value in rendered.items() if key != "renderDigest"}
        assert rendered["renderDigest"] == canonical_digest(projection)


def test_environment_specific_connection_equations_hold_at_eighty_percent() -> None:
    profile = load_profile()
    database = profile["shared"]["database"]

    assert database["application_connection_limit"] == 100
    assert database["migration_and_operations_reserve"] == 20
    assert database["per_replica_web_session_pool"] == 5
    assert database["connection_ceiling_percent"] == 80
    permitted = (
        database["application_connection_limit"] * database["connection_ceiling_percent"] // 100
    )

    expected = {"demo": (1, 25, 55), "uat": (10, 70, 10)}
    for environment, (replicas, used, headroom) in expected.items():
        values = profile["environments"][environment]
        equation = values["database_equation"]
        calculated = replicas * database["per_replica_web_session_pool"] + database[
            "migration_and_operations_reserve"
        ]

        assert values["web"]["maximum_replicas"] == replicas
        assert calculated == used <= permitted
        assert equation["web_pool_connections"] + equation["reserved_connections"] == used
        assert equation["permitted_connections"] == permitted
        assert equation["headroom_connections"] == headroom
        assert equation["expression"] == (
            f"{replicas} * 5 + 20 = {used} <= 80% * 100 = 80"
        )


def test_timeout_hierarchy_queue_concurrency_and_retry_bounds_are_finite() -> None:
    profile = load_profile()
    shared = profile["shared"]
    budgets = shared["request_budgets_ms"]

    for timeout in shared["timeouts"].values():
        if not isinstance(timeout, dict) or "milliseconds" not in timeout:
            continue
        assert timeout["milliseconds"] > 0
        assert all(timeout["milliseconds"] <= budgets[caller] for caller in timeout["callers"])

    assert shared["per_principal_concurrency"]["refreshes_per_session_family"] == 1
    for environment, replicas in (("demo", 1), ("uat", 10)):
        values = profile["environments"][environment]
        global_limit = values["concurrency"]["global_requests"]
        queues = values["queues"]
        assert global_limit == replicas * shared["aca"]["concurrent_requests_per_replica"]
        assert queues["request"] == global_limit
        assert all(0 < value <= global_limit for value in queues.values())
        assert all(
            0 < value <= global_limit
            for value in shared["per_principal_concurrency"].values()
            if isinstance(value, int)
        )

    retry = shared["overload_and_retry"]
    assert retry["request_queue_overflow_status"] == 429
    assert retry["dependency_or_lifecycle_overload_status"] == 503
    assert 0 < retry["retry_after_seconds_max"] <= min(budgets.values()) // 1000
    assert 0 < retry["retry_attempts_max"] <= 3
    assert 0 < retry["retry_backoff_initial_ms"] <= retry["retry_backoff_max_ms"]
    assert retry["retry_backoff_max_ms"] < min(budgets.values())


def test_aca_replica_and_cost_sources_match_the_accepted_profile() -> None:
    profile = load_profile()
    scaling = yaml.safe_load(
        (ROOT / "infrastructure/container-apps/scaling-rules.yaml").read_text(encoding="utf-8")
    )
    demo_tf = (
        ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf"
    ).read_text(encoding="utf-8")
    module_tf = (
        ROOT / "infrastructure/terraform/phase2/modules/workload/variables.tf"
    ).read_text(encoding="utf-8")

    assert scaling["web"]["scaling"]["max_replicas"] == 10
    aca_rule = scaling["web"]["scaling"]["rules"][0]
    assert int(aca_rule["metadata"]["concurrentRequests"]) == profile["shared"]["aca"][
        "concurrent_requests_per_replica"
    ]
    assert re.search(r"max_replicas\s*=\s*1\b", demo_tf)
    assert re.search(
        r'variable "max_replicas".*?default\s*=\s*10\b', module_tf, flags=re.DOTALL
    )

    for environment in ("demo", "uat"):
        parameters = load_json(
            f"infrastructure/deployment-stacks/goal006-runner/"
            f"{environment}.prerequisites.parameters.json"
        )
        accepted_cost = profile["environments"][environment]["cost"]
        assert parameters["parameters"]["monthlyBudgetInr"]["value"] == 10000
        assert accepted_cost["ceiling"] == profile["shared"]["cost"][
            "ceiling_per_environment"
        ] == 10000


def test_protected_actions_and_rollback_are_preserved() -> None:
    manifest = load_manifest()
    delivery = manifest["deployment_and_rollback"]

    assert "legacy browser tokens and claim authority remain rejected" in delivery["rollback"]
    assert set(delivery["protected_actions"]) == {
        "provider mutation",
        "cloud mutation",
        "deployment",
        "external traffic",
        "activation",
        "Production action",
        "approval",
        "merge",
    }
