# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R013, WC172-R015
# Constitutional basis: C-059, C-063, ADR-046, ADR-047
"""Repository guards for real money: shared tokens carry no new authority, hosted runners never read a production
vault, and the go-live checklist lists every production prerequisite with an owner, a status and evidence."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ("BP_SERVICE_JWT_SECRET", "PR_SERVICE_JWT_SECRET", "OPS_AUTH_TOKEN")
SCANNED = ("src", "infrastructure", ".github/workflows")
SKIPPED_PARTS = {"__pycache__", "node_modules", "tests", "bin", "obj"}

# The complete list of non-test files that still mention a shared token (ADR-046 forbids it as authority; WC-172 U3
# removes the governed uses per environment). A new file here is a new use and needs the Founder's review.
RECORDED_USES = {
    "infrastructure/terraform/phase2/modules/workload/main.tf",
    "src/agent-adapters/runtime_contract/http.py",
    "src/ai-runtime/transcription.py",
    "src/billing-engine/Dockerfile",
    "src/billing-engine/config.py",
    "src/billing-engine/reconciliation/router.py",
    "src/billing-engine/trial/router.py",
    "src/professional-runtime/main.py",
    "src/professional-runtime/routers/conversation_execution.py",
    "src/professional-runtime/routers/voice_orchestration.py",
}


def _uses() -> set[str]:
    found: set[str] = set()
    for base in SCANNED:
        for path in (ROOT / base).rglob("*"):
            relative = path.relative_to(ROOT)
            if not path.is_file() or SKIPPED_PARTS & set(relative.parts) or path.suffix in {".pyc", ".dll", ".png"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(token in text for token in TOKENS):
                found.add(relative.as_posix())
    return found


def test_the_remaining_uses_of_the_shared_tokens_are_exactly_the_recorded_ones() -> None:
    assert _uses() == RECORDED_USES


def test_no_new_billing_route_takes_authority_from_a_shared_token() -> None:
    for relative in (
        "src/billing-engine/invoicing/private_routes.py",
        "src/billing-engine/money_admin.py",
        "src/billing-engine/spend_chain/private_routes.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert not any(token in text for token in TOKENS), relative


def _hosted(jobs: dict) -> list[tuple[str, dict]]:
    return [
        (name, job)
        for name, job in jobs.items()
        if "self-hosted" not in str(job.get("runs-on", "")) and "keyvault" in yaml.dump(job)
    ]


def test_no_workflow_job_on_a_hosted_runner_reads_a_production_vault() -> None:
    allowed_vault_sources = {"${{ vars.AZURE_KEYVAULT_NAME }}", "$ACCEPTANCE_KEY_VAULT"}
    for path in sorted((ROOT / ".github/workflows").glob("*.y*ml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in _hosted(document.get("jobs") or {}):
            text = yaml.dump(job)
            assert not re.search(r"kv-waooaw-(prod|production)|waooaw-prod", text), (path.name, name)
            for vault in re.findall(r'--vault-name\s+(?:\\\s+)?"?([^\s"\\]+)', text):
                assert vault in {"$AZ_KV", "$ACCEPTANCE_KEY_VAULT"}, (path.name, name, vault)
            if "AZ_KV=" in text:
                assert any(source in text for source in allowed_vault_sources), (path.name, name)


def test_the_hosted_acceptance_vault_is_sandbox_only_and_never_production() -> None:
    for path in sorted((ROOT / "validation/acceptance/environments").glob("*.yaml")):
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        vault = profile["azure"]["key_vault"]
        assert path.stem in {"demo", "uat"}, path.name
        assert vault.endswith("-acc") and "prod" not in vault, vault


def test_a_vault_a_deployment_job_reads_by_environment_runs_only_on_a_private_runner() -> None:
    document = yaml.safe_load((ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8"))
    for name, job in document["jobs"].items():
        if "kv-waooaw-${{ inputs.environment }}" in yaml.dump(job):
            assert "self-hosted" in str(job["runs-on"]), name


CHECKLIST = ROOT / "architecture/reference/runbooks/go-live-checklist.md"
STATUSES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "DONE"}
REQUIRED = {
    "vault": "G-03",
    "identities": "G-04",
    "razorpay account": "G-07",
    "live keys": "G-08",
    "meta": "G-10",
    "whatsapp": "G-11",
    "protections": "G-13",
    "rollback": "G-14",
    "paging": "G-15",
    "approval": "G-23",
    "rehearsal": "G-24",
}


def _rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"G-\d\d", cells[0]):
            rows[cells[0]] = cells
    return rows


def test_the_go_live_checklist_lists_every_prerequisite_with_owner_status_and_evidence() -> None:
    rows = _rows()
    assert set(REQUIRED.values()) <= set(rows)
    for identifier, (_, requirement, owner, status, evidence) in rows.items():
        assert requirement and owner in {"Founder", "Platform IT Expert"}, identifier
        assert status in STATUSES, identifier
        assert evidence, identifier
        assert status != "DONE" or evidence.lower() != "pending", identifier


def test_only_the_founder_owns_the_live_keys_the_approval_and_the_rehearsal() -> None:
    rows = _rows()
    for identifier in ("G-07", "G-08", "G-23", "G-24"):
        assert rows[identifier][2] == "Founder", identifier
    assert "never sees a key" in rows["G-08"][4]
    assert rows["G-23"][3] == "NOT_STARTED" and rows["G-24"][3] == "NOT_STARTED"
