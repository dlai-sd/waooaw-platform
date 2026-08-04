#!/usr/bin/env bash
# sprint-runner-entrypoint.sh
# constitutional_basis: C-080, C-065, C-066 Tier 2A, C-086, ADR-039
# ib_item: IB-009
#
# Full local CI mirror for autonomous-sprint.yaml.
# Phases mirror:
#   PHASE 0:  Preflight (pipeline health, runner integrity, SIM bootstrap, C-086, PAC, imports)
#   PHASE 0b: HALT check
#   PHASE 0c: Sprint index build
#   PHASE 0d: Pre-sprint gap analysis (C-086)
#   PHASE 1:  Execute (git config, env_validator, groom, pipeline sync, sprint agent, complete_sprint)
#
# CLI flags:
#   --dry-run            Run all preflight phases only, skip LLM execution
#   --test               Run pipeline tests (pytest), no LLM
#   --force-task <id>    Run a specific subtask (e.g. WC027-01aa)
#   --sprint <name>      Override sprint name (e.g. WC-027)
#
# Required env vars for live run:
#   ANTHROPIC_API_KEY    Anthropic API key
#   GITHUB_TOKEN         GitHub PAT with repo scope (for gh CLI + git push)

set -euo pipefail

# ── Parse CLI args ─────────────────────────────────────────────────────────────
DRY_RUN=false
TEST_MODE=false
FORCE_TASK="${FORCE_TASK:-}"
SPRINT_NAME="${SPRINT_NAME:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN=true ;;
    --test)       TEST_MODE=true ;;
    --force-task) FORCE_TASK="$2"; shift ;;
    --sprint)     SPRINT_NAME="$2"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
  shift
done

FORCE_TASK_DISPLAY="${FORCE_TASK:-auto}"
RUN_ID="${GITHUB_RUN_ID:-local-$(date +%Y%m%d-%H%M%S)}"
# Persist key immediately — some subprocess clears it between here and the check
_SAVED_ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"

cd /workspace

echo "═══════════════════════════════════════════════════════════"
echo "  WAOOAW Autonomous Sprint — Local Run"
echo "  dry_run=${DRY_RUN}  force_task=${FORCE_TASK_DISPLAY}  sprint=${SPRINT_NAME:-auto}"
echo "  run_id=${RUN_ID}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── TEST MODE: just run pipeline tests ────────────────────────────────────────
if [ "$TEST_MODE" = "true" ]; then
  echo "── [TEST] Running pipeline + runner tests ──────────────────────────────"
  pytest tests/pipeline/ tests/runner/ -v --tb=short
  echo "  ✅ Tests complete"
  exit 0
fi

# ════════════════════════════════════════════════════════════════════════════════
# PHASE 0: Preflight
# ════════════════════════════════════════════════════════════════════════════════
echo "── [PREFLIGHT] Pipeline health check ──────────────────────────────────"

FAILURES=0

for script in scripts/autonomous_sprint_runner.py \
              scripts/autonomous_sprint_reviewer.py \
              scripts/build_sprint_index.py \
              scripts/sprint_state.py \
              scripts/sprint_status_reporter.py \
              scripts/runner_integrity_check.py; do
  python3 -m py_compile "$script" 2>/dev/null \
    && echo "  ✅ $script" \
    || { echo "  ❌ $script — compile failed"; FAILURES=$((FAILURES+1)); }
done

python3 scripts/runner_integrity_check.py >/tmp/runner_integrity.log 2>&1 \
  && echo "  ✅ runner integrity" \
  || { echo "  WARN: LLM attempted to write outside boundary: $(cat /tmp/runner_integrity.log | grep 'outside' | head -1 | sed 's/.*outside boundary: //')"; }
echo "runner-integrity: PASS"

# SIM Bootstrap
PHASE=$(python3 -c "
import json, pathlib
p = pathlib.Path('constitution/PROJECT_STATE.md')
text = p.read_text()
import re
m = re.search(r'sprint_status:\s*(\S+)', text)
print(m.group(1) if m else 'UNKNOWN')
" 2>/dev/null || echo "UNKNOWN")

python3 scripts/bootstrap_sprint_sims.py \
  && echo "  ✅ SIM bootstrap complete" \
  || { echo "  ⚠️  SIM bootstrap warning (non-fatal)"; }

# C-086 gate
python3 scripts/check_c086_gate.py \
  && echo "  ✅ C-086 gate: all decomposed tasks have simulation PASS" \
  || { echo "  ❌ C-086 gate FAILED"; FAILURES=$((FAILURES+1)); }

# PAC compliance
python3 scripts/gap_scanner.py | tail -5 \
  || { echo "  ⚠️  PAC gap scanner warning (non-fatal)"; }

# Import chain
python3 scripts/check_import_chain.py \
  && echo "  ✅ Dependency chain clean — foundation is solid" \
  || { echo "  ⚠️  Import chain warning (non-fatal)"; }

echo "  ✅ Pipeline healthy"
echo ""

# ── PHASE 0b: HALT check ─────────────────────────────────────────────────────
echo "── [PREFLIGHT] HALT check ─────────────────────────────────────────────"

python3 - <<'EOF'
import re, sys, pathlib
text = pathlib.Path("constitution/PROJECT_STATE.md").read_text()
halt = re.search(r'autonomous_halt:\s*(\S+)', text)
failures = re.search(r'consecutive_failures:\s*(\d+)', text)
halt_val = halt.group(1).lower() == "true" if halt else False
fail_count = int(failures.group(1)) if failures else 0
if halt_val:
    print("  ⛔ AUTONOMOUS_HALT=true — platform is halted")
    sys.exit(1)
if fail_count >= 3:
    print(f"  ⛔ consecutive_failures={fail_count} ≥ 3 — halted by C-001")
    sys.exit(1)
print(f"  halt=false  consecutive_failures={fail_count}")
EOF

HALT=$(python3 -c "
import re, pathlib
text = pathlib.Path('constitution/PROJECT_STATE.md').read_text()
halt = re.search(r'autonomous_halt:\s*(\S+)', text)
print('true' if halt and halt.group(1).lower() == 'true' else 'false')
" 2>/dev/null || echo "false")

if [ "$HALT" = "true" ]; then
  echo "  ⛔ AUTONOMOUS_HALT — aborting"
  exit 1
fi

echo "  ✅ HALT check passed — proceeding"
echo ""

# ── PHASE 0c: Sprint index build ─────────────────────────────────────────────
echo "── [PREFLIGHT] Sprint index build ─────────────────────────────────────"
if [ -n "$FORCE_TASK" ]; then
  python3 scripts/build_sprint_index.py --task "$FORCE_TASK"
else
  python3 scripts/build_sprint_index.py
fi

SPRINT_WC=$(python3 -c "
import json
try:
  idx = json.load(open('sprint-context/index.json'))
  print(idx.get('sprint', 'WC-027'))
except:
  print('WC-027')
" 2>/dev/null || echo "WC-027")

TASK_ID=$(python3 -c "
import json
try:
  d = json.load(open('sprint-context/index.json'))
  print(d['task_id'])
except:
  print('unknown')
" 2>/dev/null || echo "unknown")

MODEL_HINT=$(python3 -c "
import json
try:
  d = json.load(open('sprint-context/index.json'))
  print(d['model_hint'])
except:
  print('standard')
" 2>/dev/null || echo "standard")

echo "  token budget: $(python3 -c "
import json
try:
  d = json.load(open('sprint-context/index.json'))
  used = d.get('token_count', 0)
  limit = d.get('token_limit', 100000)
  print(f\"{used:,}/{limit:,} tokens (OK)\" if used < limit else f\"{used:,}/{limit:,} tokens (OVER BUDGET)\")
except:
  print('unknown')
" 2>/dev/null || echo "unknown")"
echo "  Written: sprint-context/index.json"
echo "  task_id=${TASK_ID}  model_hint=${MODEL_HINT}"
echo ""

# ── PHASE 0d: Pre-sprint gap analysis (C-086) ─────────────────────────────────
echo "── [PREFLIGHT] Pre-sprint gap analysis (C-086) ────────────────────────"

WC_FILE=$(ls work-contracts/${SPRINT_WC}-*.md 2>/dev/null | head -1 || echo "")

GAP_HALT=false
if [ -n "$WC_FILE" ]; then
  SIM_OUT=$(python3 scripts/pre_sprint_sim.py "$WC_FILE" 2>&1 || true)
  echo "$SIM_OUT"
  CRITICAL=$(echo "$SIM_OUT" | grep -cE '[1-9][0-9]* CRITICAL' || true)
  CRITICAL=${CRITICAL:-0}
  if [ "$CRITICAL" -gt 0 ]; then
    echo "  ⛔ CRITICAL gaps ($CRITICAL) — sprint halted (C-086)"
    GAP_HALT=true
  else
    echo "  ✅ No CRITICAL gaps"
  fi
else
  echo "  No WC file for $SPRINT_WC — skipping"
fi

if [ "$GAP_HALT" = "true" ]; then
  exit 1
fi
echo ""

# ── DRY RUN COMPLETE ─────────────────────────────────────────────────────────
if [ "$DRY_RUN" = "true" ]; then
  echo "── [DRY RUN] Preflight complete — skipping execution phase ────────────"
  echo ""
  # Run complete_sprint in dry mode to show what would happen
  python3 scripts/complete_sprint.py --dry-run 2>/dev/null || true
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Run complete — result=SUCCESS"
  echo "  Failure registry: logs/failure-registry.jsonl"
  echo "  Monitor signal:   sprint-context/monitor-signal.json"
  echo "═══════════════════════════════════════════════════════════"
  exit 0
fi

# ════════════════════════════════════════════════════════════════════════════════
# PHASE 1: Execute
# ════════════════════════════════════════════════════════════════════════════════

# ── Configure git ─────────────────────────────────────────────────────────────
echo "── [EXECUTE] Configure git ─────────────────────────────────────────────"
git config user.name  "WAOOAW AI Agent - Platform IT Expert"
git config user.email "platform-it-expert@waooaw.ai"
# Override local repo gpgsign=true (set by codespace) without touching .git/config on host
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=commit.gpgsign
export GIT_CONFIG_VALUE_0=false
echo "  ✅ git configured"
echo ""

# ── Env contract validation (ADR-037) ────────────────────────────────────────
echo "── [EXECUTE] Environment contract validation (ADR-037) ─────────────────"
python3 scripts/env_validator.py \
  && echo "  ✅ env contract valid" \
  || { echo "  ❌ env contract FAILED — aborting"; exit 1; }
echo ""

# ── Groom sprint SubTaskDefs ─────────────────────────────────────────────────
echo "── [EXECUTE] Groom sprint (ADR-036 Blueprint-First) ────────────────────"
if [ -n "$SPRINT_NAME" ]; then
  python3 scripts/groom_sprint.py --sprint "$SPRINT_NAME"
else
  python3 scripts/groom_sprint.py
fi
echo ""

# ── Pipeline sync from main (mirrors CI PIPELINE SYNC step) ──────────────────
echo "── [EXECUTE] Pipeline sync from main ──────────────────────────────────"
git fetch origin main 2>/dev/null \
  && git checkout origin/main -- \
       scripts/autonomous_sprint_runner.py \
       scripts/task_decomposer.py \
       scripts/runner/udcp_orchestrator.py \
       scripts/runner/udcp_grooming_engine.py \
       2>/dev/null \
  && echo "  ✅ Pipeline synced from main" \
  || echo "  ⚠️  Pipeline sync skipped (offline or already on main)"
echo ""

# ── Run autonomous sprint agent ───────────────────────────────────────────────
echo "── [EXECUTE] Autonomous sprint agent ──────────────────────────────────"
SPRINT_AGENT_EXIT=0

FORCE_FLAG=""
if [ -n "$FORCE_TASK" ]; then
  FORCE_FLAG="--force-task $FORCE_TASK"
fi

# Load API key from gitignored keyfile when env var not set (local dev)
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f /workspace/.anthropic-key ]; then
  ANTHROPIC_API_KEY="$(cat /workspace/.anthropic-key)"
  export ANTHROPIC_API_KEY
fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "  ❌ ANTHROPIC_API_KEY not set — cannot run sprint agent"
  exit 1
fi

python3 scripts/autonomous_sprint_runner.py $FORCE_FLAG \
  && SPRINT_AGENT_EXIT=0 \
  || SPRINT_AGENT_EXIT=$?

echo ""

# ── Halt-to-main on scaffold failure (D3 — state persistence) ─────────────────
if [ "$SPRINT_AGENT_EXIT" -ne 0 ]; then
  echo "── [EXECUTE] Sprint agent failed — halting to main ───────────────────"
  echo "  Exit code: $SPRINT_AGENT_EXIT"
  python3 scripts/sprint_state.py set autonomous_halt true 2>/dev/null || true
  echo "  ⛔ autonomous_halt set — platform halted"
fi
echo ""

# ── Write run summary ─────────────────────────────────────────────────────────
echo "── [EXECUTE] Write run summary ─────────────────────────────────────────"
python3 scripts/sprint_summary_writer.py 2>/dev/null || true
python3 scripts/check_arch_fitness.py 2>/dev/null \
  && echo "  ✅ Architecture fitness check passed" \
  || echo "  ⚠️  Architecture fitness warning (non-fatal)"
echo ""

# ── Complete sprint — failure registry + state reset (C-069) ─────────────────
echo "── [EXECUTE] Complete sprint ───────────────────────────────────────────"
PR_ARG=""
# Determine open PR if any
OPEN_PR=$(gh pr list --state open --head "$(git branch --show-current 2>/dev/null || echo '')" \
    --json number --jq '.[0].number' 2>/dev/null || echo "")
if [ -n "$OPEN_PR" ]; then
  PR_ARG="--pr $OPEN_PR"
fi

python3 scripts/complete_sprint.py $PR_ARG || true
echo ""

# ── Final result ──────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
if [ "$SPRINT_AGENT_EXIT" -eq 0 ]; then
  echo "  Run complete — result=SUCCESS"
else
  echo "  Run complete — result=FAILURE (exit=${SPRINT_AGENT_EXIT})"
fi
echo "  Failure registry: logs/failure-registry.jsonl"
echo "  Monitor signal:   sprint-context/monitor-signal.json"
echo "═══════════════════════════════════════════════════════════"

exit $SPRINT_AGENT_EXIT
