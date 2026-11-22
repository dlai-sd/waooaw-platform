# WC-147 - Cloud Workload Credential Issuance For Demo, UAT And Production

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-147 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-147 |
| Founder assignment | Current conversation: "one single PR for this ie founder working screen along with required platform changes for ceritificates which supports waooaw on any env ie demo, uat and prod"; "PR 615 is approved. keep working as per waooaw's engineering practices" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `2bf28148` |
| Related contracts | CB-021; ADR-046 Section 12 (Amendment 1); [workload-identity-cloud-issuance-contract.md](../architecture/reference/security/workload-identity-cloud-issuance-contract.md) (Sections 8 and 9 are the delivery interface and implementation record); WC-134; WC-144 |
| Requirement ledger | [WC-147-requirements.yaml](./WC-147-requirements.yaml) |
| Constitutional basis | C-023, C-059, C-063, C-083, C-084 |

## Problem And Evidence

Demo `/admin/pricing` cannot show live margin because Business Platform holds no workload credential, so it cannot sign the delegated envelope Billing requires (CB-021). The only credential is a hand-made Demo bundle that expires 2026-12-16T08:40:19Z. ADR-046 Section 12 was approved in PR #615 and designs cloud issuance for every environment: Key Vault custody, scheduled issuer jobs, 24-hour leaves renewed at 8 hours, in-process reload, and internal mutual-TLS listeners.

## Authority And Scope

### In scope

1. Terraform for every environment: Key Vault root and intermediate keys, secret slots, per-workload and per-job identities with least-privilege roles, the `ca-rotator` and `leaf-issuer` jobs, internal TCP listeners on Billing and Professional Runtime, and monitoring alerts.
2. The issuer library and job script, signing only with Key Vault keys in the cloud.
3. Billing, Professional Runtime and Business Platform read their bundle from Key Vault and swap it in process without a restart; verifiers check chain, validity, key usage and identity.
4. A service-link probe route and a non-gating owner-link state in Business Platform's health detail.
5. A deployment gate that runs both issuer jobs and requires Business Platform to report issued credentials and ready links.

### Out of scope

- Removing the interim Demo secrets, role assignments and import blocks (the plan policy rejects deletes; a follow-up PR removes them after the issuer is proven in Demo, by 2026-12-09).
- Wiring the legacy ops token to pricing routes (it stays withdrawn; ADR-046 12.1).
- New ADRs or claims; the proposed renewal claim stays a Founder decision.
- Provider and credential registry, payer model and tax invoice.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-147-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC147-R001 | Foundation and workload Terraform for demo, uat and prod create the CA keys, secret slots, job identities, issuer jobs, listeners and alerts with least-privilege roles, hold no key material, and validate |
| WC147-R002 | The issuer signs only with Key Vault keys, issues 24-hour leaves, renews at 8 hours, publishes delegation and trust material before the bundle that activates it, and prints the console lines the alerts parse |
| WC147-R003 | Billing, Professional Runtime and Business Platform reject credentials that fail chain, validity, usage, identity or lifetime checks, keep the last good credential, and reload a newer one without restart |
| WC147-R004 | Business Platform reports owner-link state without becoming unready, and a failed owner link fails closed for that owner only |
| WC147-R005 | The deployment gate fails the deployment unless both issuer jobs succeed and Business Platform reports Key Vault credentials and ready links to Billing and Professional Runtime |
| WC147-R006 | New tests run in the release-qualification gate; the ADR-046 contract and CB-021 record what was implemented and what is still unproven |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Demo evidence (issuer jobs, 24-hour expiry, renewal, ready links, Founder margin screen, outage simulation, cost) is recorded in CB-021 after the first Demo deployment.
