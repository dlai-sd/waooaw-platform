#!/usr/bin/env python3
"""
advisor_auto_extend.py — Self-healing Retry Advisor

# Implements: architecture/reference/pipeline/sprint-retry-advisor.md §Self-Healing
# Constitutional basis: C-069 (Self-Improvement — platform must detect degradation
#                       and raise proposals autonomously), C-077 (FinOps — Haiku
#                       for classification, never Frontier)
# office: Platform IT Expert (Monitor hat)

When the retry advisor hits UNKNOWN/STOP_LOSS (0% confidence) on a new C# error
code, this script:
  1. Extracts the error code + message from the monitor signal
  2. Uses Haiku (cheap model) to generate a valid RetryDiagnosis handler
  3. Validates the generated Python syntax
  4. Injects it into sprint_retry_advisor.py before the learning-cache fallback
  5. Runs the advisor test suite to confirm no regression
  6. Commits and pushes to main — every subsequent run benefits immediately

This is fully autonomous. No human needed for a new C# compiler error code.
Only if the generated handler syntax is invalid does it fall back gracefully
(log warning, skip injection).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ADVISOR_PATH = REPO_ROOT / "scripts" / "sprint_retry_advisor.py"
SIGNAL_PATH = REPO_ROOT / "sprint-context" / "monitor-signal.json"

# Injection anchor — new handlers go just before the learning-cache fallback
INJECTION_ANCHOR = "# ── Fallback 1: Learning cache (C-069 self-improvement) ──────────────"

# Only auto-extend for known C# error code families (safe to automate)
_AUTO_EXTEND_PATTERN = re.compile(r"\bCS\d{4}\b")

# Do NOT re-add codes that already have explicit handlers
_KNOWN_CODES = {
    "CS0019", "CS0037", "CS0101", "CS0103", "CS0115", "CS0117", "CS0246",
    "CS0266", "CS0505", "CS0539", "CS0738", "CS1061", "CS1503",
    "CS1729", "CS1744", "CS7036", "CS8600", "CS8602", "CS8604", "CS8618",
    "CS8629",
    # CS1024 intentionally NOT here — auto-extend will generate it on first encounter
}


def _extract_unknown_codes_from_signal(signal: dict) -> list[tuple[str, str]]:
    """
    Scan monitor signal for tasks that failed with UNKNOWN/STOP_LOSS.
    Returns list of (error_code, error_snippet) tuples for new codes only.
    """
    results = signal.get("task_results", {})
    unknown_pairs: list[tuple[str, str]] = []

    for task_id, result in results.items():
        if result.get("result") not in ("BUILD_FAILURE", "SPEC_GAP"):
            continue
        snippet = result.get("build_error_snippet", "") or ""
        codes = _AUTO_EXTEND_PATTERN.findall(snippet)
        for code in codes:
            if code.upper() not in _KNOWN_CODES:
                unknown_pairs.append((code.upper(), snippet[:300]))

    return list(dict.fromkeys(unknown_pairs))  # deduplicate, preserve order


def _generate_handler_via_llm(error_code: str, error_snippet: str, api_key: str) -> str | None:
    """
    Use Haiku to generate a RetryDiagnosis handler function for the new error code.
    Cost: ~$0.001 per call.
    """
    import urllib.request

    function_name = f"_classify_{error_code.lower()}"

    prompt = f"""You are generating a Python function to handle C# compiler error {error_code}.

Error example: {error_snippet}

Generate ONLY a single Python function with this EXACT structure (no imports, no extra text):

def {function_name}(error: str) -> Optional[RetryDiagnosis]:
    m = re.search(r"<regex to extract relevant info>", error)
    if not m:
        return None
    fix = (
        "<ONE paragraph fix instruction: what went wrong and exactly how to fix it>"
    )
    print(f"  Retry Advisor: {error_code} <short description> (confidence=80%)")
    return RetryDiagnosis(
        error_type=WRONG_FIELD_NAME,
        fix_instruction=fix,
        should_retry=True,
        confidence=0.80,
        constitutional_trace="C-082 (Build Validation — {error_code} auto-classified)"
    )

Return ONLY the function. No markdown. No explanation."""

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 400,
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
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["content"][0]["text"].strip()
    except Exception as e:
        print(f"  advisor_auto_extend: LLM call failed ({e})")
        return None


def _validate_handler_syntax(handler_code: str, error_code: str) -> bool:
    """Compile-check the generated handler before injecting."""
    # Must be a function definition
    if not handler_code.strip().startswith("def _classify_"):
        print(f"  advisor_auto_extend: handler does not start with 'def _classify_'")
        return False
    # Must contain RetryDiagnosis
    if "RetryDiagnosis" not in handler_code:
        print(f"  advisor_auto_extend: handler missing RetryDiagnosis")
        return False
    # Syntax check via py_compile
    test_code = (
        "from __future__ import annotations\n"
        "import re\n"
        "from typing import Optional\n"
        "from dataclasses import dataclass, field\n"
        "@dataclass\n"
        "class RetryDiagnosis:\n"
        "    error_type: str\n"
        "    fix_instruction: str\n"
        "    should_retry: bool\n"
        "    confidence: float\n"
        "    duplicate_files: list = field(default_factory=list)\n"
        "    constitutional_trace: str = ''\n"
        "WRONG_FIELD_NAME = 'WRONG_FIELD_NAME'\n\n"
        + handler_code
    )
    try:
        compile(test_code, "<handler>", "exec")
        return True
    except SyntaxError as e:
        print(f"  advisor_auto_extend: syntax error in generated handler: {e}")
        return False


def _inject_handler(error_code: str, handler_code: str) -> bool:
    """
    Inject the handler into sprint_retry_advisor.py before the learning-cache fallback.
    Also adds the call site in diagnose_build_error().
    """
    content = ADVISOR_PATH.read_text(encoding="utf-8")

    # 1. Check anchor exists
    if INJECTION_ANCHOR not in content:
        print(f"  advisor_auto_extend: anchor not found in advisor — skipping injection")
        return False

    # 2. Check not already present
    function_name = f"_classify_{error_code.lower()}"
    if function_name in content:
        print(f"  advisor_auto_extend: {function_name} already exists — skipping")
        return False

    # 3. Inject handler function before the learning-cache fallback block
    handler_block = (
        f"\n\n# ── Auto-generated handler: {error_code} (advisor_auto_extend.py) ──\n"
        + handler_code
        + "\n"
    )
    content = content.replace(INJECTION_ANCHOR, handler_block + "\n" + INJECTION_ANCHOR)

    # 4. Add call site in diagnose_build_error() just before the learning-cache fallback
    call_site = (
        f"    # ── Auto-extended: {error_code} ──────────────────────────────────────────\n"
        f"    if \"{error_code}\" in error_codes:\n"
        f"        _diag = {function_name}(build_error)\n"
        f"        if _diag:\n"
        f"            print(f\"  Retry Advisor: {error_code} auto-handler (confidence={{_diag.confidence:.0%}})\")\n"
        f"            return _diag\n\n"
    )
    content = content.replace(INJECTION_ANCHOR, call_site + INJECTION_ANCHOR)

    ADVISOR_PATH.write_text(content, encoding="utf-8")
    print(f"  advisor_auto_extend: ✅ {error_code} handler injected into advisor")
    return True


def _run_tests() -> bool:
    """Run advisor tests after injection to confirm no regression."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/pipeline/test_sprint_retry_advisor_comprehensive.py",
         "-q", "--tb=short"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  advisor_auto_extend: tests FAILED after injection:\n{result.stdout[-500:]}")
        return False
    print(f"  advisor_auto_extend: ✅ advisor tests pass after injection")
    return True


def _commit_and_push(error_code: str) -> bool:
    """Commit and push the auto-extended advisor to main."""
    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)

    run(["git", "add", "scripts/sprint_retry_advisor.py"])
    diff = run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print(f"  advisor_auto_extend: nothing to commit")
        return True

    commit = run(["git", "commit", "-m",
                  f"fix(advisor): auto-extend {error_code} handler (C-069 self-improvement)\n\n"
                  f"New error code encountered in sprint run — auto-generated handler\n"
                  f"via advisor_auto_extend.py. Validated with advisor test suite.\n"
                  f"Constitutional basis: C-069 (Self-Improvement), C-082 (Build Validation)"])
    if commit.returncode != 0:
        print(f"  advisor_auto_extend: commit failed: {commit.stderr[:200]}")
        return False

    push = run(["git", "push", "origin", "HEAD"])
    if push.returncode != 0:
        print(f"  advisor_auto_extend: push failed (non-fatal): {push.stderr[:200]}")
        return False

    print(f"  advisor_auto_extend: ✅ pushed to main — {error_code} handler live for next run")
    return True


def run_auto_extend(signal: dict | None = None) -> int:
    """
    Main entry point. Called from sprint_monitor.py after classification.
    Returns count of new handlers injected.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  advisor_auto_extend: no API key — skipping (non-blocking)")
        return 0

    if signal is None:
        if not SIGNAL_PATH.exists():
            print("  advisor_auto_extend: no monitor signal — skipping")
            return 0
        signal = json.loads(SIGNAL_PATH.read_text(encoding="utf-8"))

    unknown_pairs = _extract_unknown_codes_from_signal(signal)
    if not unknown_pairs:
        print("  advisor_auto_extend: no new unknown error codes found")
        return 0

    print(f"  advisor_auto_extend: {len(unknown_pairs)} new error code(s) to auto-extend: "
          f"{[p[0] for p in unknown_pairs]}")

    injected = 0
    for error_code, snippet in unknown_pairs:
        print(f"\n  advisor_auto_extend: generating handler for {error_code}...")
        handler = _generate_handler_via_llm(error_code, snippet, api_key)
        if not handler:
            continue
        if not _validate_handler_syntax(handler, error_code):
            continue
        if not _inject_handler(error_code, handler):
            continue
        # Syntax re-check after injection
        try:
            compile(ADVISOR_PATH.read_text(encoding="utf-8"), str(ADVISOR_PATH), "exec")
        except SyntaxError as e:
            print(f"  advisor_auto_extend: post-injection syntax error — reverting: {e}")
            # Revert: restore from git
            subprocess.run(["git", "checkout", "scripts/sprint_retry_advisor.py"],
                           cwd=REPO_ROOT, capture_output=True)
            continue
        if not _run_tests():
            print(f"  advisor_auto_extend: reverting {error_code} injection (test failure)")
            subprocess.run(["git", "checkout", "scripts/sprint_retry_advisor.py"],
                           cwd=REPO_ROOT, capture_output=True)
            continue
        _commit_and_push(error_code)
        # Add to known codes so we don't re-generate in same run
        _KNOWN_CODES.add(error_code)
        injected += 1

    return injected


if __name__ == "__main__":
    sys.exit(0 if run_auto_extend() >= 0 else 1)
