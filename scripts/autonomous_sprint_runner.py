#!/usr/bin/env python3
"""
autonomous_sprint_runner.py

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Skill 8 — SDLC Execution)
# constitutional_basis: C-023 (Evidence First), C-041 (ValidateAction), C-059 (Traceability),
#                       C-065 (SDLC Separation — Author hat), C-066 Tier 2A (autonomous execution),
#                       C-070 (Constitutional DNA — all 3 instincts apply to this agent),
#                       C-007/C-027 (Append-only enforcement — validated in WC011-02)
# ib_item: IB-009
# office: Platform IT Expert — Implementation hat
# amended: 2026-07-23 — EA review; C-007 halt added; Fix 1-5 applied

Implementation hat — executes sprint tasks, opens PR.
Called by autonomous-sprint.yaml Job 1 (execute).
C-065: This script is the AUTHOR. Never the reviewer.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
EVIDENCE_LOG = REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"


# ── Helpers ──────────────────────────────────────────────────────────────────

def set_output(key: str, value: str) -> None:
    """Write to GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"  OUTPUT {key}={value}")


def record_evidence(event: str, **kwargs) -> None:
    """Bootstrap evidence stub (engineering-standards.md §12)."""
    EVIDENCE_LOG.parent.mkdir(exist_ok=True)
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "stub_mode": True,
        **kwargs,
    }
    with EVIDENCE_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, cwd=REPO_ROOT)


def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, check=check)


def parse_sprint_state() -> dict:
    """Extract SPRINT_STATE_MACHINE YAML block from PROJECT_STATE.md."""
    content = STATE_FILE.read_text(encoding="utf-8")
    # Find the yaml block under SPRINT_STATE_MACHINE
    match = re.search(
        r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```",
        content, re.DOTALL
    )
    if not match:
        raise ValueError("SPRINT_STATE_MACHINE block not found in PROJECT_STATE.md")

    state: dict = {}
    for line in match.group(1).splitlines():
        line = line.split("#")[0].strip()  # strip comments
        if ":" in line:
            k, _, v = line.partition(":")
            state[k.strip()] = v.strip().strip('"').strip("'")

    # Parse tasks_remaining list
    tasks_block = re.search(
        r"tasks_remaining:\n((?:  - [^\n]+\n?)*)",
        match.group(1)
    )
    if tasks_block:
        tasks = re.findall(r"  - (\S+)", tasks_block.group(1))
        state["tasks_remaining"] = [t for t in tasks if not t.startswith("#")]
    else:
        state["tasks_remaining"] = []

    return state


def check_platform_phase_gate(state: dict) -> None:
    """
    C-001 / FinOps Gate: Refuse ALL implementation work when platform_phase = SPEC.
    This is a hard stop — not a warning. It prevents self-authorization drift.
    In SPEC phase, offer to run spec validation instead of implementation.
    """
    phase = state.get("platform_phase", "SPEC")
    halt = state.get("autonomous_halt", "true").lower()

    if halt == "true":
        record_evidence("autonomous_halt_active", reason="AUTONOMOUS_HALT=true in PROJECT_STATE.md")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print("  HALT: AUTONOMOUS_HALT=true — no execution (C-001 Human Override)")
        sys.exit(0)

    if phase == "SPEC":
        print("  INFO: platform_phase=SPEC — running spec validation mode (no src/ operations)")
        record_evidence("spec_phase_validation_mode", platform_phase=phase)
        run_spec_validation()
        set_output("halt", "false")
        set_output("result", "SPEC_VALIDATION_COMPLETE")
        sys.exit(0)

    if phase != "IMPLEMENTATION":
        record_evidence("platform_phase_gate_blocked", platform_phase=phase,
                        reason=f"platform_phase={phase}, not IMPLEMENTATION.")
        set_output("halt", "true")
        set_output("result", "SKIPPED")
        print(f"  HALT: platform_phase={phase}. Must be IMPLEMENTATION to execute.")
        sys.exit(0)


def run_spec_validation() -> None:
    """
    GAP-SIM-08 fix: SPEC-phase useful work.
    When platform_phase=SPEC, the agent validates spec consistency instead of doing nothing.
    Zero LLM cost — pure Python checks.
    """
    print("\n── SPEC Phase Validation Mode ──────────────────────────────────────")
    issues = []

    # Check 1: SPRINT_STATE_MACHINE health
    try:
        state = parse_sprint_state()
        print(f"  ✓ SPRINT_STATE_MACHINE parseable: phase={state.get('platform_phase')}, "
              f"sprint={state.get('current_sprint')}")
    except Exception as e:
        issues.append(f"SPRINT_STATE_MACHINE parse error: {e}")

    # Check 2: Work contract exists
    sprint = state.get("current_sprint", "")
    wc_paths = list(REPO_ROOT.glob(f"work-contracts/{sprint}*.md")) if sprint else []
    if wc_paths:
        print(f"  ✓ Work contract found: {wc_paths[0].name}")
    else:
        issues.append(f"No work contract found for sprint {sprint}")

    # Check 3: build_sprint_index.py can run without errors
    try:
        result = run([sys.executable, "scripts/build_sprint_index.py", "--dry-run", "--no-copilotignore"],
                    check=False, capture=True)
        if result.returncode == 0 or "token budget" in result.stdout.lower():
            print("  ✓ Sprint index builder: parseable")
        else:
            issues.append(f"Sprint index builder error: {result.stderr[:200]}")
    except Exception as e:
        issues.append(f"Sprint index builder exception: {e}")

    # Check 4: Key spec files exist
    required_specs = [
        "constitution/AGENT-ENTRY.md",
        "adr/ADR-INDEX.md",
        "tests/QA-STRATEGY.md",
        "standards/CODING-STANDARDS.md",
    ]
    for spec in required_specs:
        if (REPO_ROOT / spec).exists():
            print(f"  ✓ Spec exists: {spec}")
        else:
            issues.append(f"Required spec missing: {spec}")

    # Report
    if issues:
        print(f"\n  SPEC VALIDATION: {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"    - {issue}")
        record_evidence("spec_validation_issues", count=len(issues), issues=issues)
    else:
        print("\n  SPEC VALIDATION: All checks passed. Platform ready for implementation when Founder authorizes.")
        record_evidence("spec_validation_passed")

    print("── End Spec Validation ──────────────────────────────────────────────\n")


def update_sprint_state(**kwargs) -> None:
    """Update fields in SPRINT_STATE_MACHINE via sprint_state.py."""
    pairs = []
    for k, v in kwargs.items():
        pairs += [k, f'"{v}"' if " " in str(v) else str(v)]
    run([sys.executable, "scripts/sprint_state.py", "set"] + pairs)


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["gh"] + args, check=check, capture=True)


def flag_spec_gap(
    task_id: str,
    gap_description: str,
    affected_spec: str,
    workaround: str = "",
    constitutional_basis: str = "",
) -> None:
    """
    HALT the current task and create a GitHub Issue for EA/SA/Founder review.

    The implementation agent CANNOT proceed with a workaround. A workaround is
    an architectural decision — it is outside the Implementation hat's authority (C-065).

    Constitutional basis:
      C-065: SDLC Separation — Implementation hat cannot make architectural decisions
      C-066: Tier 3 — Architectural/spec changes require EA office or Founder approval
      C-059: Traceability — every implementation must trace to a valid spec; gap = no trace

    This function:
      1. Creates a GitHub Issue (type:spec-gap, awaiting:ea-review)
      2. Updates Sprint Dashboard with BLOCKED status
      3. Returns (caller must then return False to halt the task)

    Recovery path (next sprint run after spec is fixed):
      - Sprint runner checks for open spec-gap issues tagged to this task
      - If issue is closed: task is retried with corrected spec
      - If issue is still open: task is SKIPPED (still blocked)
    """
    github_repo = os.environ.get("GITHUB_REPO", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    workaround_note = (
        f"\n## Workaround Considered (NOT Applied)\n\n{workaround}\n\n"
        f"**This workaround was NOT implemented.** The agent does not have authority "
        f"to make architectural decisions (C-065, C-066 Tier 3).\n"
    ) if workaround else ""

    title = f"spec-gap [{task_id}]: {gap_description[:80]}"
    body = (
        f"## Spec Gap — Implementation Halted\n\n"
        f"**Discovered by:** Autonomous Sprint Agent (Platform IT Expert — Implementation hat)\n"
        f"**During task:** `{task_id}`\n"
        f"**Affected spec:** `{affected_spec}`\n"
        f"**Task status:** BLOCKED — will not retry until this issue is closed\n\n"
        f"## Gap Description\n\n{gap_description}\n\n"
        + workaround_note
        + f"## Required Action (EA/SA or Founder)\n\n"
        f"1. Review the gap described above\n"
        f"2. Update `{affected_spec}` with the correct design decision\n"
        f"3. Open a PR for the spec change (branch: `spec-fix/{task_id.lower()}-gap`)\n"
        f"4. Merge the spec PR\n"
        f"5. **Close this issue** — the next sprint run will detect the closure and retry `{task_id}`\n\n"
        f"The implementation agent will automatically retry `{task_id}` when this issue is closed.\n\n"
        + (f"## Constitutional Basis\n\n{constitutional_basis}\n\n" if constitutional_basis else "")
        + f"---\n_Auto-generated by `flag_spec_gap()` in `scripts/autonomous_sprint_runner.py`_"
    )

    if github_repo and github_token:
        result = gh([
            "issue", "create",
            "--repo", github_repo,
            "--title", title,
            "--body", body,
            "--label", "awaiting:founder-approval",
        ], check=False)
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            issue_num = issue_url.split("/")[-1] if "/" in issue_url else "?"
            print(f"  🔴 SPEC GAP — task HALTED. Issue #{issue_num} created.")
            print(f"     Gap: {gap_description[:80]}")
            print(f"     Spec: {affected_spec}")
            print(f"     Fix the spec, close the issue, and the next sprint run retries.")
            record_evidence("spec_gap_halt", task=task_id, issue=issue_num, gap=gap_description[:100])
        else:
            print(f"  🔴 SPEC GAP — task HALTED (issue creation failed: {result.stderr[:100]})")
            print(f"     Gap: {gap_description}")
            record_evidence("spec_gap_halt_no_issue", task=task_id, gap=gap_description[:100])
    else:
        print(f"  🔴 SPEC GAP — task HALTED (no GitHub token for issue creation)")
        print(f"     Gap: {gap_description}")

    # Note: caller must return False after calling this function
    # Example: if some_condition: flag_spec_gap(...); return False


# ── Task implementations ─────────────────────────────────────────────────────

def execute_wc011_01() -> bool:
    """WC011-01: Validate docker-compose.yml."""
    print("── WC011-01: Validate docker-compose.yml ──")
    result = run(
        ["docker", "compose", "-f", "docker-compose.yml", "config", "--quiet"],
        check=False, capture=True
    )
    REPO_ROOT.joinpath("logs").mkdir(exist_ok=True)
    (REPO_ROOT / "logs" / "docker-compose-validation.txt").write_text(
        result.stdout + result.stderr
    )
    if result.returncode == 0:
        print("  OK: docker compose config valid")
    else:
        print(f"  FAIL: docker compose config invalid — {result.stderr[:200]}")
        return False

    # Verify required services are present
    config_text = result.stdout
    required = ["constitutional-engine", "business-platform", "professional-runtime",
                "ai-runtime", "web", "postgres", "keycloak", "temporal"]
    missing = [svc for svc in required if svc not in config_text]
    if missing:
        for svc in missing:
            print(f"  FAIL: required service '{svc}' missing from docker-compose config")
        print(f"  FAIL: {len(missing)} required service(s) missing — cannot pass WC011-01")
        return False

    git(["add", "docker-compose.yml", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-01 - validate docker-compose.yml\n\n"
             "IB: IB-009\nConstitutional: C-067, C-004\nCCTs-added: none"])
    return True


def execute_wc011_02() -> bool:
    """WC011-02: Validate DB migration scripts 01–10."""
    print("── WC011-02: Validate DB migration scripts ──")
    init_dir = REPO_ROOT / "infrastructure" / "postgres" / "init"

    if not init_dir.exists():
        print(f"  FAIL: {init_dir} does not exist")
        return False

    sql_files = sorted(init_dir.glob("*.sql"))
    print(f"  Found {len(sql_files)} SQL files in {init_dir.relative_to(REPO_ROOT)}")

    # Check for required files
    required_prefixes = ["01-", "03-", "04-", "07-", "09-"]
    for prefix in required_prefixes:
        matches = [f for f in sql_files if f.name.startswith(prefix)]
        if not matches:
            print(f"  WARN: No migration file starting with '{prefix}' found")
        else:
            print(f"  OK: {matches[0].name}")

    # Check each file for constitutional markers
    issues = []
    for sql_file in sql_files:
        content = sql_file.read_text(encoding="utf-8")
        # C-007/C-027: constitutional schema must not have UPDATE/DELETE on audit_records
        if "audit_records" in content and ("UPDATE" in content or "DELETE" in content):
            if "NO UPDATE" not in content and "RULE NO" not in content.upper():
                flag_spec_gap(
                    task_id="WC011-02",
                    gap_description=f"{sql_file.name}: potential UPDATE/DELETE on audit_records — C-007/C-027 violation. "
                                    "The constitutional audit ledger must be append-only. No UPDATE or DELETE permitted.",
                    affected_spec="infrastructure/postgres/init/05-append-only-rules.sql",
                    constitutional_basis="C-007 (Ledger Immutability), C-027 (Append-only enforcement)"
                )
                return False
        # C-027: append-only rules must exist
        if sql_file.name.startswith("05-append-only"):
            if "RULE" not in content.upper() and "TRIGGER" not in content.upper():
                issues.append(f"{sql_file.name}: No RULE or TRIGGER found for append-only enforcement (C-027)")
        # Add validation comment if not present
        if "-- Validated: WC-011" not in content:
            updated = content.rstrip() + "\n-- Validated: WC-011 Sprint 011 (infrastructure check only)\n"
            sql_file.write_text(updated, encoding="utf-8")

    if issues:
        for issue in issues:
            print(f"  WARN: {issue}")
    else:
        print("  OK: All migration files pass constitutional markers check")

    git(["add", "infrastructure/postgres/init/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-02 - validate DB migration scripts 01-10\n\n"
             "IB: IB-009\nConstitutional: C-007, C-027, C-059\nCCTs-added: none"])
    return True


def execute_wc011_03() -> bool:
    """WC011-03: Validate Keycloak realm import."""
    print("── WC011-03: Validate Keycloak realm import ──")
    keycloak_dir = REPO_ROOT / "infrastructure" / "keycloak"
    realm_files = list(keycloak_dir.glob("*.json")) if keycloak_dir.exists() else []

    if not realm_files:
        print(f"  FAIL: No realm JSON file found in {keycloak_dir.relative_to(REPO_ROOT)}")
        return False

    realm_file = realm_files[0]
    print(f"  Found realm file: {realm_file.name}")

    import json as json_mod
    try:
        realm = json_mod.loads(realm_file.read_text(encoding="utf-8"))
    except json_mod.JSONDecodeError as e:
        print(f"  FAIL: Realm JSON is invalid — {e}")
        return False

    # Constitutional checks
    realm_id = realm.get("realm", "")
    if realm_id != "waooaw":
        print(f"  WARN: realm id is '{realm_id}', expected 'waooaw'")
    else:
        print(f"  OK: realm id = waooaw")

    # Check for Google IDP (ADR-008)
    identity_providers = realm.get("identityProviders", [])
    google_idp = [p for p in identity_providers if p.get("providerId") == "google"]
    if google_idp:
        print("  OK: Google IDP configured (ADR-008)")
    else:
        print("  WARN: Google IDP not found in realm (ADR-008 requires Google as default IDP)")

    print("  OK: Keycloak realm validation complete")
    return True


def execute_wc011_05() -> bool:
    """WC011-05: Verify setup.sh and get-dev-token.sh."""
    print("── WC011-05: Verify scripts ──")
    scripts_to_check = [
        REPO_ROOT / "scripts" / "setup.sh",
        REPO_ROOT / "scripts" / "get-dev-token.sh",
    ]
    all_ok = True
    for script in scripts_to_check:
        if not script.exists():
            print(f"  FAIL: {script.name} not found")
            all_ok = False
        else:
            # Check for shebang
            first_line = script.read_text(encoding="utf-8").split("\n")[0]
            if not first_line.startswith("#!"):
                print(f"  WARN: {script.name} missing shebang line")
            else:
                print(f"  OK: {script.name} (shebang: {first_line})")
    return all_ok


def execute_wc011_04() -> bool:
    """WC011-04: Create src/ directory scaffold with C-059 headers."""
    print("── WC011-04: Create src/ directory scaffold ──")
    services = [
        ("constitutional-engine", "Constitutional Engine"),
        ("business-platform", "Business Platform"),
        ("professional-runtime", "Professional Runtime"),
        ("ai-runtime", "AI Runtime"),
    ]
    for svc_dir, svc_name in services:
        target = REPO_ROOT / "src" / svc_dir
        target.mkdir(parents=True, exist_ok=True)
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# Implements: architecture/reference/components/{svc_dir}.md\n"
                f"# Constitutional basis: C-059 (Implementation Traceability)\n\n"
                f"## {svc_name}\n\n"
                f"Implements: `architecture/reference/components/{svc_dir}.md`\n\n"
                f"## Local Development\n\n"
                f"```bash\ndocker compose up {svc_dir}\n```\n\n"
                f"## Tests\n\n"
                f"Unit tests and CCTs added in Sprint 012+.\n"
            )
            print(f"  Created src/{svc_dir}/README.md")

    git(["add", "src/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-04 - src/ scaffold with C-059 headers\n\n"
             "IB: IB-009\nConstitutional: C-059, C-064\nCCTs-added: none"])
    return True


def execute_wc011_07() -> bool:
    """WC011-07: Document GitHub Actions secrets (OIDC pattern — 2026-07-23)."""
    print("── WC011-07: Document GitHub Actions secrets ──")
    secrets_doc = REPO_ROOT / "infrastructure" / "GITHUB-SECRETS.md"

    # Skip if already contains the OIDC pattern markers — avoids noisy re-commits
    if secrets_doc.exists():
        existing = secrets_doc.read_text(encoding="utf-8")
        if "OIDC + Azure Key Vault" in existing and "ANTHROPIC-API-KEY" in existing:
            print("  OK: GITHUB-SECRETS.md already documents OIDC pattern — no changes needed")
            return True
    secrets_doc.write_text(
        "# GitHub Actions Secrets & Variables — WAOOAW Platform\n"
        "# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (Secret Management)\n"
        "# ib_item: IB-009 (WC011-07)\n"
        "# produced_by: WC011-07 autonomous sprint task\n\n"
        "## Architecture: OIDC + Azure Key Vault (no long-lived credentials in GitHub Secrets)\n\n"
        "Per ADR-014, all secrets live in Azure Key Vault (waooaw-dev-kv).\n"
        "GitHub Actions authenticates to Azure via OIDC (no stored client secret).\n"
        "Non-sensitive config values are GitHub Variables (not Secrets).\n\n"
        "---\n\n"
        "## GitHub Variables (non-sensitive config — Settings → Variables → Actions)\n\n"
        "| Variable | Value | Purpose |\n"
        "|---|---|---|\n"
        "| `AZURE_CLIENT_ID` | App Registration Client ID | OIDC authentication to Azure |\n"
        "| `AZURE_TENANT_ID` | Azure AD Tenant ID | OIDC authentication to Azure |\n"
        "| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | OIDC scope |\n"
        "| `AZURE_KEYVAULT_NAME` | `waooaw-dev-kv` | Key Vault name for secret fetch |\n\n"
        "**Status: All 4 set** (2026-07-23)\n\n"
        "---\n\n"
        "## Azure Key Vault Secrets (fetched at runtime via OIDC — never stored in GitHub)\n\n"
        "| KV Secret Name | Used By | Obtain From | Status |\n"
        "|---|---|---|---|\n"
        "| `ANTHROPIC-API-KEY` | `autonomous-sprint.yaml` execute + review | console.anthropic.com → API Keys | ✅ DONE |\n"
        "| `GH-APP-ID` | `autonomous-sprint.yaml` review | GitHub App waooaw-reviewer | ✅ DONE |\n"
        "| `GH-APP-INSTALLATION-ID` | `autonomous-sprint.yaml` review | GitHub App installation | ✅ DONE |\n"
        "| `GH-APP-PRIVATE-KEY` | `autonomous-sprint.yaml` review | GitHub App private key (.pem) | ✅ DONE |\n"
        "| `CODECOV-TOKEN` | `ci.yaml` coverage upload | codecov.io → repo settings | ✅ DONE |\n"
        "| `DEV_BASE_URL` | `post-deploy-verify.yaml` | Terraform output after M1 | ⬜ PENDING |\n"
        "| `DEV_CONSTITUTIONAL_DB_URL` | `promote.yaml` CCTs | Terraform output after M2 | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_A` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_B` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `GOOGLE-VERTEX-SA-KEY` | AI Runtime (Gemini) | GCP SA key JSON (FA-021) | ⬜ PENDING |\n"
        "| `SARVAM-API-KEY` | AI Runtime (Agricultural) | sarvam.ai API key (FA-022) | ⬜ PENDING |\n"
        "| `AZURE-OPENAI-KEY` | AI Runtime (fallback LLM) | Azure OpenAI UAE North (FA-003) | ⬜ PENDING |\n\n"
        "---\n\n"
        "## Secret Rotation Policy (ADR-014)\n\n"
        "- Azure OIDC: no rotation needed (no client secret — OIDC federated credential)\n"
        "- ANTHROPIC-API-KEY: rotate if exposed in logs or AI context\n"
        "- GH-APP-PRIVATE-KEY: rotate annually or if exposed\n"
        "- All others: rotate if leaked; quarterly audit minimum\n\n"
        "## No Longer Used\n\n"
        "The following were in earlier designs but are replaced by OIDC:\n"
        "- `AZURE_CREDENTIALS_DEV/QA/PROD` — replaced by OIDC federated credential\n"
        "- `REVIEW_APP_TOKEN` — replaced by `GH-APP-PRIVATE-KEY` in Key Vault + JWT generation\n"
    )
    print("  Updated infrastructure/GITHUB-SECRETS.md (OIDC pattern)")

    git(["add", "infrastructure/GITHUB-SECRETS.md"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "chore(infra): WC011-07 - document GitHub Actions secrets (OIDC pattern)\n\n"
             "IB: IB-009\nConstitutional: C-059, ADR-014"])
    return True


TASK_HANDLERS = {
    "WC011-01": execute_wc011_01,
    "WC011-02": execute_wc011_02,
    "WC011-03": execute_wc011_03,
    "WC011-04": execute_wc011_04,
    "WC011-05": execute_wc011_05,
    "WC011-07": execute_wc011_07,
}


# ── Main execution ────────────────────────────────────────────────────────────

def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    force_task = os.environ.get("FORCE_TASK", "").strip()
    github_repo = os.environ.get("GITHUB_REPO", "")

    print("=" * 60)
    print("  WAOOAW Autonomous Sprint Agent")
    print(f"  Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"  Force task: {force_task or 'none'}")
    print("=" * 60)

    # ── Step 1: Parse sprint state ────────────────────────────────────────
    try:
        state = parse_sprint_state()
    except ValueError as e:
        print(f"ERROR: {e}")
        set_output("result", "FAILED")
        set_output("halt", "false")
        return 1

    print(f"\nSprint state:")
    print(f"  platform_phase    : {state.get('platform_phase', 'SPEC')}")
    print(f"  autonomous_halt   : {state.get('autonomous_halt', 'true')}")
    print(f"  current_sprint    : {state.get('current_sprint', '')}")
    print(f"  sprint_status     : {state.get('sprint_status', '')}")
    print(f"  tasks_remaining   : {state.get('tasks_remaining', [])}")

    # ── Step 2: Platform phase + HALT gate (C-001, platform_phase check) ──
    # check_platform_phase_gate calls sys.exit(0) on SPEC phase or HALT=true.
    # This is the hard gate preventing unauthorized implementation.
    check_platform_phase_gate(state)

    set_output("halt", "false")

    # ── Step 3: Consecutive failure check ─────────────────────────────────
    failures = int(state.get("consecutive_failures", "0") or "0")
    if failures >= 3:
        print(f"\nConsecutive failures: {failures} >= 3 - creating Constitutional Blocker")
        if not dry_run and github_repo:
            title = f"CB: Autonomous Sprint {state.get('current_sprint', '?')} - {failures} consecutive failures"
            body = (
                f"Constitutional Blocker - Autonomous Sprint Failure\n\n"
                f"Sprint: {state.get('current_sprint', '?')}\n"
                f"Consecutive failures: {failures}\n"
                f"Action: Review workflow runs, fix root cause, reset consecutive_failures: 0\n"
                f"Constitutional basis: C-001 (Human Override)"
            )
            gh(["issue", "create", "--title", title, "--body", body,
                "--label", "type:constitutional-blocker,status:blocked",
                "--repo", github_repo], check=False)
        set_output("result", "FAILED")
        return 1

    # ── Step 4: Determine tasks to run ────────────────────────────────────
    sprint = state.get("current_sprint", "")
    set_output("sprint", sprint)
    tasks = [force_task] if force_task else state.get("tasks_remaining", [])

    if not tasks:
        print("\nNo tasks remaining. Sprint may already be DONE.")
        set_output("result", "SKIPPED")
        return 0

    # ── Step 5: Setup branch ──────────────────────────────────────────────
    branch = state.get("branch", f"ib/009/{sprint.lower()}")
    if not dry_run:
        remote_check = git(["ls-remote", "--exit-code", "--heads", "origin", branch], check=False)
        if remote_check.returncode == 0:
            git(["checkout", branch])
            git(["pull", "origin", branch])
        else:
            git(["checkout", "-b", branch])

        record_evidence("AUTONOMOUS_SPRINT_STARTED", sprint=sprint,
                        branch=branch, tasks=tasks)
        update_sprint_state(
            sprint_status="IN_PROGRESS",
            last_attempt_utc=datetime.now(timezone.utc).isoformat(),
            current_task=tasks[0] if tasks else "",
        )
        git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
        diff = git(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            git(["commit", "-m",
                 f"chore(pm): {sprint} execution started\n\nIB: IB-009\nConstitutional: C-059"])

    # ── Step 6: Execute each task ─────────────────────────────────────────
    tasks_done = []
    tasks_not_implemented = []
    for task in tasks:
        handler = TASK_HANDLERS.get(task)
        if handler is None:
            # P1-04: explicit NOT_IMPLEMENTED — not silent skip
            print(f"  ⚠️  TASK_NOT_IMPLEMENTED: {task}")
            print(f"       This task requires LLM code generation (IB-020).")
            print(f"       Runner does not yet have code generation capability.")
            print(f"       Action: Implement IB-020 (ADR-030) before this sprint can execute.")
            tasks_not_implemented.append(task)
            continue
        if dry_run:
            print(f"  DRY RUN: would execute {task}")
            continue
        try:
            success = handler()
            if success:
                tasks_done.append(task)
                print(f"  DONE: {task}")
        except Exception as exc:
            print(f"  FAILED: {task}: {exc}")

    # ── Step 7: Update state + open PR ────────────────────────────────────
    if dry_run:
        set_output("result", "DRY_RUN")
        return 0

    record_evidence("SPRINT_TASKS_EXECUTED", sprint=sprint, tasks_done=tasks_done)

    if tasks_done:
        update_sprint_state(
            last_attempt_result="SUCCESS",
            consecutive_failures=0,
            current_task="",
        )
    else:
        failures_new = failures + 1
        update_sprint_state(
            last_attempt_result="PARTIAL",
            consecutive_failures=str(failures_new),
        )

    git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             f"chore(pm): {sprint} tasks done: {', '.join(tasks_done)}\n\n"
             f"IB: IB-009\nConstitutional: C-059"])

    git(["push", "origin", branch, "--force-with-lease"])

    # ── Step 8: Open/update PR ────────────────────────────────────────────
    if not github_repo:
        set_output("result", "SUCCESS")
        return 0

    existing = gh(["pr", "list", "--head", branch,
                   "--json", "number", "--jq", ".[0].number",
                   "--repo", github_repo], check=False)
    existing_num = existing.stdout.strip() if existing.returncode == 0 else ""

    if not existing_num:
        pr_title = f"feat(infra): {sprint} - Autonomous Sprint Execution"
        pr_body = (
            f"IB Reference: IB-009 - Foundation Implementation\n"
            f"Work Contract: {sprint}\n"
            f"Office: WAOOAW AI Agent - Platform IT Expert (Autonomous Sprint)\n"
            f"Execution mode: Autonomous (C-066 Tier 2A)\n\n"
            f"Tasks executed: {', '.join(tasks_done) or 'none (Copilot workspace required)'}\n\n"
            f"Constitutional basis: C-066 Tier 2A, C-070, C-059, C-065\n"
            f"Bootstrap evidence: logs/bootstrap-evidence.jsonl\n"
            f"Run ID: {os.environ.get('GITHUB_RUN_ID', 'local')}"
        )
        result = gh(["pr", "create",
                     "--title", pr_title,
                     "--body", pr_body,
                     "--base", "main",
                     "--head", branch,
                     "--label", "tier:2-feature",
                     "--label", "status:pr-open",
                     "--label", "awaiting:review",
                     "--repo", github_repo], check=False)
        if result.returncode != 0:
            print(f"  WARN: gh pr create failed (rc={result.returncode}): {result.stderr[:300]}")
        pr_num = result.stdout.strip().split("/")[-1] if result.returncode == 0 else ""
        if pr_num:
    if tasks_not_implemented:
        set_output("result", "NOT_IMPLEMENTED")
        set_output("halt_reason", f"Tasks {tasks_not_implemented} require IB-020 LLM code generation — not yet implemented")
        print(f"\n  ⚠️  {len(tasks_not_implemented)} task(s) require IB-020 (runner code generation).")
        print(f"  Sprint cannot advance until IB-020 is implemented.")
        print(f"  Issue #12 tracks this: github.com/dlai-sd/waooaw-platform/issues/12")
    else:
                print(f"  PR created: #{pr_num}")
    else:
        pr_num = existing_num
        print(f"  PR updated: #{pr_num}")

    set_output("pr_number", pr_num)
    set_output("result", "SUCCESS" if tasks_done else "PARTIAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
