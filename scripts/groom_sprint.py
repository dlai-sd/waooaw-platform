#!/usr/bin/env python3
"""
groom_sprint.py — Sprint Sub-Task Groomer

# Implements: standards/AUTONOMOUS-PIPELINE-STANDARD.md §Grooming
# Constitutional basis:
#   C-059 (Traceability — every SubTaskDef.wc_task_id links to authoritative PMO spec)
#   C-066 Tier 2A (Autonomous Execution — groomer runs in preflight without human approval)
#   C-070 Third Instinct (Autonomous execution is the primary production path)
#   C-077 (FinOps — Haiku for code generation, never Frontier model)
#   ADR-036 (Blueprint-First — skeleton defines exact method names; LLM implements, never invents)
# office: Platform IT Expert (INST-010)
# spec: standards/AUTONOMOUS-PIPELINE-STANDARD.md §Grooming
# ib_item: IB-022

Blueprint-First Grooming Flow (ADR-036):

  WC file (task table: task_id, scope, model_hint)
    +  EA skeleton (src/{service}/skeleton/*.py — exact interface contracts)
    → Haiku LLM (maps scope → skeleton interfaces → SubTaskDef Python struct)
    → ast.parse validation (syntax gate)
    → inject into TASK_HANDLERS (autonomous_sprint_runner.py)
    → inject into SPRINT_TASK_MANIFEST (sprint_state.py)
    → ruff check (lint gate)
    → commit to main (PIPELINE SYNC picks up in execute job)

Design principle: Without skeleton grounding, the LLM invents class names and method
signatures (the error class ADR-036 was written to eliminate). With skeleton, SubTaskDef
generation is deterministic: skeleton provides exact types, signatures, and constitutional
anchors. Haiku does scope→interface mapping only.

Usage:
  python3 scripts/groom_sprint.py [--sprint WC-027] [--dry-run]
  Called from autonomous-sprint.yaml preflight job (after halt_check, before index_build).
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
_SCRIPTS = str(REPO_ROOT / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from runner.llm_codegen import call_llm_via_magiclm  # noqa: E402
RUNNER_PATH = REPO_ROOT / "scripts" / "autonomous_sprint_runner.py"
STATE_PATH  = REPO_ROOT / "scripts" / "sprint_state.py"
PROJECT_STATE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"

# Injection anchors (must match strings added by this session)
RUNNER_ANCHOR  = "# ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──"
MANIFEST_ANCHOR = "# ── GROOMER MANIFEST INJECTION POINT — groom_sprint.py injects new sprint manifest here ──"

# Maps sprint WC prefix → service skeleton directory
_SKELETON_MAP: dict[str, str] = {
    "WC025": "src/billing-engine/skeleton",
    "WC026": "src/billing-engine/skeleton",
    "WC027": "src/billing-engine/skeleton",
    "WC028": "src/billing-engine/skeleton",
    "WC029": "src/billing-engine/skeleton",
}

# Maps sprint WC prefix → (stack, service_dir)
_SERVICE_MAP: dict[str, tuple[str, str]] = {
    "WC025": ("python", "src/billing-engine"),
    "WC026": ("python", "src/billing-engine"),
    "WC027": ("python", "src/billing-engine"),
    "WC028": ("python", "src/billing-engine"),
    "WC029": ("python", "src/billing-engine"),
}


# ── Sprint resolution ──────────────────────────────────────────────────────────

def _read_current_sprint() -> str:
    """Read current_sprint from PROJECT_STATE.md SPRINT_STATE_MACHINE."""
    text = PROJECT_STATE.read_text()
    idx = text.find("## SPRINT_STATE_MACHINE")
    sm = text[idx:] if idx >= 0 else text
    m = re.search(r"current_sprint:\s*(\S+)", sm)
    return m.group(1).strip("'\"") if m else ""


# ── WC table parsing ───────────────────────────────────────────────────────────

def _find_wc_file(sprint_key: str) -> Path | None:
    """Find work-contracts/WC-NNN-*.md for the given sprint key (e.g. 'WC-027')."""
    digits = sprint_key.lstrip("WCwc-").lstrip("0") or "0"
    padded = digits.zfill(3)
    matches = list((REPO_ROOT / "work-contracts").glob(f"WC-{padded}-*.md"))
    return matches[0] if matches else None


def _parse_wc_tasks(wc_file: Path, sprint_prefix: str) -> list[dict]:
    """
    Parse WC tasks from the work contract file.
    Supports two formats:
      1. Markdown table rows: | WC027-01 | scope | model_hint | status |
      2. ### WC027-01 — Title headers with **Scope:**, **model_hint:** fields
    Returns list of dicts with: task_id, scope, model_hint, title
    """
    text = wc_file.read_text()
    tasks: list[dict] = []

    # Format 1: table rows — optional [a-z] suffix for split tasks (WC027-01a, WC027-01b)
    table_row = re.compile(
        r"\|\s*(" + re.escape(sprint_prefix) + r"-\d{2}[a-z]?)\s*\|"
        r"\s*([^|]+)\s*\|\s*(`?)(reasoning|auto|none)`?\s*\|"
    )
    for m in table_row.finditer(text):
        tasks.append({
            "task_id": m.group(1).strip(),
            "scope":      m.group(2).strip(),
            "model_hint": m.group(4).strip(),
            "title":      m.group(2).strip()[:80],
        })

    if tasks:
        return tasks

    # Format 2: ### WCxxx-NN[a-z] — Title headers (optional letter suffix for split tasks)
    blocks = re.split(r"(?=###\s+" + re.escape(sprint_prefix) + r"-\d{2}[a-z]?)", text)
    for block in blocks:
        m = re.match(r"###\s+(" + re.escape(sprint_prefix) + r"-\d{2}[a-z]?)\s*[—-]?\s*(.+)", block)
        if not m:
            continue
        task_id = m.group(1)
        title   = m.group(2).strip()

        def _field(name: str) -> str:
            fm = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.*?)(?=\n\*\*|\Z)", block, re.DOTALL)
            v = fm.group(1).strip() if fm else ""
            return re.sub(r"^`([^`]+)`$", r"\1", v)

        tasks.append({
            "task_id":    task_id,
            "scope":      _field("Scope") or title,
            "model_hint": _field("model_hint") or "auto",
            "title":      title,
        })

    return tasks


# ── Already-groomed detection ──────────────────────────────────────────────────

def _remove_groomed_entry(task_id: str) -> None:
    """Remove a corrupted task entry block from TASK_HANDLERS so it can be re-injected."""
    lines = RUNNER_PATH.read_text().splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.rstrip("\n") == f'        "{task_id}": {{':
            start = i
            break
    if start is None:
        return
    # Find where this entry ends: next 8-space "WC task key or the injection anchor
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].lstrip()
        if lines[i].startswith('        "WC') or lines[i].startswith('    # ──'):
            end = i
            break
    RUNNER_PATH.write_text("".join(lines[:start] + lines[end:]))


def _already_groomed(task_id: str) -> bool:
    """Return True only if task_id has an entry with the canonical scaffold id.

    If the entry exists but scaffold id is non-canonical, remove it so the groomer re-injects.
    """
    content = RUNNER_PATH.read_text()
    if f'"{task_id}"' not in content and f"'{task_id}'" not in content:
        return False
    canonical_scaffold = f"{task_id}a"
    if f'id="{canonical_scaffold}"' not in content and f"id=\'{canonical_scaffold}\'" not in content:
        print(f"  ⚠️  {task_id}: entry has non-canonical scaffold id — removing for re-groom")
        _remove_groomed_entry(task_id)
        return False
    return True


# ── Skeleton reading ───────────────────────────────────────────────────────────

def _read_skeleton(sprint_prefix: str) -> str:
    """Read all skeleton/*.py files for the service and return concatenated content."""
    skel_dir_rel = _SKELETON_MAP.get(sprint_prefix)
    if not skel_dir_rel:
        return ""
    skel_dir = REPO_ROOT / skel_dir_rel
    if not skel_dir.exists():
        return ""
    parts = []
    for f in sorted(skel_dir.glob("*.py")):
        parts.append(f"# === {f.name} ===\n" + f.read_text())
    return "\n".join(parts)


# ── LLM SubTaskDef generation ──────────────────────────────────────────────────

# ── Staged generation: 3-subtask chain per WC task ───────────────────────────
#
# Scaffold  (compile_gate="py_compile") — LLM implements business logic only
# Polish    (compile_gate="ruff")       — LLM adds type annotations only (templated, no LLM call)
# Test      (compile_gate="ruff")       — LLM writes tests against scaffold output

_SCAFFOLD_SYSTEM_PROMPT = """You are a Python code generator for the WAOOAW autonomous sprint pipeline.
You produce the SCAFFOLD SubTaskDef for a WC task — the first of three staged subtasks.

SCAFFOLD RULES (staged generation — see architecture/reference/pipeline/staged-generation.md):
1. compile_gate MUST be "py_compile" — scaffold gate is syntax only, NOT ruff
2. output_files MUST be derived from the scope — real module paths under the service dir
3. constitutional_check MUST reference exact skeleton ABC class and method names
4. constitutional_check MUST say: "Implement business logic. Type annotations optional here — polish pass adds them."
5. inject_source_files MUST include the skeleton file
6. model_hint from WC table (reasoning/auto — never 'standard')
7. depends_on: prior scaffold subtask id, or [] for first task in sprint
8. Wrap your output in exactly one XML file block — required by the pipeline FORMAT gate:
   <file path="scripts/autonomous_sprint_runner.py">SubTaskDef(...)</file>
"""

_TEST_SYSTEM_PROMPT = """You are a Python test generator for the WAOOAW autonomous sprint pipeline.
You produce the TEST SubTaskDef for a WC task — the third of three staged subtasks.

TEST RULES:
1. compile_gate MUST be "ruff" — tests exempt from ANN per pyproject.toml per-file-ignores
2. output_files MUST be test files under tests/{service}/ directory
3. inject_source_files MUST include scaffold output files (the implementation being tested)
4. constitutional_check must list: happy path, idempotency cases, error cases, constitutional invariants
5. model_hint MUST be "reasoning" — test quality requires understanding edge cases
6. max_tokens: 6000
7. depends_on: the polish subtask id (e.g. WC027-02b)
8. Wrap your output in exactly one XML file block — required by the pipeline FORMAT gate:
   <file path="scripts/autonomous_sprint_runner.py">SubTaskDef(...)</file>
"""


def _llm_call(prompt: str, system: str, api_key: str, max_tokens: int = 2048) -> str | None:
    """Groom LLM call — delegates to the governed MagicLLM layer (C-077, ADR-030).

    api_key is accepted for backward compatibility but MagicLLM reads it from
    ANTHROPIC_API_KEY env directly.  system is forwarded as constitutional_check
    so MagicLLM appends it to the context block seen by the model.
    """
    return call_llm_via_magiclm(
        task_id="GROOM-SUBTASK",
        task_description=prompt,
        spec_content="",
        constitutional_check=system,
        model_hint="auto",
        max_tokens=max_tokens,
    )


def _strip_llm_fences(text: str) -> str:
    """Extract bare SubTaskDef literal from XML file-block envelope, fences, or plain output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()
    idx = text.find("SubTaskDef(")
    if idx > 0:
        text = text[idx:]
    # Strip XML closing tag when LLM wraps output in <file path="...">...</file>
    end_tag = text.rfind("</file>")
    if end_tag != -1:
        text = text[:end_tag].rstrip()
    return text


def _extract_subtaskdef_id(literal: str) -> str | None:
    """Return the value of id= from a SubTaskDef literal, or None if not found."""
    m = re.search(r'\bid\s*=\s*["\'](.*?)["\']', literal)
    return m.group(1) if m else None


def _normalize_subtask_id(literal: str, task_id: str, suffix: str) -> str:
    """
    Enforce canonical SubTaskDef id: {task_id}{suffix}.

    LLMs sometimes invent non-canonical ids (e.g. 'WC027-01a-scaffold' instead
    of 'WC027-01aa'). This causes depends_on mismatches at runtime: polish
    declares depends_on=['WC027-01aa'] but completed only has 'WC027-01a-scaffold'
    → all downstream subtasks are BLOCKED even when scaffold succeeded.

    This is a pure string normalisation — no semantic change.
    """
    actual = _extract_subtaskdef_id(literal)
    expected = f"{task_id}{suffix}"
    if actual and actual != expected:
        print(f"  ⚠️  SubTaskDef id normalised: '{actual}' → '{expected}'")
        literal = re.sub(
            r'\bid\s*=\s*["\'][^"\'\']+["\']',
            f'id="{expected}"',
            literal,
            count=1,
        )
    return literal


def _extract_output_files(subtaskdef_literal: str) -> list[str]:
    """Extract implementation .py paths from output_files in a SubTaskDef literal."""
    m = re.search(r'output_files\s*=\s*\[(.*?)\]', subtaskdef_literal, re.DOTALL)
    if not m:
        return []
    return [
        p for p in re.findall(r'["\']([^"\']+\.py)["\']', m.group(1))
        if not p.startswith("tests/") and "skeleton" not in p
    ]


def _generate_scaffold_subtaskdef(
    task: dict,
    stack: str,
    service_dir: str,
    prior_subtask_id: str | None,
    wc_filename: str,
    skeleton: str,
    api_key: str,
) -> str | None:
    """Returns bare SubTaskDef(...) literal (no dict wrapper). compile_gate='py_compile'."""
    task_id = task["task_id"]
    depends_on_str = f'"{prior_subtask_id}"' if prior_subtask_id else ""
    model_hint = task.get("model_hint", "auto")
    if model_hint not in ("reasoning", "auto"):
        model_hint = "auto"
    max_tokens = 8000 if model_hint == "reasoning" else 4000

    prompt = f"""Generate a SCAFFOLD SubTaskDef for this WC task.

Task ID: {task_id}
Scope: {task['scope']}
model_hint: {model_hint}
Stack: {stack}
Service dir: {service_dir}
Prior subtask id (depends_on): {prior_subtask_id or 'none — first task'}
WC file: {wc_filename}

EA SKELETON (frozen — do not invent new names):
{skeleton[:6000]}

Wrap output in one XML file block (pipeline FORMAT gate requirement):
<file path="scripts/autonomous_sprint_runner.py">
SubTaskDef(
    id="{task_id}a",
    description="<one sentence: business logic implemented>",
    type="llm",
    depends_on=[{depends_on_str}],
    compile_gate="py_compile",
    service_dir="{service_dir}",
    wc_task_id="{task_id}",
    stack="{stack}",
    output_files=[
        "<service module path, e.g. {service_dir}/wallet/service.py>",
    ],
    inject_source_files=[
        "{service_dir}/skeleton/wbe_interfaces.py",
    ],
    spec_sections={{
        "work-contracts/{wc_filename}": "{task_id}",
    }},
    constitutional_check=(
        "Implement <ExactABCClass>.<method>() from skeleton.\\n"
        "DO NOT change signatures — implement bodies only (ADR-036).\\n"
        "Type annotations optional in scaffold — polish pass enforces ANN001.\\n"
        "<C-xxx: constitutional invariant from skeleton annotations>"
    ),
    model_hint="{model_hint}",
    max_tokens={max_tokens},
)
</file>
"""
    result = _llm_call(prompt, _SCAFFOLD_SYSTEM_PROMPT, api_key)
    return _strip_llm_fences(result) if result else None


def _generate_polish_subtaskdef(
    task_id: str,
    scaffold_output_files: list[str],
    service_dir: str,
    wc_filename: str,
    stack: str,
    scaffold_id: str = "",
) -> str:
    """Returns bare SubTaskDef(...) literal (4-space fields). No LLM call — fully templated."""
    # scaffold_id is the normalised id of the scaffold subtask — defaults to {task_id}a
    depends_on_id = scaffold_id or f"{task_id}a"
    files_str = "\n        ".join(f'"{f}",' for f in scaffold_output_files)
    inject_str = "\n        ".join(f'"{f}",' for f in scaffold_output_files)
    return f'''SubTaskDef(
    id="{task_id}b",
    description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
    type="llm",
    depends_on=["{depends_on_id}"],
    compile_gate="ruff",
    service_dir="{service_dir}",
    wc_task_id="{task_id}",
    stack="{stack}",
    output_files=[
        {files_str}
    ],
    inject_source_files=[
        {inject_str}
    ],
    spec_sections={{
        "work-contracts/{wc_filename}": "{task_id}",
    }},
    constitutional_check=(
        "POLISH PASS — type annotation enforcement only.\\n"
        "Add type annotations to ALL function parameters (ANN001).\\n"
        "Add return type annotations to ALL functions (ANN201, ANN202).\\n"
        "DO NOT change function names, business logic, or structure.\\n"
        "DO NOT add new imports beyond those needed for type annotations."
    ),
    model_hint="auto",
    max_tokens=3000,
)'''


def _generate_test_subtaskdef(
    task: dict,
    scaffold_output_files: list[str],
    service_dir: str,
    wc_filename: str,
    stack: str,
    api_key: str,
) -> str | None:
    """Returns bare SubTaskDef(...) literal (4-space fields). compile_gate='ruff' (tests ANN-exempt)."""
    task_id = task["task_id"]
    test_dir = "tests/" + service_dir.removeprefix("src/")
    svc_file = scaffold_output_files[0] if scaffold_output_files else ""
    svc_name = Path(svc_file).stem if svc_file else task_id.lower().replace("-", "_")
    test_file = f"{test_dir}/test_{svc_name}.py"
    files_str = "\n        ".join(f'"{f}",' for f in scaffold_output_files)

    prompt = f"""Generate a TEST SubTaskDef for this WC task.

Task ID: {task_id}
Scope: {task['scope']}
Implementation files (inject these — tests target the actual code):
{chr(10).join(scaffold_output_files)}
Test file to produce: {test_file}
WC file: {wc_filename}

Wrap output in one XML file block (pipeline FORMAT gate requirement):
<file path="scripts/autonomous_sprint_runner.py">
SubTaskDef(
    id="{task_id}c",
    description="<one sentence: what this test suite covers>",
    type="llm",
    depends_on=["{task_id}b"],
    compile_gate="ruff",
    service_dir="{service_dir}",
    wc_task_id="{task_id}",
    stack="{stack}",
    output_files=[
        "{test_file}",
    ],
    inject_source_files=[
        {files_str}
    ],
    spec_sections={{
        "work-contracts/{wc_filename}": "{task_id}",
    }},
    constitutional_check=(
        "TEST PASS — write pytest tests against the provided implementation.\\n"
        "Cover: happy path, error cases, <idempotency/invariant specific to scope>.\\n"
        "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\\n"
        "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures."
    ),
    model_hint="reasoning",
    max_tokens=6000,
)
</file>
"""
    result = _llm_call(prompt, _TEST_SYSTEM_PROMPT, api_key)
    return _strip_llm_fences(result) if result else None


def _indent_subtask(literal: str, spaces: int = 8) -> str:
    """Indent all lines of a bare SubTaskDef literal for placement inside 'subtasks' list."""
    pad = " " * spaces
    return "\n".join((pad + line) if line.strip() else line for line in literal.splitlines())


def _generate_subtask_chain(
    task: dict,
    skeleton: str,
    prior_subtask_id: str | None,
    sprint_prefix: str,
    wc_filename: str,
    api_key: str,
) -> str | None:
    """
    Generate a 3-subtask chain (scaffold → polish → test) for one WC task row.
    Returns the complete TASK_HANDLERS dict entry string, or None on failure.
    Assembly is done entirely in Python — no string surgery on LLM output.
    """
    stack, service_dir = _SERVICE_MAP.get(sprint_prefix, ("python", "src/billing-engine"))
    task_id = task["task_id"]

    # Pass 1: scaffold (LLM) — returns bare SubTaskDef(...) literal
    scaffold_literal = _generate_scaffold_subtaskdef(
        task=task, stack=stack, service_dir=service_dir,
        prior_subtask_id=prior_subtask_id, wc_filename=wc_filename,
        skeleton=skeleton, api_key=api_key,
    )
    if not scaffold_literal:
        return None

    # Enforce canonical scaffold id — LLMs sometimes use {task_id}-scaffold instead
    # of {task_id}a, which breaks the depends_on chain for polish and cross-task deps.
    scaffold_literal = _normalize_subtask_id(scaffold_literal, task_id, "a")
    scaffold_id = f"{task_id}a"  # always canonical after normalisation above

    # Extract output_files from scaffold literal to feed polish and test
    scaffold_output_files = _extract_output_files(scaffold_literal)

    if not scaffold_output_files:
        print(f"  ❌ {task_id}: scaffold output_files not parseable — cannot build polish/test chain")
        return None

    # Pass 2: polish (templated, no LLM call) — returns bare SubTaskDef(...) literal
    polish_literal = _generate_polish_subtaskdef(
        task_id=task_id, scaffold_output_files=scaffold_output_files,
        service_dir=service_dir, wc_filename=wc_filename, stack=stack,
        scaffold_id=scaffold_id,
    )

    # Pass 3: test (LLM) — returns bare SubTaskDef(...) literal
    test_literal = _generate_test_subtaskdef(
        task=task, scaffold_output_files=scaffold_output_files,
        service_dir=service_dir, wc_filename=wc_filename, stack=stack, api_key=api_key,
    )
    if not test_literal:
        print(f"  ❌ {task_id}: test SubTaskDef LLM call failed — cannot build complete chain")
        return None

    # Enforce canonical test id — same guard as scaffold above
    test_literal = _normalize_subtask_id(test_literal, task_id, "c")

    # Assemble entirely in Python — indent each literal to 8 spaces inside "subtasks" list
    blocks = [scaffold_literal, polish_literal, test_literal]
    subtasks_block = ",\n".join(_indent_subtask(b) for b in blocks)
    return f'"{task_id}": {{\n    "subtasks": [\n{subtasks_block},\n    ]\n}},'


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_generated_entry(code: str, task_id: str) -> bool:
    """
    Validate the generated TASK_HANDLERS entry.
    1. Must contain the task_id as a dict key
    2. Must contain 'SubTaskDef(' literal
    3. Must be parseable as Python (wrapped in a minimal module context)
    """
    if f'"{task_id}"' not in code and f"'{task_id}'" not in code:
        print(f"  ❌ Validation: missing task_id key '{task_id}' in generated code")
        return False
    if "SubTaskDef(" not in code:
        print(f"  ❌ Validation: no SubTaskDef( in generated code")
        return False
    if f'"{task_id}a"' not in code and f"'{task_id}a'" not in code:
        print(f"  ❌ Validation: missing scaffold subtask '{task_id}a' — id not normalised")
        return False
    if f'"{task_id}b"' not in code and f"'{task_id}b'" not in code:
        print(f"  ❌ Validation: missing polish subtask '{task_id}b' — incomplete chain")
        return False
    if f'"{task_id}c"' not in code and f"'{task_id}c'" not in code:
        print(f"  ❌ Validation: missing test subtask '{task_id}c' — incomplete chain")
        return False
    if f'depends_on=["{task_id}a"]' not in code and f"depends_on=['{task_id}a']" not in code:
        print(f"  ❌ Validation: polish depends_on chain broken — '{task_id}b' must depend on '{task_id}a'")
        return False
    if f'depends_on=["{task_id}b"]' not in code and f"depends_on=['{task_id}b']" not in code:
        print(f"  ❌ Validation: test depends_on chain broken — '{task_id}c' must depend on '{task_id}b'")
        return False
    # Wrap in parseable context for ast.parse
    wrapper = f"""
from dataclasses import dataclass
from typing import Optional
@dataclass
class SubTaskDef:
    id: str = ""
    description: str = ""
    type: str = "llm"
    depends_on: list = None
    compile_gate: str = "ruff"
    service_dir: str = ""
    wc_task_id: str = ""
    stack: str = "python"
    output_files: list = None
    inject_source_files: list = None
    not_regenerate_from: list = None
    spec_sections: dict = None
    constitutional_check: str = ""
    model_hint: str = "auto"
    max_tokens: int = 4000

_entry = {{
{code}
}}
"""
    try:
        ast.parse(wrapper)
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error in generated code: {e}")
        return False


# ── Injection ─────────────────────────────────────────────────────────────────

def _inject_task_handler(code: str) -> bool:
    """Inject the generated TASK_HANDLERS entry before the GROOMER INJECTION POINT anchor."""
    content = RUNNER_PATH.read_text()
    if RUNNER_ANCHOR not in content:
        print(f"  ❌ Injection anchor not found in {RUNNER_PATH.name}")
        return False
    # Indent the entry: it goes inside the TASK_HANDLERS dict (4-space indent)
    indented = "\n".join("    " + line if line.strip() else line for line in code.splitlines())
    new_content = content.replace(
        f"    {RUNNER_ANCHOR}",
        f"    {indented}\n    {RUNNER_ANCHOR}",
    )
    RUNNER_PATH.write_text(new_content)
    return True


def _inject_manifest_entry(sprint_key: str, task_ids: list[str]) -> bool:
    """Inject sprint manifest entry before the GROOMER MANIFEST INJECTION POINT anchor."""
    content = STATE_PATH.read_text()
    if MANIFEST_ANCHOR not in content:
        print(f"  ❌ Manifest anchor not found in {STATE_PATH.name}")
        return False
    # Check not already present
    if f'"{sprint_key}"' in content:
        print(f"  ℹ️  {sprint_key} already in SPRINT_TASK_MANIFEST — skipping")
        return True
    ids_str = ", ".join(f'"{t}"' for t in task_ids)
    entry = f'    "{sprint_key}": [{ids_str}],\n    '
    new_content = content.replace(f"    {MANIFEST_ANCHOR}", f"{entry}{MANIFEST_ANCHOR}")
    STATE_PATH.write_text(new_content)
    return True


# ── Lint gate ─────────────────────────────────────────────────────────────────

def _run_ruff(path: Path) -> bool:
    result = subprocess.run(
        ["python3", "-m", "ruff", "check", "--select", "E,F", "--ignore", "E501,F401,F811", str(path)],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode != 0:
        print(f"  ⚠️  ruff warnings (non-blocking):\n{result.stdout[:500]}")
    return True  # ruff warnings don't block grooming — syntax gate is the hard gate


# ── Git commit ────────────────────────────────────────────────────────────────

def _git_commit(sprint_key: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] Would commit groomed SubTaskDefs for {sprint_key} to main")
        return
    for cmd in [
        ["git", "config", "user.email", "autonomy@waooaw.ai"],
        ["git", "config", "user.name", "WAOOAW Sprint Groomer"],
        ["git", "add", str(RUNNER_PATH), str(STATE_PATH)],
        ["git", "commit", "-m",
         f"chore(pr): groom {sprint_key} SubTaskDefs from skeleton (ADR-036, C-059)"],
        ["git", "push", "origin", "main"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            print(f"  ⚠️  git cmd failed: {' '.join(cmd)}\n  {r.stderr[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Groom sprint SubTaskDefs from WC + skeleton")
    parser.add_argument("--sprint", default="", help="Sprint key e.g. WC-027")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no file writes")
    args = parser.parse_args()

    sprint_key = args.sprint.strip() or _read_current_sprint()
    if not sprint_key:
        print("  ❌ Could not determine current sprint from PROJECT_STATE.md")
        return 1

    # Normalise: WC-027 → WC-027, WC027 → WC-027
    if "-" not in sprint_key:
        sprint_key = sprint_key[:2] + "-" + sprint_key[2:]
    sprint_prefix = sprint_key.replace("-", "")  # WC-027 → WC027

    print(f"\n── Sprint Groomer: {sprint_key} ──────────────────────────────────────")

    # 1. Find WC file
    wc_file = _find_wc_file(sprint_key)
    if not wc_file:
        print(f"  ℹ️  No WC file found for {sprint_key} — grooming skipped (not yet pushed)")
        return 0

    print(f"  WC file: {wc_file.name}")

    # 2. Parse tasks
    tasks = _parse_wc_tasks(wc_file, sprint_prefix)
    if not tasks:
        print(f"  ℹ️  No tasks parsed from {wc_file.name} — check table format")
        return 0

    print(f"  Tasks in WC: {[t['task_id'] for t in tasks]}")

    # 3. Filter to ungroomed tasks
    ungroomed = [t for t in tasks if not _already_groomed(t["task_id"])]
    if not ungroomed:
        print(f"  ✅ All {len(tasks)} tasks already groomed — nothing to do")
        return 0

    print(f"  Ungroomed tasks: {[t['task_id'] for t in ungroomed]}")

    # 4. Read skeleton
    skeleton = _read_skeleton(sprint_prefix)
    if not skeleton:
        print(f"  ⚠️  No skeleton found for {sprint_prefix} — grooming without blueprint")
        print(f"  EA must produce skeleton before grooming can be skeleton-grounded (ADR-036)")

    # 5. Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not set — cannot call LLM")
        return 1

    # 6. Build depends_on chain: start from last groomed task's subtask id
    # Find the last subtask id from already-groomed tasks in this sprint
    prior_subtask_id: str | None = None
    runner_content = RUNNER_PATH.read_text()
    for t in tasks:
        if _already_groomed(t["task_id"]):
            candidate = t["task_id"] + "a"
            if candidate in runner_content:
                prior_subtask_id = candidate

    groomed_count = 0
    groomed_task_ids = []

    for task in ungroomed:
        task_id = task["task_id"]
        print(f"\n  Grooming {task_id}: {task['scope'][:60]}...")

        # Generate 3-subtask chain: scaffold → polish → test
        generated = _generate_subtask_chain(
            task=task,
            skeleton=skeleton,
            prior_subtask_id=prior_subtask_id,
            sprint_prefix=sprint_prefix,
            wc_filename=wc_file.name,
            api_key=api_key,
        )
        if not generated:
            print(f"  ❌ {task_id}: LLM generation failed — skipping")
            continue

        # Validate
        if not _validate_generated_entry(generated, task_id):
            print(f"  ❌ {task_id}: validation failed — skipping")
            print(f"  Generated:\n{generated[:400]}")
            continue

        if args.dry_run:
            print(f"  [dry-run] Would inject {task_id}:\n{generated[:300]}...")
            groomed_task_ids.append(task_id)
            prior_subtask_id = task_id + "a"  # cross-task: scaffold-to-scaffold dep only
            continue

        # Inject into TASK_HANDLERS
        if not _inject_task_handler(generated):
            print(f"  ❌ {task_id}: injection failed")
            continue

        groomed_count += 1
        groomed_task_ids.append(task_id)
        prior_subtask_id = task_id + "a"  # cross-task: scaffold-to-scaffold dep only
        print(f"  ✅ {task_id}: 3-subtask chain injected (scaffold/polish/test)")

    # 7. Update SPRINT_TASK_MANIFEST with all tasks (groomed + already-groomed)
    all_task_ids = [t["task_id"] for t in tasks]
    if groomed_count > 0 and not args.dry_run:
        _inject_manifest_entry(sprint_key, all_task_ids)
        print(f"\n  ✅ SPRINT_TASK_MANIFEST updated: {sprint_key} → {all_task_ids}")

    # 8. Lint gate
    if groomed_count > 0 and not args.dry_run:
        _run_ruff(RUNNER_PATH)
        _run_ruff(STATE_PATH)

    # 9. Compile gate (syntax check)
    if groomed_count > 0 and not args.dry_run:
        for path in [RUNNER_PATH, STATE_PATH]:
            r = subprocess.run(
                ["python3", "-m", "py_compile", str(path)],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                print(f"  ❌ Syntax error after injection in {path.name}: {r.stderr[:300]}")
                print(f"  CRITICAL: manual fix required — reverting is not possible in CI")
                return 1
        print(f"  ✅ Syntax check passed for runner and sprint_state")

    # 10. Commit to main
    if groomed_count > 0:
        _git_commit(sprint_key, args.dry_run)
        print(f"\n── Grooming complete: {groomed_count} task(s) groomed for {sprint_key} ──")
    else:
        print(f"\n── Grooming: no new tasks injected for {sprint_key} ──")

    return 0


if __name__ == "__main__":
    sys.exit(main())
