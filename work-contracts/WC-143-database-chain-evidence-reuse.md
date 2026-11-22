# WC-143 - Reuse Of An Unchanged WC-124 Database Authority Chain

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-143 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-143 |
| Founder assignment | Current conversation: "proceed as per your plan of 3 prs"; implementation authorized for WC-145, then WC-143, then WC-144 |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `cf7c1f72`; Demo deployment run 44929414330 (45 min 50 s, Apply 35 min 41 s) |
| Related contracts | WC-124 (database authority chain, preserved), WC-142 (deploy-time phase 1) |
| Requirement ledger | [WC-143-requirements.yaml](./WC-143-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Problem And Evidence

Every Demo or UAT deployment re-runs the full WC-124 chain even when nothing it governs has changed: open authority and grant (108 s), quiesce (74 s), provisioner create, run and delete (162 s), handoff (87 s) and Entra bootstrap removal (46 s), together about 477 s in run 44929414330. The steady state is `REVOKED` (password authentication enabled, no bootstrap administrator, no provisioner Key Vault role). The provisioner reuses existing credentials and skips init files whose digest is already in `wc124_provisioning.init_chain_ledger`, so on unchanged inputs the whole chain reproduces the previous result.

There is no existing skip rule: `reset_demo_database` is the only related input, and `scripts/wc124_database_transition.py` always requires the full chain in `REVOKED`.

## Authority And Scope

### In scope

1. After a deployment completes successfully on the full chain, the workflow stores a sealed record (provisioner result, provisioner execution, input fingerprint, live facts) as a blob next to the foundation cache.
2. A later deployment reuses that evidence, and skips the authority chain, only when every binding in WC143-R002 still holds.
3. Evidence consumers keep their strict validation; reused evidence is labelled as reused.

### Out of scope

- Any change to the provisioner, handoff, transition resolver or Terraform.
- Skipping vendor migrations, Temporal qualification, WhatsApp activation or application activation (separate levers).
- Running the chain verification through a different identity.

## Design Decisions (Founder may override)

| Decision | Choice | Reason |
|---|---|---|
| Maximum record age | 7 days (`MAX_RECORD_AGE`) | Bounds how long an undetected out-of-band database change can persist; the chain rotates nothing, so age is not about credential freshness |
| Workflow YAML in fingerprint | Excluded | Including it would invalidate the record on every workflow edit; the fingerprint covers the files the chain executes plus the foundation fingerprint |
| First deployment after merge | Full chain, writes the record | Reuse is first exercised on the second deployment |
| Record tamper resistance | sha256 seal only, not keyed | Integrity against accident; live facts and the terminal live authority checks are the drift control |
| Record write failure | Never fails the deployment | A missing record only costs the next deployment its reuse |

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-143-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC143-R001 | A record is written only by a Demo or UAT deployment that ran the full chain and whose job otherwise succeeded, after the last deployment-identity step; the write is best-effort and cannot fail the job |
| WC143-R002 | The chain is skipped only when the record is intact, the input fingerprint and the live server and credential facts match, the transition state is `REVOKED`, no database reset is requested, the record is no older than 7 days, the recorded result is a full non-reset provisioning bound to one succeeded execution, and the recorded Demo spend authority equals the current Founder policy |
| WC143-R003 | Any missing, unreadable, mismatched or erroring input selects the full chain; the decision step never ignores its own failure |
| WC143-R004 | On reuse the authority, quiesce and provisioner steps do not run, and the provisioner result, execution and authority evidence are restored from the record, labelled as reused, and still pass the unchanged pre-activation evidence validator |
| WC143-R005 | The pre-activation evidence records `identity_reused` and the record digest, and rejects a reuse record bound to a different execution |
| WC143-R006 | The terminal live checks (no Secrets Officer assignment, no bootstrap administrator) and the credential handoff verification run on every deployment, reused or not |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. The expected saving is about 8 minutes on a reused Demo deployment (the chain total above, less the credential verification that still runs) and is measured by the second deployment after merge; it is not claimed here. It does not reach the 30-minute target alone.
