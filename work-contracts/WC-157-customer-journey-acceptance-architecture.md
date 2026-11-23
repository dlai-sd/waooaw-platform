# WC-157 - Customer Journey Acceptance Architecture

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-157 |
| Office | Enterprise Architect (INST-004), Office 04 |
| Status | DRAFT FOR FOUNDER REVIEW - ARCHITECTURE ONLY - IMPLEMENTATION NOT AUTHORIZED |
| Founder assignment | Current conversation, 2026-11-23: a fully automated, manually triggered, post-deployment integration and system test driven through the user interface; Demo first with an environment selector; sandbox providers; secrets in Azure Key Vault; real Keycloak login; throwaway test data; report-only verdict; first slice discover to connect Facebook |
| Baseline | `origin/main` at `b089a9d169c37306e162ab54c11cd24ee1e2d9be` |
| Branch | `ib/157/customer-journey-acceptance-architecture` |
| Decisions | ADR-054 Customer Journey Acceptance; ADR-055 Synthetic Acceptance Tenants and Evidence (both PROPOSED) |
| Requirement ledger | [WC-157-requirements.yaml](./WC-157-requirements.yaml) (NOT_APPLICABLE: architecture only) |
| Constitutional basis | C-023, C-027, C-049, C-059, C-063, C-065, C-071, C-080 |
| Parked by Founder | The customer-value epic list (operations and Founder-proving work removed from focus) is retained in the session record and is not part of this contract |

## Authority And Scope

### In scope

1. ADR-054 and ADR-055 and their ADR-INDEX rows.
2. `architecture/reference/acceptance/customer-journey-acceptance-architecture.md`: context and component views,
   run lifecycle, identity and secrets, slice 1 journey, oracle read contract, coverage and depth model,
   architecture fitness contract, failure modes, dependency-impact map, handoff and assumptions.
3. `architecture/reference/acceptance/journey-slice-1.v1.yaml`: the machine-readable slice 1 journey.
4. `architecture/reference/runbooks/acceptance-sandbox-setup.md`: the Founder's credential-entry procedure.

### Out of scope and prohibited

- Writing the workflow, harness, tests or any `src/` code; creating Azure, Keycloak or provider resources;
  entering or reading any secret; running anything against Demo; changing promotion or required checks.
- Authorizing WC-158 to WC-162. They are proposed in the architecture handoff and each needs Founder authorization
  and its own ledger before implementation.
- Changing the disabled E2E workflow, constitutional documents or existing ADR decisions.

## Inputs

| Input | Status |
|---|---|
| Founder brief and answers in this conversation | Present |
| `fundamental-customer-journeys.md`, `WC-107-requirements.yaml` | Present on `main` |
| GOAL-005 program and product gap register | Present on `main` |
| ADR-003, 014, 046, 050, 053; settings policy | Present on `main` |
| Code and workflow surveys of 2026-11-23 | Read-only; findings cited in the architecture |

## Canonical Requirement Index

None. This contract authorizes no implementation, so its ledger is `NOT_APPLICABLE`. The measurable obligations
for the future build are the fitness checks F1 to F18 in the architecture, which the implementing contracts
convert into requirement IDs.

## Definition Of Done

1. ADR-054, ADR-055 and the architecture package exist, cross-reference each other and cite only existing
   capabilities, drivers, claims, requirement IDs, story IDs and gap IDs.
2. Every component traces to a capability; every technology choice has an ADR covering alternatives, maturity,
   security, operability, cost, interoperability, reversibility and build-versus-adopt.
3. The journey YAML parses, and every identifier it cites exists in its source register or ledger.
4. ADR-INDEX lists both ADRs; platform state refresh has been run in Docker and the PR body precheck passes.
5. Author review recorded in the PR for the exact head; Founder reviews and merges.

## Stop Conditions

- Any need to decide a technology outside ADR-054 or ADR-055.
- A constitutional conflict between synthetic evidence and C-027 or C-023 that the ADR cannot resolve.
- A cited identifier that does not exist.
- Any request to execute, deploy, provision or handle a secret under this contract.

## Handoff

The Solution Architect may decompose WC-158 to WC-162 as listed in the architecture section 12. Prohibited,
deferred and owner-decided items are listed there and in section 13.
