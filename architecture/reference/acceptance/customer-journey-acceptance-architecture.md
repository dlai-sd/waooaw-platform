# Customer Journey Acceptance Architecture

**Status:** PROPOSED - architecture package v1.0 for Founder review (WC-157). No implementation is authorized.
**Owner:** Enterprise Architecture (INST-004)
**Decisions:** ADR-054 (acceptance architecture), ADR-055 (synthetic tenants and evidence)
**Capabilities:** 6.3 Record Constitutional Evidence; 6.4 Observe Platform Health and Constitutional Compliance;
6.7 Implement Governed Cloud Delivery (with 6.2, 6.5 through ADR-055)
**Drivers:** AD-002, AD-003, AD-004, AD-006, AD-008, AD-009, AD-010
**Claims:** C-023, C-027, C-042, C-049, C-059, C-063, C-065, C-071, C-080, C-086
**Reuses:** `architecture/reference/components/fundamental-customer-journeys.md` (WC-107 stories and trace rules),
`work-contracts/WC-107-requirements.yaml`, `architecture/reference/product/waooaw-product-gap-register.md`,
`goals/GOAL-005-agent-employment-experience-program.md`, `architecture/reference/api-specs/*.openapi.yaml`,
`architecture/reference/platform-component-registry.yaml`, `.github/actions/run-validation-gate`

## 1. Purpose

After a deployment completes, the Founder presses one button. A synthetic customer then uses the deployed
product through its real web interface, and WAOOAW reports what works, how deeply it was checked, and what
was not checked. The result informs; it does not block (ADR-054 item 8).

Success is a trustworthy statement of the form: "On this exact deployed candidate, stage X was proven by
screen, platform record and provider sandbox, to depth L4; stage Y was blocked by flag Z; stage W was not
covered."

Out of scope: unit and integration testing (unchanged), load testing, penetration testing, Production
execution, AI exploratory testing, and any change to promotion rules.

## 2. Context View

```
                       Founder (workflow_dispatch: environment, journey)
                                        |
                              GitHub Actions workflow
                                        |
     Azure OIDC (acceptance identity) --+-- reads Key Vault acceptance-* secrets
                                        |
                          Docker runner (digest-pinned)
                                        |
        +-------------------+-----------+------------+----------------------+
        |                   |                        |                      |
  Playwright (UI)    Platform reader (W2)     Provider readers (W3)   Telemetry reader (W4, optional)
        |                   |                        |                      |
  Deployed Web  ->  Business Platform APIs     Razorpay test API      Azure Monitor workspace
  Keycloak (real)   (customer session only)    Meta Graph (test app)   (read-only)
                                               WhatsApp sandbox number
```

External actors: Founder, Azure Entra OIDC, Key Vault, the deployed environment, provider sandboxes.
The workflow never holds deployment authority and never writes product storage directly.

## 3. Components

| Component | Responsibility | Proposed home | Capability |
|---|---|---|---|
| Acceptance workflow | Manual trigger, environment and journey inputs, concurrency of one run per environment, artifact upload, verdict-to-conclusion mapping | `.github/workflows/customer-journey-acceptance.yaml` | 6.7 |
| Environment profile | Non-secret addresses, Key Vault name, sandbox identifiers, allowed journeys, synthetic ceiling | `validation/acceptance/environments/<env>.yaml` | 6.7 |
| Journey definition | Versioned steps, claims, witnesses, requirement and story identifiers | `validation/acceptance/journeys/<id>.v1.yaml` | 6.4 |
| Harness runner | Executes a journey; contains no journey logic; produces the report | `tests/journey-acceptance/` | 6.4 |
| Identity provisioner | Creates and removes the run's two synthetic Keycloak users in the `synthetic` group | harness module + provisioning identity | 6.1, 6.2 |
| UI driver | Playwright, real Keycloak sign-in, role and label locators, trace, video and screenshot capture with masking | harness module | 6.6 |
| Platform reader (W2) | Reads platform records through customer-facing APIs under the synthetic customer's session | harness module | 6.3 |
| Provider readers (W3) | Read provider sandbox state with sandbox credentials | harness module | 6.5 |
| Telemetry reader (W4) | Reads the correlated trace for depth; optional | harness module | 6.4 |
| Guards | Always-on detectors on every page and response | harness module | 6.4 |
| Coverage engine | Computes per-identifier depth against the denominators | harness module | 6.4 |
| Report | `acceptance-report.json` plus human summary and evidence bundle | workflow artifact | 6.4 |

Every component traces to a capability above; none introduces a new technology beyond Playwright, which
is already in the repository.

## 4. Run Lifecycle

1. **Resolve.** Load the environment profile and journey; record commit, journey digest and profile digest.
2. **Authenticate to Azure** with the acceptance OIDC identity; verify its subscription; read the
   `acceptance-*` secrets needed by the journey. Mask every value.
3. **Probe the environment.** Health and readiness of Web, Business Platform and Keycloak. If not ready,
   emit `ENV-UNAVAILABLE` and stop.
4. **Record the candidate.** Read deployed image digests and revisions for each service; read the effective
   feature settings. Steps whose prerequisite flag is off become `BLOCKED-BY-FLAG`.
5. **Verify provider mode** (Razorpay key id prefix `rzp_test_`, Meta app in development mode, WhatsApp
   sandbox number). A live credential stops the run with a configuration finding.
6. **Provision** synthetic customers A and B (ADR-055).
7. **Execute steps.** Per step: stimulus, then witnesses W1, W2, W3 (and W4 when available), then verdict.
   Guards observe throughout.
8. **Exercise failure paths** declared by the journey (section 6).
9. **Clean up** through product paths (revoke, cancel) and remove Keycloak users; report volumes.
10. **Compute coverage, write the report, scan artifacts for secrets, upload.** A leak finding fails the run
    and withholds the artifact.

## 5. Identity, Secrets And Authority

| Concern | Decision |
|---|---|
| Azure identity | One federated identity per environment, subject bound to this workflow and branch `main`; read-only on Key Vault secrets whose names begin `acceptance-`; Monitoring Reader on the telemetry workspace only; no Contributor, no role-assignment rights, no deployment authority (C-065). |
| Where secrets live | Azure Key Vault. No GitHub environment secret or variable holds a credential. Addresses are non-secret data in git (settings policy S1, S3). |
| Secret names | `acceptance-razorpay-key-id`, `acceptance-razorpay-key-secret`, `acceptance-razorpay-webhook-secret`, `acceptance-meta-app-id`, `acceptance-meta-app-secret`, `acceptance-meta-test-user-session`, `acceptance-meta-test-page-id`, `acceptance-whatsapp-sandbox-recipient`, `acceptance-whatsapp-webhook-secret`, `acceptance-keycloak-provisioner-client-secret`. Each environment's vault holds its own. |
| Platform reads | Only through customer-facing APIs with the synthetic customer's session (ADR-003 tenant authority). No service token, no database access, no ADR-046 route grant. |
| Provider credentials in the product | The harness never reads `customer-connection-` secrets. Custody stays inside Business Platform. Connection proof comes from the provider side (section 6, step S6). |
| Output | Traces, HAR and videos mask password, token and payment fields; artifacts are scanned before upload. |

## 6. Slice 1 Journey: Discover To Connect

Slice 1 reuses WC-107's stories and requirement IDs so the first run also supplies the deployed proof
WC107-R019 still needs. Steps, claims and witnesses:

| Step | Customer action | Claim to verify | W1 screen | W2 platform | W3 provider | Proves |
|---|---|---|---|---|---|---|
| S1 Discover | Open public site, browse catalogue, inspect the DMA card | Offer, rights, limits and GST-inclusive monthly price are shown | Card text | Public catalogue and offerability APIs give the same price, rights and limits | none | AE-01-S02; PG-02, PG-09; WC107-R009 |
| S2 Sign in | Sign in through Keycloak as customer A; sign out and in again | Same account resumes; no forced registration; no token reachable from page script | Landing state | Identity endpoint resolves A's membership; no second identity created | none | PG-03; WC107-R001, R004, R005, R017 |
| S3 Trial | Accept terms and privacy consent, start the trial | Trial is active, rights disclosed, no payment code ran | Confirmation after fresh projection | Relationship state is Trial; timeline and evidence entries exist | none | AE-01-S05; PG-08; WC107-R010, R011, R015 |
| S3b Trial retry | Start the trial again for the same agent | Refused with a clear message; no second trial | Message | Still one trial relationship | none | PG-08 (L5); WC107-R011 |
| S4 Contract | Review and accept the Employment Contract | Contract accepted at the shown version | Accepted state | Contract-journey shows accepted version; acceptance evidence exists | none | AE-01-S06, S07; PG-10 |
| S5 Pay | Pay the onboarding amount with a Razorpay test card | Paid exactly once; relationship Active | Active card | Checkout intent settled; relationship Active; evidence recorded; one activation | Sandbox payment captured for the shown GST-inclusive amount | AE-01-S08; PG-11, PG-12; WC107-R013, R014 |
| S5b Replay and decline | Replay the signed payment webhook; attempt a declined test card | No second activation or charge; decline leaves the relationship not Active | Error and unchanged state | State and evidence unchanged | One captured payment only | PG-12 (L5); WC107-R014 |
| S6 Connect | Start Facebook connection on `/connections`, authorize as the Meta test user | Connected with the granted scopes | Connected card | Provider-connection list shows CONNECTED, scopes, expiry; no token in any response | Meta Graph permission read for the test user shows the app grant | AE-02-S01; PG-16; WC149-R007, R008, R010 |
| S6b Revoke | Revoke the connection | Revoked and the stored secret gone | Revoked state | List shows REVOKED; no token ever returned | Grant no longer used by the platform | PG-16 (L5); WC149-R008 |
| S7 Stop | Use Emergency Stop from the active relationship, then release | Stop reachable, evidenced and reversible | Confirmed stop state | Stop state and evidence recorded | none | AE-01-S10; PG-04, PG-15; C-001 |
| S8 Isolate | As A, request B's relationship and connection by identifier | Refused; B's data never appears | Denial | No B identifiers in any A response | none | AD-004; ADR-003 |

Conversation-driven stories (AE-01-S01, S03, S04, S09) depend on `WC120_CONVERSATION_ENABLED` and the
conversational employment protocol, which default off. Slice 1 reports them `BLOCKED-BY-FLAG` until the
Founder enables those settings for the environment through the settings path; they then run as slice 1c
without architectural change. The machine-readable form of this slice is
`architecture/reference/acceptance/journey-slice-1.v1.yaml`.

Slice 2 (publish through the broker with Graph confirmation of the post) and later slices follow the same
format; they are the strongest emulator-detection steps and depend on removing the Facebook emulator path.

## 7. Oracle Read Contract

| Witness | Source | Authority and limits |
|---|---|---|
| W1 Screen | Playwright DOM using role and label locators, plus the network log | Observational only; never sufficient for a state claim |
| W2 Platform | Customer-facing Business Platform routes under the synthetic customer's session: relationship detail and timeline, contract-journey, checkout intent, evidence list and detail, provider-connections list, notifications, attention, results | Read-only except the stimulus actions a customer can perform; follows ADR-003; routes are taken from `business-platform.openapi.yaml` and verified at build time |
| W3 Provider | Razorpay test API (order and payment fetch); Meta Graph with the test app and test user; WhatsApp sandbox delivery status and signed-webhook delivery to the environment's own endpoint | Sandbox credentials only; mode verified before use |
| W4 Telemetry | Azure Monitor query by correlation identifier for the run | Read-only; optional. If absent, service-reach depth is `NOT-WITNESSED`; client-observed endpoint depth from the HAR still applies |

A claim lists which witnesses are required. A required witness that cannot be read gives `NOT-WITNESSED`.
A witness not declared required for that claim is not applicable and does not affect the verdict.

Raw Billing Engine, constitutional-schema and Key Vault custody data are deliberately unreadable by the
harness; their effects are verified through W2 and W3.

## 8. Coverage And Depth Model

**Depth levels per identifier:** L1 rendered; L2 acted on; L3 state changed and confirmed by W2; L4 evidence
recorded and visible through W2; L5 declared failure path exercised with correct result. A step may state
a depth only when its witnesses agree.

**Denominators:**

| Dimension | Denominator | Source |
|---|---|---|
| Stories | AE-01 to AE-06 stories | `goals/GOAL-005-agent-employment-experience-program.md` |
| Shared gaps | PG-01 to PG-37 | product gap register |
| Requirements | Identifiers listed in a `live_scope` set, seeded from ledgers whose contracts record "provable only on Demo" (WC-107 R009-R016 and R019, WC-149 R007-R010, others added by contract) | `validation/acceptance/live-scope.yaml` |
| Endpoints | Operations in the customer-facing OpenAPI specs | `architecture/reference/api-specs/` |
| Services | Entries in the component registry | `architecture/reference/platform-component-registry.yaml` |

**Report content:** for every denominator item, deepest level reached, step identifiers that reached it, and
`NOT-COVERED` where none did; a flake list; the flag-blocked list; provider-mode findings; synthetic volume;
and the candidate binding (commit, image digests, profile digest, journey digest).

**Honesty rule:** the summary lists what was not tested before it lists what passed.

## 9. Architecture Fitness Contract

Thresholds marked * are initial and are calibrated by the first three runs through a recorded revision.

| ID | Check | Measure | Automated by |
|---|---|---|---|
| F1 | Manual trigger only | Workflow `on:` contains only `workflow_dispatch` | Static test |
| F2 | No credential in GitHub | Workflow references no `secrets.*` other than the automatic token; no credential-named variable | Static test |
| F3 | Environment by data | No code or workflow logic branches on an environment name; a new environment is one profile file plus one workflow option line, and the option list equals the profile files | Static test and schema validation |
| F4 | Witness discipline | Every state claim in every journey requires at least two witnesses unless a listed exception with a reason exists | Journey schema validation |
| F5 | Traceability | Every step cites at least one existing requirement, story or gap identifier | Journey validation against ledgers and registers |
| F6 | Negative control | A fault-injected stub that reports success without calling the provider yields `FAIL`; a stale-cache stub yields `FAIL` | Harness self-test in Docker |
| F7 | Guard efficacy | A seeded token, foreign-tenant identifier and axe violation are each detected | Harness self-test |
| F8 | Leak freedom | Zero secret-pattern findings across all uploaded artifacts | Pre-upload scan |
| F9 | Isolation | Zero customer B identifiers in any customer A response | Guard, every run |
| F10 | Report completeness | Report validates against its schema and contains candidate binding, per-identifier depth and the not-covered list | Report schema validation |
| F11 | Determinism | Step verdicts identical on three consecutive runs of an unchanged candidate for at least 95%* of steps; every retry recorded | Calibration runs |
| F12 | Budget | Slice 1 completes within 20 minutes* and 30 runner minutes*; AI generation within the governed ceiling; no non-sandbox provider traffic (AD-006) | Run metrics |
| F13 | Cleanup | After each run, zero `synthetic` Keycloak users older than 24 hours; zero active synthetic provider connections or subscriptions | Post-run check |
| F14 | No stray messaging | Zero outbound messages from synthetic tenants to non-sandbox recipients | Outbox check |
| F15 | Availability result | A stopped environment returns `ENV-UNAVAILABLE` within 2 minutes* with zero step failures | Harness test |
| F16 | Least authority | The acceptance identity holds no write or role-assignment rights outside its scope | Infrastructure test and run-time role inspection |
| F17 | Report-only | No required check, branch rule or deployment dependency references the workflow | Static test |

## 10. Failure Modes

| Failure | Detection | Result |
|---|---|---|
| Environment stopped or unhealthy | Readiness probe | `ENV-UNAVAILABLE`; no step verdicts |
| Feature flag off | Effective settings read | `BLOCKED-BY-FLAG` with flag name |
| Provider sandbox down or rate limited | W3 error | `NOT-WITNESSED` for that claim, never pass |
| Live credential configured | Mode verification | Run stops; configuration finding |
| Provider blocks automated Meta login | S6 fails at consent | `NOT-WITNESSED`; follow-up to refresh the stored test-user session |
| Keycloak cannot restrict provisioning to a group | Provisioning check | Stop; return to ADR-055 |
| Telemetry unreadable | W4 error | Service-reach depth `NOT-WITNESSED`; run continues |
| Flaky element | Retry recorded | `FLAKY` mark; never silent |
| Secret pattern in an artifact | Pre-upload scan | Run fails; artifact withheld |
| Cleanup fails | Post-run check | Finding in report; next run refuses until resolved or ceiling reported |

## 11. Dependency-Impact Map

| Area | Change | Note |
|---|---|---|
| GitHub | New workflow; one new validation gate id in `validation/engineering-validation.yaml` | Follow CI Validation Speed Policy; test files added to the gate command list |
| Azure | Per-environment acceptance federated identity, `acceptance-` secret prefix, Monitoring Reader | Terraform under the workload module requires Pre-PR runtime lifecycle evidence |
| Keycloak | `synthetic` group and a group-limited provisioning client | Requires fine-grained admin permission support; stop condition |
| Business Platform | Trusted synthetic-tenant marker; exclusion from aggregates; messaging suppression to non-sandbox recipients; correlation identifier on customer responses if absent | Same code paths otherwise; no authority change |
| Billing Engine | Exclude synthetic tenants from revenue aggregation; verify Razorpay test mode | No ledger change |
| Web | None required; role and label locators. Add stable labels only where accessibility requires them | Avoids test-only hooks |
| Existing tests | Unchanged; disabled E2E workflow stays disabled until a separate decision | No overlap |
| Documents | ADR-INDEX, platform state refresh, WC registry | Done in this package |

## 12. Handoff To Solution Architecture

The Solution Architect may decompose the following without inventing a boundary. Each proposed contract
is **not authorized**; each needs Founder authorization.

| Proposed WC | Scope | Depends on |
|---|---|---|
| WC-158 Harness core | Journey and environment schemas, runner, guards, report and coverage engine, negative controls, workflow; self-qualified against a local Docker stack | ADR-054 accepted |
| WC-159 Synthetic tenant support | Marker and its trusted write path, exclusions, messaging suppression, Keycloak group and provisioner, Terraform for the acceptance identity and secret prefix | ADR-055 accepted |
| WC-160 Slice 1 content | S1 to S8 with W1-W3 witnesses; Razorpay and Meta readers; live-scope seed | WC-158, WC-159, sandbox values present |
| WC-161 Sandbox readiness check | Read-only verification that each sandbox secret exists, is non-empty and in test mode, without printing values | Runbook; sandboxes created |
| WC-162 Slice 2 and later | Publish with Graph confirmation; conversational stories; lifecycle rights | Broker path replacing the emulator; relevant flags on |

**Prohibited until authorized:** writing the workflow or harness, creating Azure or Keycloak resources,
touching Demo, entering secrets, and any change to promotion.

**Deferred:** Production profile; AI exploratory companion; promotion gating; additional agents.

## 13. Assumptions And Owners

| ID | Assumption | Owner | If false |
|---|---|---|---|
| A1 | Deployed Keycloak supports restricting a client to one user group | Security Architect | Redesign provisioning; ADR-055 amendment |
| A2 | A trusted marker write path can be added without altering authority | Solution Architect | Return to ADR-055 |
| A3 | A persisted Meta test-user session survives consent without interactive login | Platform IT Expert | Report `NOT-WITNESSED` for S6 until resolved |
| A4 | Razorpay can deliver webhooks to the environment, or the harness can deliver signed replays | Platform IT Expert | Signed replay only |
| A5 | Demo uses Razorpay test mode | Platform IT Expert (verify at build) | Stop; configuration finding |
| A6 | Correlation identifiers reach the telemetry workspace (WC107-R018) | Platform IT Expert | W4 unavailable; depth degraded, declared |
| A7 | Conversation settings can be enabled on Demo by the Founder through the settings path | Founder | Conversational stories stay `BLOCKED-BY-FLAG` |
