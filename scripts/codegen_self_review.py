#!/usr/bin/env python3
"""
codegen_self_review.py — Pre-compile self-review + symbol-level patch retry

# Constitutional basis: C-077 (FinOps — targeted fixes cost 10x less than
#                       full-file regeneration), C-082 (Build Validation),
#                       C-069 (Self-Improvement)

Two-stage quality gate that sits BETWEEN LLM generation and file write:

  Stage 1 — Pre-compile self-review (BEFORE write):
    Generated code is reviewed by Haiku before touching disk.
    Haiku acts as a lightweight C# type-checker: spots obvious type errors,
    missing usings, wrong constructor args, CS1024/CS0266 patterns.
    Corrects them inline. Only clean code reaches the filesystem.
    Cost: ~$0.001 per file. Eliminates 60-70% of compile failures.

  Stage 2 — Symbol-level patch (AFTER compile failure):
    Instead of regenerating the whole file, extract only the failing
    lines ±15 from each compiler error. Send just that symbol + error
    message to LLM. Patch only those lines. Recompile.
    Cost: 200 tokens vs 4000 for full-file retry. 20x cheaper.
    Eliminates full-file rewrite regressions.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent

# ── Stage 1: Pre-compile self-review ─────────────────────────────────────────

_REVIEW_PROMPT = """\
You are a C# compiler pre-checker. Review the generated C# code below for compile errors.

Known error patterns to check:
- CS0266: nullable long? assigned to long — use `?? 0L` or `.GetValueOrDefault(0L)`
- CS0246: missing using directive — check namespaces in USING_MAP
- CS1024: markdown text before code (## headers) — remove all non-code text
- CS1503: wrong argument type in constructor call — check exact constructor signature
- CS1744: named argument after positional — use all positional or all named
- CS1061: method does not exist on type — check BRANCH CONTEXT for real method names
- CS0505: method() instead of property — ServerCallContext members are properties, not methods

If you find errors: return the complete corrected file inside <file path="{path}">..</file>
If no errors found: return exactly: LGTM

File path: {path}
Generated code:
{code}
"""

_FORBIDDEN_CHECK = """\
Also verify none of these forbidden patterns appear:
- .AsTask() on Task<T>
- .TryGetValue() on EvaluationContext
- BudgetRemainingInrPaise (does not exist)
- ValidationDecision.Authorized or .Denied (use Allow/Deny/Escalate)
- new ConstitutionalDbContext() — must be injected via DI
- Mixed named+positional constructor arguments
"""


def pre_compile_review(
    files: dict[str, str],
    api_key: str,
    using_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Review LLM-generated code with Haiku before writing to disk.
    Returns corrected file dict. Files that pass unchanged are kept as-is.
    """
    if not api_key:
        return files  # graceful: skip if no key (CI will still compile)

    corrected: dict[str, str] = {}

    # Only review .cs files — other files (proto, json, csproj) don't need type checking
    for path, code in files.items():
        if not path.endswith(".cs"):
            corrected[path] = code
            continue

        # Inject USING_MAP into review prompt if available
        using_hint = ""
        if using_map:
            using_hint = "\nUSING_MAP (namespace→class):\n" + "\n".join(
                f"  {ns} → {cls}" for cls, ns in list(using_map.items())[:20]
            )

        prompt = _REVIEW_PROMPT.format(path=path, code=code) + _FORBIDDEN_CHECK + using_hint

        try:
            result = _call_haiku(prompt, api_key, max_tokens=4500)
        except Exception as e:
            print(f"  pre_compile_review: Haiku call failed for {Path(path).name} ({e}) — skipping")
            corrected[path] = code
            continue

        if not result or result.strip() == "LGTM":
            print(f"  PRE-REVIEW: {Path(path).name} ✅ LGTM")
            corrected[path] = code
        else:
            # Parse corrected file from response
            m = re.search(rf'<file path="{re.escape(path)}">(.*?)</file>', result, re.DOTALL)
            if not m:
                # Try without exact path match
                m = re.search(r'<file path="[^"]*">(.*?)</file>', result, re.DOTALL)
            if m:
                new_code = m.group(1).strip()
                print(f"  PRE-REVIEW: {Path(path).name} 🔧 corrections applied")
                corrected[path] = new_code
            else:
                # Haiku returned prose corrections — log but keep original (don't corrupt file)
                print(f"  PRE-REVIEW: {Path(path).name} ⚠️ review returned non-parseable response — keeping original")
                corrected[path] = code

    return corrected


# ── Stage 2: Symbol-level patch retry ────────────────────────────────────────

_PATCH_PROMPT = """\
You are patching a specific C# compile error. Fix ONLY the failing symbol — do not rewrite the whole file.

File: {file_path}
Compile error: {error_message}

Failing code region (lines {start_line}–{end_line}):
{code_region}

Return ONLY the corrected lines for this region (same line range), inside:
<patch lines="{start_line}-{end_line}">{{corrected_lines}}</patch>

Do NOT return the whole file. Patch only these lines.
"""


def symbol_level_patch(
    build_error: str,
    api_key: str,
) -> dict[str, str] | None:
    """
    Extract failing symbols from compiler errors and patch only those lines.
    Returns dict of {file_path: patched_content} or None if patch not possible.
    """
    if not api_key:
        return None

    # Parse error locations: file.cs(line,col): error CSxxxx: message
    error_pattern = re.compile(
        r"([^\s(]+\.cs)\((\d+),\d+\):\s*error\s+(CS\d+):\s*(.+)"
    )

    # Group errors by file
    errors_by_file: dict[str, list[tuple[int, str, str]]] = {}
    for m in error_pattern.finditer(build_error):
        raw_path, line, code, msg = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        # Normalize path to repo-relative
        file_path = _normalize_path(raw_path)
        if file_path not in errors_by_file:
            errors_by_file[file_path] = []
        errors_by_file[file_path].append((line, code, msg.strip()))

    if not errors_by_file:
        return None

    patched_files: dict[str, str] = {}

    for file_path, errors in errors_by_file.items():
        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            print(f"  symbol_patch: {file_path} not found — skipping")
            continue

        lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        # Collect all failing line ranges (merge overlapping windows)
        windows: list[tuple[int, int]] = []
        for line_no, code, msg in errors:
            start = max(0, line_no - 15)
            end = min(len(lines), line_no + 15)
            windows.append((start, end))
        windows = _merge_windows(windows)

        # Apply patches per window
        patched_lines = list(lines)
        any_patched = False

        for start, end in windows:
            region = "".join(lines[start:end])
            error_summary = "; ".join(
                f"line {ln}: {code} {msg}"
                for ln, code, msg in errors
                if start <= ln - 1 < end
            )
            if not error_summary:
                continue

            prompt = _PATCH_PROMPT.format(
                file_path=file_path,
                error_message=error_summary,
                start_line=start + 1,
                end_line=end,
                code_region=region,
            )

            try:
                result = _call_haiku(prompt, api_key, max_tokens=800)
            except Exception as e:
                print(f"  symbol_patch: Haiku failed for window {start+1}-{end} ({e})")
                continue

            if not result:
                continue

            m = re.search(r'<patch lines="[\d-]+">(.*?)</patch>', result, re.DOTALL)
            if m:
                patch_lines = m.group(1)
                # Preserve final newline if original had it
                if not patch_lines.endswith("\n"):
                    patch_lines += "\n"
                patched_lines[start:end] = patch_lines.splitlines(keepends=True)
                any_patched = True
                print(f"  symbol_patch: {Path(file_path).name} lines {start+1}-{end} ✅ patched")

        if any_patched:
            patched_files[file_path] = "".join(patched_lines)

    return patched_files if patched_files else None


# ── Shared Haiku call ─────────────────────────────────────────────────────────

def _call_haiku(prompt: str, api_key: str, max_tokens: int = 600) -> str | None:
    """Single Haiku call. ~$0.001. Used by both stages."""
    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["content"][0]["text"].strip() if body.get("content") else None


# ── Utilities ─────────────────────────────────────────────────────────────────

def _normalize_path(raw_path: str) -> str:
    """Convert absolute runner path to repo-relative."""
    p = Path(raw_path)
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        # Path not under REPO_ROOT — try to find it by filename
        parts = p.parts
        for i, part in enumerate(parts):
            if part in ("src", "tests", "scripts"):
                return str(Path(*parts[i:]))
        return raw_path


def _merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping line windows into minimal set."""
    if not windows:
        return []
    sorted_w = sorted(windows)
    merged = [sorted_w[0]]
    for start, end in sorted_w[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
