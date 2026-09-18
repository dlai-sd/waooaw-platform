# WC-NNN - Title

## Record Control

| Field | Value |
|---|---|
| Office | Authoring office |
| Status | DRAFT FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED |
| Implementing office | Named implementation office after current-session Founder authorization |

## Authority And Scope

State the exact authorized behavior, owning components, exclusions, and upstream approvals.

## Inputs

List every required approved specification, fixture, identity, service, secret, and environment authority.

## Canonical Requirement Index

Assign one stable `WCNNN-RNNN` ID to every normative implementation obligation. Before implementation,
create `work-contracts/WC-NNN-requirements.yaml` using schema
`waooaw.requirement-evidence-ledger/v1`, bind it to this file's complete SHA-256 digest, and validate it
with `scripts/validate_requirement_ledger.py` in the repository Docker test runner.
The Work Contract may not advance to `IMPLEMENTATION_AUTHORIZED`, and the implementing office may not
present its implementation plan or declare its first story `START`, until that validation passes.

## Definition Of Done

Define direct executable evidence, exact-head aggregate qualification, author review, and Founder handoff.

## Stop Conditions

Name every authority, safety, architecture, provider, quality, and scope condition that stops implementation.