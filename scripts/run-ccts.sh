#!/usr/bin/env bash
# run-ccts.sh — Constitutional Compliance Test runner for deployed environments
#
# constitutional_basis: C-001, C-023, C-071, C-073
# ib_item: IB-009
# spec: architecture/reference/engineering-standards.md §2 (CCT Framework)
#
# G-07 FIX: This script was referenced in post-deploy-verify.yaml but did not
# exist, causing the post-deploy CCT gate to silently skip. An empty/skipped
# CCT gate is constitutionally indistinguishable from a passing CCT gate.
# This stub exists from Sprint 011; CCT implementations are added in Sprint 012+.
#
# Usage:
#   ./scripts/run-ccts.sh --environment dev --base-url https://dev.waooaw.ai
#   ./scripts/run-ccts.sh --environment qa  --base-url https://qa.waooaw.ai
#   ./scripts/run-ccts.sh --environment prod --base-url https://waooaw.ai
#
# Exit codes:
#   0  All CCTs pass
#   1  One or more CCTs failed (constitutional violation)
#   2  CCT suite is empty (blocked — no promotion without at least CCT-EF-01)
#   3  Environment unreachable (health check failed before CCTs ran)

set -euo pipefail

# ─── Argument parsing ────────────────────────────────────────────────────────
ENVIRONMENT=""
BASE_URL=""
TIMEOUT=30
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --environment) ENVIRONMENT="$2"; shift 2 ;;
    --base-url)    BASE_URL="$2";    shift 2 ;;
    --timeout)     TIMEOUT="$2";     shift 2 ;;
    --verbose)     VERBOSE=true;     shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$ENVIRONMENT" || -z "$BASE_URL" ]]; then
  echo "Usage: run-ccts.sh --environment <env> --base-url <url>" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CCT_DIR="$REPO_ROOT/tests/constitutional"
RESULTS_DIR="$REPO_ROOT/test-results/cct-$ENVIRONMENT-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "═══════════════════════════════════════════════════════════"
echo "  WAOOAW Constitutional Compliance Test Suite"
echo "  Environment : $ENVIRONMENT"
echo "  Base URL    : $BASE_URL"
echo "  Timestamp   : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# ─── Gate 0: CCT suite must be non-empty ────────────────────────────────────
CCT_COUNT=$(find "$CCT_DIR" -name "test_cct_*.py" 2>/dev/null | wc -l)
if [[ "$CCT_COUNT" -eq 0 ]]; then
  echo ""
  echo "❌ CONSTITUTIONAL GATE BLOCKED: No CCT test files found."
  echo "   tests/constitutional/ contains zero test_cct_*.py files."
  echo "   Promotion is prohibited without at least CCT-EF-01 and CCT-HO-01."
  echo "   Sprint 012 (Constitutional Engine skeleton) must add these tests first."
  exit 2
fi
echo "✓ CCT suite: $CCT_COUNT test file(s) found"

# ─── Gate 1: Environment health check ───────────────────────────────────────
echo ""
echo "── Health checks ───────────────────────────────────────────"
HEALTH_FAILED=0
SERVICES=(
  "$BASE_URL/health"       # Business Platform
  "$BASE_URL/ce/health"    # Constitutional Engine
  "$BASE_URL/pr/health"    # Professional Runtime
  "$BASE_URL/ai/health"    # AI Runtime
)

for url in "${SERVICES[@]}"; do
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
  if [[ "$STATUS" == "200" ]]; then
    echo "  ✓ $url → $STATUS"
  else
    echo "  ❌ $url → $STATUS (unreachable or unhealthy)"
    HEALTH_FAILED=1
  fi
done

if [[ "$HEALTH_FAILED" -eq 1 ]]; then
  echo ""
  echo "❌ Environment health check failed. CCTs cannot run against unhealthy services."
  echo "   This does not constitute a CCT failure — it is an infrastructure failure."
  echo "   Check Azure Container Apps logs and raise a P0 incident if needed."
  exit 3
fi

# ─── Gate 2: Run Python CCTs ────────────────────────────────────────────────
echo ""
echo "── Running Python CCTs ─────────────────────────────────────"

# Export environment config for CCT test fixtures
export WAOOAW_TEST_BASE_URL="$BASE_URL"
export WAOOAW_TEST_ENVIRONMENT="$ENVIRONMENT"

CCT_ARGS=(
  "$CCT_DIR"
  "--junit-xml=$RESULTS_DIR/cct-results.xml"
  "-v"
  "--tb=short"
  "--strict-markers"
  "-m" "cct"          # Only run tests marked @pytest.mark.cct
)

if [[ "$VERBOSE" == "true" ]]; then
  CCT_ARGS+=("-s")
fi

cd "$REPO_ROOT"

# Run CCTs — capture exit code without set -e stopping us
PYTHON_CCT_EXIT=0
python -m pytest "${CCT_ARGS[@]}" 2>&1 | tee "$RESULTS_DIR/cct-output.txt" || PYTHON_CCT_EXIT=$?

# ─── Gate 3: Emergency Stop latency (C-001 constitutional floor) ─────────────
echo ""
echo "── Emergency Stop latency (CCT-HO-01 — C-001 floor ≤250ms) ─"
# TODO Sprint 012: implement ws-emergency-stop-test.py once PR WebSocket is live
# The script sends a WebSocket "EMERGENCY_STOP" and measures round-trip time.
# P99 over 10 runs must be ≤ 250ms. Failure = constitutional violation, not a bug.
echo "  ⏳ CCT-HO-01 Emergency Stop: pending Sprint 012 (PR WebSocket implementation)"

# ─── Results summary ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  CCT Suite Results — $ENVIRONMENT"
echo "  Results saved: $RESULTS_DIR/"
echo "═══════════════════════════════════════════════════════════"

if [[ "$PYTHON_CCT_EXIT" -ne 0 ]]; then
  echo ""
  echo "❌ CONSTITUTIONAL COMPLIANCE TEST FAILURE"
  echo "   One or more CCTs failed in $ENVIRONMENT."
  echo "   This is a constitutional violation — not a bug."
  echo "   REQUIRED ACTION: Raise Constitutional Blocker in blockers/"
  echo "   DO NOT promote this build to the next environment."
  echo "   DO NOT apply a manual override — CCT gates have no bypass."
  exit 1
fi

echo "✓ All CCTs passed in $ENVIRONMENT — build is constitutionally compliant"
echo "✓ Eligible for promotion to next environment"
exit 0
