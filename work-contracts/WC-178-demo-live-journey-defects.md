# WC-178 - Demo Live Journey Defects Found By Synthetic Customers

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-178 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-134 (Demo rollout recovery), continuing WC-176 |
| Founder assignment | Current conversation, 2026-11-28: "i suggest to creat new defect work contract for defect you are getting. i will supply my defects as well" |
| Status | OPEN. Defects are added as live runs find them; the Founder adds his own. Each defect is fixed in code and in Terraform or SQL, proved by an automated test, and read back live with a throwaway customer. |
| Baseline | `origin/main` at `110d9e69` (PR #663 WC-176 and PR #664 WC-177 forward fix merged; Demo deployed from it, run 46135059225) |
| Requirement ledger | [WC-178-requirements.yaml](./WC-178-requirements.yaml) |
| Constitutional basis | C-005, C-023, C-049, C-059, C-063, C-065 |
| Relationship to WC-176 | WC-176 built the journeys; this contract holds what stopped them working on the live Demo environment |
| Deployment | Founder-started; one Demo deployment per fix batch, then the live synthetic run |

## Why This Contract Exists

The first live run of the WC-176 journeys on Demo with throwaway customers (run `s1128354a`, 2026-11-28) showed that
registration, the Alerts inbox (the 403 is fixed), Settings, Billing and My Agents work, and that a Trial cannot start.
The Trial start crosses the Business Platform, the billing engine and its database, and each hop had never been used on
Demo: the first hop failed silently, so each fix revealed the next defect. This contract records each one with its cause
and proof so none is lost and none is fixed twice.

## Method

| Step | Evidence |
|---|---|
| Walk | `scripts/run_demo_customer_walk.sh` with `JOURNEY=register`, `probe`, `trial` against Demo, as a throwaway customer |
| Cause | Business Platform and billing-engine console logs in Log Analytics (`law-waooaw-demo-validation`), read by trace |
| Fix | A forward fix in the repository (Terraform or SQL or code) and a test; a hotfix on Demo only when it is the same change, so the walk can continue |
| Read-back | The same walk step returns the expected result |

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC178-R001 | [DEFECT, S] The Business Platform is given the billing engine's internal address (`BillingEngine__BaseUrl`). Without it the Business Platform called `http://billing-engine:8140`, a name that does not exist on Demo, so every call to the billing owner from the Business Platform (Trial start, Trial status, subscriptions) failed. Found live: Trial start 503. |
| WC178-R002 | [DEFECT, S] The web application is given the billing engine's internal address (`BILLING_ENGINE_URL`). Without it Hire checkout, its confirmation and its cancellation called `localhost:8140` from the web container. Found by reading the deployed web settings. |
| WC178-R003 | [DEFECT, S] The billing engine has a Trial free-unit allowance for `DIGITAL_MARKETING_LOCAL_SERVICE` (`TRIAL_FREE_UNITS`). Without an entry every Trial start answers 422 `TRIAL_CONFIG_MISSING`. The Trial grants only free local classification: no paid provider call and no spend. |
| WC178-R004 | [DEFECT, M] `business.trial_allocations.agent_type` holds any agent type code. It was `VARCHAR(20)` with a CHECK on the four legacy codes `DMA`, `DPA`, `DCA`, `DSA`, so the first Trial of `DIGITAL_MARKETING_LOCAL_SERVICE` (31 characters) failed with "value too long for type character varying(20)". Migration `99zzzzzzzz-wc176-03-trial-agent-type.sql` widens it to 64 and replaces the CHECK with a shape rule. Full-class by design (the update path refuses column type changes). |
| WC178-R005 | [DEFECT, M] The billing engine's application role can record a Trial. The insert into `business.trial_allocations` is refused by row-level security ("new row violates row-level security policy"), which migration 60 forces on business tables. The table needs a policy for the billing application role, proved against a real PostgreSQL as the non-owner role. |
| WC178-R006 | [DEFECT, S] A failed call from the Business Platform to the billing owner is logged with its status and reason. `StartWbeTrialAsync` returned null for every failure without a log line, so the customer saw "Acquisition continuation unavailable" and the cause took four log queries to find. The refusal status is now logged (never the body). |
| WC178-R007 | [PROCESS, S] Before a deployment, a check compares each service's required settings (addresses, allowances) with what Terraform renders, so a missing setting is found before the customer finds it. |
| WC178-R008 | [DEFECT, L, FOUNDER DECISION] The Trial is recorded for the right customer. `business.trial_allocations.customer_id` references `business.organisations(id)`, but the Business Platform sends the relationship's initiating participant id (`binding.CustomerId`), and Hire checkout sends the account reference. Neither is an organisation id, so the insert fails with `trial_allocations_customer_id_fkey` and no Trial can start. The billing engine's tests use SQLite without the foreign key, so they never saw it. Options: (A) the Business Platform looks up the organisation id of the tenant and sends that for Trial start, Trial status and Hire (recommended: wallets and trials are already keyed by organisation); (B) key the billing records by tenant id and change the foreign key. Both change what "customer" means for billing, so the Founder decides before it is built. |
| WC178-R009 | [DEFECT, ?] Founder-supplied defects are added here from R009 onward, each with its evidence. |

## Defect Register

| Id | Found | Where seen | Root cause | Fixed in | Live read-back |
|---|---|---|---|---|---|
| R001 | 2026-11-28 11:34 | Trial start 503 | No address for the billing engine in Business Platform settings | `workload-identity.tf` (this PR); hotfix on Demo revision `ca-demo-business-platform--0000175` | After R002 to R005 |
| R002 | 2026-11-28 11:35 | Deployed web settings | No `BILLING_ENGINE_URL` in web settings | `main.tf` (this PR); hotfix on Demo revision `ca-demo-web--0000131` | Hire checkout (needs a published package) |
| R003 | 2026-11-28 11:34 | Billing engine 422 | `TRIAL_FREE_UNITS` empty | `main.tf` (this PR); hotfix on Demo revision `ca-demo-billing-engine--0000131` | After R004, R005 |
| R004 | 2026-11-28 11:38 | Billing engine 500, `StringDataRightTruncationError` | Legacy `VARCHAR(20)` and CHECK | `99zzzzzzzz-wc176-03-trial-agent-type.sql` (this PR); applied once on Demo through the update job (D2 principal) | After R005 |
| R005 | 2026-11-28 11:42 | Billing engine 500, `InsufficientPrivilegeError` | Forced row security, no policy for the billing role on `trial_allocations` | `99zzzzzzzz-wc178-01-trial-allocations-billing-policy.sql`, update-class (this PR); applied once on Demo through the update job | After R008 |
| R006 | 2026-11-28 11:44 | Log reading | Silent null return | `RelationshipTrialService.cs` logs the refusal status (this PR) | Next deployment |
| R007 | 2026-11-28 | Pattern across R001 to R003 | No pre-deployment check of required settings | Open | Open |
| R008 | 2026-11-28 11:50 | Billing engine 500, `ForeignKeyViolationError` on `trial_allocations_customer_id_fkey` | The Business Platform sends a participant id where the table needs an organisation id | Open: Founder decision (options A and B in the requirement) | Open |

## Authority And Scope

In scope: Terraform settings for Demo and UAT, SQL init files, the billing engine and Business Platform code and tests, the
customer web server routes, and the live synthetic runs.

Out of scope: Production; real customers; changing Razorpay or WhatsApp accounts; any Founder decision recorded in WC-176.

## Definition Of Done

1. Every requirement has an automated test or a recorded check, and a live read-back with a throwaway customer.
2. The Trial journey runs from Register to the agent's workspace on Demo with no hotfix: a Founder-started deployment
   renders every fixed setting and the database migration is applied by the deployment, not by hand.
3. Hotfixes applied by hand to Demo are listed in the Defect Register and replaced by the deployment.
4. Every throwaway customer is deleted afterwards.
5. Author review is bound to the exact head commit; every PR goes to the Founder for review and merge.

## Stop Conditions

- A defect needs a Founder decision (Trial allowance for another agent, retention, pricing) or a Razorpay, Meta or Google account action.
- A fix would change a trust rule in identity, or row-level security for another table.
- A live step would send a WhatsApp message to a real person.

## Implementation Record

| Date | Item | Result |
|---|---|---|
| 2026-11-28 | Contract created | Six defects found in one live Trial attempt; R001 to R005 fixed in the repository and applied to Demo by hand so the walk could continue; R006 logging added; R008 (customer identity key) found next and needs a Founder decision |
