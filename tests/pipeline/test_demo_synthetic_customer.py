from __future__ import annotations

import json
import re
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

import demo_synthetic_customer as utility

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def test_usernames_carry_the_reserved_prefix_and_reject_unsafe_parts() -> None:
    assert utility.synthetic_username("s1126ab1", "a") == "acc-s1126ab1-a"
    for run_id, label in (("UPPER", "a"), ("short7a", "a"), ("s1126ab1", "1"), ("s1126ab1", "toolong"), ("s1126ab/..", "a")):
        with pytest.raises(utility.UtilityError):
            utility.synthetic_username(run_id, label)


def test_customers_have_synthetic_emails_and_unique_secrets() -> None:
    customers = utility.make_customers("s1126ab1", ["a", "b"])

    assert set(customers) == {"A", "B"}
    assert all(c["email"] == f"{c['username']}@synthetic.waooaw.test" for c in customers.values())
    assert customers["A"]["password"] != customers["B"]["password"]
    assert customers["A"]["otpSecret"] != customers["B"]["otpSecret"]
    assert all(len(c["otpSecret"]) >= 32 for c in customers.values())
    mobiles = [c["mobile"] for c in customers.values()]
    assert len(set(mobiles)) == len(mobiles)
    assert all(re.fullmatch(r"\+1555[0-9]{7}", mobile) for mobile in mobiles)


def test_run_ids_are_valid_and_vary() -> None:
    first, second = utility.new_run_id(NOW), utility.new_run_id(NOW)

    assert utility.RUN_ID.fullmatch(first) and first.startswith("s1126") and first != second


def test_job_script_never_forces_a_host_header_and_only_deletes_prefixed_group_members() -> None:
    compile(utility.JOB_SCRIPT, "job", "exec")
    # Container Apps routes on Host; forcing it produced HTTP 404 for every admin call.
    assert '"Host"' not in utility.JOB_SCRIPT and "'Host'" not in utility.JOB_SCRIPT
    assert '"X-Forwarded-Host": "auth.demo.waooaw.com"' in utility.JOB_SCRIPT
    assert 'u["username"].startswith(prefix)' in utility.JOB_SCRIPT
    assert "refusing a username outside the synthetic prefix" in utility.JOB_SCRIPT
    assert "members?first=0&max=500" in utility.JOB_SCRIPT


def test_job_lines_keep_only_known_markers() -> None:
    lines = ["noise", "SYN USER A acc-x-a created 201 id abc", "SYN DELETED acc-x-a 204", "SYN OTHER x", "SYN COMPLETE"]

    assert [line[1] for line in utility.parse_job_lines(lines)] == ["USER", "DELETED", "COMPLETE"]


def test_private_files_are_owner_only(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "run.json"

    utility.private_write(target, {"a": 1})

    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert json.loads(target.read_text()) == {"a": 1}


def test_harness_state_lets_the_acceptance_harness_adopt_the_customers() -> None:
    customers = utility.make_customers("s1126ab1", ["a", "b"])
    for index, customer in enumerate(customers.values()):
        customer["userId"] = f"id-{index}"

    state = utility.harness_state("s1126ab1", customers, NOW)

    assert state["runId"] == "s1126ab1" and set(state["customers"]) == {"A", "B"}
    assert set(state["customers"]["A"]) == {"userId", "username", "email", "password", "otpSecret"}
    assert state["values"] == {}


def test_create_registers_a_marker_for_every_customer_and_writes_private_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    posted: list[tuple[str, str, dict | None]] = []
    monkeypatch.setattr(utility, "PRIVATE_DIRECTORY", tmp_path / "private")
    monkeypatch.setattr(utility, "provisioner_token", lambda: "token")
    monkeypatch.setattr(utility, "provisioner_client_secret", lambda: "client-secret")

    def fake_network(spec, token, **_kwargs):
        assert spec["action"] == "create" and token == "client-secret"
        return [
            ["SYN", "USER", label, c["username"], "created", "201", "id", f"uid-{label}"] for label, c in spec["users"].items()
        ] + [["SYN", "COMPLETE"]]

    monkeypatch.setattr(utility, "run_in_network", fake_network)
    monkeypatch.setattr(utility, "http", lambda method, url, token, body=None: posted.append((method, url, body)) or 201)

    path = utility.create(2, "s1126ab1", tmp_path / "harness")

    assert [url for _, url, _ in posted] == [f"{utility.API_ORIGIN}/internal/v1/acceptance/runs/s1126ab1/synthetic-subjects"] * 2
    assert [body for _, _, body in posted] == [{"subject": "uid-A"}, {"subject": "uid-B"}]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads((tmp_path / "harness" / "run-state.json").read_text())["runId"] == "s1126ab1"


def test_create_fails_and_names_the_customer_when_keycloak_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(utility, "PRIVATE_DIRECTORY", tmp_path)
    monkeypatch.setattr(utility, "provisioner_token", lambda: "token")
    monkeypatch.setattr(utility, "provisioner_client_secret", lambda: "client-secret")
    monkeypatch.setattr(
        utility,
        "run_in_network",
        lambda spec, token, **_: [["SYN", "USER", "A", "acc-s1126ab1-a", "created", "404", "id", ""], ["SYN", "COMPLETE"]],
    )

    with pytest.raises(utility.UtilityError, match="acc-s1126ab1-a was not created"):
        utility.create(1, "s1126ab1", None)


def test_delete_only_touches_the_requested_run_prefix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    specs: list[dict] = []
    monkeypatch.setattr(utility, "PRIVATE_DIRECTORY", tmp_path)
    (tmp_path / "s1126ab1.json").write_text("{}")
    monkeypatch.setattr(utility, "provisioner_token", lambda: "token")
    monkeypatch.setattr(utility, "provisioner_client_secret", lambda: "client-secret")
    monkeypatch.setattr(utility, "run_in_network", lambda spec, token, **_: specs.append(spec) or [["SYN", "COMPLETE"]])
    monkeypatch.setattr(utility, "http", lambda *args, **kwargs: 204)

    utility.delete("s1126ab1")

    assert specs[0]["run_prefix"] == "acc-s1126ab1-" and specs[0]["prefix"] == "acc-"
    assert not (tmp_path / "s1126ab1.json").exists()


def test_the_job_gets_its_own_token_because_the_provisioner_token_expires_in_a_minute() -> None:
    assert 'os.environ["CLIENT_SECRET"]' in utility.JOB_SCRIPT
    assert "protocol/openid-connect/token" in utility.JOB_SCRIPT
    assert 'os.environ["TOK"]' not in utility.JOB_SCRIPT
    assert utility.job_spec("list")["client_id"] == utility.CLIENT_ID


def test_passwords_satisfy_the_realm_policy() -> None:
    # infrastructure/keycloak/waooaw-realm.json: length(12) and upperCase(1) and digits(1) and specialChars(1) and notUsername
    for _ in range(50):
        password = utility.realm_password()
        assert len(password) >= 12 and any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password) and any(not c.isalnum() for c in password)


def test_run_ids_meet_the_platform_marker_route_minimum_length() -> None:
    # AcceptanceSyntheticController.RunIdPattern is ^[A-Za-z0-9._-]{8,64}$; shorter ids answer HTTP 400.
    assert len(utility.new_run_id(NOW)) >= 8
    with pytest.raises(utility.UtilityError):
        utility.synthetic_username("s1126a", "a")


def test_throwaway_customers_claim_a_provider_through_an_admin_only_attribute_and_one_link() -> None:
    compile(utility.JOB_SCRIPT, "job", "exec")
    assert '"attributes": {"synthetic_idp": [spec["idp"]]}' in utility.JOB_SCRIPT
    assert "/federated-identity/{spec['idp']}" in utility.JOB_SCRIPT
    assert utility.IDP_ALIAS in {"google", "facebook"}
