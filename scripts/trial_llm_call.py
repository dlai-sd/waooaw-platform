#!/usr/bin/env python3
"""
Local LLM Trial Script
======================
Tests call_llm() against the real Anthropic API without triggering a full CI run.
Reads ANTHROPIC_API_KEY from environment — never from chat.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 scripts/trial_llm_call.py [task_id]

    task_id defaults to WC012-02 (the task that's been failing).

What it does:
    1. Loads the exact spec + constitutional_check for the task from TASK_HANDLERS
    2. Calls call_llm() with current parameters (thinking mode, budget, max_tokens)
    3. Prints full observability block: REQ / LLM / THINK / RESP / TEXT
    4. If files returned: lists each file and first 100 chars
    5. Does NOT commit, push, open PRs, or mutate any state

Use this to validate a thinking config change locally in ~2 minutes
before triggering an 15-minute CI run.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# ── Validate environment ───────────────────────────────────────────────────────
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("❌ ANTHROPIC_API_KEY not set.")
    print("   Set it in your terminal (NOT in chat):")
    print('   export ANTHROPIC_API_KEY="sk-ant-..."')
    sys.exit(1)

# Set minimal env so runner imports don't crash
os.environ.setdefault("GITHUB_REPO", "dlai-sd/waooaw-platform")

# ── Import runner ──────────────────────────────────────────────────────────────
print("Loading runner...")
from autonomous_sprint_runner import (   # type: ignore[import]
    TASK_HANDLERS, call_llm, parse_llm_files, _build_system_prompt,
    get_branch_context, REPO_ROOT as _REPO,
)

# ── Select task ────────────────────────────────────────────────────────────────
task_id = sys.argv[1] if len(sys.argv) > 1 else "WC012-02"
# Optional: override max_tokens via CLI arg (e.g. python3 trial_llm_call.py WC012-02 14000)
max_tokens_override = int(sys.argv[2]) if len(sys.argv) > 2 else None
handler = TASK_HANDLERS.get(task_id)

if handler is None:
    print(f"❌ No handler for {task_id}. Available: {list(TASK_HANDLERS.keys())}")
    sys.exit(1)

if not callable(handler):
    print(f"❌ {task_id} uses TaskDecomposer (sub-tasks). Trial individual sub-task instead.")
    print(f"   Sub-tasks: {[s.id for s in handler.get('subtasks', [])]}")
    sys.exit(1)

# ── Extract spec from handler lambda ──────────────────────────────────────────
# The handler is: lambda: execute_with_llm(task_id, description, spec_sections, check, hint, max_tokens)
# We need to extract these args. Inspect the closure.
import inspect
closure = inspect.getclosurevars(handler)
# execute_with_llm is called inside the lambda — get its args from __code__
# Simpler: just import and call with introspection via the source
# Fall back: extract from the TASK_HANDLERS source directly
source_file = Path(__file__).parent / "autonomous_sprint_runner.py"
source = source_file.read_text()

# Find the handler definition block for the task
start = source.find(f'"{task_id}": lambda')
if start == -1:
    start = source.find(f"'{task_id}': lambda")

# Extract until the closing ),
block = source[start:start+2000]
lines = block.splitlines()[:30]
print(f"\nHandler definition for {task_id}:")
for line in lines:
    print(f"  {line}")

print()
print("─" * 60)
print(f"Running trial call for: {task_id}")
print("─" * 60)

# ── Build spec content (same as execute_with_llm does) ────────────────────────
# Parse out spec_sections, constitutional_check, model_hint, max_tokens from source
import re

# Extract the execute_with_llm call args from the lambda
spec_match = re.search(
    rf'"{re.escape(task_id)}": lambda[^,]+execute_with_llm\(\s*'
    r'"[^"]+",\s*"([^"]+)",\s*\{([^}]+)\},\s*"([^"]+)"',
    source, re.DOTALL
)

if not spec_match:
    print("Could not auto-parse handler args. Running handler directly...")
    # Last resort: just run the handler and show what call_llm would receive
    print("Use FORCE_TASK env var and a real sprint run for this task.")
    sys.exit(0)

task_description = spec_match.group(1)
# Parse spec_sections dict from source text
spec_text = spec_match.group(2)
spec_pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', spec_text)
spec_sections: dict[str, str] = dict(spec_pairs)

# Build spec content
spec_lines = [f"# Spec context for {task_id}"]
for file_path, section in spec_sections.items():
    full_path = _REPO / file_path
    if full_path.is_file():
        content = full_path.read_text(encoding="utf-8", errors="replace")
        spec_lines.append(f"\n## {file_path}\n{content[:4000]}")
        print(f"  ✅ Spec file loaded: {file_path} ({len(content)} chars)")
    else:
        print(f"  ⚠️  Spec file missing: {file_path}")
spec_content = "\n".join(spec_lines)

# Inject branch context
branch_context = get_branch_context()
if branch_context:
    spec_content += branch_context
    print(f"  Branch context: {len(branch_context.splitlines())} lines")

# ── Run the actual call ────────────────────────────────────────────────────────
print()
print("─" * 60)
print(f"Calling LLM now... (this takes 1-3 minutes)")
print("─" * 60)

response = call_llm(
    task_id=task_id,
    task_description=task_description,
    spec_content=spec_content,
    constitutional_check=spec_match.group(3) if spec_match.group(3) else "",
    model_hint="reasoning",
    max_tokens=max_tokens_override if max_tokens_override else 10000,
    attempt=1,
)
print(f"\nmax_tokens used: {max_tokens_override or 10000} (effective with overhead: {(max_tokens_override or 10000) + 8000})")

# ── Analyse response ───────────────────────────────────────────────────────────
print()
print("─" * 60)
print("TRIAL RESULT")
print("─" * 60)

if not response:
    print("❌ call_llm returned None or empty — check WARN lines above")
    sys.exit(1)

files = parse_llm_files(response)

print(f"Response length: {len(response):,} chars")
print(f"Files parsed:    {len(files)}")
print()

if files:
    print("✅ Files generated:")
    for path, content in files.items():
        print(f"  {path} ({len(content):,} chars)")
        print(f"    → {content[:100].replace(chr(10), ' ')}...")
else:
    print("❌ No <file path='...'> blocks found in response")
    print()
    print("First 800 chars of response:")
    print(response[:800])
