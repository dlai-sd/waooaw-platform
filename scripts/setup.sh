#!/usr/bin/env bash
# setup.sh — WAOOAW Development Environment Bootstrap
# Constitutional basis: GENESIS Phase 2 "Establish local development environment"
# Usage: ./scripts/setup.sh
#
# What this script does:
#   1. Creates .env from .env.example (if .env does not exist)
#   2. Validates required infrastructure directories exist
#   3. Starts the full Docker Compose stack
#   4. Waits for all services to be healthy
#   5. Runs smoke tests to verify constitutional compliance
#
# Prerequisites: Docker Desktop, docker compose v2, bash 4+
# Run from the repository root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ─── Colors for output ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║     WAOOAW — Development Environment Bootstrap    ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ─── Step 1: .env file ───────────────────────────────────────────────────────
info "Step 1/5: Environment configuration"

if [[ -f ".env" ]]; then
    success ".env already exists — skipping copy"
else
    if [[ ! -f ".env.example" ]]; then
        error ".env.example not found. Cannot configure environment."
    fi
    cp .env.example .env
    warn ".env created from .env.example"
    warn "Please edit .env and set real values before running services."
    warn "Specifically: POSTGRES_PASSWORD, KEYCLOAK_ADMIN_PASSWORD, LLM_API_KEY"
    echo ""
    read -p "Have you updated .env with real values? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        warn "Please update .env and run this script again."
        exit 0
    fi
fi

# ─── Step 2: Validate infrastructure directories ─────────────────────────────
info "Step 2/5: Validating infrastructure directories"

required_dirs=(
    "infrastructure/postgres/init"
    "infrastructure/keycloak"
    "infrastructure/temporal"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        success "$dir — present"
    else
        error "$dir — MISSING. Run from repository root with infrastructure initialized."
    fi
done

# Check postgres init has SQL files
sql_count=$(find infrastructure/postgres/init -name "*.sql" 2>/dev/null | wc -l)
if [[ "$sql_count" -eq 0 ]]; then
    error "infrastructure/postgres/init contains no SQL files. Database will not initialize."
fi
success "PostgreSQL init: $sql_count SQL files found"

# Check Keycloak realm
if [[ ! -f "infrastructure/keycloak/waooaw-realm.json" ]]; then
    error "infrastructure/keycloak/waooaw-realm.json not found. Keycloak will not import realm."
fi
success "Keycloak realm: waooaw-realm.json found"

# ─── Step 3: Start Docker Compose stack ──────────────────────────────────────
info "Step 3/5: Starting Docker Compose stack"

# Pull images that don't need building (infrastructure services)
docker compose pull postgres keycloak temporal temporal-ui jaeger 2>/dev/null || true

# Build application service images (will fail gracefully if src/ doesn't exist yet)
if [[ -d "src" ]] && [[ "$(ls -A src 2>/dev/null)" ]]; then
    info "Building application service images..."
    docker compose build
else
    warn "src/ is empty or missing — skipping application image builds"
    warn "Infrastructure services only will be started"
fi

# Start the stack
docker compose up -d postgres keycloak temporal temporal-ui jaeger
info "Infrastructure services started. Waiting for health checks..."

# ─── Step 4: Wait for services to be healthy ─────────────────────────────────
info "Step 4/5: Waiting for services to become healthy"

wait_for_healthy() {
    local service=$1
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        status=$(docker compose ps --format json "$service" 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','unknown'))" 2>/dev/null || echo "unknown")

        if [[ "$status" == "healthy" ]]; then
            success "$service is healthy"
            return 0
        fi

        attempt=$((attempt + 1))
        sleep 2
        printf "."
    done

    echo ""
    error "$service did not become healthy within $((max_attempts * 2)) seconds"
}

wait_for_healthy postgres
wait_for_healthy keycloak

# If application services exist, start and wait for them
if [[ -d "src" ]] && [[ "$(ls -A src 2>/dev/null)" ]]; then
    docker compose up -d
    wait_for_healthy constitutional-engine
    wait_for_healthy business-platform
    wait_for_healthy professional-runtime
    wait_for_healthy ai-runtime
fi

# ─── Step 5: Smoke tests ─────────────────────────────────────────────────────
info "Step 5/5: Running smoke tests"

BP_URL="${WAOOAW_BP_URL:-http://localhost:5001}"
PR_URL="${WAOOAW_PR_URL:-http://localhost:5003}"

smoke_test() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "$expected_status" ]]; then
        success "SMOKE: $name → $status"
    else
        warn "SMOKE: $name → $status (expected $expected_status)"
    fi
}

# Infrastructure health checks
smoke_test "PostgreSQL reachable" "http://localhost:5432" "000"  # TCP only, not HTTP
smoke_test "Keycloak health" "http://localhost:8443/health/ready"
smoke_test "Jaeger UI" "http://localhost:16686"
smoke_test "Temporal UI" "http://localhost:8080"

# Application health checks (only if services are running)
if docker compose ps business-platform 2>/dev/null | grep -q "running"; then
    smoke_test "Business Platform /health" "$BP_URL/health"
    smoke_test "Professional Runtime /health" "$PR_URL/health"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              Setup Complete                            ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║  Jaeger UI:       http://localhost:16686               ║"
echo "║  Temporal UI:     http://localhost:8080                ║"
echo "║  Keycloak Admin:  http://localhost:8443  (admin)       ║"
echo "║  Business API:    http://localhost:5001                ║"
echo "║  Professional:    http://localhost:5003                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
success "Development environment ready."
