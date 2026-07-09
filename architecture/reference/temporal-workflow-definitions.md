# Temporal Workflow Definitions

**Authority:** GENESIS Part 05 — Agent Runtime Protocol; ADR-015 (Temporal Deployment Strategy); ADR-018 (Emergency Stop via Temporal Signal)
**Date:** 2026-07-09
**Constitutional Basis:** C-023 (Evidence First); C-034 (Employment lifecycle); DP-014 (Maturity-Driven Skill Activation)
**Purpose:** Formal workflow and activity interface definitions for all Temporal workflows used by the platform. Developers implement Temporal workers to these interfaces. The Professional Runtime and Business Platform are Temporal clients + workers.

---

## Workflow Architecture Overview

```
Business Platform (Temporal client)
    → starts/signals: EmploymentLifecycleWorkflow, TrialExpiryWorkflow, PauseResumeWorkflow

Professional Runtime (Temporal worker + client)
    → executes: PAASSessionWorkflow (existing), SkillExecutionWorkflow (new)
    → starts: MarketResearchWorkflow

AI Runtime (Temporal activity executor)
    → implements activities: CustomerProfilingActivity, MarketResearchActivity,
                              SyntheticApprovalActivity, SelfGovernanceActivity
```

---

## 1. MarketResearchWorkflow

**Worker:** Professional Runtime
**Queue:** `market-research-queue`
**Timeout:** 10 minutes (research may take 3-5 minutes; allow retries)
**Retry policy:** 3 attempts with 30s initial backoff; on terminal failure, deliver partial report

### Workflow Interface
```python
@workflow.defn
class MarketResearchWorkflow:
    @workflow.run
    async def run(self, input: MarketResearchWorkflowInput) -> MarketResearchWorkflowResult:
        ...

@dataclass
class MarketResearchWorkflowInput:
    organisation_id: str          # UUID
    contract_id: str              # UUID — Employment Contract driving this research
    business_name: str
    locality: str
    city: str
    business_domain: str
    trigger: str                  # "ONBOARDING" | "6_MONTH_REFRESH" | "CUSTOMER_REQUEST"

@dataclass
class MarketResearchWorkflowResult:
    maturity_score: int           # 1-7
    maturity_score_id: str        # UUID of saved maturity_scores row
    report_pdf_url: str | None    # signed URL to PDF (None if PDF generation failed)
    delivery_status: dict         # {channel: "SENT"|"FAILED"} per channel
    partial: bool                 # True if some research axes failed (degraded report)
```

### Activities (implement in AI Runtime)
```python
# Activity 1: Run parallel web research
@activity.defn
async def research_digital_presence(input: ResearchInput) -> ResearchResult:
    # Calls: web-search-mcp, google-places-mcp, social-profile-mcp,
    #        meta-ad-library-mcp, web-scan-mcp (parallel via asyncio.gather)
    # CE.ValidateAction called before each MCP call (C-041)
    # Returns: per-axis findings dict
    ...

# Activity 2: Score and generate report
@activity.defn
async def calculate_maturity_score(findings: dict) -> MaturityScore:
    # LLM call: score each axis 1-7, compute composite
    # Retrieve Tier 3 benchmark (platform-analytics-mcp or direct DB query)
    # Build needs heat map
    ...

# Activity 3: Save score to DB
@activity.defn
async def save_maturity_score(score: MaturityScore, organisation_id: str) -> str:
    # Calls customer-profile-mcp.maturity.save_score
    # Returns maturity_score_id
    ...

# Activity 4: Generate PDF
@activity.defn
async def generate_report_pdf(score: MaturityScore, organisation_id: str) -> str | None:
    # Calls pdf-generation-mcp (port 8123 — to be added to docker-compose)
    # Returns signed URL or None on failure (DEGRADABLE)
    ...

# Activity 5: Deliver report
@activity.defn
async def deliver_maturity_report(
    organisation_id: str, report_url: str | None, channels: list[str]
) -> dict:
    # For each channel in customer's delivery_channels preference:
    #   WHATSAPP_VOICE: whatsapp-business-mcp.send_hsm_template (report_ready template)
    #   WHATSAPP_TEXT:  whatsapp-business-mcp.send_text
    #   EMAIL_PDF:      email-mcp.send_report (port 8124 — to be added)
    #   PORTAL:         no action — portal reads from DB
    #   PUSH:           push-notification-mcp.send (port 8125 — to be added)
    ...
```

---

## 2. TrialExpiryWorkflow

**Worker:** Business Platform
**Queue:** `employment-queue`
**Started by:** Business Platform — EmploymentManager on contract formation with trial_end_date set
**Timeout:** max = trial_duration + 1 hour

### Workflow Interface
```python
@workflow.defn
class TrialExpiryWorkflow:
    @workflow.run
    async def run(self, input: TrialExpiryInput) -> None:
        ...

    # Signal: customer converts before expiry
    @workflow.signal
    def trial_converted(self) -> None: ...

    # Signal: customer explicitly terminates trial
    @workflow.signal
    def trial_terminated(self) -> None: ...

@dataclass
class TrialExpiryInput:
    contract_id: str
    organisation_id: str
    trial_end_date: str           # ISO datetime
    reminder_days_before: int = 2 # Send reminder N days before expiry
```

### Activities
```python
@activity.defn
async def send_trial_expiry_reminder(contract_id: str, days_remaining: int) -> None:
    # Notify customer via all channels: "Your trial ends in X days. Hire to continue."
    ...

@activity.defn
async def auto_terminate_trial(contract_id: str) -> None:
    # Transitions employment contract to TERMINATED state
    # CE.RecordEvidence: EMPLOYMENT_TERMINATED (trial_expired=true)
    # Billing: no charge — trial was free
    # Tier 2 RAG: preserved per CD-003 (data retention during inactive period)
    ...
```

---

## 3. PauseResumeWorkflow

**Worker:** Business Platform + Professional Runtime
**Queue:** `employment-queue`
**Started by:** Business Platform on contract pause

### Pause Activity (Professional Runtime)
```python
@activity.defn
async def pause_skill_execution(contract_id: str, skill_id: str, skill_type: str) -> PauseResult:
    """
    Gracefully pauses a running skill. Per-skill actions:

    Content skills (CONTENT_STRATEGY, INSTAGRAM_MARKETING, FACEBOOK_MARKETING, etc.):
      - scheduling-mcp: cancel all scheduled posts AFTER pause timestamp
      - Posts already published: leave (cannot undo published content)
      - Content calendar: preserve draft state

    PAID_ADVERTISING:
      - meta-ads-mcp.campaign.pause: pause ALL active campaigns immediately
      - google-ads-mcp.campaign.pause: same
      - CRITICAL: must complete within 30 seconds to prevent unintended spend

    COMPETITIVE_INTELLIGENCE:
      - No action required — monitoring is read-only; next cycle will not start

    A/B tests (CONVERSION_OPTIMISATION):
      - web-optimisation-mcp.ab_test.pause: pause active tests
      - Record test state for later resumption
    """
    ...

@dataclass
class PauseResult:
    skill_type: str
    paused_at: str                         # ISO timestamp
    cancelled_scheduled_posts: int
    paused_campaigns: list[str]            # campaign IDs paused
    preserved_state: dict                  # state to restore on resume
    billing_pause_timestamp: str           # for pro-rata calculation (C-038)
```

### Resume Activity (Professional Runtime)
```python
@activity.defn
async def resume_skill_execution(
    contract_id: str, skill_id: str, preserved_state: dict
) -> ResumeResult:
    """
    Restores skill to pre-pause state.
    - Synthetic Approval: check model freshness (DP-015, AD-017)
      If model is stale (last_calibrated > stale_after_days): downgrade to EXCEPTION_APPROVAL
    - Content: resume content calendar from current week (do not backfill missed posts)
    - Paid Advertising: resume paused campaigns (if budget remains)
    - A/B tests: restore test state
    """
    ...
```

---

## 4. SkillExecutionWorkflow

**Worker:** Professional Runtime
**Queue:** `skill-execution-queue`
**Purpose:** Durable orchestration for approval-gate skill execution (replaces ad-hoc HTTP chains)

### Workflow Interface
```python
@workflow.defn
class SkillExecutionWorkflow:
    @workflow.run
    async def run(self, input: SkillExecutionInput) -> SkillExecutionResult:
        ...

    # Signal: customer approves
    @workflow.signal
    def customer_approved(self, approval_id: str) -> None: ...

    # Signal: customer rejects
    @workflow.signal
    def customer_rejected(self, approval_id: str, reason: str) -> None: ...

@dataclass
class SkillExecutionInput:
    contract_id: str
    skill_id: str
    skill_type: str               # e.g., "INSTAGRAM_MARKETING"
    action_type: str              # e.g., "INSTAGRAM_POST"
    approval_mode: str            # "CUSTOMER_APPROVAL" | "EXCEPTION_APPROVAL" | "SYNTHETIC_APPROVAL"
    proposed_content: dict        # the action to be executed
    approval_timeout_hours: int = 72
```

### Execution Flow (Approval-Gate Mode)
```
1. CE.RecordEvidence(PROPOSED) → action_instance_id
2. BP.CreateApprovalRequest → approval_id
3. Notify customer (push-notification-mcp or whatsapp-business-mcp)
4. Wait for customer_approved / customer_rejected signal (max approval_timeout_hours)
   If timeout: CE.RecordEvidence(ABANDONED) → close
5. On APPROVED:
   CE.RecordEvidence(APPROVED)
   Execute action via MCP tool
   CE.RecordEvidence(EXECUTED)
6. On REJECTED:
   CE.RecordEvidence(REJECTED) → close
```

### Execution Flow (Synthetic Approval Mode)
```
1. AI Runtime computes confidence score
2. CE.ValidateAction(SYNTHETIC, confidence, budget_context?) → ALLOW / DENY
3. If DENY: downgrade to customer approval for this action
4. If ALLOW:
   CE.RecordEvidence(SYNTHETIC_APPROVAL)
   BP.RecordSyntheticApproval (creates synthetic_approval_records row)
   Notify customer (REQUIRED before execution)
   Execute action via MCP tool
   CE.RecordEvidence(EXECUTED)
   Start override window timer
5. If customer overrides within window:
   Reverse action where possible (skill-type-specific)
   Update override rate counter → check DP-015 auto-downgrade threshold
```

---

## 5. SelfGovernanceWorkflow

**Worker:** Professional Runtime
**Queue:** `self-governance-queue`
**Triggered by:** Temporal cron schedule — day 15 of month, last 3 working days of month

### Cron Schedule
```python
# In Professional Runtime worker startup:
await client.start_workflow(
    SelfGovernanceWorkflow.run,
    SelfGovernanceWorkflowInput(contract_id=contract_id, skill_id=skill_id),
    id=f"self-governance-{contract_id}-{skill_id}",
    task_queue="self-governance-queue",
    cron_schedule="0 9 15 * *",        # Day 15 at 9 AM IST (3:30 AM UTC)
)
# Month-end narrative: separate cron
await client.start_workflow(
    MonthEndNarrativeWorkflow.run,
    ...,
    cron_schedule="0 6 L * *",          # Last day of month at 6 AM IST
)
```

---

## Developer Quick-Start — Running Workflows Locally

```bash
# 1. Temporal server must be running (docker-compose includes it)
docker-compose up temporal temporal-ui

# 2. Start the skill execution worker (Professional Runtime)
cd src/professional-runtime
uvicorn main:app &
python worker.py --queue skill-execution-queue &

# 3. Start a test MarketResearchWorkflow
python -c "
import asyncio
from temporalio.client import Client
async def main():
    client = await Client.connect('localhost:7233')
    handle = await client.start_workflow(
        'MarketResearchWorkflow',
        {'organisation_id': 'test-org-id', 'business_name': 'Test Business',
         'locality': 'Koramangala', 'city': 'Bangalore',
         'business_domain': 'FITNESS_STUDIO', 'trigger': 'ONBOARDING'},
        id='test-market-research-1',
        task_queue='market-research-queue',
    )
    result = await handle.result()
    print(result)
asyncio.run(main())
"
```

---

## Missing Infrastructure (Developer Must Add to docker-compose)

| Service | Port | Purpose | Added in |
|---|---|---|---|
| `push-notification-mcp` | 8125 | Firebase FCM / APNs push notifications for approval alerts | v0.18.0 |
| `email-mcp` | 8124 | Transactional email (SendGrid/SES) for Maturity Report PDFs, billing | v0.18.0 |
| `pdf-generation-mcp` | 8123 | PDF generation from HTML (Puppeteer/Gotenberg) for Maturity Reports | v0.18.0 |
| `oauth-vault` | 8130 | Customer OAuth token storage and refresh (ADR-021) | v0.18.0 |
| `razorpay-mcp` | 8131 | Razorpay subscription and payment management (ADR-022) | v0.18.0 |
