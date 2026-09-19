# Web App Agent Testing — Continuous Quality Loop

**Status:** Founder brainstorming proposal — not an approved architecture or implementation authorization
**Date:** 2026-09-19
**Prepared by:** Enterprise Architect (INST-004), Founder-requested strategy session
**Decision owner:** Founder / Constitutional Steward (INST-001)
**Purpose:** Create a durable basis for deciding how WAOOAW can automate web application and WhatsApp client testing with minimal Founder intervention.

## 1. Objective

Enable a single-person software company to receive continuous, evidence-backed quality feedback without manually executing every web and WhatsApp test.

The proposed Continuous Quality (CQ) Loop should:

- maintain a growing bank of web and WhatsApp test cases;
- identify test cases affected by each Work Contract, component, and PR;
- execute tests against an isolated, reachable test deployment;
- use deterministic assertions for constitutional and business-critical behavior;
- use visual or natural-language testing for exploratory UI coverage;
- capture screenshots, traces, logs, and structured failure data; and
- produce a concise defect register that the Founder can review and convert into a GitHub Issue or Work Contract.

The target operating model is **Founder reviews defects and decisions; the testing system performs routine execution and evidence collection**.

## 2. Problem

The current platform is large enough that manual testing by one person is no longer a reliable quality strategy. The application includes a web portal, multiple backend services, customer journeys, identity flows, and a WhatsApp channel. A human tester cannot repeatedly exercise all relevant journeys after every change with consistent evidence and coverage.

The proposed solution must also respect the current deployment boundary:

- Demo is a temporary Azure Container Apps deployment.
- Demo access is restricted to the Founder browser public IPv4 address (`/32`).
- A GitHub-hosted runner does not originate from that laptop IP.
- The Demo URL is therefore not automatically reachable by a normal GitHub Actions runner.

This is a network and environment problem, not only a test-tool problem.

## 3. Current Repository Baseline

The repository already provides useful building blocks:

| Existing capability | Current evidence | CQ implication |
|---|---|---|
| Web E2E framework | `web/playwright.config.ts` | Use Playwright as the deterministic execution base. |
| Web test location | `web/tests/e2e/` | Keep executable browser adapters close to the web package. |
| Acceptance test convention | `tests/acceptance/` | Keep cross-channel business journeys and acceptance ownership visible. |
| E2E workflow | `.github/workflows/e2e-acceptance-tests.yaml` | Reuse reporting and artifact patterns, but add dynamic target URL support. |
| Deployment URL | `environment-deployment.yaml` outputs `web_url` | The URL reaches `deploy.yaml`, but is currently printed only in the workflow summary. |
| Demo access control | `scripts/goal006_dispatch_inputs.py` and Goal 006 deployment topology | Demo apply requires the Founder browser IPv4 address. |
| Existing quality guidance | `tests/QA-STRATEGY.md`, `tests/QA-POLICY.md`, `tests/AGENTS.md` | CQ must preserve existing coverage, synthetic-data, and separation-of-duties rules. |

## 4. Proposed CQ Operating Model

The CQ system is a testing capability, not a replacement for the application’s constitutional runtime controls.

```text
Work Contract / PR
        |
        v
Agent identifies affected routes, contracts, journeys, and existing test cases
        |
        v
Test-case bank compliance and code-coverage pre-check
        |
        v
Application deployed to an isolated CQ-reachable environment
        |
        v
Deterministic Playwright tests + optional visual/natural-language exploration
        |
        v
WhatsApp sandbox/API tests, where applicable
        |
        v
Structured result JSON + screenshots + traces + logs
        |
        v
HTML report and Founder-readable defect register
```

The first release should not depend on a low-code AI orchestrator. GitHub Actions, Playwright, structured result files, and a small report generator are sufficient for the first useful loop. Midscene.js or another visual agent can be added as an adapter after the deterministic path is reliable.

## 5. Execution Entry Points

The CQ execution should be a separate workflow from deployment.

### 5.1 Automatic Entry

The preferred automatic path is a `deployment_status` event:

```text
deploy.yaml
  -> create or update GitHub Deployment
  -> environment = cq or approved test target
  -> state = success
  -> target_url = verified web URL
  -> Continuous Quality workflow starts
```

The CQ workflow must ignore deployments that are not successful, not intended for CQ, or missing a validated `target_url`.

### 5.2 Manual Entry

The same CQ workflow should support `workflow_dispatch` with:

- target URL;
- environment label;
- optional PR or Work Contract reference; and
- optional scenario selection.

The manual path must call the same test job as the automatic path. It is a recovery mechanism, not a second test implementation.

### 5.3 Deployment Contract Gap

The current deployment engine exposes `web_url` as a reusable-workflow output and `deploy.yaml` writes the URL to `$GITHUB_STEP_SUMMARY`. This does not create a GitHub Deployment or emit `deployment_status` with `target_url`.

Therefore, automatic CQ triggering requires a deployment-contract change. The change must preserve the current authorization, verification, and environment boundaries.

## 6. Network and Environment Strategy

### 6.1 Why Current Demo Does Not Work for GitHub-Hosted CQ

The current Demo FQDN is publicly named but source-restricted. The ingress allowlist accepts the Founder laptop public IP, not every internet client. A GitHub-hosted runner has a different and changing egress address.

The URL is not DNS-bound to the laptop. The ingress policy is bound to the laptop IP.

### 6.2 Options

| Option | Feasibility | Cost / risk | Assessment |
|---|---|---|---|
| GitHub-hosted runner against current Demo | Low | No stable allowlisted source; access fails | Not suitable. |
| Dynamically allow GitHub-hosted runner ranges | Low | Broad, changing ranges and weak boundary | Avoid. |
| Dedicated Azure runner with stable NAT IP | High | Additional networking and NAT cost | Works if cost is accepted. |
| Separate CQ environment reachable by Azure runner | High | Additional environment cost and deployment work | Preferred autonomous model. |
| Laptop tunnel | Low | Requires laptop online and Founder involvement | Not autonomous. |

### 6.3 Recommended Direction

Keep Demo Founder-only and introduce a separately controlled CQ target reachable by the CQ runner. The CQ target may be:

- a short-lived environment;
- a dedicated revision or deployment boundary; or
- an Azure-hosted test runner with a stable egress IP temporarily allowlisted under a lease.

The choice depends on Azure cost, topology, and whether the existing environment contract can support a new `cq` environment. No production traffic or customer data is required for CQ.

## 7. Test Case Bank

The web test bank should be maintained like unit tests: versioned, reviewable, linked to work, and protected from silent weakening.

Suggested structure:

```text
tests/
  web/
    cases/
      baseline/          # protected business and constitutional journeys
      work-contracts/    # cases required by accepted Work Contracts
      generated/         # agent-created candidate cases for a PR
    schemas/             # YAML/JSON schema and validation rules
    manifests/           # case ownership and coverage index
```

Executable adapters remain separate:

```text
web/tests/e2e/            # Playwright and visual-agent adapters
```

### 7.1 Case Categories

| Category | Purpose | Can the agent weaken it automatically? |
|---|---|---|
| Protected baseline | Preserve known business, security, and constitutional behavior | No |
| Work Contract case | Prove the current component’s acceptance criteria | Only within approved scope |
| Generated candidate | Explore changed routes and likely regressions | Yes, but changes remain visible and non-authoritative until promoted |
| Exploratory visual case | Find unexpected layout or interaction defects | Yes, subject to evidence and triage |

### 7.2 Case Contract

Each case should contain:

- stable case ID and title;
- Work Contract, PR, or requirement reference;
- channel (`web`, `whatsapp`, or `api`);
- priority and blocking policy;
- preconditions and synthetic-data requirements;
- natural-language steps where visual execution is intended;
- deterministic assertions for mandatory outcomes;
- expected security and tenant-isolation conditions;
- artifact policy; and
- lifecycle status (`candidate`, `active`, `protected`, `retired`).

Example shape:

```yaml
id: WEB-AUTH-001
title: Customer reaches the correct dashboard after sign-in
source:
  work_contract: WC-NNN
  requirement: Customer authentication
status: protected
priority: P0
channel: web
steps:
  - instruction: Open the customer login page
  - instruction: Sign in with the synthetic customer account
assertions:
  - The customer dashboard is visible
  - Only the authenticated customer's data is displayed
evidence:
  screenshot: on-failure
  trace: on-failure
  video: on-failure
```

Selectors, fixture wiring, and provider-specific mechanics should remain in adapters. The case bank should describe intent and expected behavior rather than fragile CSS or XPath.

## 8. Case-Bank Maintenance in PRs and Work Components

### 8.1 Work Component Start

When a Work Contract is groomed, the responsible quality context identifies:

1. existing baseline cases affected by the work;
2. new acceptance cases required by the Definition of Done;
3. negative, authorization, tenant-isolation, and failure cases;
4. required synthetic personas and disposable state; and
5. whether the case needs web, API, WhatsApp, or multiple adapters.

### 8.2 PR Pre-Check

Before compilation or deployment, the pre-check should:

- validate case syntax and schema;
- map changed web routes/components to cases;
- require a linked case for behavior-changing web work;
- prevent deletion of protected cases without an explicit approved reason;
- detect assertion weakening;
- run existing unit/component coverage gates; and
- report code coverage separately from business-scenario coverage.

### 8.3 Agent-Generated Cases

The agent may inspect the PR diff, Work Contract, API contract, visible routes, and existing cases to propose new candidate cases. It must not infer that a passing exploratory interaction proves a business requirement.

Generated cases become authoritative only when their source requirement and expected outcome are traceable. A generated case may be committed by automation, but its status must remain visible.

### 8.4 Retirement

A protected case is retired only when the owning requirement is explicitly removed or replaced. A failing case is evidence of a defect; it is not evidence that the case should be weakened.

## 9. Test Execution Layers

### Layer 1 — Deterministic Checks

Use existing Jest, TypeScript, Python, .NET, API, and Playwright assertions for:

- authentication and authorization;
- tenant isolation;
- lifecycle transitions;
- billing and limits;
- constitutional controls;
- accessibility rules;
- API contracts; and
- failure and recovery behavior.

These checks should block the CQ result when mandatory assertions fail.

### Layer 2 — Visual and Natural-Language Exploration

Use Playwright as the execution base. Midscene.js or a comparable visual agent may drive natural-language flows for exploratory coverage.

Constraints:

- model cost and local-model availability must be verified;
- AI output must not replace deterministic assertions;
- screenshots and traces are required for triage;
- nondeterministic exploratory failures should be classified separately from blocking failures; and
- visual agents must use synthetic accounts and bounded test data.

### Layer 3 — WhatsApp Sandbox/API

Use an official Meta WhatsApp Cloud API test resource or another explicitly isolated provider sandbox. Do not automate a personal WhatsApp Web session or use an unofficial client against a real account.

The adapter should validate:

- outbound message acceptance;
- webhook correlation;
- response content and state transition;
- retry and timeout behavior;
- redaction of payloads in evidence; and
- absence of production recipients.

## 10. Evidence and Defect Register

Every run should produce machine-readable results before rendering human-readable output.

```text
raw test result
  -> normalized result.json
  -> evidence manifest
  -> defect-register.md
  -> HTML report
```

The normalized result should include:

- run ID, commit SHA, PR, Work Contract, environment, and target URL;
- case ID, attempt, start/end time, and outcome;
- failure category and severity;
- assertion or exception summary;
- screenshot, trace, video, console, network, and webhook artifact references;
- suspected component or owner; and
- reproducibility information.

The HTML report is useful for the Founder. The structured JSON is the durable input for later automation or Copilot-assisted Issue creation.

The first version may stop at HTML plus copy/paste into Copilot. Automatic GitHub Issue creation is a later convenience, not a prerequisite for CQ value.

## 11. Coverage Model

Code coverage and scenario coverage must not be conflated.

| Measure | Answers | Gate |
|---|---|---|
| Unit/component coverage | Which executable lines and branches were exercised? | Existing repository thresholds, including the current web Jest baseline. |
| Protected case coverage | Which required journeys were executed? | All applicable P0/P1 cases must run. |
| Requirement traceability | Which Work Contract requirements have cases? | No unlinked behavior-changing web requirement. |
| Exploratory coverage | What unexpected UI behavior did the agent probe? | Reported as evidence, not automatically treated as complete business coverage. |

## 12. Components Impacted

Potentially impacted repository areas are:

| Area | Expected responsibility |
|---|---|
| `tests/web/` | Test-case bank, schemas, manifests, and case metadata |
| `web/tests/e2e/` | Playwright and visual-agent adapters |
| `web/playwright.config.ts` | Dynamic base URL and artifact configuration |
| `.github/workflows/` | PR pre-check, deployment-triggered CQ, manual fallback, artifact publishing |
| `deploy.yaml` | Deployment metadata contract and verified `target_url` publication |
| Azure deployment topology | CQ environment, runner network reachability, access lease, and cleanup |
| `scripts/` | Case validation, result normalization, and report generation |
| `tests/QA-*` | Quality-gate and ownership alignment, subject to required authority |
| GitHub Environments/Secrets | Test credentials, sandbox credentials, and least-privilege workflow permissions |

This list is an impact map, not authorization to modify any of these areas.

## 13. Proposed End-to-End Process

```text
1. Work Contract defines behavior and acceptance criteria.
2. Agent maps requirements to existing test cases.
3. Agent proposes new cases for uncovered behavior.
4. PR pre-check validates case bank, traceability, and code coverage.
5. Application is built and deployed to a CQ-reachable isolated target.
6. Deployment publishes verified target URL and CQ trigger metadata.
7. CQ runs protected cases, Work Contract cases, and bounded exploratory cases.
8. WhatsApp adapter runs only against a sandbox/test identity.
9. Results are normalized and evidence is uploaded.
10. HTML defect register is generated.
11. Blocking failures stop the CQ result; non-blocking findings remain reportable.
12. Founder reviews the report and creates or approves the next Issue/Work Contract.
13. Passing new cases are promoted to protected coverage through the normal review process.
```

## 14. Feasibility Assessment

| Area | Feasibility | Finding |
|---|---|---|
| Test-case bank | High | Fits existing acceptance and Playwright conventions. |
| PR compliance and coverage | High | Existing workflows and coverage tools provide a usable base. |
| Automatic post-deployment trigger | Medium | Requires a real GitHub Deployment with `target_url`; the current workflow only prints the URL to the summary. |
| Autonomous access to current Demo | Low without change | Demo allowlists the Founder laptop IP; GitHub-hosted runners cannot reach it. |
| Dedicated Azure runner or CQ target | High | Technically viable, with networking and cost decisions required. |
| Visual AI testing | Medium | Useful for exploration, but model cost and nondeterminism require bounded use. |
| WhatsApp testing | Medium | Feasible through an official sandbox/API; real WhatsApp Web automation is unsuitable. |
| HTML-first reporting | High | Can deliver value before automatic Issue creation. |

## 15. Simulation Run Findings

The proposed workflow was simulated against the current repository structure and deployment behavior.

| Simulated path | Result | Blocker or gap |
|---|---|---|
| `deployment_status` automatic trigger | Blocked | `deploy.yaml` does not create a deployment status containing `target_url`. |
| Manual URL execution | Feasible | A new workflow is required, but it can accept a URL directly. |
| Playwright execution | Partially ready | Existing E2E workflow uses static URL secrets or localhost fallback, not normalized CQ input. |
| Agent-managed test bank | Missing | No protected bank, schema, PR mapping, or lifecycle policy exists yet. |
| Structured report and Issue creation | Missing | No normalized result processor or defect-register generator exists yet. |
| Current Demo reachability | Blocked for hosted runner | Ingress is restricted to the Founder browser IP. |

## 16. Phased Feasibility Path

### Phase 0 — Decision and Boundary

- Decide whether CQ uses a dedicated Azure target or a fixed-egress Azure runner.
- Confirm cost ceiling and data boundary.
- Confirm whether the first output is HTML only or HTML plus GitHub Issue automation.

### Phase 1 — CQ Foundation

- Define the case schema and protected-bank rules.
- Add manual URL execution.
- Normalize Playwright URL, result, and artifact handling.
- Produce HTML and structured JSON.

### Phase 2 — Deployment Integration

- Publish verified deployment metadata.
- Add automatic CQ trigger after successful CQ-reachable deployment.
- Add cleanup and access-lease evidence.

### Phase 3 — Agent Case Maintenance

- Generate candidate cases from Work Contracts and PR changes.
- Add traceability and assertion-strength checks.
- Promote reviewed cases into the protected baseline.

### Phase 4 — Visual and WhatsApp Adapters

- Add bounded Midscene-style exploration.
- Add official WhatsApp sandbox/API flows.
- Add channel-specific evidence and redaction checks.

### Phase 5 — Defect Automation

- Normalize all failures into a defect register.
- Deduplicate by case, commit, environment, and failure fingerprint.
- Optionally create or update GitHub Issues with least-privilege permissions.

## 17. Open Decisions for Further Brainstorming

1. Is the cost of a dedicated stable-egress Azure CQ runner acceptable?
2. Should CQ run in a new `cq` environment, or should an existing environment gain a dedicated test boundary?
3. Should the first release produce HTML only, with Founder/Copilot Issue creation, or should Issue automation be included immediately?
4. Which three web journeys are the first protected baseline?
5. Which WhatsApp provider and test identity are acceptable under the sandbox boundary?
6. Which failures block the CQ result, and which remain advisory?
7. Is Midscene required for the first release, or should deterministic Playwright establish the foundation first?

## 18. Current Conclusion

The CQ Loop is feasible and valuable, but the current Demo deployment cannot be the autonomous test target without changing its network access boundary. The lowest-risk next step is to preserve Demo as Founder-only, establish a CQ-reachable test target, and begin with a protected test-case bank plus deterministic Playwright execution.

The system should earn the right to add visual AI and WhatsApp automation after the basic loop can reliably produce evidence and an HTML defect register. Automatic GitHub Issue creation is useful, but it is not required to prove the core value.
