# CB-014 - WC-115 Command Owner Dispatch Contract

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-014` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-08` |
| Status | **RESOLVED** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-115 Stages WC115-02, WC115-03, WC115-05 through WC115-07; WC115-R007-R010, R017-R018, R029-R038, R044, R057, R062, R067, R072 and R074 |
| Constitutional basis | C-023, C-026, C-059, C-065, C-079; WC-115 Sections 2.2, 3, 5, 6, 8, 13 and 14 |
| Resolution authority | Chief Solution Architect repair of the WC-114/WC-115 controlling package followed by Founder acceptance |

## Blocking Facts

The WC-115 author review found that the implementation cannot complete the required cross-owner
command path without inventing authority and transport semantics.

The accepted candidate defines nine BP command variants and names reusable PR, CE, WBE and domain
adapter operations. It does not define:

1. the required owner-step set and order for each command variant;
2. which command variants require PR execution, WBE mutation, adapter validation or read-only owner
   projection;
3. how a BP employment command maps to PR's mandatory `conversationId`, `messageId` and complete
   `OperationalMandateV1` required by `startConversationExecution`;
4. how command-specific expected plan, Decision Space and WBE versions bind to each owner request;
5. the terminal and ambiguous response mapping from each reused owner operation into the closed
   `EmploymentCommandOutcomeV1` owner-step vocabulary; or
6. which owner calls are prohibited for each command, which is necessary to prove zero calls after
   validation, version or idempotency failure.

The current implementation guessed that every accepted command has CE, PR, WBE and domain-adapter
steps. That guess is not supported by the controlling package and would transfer or invoke owner
authority unnecessarily. The author review stopped this path before wiring it to production clients.

The existing PR `startConversationExecution` contract is not a generic employment-command envelope.
Its mandatory operational mandate contains identities and authorization references that are absent
from every candidate employment command. Constructing placeholders, deriving unrelated values or
adding a new private endpoint would violate the no-invention and no-new-interface rules.

## Gate Effect

- WC115-02 cannot prove real PR coordination, durable external intent or AIR/adapter dispatch.
- WC115-03 cannot claim complete BP command composition or durable responsibility.
- WC115-05 cannot execute the required cross-owner success, partial, unknown, outage and
  reconciliation journeys.
- CEW-FIT-04, CEW-FIT-06, CEW-FIT-11, CEW-FIT-13 and CEW-FIT-14 cannot receive truthful runtime
  evidence.
- Acceptance scenarios 1-5 and 8-10 cannot be completed without guessed owner calls.
- Final qualification, requirement-ledger PASS, exact-head author-review PASS and PR creation are
  blocked.
- The default-off gate remains disabled. No deployment, activation, customer traffic or DMA-specific
  production change is authorized or required.

## Required Resolution

1. Publish a closed command-to-owner execution matrix for all nine command variants.
2. For every required owner step, specify the reused operation, canonical request mapping, stable
   idempotency identity, expected-version bindings, evidence transition, timeout behavior,
   reconciliation operation and terminal mapping.
3. Explicitly identify commands for which PR, WBE or adapter calls are prohibited.
4. Supply the authoritative mapping from employment relationship/contribution/command identities to
   the existing PR conversation execution mandate, or publish an approved superseding candidate
   interface if the existing operation cannot represent the required semantics.
5. Bind the repaired package to an immutable digest and obtain Founder acceptance before WC-115
   implementation resumes on the affected stages.

The Platform IT Expert may continue only work independent of this dispatch contract. It may not
invent the matrix, populate mandatory owner identities with placeholders, collapse unknown outcomes,
remove owner steps to make tests pass, or represent in-memory simulation as production composition.

## Resolution

Acting on the Founder's explicit authorization, the Chief Solution Architect published solution
contract `1.0.0-candidate.3`. The repair:

- separates Conversation Core contribution execution from the nine BP employment commands;
- prohibits PR calls for all nine commands rather than synthesizing mandatory PR mandate identities;
- fixes the exact adapter and WBE read validations for each command;
- fixes domain adapter, WBE, CE and BP ordering, deterministic owner keys, evidence identity,
  timeout/reconciliation behavior and prohibited calls; and
- leaves all five wire contracts and the specialist profile unchanged at
  `1.0.0-candidate.2`.

The Founder authorized this architecture repair and directed WC-115 implementation to resume. The
Platform IT Expert may implement only the closed matrix above; activation, deployment, customer
traffic and DMA-specific production changes remain prohibited.
