#!/usr/bin/env bash
# setup-github-labels.sh — Create all WAOOAW GitHub labels
# Run once per repository. Safe to re-run (existing labels are skipped).
# Usage: ./scripts/setup-github-labels.sh [--repo owner/repo]
#
# Requires: gh CLI authenticated (gh auth login)

set -euo pipefail

REPO="dlai-sd/waooaw-platform"
if [[ "${1:-}" == "--repo" ]]; then REPO="${2:-$REPO}"; fi

create() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null || \
  gh label edit  "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null || true
}

echo "Creating labels for $REPO..."

# ─── Issue type ──────────────────────────────────────────────────────────────
create "type:implementation"      "0075ca" "IB item for Runtime Professional to implement"
create "type:architecture"        "e4e669" "IB item for an architecture office"
create "type:constitutional-blocker" "d73a4a" "Formal Constitutional Blocker — halts work"
create "type:sprint-plan"         "5319e7" "Sprint Plan awaiting Founder approval"
create "platform-status"          "1d76db" "Pinned Platform Delivery Status issue"

# ─── Office ──────────────────────────────────────────────────────────────────
create "office:runtime-professional"    "bfd4f2" "Office 10 — implements code"
create "office:enterprise-architect"    "c5def5" "Office 04 — reference architecture"
create "office:solution-architect"      "c5def5" "Office 05 — component specs + API contracts"
create "office:data-architect"          "c5def5" "Office 06 — data architecture"
create "office:platform-architect"      "c5def5" "Office 09 — infra + CI/CD"
create "office:security-architect"      "f9d0c4" "Office 07 — security architecture"
create "office:ai-architect"            "c5def5" "Office 08 — AI architecture"
create "office:business-architect"      "e4e669" "Office 03 — capabilities + drivers"
create "office:constitutional-analyst"  "fbca04" "Office 02 — knowledge claims"
create "office:product-owner"           "5319e7" "Office 11 — sprint planning"

# ─── Component ───────────────────────────────────────────────────────────────
create "component:constitutional-engine"  "0075ca" "CE — gRPC, audit ledger, governance"
create "component:business-platform"      "0075ca" "BP — REST, employment, approvals"
create "component:professional-runtime"   "0075ca" "PR — PAAS, approval-gate, Emergency Stop"
create "component:ai-runtime"             "0075ca" "AI — LLM gateway, tool execution"
create "component:web"                    "0075ca" "Web — Next.js PWA, Emergency Stop UI"
create "component:infrastructure"         "0075ca" "Infra — postgres, keycloak, temporal"
create "component:platform-ops"           "0075ca" "Ops — monitoring, runbooks, CI/CD"

# ─── Capability domain ───────────────────────────────────────────────────────
create "domain:d1-hire"           "006b75" "D1 — Hire Professional"
create "domain:d2-govern"         "006b75" "D2 — Govern Work"
create "domain:d3-execute"        "006b75" "D3 — Execute Work"
create "domain:d4-authority"      "006b75" "D4 — Manage Authority"
create "domain:d5-terminate"      "006b75" "D5 — Terminate Employment"
create "domain:d6-platform"       "006b75" "D6 — Platform Infrastructure"
create "domain:d7-portal"         "006b75" "D7 — Customer Portal"
create "domain:d8-cs-agents"      "006b75" "D8 — CS Agents (FR-001 Path A)"
create "domain:nfr-security"      "b60205" "NFR — Security"
create "domain:nfr-performance"   "b60205" "NFR — Performance / Latency"
create "domain:nfr-cost"          "b60205" "NFR — Cost (AD-006)"
create "domain:nfr-observability" "b60205" "NFR — OTel / Observability"
create "domain:platform-foundation" "006b75" "Platform foundation / skeleton"

# ─── Gate ────────────────────────────────────────────────────────────────────
create "gate:G5"              "0e8a16" "Gate G5 — foundation implementation"
create "gate:G5-parallel"     "0e8a16" "G5-parallel — runs alongside IB-009"
create "gate:G5-prerequisite" "d93f0b" "G5-prerequisite — must complete before IB-009"
create "gate:post-G5"         "c2e0c6" "Post-G5 — future epochs"

# ─── Sprint ──────────────────────────────────────────────────────────────────
for i in $(seq 1 10); do
  create "sprint:$i" "f9d0c4" "Sprint $i"
done

# ─── Status ──────────────────────────────────────────────────────────────────
create "status:waiting"    "ededed" "Waiting for dependencies or sprint start"
create "status:in-progress" "0e8a16" "Agent is executing"
create "status:blocked"    "d73a4a" "Constitutional Blocker raised"
create "status:done"       "0e8a16" "Complete — merged and verified"
create "status:approved"   "0e8a16" "Sprint Plan approved — Mode 2 active"

# ─── Awaiting ────────────────────────────────────────────────────────────────
create "awaiting:founder-approval" "fbca04" "Sprint Plan awaiting /approved from Founder"

# ─── Priority ────────────────────────────────────────────────────────────────
create "priority:critical" "d73a4a" "P0 — Constitutional Floor or gate-blocking"
create "priority:high"     "e4e669" "P1 — High value, needed soon"
create "priority:medium"   "ededed" "P2 — Important but not blocking"

echo ""
echo "✅ All labels created/updated for $REPO"
echo "Total label count: $(gh label list --repo "$REPO" --limit 200 --json name | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')"
