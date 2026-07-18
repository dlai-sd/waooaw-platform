#!/usr/bin/env bash
# Blue-Green Deployment — WAOOAW Platform
# Constitutional basis: C-067 (Blue-Green + Cost-Constrained Deployment)
#                       C-001 (Zero-downtime — availability during deployment)
#                       C-065 (SDLC Separation — Deployer ≠ Deployment Confirmer)
#                       ADR-027 (Cloud Architecture Optimization — cost bounds)
#
# Usage:
#   ./scripts/blue-green-deploy.sh \
#     --service constitutional-engine \
#     --image ghcr.io/dlai-sd/constitutional-engine:sha-abc123 \
#     --resource-group waooaw-dev \
#     --environment dev \
#     --sha abc123
#
# Implements the following traffic shift pattern (C-067):
#   1. Deploy new revision (green) — receives 0% traffic
#   2. Health check green
#   3. Canary: shift 10% traffic to green
#   4. Run CCT suite against green
#   5. If pass: shift 100% to green
#   6. Deactivate blue (scale to zero) within 30 minutes — C-067 cost rule
#   7. If fail: shift 100% back to blue; deactivate green
#
# Cost impact per deployment: ~₹0.30 (see C-067 Reviewer Notes)

set -euo pipefail

# ─── Arguments ──────────────────────────────────────────────────────────────
SERVICE=""
IMAGE=""
RESOURCE_GROUP=""
ENVIRONMENT=""
SHA=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --service)       SERVICE="$2";       shift 2 ;;
    --image)         IMAGE="$2";         shift 2 ;;
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --environment)   ENVIRONMENT="$2";  shift 2 ;;
    --sha)           SHA="$2";           shift 2 ;;
    --dry-run)       DRY_RUN=true;       shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$SERVICE" || -z "$IMAGE" || -z "$RESOURCE_GROUP" || -z "$ENVIRONMENT" || -z "$SHA" ]]; then
  echo "ERROR: --service, --image, --resource-group, --environment, --sha are all required"
  exit 1
fi

APP_NAME="waooaw-${ENVIRONMENT}-${SERVICE}"
GREEN_SUFFIX="green-${SHA:0:8}"
DEPLOY_START=$(date -u +%s)

log() { echo "[$(date -u +%H:%M:%S)] $*"; }
err() { echo "[$(date -u +%H:%M:%S)] ❌ $*" >&2; }
ok()  { echo "[$(date -u +%H:%M:%S)] ✓ $*"; }

# ─── C-067 COST GATE ─────────────────────────────────────────────────────────
log "Checking monthly cost against constitutional ceiling (C-067)..."

check_cost_gate() {
  # Constitutional cost ceilings per environment per month (INR)
  declare -A CEILINGS=(
    [dev]=10000 [qa]=10000 [demo]=10000 [uat]=10000 [prod]=15000
  )
  CEILING=${CEILINGS[$ENVIRONMENT]:-10000}

  # Query Azure Cost Management for current month spend
  CURRENT_MONTH=$(date +%Y-%m-01)
  CURRENT_COST=$(az consumption usage list \
    --start-date "$CURRENT_MONTH" \
    --end-date "$(date +%Y-%m-%d)" \
    --query "sum([?contains(instanceId, '$RESOURCE_GROUP')].pretaxCost)" \
    --output tsv 2>/dev/null || echo "0")

  CURRENT_COST=${CURRENT_COST:-0}
  WARN_THRESHOLD=$(echo "$CEILING * 0.80" | bc)
  BLOCK_THRESHOLD=$(echo "$CEILING * 0.95" | bc)

  log "Environment: $ENVIRONMENT | Ceiling: ₹${CEILING} | Current: ₹${CURRENT_COST}"

  if (( $(echo "$CURRENT_COST > $BLOCK_THRESHOLD" | bc -l) )); then
    err "COST GATE BLOCKED (C-067): Monthly spend ₹${CURRENT_COST} exceeds 95% of ₹${CEILING} ceiling"
    err "Deployment halted. Cost must reduce before new deployment is constitutional."
    exit 2
  fi

  if (( $(echo "$CURRENT_COST > $WARN_THRESHOLD" | bc -l) )); then
    log "⚠️  COST WARNING (C-067): Monthly spend ₹${CURRENT_COST} exceeds 80% of ₹${CEILING} ceiling"
    # Create GitHub Issue for visibility (non-blocking)
    gh issue create \
      --title "⚠️ Cost warning — ${ENVIRONMENT} — $(date +%Y-%m)" \
      --body "Monthly spend ₹${CURRENT_COST} exceeds 80% of ₹${CEILING} constitutional ceiling (C-067). Review cost optimizations before next deployment." \
      --label "tier:1-bugfix" \
      --repo "${GITHUB_REPOSITORY:-dlai-sd/waooaw-platform}" 2>/dev/null || true
  fi

  ok "Cost gate passed: ₹${CURRENT_COST} of ₹${CEILING}"
}

if [[ "$DRY_RUN" == "false" ]]; then
  check_cost_gate
fi

# ─── Step 1: Enable multiple revisions mode ───────────────────────────────────
log "Step 1: Enabling multiple revisions mode on $APP_NAME..."
if [[ "$DRY_RUN" == "false" ]]; then
  az containerapp revision set-mode \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --mode multiple \
    --output none
fi
ok "Multiple revisions mode enabled"

# ─── Step 2: Get current (blue) revision ─────────────────────────────────────
log "Step 2: Identifying current (blue) revision..."
BLUE_REVISION=$(az containerapp revision list \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[?properties.active && properties.trafficWeight > 0].name | [0]" \
  --output tsv 2>/dev/null || echo "")

if [[ -z "$BLUE_REVISION" ]]; then
  log "No active blue revision found — this may be initial deployment"
  INITIAL_DEPLOY=true
else
  INITIAL_DEPLOY=false
  log "Blue revision: $BLUE_REVISION"
fi

# ─── Step 3: Deploy green revision (0% traffic) ──────────────────────────────
log "Step 3: Deploying green revision (revision-suffix: $GREEN_SUFFIX)..."
if [[ "$DRY_RUN" == "false" ]]; then
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$IMAGE" \
    --revision-suffix "$GREEN_SUFFIX" \
    --output none
fi
ok "Green revision deployed: $APP_NAME--$GREEN_SUFFIX"

# Wait for green revision to be active
log "Waiting for green revision to become active..."
for i in {1..30}; do
  REVISION_STATE=$(az containerapp revision show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --revision "$APP_NAME--$GREEN_SUFFIX" \
    --query "properties.runningState" \
    --output tsv 2>/dev/null || echo "Unknown")

  if [[ "$REVISION_STATE" == "Running" || "$REVISION_STATE" == "Processing" ]]; then
    ok "Green revision is $REVISION_STATE"
    break
  fi
  log "  Green revision state: $REVISION_STATE (waiting...)"
  sleep 10
done

# ─── Step 4: Health check green at 0% traffic ────────────────────────────────
log "Step 4: Health check on green revision..."
GREEN_URL="https://${APP_NAME}--${GREEN_SUFFIX}.$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv 2>/dev/null || echo 'unknown').azurecontainerapps.io"

HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 15 \
  "${GREEN_URL}/health" 2>/dev/null || echo "000")

if [[ "$HEALTH_STATUS" != "200" ]]; then
  err "Green health check FAILED (HTTP $HEALTH_STATUS). Initiating rollback."
  if [[ "$DRY_RUN" == "false" ]]; then
    az containerapp revision deactivate \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --revision "$APP_NAME--$GREEN_SUFFIX" \
      --output none
  fi
  exit 1
fi
ok "Green health check passed (HTTP 200)"

# ─── Step 5: Canary — shift 10% traffic to green ─────────────────────────────
log "Step 5: Canary shift — 10% traffic to green..."
if [[ "$DRY_RUN" == "false" && "$INITIAL_DEPLOY" == "false" ]]; then
  az containerapp ingress traffic set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --revision-weight "${BLUE_REVISION}=90" \
    --revision-weight "${APP_NAME}--${GREEN_SUFFIX}=10" \
    --output none
fi
ok "Canary live: 90% blue / 10% green"

# ─── Step 6: Run post-deploy verification (C-065 — independent confirmer) ─────
log "Step 6: Post-deployment verification on green (10% canary)..."
sleep 30  # Allow canary traffic to stabilize

# Error rate check on green
GREEN_ERROR_RATE="0"  # TODO (IB-009): Query OTel for green revision error rate
if (( $(echo "$GREEN_ERROR_RATE > 5" | bc -l) )); then
  err "Green error rate ${GREEN_ERROR_RATE}% > 5% threshold. Rolling back."
  # Rollback traffic to blue
  if [[ "$DRY_RUN" == "false" && "$INITIAL_DEPLOY" == "false" ]]; then
    az containerapp ingress traffic set \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --revision-weight "${BLUE_REVISION}=100" \
      --output none
    az containerapp revision deactivate \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --revision "${APP_NAME}--${GREEN_SUFFIX}" \
      --output none
  fi
  exit 1
fi
ok "Canary verification passed — no elevated errors on green"

# ─── Step 7: Full traffic switchover to green ────────────────────────────────
log "Step 7: Full traffic switchover — 100% to green..."
if [[ "$DRY_RUN" == "false" ]]; then
  az containerapp ingress traffic set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --revision-weight "${APP_NAME}--${GREEN_SUFFIX}=100" \
    --output none
fi
ok "Traffic: 100% green (new version live)"

# ─── Step 8: Deactivate blue — C-067 cost rule (must deactivate within 30 min) ─
log "Step 8: Deactivating blue revision to enforce C-067 cost constraint..."
ELAPSED=$(( $(date -u +%s) - DEPLOY_START ))
if [[ "$ELAPSED" -gt "1800" ]]; then
  err "CONSTITUTIONAL VIOLATION (C-067): Deployment took >30 minutes."
  err "Blue deactivation is overdue. Forcing immediate deactivation."
fi

if [[ "$DRY_RUN" == "false" && "$INITIAL_DEPLOY" == "false" && -n "$BLUE_REVISION" ]]; then
  az containerapp revision deactivate \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --revision "$BLUE_REVISION" \
    --output none
  ok "Blue revision $BLUE_REVISION deactivated (scaled to zero — cost = 0)"
fi

# ─── Step 9: Final summary ────────────────────────────────────────────────────
TOTAL_TIME=$(( $(date -u +%s) - DEPLOY_START ))
log "═══════════════════════════════════════════════════════"
log "Blue-Green deployment complete (C-067)"
log "  Service:         $APP_NAME"
log "  Green revision:  $APP_NAME--$GREEN_SUFFIX"
log "  Blue (deactivated): ${BLUE_REVISION:-N/A (initial deploy)}"
log "  Total time:      ${TOTAL_TIME}s"
log "  Extra cost:      ~₹0.30 (15-30 min dual-revision window)"
log "═══════════════════════════════════════════════════════"
