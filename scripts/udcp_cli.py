#!/usr/bin/env python3
# Implements: UDCP standalone local harness (ADR-039 §5 — local iteration loop)
# constitutional_basis: C-082 (compile gate), C-065 (write boundary)
# ib_item: IB-009
"""
UDCP standalone CLI — run the full pipeline locally without GitHub Actions.

Modes
-----
  dry   Grooming → PTR gate → scaffold only. No LLM call, no write of logic.
        Scaffold stubs ARE written so you can inspect them.  Free, instant.
  mock  Full pipeline with a stub LLM that fills logic markers with `pass`.
        No ANTHROPIC_API_KEY needed.  Good for end-to-end wiring tests.
  live  Full pipeline with real Anthropic API.  Requires ANTHROPIC_API_KEY.

Examples
--------
  # Inspect what UDCP would scaffold for WC027-01a (no cost, no API key):
  python scripts/udcp_cli.py --task-id WC027-01a --mode dry

  # Full mock run — verify wiring without spending tokens:
  python scripts/udcp_cli.py --task-id WC027-01a --mode mock

  # Real cheap run with Haiku (~$0.001):
  python scripts/udcp_cli.py --task-id WC027-01a --mode live --model haiku

  # Docker (no API key):
  docker compose run --rm udcp-runner python scripts/udcp_cli.py \\
      --task-id WC027-01a --mode dry

  # Docker (live, key passed via env):
  ANTHROPIC_API_KEY=sk-... docker compose run --rm udcp-runner \\
      python scripts/udcp_cli.py --task-id WC027-01a --mode live
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Allow running as `python scripts/udcp_cli.py` from repo root
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from runner.udcp_orchestrator import UDCPOrchestrator, TaskResult  # noqa: E402

# ── ANSI colours ─────────────────────────────────────────────────────────────

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _c(colour: str, text: str) -> str:
    return f"{colour}{text}{_RESET}" if sys.stdout.isatty() else text


# ── Mock LLM stub ─────────────────────────────────────────────────────────────

_FILLER_BLOCK_RE = re.compile(
    r"# \[WAOOAW_LOGIC_FILLER_START\].*?# \[WAOOAW_LOGIC_FILLER_END\]",
    re.DOTALL,
)
_SCAFFOLD_CODE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
_FILE_PATH_RE = re.compile(r'<file path="([^"]+)">')


def _mock_llm_fn(
    *,
    task_id: str,
    prompt: str,
    model_hint: str = "auto",
    max_tokens: int = 8000,
    attempt: int = 1,
    **_kwargs: object,
) -> str | None:
    """
    Stub LLM: Track 1 fills LOGIC_FILLER markers with `pass  # [MOCK_LOGIC]`.
    Track 2 returns the stub unchanged (no-op implementation).
    """
    path_m = _FILE_PATH_RE.search(prompt)
    if path_m:
        # Track 1: scaffold block → replace filler sections
        rel_path = path_m.group(1)
        code_m = _SCAFFOLD_CODE_RE.search(prompt)
        content = code_m.group(1) if code_m else ""
        filled = _FILLER_BLOCK_RE.sub("pass  # [MOCK_LOGIC]", content)
        return f'<file path="{rel_path}">\n{filled}\n</file>'

    # Track 2: return stub unchanged
    stub_m = _SCAFFOLD_CODE_RE.search(prompt)
    if stub_m:
        return f"```python\n{stub_m.group(1)}\n```"
    return None


# ── Scope text resolution ─────────────────────────────────────────────────────

def _load_scope(scope_arg: str | None, task_id: str, wc_file: str | None) -> str:
    """
    Resolve scope text from:
    1. --scope (inline string or @file path)
    2. --wc (work-contract markdown — extract row for task_id)
    3. Auto-detect work-contract from task_id prefix (e.g. WC027 → WC-027-*.md)
    """
    if scope_arg:
        if scope_arg.startswith("@"):
            return Path(scope_arg[1:]).read_text(encoding="utf-8")
        return scope_arg

    # Resolve work-contract file
    wc_path: Path | None = None
    if wc_file:
        wc_path = _REPO_ROOT / wc_file
    else:
        # Auto-detect: WC027-01a → WC-027
        prefix_m = re.match(r"WC(\d+)", task_id, re.IGNORECASE)
        if prefix_m:
            num = prefix_m.group(1)
            candidates = list((_REPO_ROOT / "work-contracts").glob(f"WC-{num}-*.md"))
            if candidates:
                wc_path = candidates[0]

    if wc_path and wc_path.is_file():
        text = wc_path.read_text(encoding="utf-8")
        # Find the row whose first cell matches task_id
        for line in text.splitlines():
            if f"| {task_id} |" in line or f"| {task_id} " in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    return parts[1]  # scope column

    print(
        _c(_YELLOW, f"  WARN: could not auto-resolve scope for {task_id}. "
           "Pass --scope <text> or --wc <path>.")
    )
    return f"Implement {task_id}"


# ── Main ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="UDCP standalone local harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--task-id", required=True, help="e.g. WC027-01a")
    p.add_argument(
        "--mode", choices=["dry", "mock", "live"], default="dry",
        help="dry=scaffold only | mock=stub LLM | live=real API (default: dry)",
    )
    p.add_argument("--scope", default=None, help="Scope text, or @path/to/file.txt")
    p.add_argument("--wc", default=None, help="Path to work-contract markdown (optional)")
    p.add_argument("--sprint-id", default="", help="Sprint ID (e.g. WC-027)")
    p.add_argument(
        "--model", default="reasoning",
        choices=["reasoning", "auto", "haiku", "sonnet"],
        help="Model hint (live mode only, default: reasoning)",
    )
    p.add_argument("--max-tokens", type=int, default=8000)
    p.add_argument(
        "--show-prompt", action="store_true",
        help="In dry mode: print the full scaffold content to stdout",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    scope_text = _load_scope(args.scope, args.task_id, args.wc)
    sprint_id = args.sprint_id or re.sub(r"-\d+\w*$", "", args.task_id)

    print(_c(_BOLD, f"\n{'=' * 60}"))
    print(_c(_BOLD, f"  UDCP CLI — mode={args.mode}  task={args.task_id}"))
    print(_c(_BOLD, f"{'=' * 60}\n"))

    # ── Build orchestrator ───────────────────────────────────────────────────
    if args.mode == "dry":
        orch = UDCPOrchestrator(dry_run=True, repo_root=_REPO_ROOT)
    elif args.mode == "mock":
        orch = UDCPOrchestrator(llm_fn=_mock_llm_fn, repo_root=_REPO_ROOT)
    else:  # live
        orch = UDCPOrchestrator(repo_root=_REPO_ROOT)

    print(_c(_CYAN, "  [1] Running UDCP pipeline..."))

    result: TaskResult = orch.execute_task(
        task_id=args.task_id,
        scope_text=scope_text,
        sprint_id=sprint_id,
        model_hint=args.model,
        max_tokens=args.max_tokens,
    )

    # ── Report ───────────────────────────────────────────────────────────────
    print()
    print(_c(_BOLD, "  Result:"))
    status = _c(_GREEN, "SUCCESS") if result.success else _c(_RED, "FAILURE")
    print(f"    status      : {status}")
    print(f"    track       : {result.track}")
    print(f"    dry_run     : {result.dry_run}")
    print(f"    files       : {result.files_written or '(none)'}")

    if not result.success:
        print(f"    error_type  : {_c(_RED, result.error_type or '')}")
        print(f"    error       : {result.error_snippet or ''}")

    if result.dry_run and result.prompt_preview and args.show_prompt:
        print()
        print(_c(_CYAN, "  ── Scaffold preview ──"))
        print(result.prompt_preview)

    if result.dry_run and result.files_written:
        print()
        print(_c(_YELLOW, "  Dry-run: scaffolds rendered in memory only — no files written to disk."))
        print(_c(_YELLOW, "  Run --mode mock to write stubs + fill logic (no API cost)."))
        for f in result.files_written:
            print(f"    (would write) {_REPO_ROOT / f}")

    print()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
