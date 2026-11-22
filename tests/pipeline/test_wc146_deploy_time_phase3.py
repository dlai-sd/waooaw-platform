from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
ENGINE = yaml.safe_load((WORKFLOWS / "environment-deployment.yaml").read_text(encoding="utf-8"))
ENGINE_TEXT = (WORKFLOWS / "environment-deployment.yaml").read_text(encoding="utf-8")
DEPLOY = yaml.safe_load((WORKFLOWS / "deploy.yaml").read_text(encoding="utf-8"))


def test_verification_runs_inside_the_engine_alongside_runner_cleanup() -> None:
    verify = ENGINE["jobs"]["verify"]

    assert verify["uses"] == "./.github/workflows/environment-deployment-verification.yaml"
    assert verify["needs"] == ["terraform"]
    assert "cleanup-private" not in verify["needs"]
    assert "verify" not in ENGINE["jobs"]["cleanup-private"]["needs"]
    condition = " ".join(verify["if"].split())
    assert "always()" in condition
    assert "inputs.apply" in condition
    assert "needs.terraform.outputs.apply_result == 'success'" in condition
    assert verify["with"]["verification_client_id"] == "${{ needs.terraform.outputs.verification_client_id }}"
    assert verify["with"]["web_url"] == "${{ needs.terraform.outputs.web_url }}"
    assert verify["secrets"] == "inherit"


def test_the_neutral_entry_publishes_only_after_the_engine_including_verification_succeeds() -> None:
    assert "verify" not in DEPLOY["jobs"]
    publish = DEPLOY["jobs"]["publish-url"]

    assert publish["needs"] == ["authorize", "deploy"]
    assert "needs.deploy.result == 'success'" in " ".join(publish["if"].split())


def test_the_verification_workflow_still_enforces_the_trusted_top_level_caller() -> None:
    verification = (WORKFLOWS / "environment-deployment-verification.yaml").read_text(encoding="utf-8")

    assert "EXPECTED_CALLER_WORKFLOW_REF: ${{ github.repository }}/.github/workflows/deploy.yaml@refs/heads/main" in verification
    assert "Reject stale release before independent verification" in verification
    assert "environment: ${{ inputs.environment }}-verification" in verification


def test_every_log_analytics_poll_carries_a_unique_query_text() -> None:
    # Log Analytics serves a cached result for about two minutes to identical query text (WC-146).
    sources = [
        (WORKFLOWS / "environment-deployment.yaml", ENGINE_TEXT),
        (ROOT / "scripts/goal006_capture_aca_execution.sh", (ROOT / "scripts/goal006_capture_aca_execution.sh").read_text()),
    ]
    for path, text in sources:
        for call in re.finditer(r"az monitor log-analytics query\b(.*?)--output json", text, re.DOTALL):
            assert "// poll " in call.group(1) or "// poll " in text[call.start() - 600 : call.start()], path.name


def test_temporal_log_wait_polls_quickly_within_the_previous_budget() -> None:
    step = ENGINE_TEXT.split("- name: Qualify exact Temporal startup through PgBouncer", 1)[1].split("\n      - name:", 1)[0]
    wait = step.split("for attempt in $(seq 1 60); do", 1)[1]

    assert "// poll $attempt-$(date +%s%N)" in wait
    assert "[wc124-temporal-pool] attempt=$attempt latest_log=$latest_log end_time=$end_time" in wait
    assert 'test "$attempt" != 60' in wait
    assert "sleep 3\n" in wait
    assert "sleep 10" not in wait
    assert 'latest_epoch" -ge "$end_epoch"' in wait
