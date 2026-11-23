# WC-163 - Acceptance Coverage, Telemetry Witness And Closed Boundaries

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-163 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-163 |
| Founder assignment | Current conversation, 2026-11-23: "complete these points in next pr": journeys for `WC107-R012`, `WC107-R016` and `WC107-R019`; OTLP wiring and the telemetry witness; the Production profile, AI exploratory companion, promotion gating and additional agents. The blocked items (Key Vault access path, sandbox secrets, Terraform and Keycloak applies) are supplied by the Founder at the end of this PR |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `76a4e31995ef3593048cf719c171dd22b1aadf65` |
| Branch | `ib/163/acceptance-coverage-telemetry-and-guards` |
| Decisions | ADR-054, ADR-055 (accepted); ADR-056 (authored here, PROPOSED) |
| Requirement ledger | [WC-163-requirements.yaml](./WC-163-requirements.yaml) |
| Depends on | WC-158 to WC-162 (merged) |
| Constitutional basis | C-023, C-049, C-059, C-063, C-065, C-071, C-080 |

## Authority And Scope

### In scope

1. **Journeys.** Plan `slice-3-hire-and-selection` with S10 (coupon changes the payable amount before checkout, `WC107-R012`) and S11 (My Agents selection is one-use, `WC107-R016`); specs; the secret name `acceptance-demo-coupon-code`.
2. **WC107-R019 rollup.** `validation/acceptance/rollup.v1.yaml` mapping the five fundamental journeys to steps; a `device` dimension (desktop or a 360 wide phone) in the config, workflow and report; a rollup command that proves the requirement only for one exact candidate and keeps it open while any journey, device or candidate identity is missing.
3. **OTLP and the telemetry witness.** The `otlp_endpoint` variable in the workload Terraform (default null, three services); a correlation id on every request the harness makes; a console-log correlation reader (workflow step and report section) that states honestly that a cross-service trace is not yet witnessed.
4. **Additional agents.** `validation/acceptance/agents.yaml`; plans name an ACTIVE registered agent; specs take the offer text from the registry and may not hard-code an agent name.
5. **Closed boundaries.** The Production boundary as reserved data that is never runnable; the AI exploratory companion as a disabled, non-deciding, zero-budget policy and a report field that cannot change the verdict; promotion gating as ADR-056 (PROPOSED), a `promotion-policy.yaml` with `enforced: false` and a pure evaluator that nothing may reference.
6. Correction found while reading the web source: a confirmed trial returns the relationship in its response and lands on My Agents, so the shared trial step now reads the relationship from that response.

### Out of scope and prohibited

- Running anything against Demo or any provider; entering or reading any secret; applying Terraform or Keycloak changes.
- Deploying an OTLP collector or setting `otlp_endpoint` in any environment root.
- Making Production runnable, accepting ADR-056, wiring any required check or promotion step to acceptance, enabling the exploratory companion or activating a reserved agent.
- Any product change.

## Inputs

| Input | Status |
|---|---|
| PRs #627 and #628 merged | Present on `main` |
| WC-107 ledger and `fundamental-customer-journeys.md` sections 5.3 and 5.4 | Present on `main` |
| Founder authorization of implementation code in this session | Present (current conversation) |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC163-R001 | S10 requires the Hire command amount, the platform-validated amount and a clean address to agree, with no checkout order created before the coupon is applied |
| WC163-R002 | S11 requires a clean My Agents address, the selected card, and a hand-off cookie that is HttpOnly, Secure, SameSite=Strict, path-scoped, free of any identifier and rejected on replay |
| WC163-R003 | The shared trial step reads the relationship from the confirmation response and the My Agents landing, not from the address |
| WC163-R004 | The rollup passes only when every mapped journey passes on desktop and mobile for reports with the same commit and service images; a journey with no steps, a missing device, a failing step or a candidate mismatch keeps it open |
| WC163-R005 | The rollup map names only existing steps, explains every empty journey and covers desktop and mobile; the Registration journey is recorded as not coverable by synthetic users |
| WC163-R006 | Every report records its device, and the mobile run uses a 360 wide phone viewport |
| WC163-R007 | Every harness request to the product carries the run's correlation id and the telemetry query is built only from safe inputs with a poll nonce |
| WC163-R008 | The report states whether telemetry was not read, empty or seen and never claims a cross-service trace from console-log correlation |
| WC163-R009 | The `otlp_endpoint` variable is null by default, validated, applied to exactly three services and absent from every environment root |
| WC163-R010 | A plan may test only a registered ACTIVE agent, a non-active agent needs a reason, and no spec or harness code names an agent |
| WC163-R011 | Production is reserved data that is never runnable, never a profile, never a workflow option and lists its prerequisites |
| WC163-R012 | The exploratory companion is disabled, non-deciding and zero-budget, and exploratory notes cannot change a verdict or a conclusion |
| WC163-R013 | The promotion policy is not enforced, the evaluator answers ELIGIBLE or NOT_ELIGIBLE with every reason and is declared evidence only, and nothing in workflows, catalog or scripts references them |
| WC163-R014 | The ratchet baseline records `WC107-R012` and `WC107-R016` as covered and the live scope drops their deferrals, while the gate still refuses a lower floor or a new deferral |

## Definition Of Done

1. Every requirement has direct executable evidence run in Docker at the exact head.
2. `terraform fmt` and `validate` pass for the workload root; the workflow passes `actionlint`.
3. A local run of the slice 3 plan against a non-product stand-in produces a schema-valid report, and the rollup command runs on two device reports.
4. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for the exact head; Founder reviews and merges.
5. No Demo, Meta or live-provider result is claimed.

## Stop Conditions

- Any change that makes Production runnable, enforces promotion gating, enables the exploratory companion or activates a reserved agent.
- Any need to put a credential in GitHub or to change a product behavior.
- A cited identifier that does not exist.

## Implementation Record

Evidence at the exact head is in the PR body.

- **Registration stays open.** `WC107-R019` needs a Registration journey, which local synthetic users cannot exercise (architecture T9). The rollup therefore reports the requirement OPEN until a later contract covers it; it is never reported as passed.
- **Console logs are not a trace.** The correlation reader shows which services logged a run's id. It does not witness `WC107-R018`, which needs queryable cross-service traces from an OTLP collector the Founder must deploy and point `otlp_endpoint` at.
- **Coupon.** S10 needs a test coupon that gives a partial discount on the Digital Marketing hire; the Founder creates it on the pricing admin screen and stores it as `acceptance-demo-coupon-code`.
- **Mobile means a second run.** One run per device keeps each device's customers separate (one trial per customer); the rollup combines the two reports.
- **Not run:** any Demo or provider call, a real OTLP export, a Production profile of any kind.
