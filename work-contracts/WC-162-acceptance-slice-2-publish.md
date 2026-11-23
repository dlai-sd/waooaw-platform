# WC-162 - Customer Journey Acceptance Slice 2: Publish

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-162 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-162 |
| Founder assignment | Current conversation, 2026-11-23: "pr is approved ... proceed to next slice" after merge of PR #627 (WC-158 to WC-160) |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `dec839e50ca142ebd11a0e4491f39fc2e318cf43` |
| Branch | `ib/162/acceptance-slice-2-publish` |
| Decisions | ADR-054, ADR-055 (accepted) |
| Controlling specification | `architecture/reference/acceptance/customer-journey-acceptance-architecture.md` sections 6 (slice 2), 7, 8, 12 |
| Requirement ledger | [WC-162-requirements.yaml](./WC-162-requirements.yaml) |
| Depends on | WC-158, WC-159, WC-160 (merged in PR #627) |
| Constitutional basis | C-023, C-049, C-059, C-063, C-065, C-071, C-080 |

## Authority And Scope

### In scope

1. The journey plan `validation/acceptance/plans/slice-2-publish.v1.yaml` with steps S9 (publish an approved post) and S9b (a refused post publishes nothing), added to the demo profile and the workflow's journey options.
2. Specs for both steps and the Graph readers they need: read a post by id, list the Page feed, delete the run's own post.
3. The secret name `acceptance-meta-test-page-token` in the profile, the foundation Terraform secret lists, the runbook and the secret register.
4. Multi-plan static gates: step identifiers are unique across plans, each plan's steps need specs, a spec citing a step in no plan fails, and the ratchet is computed over all plans.
5. Specs of steps outside the selected journey skip themselves.
6. `WC149-R009` and `AE-02-S05` move from deferred and uncovered to covered in the live scope and the ratchet baseline (the ratchet may rise).

### Out of scope and prohibited

- Running anything against Demo or Meta; entering or reading any secret; creating Azure, Keycloak or provider resources.
- Conversation stories (`AE-02-S02`, `AE-02-S03`), which stay `BLOCKED-BY-FLAG` behind `WC120_CONVERSATION_ENABLED`; lifecycle rights (PG-26); WhatsApp.
- Any product change: the Publish post form and its same-origin route already exist (WC-149).
- Reading the Business Platform bearer token or any `customer-connection-` secret.

## Inputs

| Input | Status |
|---|---|
| PR #627 merged (harness, synthetic tenants, slice 1) | Present on `main` |
| WC-149 publish form and route (`POST /api/provider-connections/{id}/publish`, 2000 character limit) | Present on `main` |
| Founder authorization of implementation code in this session | Present (current conversation) |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC162-R001 | The slice 2 plan passes the plan gates (schema, witness discipline, existing identifiers) and every step has a spec citing only identifiers the step proves |
| WC162-R002 | Step identifiers are unique across plans, a spec citing a step in no plan fails, and the coverage ratchet is computed over all plans |
| WC162-R003 | The ratchet baseline and live scope record `WC149-R009` and `AE-02-S05` as covered and drop the `WC149-R009` deferral, and the gate still refuses a lowered floor or a new deferral |
| WC162-R004 | A post is read from Graph by id with the test Page token, a missing post reads as undefined, a malformed id is refused, and the Page feed is listed in a stable order |
| WC162-R005 | The run deletes the one post it published whatever the verdict, and reports a leftover instead of throwing |
| WC162-R006 | S9 requires screen, platform and Graph to agree on exactly one post with exactly the approved text, and the connection staying CONNECTED with no token in any response |
| WC162-R007 | S9b requires the empty and over-limit posts to be refused by screen and platform and the Page feed to be unchanged on Graph |
| WC162-R008 | Specs of steps outside the selected journey skip, and a missing Meta credential or Page token yields `BLOCKED-BY-FLAG` with its reason |
| WC162-R009 | The new secret name is in the demo profile, in the demo and uat foundation secret lists (equal to the profile list) and in the runbook |

## Definition Of Done

1. Every requirement has direct executable evidence run in Docker at the exact head.
2. `playwright test --list` enumerates S9 and S9b; a local run of the slice 2 plan against a non-product stand-in produces a schema-valid report with both steps `BLOCKED-BY-FLAG`.
3. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for the exact head; Founder reviews and merges.
4. No Demo, Meta or live-provider result is claimed.

## Stop Conditions

- Any need to change a decision in ADR-054 or ADR-055, or the product publish path.
- Any need to hold the Page token in GitHub or print it.
- A cited identifier that does not exist.

## Implementation Record

Evidence at the exact head is in the PR body.

- **Page token.** Reading and deleting a post on Graph needs a token for the test Page, which the harness never obtains from the product. The Founder enters it as `acceptance-meta-test-page-token` (runbook). Without it S9 and S9b are `BLOCKED-BY-FLAG`, not failures.
- **Setup is not a claim.** Slice 2 signs in and connects the test Page itself because slice 1 ends by revoking the connection; a failed setup is reported on the step that needed it.
- **Locators are unproven on Demo.** They come from the `PublishForm` source (labels "Post message", "I approve this exact post", "Publish post"); the first run is the calibration run.
- **Not run:** any Demo or Meta call.
