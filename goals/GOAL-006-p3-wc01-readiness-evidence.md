# GOAL-006 P3-WC01 Readiness Evidence

| Field | Value |
|---|---|
| `record_id` | `CR-GOAL-006-INST-009-04` |
| `record_type` | Contribution Record - blocked attempt |
| `goal_id` | GOAL-006 |
| Component | P3-WC01 - Cloud Readiness And Authorization |
| Authorization | FA-050; GOA-GOAL-006-INST-009-03; ACC-GOAL-006-INST-009-03 |
| Executor | INST-009 - Platform Architect |
| Attempted at | 2026-08-14T06:14:13Z |
| Result | BLOCKED - Azure live read token rejected by Entra security defaults |
| Mutation and spend | NONE; INR 0 |

## Evidence Sequence

| Step | Result | Evidence and consequence |
|---|---|---|
| Authorization chronology | PASS | GOA issued at 06:07:53Z; executor Acceptance at 06:09:44Z |
| GitHub identity | PASS | Authenticated GitHub CLI identity is `dlai-sd` |
| Azure cached account boundary | PASS, NOT LIVE SUFFICIENCY | CLI account metadata named the authorized tenant `0471534c-1bbe-40ab-ae65-3f721b62582c`, subscription `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84`, enabled state and user identity |
| Offline exact-six manifest | PASS | `scripts/goal006_manifest.py` returned `{"passed": true, "violations": []}` before provider access |
| Azure resource inventory | BLOCKED | Entra returned `AADSTS530035: Access has been blocked by security defaults` and required interactive authentication for the authorized tenant |
| Azure provider/region, quotas and budgets | NOT EXECUTED | Fail-closed command sequencing stopped after inventory authentication failure |
| GHCR exact-six retrievability | NOT EXECUTED | Fail-closed command sequencing stopped before registry queries |
| Public DNS control evidence | NOT EXECUTED | Fail-closed command sequencing stopped before DNS queries |
| Public pricing evidence | NOT EXECUTED | Not started before the identity stop condition |
| CT-07 | `NOT_EXECUTED_PHASE_3` | No live inventory exists from which a topology verdict can be made |

## Blocker And Recovery

The approved user identity requires interactive Azure reauthentication under tenant security
defaults. Credentials, device codes, passphrases and MFA responses must not be sent through chat or
stored in repository evidence.

Recovery requires the Founder to authenticate directly in the terminal with:

```bash
az logout
az login --tenant "0471534c-1bbe-40ab-ae65-3f721b62582c" \
  --scope "https://management.core.windows.net//.default"
```

After successful direct authentication, a fresh active-session authorization window is required
because FA-050 expires at session close or a stop condition, whichever occurs first. The next attempt
must begin again with identity-only verification. No permission expansion or alternate identity is
authorized as a workaround.

## Readiness Verdict

**ATTEMPT 1 BLOCKED WITHOUT A READINESS VERDICT.** No Azure inventory, quota, budget, GHCR, DNS,
pricing or CT-07 conclusion was established by this attempt. P3-WC02 through P3-WC08 remained
unauthorized.

## Attempt 2 - Renewed Read-Only Evidence

| Field | Value |
|---|---|
| Authorization | FA-051; GOA-GOAL-006-INST-009-04; ACC-GOAL-006-INST-009-04 |
| Executed | 2026-08-14T07:12:01Z through 2026-08-14T07:15:18Z |
| Monetary result | INR 0 new spend; no resource, role, provider, registry or DNS mutation |
| Identity | PASS - exact authorized tenant/subscription, enabled state, user session |
| Overall result | BLOCKED - P3-WC01 exit conditions are not satisfied |

### Live Inventory And CT-07

The subscription contains one Central India resource group, `waooaw-dev-rg`, with one Central India
Key Vault. It also contains three out-of-region Cognitive Services resources: one in UAE North and
two in West US 3. There are no Container Apps environments and no Container Apps.

| CT-07 expectation | Observed | Result |
|---|---|---|
| Approved Central India delivery boundary | Existing development group and Key Vault are in Central India; unrelated AI resources exist outside the approved P3-WC01 region | PARTIAL |
| Exact-six runtime topology | Zero Container Apps environments and zero Container Apps | FAIL |
| Exact-six manifest identity | Offline signed manifest validates; no live runtime tuple exists | FAIL_LIVE |
| Internal/public ingress topology | No live Container Apps topology exists to inspect | NOT_PROVABLE |
| CT-07 verdict | Authorized inventory does not match the accepted six-member topology | **FAIL** |

CT-07 failure records current absence; it does not authorize creation or repair.

### Azure Prerequisites

| Check | Observed | Result |
|---|---|---|
| `Microsoft.App` | Registered; 35 Central India resource types | PASS |
| Container Apps managed-environment quota | 0 used of 20 | PASS |
| `Microsoft.KeyVault` | Registered | PASS |
| `Microsoft.DBforPostgreSQL` | Registered | PASS |
| `Microsoft.OperationalInsights` | Registered | PASS |
| `Microsoft.ManagedIdentity` | Registered | PASS |
| `Microsoft.Storage` | Not registered | BLOCKED_PREREQUISITE |
| `Microsoft.Insights` | Not registered | BLOCKED_PREREQUISITE |
| Subscription budgets | None | BLOCKED_PREREQUISITE |
| Current human role | Subscription Owner, plus duplicate Owner and service roles | EXCESSIVE_FOR_READINESS |

No provider was registered, budget created or role changed. P3-WC02 requires separately authorized
least-privilege identities and prerequisite creation; the human Owner session is not recommended as
the delivery identity.

### GHCR Exact-Six Retrievability

The signed offline manifest passed with zero violations. `dlai-sd` is a GitHub user owner, not an
organization owner. Both organization and user package endpoints returned HTTP 404 for every
expected package, so none of the six reviewed digests is currently retrievable from the approved
GHCR namespace.

| Member | Digest | Live result |
|---|---|---|
| constitutional-engine | `sha256:9f17b7fcd98aecbe343f28594a3a7ce8222762c4a5cbd7c9d2ff69571250568d` | PACKAGE_NOT_FOUND |
| business-platform | `sha256:e1b6bbd028819ed3cc5d92fd209e26ff907d350cc705b45b358af09bc27b825d` | PACKAGE_NOT_FOUND |
| professional-runtime | `sha256:8b92afcece53868076b9a1faea32ef4bf9ae37a833a5d13745d0920b23c8e67e` | PACKAGE_NOT_FOUND |
| ai-runtime | `sha256:ff843470679e98356bb0bb06d72e76ff6c3ee9b496d0ef465ca25a18dc3da8c6` | PACKAGE_NOT_FOUND |
| web | `sha256:99529bdbe80d01eca6cacbee3ed054e86b024956d505a4b08a401236561857ed` | PACKAGE_NOT_FOUND |
| billing-engine | `sha256:253334ac456574e186d3cc016bcbb4b3ccdba16dbc8abda117d7ab06d197ff27` | PACKAGE_NOT_FOUND |

P3-R04 is not satisfied. Publishing or rebuilding images requires a separate implementation and
registry-push authorization; mutable tags or replacement digests cannot repair this result.

### Public DNS Evidence

| Record | Observed value |
|---|---|
| NS | `ns01.domaincontrol.com`, `ns02.domaincontrol.com` |
| SOA | `ns01.domaincontrol.com`, responsible mailbox at `dns.jomax.net` |
| Apex A | `35.190.6.91` |
| `www` A | `35.190.6.91` |
| CAA | No record observed |

This proves public delegation and resolution, not authenticated registrar control. No DNS record was
changed. Environment hostname activation remains Founder-protected.

### Dated Public Pricing Evidence

The Azure Retail Prices API returned 210 Central India records on 2026-08-14 in USD. Relevant
consumption rates include:

| Meter | Public retail rate |
|---|---|
| Container Apps standard active vCPU | USD 0.000024 per second |
| Container Apps standard idle vCPU | USD 0.000003 per second |
| Container Apps standard active/idle memory | USD 0.000003 per GiB-second |
| Container Apps standard requests | USD 0.40 per 1 million requests |
| PostgreSQL Flexible Server B1MS compute | USD 0.0245 per hour |
| PostgreSQL Flexible Server Premium SSD v2 storage | USD 0.131 per GiB-month |
| Log Analytics free data analyzed | USD 0.00 per GB, subject to service terms and limits |

A trustworthy Demo/UAT/Production total cannot be calculated yet because accepted environment
hours, PostgreSQL SKU/storage/backup, telemetry volume, traffic, data egress, DNS/TLS/edge choice,
tax and USD/INR conversion basis remain unresolved. The Terraform workload defaults all six members
to zero minimum replicas, 0.5 vCPU and 1 GiB with a maximum of 10; that is a scaling contract, not an
accepted workload forecast. P3-R06 is PARTIAL and TGT-02 through TGT-15 remain owner decisions or
unaccepted recommendations.

## Consolidated P3-WC01 Verdict

**BLOCKED - NOT READY FOR P3-WC02.** Identity, Central India Container Apps availability, basic
quota, public DNS observation and dated unit pricing are established. P3-WC01 exit fails because
CT-07 fails, all six GHCR packages are absent, required providers and budgets are missing,
authenticated DNS control is unproven, access is not least privilege, total cost ranges are
incomplete and TGT-02 through TGT-15 remain unresolved. No mutation or spend occurred. P3-WC02
through P3-WC08 remain unauthorized.