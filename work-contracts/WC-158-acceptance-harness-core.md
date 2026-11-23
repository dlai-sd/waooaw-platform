# WC-158 - Customer Journey Acceptance Harness Core

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-158 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-158 |
| Founder assignment | Current conversation, 2026-11-23: "Synthetic customer for testing"; scope WC-158 + WC-159 + WC-160 (through slice 1); ADR-054 and ADR-055 accepted; implementation code authorized for this session |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `018d196e184e6a29f5ec4264bfe80d9134ea0cd4` |
| Branch | `ib/158/synthetic-acceptance-customers` |
| Decisions | ADR-054 (accepted), ADR-055 (accepted) |
| Controlling specification | `architecture/reference/acceptance/customer-journey-acceptance-architecture.md` sections 3, 4, 7, 8, 9, 10 |
| Requirement ledger | [WC-158-requirements.yaml](./WC-158-requirements.yaml) |
| Constitutional basis | C-023, C-027, C-049, C-059, C-063, C-065, C-071, C-080 |

## Authority And Scope

### In scope

1. JSON Schemas and validators for the environment profile, the journey test plan and the acceptance report.
2. The environment profile for `demo` (non-secret data only).
3. The helper library and runner in `tests/journey-acceptance/`: `claim()` witness discipline, verdict
   vocabulary, run-depth engine, always-on guards, secret scanner, report writer, availability probe.
4. The static coverage gate, the ratchet file `validation/acceptance/coverage-baseline.yaml`, plan/spec agreement,
   and wiring of these static checks into the validation catalog and release qualification.
5. The workflow `.github/workflows/customer-journey-acceptance.yaml` (manual only, report-only, no GitHub secrets).
6. Self-tests that prove the harness detects a fault-injected success (negative control) and each guard.

### Out of scope and prohibited

- Running the workflow, or anything else, against Demo or any provider; entering or reading any secret.
- Creating Azure, Keycloak or provider resources (WC-159 authors Terraform; applying it needs separate authority).
- Making any required check, deployment gate or branch rule depend on the acceptance workflow.
- Journey content (WC-160) and synthetic tenant support (WC-159).

## Inputs

| Input | Status |
|---|---|
| ADR-054 and ADR-055 | ACCEPTED by the Founder, 2026-11-23 |
| Architecture package (WC-157, PR #626) | Merged on `main` |
| Digest-pinned TypeScript runner (`Dockerfile.test-runner-ts`, Playwright 1.62.1) | Present on `main` |
| Founder authorization of implementation code in this session | Present (current conversation) |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC158-R001 | The acceptance workflow triggers only on `workflow_dispatch`, with a `concurrency` group of one run per environment (F1) |
| WC158-R002 | The workflow references no `secrets.*` other than the automatic token and holds no credential-named variable (F2) |
| WC158-R003 | Environment is data: no harness code or workflow logic branches on an environment name, and the workflow option list equals the profile files (F3) |
| WC158-R004 | `claim()` rejects a claim with fewer than two required witnesses unless a listed exception with a reason exists, and a required witness that cannot be read yields `NOT-WITNESSED`, never a pass (F4) |
| WC158-R005 | Plan validation fails a step that cites no requirement, story, gap or driver identifier, or any identifier that does not exist in its source register or ledger (F5) |
| WC158-R006 | A fault-injected provider stub that reports success without calling the provider, and a stale-cache stub, both yield `FAIL` (F6) |
| WC158-R007 | A seeded token, a seeded foreign-tenant identifier and a seeded accessibility violation are each detected by the guards (F7) |
| WC158-R008 | The pre-upload artifact scan finds seeded secret patterns, fails the run and withholds the artifact (F8) |
| WC158-R009 | A customer B identifier in any customer A response is a `FAIL` finding (F9) |
| WC158-R010 | The report validates against its JSON Schema and always contains candidate binding, per-identifier depth, flag-blocked list and the not-covered list before the passed list (F10, C-049) |
| WC158-R011 | The depth engine assigns L1 to L5 only when the witnesses for that level agree, and never above the weakest witnessed level (ADR-054 item 6) |
| WC158-R012 | The workflow conclusion is red only for any `FAIL` or `ENV-UNAVAILABLE`; the other non-pass verdicts are warnings; nothing in required checks or deployment references the workflow (F17) |
| WC158-R013 | The static coverage gate fails a pull request that lowers `coverage-baseline.yaml`, or adds a live-scope identifier without a spec (F19) |
| WC158-R014 | The plan/spec gate fails a plan step without a spec, and a spec citing a step or identifier that does not exist (F20) |
| WC158-R015 | A stopped or unreachable environment yields `ENV-UNAVAILABLE` within the probe timeout with zero step failures (F15) |
| WC158-R016 | The static acceptance checks and the harness unit tests run in the validation catalog on every pull request that changes them (`quality:scripts` and `quality:typescript`), with the harness type-checked and covered at 90% line and 80% branch |

## Definition Of Done

1. Every requirement above has direct executable evidence run in Docker at the exact head (unit tests through the
   digest-pinned TypeScript runner; schema and static checks through the Python runner).
2. The Playwright specs compile with `tsc` and are listed by `playwright test --list` in the runner.
3. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for
   the exact head; Founder reviews and merges.
4. No hosted or Demo execution is claimed.

## Stop Conditions

- Any need to change a decision in ADR-054 or ADR-055.
- Any design that requires a credential in GitHub, a service token, direct database access or an ADR-046 grant.
- Any change that makes the acceptance verdict block promotion.
- A cited identifier that does not exist.

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Decisions and limits found while building:

- **Unit-test runner.** The helper-library unit tests use the built-in Node test runner on the pinned runner's Node 24 (type stripping, no new dependency) instead of Jest: the repository's Jest setup is bound to the Next.js app directory and cannot host a second root. Coverage is enforced with `--test-coverage-lines=90 --test-coverage-branches=80` in `scripts/validation_control/run_typescript_quality_gate.sh`.
- **Plan and profile compile.** The harness reads JSON compiled by `scripts/acceptance_static_gates.py compile` (the runner image has no YAML parser at top level); the same script runs the static gates F1 to F5, F17, F19 and F20.
- **Trace and video are off in v1.** They cannot be masked reliably; the report states this as a limit. A redacted network log is kept.
- **Private Key Vault.** The environment vault has `public_network_access_enabled = false`, so a GitHub-hosted runner cannot read the `acceptance-` secrets. The workflow records unreadable secrets as a configuration finding and steps degrade to `BLOCKED-BY-FLAG` or `NOT-WITNESSED`. The Founder must choose the access path before the first Demo run (runbook step 6).
- **Not run:** the workflow itself, any Demo or provider call, and the hosted gates.
