# GOAL-005 WC-066 Evidence Sample And Sufficiency Assessment

**Date:** 2026-08-13
**Owner:** Product Owner selection required; Goal Orchestrator evidence assembly
**Source delivery:** WC-065 merged by PR #278 as `f28badc`
**Assessment:** INSUFFICIENT FOR DETAILED GROOMING
**Authority:** Evidence collection only; no WC-066 grooming, implementation, GOA, or Acceptance

## Purpose

Assess the WC-066 first-grooming trigger using evidence actually present after WC-065 delivery.
This record separates executable contract proof from real customer or active-employment evidence.
Synthetic fixtures are never represented as customer proof.

## Evidence Classification

| Class | Meaning | May satisfy real-sample trigger? |
|---|---|---|
| Delivered mechanism | Merged code, schema, contract, or enforcement behavior | No; proves capability only |
| Synthetic contract proof | Deterministic test fixture proving an outcome or failure path | No; supports later contract design only |
| Operational observation | Tenant-authorized record produced by actual use | Yes, subject to minimisation and Product selection |
| Customer proof | Authorized outcome, participation, disclosure, or response from actual employment | Yes, subject to consent, rights, and Product selection |

## WC-066 Trigger Matrix

| Required sample | Evidence found | Class | Gate status |
|---|---|---|---|
| Allowed offerability decision | `OfferabilityServiceTests.CurrentEvidenceAndNonNegativeDirectContributionAllows`; orchestration persists `ALLOW` with WBE version and CE evidence | Synthetic contract proof | PARTIAL |
| Calculated-risk decision | FA-047 disables calculated risk; test proves `ESCALATE` with `CALCULATED_RISK_DISABLED` | Synthetic contract proof; policy says no such allowed sample exists | POLICY-NOT-APPLICABLE pending Product confirmation |
| Revised decision | Negative contribution and stale owner tests produce `REVISE` semantics | Synthetic contract proof | PARTIAL |
| Escalated decision | Calculated-risk-disabled test produces `ESCALATE` | Synthetic contract proof | PARTIAL |
| Blocked decision | Floor/customer-protection and missing-owner orchestration tests produce `BLOCK` | Synthetic contract proof | PARTIAL |
| Version-pinned expected economic envelope used by an active relationship | Decision schema stores policy version, relationship state version, owner versions, direct contribution, evidence, and expiry | Delivered mechanism; no actual active-relationship row in repository evidence | MISSING REAL SAMPLE |
| Version-pinned resource envelope used by an active relationship | No WC-065 retained record or evidence artifact links resources/providers/goals to an active relationship | None | MISSING |
| Stale/unavailable behavior | Policy and orchestration tests fail closed; activation guard rejects expired or state-version-mismatched decisions | Synthetic contract proof | PARTIAL |
| Policy-expiry behavior | Decision expiry is persisted and enforced by activation guard | Delivered mechanism and synthetic proof; no observed expiry case | MISSING REAL SAMPLE |
| Customer-facing disclosure carried into employment | Founder workbench displays policy, evidence, expiry, disposition, contribution, and reasons | Synthetic UI proof; no customer acknowledgement or carried-employment record | MISSING REAL SAMPLE |
| Successful active-employment case | None | None | MISSING |
| Underperforming active-employment case | None | None | MISSING |
| Resource-constrained case | None | None | MISSING |
| Customer-non-participation case | None | None | MISSING |
| Provider-variance case | None | None | MISSING |
| Insufficient-evidence active-employment case | WC-065 owner-unavailable test exists, but no active-employment observation exists | Synthetic contract proof | MISSING REAL SAMPLE |

## Authoritative Evidence Available

1. `business.offerability_decisions` is append-only and tenant isolated. It retains decision,
   relationship/state version, policy version, owner versions, direct contribution, reasons,
   evidence reference, production time, and expiry.
2. FA-047 policy tests prove deterministic `ALLOW`, `REVISE`, `ESCALATE`, and `BLOCK` behavior.
3. Orchestration tests prove WBE ownership, CE evidence ordering, exact replay, changed-intent
   conflict, and fail-closed unavailable-owner behavior.
4. PostgreSQL integration tests prove RLS, append-only history, and concurrent idempotency.
5. Founder UI tests prove evidence/policy/expiry display and that the browser does not provide
   cost truth.

These are implementation and contract evidence. They are not real customer or employment proof.

## Collection Manifest Required To Satisfy The Gate

The Product Owner must select a minimised, tenant-authorized sample. Each row must retain source,
owner, observed-at/effective-at time, freshness, confidence or explicit unknown state, and evidence
reference. Raw customer content, credentials, prompts, and unnecessary identifiers are excluded.

| Sample cohort | Minimum evidence bundle | Owning source |
|---|---|---|
| Successful | WC-065 decision, accepted contract/envelope, active state version, observed customer outcome, resource/provider observations, current WBE projection | BP relationship; outcome owner; PR/AIR/provider; WBE |
| Underperforming | Same baseline plus observed goal variance and unresolved-causation alternatives | Outcome owner and BP projection |
| Resource constrained | Expected resource envelope plus actual/provisional usage and explicit insufficiency signal | PR/AIR/provider owner; WBE for economics |
| Customer non-participation | Required customer action, delivery/acknowledgement evidence, missing response window, and non-punitive uncertainty | BP relationship/channel owner |
| Provider variance | Expected provider envelope, owner-observed availability/quality/usage variance, and customer impact | AIR/provider owner; WBE for cost state |
| Insufficient evidence | Explicit missing/stale/conflicting owner states and resulting no-diagnosis outcome | Each missing owner; BP assembly |

For every selected case, record whether disclosure and evidence references were carried into the
employment bargain and whether the customer had notice, choice, review, or remedy where required.

## Gate Verdict

**BLOCKED FOR DETAILED GROOMING.** WC-065 delivered the mechanisms needed to create evidence, but
the repository does not contain the representative real decision-and-outcome sample required by
WC-066. Product selection has not occurred. Calculated-risk `ALLOW` is intentionally disabled by
FA-047 and must be marked not applicable or replaced by an approved equivalent by the Product and
policy owners; synthetic escalation is not a calculated-risk customer sample.

## Unblock Conditions

1. Product Owner selects the six representative real case classes above and records why the sample
   is representative, including missingness and selection bias.
2. Each case includes a real WC-065 decision and a version-pinned active-employment baseline.
3. Required owner observations are available with provenance/freshness, or explicitly unavailable.
4. Customer disclosures/evidence references carried into employment are demonstrated.
5. Product and policy owners resolve calculated-risk sample applicability under FA-047.
6. An independent reviewer verifies classification, minimisation, and the no-customer-proof claim.

Only after all six conditions close may WC-066 detailed grooming and its authorization journey
begin. This assessment grants no implementation authority.