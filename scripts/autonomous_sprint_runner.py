#!/usr/bin/env python3
"""
autonomous_sprint_runner.py

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Skill 8 — SDLC Execution)
# constitutional_basis: C-023 (Evidence First), C-041 (ValidateAction), C-059 (Traceability),
#                       C-065 (SDLC Separation — Author hat), C-066 Tier 2A (autonomous execution),
#                       C-070 (Constitutional DNA — all 3 instincts apply to this agent),
#                       C-007/C-027 (Append-only enforcement — validated in WC011-02),
#                       C-077 (Dev Tooling Cost Ceiling ₹5,000/month — ADR-030)
# ib_item: IB-009, IB-020
# office: Platform IT Expert — Implementation hat
# amended: 2026-07-23 — IB-020 ADR-030: call_llm() + parse_llm_files() implemented

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

# ── ADR-030: File write boundary enforcement (C-059 + C-065) ─────────────────
ALLOWED_WRITE_ROOTS = [
    "src/",
    "tests/",
    "infrastructure/postgres/",
    "infrastructure/keycloak/",
    "logs/",
]

# ADR-030: Constitutional system prompt for all code generation tasks
CONSTITUTIONAL_SYSTEM_PROMPT = """You are WAOOAW AI Agent — Platform IT Expert (Implementation hat).
You generate production-ready code for the WAOOAW platform under constitutional governance.

Constitutional obligations (non-negotiable):
- C-059: Every source file must carry a header: # Implements: <spec-path> and # constitutional_basis: <claims>
- C-073: Every function implementing a constitutional obligation carries an annotation comment
- C-076: Every service must have ≥90% unit test coverage. Write tests alongside implementation.
- C-065: You are the Author. You do not approve or merge your own work.

Output format — respond ONLY with XML file blocks:
<file path="src/service-name/FileName.ext">
file content here
</file>

Rules:
- Paths must start with one of: src/, tests/, infrastructure/postgres/, infrastructure/keycloak/
- Never output paths starting with: constitution/, adr/, architecture/, knowledge/, standards/
- Every .cs file: nullable enabled, structured logging (ILogger<T>), OTel spans
- Every .py file: type hints, ruff-compliant, async FastAPI patterns
- Include unit tests in a separate <file path="tests/..."> block
- If a design decision is unclear, add a comment: # DESIGN_QUESTION: <question>
  (these will be flagged as spec gaps for EA review)

EXTEND-NOT-REPLACE RULE (critical — read the BRANCH CONTEXT section before writing ANY file):
- The sprint branch may already contain files from earlier tasks in this sprint.
- The BRANCH CONTEXT section below lists EVERY file already on the branch.
- For files listed in BRANCH CONTEXT: you MAY output an updated version that EXTENDS the existing
  implementation (e.g. adding a new method to ConstitutionalEngineService.cs that was stubbed).
  You MUST NOT change existing correct code, only add to it.
- NEVER recreate Data layer entities, DbContexts, or .csproj files that already exist.
  Creating a duplicate class causes CS0101 (namespace already contains definition) and fails the build.
- If a file you would normally generate already exists and needs NO changes, OMIT it from your output.

PROJECT STRUCTURE RULES (mandatory — violating these causes build failures):

.NET services (src/{service}/ and tests/{service}.Tests/):
  EXACTLY ONE .csproj in src/{service}/ — named {service}.csproj (lowercase-hyphenated)
  EXACTLY ONE .csproj in tests/{service}.Tests/ — named {service}.Tests.csproj
  NEVER create a second .csproj alongside an existing one (causes MSB1050 build error)
  NEVER create a .csproj inside a subdirectory of tests/
  CCT tests: tests/{service}.Tests/{Feature}/CCT_{ID}_*Tests.cs
  Example: src/constitutional-engine/constitutional-engine.csproj
           tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj

Python services (src/{service}/ and tests/{service}/):
  pyproject.toml at src/{service}/pyproject.toml — ONE per service
  Tests at tests/{service}/test_{module}.py (pytest convention)
  NEVER create a setup.py alongside a pyproject.toml

TypeScript/Next.js (web/ or src/{service}/):
  package.json at the root of the service directory — ONE per service
  tsconfig.json at the same level as package.json
  NEVER create a nested package.json in a subdirectory

PYTHON PACKAGE RULES (critical — prevents import errors and build failures):
  Temporal: import from 'temporalio' (1.x stable) — NOT 'temporal-sdk', 'temporal-python'
  Vertex AI: 'from google.cloud import aiplatform' — NOT 'import vertexai' (different SDK)
  Sarvam AI: NO Python SDK exists — use httpx for REST calls only — NEVER 'import sarvam'
  AI4Bharat IndicNER: use transformers.pipeline('ner', model='ai4bharat/IndicNER') — NO 'ai4bharat' PyPI package
  Gemini model name: 'gemini-2.0-flash' — NOT 'gemini-pro' (deprecated)
"""


def get_branch_context(service_dir: str = "src/constitutional-engine") -> str:
    """
    Scan the current sprint branch for files already committed from prior tasks.
    Returns a formatted BRANCH CONTEXT block injected into every LLM prompt.

    This implements the RAG insight: the LLM must know the current state of the
    branch before generating new code. Without this, Task 2 regenerates Task 1's
    files, causing duplicate class definitions and build failures.

    C-083 (Emit-Transport-Listen): the branch state IS the signal from prior tasks.
    C-085 (Idempotency): the LLM must check existing state before acting.
    """
    try:
        # Find all code files added/modified on this branch vs main
        result = run(["git", "diff", "--name-only", "origin/main...HEAD"], check=False, capture=True)
        if result.returncode != 0:
            return ""

        branch_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        code_files = [f for f in branch_files if f.endswith((".cs", ".py", ".ts", ".proto", ".csproj"))]

        if not code_files:
            return ""

        lines = [
            "\n\n# ═══ BRANCH CONTEXT — EXISTING FILES FROM PRIOR TASKS ═══",
            "# These files are ALREADY on the sprint branch from completed tasks.",
            "# Apply EXTEND-NOT-REPLACE rule: do NOT recreate these. Read them to understand",
            "# existing types, namespaces, and interfaces before writing new code.\n",
        ]

        for file_path in sorted(code_files):
            full_path = REPO_ROOT / file_path
            if not full_path.is_file():
                continue

            content = full_path.read_text(encoding="utf-8", errors="replace")

            # For .csproj and appsettings: just list them (don't regenerate)
            if file_path.endswith((".csproj", ".json", ".proto")):
                lines.append(f"## EXISTING (DO NOT REGENERATE): {file_path}")
                if file_path.endswith(".csproj"):
                    # Include package references so LLM uses correct types
                    lines.append(content[:800])
                lines.append("")
                continue

            # For .cs source files: include namespace, class declaration, and method signatures
            # This tells the LLM what types already exist without full file content
            important_lines = []
            for line in content.splitlines():
                stripped = line.strip()
                if any(stripped.startswith(kw) for kw in (
                    "namespace ", "public ", "internal ", "protected ", "private ",
                    "// Implements:", "// constitutional_basis:", "interface ", "record ",
                    "sealed class", "abstract class", "static class",
                )):
                    important_lines.append(line)
                    if len(important_lines) > 30:  # cap per file
                        break

            if important_lines:
                lines.append(f"## EXISTING (may EXTEND but not duplicate): {file_path}")
                lines.append("\n".join(important_lines[:30]))
                lines.append("")

        if len(lines) <= 4:  # only header, no files
            return ""

        lines.append("# ═══ END BRANCH CONTEXT ═══\n")
        return "\n".join(lines)

    except Exception as e:
        print(f"  WARN: get_branch_context failed: {e}")
        return ""


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


# ── ADR-030: LLM code generation functions ────────────────────────────────────

def call_llm(task_id: str, task_description: str, spec_content: str,
             constitutional_check: str, model_hint: str = "reasoning",
             max_tokens: int = 10000) -> str | None:
    """
    Call Claude Sonnet 4.6 to generate code for a sprint task.
    Returns the raw LLM response string, or None on failure.

    constitutional_basis: ADR-030 (code generation protocol), C-077 (cost ceiling)
    ib_item: IB-020
    """
    if model_hint not in ("reasoning", "auto"):
        return None  # model_hint: none — no LLM needed

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  WARN: ANTHROPIC_API_KEY not set — cannot call LLM for {task_id}")
        return None

    try:
        import urllib.request
        import json as json_mod

        user_prompt = (
            f"Task: {task_id} — {task_description}\n\n"
            f"Spec context:\n{spec_content}\n\n"
            f"Constitutional check (must pass):\n{constitutional_check}\n\n"
            f"Generate the implementation files now. "
            f"Use <file path=\"...\"> blocks for each file. "
            f"Include unit tests in tests/ directory."
        )

        # ADR-030: Claude Sonnet 4.6 authorized by Yogesh 2026-07-23 for all planned sprints (C-077)
        # API alias follows pattern: claude-sonnet-{major}-{minor}
        # Fallback: if 4-6 alias not yet published, claude-sonnet-4-5 is acceptable
        model_id = os.environ.get("SPRINT_LLM_MODEL", "claude-sonnet-4-6")
        payload = {
            "model": model_id,
            "max_tokens": max_tokens,  # Per-task: scaffold=16000, implementation=10000 (C-077 token floor)
            "temperature": 0,
            "system": CONSTITUTIONAL_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json_mod.dumps(payload).encode(),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        # Timeout: Claude Sonnet generates ~50 tokens/sec.
        # Allow 3× the expected generation time as safety margin.
        # 16000 tokens → 960s expected → 600s floor (API is faster in practice)
        api_timeout = max(600, (max_tokens // 50) * 3)
        with urllib.request.urlopen(req, timeout=api_timeout) as resp:
            result = json_mod.loads(resp.read())
            content = result.get("content", [])
            text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
            tokens_in = result.get("usage", {}).get("input_tokens", 0)
            tokens_out = result.get("usage", {}).get("output_tokens", 0)
            print(f"  LLM: {task_id} → {tokens_in} in / {tokens_out} out tokens")
            record_evidence("llm_call", task=task_id, tokens_in=tokens_in, tokens_out=tokens_out)
            return text
    except urllib.error.HTTPError as e:
        body = e.read(300).decode("utf-8", errors="replace")
        if e.code == 429:
            print(f"  INFRA: HTTP 429 rate limit for {task_id} — caller should retry with backoff")
            raise RuntimeError(f"RATE_LIMIT:{e.code}:{body}") from e
        elif e.code >= 500:
            print(f"  INFRA: HTTP {e.code} server error for {task_id}")
            raise RuntimeError(f"API_SERVER_ERROR:{e.code}:{body}") from e
        else:
            print(f"  WARN: HTTP {e.code} for {task_id}: {body}")
            return None
    except TimeoutError:
        print(f"  INFRA: API read timed out after {api_timeout}s for {task_id}")
        raise RuntimeError(f"API_TIMEOUT:{api_timeout}s") from None
    except Exception as e:
        err = str(e)
        if "timed out" in err.lower() or "timeout" in err.lower():
            print(f"  INFRA: API read timed out for {task_id}: {err}")
            raise RuntimeError(f"API_TIMEOUT:{err}") from e
        print(f"  WARN: LLM call failed for {task_id}: {err}")
        return None


def parse_llm_files(response: str) -> dict[str, str]:
    """
    Parse <file path="...">content</file> blocks from LLM response.
    Returns dict of {relative_path: content}.
    Enforces ADR-030 write boundary (ALLOWED_WRITE_ROOTS).
    """
    files: dict[str, str] = {}
    pattern = re.compile(r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>', re.DOTALL)
    for match in pattern.finditer(response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        # ADR-030: enforce write boundary
        if not any(path.startswith(root) for root in ALLOWED_WRITE_ROOTS):
            print(f"  WARN: LLM attempted to write outside boundary: {path} — skipped")
            continue
        # Check for design questions that need spec clarification
        if "DESIGN_QUESTION:" in content:
            questions = re.findall(r"DESIGN_QUESTION: (.+)", content)
            for q in questions:
                print(f"  ⚠️  Design question in {path}: {q}")
        files[path] = content
    return files


def write_llm_files(files: dict[str, str]) -> list[str]:
    """Write parsed files to disk. Returns list of written paths."""
    written = []
    for rel_path, content in files.items():
        abs_path = REPO_ROOT / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        written.append(rel_path)
        print(f"  Written: {rel_path} ({len(content)} chars)")
    return written


def validate_written_files(written: list[str]) -> tuple[bool, str]:
    """Run validation appropriate to file type. Returns (ok, error_text)."""
    py_files = [f for f in written if f.endswith(".py")]
    cs_files = [f for f in written if f.endswith(".cs")]
    ok = True
    errors: list[str] = []

    for f in py_files:
        result = run(["python3", "-m", "py_compile", f], check=False, capture=True)
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            print(f"  FAIL: {f} syntax error: {msg[:200]}")
            errors.append(f"{f}: {msg[:300]}")
            ok = False
        else:
            print(f"  ✅ Python syntax OK: {f}")

    if cs_files:
        # Find the csproj dir: src/<service>/ from the first .cs file
        csproj_dirs: set[str] = set()
        for f in cs_files:
            parts = Path(f).parts
            if len(parts) > 1:
                csproj_dirs.add(str(REPO_ROOT / parts[0] / parts[1]))
        for csproj_dir in csproj_dirs:
            # Check .csproj exists — if not, that's an explicit error for the retry context
            csproj_files = list(Path(csproj_dir).glob("*.csproj")) if Path(csproj_dir).exists() else []
            if not csproj_files:
                msg = (f"No .csproj file found in {csproj_dir}. "
                       f"You MUST generate the .csproj in src/constitutional-engine/ (not any other directory). "
                       f"Write ALL files to src/constitutional-engine/ only.")
                print(f"  FAIL: {msg}")
                errors.append(msg)
                ok = False
                continue
            # Pick specific .csproj to avoid MSB1050 (multiple .csproj in dir)
            if len(csproj_files) > 1:
                canonical = [f for f in csproj_files if "-" in f.name]
                build_target = str(canonical[0]) if canonical else str(csproj_files[0])
                print(f"  WARN: {len(csproj_files)} .csproj found — building {Path(build_target).name}")
            else:
                build_target = str(csproj_files[0])
            result = run(["dotnet", "build", build_target, "--nologo", "-v", "quiet"],
                        check=False, capture=True)
            if result.returncode != 0:
                # dotnet quiet mode sends errors to stdout, not stderr
                build_output = (result.stdout.strip() or result.stderr.strip())[:600]
                print(f"  FAIL: dotnet build in {csproj_dir}:\n{build_output}")
                errors.append(f"dotnet build {csproj_dir}:\n{build_output}")
                ok = False
            else:
                print(f"  ✅ .NET build OK: {csproj_dir}")
    return ok, "\n".join(errors)


def execute_with_llm(task_id: str, task_description: str, spec_sections: dict,
                     constitutional_check: str, model_hint: str = "reasoning",
                     max_tokens: int = 10000) -> bool:
    """
    Execute a code generation task using Claude (ADR-030 protocol).
    Implements the 3-attempt retry loop with validation.
    Returns True on success, False (with flag_spec_gap) on exhausted retries.

    constitutional_basis: ADR-030, C-059, C-076, C-077
    ib_item: IB-020
    """
    # Build spec content from sections
    spec_lines = [f"# Spec context for {task_id}"]
    for file_path, section in spec_sections.items():
        full_path = REPO_ROOT / file_path
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if section == "full" or len(content) < 6000:
                spec_lines.append(f"\n## {file_path}\n{content[:4000]}")
            else:
                spec_lines.append(f"\n## {file_path} (section: {section})\n[load section '{section}' from this file]")
    spec_content = "\n".join(spec_lines)

    # RAG: inject branch context — tell LLM what prior tasks already generated.
    # C-083 (Emit-Transport-Listen): prior task outputs are signals for this task.
    # C-085 (Idempotency): LLM must not regenerate files that already exist.
    branch_context = get_branch_context()
    if branch_context:
        spec_content = spec_content + branch_context
        print(f"  Branch context injected ({len(branch_context.splitlines())} lines) — EXTEND-NOT-REPLACE active")

    failure_context = ""
    infra_failures = 0  # count of transient API failures (timeout, rate limit, server error)
    for attempt in range(1, 4):
        print(f"\n── {task_id} (attempt {attempt}/3) ──")

        prompt_with_context = spec_content
        if failure_context:
            prompt_with_context += f"\n\n# Previous attempt failed:\n{failure_context}\nFix the issues above."

        try:
            response = call_llm(task_id, task_description, prompt_with_context,
                               constitutional_check, model_hint, max_tokens)
        except RuntimeError as infra_err:
            err_str = str(infra_err)
            infra_failures += 1
            if err_str.startswith("API_TIMEOUT"):
                print(f"  INFRA_TIMEOUT on attempt {attempt} — NOT a spec gap. Retrying in 30s.")
            elif err_str.startswith("RATE_LIMIT"):
                print(f"  RATE_LIMIT on attempt {attempt} — backing off 60s before retry.")
                import time; time.sleep(60)
            elif err_str.startswith("API_SERVER_ERROR"):
                print(f"  API_SERVER_ERROR on attempt {attempt} — retrying in 30s.")
            else:
                print(f"  INFRA_ERROR on attempt {attempt}: {err_str}")
            import time; time.sleep(30)
            continue

        if not response:
            print(f"  LLM call returned no response on attempt {attempt}")
            continue

        files = parse_llm_files(response)
        if not files:
            print(f"  No <file> blocks found in LLM response on attempt {attempt}")
            failure_context = "Response contained no <file path='...'> blocks. Generate file blocks."
            continue

        written = write_llm_files(files)
        ok, build_error = validate_written_files(written)
        if ok:
            # Commit the generated files
            git(["add"] + written, check=False)
            diff = git(["diff", "--cached", "--quiet"], check=False)
            if diff.returncode != 0:
                git(["commit", "-m",
                     f"feat: {task_id} — {task_description}\n\n"
                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
            print(f"  ✅ {task_id} complete ({len(written)} files)")
            # Emit success signal for Constitutional Monitor (C-069)
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SUCCESS", "error_type": None,
                "build_error_snippet": None, "attempts": attempt, "spec_gap_issue": None,
            }
            return True
        else:
            # Pass the ACTUAL build error to Claude on the next attempt
            failure_context = (
                f"Build/syntax validation failed for files: {written}\n"
                f"Exact error output:\n{build_error}"
            )
            print(f"  Validation failed on attempt {attempt} — retrying with failure context")

    # All 3 attempts exhausted — categorize the failure type
    if infra_failures == 3:
        # ALL failures were infrastructure (timeout/rate-limit/server error) — NOT a spec gap
        print(f"  ⚠️  INFRA_FAILURE: {task_id} — all 3 attempts were API failures (timeout/rate-limit).")
        print(f"  This is NOT a spec gap. No issue created. Next cron run will retry automatically.")
        # Signal to main() that this was an infra failure, not a code/spec failure
        _INFRA_ERROR_TASKS.append(task_id)
        # Emit INFRA_ERROR signal for Constitutional Monitor (C-069)
        _MONITOR_SIGNAL["task_results"][task_id] = {
            "result": "INFRA_ERROR", "error_type": "API_TIMEOUT",
            "build_error_snippet": None, "attempts": 3, "spec_gap_issue": None,
        }
        return False
    elif infra_failures > 0:
        # Mixed: some infra failures + some build failures — treat as spec gap but note it
        gap_desc = (f"{task_id} failed after 3 attempts ({infra_failures} API timeouts, "
                    f"{3 - infra_failures} build failures). Last build error: {failure_context[:200]}")
    else:
        gap_desc = f"{task_id} failed validation after 3 LLM attempts. Last error: {failure_context[:300]}"

    flag_spec_gap(
        task_id=task_id,
        gap_description=gap_desc,
        affected_spec=list(spec_sections.keys())[0] if spec_sections else "unknown",
        constitutional_basis="C-059 (Traceability — implementation must match spec), C-076 (Coverage)"
    )
    return False


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
            # Emit SPEC_GAP signal for Constitutional Monitor (C-069)
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SPEC_GAP", "error_type": "BUILD_ERROR",
                "build_error_snippet": gap_description[:200],
                "attempts": 3, "spec_gap_issue": issue_num,
            }
            _MONITOR_SIGNAL["spec_gap_issues"].append(issue_num)
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


def execute_wc012_01() -> bool:
    """
    WC012-01: CE project scaffold — DETERMINISTIC (no LLM call).

    Root cause of 3+ failures: calling Claude to copy reference files produces hallucinations.
    Fix: copy reference files verbatim + write minimal templates. No Claude, no hallucination.

    constitutional_basis: C-059 (Traceability), C-082 (build validation), ADR-001 (gRPC)
    """
    print("── WC012-01: CE project scaffold (DETERMINISTIC) ──")
    service = "constitutional-engine"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / f"{service}.Tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "Protos").mkdir(exist_ok=True)
    (src_dir / "Services").mkdir(exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Copy .csproj verbatim from reference dotfile (C-081) ──────────────
    ref_csproj = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "constitutional-engine.csproj"
    if not ref_csproj.is_file():
        print(f"  ❌ Reference csproj not found: {ref_csproj}")
        return False
    (src_dir / "constitutional-engine.csproj").write_text(ref_csproj.read_text())
    print("  ✅ constitutional-engine.csproj copied from reference dotfile")

    # ── 2. Copy proto verbatim from architecture reference ────────────────────
    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    if not ref_proto.is_file():
        print(f"  ❌ Reference proto not found: {ref_proto}")
        return False
    (src_dir / "Protos" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied from architecture reference")

    # ── 3. Program.cs — minimal template (no OTel hallucination risk) ─────────
    (src_dir / "Program.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry)\n\n"
        "using Waooaw.ConstitutionalEngine.Services;\n\n"
        "var builder = WebApplication.CreateBuilder(args);\n"
        "builder.Services.AddGrpc();\n\n"
        "var app = builder.Build();\n"
        "app.MapGrpcService<ConstitutionalEngineService>();\n"
        "app.Run();\n"
    )
    print("  ✅ Program.cs written from template")

    # ── 4. ConstitutionalEngineService.cs — stub inheriting proto base ─────────
    # All RPCs return default empty responses — stubs only. WC012-02/03/04 fill them.
    (src_dir / "Services" / "ConstitutionalEngineService.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop)\n\n"
        "using Grpc.Core;\n"
        "using Waooaw.ConstitutionalEngine.Grpc;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Services;\n\n"
        "/// <summary>gRPC service stub — full implementation in WC012-02/03/04.</summary>\n"
        "public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase\n"
        "{\n"
        "    public override Task<RecordEvidenceResponse> RecordEvidence(RecordEvidenceRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RecordEvidenceResponse());\n"
        "    public override Task<ValidateActionResponse> ValidateAction(ValidateActionRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new ValidateActionResponse());\n"
        "    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(GrantAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new GrantAuthorityResponse());\n"
        "    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(RevokeAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RevokeAuthorityResponse());\n"
        "    public override Task<EvaluatePolicyResponse> EvaluatePolicy(EvaluatePolicyRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EvaluatePolicyResponse());\n"
        "    public override Task<EmergencyStopResponse> TriggerEmergencyStop(EmergencyStopRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EmergencyStopResponse());\n"
        "}\n"
    )
    print("  ✅ ConstitutionalEngineService.cs stub written from template")

    # ── 5. appsettings files ───────────────────────────────────────────────────
    (src_dir / "appsettings.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Information" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "" },\n'
        '  "Kestrel": { "Endpoints": { "Grpc": { "Url": "http://0.0.0.0:5002", "Protocols": "Http2" } } }\n}\n'
    )
    (src_dir / "appsettings.Development.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Debug" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "Host=localhost;Port=5432;Database=constitutional;Username=constitutional_engine;Password=dev_password_replace_in_prod" }\n}\n'
    )
    print("  ✅ appsettings.json + appsettings.Development.json written")

    # ── 6. Test project .csproj ────────────────────────────────────────────────
    (test_dir / "constitutional-engine.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '    <Nullable>enable</Nullable>\n'
        '    <ImplicitUsings>enable</ImplicitUsings>\n'
        '    <IsPackable>false</IsPackable>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '    <ProjectReference Include="..\\..\\src\\constitutional-engine\\constitutional-engine.csproj" />\n'
        '  </ItemGroup>\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />\n'
        '    <PackageReference Include="xunit" Version="2.9.3" />\n'
        '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '    <PackageReference Include="Moq" Version="4.20.72" />\n'
        '    <PackageReference Include="FluentAssertions" Version="6.12.2" />\n'
        '    <PackageReference Include="coverlet.collector" Version="6.0.4">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    print("  ✅ constitutional-engine.Tests.csproj written")

    # ── 7. Validate build ──────────────────────────────────────────────────────
    build = run(["dotnet", "build", str(src_dir / "constitutional-engine.csproj"),
                 "--nologo", "-v", "quiet"], check=False, capture=True)
    if build.returncode != 0:
        print(f"  ❌ dotnet build FAILED:\n{build.stderr[:500]}")
        # Clean up on failure so next run starts fresh
        import shutil
        for p in [src_dir / "Protos", src_dir / "Services", src_dir / "Program.cs",
                  src_dir / "appsettings.json", src_dir / "appsettings.Development.json",
                  src_dir / "constitutional-engine.csproj", test_dir]:
            if p.is_dir(): shutil.rmtree(p)
            elif p.is_file(): p.unlink()
        return False
    print("  ✅ dotnet build PASSED")

    # ── 8. Commit ──────────────────────────────────────────────────────────────
    git(["add", "src/constitutional-engine/", "tests/constitutional-engine.Tests/"])
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat: WC012-01 — CE project scaffold (.NET 9 gRPC service)\n\n"
             "IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
    print("  ✅ WC012-01 complete (deterministic — no LLM)")
    return True


_INFRA_ERROR_TASKS: list[str] = []  # populated by execute_with_llm when all 3 attempts are API failures

# ── Sprint Monitor signal (C-069: self-improvement loop) ──────────────────────
# Scaffold tasks are EXPLICITLY declared — never inferred from position.
# If WC012-01 fails, all downstream tasks cannot compile. The monitor uses this
# to distinguish CASCADE_PIPELINE_BUG from SPEC_GAP_GENUINE.
SCAFFOLD_TASKS: frozenset[str] = frozenset({
    "WC012-01", "WC013-01", "WC014-01", "WC015-01",
    "WC016-01", "WC017-01", "WC018-01",
})

# Populated during execution — written to sprint-context/monitor-signal.json
# and uploaded as artifact for the Constitutional Monitor job to consume.
_MONITOR_SIGNAL: dict = {
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "sprint": "",
    "scaffold_task": None,     # task ID of the scaffold (if any) in this run
    "scaffold_failed": False,  # True = downstream spec-gap issues are CASCADE bugs
    "task_results": {},        # per-task: result, error_type, snippet, attempts, issue
    "spec_gap_issues": [],     # GitHub issue numbers opened by flag_spec_gap()
    "overall_result": "UNKNOWN",
}

TASK_HANDLERS = {
    "WC011-01": execute_wc011_01,
    "WC011-02": execute_wc011_02,
    "WC011-03": execute_wc011_03,
    "WC011-04": execute_wc011_04,
    "WC011-05": execute_wc011_05,
    "WC011-07": execute_wc011_07,
    # WC-012: Constitutional Engine skeleton
    # WC012-01 is DETERMINISTIC — copies reference files, no Claude call.
    # Root cause of 3 prior failures: Claude hallucinated API methods when asked to copy known-good files.
    "WC012-01": execute_wc012_01,
    "WC012-02": lambda: execute_with_llm(
        "WC012-02", "CE ValidateAction RPC + unit tests ≥90%",
        {
            "architecture/reference/components/constitutional-engine.md": "§2 PAAS Boundary Validator",
            "architecture/reference/ce-validate-action-evaluators.md": "full",
            "architecture/reference/dotfiles/constitutional-engine.csproj": "full",
            "tests/QA-STRATEGY.md": "§5.1 Unit Tests",
        },
        "⚠️  BRANCH CONTEXT RULE: WC012-01 already generated the scaffold on this branch. "
        "READ the BRANCH CONTEXT section carefully before writing any file. "
        "DO NOT regenerate: constitutional-engine.csproj, Protos/, Program.cs, appsettings*.json, "
        "Services/ConstitutionalEngineService.cs, Data/ConstitutionalDbContext.cs, "
        "Data/Entities/EvidenceRecord.cs. These files EXIST — duplicating them causes CS0101. \n"
        "FOR ConstitutionalEngineService.cs: add the ValidateAction implementation to the EXISTING file. "
        "Use EvaluatorRegistry pattern. Evaluators go in src/constitutional-engine/Evaluators/. "
        "Use the .csproj from architecture/reference/dotfiles/constitutional-engine.csproj — "
        "do NOT add extra packages or invent package names. "
        "tests go in tests/constitutional-engine.Tests/ ONLY — NEVER create nested .csproj. "
        "ValidateAction returns ALLOW/DENY/ESCALATE. Default deny for unknown tools (C-041). "
        "Unit tests use xUnit + Moq. FakeServerCallContext (NOT Mock<ServerCallContext> — non-virtual). "
        "CCT format: tests/constitutional-engine.Tests/Evaluators/CCT_EF01_*Tests.cs",
        model_hint="reasoning",
        max_tokens=10000  # Implementation task: evaluators + tests fit in 10k
    ),
    "WC012-03": lambda: execute_with_llm(
        "WC012-03", "CE Evidence First record + CCT-EF-01",
        {
            "architecture/reference/components/constitutional-engine.md": "§1 Evidence First Enforcer",
            "architecture/reference/data/": "§constitutional schema",
        },
        "⚠️  BRANCH CONTEXT RULE: WC012-01 and WC012-02 already generated files. READ BRANCH CONTEXT. "
        "DO NOT regenerate: csproj, Protos/, Program.cs, Services/ConstitutionalEngineService.cs, "
        "Data/ConstitutionalDbContext.cs, Data/Entities/EvidenceRecord.cs, any Evaluator files. "
        "FOR ConstitutionalEngineService.cs: implement RecordEvidence in the EXISTING stub. "
        "RecordEvidence writes to constitutional.evidence_records BEFORE returning success (C-023 Evidence First). "
        "Append-only — no UPDATE or DELETE ever issued (C-007/C-027). "
        "Idempotency: check idempotency_key in DB before inserting — return existing record if found (C-085). "
        "CCT-EF-01: tests/constitutional-engine.Tests/Services/CCT_EF01_EvidenceFirstTests.cs "
        "Test verifies: RecordEvidence writes DB record BEFORE returning the gRPC response. "
        "All .cs files carry // Implements: and // constitutional_basis: headers.",
        model_hint="reasoning",
        max_tokens=10000  # Implementation task
    ),
    "WC012-04": lambda: execute_with_llm(
        "WC012-04", "CE Emergency Stop signal + CCT-HO-01",
        {
            "architecture/reference/components/constitutional-engine.md": "§4 Emergency Stop Handler",
            "architecture/reference/api-specs/emergency-stop-ws.md": "full",
            "adr/ADR-031-ce-fail-safe-unavailability.md": "§Recovery",
            "architecture/reference/dotfiles/constitutional-engine.csproj": "full",
        },
        "⚠️  BRANCH CONTEXT RULE: WC012-01/02/03 already generated files. READ BRANCH CONTEXT. "
        "DO NOT regenerate: csproj, Protos/, Program.cs, Services/ConstitutionalEngineService.cs, "
        "Data/ entities or DbContexts, or any Evaluator files. "
        "FOR ConstitutionalEngineService.cs: implement TriggerEmergencyStop in the EXISTING stub. "
        "FOR csproj: DO NOT touch — it already exists on branch with correct Temporalio 0.1.0-beta1. "
        "Add EmergencyStop/ subdirectory INSIDE src/constitutional-engine/ with new classes ONLY. "
        "TriggerEmergencyStop: C-001 absolute — records to constitutional.emergency_stop_events "
        "BEFORE signalling Temporal (Evidence First, C-023). Temporal signal within 100ms. "
        "CCT-HO-01: tests/constitutional-engine.Tests/EmergencyStop/CCT_HO01_*Tests.cs "
        "Test verifies Emergency Stop completes ≤250ms with mocked dependencies. "
        "Use FakeServerCallContext (NOT Mock<ServerCallContext> — non-virtual property). "
        "All .cs files carry // Implements: and // constitutional_basis: headers.",
        model_hint="reasoning",
        max_tokens=10000  # Implementation task
    ),
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
    infra_error_tasks = _INFRA_ERROR_TASKS   # populated by execute_with_llm on pure API failures
    # RC#1: scaffold task for this run = first queued task that is in SCAFFOLD_TASKS.
    # If scaffold already succeeded in a prior run, it won't be in tasks — scaffold_run_task=None.
    scaffold_run_task = next((t for t in tasks if t in SCAFFOLD_TASKS), None)
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
                # RC#2: Write tasks_done/tasks_remaining to PROJECT_STATE.md after each success.
                # Prevents duplicate re-execution across cron runs on the same open PR.
                # C-083 (Emit-Transport-Listen), C-059 (Traceability), C-085 (Idempotency)
                all_remaining = [t for t in state.get("tasks_remaining", []) if t not in tasks_done]
                run([sys.executable, "scripts/sprint_state.py", "set-list", "tasks_done"] + tasks_done)
                run([sys.executable, "scripts/sprint_state.py", "set-list", "tasks_remaining"] + all_remaining)
                print(f"  DONE: {task}")
            else:
                print(f"  FAILED: {task}")
                # RC#1: Halt on scaffold failure (C-084 Step Dependency Ordering)
                if task == scaffold_run_task:
                    print(f"  HALT: scaffold task {task} failed — downstream tasks cannot build. "
                          f"Stopping sprint. (C-084)")
                    break
                # Dependent chain halt: any non-scaffold failure also halts remaining tasks.
                # In a multi-task sprint, tasks share the same codebase. WC012-02 failing
                # means WC012-03/04 reference missing types → guaranteed to fail too.
                # Running them wastes 6 Claude API calls — C-077 FinOps violation.
                # On the next run, branch context (EXTEND-NOT-REPLACE) gives full state.
                print(f"  HALT: task {task} failed — stopping sprint to avoid wasted API calls "
                      f"on dependent tasks. Next run gets full branch context. (C-077 + C-084)")
                break
        except Exception as exc:
            print(f"  FAILED: {task}: {exc}")
            # RC#1 / chain halt on exception too
            print(f"  HALT: exception on {task} — stopping sprint. (C-084)")
            break

    # Determine if ALL failures were infrastructure (no spec gap, no human action needed)
    all_infra_errors = (
        not tasks_done
        and not tasks_not_implemented
        and len(infra_error_tasks) > 0
        and len(infra_error_tasks) == len([t for t in tasks if t not in tasks_done and t not in tasks_not_implemented])
    )

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

    # Push sprint branch — use -u (set upstream) not --force-with-lease.
    # --force-with-lease fails when no remote tracking ref exists (new branch).
    push = git(["push", "-u", "origin", branch], check=False)
    if push.returncode != 0:
        print(f"  WARN: branch push failed (non-fatal): {push.stderr[:200]}")
        # Retry once with --force in case of ref mismatch
        git(["push", "--force", "origin", branch], check=False)

    # ── Step 8: Open/update PR ────────────────────────────────────────────
    if not github_repo:
        set_output("result", "SUCCESS")
        return 0

    existing = gh(["pr", "list", "--head", branch,
                   "--json", "number", "--jq", ".[0].number",
                   "--repo", github_repo], check=False)
    existing_num = existing.stdout.strip() if existing.returncode == 0 else ""

    # Never open an empty PR — a PR with no code commits is noise (C-077 FinOps)
    if not tasks_done and not existing_num:
        print("  No tasks completed and no existing PR — skipping PR creation (empty PR is noise).")
        set_output("result", "PARTIAL")
        return 0

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
            print(f"  PR created: #{pr_num}")
    else:
        pr_num = existing_num
        print(f"  PR updated: #{pr_num}")

    set_output("pr_number", pr_num)
    if tasks_not_implemented:
        set_output("result", "NOT_IMPLEMENTED")
        set_output("halt_reason", f"Tasks {tasks_not_implemented} require IB-020 LLM code generation — not yet implemented")
        print(f"\n  ⚠️  {len(tasks_not_implemented)} task(s) require IB-020 (runner code generation).")
        print(f"  Sprint cannot advance until IB-020 is implemented.")
        print(f"  Issue #12 tracks this: github.com/dlai-sd/waooaw-platform/issues/12")
    elif not tasks_done and all_infra_errors:
        # Every task failed due to API infrastructure (timeout/rate-limit/server error)
        set_output("result", "INFRA_ERROR")
        set_output("halt_reason", "All tasks failed due to API timeouts or rate limits. No spec gap. Next cron run will retry automatically.")
        print("\n  ⚠️  INFRA_ERROR: all tasks failed due to API failures, not spec issues.")
        print("  Cron will retry. No founder action required.")
    else:
        set_output("result", "SUCCESS" if tasks_done else "PARTIAL")

    # ── Emit monitor signal artifact (C-069 — observable state for downstream jobs) ──
    # Scaffold task = first task in this run's queue that is in SCAFFOLD_TASKS.
    # If scaffold already succeeded in a prior run, it's not in the queue → scaffold_task=None.
    scaffold_t = next((t for t in tasks if t in SCAFFOLD_TASKS), None)
    scaffold_failed = scaffold_t is not None and scaffold_t not in tasks_done
    _MONITOR_SIGNAL["sprint"] = sprint
    _MONITOR_SIGNAL["scaffold_task"] = scaffold_t
    _MONITOR_SIGNAL["scaffold_failed"] = scaffold_failed
    _MONITOR_SIGNAL["overall_result"] = (
        "SUCCESS" if tasks_done and not scaffold_failed
        else "INFRA_ERROR" if all_infra_errors
        else "PARTIAL"
    )
    signal_path = Path("sprint-context/monitor-signal.json")
    signal_path.parent.mkdir(exist_ok=True)
    import json as _json
    signal_path.write_text(_json.dumps(_MONITOR_SIGNAL, indent=2))
    print(f"  📡 Monitor signal emitted: {signal_path}")
    # Scalar outputs consumed directly by the monitor job
    set_output("scaffold_failed", str(scaffold_failed).lower())
    set_output("infra_error_tasks", ",".join(str(t) for t in infra_error_tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
