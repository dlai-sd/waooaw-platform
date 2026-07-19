# MCP Orchestration Protocol — On-the-Fly Capability Provisioning

**Version:** 1.0
**Date:** 2026-07-19
**Authority:** C-074 (On-the-Fly Capability Provisioning — RATIFIED)
**Owner:** WAOOAW AI Agent — Platform Operations
**Applies to:** Every new customer onboarding + every new domain activation

---

## 1. The Problem This Protocol Solves

When a new customer domain requires an MCP that is not yet running, the old answer was
"developer updates docker-compose, raises PR, deploys." That takes days. C-074 prohibits this.

This protocol ensures capability gaps are resolved automatically or escalated with a 24-hour SLA
— without developer involvement, without manual deployment decisions.

---

## 2. MCP Credential Classification

Every MCP in the platform is classified into one of three types. The type determines the
provisioning path.

### Type 1 — Customer Credentials (Customer provides during Skill 1b onboarding)

The MCP requires credentials specific to the customer's own account on a third-party platform.

| MCP | Credentials needed | Who provides |
|---|---|---|
| `zomato-mcp` | Zomato Restaurant Partner email + password | Customer (Ramesh) |
| `swiggy-mcp` | Swiggy Merchant Portal login | Customer (Ramesh) |
| `booking-mcp/practo` | Practo Doctor/Clinic login | Customer (Dr. Mehta) |
| `booking-mcp/fresha` | Fresha business login | Customer (Rupali) |
| `instagram-mcp` | Instagram Business account (OAuth) | Customer |
| `facebook-mcp` | Facebook Page (OAuth) | Customer |
| `google-business-mcp` | Google Business Profile (OAuth) | Customer |
| `youtube-mcp/customer` | YouTube channel (Google OAuth) | Customer |

**Provisioning path:** Platform requests credentials from customer during Skill 1b.
Customer provides → oauth-vault stores → MCP auto-provisions within 30 minutes.
**Founder involvement: NONE.**

### Type 2 — Platform Credentials (WAOOAW's account on a platform)

The MCP requires WAOOAW's own credentials — a service account, API key, or verified business account.

| MCP | Credentials needed | FA item | Status |
|---|---|---|---|
| `ga4-mcp` | GCP Service Account key (FA-021) | FA-021 | PENDING |
| `youtube-mcp` (analytics) | GCP Service Account key (FA-021) | FA-021 | PENDING |
| `meta-ads-mcp` | Meta Business Manager (FA-002) | FA-002 | PENDING |
| `google-ads-mcp` | Google MCC (FA-006) | FA-006 | PENDING |
| `whatsapp-business-mcp` (WABA) | WAOOAW WABA (FA-009) | FA-009 | PENDING |
| `sarvam-mcp` | Sarvam AI API key (FA-022) | FA-022 | PENDING |

**Provisioning path:**
1. Check Azure Key Vault for the required secret
2. If present → auto-provision immediately (no Founder action needed)
3. If absent → auto-raise Founder Action (see Section 4) + notify Sujay + inform customer (24h SLA)
**Founder involvement: ONLY if secret not in Key Vault.**

### Type 3 — No Credentials (public APIs, no authentication)

| MCP | Notes |
|---|---|
| `web-search-mcp` | Public web search |
| `web-scan-mcp` | Public website scanning |
| `google-places-mcp` | Google Places API (uses platform key, always available) |
| `social-profile-mcp` | Public profile data |
| `meta-ad-library-mcp` | Public Meta Ad Library |
| `scheduling-mcp` | Internal scheduling service |

**Provisioning path:** Auto-provision immediately on demand. No human involvement ever.

---

## 3. Domain Capability Check (runs at every new customer onboarding)

**Trigger:** Customer completes Skill 0 (profile confirmed) with a `business_domain` value.

**Execution:** WAOOAW AI Agent — Platform Operations runs `domain_capability_check` workflow
(Temporal activity, runs within 5 minutes of profile confirmation).

```python
# Pseudocode for domain_capability_check

def domain_capability_check(customer_id: UUID, business_domain: str) -> CapabilityCheckResult:
    """
    C-074: Check all MCPs required for this domain.
    Returns: what's ready, what needs customer credentials, what needs Founder action.
    """
    required_mcps = mcp_registry.get_required_mcps(business_domain)
    
    ready = []
    needs_customer_creds = []
    needs_founder_action = []
    
    for mcp in required_mcps:
        status = mcp_registry.get_status(mcp.mcp_id)
        
        if status == MCP_STATUS.RUNNING:
            ready.append(mcp)
        
        elif mcp.credential_type == CredentialType.NONE:
            # Auto-provision immediately
            mcp_orchestrator.provision(mcp, customer_id)
            ready.append(mcp)
        
        elif mcp.credential_type == CredentialType.CUSTOMER:
            # Queue for Skill 1b credential collection
            needs_customer_creds.append(mcp)
        
        elif mcp.credential_type == CredentialType.PLATFORM:
            # Check Key Vault
            if key_vault.secret_exists(mcp.required_secret_name):
                mcp_orchestrator.provision(mcp, customer_id)
                ready.append(mcp)
            else:
                # Founder action required
                needs_founder_action.append(mcp)
    
    return CapabilityCheckResult(
        ready=ready,
        needs_customer_creds=needs_customer_creds,
        needs_founder_action=needs_founder_action
    )
```

---

## 4. Automated Response per Gap Type

### 4a: Customer Credentials Needed → Skill 1b Collection

The Platform Operations agent adds the missing MCP to the Skill 1b setup checklist:

```yaml
skill_1b_dynamic_addition:
  trigger: domain_capability_check.needs_customer_creds is not empty
  action: append to Skill 1b platform_setup_standard checklist
  
  examples:
    zomato-mcp:
      checklist_item: "Connect your Zomato Restaurant Partner account"
      instructions: |
        "Ramesh ji, to manage your Zomato listing and reviews from here, I need access
         to your Zomato Restaurant Partner account.
         
         Steps (2 minutes):
         1. Go to restaurant.zomato.com
         2. Log in with your restaurant email
         3. Settings → API Access → Generate token
         4. Share the token here (secure — encrypted immediately)
         
         Once you share it, I'll connect within 10 minutes."
      credential_name: "ZOMATO_PARTNER_TOKEN"
      oauth_vault_key: "zomato_{customer_id}"
      
    swiggy-mcp:
      checklist_item: "Register / connect your Swiggy Merchant account"
      instructions: |
        "To get your restaurant on Swiggy, I'll guide you through the merchant registration.
         This takes 7-14 days (Swiggy's verification process).
         
         I'll start the process now and keep you updated daily.
         You'll need: FSSAI license, PAN card, bank account details.
         
         Can you confirm you have these ready?"
      note: "Swiggy registration is async (7-14 days) — customer informed upfront"
```

**Customer notification (WhatsApp, sent within 1 hour of onboarding):**
```
"Namaste Ramesh ji! Welcome to WAOOAW. Here's your current status:

✅ What's ready now:
   - Google Business Profile setup
   - Instagram Business account creation
   - Content calendar for your first month

⏳ What I'm setting up (needs your help — 10 min):
   - Zomato: I need your Restaurant Partner login. Here's how: [link]
   - Swiggy: I'll guide you through merchant registration

Once you share your Zomato credentials, I'll connect within 30 minutes.
Swiggy registration takes 7-14 days (Swiggy's process, not ours).

I'm already working on the things that don't need your login.
Let's get Zomato connected first — reply YES when you're ready."
```

### 4b: Platform Credentials Missing → Automated Founder Action

```yaml
automated_founder_action:
  trigger: domain_capability_check.needs_founder_action is not empty
  sla: 15 minutes from detection to Founder notification
  
  steps:
    1_create_fa_item:
      # Auto-creates a new entry in security/FOUNDER-ACTIONS.md via GitHub API
      fa_id: "FA-AUTO-{timestamp}"
      priority: P0
      action: "Provision {mcp_name} — required for {business_domain} customer {customer_id}"
      unlocks: "{capability} for customer {customer_name}"
      effort: "{credential_effort from mcp_registry}"
      status: PENDING
      github_issue: auto-created with label "type:founder-action, priority:p0, auto-generated"
      
    2_notify_sujay:
      channel: Steward Assistant (WhatsApp + web)
      message: |
        "⚠️ Capability gap detected for new {business_domain} customer ({customer_name}).
         
         Missing: {mcp_name} requires {credential_description}
         FA item created: FA-AUTO-{timestamp}
         Customer notified: 24h SLA given.
         
         What I need from you/Yogesh:
         {required_action_from_founder}
         
         This is the only blocker. Everything else is running.
         Tap to view FA item: [GitHub issue link]"
    
    3_notify_customer:
      channel: WhatsApp (primary)
      sla: 24 hours
      message: |
        "Namaste {customer_name}! Here's your setup status:
         
         ✅ Ready now: [list what's working]
         
         ⏳ Setting up in the next 24 hours:
         - {capability_name}: We're finalizing our connection to {platform_name}.
           You'll have full access by [timestamp + 24h].
         
         I'm already working on your content and platform presence.
         You won't lose any time — everything I can do without {platform_name} is running.
         
         I'll message you as soon as {capability_name} is live. 🙏"
```

### 4c: Auto-Provision (Type 3 or credential already in Key Vault)

No notifications. MCP provisions silently. Customer sees full capabilities from Day 1.

---

## 5. Azure Container Apps Dynamic Provisioning

For cloud environments (QA/UAT/prod), new MCPs are provisioned via Azure Container Apps API
without any deployment pipeline involvement.

```python
class MCPOrchestrator:
    """
    Provisions MCP servers dynamically on Azure Container Apps.
    No docker-compose changes. No PR. No deployment pipeline.
    C-074: runtime provisioning, not deployment-time configuration.
    """
    
    def provision(self, mcp: MCPRegistryEntry, customer_id: UUID) -> None:
        """
        Provision an MCP server for a customer.
        For customer-credential MCPs: one instance per customer (tenant-isolated).
        For platform-credential MCPs: one shared instance per environment.
        """
        if mcp.isolation == "per_customer":
            app_name = f"{mcp.mcp_id}-{customer_id[:8]}"
        else:
            app_name = f"{mcp.mcp_id}-{self.environment}"
        
        # Azure Container Apps API: create new container app
        container_apps_client.create_or_update(
            resource_group=self.resource_group,
            name=app_name,
            template=ContainerAppTemplate(
                image=mcp.docker_image,
                env_vars=self._build_env(mcp, customer_id),
                scale=ScaleConfig(min_replicas=0, max_replicas=1),  # Scale to zero
                ingress=IngressConfig(external=False, target_port=mcp.port)
            )
        )
        
        # Register the running URL in mcp_registry
        url = f"https://{app_name}.{self.container_apps_domain}"
        mcp_registry.update_status(mcp.mcp_id, customer_id, MCP_STATUS.RUNNING, url)
        
        # Record evidence (C-023)
        audit_client.record(
            record_type="MCP_PROVISIONED",
            evidence_key=f"{mcp.mcp_id}_{customer_id}",
            constitutional_basis="C-074"
        )
```

**For local development (docker-compose):**

```python
class MCPOrchestratorDev:
    """
    Development environment: start new MCP containers via Docker SDK.
    No compose file changes needed.
    """
    def provision(self, mcp: MCPRegistryEntry, customer_id: UUID) -> None:
        docker_client.containers.run(
            image=mcp.docker_image,
            name=f"{mcp.mcp_id}-{customer_id[:8]}",
            network="waooaw-dev",
            ports={f"{mcp.port}/tcp": mcp.port},
            environment=self._build_env(mcp, customer_id),
            detach=True
        )
```

---

## 6. MCP Lifecycle Management

```
PROVISION → RUNNING → IDLE (no requests in 24h) → SUSPENDED → RE-PROVISION on next request

Cost optimisation: MCPs that haven't been called in 24h are suspended.
  Container Apps: scale to 0 (zero cost when idle — ADR-027 O-07)
  Customer never loses capability — re-provision takes < 2 minutes on next call.
  Platform Operations monitors idle MCPs and suspends them automatically.

Evidence: MCP_PROVISIONED, MCP_SUSPENDED, MCP_RESUMED in constitutional.audit_records
```

---

## 7. Skill 1b Integration — Credential Collection Flow

Skill 1b now has a dynamic section generated from `domain_capability_check` results:

```
STATIC SECTION (same for all customers):
  GBP, Instagram, Facebook, WhatsApp setup [existing Skill 1b]

DYNAMIC SECTION (generated per customer based on missing MCPs):
  "To unlock the following capabilities for your [domain] business,
   I'll need a few additional connections. Each takes 5-10 minutes.
   I'll guide you through each one."
  
  [For Ramesh — restaurant]:
    "Zomato Partner access → manage your listing + reviews"
    "Swiggy Merchant Portal → delivery channel (7-14 day registration)"
    
  [For Dr. Mehta — dental]:
    "Practo Doctor login → manage patient enquiries"
    "Google Analytics → track which posts bring patients"
    
  [For Rupali — beauty]:
    "Fresha login → manage client bookings"

Each credential request:
  → Clear explanation of WHY it's needed (business benefit)
  → Step-by-step guide (not just "enter your password")
  → Security assurance ("encrypted immediately, you can revoke anytime")
  → What happens if they decline ("I'll work without it — here's what I can't do")
```

---

## 8. The 24-Hour SLA Guarantee

| Scenario | Response time | Customer notification | Founder involvement |
|---|---|---|---|
| Type 3 MCP (no credentials) | < 5 minutes | Not needed — already working | None |
| Type 1 MCP (customer credentials) | < 30 min after customer provides | Capability gap disclosed + guide sent within 1h | None |
| Type 2 MCP (platform credentials in Key Vault) | < 30 min from detection | Not needed — already provisioning | None |
| Type 2 MCP (platform credentials MISSING) | 24h SLA from detection | Gap disclosed within 1h + 24h timeline | Required + auto-notified within 15 min |
| Third-party platform slow onboarding (Swiggy 7-14d) | Disclosed at onboarding | Full transparency — "Swiggy takes 7-14 days, not us" | None |

**The 24-hour SLA is a constitutional commitment under C-074 + C-049.**
If it cannot be met, the customer is informed BEFORE the 24h passes — not after.

---

## 9. Persistence — MCP Survival Across Restarts, Crashes, and Scaling Events

### 9.1 The Problem

A dynamically provisioned MCP container can be lost due to:
- **Host reboot** — Docker containers without a restart policy are not restarted
- **Container App scaling to zero** — Azure Container Apps scales to 0 when idle; on first request, cold start ~3s (acceptable). BUT: if the Container App resource itself is deleted, it does not come back.
- **Platform restart** — when the AI Runtime or Platform Operations agent restarts, it has no in-memory state of which MCPs were provisioned

**The solution:** PostgreSQL (`institutional.customer_mcp_status`) is the **persistent source of truth**. Physical containers are ephemeral and disposable. The database record is authoritative. On any restart, the reconciliation loop rebuilds the physical state from the database.

### 9.2 Three-Layer Persistence Strategy

```
LAYER 1 — Restart Policy (prevents most losses)
  Docker:           restart: unless-stopped on every dynamically provisioned container
  Azure Container:  apps persist in ARM by default; scale-to-zero is NOT deletion
  
LAYER 2 — Startup Reconciliation (catches what restart policy misses)
  Temporal workflow: mcp-reconciliation (runs on Platform Operations startup)
  Reads: customer_mcp_status WHERE status = 'RUNNING'
  Checks: is this container/app actually reachable? (health check HTTP GET)
  Action: if not reachable → re-provision using stored credentials from oauth-vault
  
LAYER 3 — Periodic Health Probe (catches silent failures between restarts)
  Temporal schedule: every 5 minutes
  Checks: all RUNNING MCPs respond to /health endpoint
  Action: RUNNING → health check fails → update status to 'ERROR' → re-provision → alert
```

### 9.3 Docker Restart Policy

Every container started via Docker SDK must include `restart: unless-stopped`:

```python
class MCPOrchestratorDev:
    def provision(self, mcp: MCPRegistryEntry, customer_id: UUID) -> None:
        docker_client.containers.run(
            image=mcp.docker_image,
            name=f"{mcp.mcp_id}-{customer_id[:8]}",
            network="waooaw-dev",
            ports={f"{mcp.port}/tcp": mcp.port},
            environment=self._build_env(mcp, customer_id),
            detach=True,
            restart_policy={"Name": "unless-stopped"},  # ← REQUIRED for persistence
            labels={
                "waooaw.mcp_id": mcp.mcp_id,
                "waooaw.customer_id": str(customer_id),
                "waooaw.managed": "true",
            }
        )
        # Labels enable the reconciliation loop to re-discover managed containers
```

**`restart: unless-stopped`** means:
- Container restarts automatically after host reboot ✓
- Container restarts after OOM kill ✓
- Container restarts after crash ✓
- Container does NOT restart after `docker stop` (manual stop = intentional) ✓

### 9.4 Azure Container Apps Persistence

Azure Container Apps resources persist in ARM (Azure Resource Manager) independently of
whether they're running. Scale-to-zero = 0 replicas → resource still exists → auto-scales
on first HTTP request (cold start ~2-3 seconds at Consumption tier).

```python
class MCPOrchestratorCloud:
    def provision(self, mcp: MCPRegistryEntry, customer_id: UUID) -> None:
        app_name = f"{mcp.mcp_id}-{customer_id[:8]}"
        
        container_apps_client.create_or_update(
            resource_group=self.resource_group,
            name=app_name,
            template=ContainerAppTemplate(
                image=mcp.docker_image,
                env_vars=self._build_env(mcp, customer_id),
                scale=ScaleConfig(
                    min_replicas=0,   # Scale to zero when idle (cost: ₹0)
                    max_replicas=1,
                    rules=[ScaleRule(
                        name="http-scale",
                        http=HttpScaleRule(concurrent_requests=10)
                    )]
                ),
                # Container Apps restart automatically on crash — no explicit policy needed
                # The ARM resource itself is durable; only replicas scale to 0
            )
        )
        
        # Store ARM resource ID for reconciliation verification
        arm_resource_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.App/containerApps/{app_name}"
        mcp_registry.update_arm_resource_id(mcp.mcp_id, customer_id, arm_resource_id)
```

**After ARM resource creation, the MCP is durable by default.** No additional persistence configuration needed for Azure.

### 9.5 Startup Reconciliation Workflow

This Temporal workflow runs automatically every time Platform Operations starts.
It is the safety net that rebuilds physical state from the database record.

```python
@workflow.defn
class MCPReconciliationWorkflow:
    """
    C-074: Reconcile physical MCP state against database on every Platform Operations startup.
    Runs as first activity before accepting any new customer requests.
    """
    
    @workflow.run
    async def run(self) -> ReconciliationResult:
        # Get all MCPs that should be RUNNING according to the database
        expected_running = await workflow.execute_activity(
            get_expected_running_mcps,
            schedule_to_close_timeout=timedelta(minutes=2)
        )
        
        results = ReconciliationResult(checked=0, healthy=0, reprovisioned=0, failed=0)
        
        for entry in expected_running:
            results.checked += 1
            
            # Health check the physical container/app
            is_healthy = await workflow.execute_activity(
                health_check_mcp,
                args=[entry.container_url],
                schedule_to_close_timeout=timedelta(seconds=10)
            )
            
            if is_healthy:
                results.healthy += 1
                # Update last_seen_at
                await workflow.execute_activity(
                    update_mcp_last_seen, args=[entry.customer_id, entry.mcp_id]
                )
            else:
                # Not healthy — re-provision using stored credentials
                reprovisioned = await workflow.execute_activity(
                    reprovision_mcp,
                    args=[entry.customer_id, entry.mcp_id, entry.mcp_registry],
                    schedule_to_close_timeout=timedelta(minutes=5)
                )
                if reprovisioned:
                    results.reprovisioned += 1
                    # Notify customer that their integration was briefly interrupted and is restored
                    await workflow.execute_activity(
                        notify_customer_mcp_restored,
                        args=[entry.customer_id, entry.mcp_id]
                    )
                else:
                    results.failed += 1
                    # Alert Sujay — re-provision failed, human attention needed
                    await workflow.execute_activity(
                        alert_steward_mcp_failed,
                        args=[entry.customer_id, entry.mcp_id, "reconciliation_failed"]
                    )
        
        # Record evidence of reconciliation run (C-023)
        await workflow.execute_activity(
            record_evidence,
            args=["MCP_RECONCILIATION_COMPLETE", results.__dict__, "C-074"]
        )
        
        return results
```

### 9.6 Periodic Health Probe (every 5 minutes)

Integrated into Platform Operations Skill A (Continuous Health Monitoring):

```python
async def mcp_health_probe_activity() -> MCPHealthReport:
    """
    Runs every 5 minutes. Checks all RUNNING MCPs.
    Failures trigger automatic re-provision + optional customer notification.
    """
    running_mcps = await db.fetch_all(
        """SELECT customer_id, mcp_id, container_url
           FROM institutional.customer_mcp_status
           WHERE status = 'RUNNING'"""
    )
    
    failures = []
    for mcp in running_mcps:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{mcp.container_url}/health")
                if r.status_code != 200:
                    failures.append(mcp)
        except (httpx.ConnectError, httpx.TimeoutException):
            failures.append(mcp)
    
    for failed in failures:
        # Mark as ERROR
        await db.execute(
            "UPDATE institutional.customer_mcp_status SET status = 'ERROR' WHERE customer_id = $1 AND mcp_id = $2",
            failed.customer_id, failed.mcp_id
        )
        # Record to health_check_log
        await db.execute(
            """INSERT INTO institutional.mcp_health_check_log
               (customer_id, mcp_id, status, error_reason, checked_at)
               VALUES ($1, $2, 'FAIL', 'health_check_timeout', NOW())""",
            failed.customer_id, failed.mcp_id
        )
        # Queue re-provision (async — does not block health probe)
        await temporal.signal_workflow("mcp-reprovision", {"customer_id": failed.customer_id, "mcp_id": failed.mcp_id})
    
    return MCPHealthReport(total=len(running_mcps), healthy=len(running_mcps)-len(failures), failed=len(failures))
```

### 9.7 Customer Notification on Recovery

When an MCP is silently re-provisioned after a failure, the customer receives a WhatsApp message only if their services were **interrupted for more than 2 minutes**:

```
"Namaste [Name]! A quick update: there was a brief interruption with your
 [Platform Name] integration (e.g., Zomato) — it went offline for [N] minutes
 and has now been automatically restored.
 
 No data was lost. Your integration is working normally again. 🙏
 
 You don't need to do anything."
```

Threshold: < 2 minutes → silent (no customer notification, internal log only).
> 2 minutes → customer notified as above.
> 15 minutes → Sujay also notified via Steward Assistant.

### 9.8 CCT for MCP Persistence

**CCT-MCP-01: MCP persists after platform restart**
```
Setup:    Provision a Type 1 MCP (customer credential) for a test customer.
          Verify it's running: GET /health → 200.
Action:   Restart the AI Runtime service (simulates crash).
Assert:   After 60 seconds, GET /health on the same MCP URL → 200.
          customer_mcp_status.status is still RUNNING (or was RUNNING → ERROR → RUNNING via reconciliation).
          No customer notification sent (< 2 min downtime).
Constitutional basis: C-074 (MCP persistence obligation)
```

**CCT-MCP-02: Reconciliation re-provisions deleted MCP**
```
Setup:    Provision a Type 1 MCP. Manually stop the container (simulate crash with no restart).
          Update customer_mcp_status.status = 'RUNNING' (simulate stale state).
Action:   Trigger MCPReconciliationWorkflow.
Assert:   Container is re-provisioned (new health check passes).
          customer_mcp_status.status = 'RUNNING' with updated container_url.
          Evidence record: MCP_RECONCILIATION_COMPLETE with reprovisioned = 1.
Constitutional basis: C-074, C-023 (Evidence First)
```
