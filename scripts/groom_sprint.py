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

# LLM is asked for prose only — paths and structure are built deterministically in Python.
_SCAFFOLD_PROSE_PROMPT = """You are generating metadata for a Python scaffold subtask in the WAOOAW platform.
Return ONLY a JSON object with exactly these two fields:
{
  "description": "one sentence starting with a verb — the business logic implemented",
  "constitutional_check": "multi-line string: exact ABC class and method names from skeleton, constitutional references (C-NNN), ADR references"
}
No code. No SubTaskDef struct. JSON only."""

_TEST_PROSE_PROMPT = """You are generating metadata for a pytest scaffold subtask in the WAOOAW platform.
Return ONLY a JSON object with exactly these two fields:
{
  "description": "one sentence starting with 'Write pytest tests for ...'",
  "constitutional_check": "multi-line string: test cases required, constitutional invariants (C-NNN), audit obligations"
}
No code. No SubTaskDef struct. JSON only."""


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


def _is_test_task(task: dict) -> bool:
    """Return True when ALL output files declared in the scope live under tests/.

    Test tasks (e.g. WC027-02) write only pytest files, not implementation modules.
    They need a different scaffold prompt and service_dir="" so that paths like
    'tests/billing-engine/test_markup.py' resolve relative to the repo root.
    """
    scope = task.get("scope", "")
    # Collect all file paths mentioned at the start of the scope (before " — ")
    # Format: "tests/billing-engine/test_markup.py — description..."
    paths = re.findall(r"(?:src|tests)/[\w/._-]+\.py", scope)
    if not paths:
        # No explicit paths — fall back to checking if scope mentions tests/ first
        return scope.lstrip().startswith("tests/")
    return all(p.startswith("tests/") for p in paths)


def _extract_output_files(subtaskdef_literal: str, include_tests: bool = False) -> list[str]:
    """Extract .py paths from output_files in a SubTaskDef literal.

    By default, filters out tests/ paths so the caller (polish/test chain builder)
    receives only implementation files.  Pass include_tests=True for test tasks where
    the scaffold itself produces test files that the polish pass must annotate.
    """
    m = re.search(r'output_files\s*=\s*\[(.*?)\]', subtaskdef_literal, re.DOTALL)
    if not m:
        return []
    return [
        p for p in re.findall(r'["\']([^"\']+\.py)["\']', m.group(1))
        if (include_tests or not p.startswith("tests/")) and "skeleton" not in p
    ]


def _extract_scope_paths(scope: str) -> list[str]:
    """Extract explicit .py file paths from a WC task scope string (deterministic, no LLM)."""
    clean = scope.replace("`", "")
    return [
        p for p in re.findall(r"(?:src|tests)/[\w/._-]+\.py", clean)
        if "skeleton" not in p
    ]


def _derive_service_dir(output_files: list[str]) -> str:
    """Derive service_dir from output_files without LLM. Returns '' for test-only tasks."""
    if not output_files or all(p.startswith("tests/") for p in output_files):
        return ""
    for p in output_files:
        if p.startswith("src/"):
            parts = p.split("/")
            if len(parts) >= 2:
                return "/".join(parts[:2])
    return ""


def _list_skeleton_files(sprint_prefix: str) -> list[str]:
    """Return skeleton file paths for inject_source_files (deterministic)."""
    skel_dir_rel = _SKELETON_MAP.get(sprint_prefix)
    if not skel_dir_rel:
        return []
    skel_dir = REPO_ROOT / skel_dir_rel
    if not skel_dir.exists():
        return []
    return [f"{skel_dir_rel}/{f.name}" for f in sorted(skel_dir.glob("*.py"))]


def _parse_prose_response(text: str) -> tuple[str, str]:
    """Extract (description, constitutional_check) from LLM JSON prose response."""
    import json as _json
    text = re.sub(r"^```\w*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text).strip()
    try:
        obj = _json.loads(text)
        return str(obj.get("description", "")), str(obj.get("constitutional_check", ""))
    except _json.JSONDecodeError:
        pass
    m = re.search(r"\{[^{}]*\"description\"[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            obj = _json.loads(m.group(0))
            return str(obj.get("description", "")), str(obj.get("constitutional_check", ""))
        except _json.JSONDecodeError:
            pass
    desc_m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)+)"', text)
    cc_m = re.search(r'"constitutional_check"\s*:\s*"((?:[^"\\]|\\.)+)"', text)
    description = desc_m.group(1).replace("\\n", "\n") if desc_m else ""
    const_check = cc_m.group(1).replace("\\n", "\n") if cc_m else ""
    return description, const_check


def _build_scaffold_subtaskdef(
    task_id: str,
    output_files: list[str],
    service_dir: str,
    inject_source_files: list[str],
    description: str,
    constitutional_check: str,
    is_test: bool,
    stack: str,
    wc_filename: str,
    prior_subtask_id: str | None,
    model_hint: str,
    max_tokens: int,
) -> str:
    """Build SubTaskDef literal from structured data — zero LLM path generation."""
    compile_gate = "ruff" if is_test else "py_compile"
    depends_on_str = f"[{repr(prior_subtask_id)}]" if prior_subtask_id else "[]"
    files_str = "\n        ".join(f"{repr(f)}," for f in output_files)
    inject_str = "\n        ".join(f"{repr(f)}," for f in inject_source_files)
    return (
        f"SubTaskDef(\n"
        f"    id={repr(task_id + 'a')},\n"
        f"    description={repr(description)},\n"
        f"    type=\"llm\",\n"
        f"    depends_on={depends_on_str},\n"
        f"    compile_gate={repr(compile_gate)},\n"
        f"    service_dir={repr(service_dir)},\n"
        f"    wc_task_id={repr(task_id)},\n"
        f"    stack={repr(stack)},\n"
        f"    output_files=[\n"
        f"        {files_str}\n"
        f"    ],\n"
        f"    inject_source_files=[\n"
        f"        {inject_str}\n"
        f"    ],\n"
        f"    spec_sections={{\n"
        f"        {repr('work-contracts/' + wc_filename)}: {repr(task_id)},\n"
        f"    }},\n"
        f"    constitutional_check={repr(constitutional_check)},\n"
        f"    model_hint={repr(model_hint)},\n"
        f"    max_tokens={max_tokens},\n"
        f")"
    )


def _generate_scaffold_subtaskdef(
    task: dict,
    stack: str,
    service_dir: str,
    output_files: list[str],
    inject_source_files: list[str],
    prior_subtask_id: str | None,
    wc_filename: str,
    skeleton: str,
    api_key: str,
    is_test: bool = False,
) -> str | None:
    """Returns bare SubTaskDef(...) literal (no dict wrapper).

    For implementation tasks (is_test=False): compile_gate='py_compile', service_dir as given.
    For test tasks (is_test=True): compile_gate='ruff', service_dir='',
    and uses _TEST_SYSTEM_PROMPT so the LLM generates pytest code, not business logic.
    """
    task_id = task["task_id"]
    depends_on_str = f'"{prior_subtask_id}"' if prior_subtask_id else ""
    model_hint = task.get("model_hint", "auto")
    if model_hint not in ("reasoning", "auto"):
        model_hint = "auto"
    max_tokens = 8000 if model_hint == "reasoning" else 4000

    """Generate scaffold SubTaskDef literal. LLM generates prose only; paths are deterministic."""
    task_id = task["task_id"]
    model_hint = task.get("model_hint", "auto")
    if model_hint not in ("reasoning", "auto"):
        model_hint = "auto"
    max_tokens = 8000 if model_hint == "reasoning" else 4000

    if is_test:
        system_prompt = _TEST_PROSE_PROMPT
        prompt = (
            f"Task: {task_id}\n"
            f"Scope: {task['scope']}\n"
            f"Output files (already determined — do NOT change): {output_files}\n"
            f"Skeleton interfaces to test:\n{skeleton[:3000]}\n\n"
            f'Return ONLY JSON: {{"description": "Write pytest tests for ...", "constitutional_check": "..."}}'
        )
    else:
        system_prompt = _SCAFFOLD_PROSE_PROMPT
        prompt = (
            f"Task: {task_id}\n"
            f"Scope: {task['scope']}\n"
            f"Output files (already determined — do NOT change): {output_files}\n"
            f"Skeleton (frozen — do not invent new names):\n{skeleton[:5000]}\n\n"
            f'Return ONLY JSON: {{"description": "...", "constitutional_check": "Implement <ABCClass>.<method> from skeleton..."}}'
        )

    result = _llm_call(prompt, system_prompt, api_key, max_tokens=512)
    if not result:
        return None

    description, constitutional_check = _parse_prose_response(result)
    if not description:
        description = f"Implement {task['scope'][:80]}"
    if not constitutional_check:
        constitutional_check = "Implement skeleton interfaces per ADR-036. Do not change method signatures."

    return _build_scaffold_subtaskdef(
        task_id=task_id,
        output_files=output_files,
        service_dir=service_dir,
        inject_source_files=inject_source_files,
        description=description,
        constitutional_check=constitutional_check,
        is_test=is_test,
        stack=stack,
        wc_filename=wc_filename,
        prior_subtask_id=prior_subtask_id,
        model_hint=model_hint,
        max_tokens=max_tokens,
    )


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


def _generate_pytest_run_subtaskdef(
    task_id: str,
    test_output_files: list[str],
    wc_filename: str,
    stack: str,
    polish_id: str = "",
) -> str:
    """Fully-templated 'c' subtask for TEST tasks: run pytest on the produced test file.

    No LLM call needed — the test file was generated in the 'a' subtask.  This
    subtask verifies that the tests execute without import/collection errors.
    compile_gate='pytest' runs the test file directly.
    """
    depends_on_id = polish_id or f"{task_id}b"
    # pytest service_dir: the directory containing the test files
    # For tests/billing-engine/test_markup.py → tests/billing-engine
    test_dir = str(Path(test_output_files[0]).parent) if test_output_files else "tests"
    files_str = "\n        ".join(f'"{f}",' for f in test_output_files)
    inject_str = "\n        ".join(f'"{f}",' for f in test_output_files)
    return f'''SubTaskDef(
    id="{task_id}c",
    description="Run pytest on {test_dir} to verify all tests pass",
    type="llm",
    depends_on=["{depends_on_id}"],
    compile_gate="pytest",
    service_dir="{test_dir}",
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
        "PYTEST RUN — execute the test file and confirm all tests pass.\\n"
        "If tests fail due to missing fixtures or imports, fix the test file.\\n"
        "Do NOT modify the implementation under test."
    ),
    model_hint="auto",
    max_tokens=2000,
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
    # Fully templated — no LLM call; paths are deterministic from scaffold_output_files
    return f'''SubTaskDef(
    id="{task_id}c",
    description="Write pytest suite covering happy path, error cases and constitutional invariants for {svc_name}",
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
        "Cover: happy path, error cases, idempotency, constitutional invariants from scope.\\n"
        "Tests file is exempt from ANN (per pyproject.toml per-file-ignores).\\n"
        "Use pytest-asyncio for async tests. Mock Redis/DB with pytest fixtures.\\n"
        "Use f-strings only — never % string formatting."
    ),
    model_hint="reasoning",
    max_tokens=6000,
)'''


def _indent_subtask(literal: str, spaces: int = 8) -> str:
    """Indent all lines of a bare SubTaskDef literal for placement inside 'subtasks' list."""
    pad = " " * spaces
    return "\n".join((pad + line) if line.strip() else line for line in literal.splitlines())


def _generate_subtask_chain(
    task: dict,
    skeleton: str,
    skeleton_files: list[str] | None = None,
    prior_subtask_id: str | None = None,
    sprint_prefix: str = "",
    wc_filename: str = "",
    api_key: str = "",
    accumulated_impl_files: list[str] | None = None,
) -> str | None:
    """
    Generate a 3-subtask chain (scaffold → polish → test) for one WC task row.
    Returns the complete TASK_HANDLERS dict entry string, or None on failure.

    Paths are extracted deterministically from the WC scope string; the LLM is
    called only for prose (description + constitutional_check JSON).
    """
    stack, service_dir_fallback = _SERVICE_MAP.get(sprint_prefix, ("python", "src/billing-engine"))
    task_id = task["task_id"]
    skeleton_files = skeleton_files or []

    # --- Deterministic path extraction from WC scope ---
    scope_paths = _extract_scope_paths(task.get("scope", ""))
    if scope_paths:
        output_files = scope_paths
        service_dir = _derive_service_dir(output_files)
        is_test = all(p.startswith("tests/") for p in output_files)
    else:
        # Fallback: scope has no explicit .py paths — use _SERVICE_MAP + heuristic
        print(f"  ⚠️  {task_id}: no file paths in scope — falling back to LLM path generation")
        is_test = _is_test_task(task)
        service_dir = "" if is_test else service_dir_fallback
        output_files = []

    # --- Compose inject_source_files deterministically ---
    if is_test:
        inject_source_files = (accumulated_impl_files or []) + skeleton_files
    else:
        inject_source_files = skeleton_files

    # Pass 1: scaffold (LLM for prose only; paths are deterministic)
    scaffold_literal = _generate_scaffold_subtaskdef(
        task=task, stack=stack, service_dir=service_dir,
        output_files=output_files, inject_source_files=inject_source_files,
        prior_subtask_id=prior_subtask_id, wc_filename=wc_filename,
        skeleton=skeleton, api_key=api_key, is_test=is_test,
    )
    if not scaffold_literal:
        return None

    scaffold_literal = _normalize_subtask_id(scaffold_literal, task_id, "a")
    scaffold_id = f"{task_id}a"

    scaffold_output_files = _extract_output_files(scaffold_literal, include_tests=is_test)
    if not scaffold_output_files:
        print(f"  ❌ {task_id}: scaffold output_files not parseable — cannot build polish/test chain")
        return None

    # Pass 2: polish (fully templated, no LLM call)
    polish_literal = _generate_polish_subtaskdef(
        task_id=task_id, scaffold_output_files=scaffold_output_files,
        service_dir=service_dir, wc_filename=wc_filename, stack=stack,
        scaffold_id=scaffold_id,
    )

    # Pass 3: test/pytest-run (fully templated for both impl and test tasks)
    if is_test:
        test_literal = _generate_pytest_run_subtaskdef(
            task_id=task_id, test_output_files=scaffold_output_files,
            wc_filename=wc_filename, stack=stack, polish_id=f"{task_id}b",
        )
    else:
        test_literal = _generate_test_subtaskdef(
            task=task, scaffold_output_files=scaffold_output_files,
            service_dir=service_dir, wc_filename=wc_filename, stack=stack, api_key=api_key,
        )
        if not test_literal:
            print(f"  ❌ {task_id}: test SubTaskDef generation failed — cannot build complete chain")
            return None

    test_literal = _normalize_subtask_id(test_literal, task_id, "c")

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
        ["git", "add", str(RUNNER_PATH)],
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
    skeleton_files = _list_skeleton_files(sprint_prefix)
    if not skeleton:
        print(f"  ⚠️  No skeleton found for {sprint_prefix} — grooming without blueprint")
        print(f"  EA must produce skeleton before grooming can be skeleton-grounded (ADR-036)")

    # 5. Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not set — cannot call LLM")
        return 1

    # 6. Build depends_on chain: start from last groomed task's subtask id
    prior_subtask_id: str | None = None
    runner_content = RUNNER_PATH.read_text()
    for t in tasks:
        if _already_groomed(t["task_id"]):
            candidate = t["task_id"] + "a"
            if candidate in runner_content:
                prior_subtask_id = candidate

    # Pre-accumulate all impl output_files (needed for test task inject_source_files)
    # Includes already-groomed tasks — test task may run when impl tasks are already done.
    accumulated_impl_files: list[str] = []
    for t in tasks:
        if not _is_test_task(t):
            t_paths = _extract_scope_paths(t.get("scope", ""))
            accumulated_impl_files.extend(p for p in t_paths if p not in accumulated_impl_files)

    groomed_count = 0
    groomed_task_ids = []

    for task in ungroomed:
        task_id = task["task_id"]
        print(f"\n  Grooming {task_id}: {task['scope'][:60]}...")

        generated = _generate_subtask_chain(
            task=task,
            skeleton=skeleton,
            skeleton_files=skeleton_files,
            prior_subtask_id=prior_subtask_id,
            sprint_prefix=sprint_prefix,
            wc_filename=wc_file.name,
            api_key=api_key,
            accumulated_impl_files=accumulated_impl_files,
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

    # 7. Lint gate — runner only (sprint_state.py no longer managed by groomer)
    if groomed_count > 0 and not args.dry_run:
        _run_ruff(RUNNER_PATH)

    # 8. Compile gate (syntax check)
    if groomed_count > 0 and not args.dry_run:
        r = subprocess.run(
            ["python3", "-m", "py_compile", str(RUNNER_PATH)],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"  ❌ Syntax error after injection in {RUNNER_PATH.name}: {r.stderr[:300]}")
            print(f"  CRITICAL: manual fix required — reverting is not possible in CI")
            return 1
        print(f"  ✅ Syntax check passed for runner")

    # 10. Commit to main
    if groomed_count > 0:
        _git_commit(sprint_key, args.dry_run)
        print(f"\n── Grooming complete: {groomed_count} task(s) groomed for {sprint_key} ──")
    else:
        print(f"\n── Grooming: no new tasks injected for {sprint_key} ──")

    return 0


if __name__ == "__main__":
    sys.exit(main())
