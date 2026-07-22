#!/usr/bin/env python3
"""
build_sprint_index.py
constitutional_basis: C-066 Tier 2A, C-071 (Quality), C-076 (Coverage)
ib_item: IB-009

FinOps Context Injector — runs BEFORE the Copilot agent loop in autonomous-sprint.yaml.

PURPOSE: Maps current sprint task to the MINIMUM spec content needed.
CRITICAL DESIGN RULE (GAP-SIM-01/02 from SIM-022):
  Do NOT load full spec files. Load only the SECTION relevant to the task.
  ai-runtime.md = 11,575 tokens alone. A free model (llama-3.1-8b) has 8K total.
  Full-file loading = model sees 0 spec content after BOOTSTRAP fills context.
  Section targeting = model gets the relevant 1-2K tokens it actually needs.

TOKEN BUDGET (enforced):
  FREE_MODEL_CONTEXT  = 8,192  (llama-3.1-8b, phi-3.5-mini — GitHub Models free tier)
  RESERVED_FOR_BOOT   = 3,500  (AGENT-ENTRY: ~3.4K — always loaded before task context)
  MAX_TASK_CONTEXT    = 4,500  (hard cap on total spec_files content)
  MAX_TOKENS_PER_FILE = 1,500  (single file cap — triggers section targeting)

Usage:
    python3 scripts/build_sprint_index.py
    python3 scripts/build_sprint_index.py --task WC011-04
    python3 scripts/build_sprint_index.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
INDEX_OUTPUT = REPO_ROOT / "sprint-context" / "index.json"

# ── Token budget constants (SIM-022 GAP-SIM-01/02 fix) ───────────────────────
FREE_MODEL_CONTEXT  = 8_192   # llama-3.1-8b / phi-3.5-mini hard context limit
RESERVED_FOR_BOOT   = 3_500   # AGENT-ENTRY.md always loaded first (~3.4K tokens)
MAX_TASK_CONTEXT    = 4_500   # hard cap for all spec_files combined
MAX_TOKENS_PER_FILE = 1_500   # single file triggers section targeting above this

# ── Task → Spec section mapping ───────────────────────────────────────────────
# CRITICAL: spec_sections maps file → relevant section heading (not whole file).
# Agent reads: {file}#{section} → extracts only that section.
# This keeps per-task context under MAX_TASK_CONTEXT even for large spec files.
TASK_CONTEXT_MAP: dict[str, dict] = {
    # WC-011: Infrastructure Foundation (rule-based tasks — model_hint: auto)
    "WC011-01": {
        "description": "Validate docker-compose.yml",
        "model_hint": "none",          # Pure Python validation — NO LLM needed
        "spec_sections": {
            "docker-compose.yml": "full",   # 730 tokens — fits
        },
        "relevant_claims": ["C-067", "C-004"],
        "relevant_adrs": ["ADR-015"],
        "constitutional_check": "Verify docker-compose.yml services match ADR-015 Temporal deployment strategy",
    },
    "WC011-02": {
        "description": "Validate DB migration scripts 01-09",
        "model_hint": "none",
        "spec_sections": {
            "infrastructure/postgres/": "list",  # directory listing only
        },
        "relevant_claims": ["C-007", "C-027", "C-059"],
        "relevant_adrs": ["ADR-011"],
        "constitutional_check": "Verify migrations are additive-only (C-007/C-027: no destructive ops on constitutional schema)",
        "note": "data-architecture.md not yet created (IB-007 output pending IB-009). Use infrastructure/postgres/ listings.",
    },
    "WC011-03": {
        "description": "Validate Keycloak realm import",
        "model_hint": "none",
        "spec_sections": {
            "infrastructure/keycloak/": "list",
        },
        "relevant_claims": ["C-005", "C-059"],
        "relevant_adrs": ["ADR-008"],
        "constitutional_check": "Verify realm import includes Google IDP config (ADR-008) and tenant_id claim (ADR-003)",
    },
    "WC011-04": {
        "description": "Create src/ directory scaffold with C-059 headers",
        "model_hint": "auto",          # Simple file creation — cheap model sufficient
        "spec_sections": {
            # AGENT-ENTRY.md is already in global_context — do NOT duplicate here
            # Section targeting: only the C-059 header requirement, not all 7K tokens
            "standards/CODING-STANDARDS.md": "§1.5 Structured Comments",
            "standards/runtime-professional.md": "§Decision Space,§Output Standards",
        },
        "relevant_claims": ["C-059", "C-065", "C-073"],
        "relevant_adrs": ["ADR-016"],
        "constitutional_check": "Every src/ README must have: '# Implements: architecture/reference/components/{service}.md' header",
    },
    "WC011-05": {
        "description": "Verify setup.sh and get-dev-token.sh",
        "model_hint": "none",
        "spec_sections": {
            "scripts/setup.sh": "full",         # 1,967 tok — fits
            "scripts/get-dev-token.sh": "full", # 415 tok — fits
        },
        "relevant_claims": ["C-059"],
        "relevant_adrs": [],
        "constitutional_check": "Scripts must be executable and idempotent (safe to re-run)",
    },
    "WC011-07": {
        "description": "GitHub Actions secrets documentation",
        "model_hint": "none",
        "spec_sections": {
            "infrastructure/GITHUB-SECRETS.md": "full",  # if exists
        },
        "relevant_claims": ["C-059", "C-066"],
        "relevant_adrs": ["ADR-014"],
        "constitutional_check": "All secrets must be listed; none hardcoded in workflow YAML",
    },
    # WC-012: Constitutional Engine skeleton (code authoring — model_hint: reasoning)
    "WC012-01": {
        "description": "CE project scaffold (.NET 9 gRPC service)",
        "model_hint": "reasoning",
        "spec_sections": {
            # Section targeting: key sections only, not full 7K CODING-STANDARDS
            "architecture/reference/components/constitutional-engine.md": "full",  # 1,289 tok — fits
            "architecture/reference/proto/constitutional_service.proto": "§ValidateActionRequest,§ValidateActionResponse,§ConstitutionalService",
            "standards/CODING-STANDARDS.md": "§2.1 Tools,§2.2 Naming Conventions,§1.5 Structured Comments,§7.5 Code Coverage",
            "standards/runtime-professional.md": "full",  # 1,860 tok — fits
        },
        "relevant_claims": ["C-023", "C-041", "C-059", "C-072", "C-076"],
        "relevant_adrs": ["ADR-001", "ADR-007"],
        "constitutional_check": "Every .cs file: header comment with Constitutional basis + ADR reference. Tests alongside code (C-076 ≥90%).",
    },
    "WC012-02": {
        "description": "CE ValidateAction RPC + unit tests (≥90% coverage)",
        "model_hint": "reasoning",
        "spec_sections": {
            "architecture/reference/components/constitutional-engine.md": "§ValidateAction,§Decision Space Evaluation",
            "architecture/reference/ce-validate-action-evaluators.md": "full",  # focused spec
            "standards/CODING-STANDARDS.md": "§2.3 Async Rules,§2.4 Error Handling,§7.1 AAA Pattern,§7.4 Property-Based Tests,§7.5 Code Coverage",
            "tests/QA-STRATEGY.md": "§4 Coverage Requirements,§5.1 Unit Tests",
        },
        "relevant_claims": ["C-023", "C-041", "C-059", "C-071", "C-076"],
        "relevant_adrs": ["ADR-001"],
        "constitutional_check": "ValidateAction MUST record evidence before returning success (C-023 Evidence First).",
    },
    "WC012-03": {
        "description": "CE Evidence First record + CCT-EF-01",
        "model_hint": "reasoning",
        "spec_sections": {
            "architecture/reference/components/constitutional-engine.md": "§Evidence First,§Audit Ledger",
            "architecture/reference/data/": "§constitutional schema",
            "standards/CODING-STANDARDS.md": "§7.1 AAA Pattern,§7.5 Code Coverage",
            "tests/QA-STRATEGY.md": "§5.4 Constitutional Compliance Tests",
        },
        "relevant_claims": ["C-007", "C-023", "C-027", "C-059", "C-076"],
        "relevant_adrs": ["ADR-001", "ADR-011"],
        "constitutional_check": "CCT-EF-01: evidence recorded BEFORE success returned. Append-only ledger (C-007/C-027).",
    },
}

# Global context always injected (condensed — not full corpus)
GLOBAL_CONTEXT_FILES = [
    "constitution/AGENT-ENTRY.md",   # 3,438 tokens — mandatory routing + current state
    "adr/ADR-INDEX.md",              # 2,269 tokens — all 29 ADRs in 36 lines
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_sprint_state() -> dict[str, str]:
    content = STATE_FILE.read_text(encoding="utf-8")
    match = re.search(r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```", content, re.DOTALL)
    if not match:
        return {}
    state: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.split("#")[0].strip()
        if ":" in line:
            k, _, v = line.partition(":")
            state[k.strip()] = v.strip().strip('"').strip("'")
    return state


def estimate_tokens(path: str) -> int:
    """Estimate token count for a file (4 chars ≈ 1 token)."""
    p = REPO_ROOT / path
    if p.is_file():
        return len(p.read_text(encoding="utf-8", errors="replace")) // 4
    return 0


def resolve_spec_sections(spec_sections: dict[str, str]) -> tuple[list[dict], int]:
    """
    Resolve spec_sections to loadable entries with token estimates.
    Flags files that exceed MAX_TOKENS_PER_FILE with section targeting instructions.
    Returns (resolved_entries, total_estimated_tokens).
    """
    resolved = []
    total_tokens = 0

    for file_path, section in spec_sections.items():
        p = REPO_ROOT / file_path
        exists = p.exists()
        tokens = estimate_tokens(file_path) if exists and p.is_file() else 0

        if not exists:
            resolved.append({
                "file": file_path,
                "section": section,
                "status": "MISSING — skip this file, task may not require it yet",
                "tokens": 0,
            })
            continue

        if tokens > MAX_TOKENS_PER_FILE and section == "full":
            resolved.append({
                "file": file_path,
                "section": "TOO_LARGE — use targeted section read instead of full file",
                "status": f"WARNING: {tokens:,} tokens exceeds {MAX_TOKENS_PER_FILE:,} limit for free models. Read only the section specified in the task.",
                "tokens": min(tokens, MAX_TOKENS_PER_FILE),
            })
            total_tokens += MAX_TOKENS_PER_FILE
        elif tokens > MAX_TOKENS_PER_FILE and section != "full":
            resolved.append({
                "file": file_path,
                "section": section,
                "status": f"LARGE FILE — read section '{section}' only (~{min(tokens//10, MAX_TOKENS_PER_FILE)} tokens estimated)",
                "tokens": min(tokens // 10, MAX_TOKENS_PER_FILE),
            })
            total_tokens += min(tokens // 10, MAX_TOKENS_PER_FILE)
        else:
            resolved.append({
                "file": file_path,
                "section": section,
                "status": f"OK — {tokens:,} tokens",
                "tokens": tokens,
            })
            total_tokens += tokens

    return resolved, total_tokens


def build_index(task_id: str) -> dict:
    sprint_state = parse_sprint_state()
    context = TASK_CONTEXT_MAP.get(task_id, {})

    spec_entries, task_tokens = resolve_spec_sections(context.get("spec_sections", {}))

    # Token budget check
    global_tokens = sum(estimate_tokens(f) for f in GLOBAL_CONTEXT_FILES)
    total_tokens = global_tokens + task_tokens
    budget_ok = total_tokens <= FREE_MODEL_CONTEXT

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": sprint_state.get("current_sprint", "unknown"),
        "platform_phase": sprint_state.get("platform_phase", "SPEC"),
        "task_id": task_id,
        "task_description": context.get("description", "unknown task"),
        "model_hint": context.get("model_hint", "reasoning"),
        "constitutional_check": context.get("constitutional_check", ""),

        # Token budget (SIM-022 GAP-SIM-01/02 fix)
        "token_budget": {
            "free_model_limit": FREE_MODEL_CONTEXT,
            "global_context_tokens": global_tokens,
            "task_context_tokens": task_tokens,
            "total_tokens": total_tokens,
            "budget_ok": budget_ok,
            "warning": None if budget_ok else (
                f"OVERFLOW: {total_tokens:,} tokens exceeds free model limit ({FREE_MODEL_CONTEXT:,}. "
                f"Use section targeting or a reasoning model."
            ),
        },

        "finops_rule": (
            "Read ONLY the listed sections, not full files. "
            f"Total context must stay under {FREE_MODEL_CONTEXT:,} tokens for zero-cost execution. "
            "If token_budget.budget_ok=false, escalate to reasoning model."
        ),

        "global_context": GLOBAL_CONTEXT_FILES,
        "spec_sections": spec_entries,
        "relevant_claims": context.get("relevant_claims", []),
        "relevant_adrs": context.get("relevant_adrs", []),

        "excluded_from_workspace": [
            "simulation/*", "reviews/*", "blockers/*", "pmo/*", "legal/*",
            "knowledge/claims/*", "architecture/100k/*", "architecture/32k/*",
            "constitution/CONSTITUTION.md", "constitution/GENESIS.md",
            "constitution/ORGANIZATION.md", "constitution/PROJECT_STATE_ARCHIVE.md",
        ],

        "tasks_remaining": sprint_state.get("tasks_remaining", []),
    }


def write_copilotignore(excluded: list[str]) -> None:
    ignore_path = REPO_ROOT / ".copilotignore"
    lines = [
        "# Auto-generated by build_sprint_index.py — regenerated each sprint run",
        "# constitutional_basis: C-066, FinOps token budget (SIM-022)",
        "",
    ] + excluded + [""]
    ignore_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="Force task ID")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-copilotignore", action="store_true")
    args = parser.parse_args()

    task_id = args.task
    if not task_id:
        state = parse_sprint_state()
        remaining = state.get("tasks_remaining", [])
        task_id = remaining[0] if isinstance(remaining, list) and remaining else None

    if not task_id:
        print("ERROR: No task ID. Pass --task or ensure tasks_remaining is set.")
        sys.exit(1)

    print(f"Building sprint context index: task={task_id}")
    index = build_index(task_id)

    budget = index["token_budget"]
    print(f"  model_hint: {index['model_hint']}")
    print(f"  token budget: {budget['total_tokens']:,}/{budget['free_model_limit']:,} tokens "
          f"({'OK' if budget['budget_ok'] else 'OVERFLOW — check spec sections'})")
    if budget.get("warning"):
        print(f"  WARNING: {budget['warning']}")

    if args.dry_run:
        print(json.dumps(index, indent=2))
        return

    INDEX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    INDEX_OUTPUT.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"  Written: {INDEX_OUTPUT.relative_to(REPO_ROOT)}")

    if not args.no_copilotignore:
        write_copilotignore(index["excluded_from_workspace"])


if __name__ == "__main__":
    main()
