#!/usr/bin/env python3
"""
wc_spec_reader.py — Work Contract Specification Reader

# Implements: architecture/reference/pipeline/wc-spec-reader.md
# constitutional_basis:
#   C-059 (Traceability — SubTaskDef.wc_task_id creates verifiable link to PMO spec)
#   C-032 (Implementation may not create architecture — WCSpecReader READS specs, never creates them)
#   C-083 (Emit-Transport-Listen — parsed WC spec is structured signal into SubTaskDef chain)
#   DP-009 (API First — PMO Work Contract is the authoritative interface spec)
# office: Enterprise Architect (spec author) + Platform IT Expert (implementation)
# ib_item: IB-022

Eliminates hand-written constitutional_check strings from SubTaskDef.
Each SubTaskDef.wc_task_id links to a PMO Work Contract task — WCSpecReader
reads the **Constitutional check:**, **Scope:**, **model_hint:**, and **CCT gate:**
fields, feeding them into _build_effective_check() in task_decomposer.py.

Graceful degradation: if WC file not found or field missing, execution continues
using SubTaskDef.constitutional_check as delta. Never blocks sprint execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
WC_DIR    = REPO_ROOT / "work-contracts"


@dataclass
class WCTaskSpec:
    """
    Structured data extracted from a PMO Work Contract task block.
    constitutional_basis: C-059, DP-009
    """
    task_id: str               # "WC012-02"
    title: str                 # "ValidateAction + unit tests (≥90% coverage)"
    scope: str                 # verbatim **Scope:** field text
    model_hint: str            # "reasoning" | "auto" | "none" | ""
    constitutional_check: str  # verbatim **Constitutional check:** field text (may be "")
    cct_gate: str              # "CCT-EF-01 must pass" | ""
    stack: str                 # inferred stack: "dotnet" | "python" | "typescript" | "terraform" | "mixed"


# ── WC file finder ─────────────────────────────────────────────────────────────

def find_wc_file(wc_number: str) -> Optional[Path]:
    """
    Find the work contract file for a given WC number.
    Accepts "WC012", "012", or "12" — normalises to zero-padded 3-digit form.
    Returns None if not found (graceful degradation).
    """
    # Normalise: strip "WC" prefix if present, zero-pad to 3 digits
    digits = wc_number.lstrip("WCwc").lstrip("0") or "0"
    padded = digits.zfill(3)
    pattern = f"WC-{padded}-*.md"
    matches = list(WC_DIR.glob(pattern))
    if matches:
        return matches[0]
    # Also try without leading zero (e.g. WC-12-*.md)
    pattern2 = f"WC-{digits}-*.md"
    matches2 = list(WC_DIR.glob(pattern2))
    return matches2[0] if matches2 else None


# ── Stack inference ─────────────────────────────────────────────────────────────

def _infer_stack(scope: str, title: str) -> str:
    """
    Infer the technology stack from scope/title text.
    Explicit SubTaskDef.stack= always overrides this inference.
    """
    text = (scope + " " + title).lower()
    dotnet  = any(k in text for k in ("constitutional-engine", "business-platform", ".cs", ".net", "csproj", "dotnet"))
    python  = any(k in text for k in ("professional-runtime", "ai-runtime", ".py", "fastapi", "temporal", "python"))
    ts      = any(k in text for k in ("web/", ".tsx", ".ts", "next.js", "nextjs", "vitest", "react"))
    tf      = any(k in text for k in ("terraform", ".tf", "infrastructure/terraform"))

    hits = sum([dotnet, python, ts, tf])
    if hits > 1:
        return "mixed"
    if dotnet:
        return "dotnet"
    if python:
        return "python"
    if ts:
        return "typescript"
    if tf:
        return "terraform"
    return "dotnet"  # default for new sprints until explicitly set


# ── WC document parser ─────────────────────────────────────────────────────────

def _extract_field(block: str, field_name: str) -> str:
    """
    Extract a bolded field value from a WC task block.
    Matches: **{field_name}:** {value until next bold field or end of block}
    Returns "" if not found.
    """
    # Match **Field:** followed by text (possibly multi-line) until next **...: or end
    pattern = rf'\*\*{re.escape(field_name)}:\*\*\s*(.*?)(?=\n\*\*\w|\Z)'
    m = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    # Clean: strip backtick wrappers around single-word values (e.g. `reasoning`)
    value = m.group(1).strip()
    value = re.sub(r'^`([^`]+)`$', r'\1', value)
    return value


def _parse_wc_table(content: str) -> dict[str, WCTaskSpec]:
    """
    Parse WC documents that use a markdown table format instead of ### headers.
    Handles rows like: | WC026-02 | Scope text | `model_hint` | status |
    """
    result: dict[str, WCTaskSpec] = {}
    row_pattern = re.compile(
        r'^\|\s*(WC\d{3}-\d{2}(?:-\w+)?)\s*\|([^|]+)\|([^|]+)\|',
        re.MULTILINE,
    )
    for m in row_pattern.finditer(content):
        task_id    = m.group(1).strip()
        scope      = m.group(2).strip()
        model_hint = re.sub(r'^`([^`]+)`$', r'\1', m.group(3).strip())
        result[task_id] = WCTaskSpec(
            task_id=task_id,
            title=scope[:80],
            scope=scope,
            model_hint=model_hint,
            constitutional_check="",
            cct_gate="",
            stack=_infer_stack(scope, scope),
        )
    return result


def _parse_wc_file(content: str) -> dict[str, WCTaskSpec]:
    """
    Parse all task blocks from a WC document.
    Returns dict of task_id → WCTaskSpec.
    """
    result: dict[str, WCTaskSpec] = {}

    # Split on task headers: ### WC012-01 — title
    task_pattern = re.compile(
        r'^###\s+(WC\d{3}-\d{2}(?:-\w+)?)\s+[—–-]\s+(.+?)$',
        re.MULTILINE,
    )

    # Find all task header positions
    headers = list(task_pattern.finditer(content))
    if not headers:
        # Fallback: try table format (| WCxxx-xx | scope | model_hint | status |)
        return _parse_wc_table(content)

    for i, header in enumerate(headers):
        task_id = header.group(1).strip()
        title   = header.group(2).strip()

        # Extract block between this header and the next (or end of file)
        block_start = header.end()
        block_end   = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        block       = content[block_start:block_end]

        scope                = _extract_field(block, "Scope")
        model_hint           = _extract_field(block, "model_hint")
        constitutional_check = _extract_field(block, "Constitutional check")
        cct_gate             = _extract_field(block, "CCT gate")
        stack                = _infer_stack(scope, title)

        result[task_id] = WCTaskSpec(
            task_id=task_id,
            title=title,
            scope=scope,
            model_hint=model_hint,
            constitutional_check=constitutional_check,
            cct_gate=cct_gate,
            stack=stack,
        )

    return result


# ── Public API ─────────────────────────────────────────────────────────────────

# Module-level cache: wc_number → parsed tasks
_cache: dict[str, dict[str, WCTaskSpec]] = {}


def load(wc_number: str) -> dict[str, WCTaskSpec]:
    """
    Parse all tasks from a Work Contract.
    Result is cached for the process lifetime.
    Returns empty dict if file not found — never raises.
    """
    # Normalise key
    digits = wc_number.lstrip("WCwc").lstrip("0") or "0"
    cache_key = digits.zfill(3)

    if cache_key in _cache:
        return _cache[cache_key]

    wc_file = find_wc_file(wc_number)
    if wc_file is None:
        print(f"  WCSpecReader: WC-{cache_key} not found in {WC_DIR} — using constitutional_check delta only")
        _cache[cache_key] = {}
        return {}

    try:
        content = wc_file.read_text(encoding="utf-8", errors="replace")
        tasks   = _parse_wc_file(content)
        _cache[cache_key] = tasks
        print(f"  WCSpecReader: loaded {len(tasks)} task(s) from {wc_file.name}")
        return tasks
    except Exception as e:
        print(f"  WCSpecReader: failed to parse {wc_file.name}: {e} — using delta only")
        _cache[cache_key] = {}
        return {}


def get_task(task_id: str) -> Optional[WCTaskSpec]:
    """
    Get spec for a specific task ID (e.g. "WC012-02").
    Derives WC number from the task ID (characters 2–4).
    Returns None if not found — never raises.
    """
    # Extract WC number: "WC012-02" → "012"
    m = re.match(r'^WC(\d{2,3})', task_id.upper())
    if not m:
        return None
    wc_number = m.group(1).zfill(3)
    tasks = load(wc_number)
    return tasks.get(task_id)


def clear_cache() -> None:
    """Clear the module-level cache (used in tests)."""
    _cache.clear()


if __name__ == "__main__":  # pragma: no cover
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "WC012-02"
    spec = get_task(task)
    if spec:
        print(f"Task: {spec.task_id} — {spec.title}")
        print(f"Stack: {spec.stack} | model_hint: {spec.model_hint}")
        print(f"Scope: {spec.scope}")
        print(f"Constitutional check: {spec.constitutional_check or '(none)'}")
        print(f"CCT gate: {spec.cct_gate or '(none)'}")
    else:
        print(f"Task {task!r} not found")
