# WC-156 - Validation Runner Image Pull Retry

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-156 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-156 |
| Founder assignment | Current conversation: "ok fix it" (the web gate failed on PR 624 because the runner image pull was reset) |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `cf739c71` |
| Related contracts | WC-104 (immutable runner supply and consumption); WC-155 |
| Requirement ledger | [WC-156-requirements.yaml](./WC-156-requirements.yaml) |
| Constitutional basis | C-059, C-065, C-071 |

## Problem And Evidence

Run 45122486536 on PR 624: the job "Web unit tests + type check" failed 8 seconds in with `failed to copy: read tcp ...:443: connection reset by peer` while `.github/actions/use-validation-runner` ran `docker pull "$image"` for the digest-pinned TypeScript runner. No test had started. The step had no retry, so a single transient registry reset failed the gate and forced a manual re-run.

Run 45125464858 on PR 625 (the first fix for the above): the job ".NET unit tests (test-dotnet:business-platform)" failed with 1 of 4163 tests, `GovernedReservationAndSettlementUseSignedMtlsEvidenceAndFullActuals`, throwing `Failed to bind to address http://0.0.0.0:5001: address already in use` from `RawConstitutionalServer.StartAsync`. Root cause: that test helper starts a real Kestrel host on a free loopback port, but VSTest runs from the build output directory, which holds the production `appsettings.json` (`Kestrel:Endpoints:Rest:Url = http://0.0.0.0:5001`). The slim builder therefore also bound the production endpoint in every instance. More than ten tests in `ConstitutionalGrpcCoverageTests` and the Postgres owner test use the helper and xunit runs test classes in parallel, so any overlap of two servers fails the later one. This is a latent defect in the test, independent of the registry.

## Authority And Scope

### In scope

1. The pull of the already attested, digest-pinned runner image is attempted up to three times with short waits (5 s, 10 s) and fails the step with a clear error after the third attempt.
2. A regression test that the retry exists, is bounded, runs after the attestation check, and still pulls by the same pinned reference.
3. `RawConstitutionalServer` in `tests/business-platform.Tests` no longer inherits production configuration, so concurrent instances cannot collide on the production Kestrel endpoint, with a regression test that starts two at once.

### Out of scope

- Any change to which image is pulled, to attestation verification, or to the pull duration telemetry schema.
- Retries for other network steps.
- Any change to `src/business-platform` production configuration or to test parallelism; the defect is in the test helper, not in the product.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-156-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC156-R001 | The runner image pull retries transient failures at most three times, then fails the step with an error naming the image |
| WC156-R002 | The retry follows attestation verification and pulls the same digest-pinned reference, so a retry cannot change what runs |
| WC156-R003 | In-process test servers that open real sockets use only their explicit loopback port and never the production Kestrel endpoint from `appsettings.json`, so two can run at the same time |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body.
