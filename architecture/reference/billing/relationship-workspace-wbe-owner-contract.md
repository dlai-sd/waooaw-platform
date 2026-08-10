# WC-034 F4 Relationship Workspace WBE Owner Contract

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-005-07 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T13:44:59+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-005-03 |
| `acceptance_record` | ACC-GOAL-005-INST-005-03 |
| Gate contribution | G-F4-08 — logical WAOOAW Billing Engine owner contract |
| Order 3 decision | ACCEPTED — G-F4-08 contribution evidence SATISFIED within INST-005 logical component-owner Decision Space; fresh INST-004 review remains required |
| Authority boundary | Logical WBE component and internal contract ownership only; no commercial-policy selection, canonical OpenAPI edit, generated client, source, test, migration, implementation, deployment, F5-F8, self-review, or integrated-review authority |

After `GOA-GOAL-005-INST-005-03` was issued and `ACC-GOAL-005-INST-005-03` was recorded at `2026-08-10T13:41:01+00:00`, INST-005 produced this logical WBE owner acceptance under Amendment 3 `GEP-GOAL-005-INST-013-04` and R-062 / `CR-GOAL-005-INST-002-05`. It relies on the published Order 1 records `CR-GOAL-005-INST-003-04` and `CR-GOAL-005-INST-011-05`, and the published Order 2 records `CR-GOAL-005-INST-004-08`, `CR-GOAL-005-INST-006-04`, and `CR-GOAL-005-INST-007-05`. Repository search found no Contribution Record identifier collision for `CR-GOAL-005-INST-005-07`.

## 1. Owner Acceptance

The logical WAOOAW Billing Engine owner accepts WBE as the sole authority for Relationship Workspace commercial truth. WBE accepts the internal operation and schema families proposed in `relationship-workspace-solution-contract.md` Section 5.1:

| Logical operation | Accepted contract |
|---|---|
| `getRelationshipCommercialProjection` | Returns authoritative `WbeRelationshipCommercialProjectionV1` for one service-authorized, tenant- and relationship-bound purpose |
| `submitRelationshipCommercialCommand` | Accepts typed `WbeCommercialCommandRequestV1` and returns `WbeCommercialCommandReceiptV1` |
| `getRelationshipCommercialCommand` | Reconciles one existing command as `WbeCommercialCommandOutcomeV1` |

These are logical internal contracts. This record creates no endpoint, changes no canonical OpenAPI, and authorizes no implementation.

## 2. Authoritative Commercial Projection

`WbeRelationshipCommercialProjectionV1` is the authoritative WBE-owned relationship commercial projection. It contains `schemaVersion`, `projectionVersion`, relationship binding, customer-language period and units, `producedAt`, source observation/confirmation time where applicable, `validUntil`, currency/freshness state, and the following distinct families:

| Family | Accepted authoritative meaning |
|---|---|
| Actual | Observed, posted commercial or allowance use for the named period in customer-understandable units; never a forecast, reservation, provider cost, or transport event |
| Allowance | Allocated, consumed, reserved where customer-relevant, remaining, renewal/reset meaning, and boundary consequence in the approved customer unit; allowance is not currency |
| Budget | The agreed financial boundary and authoritative current state for the relationship; a budget or ceiling does not grant work authority |
| Ceiling | The approved maximum financial exposure or spend boundary, its period, remaining headroom when authoritative, and the exact owner-approved consequence of approach or breach |
| Forecast | A bounded future range with horizon, production time, assumptions, uncertainty, validity, and accountable WBE model/version; never an actual charge or guaranteed outcome |
| Threshold | The WBE-owned state of a named allowance or financial boundary, observed value, threshold definition, time, validity, and owner-approved consequence |
| Assumption | A named input and bounded interpretation used by a forecast or consequence, including source, version, effective period, uncertainty, and invalidation condition |
| Validity | The source-owned time or condition through which each meaning may be treated as current; missing validity never means indefinite validity |
| Consequence | The typed commercial effect that WBE can authoritatively state, including whether commercial processing is completed, pending, blocked, unresolved, or unavailable; it does not invent BP lifecycle, authority, or work state |

Forecast, actual, allowance, budget, ceiling, threshold, assumption, validity, and consequence remain independently typed even when they share a unit or period. Zero is not unknown, stale, unavailable, or not yet observed. A stale or unsupported projection cannot authorize a consequential commercial command.

WBE supplies customer-understandable units and labels suitable for BP relay. It does not expose provider tokens, model units, procurement cost, platform margin, Thread Catalog internals, raw wallet/bucket rows, raw meter events, ledger coordinates, reconciliation controls, or operational telemetry through this projection.

## 3. Commercial Command Families

`WbeCommercialCommandRequestV1` is a generated-discriminated logical family, not a free-form action. It accepts only owner-approved variants:

- `CHANGE_BUDGET_CEILING` for a version-checked ceiling change within approved financial authority;
- `CHANGE_PACING` for a named owner-supplied pacing choice and stated commercial effect;
- `REQUEST_ALLOWANCE_ADDITION` for an approved allowance-addition or purchase path when Founder policy permits it; and
- typed lifecycle commercial-effect commands for pause, resume, renewal, or termination only when the complete commercial and re-entry policy is owner-approved.

Every request carries schema version, relationship and subject binding, command kind, purpose, expected projection and subject versions, approved customer acknowledgement where required, BP command correlation, and a WBE owner-scoped idempotency identity. It does not accept a browser token, public tenant authority, generic destination, provider identifier, raw price override, ledger mutation, or arbitrary consequence.

WBE validates only commercial authority and truth within its ownership. It does not grant constitutional authority, confirm scope, approve work, own BP relationship lifecycle, rank attention, or report professional execution completion.

## 4. Receipt And Outcome Semantics

`WbeCommercialCommandReceiptV1` returns an opaque WBE command/outcome identity, accepted command kind, relationship binding, status, accepted time, idempotency-replay meaning, projection version used, and reconciliation reference suitable only for BP.

`WbeCommercialCommandOutcomeV1` returns one of:

- `COMPLETED`: WBE's represented commercial mutation and required WBE evidence are authoritative;
- `PENDING`: WBE durably owns completion/reconciliation but the commercial effect is not final;
- `REJECTED`: commercial policy or state definitively denied the request and no represented success occurred;
- `CONFLICT`: expected WBE version or commercial subject changed and BP must obtain a fresh projection;
- `UNKNOWN`: WBE cannot yet prove commit or non-commit; no success or blind retry is allowed;
- `UNAVAILABLE`: the authoritative WBE capability or dependency cannot currently supply a safe outcome; and
- `BLOCKED`: an unresolved Founder policy, commercial authority, lifecycle, assurance, or owner prerequisite forbids execution.

The outcome includes prior and resulting projection versions where known, customer-language commercial effect, evidence/status references safe for BP mediation, unresolved step, reconciliation action, and completion or last-confirmation time. A transport response, reservation, accepted job, or ledger-write attempt is not automatically `COMPLETED`.

## 5. Service Authorization And Delegation

Only authenticated BP service identity may call the Relationship Workspace commercial contracts. WBE verifies service audience, delegated operation, purpose, actor reference where commercially required, server-derived tenant context, Employment Relationship binding, BP command identity, expected WBE versions, and authorization expiry independently of request possession.

Delegation is least-privilege and operation-specific. A BP credential valid for projection read does not imply command authority. A command delegation cannot be replayed for another tenant, relationship, subject, purpose, command kind, version, or time window. The browser, web runtime, PR, CE, professional/domain adapter, provider, and customer credential cannot invoke these contracts directly.

Tenant context is carried only by approved authenticated service context or transport metadata. A body field is correlation data at most and never independently establishes tenant authority.

## 6. Version, Freshness, Idempotency, And Reconciliation

Publicly relayed WBE schema families begin at semantic major version `1`. Every projection, receipt, and outcome declares `schemaVersion`; every commercial truth snapshot declares monotonic `projectionVersion`, `producedAt`, authoritative observation/confirmation time where applicable, `validUntil`, and currency/freshness state.

- additive optional meanings are minor-compatible only when they do not alter existing unit, ordering, status, validity, or consequence semantics;
- removing, renaming, retyping, or changing the meaning of actual, allowance, budget, ceiling, forecast, threshold, assumption, validity, or consequence requires a new major version and explicit coexistence/migration rules;
- BP must reject or isolate an unknown major version, mark the dependent public family unavailable/unknown, and block dependent commands; and
- a stale or expired projection remains historical context only and cannot silently authorize a command.

WBE binds idempotency to authenticated BP identity, tenant, relationship, command family, owner-scoped key, canonical request hash, and initial expected versions. The same binding and hash returns the original command and latest authoritative outcome. Key reuse with another hash returns conflict and performs no mutation.

After timeout or uncertain transport, BP queries `getRelationshipCommercialCommand` using the original command identity. WBE must establish committed, not committed, pending, or unknown before any new semantic mutation. Compensation, where an approved policy permits it, is a new versioned and evidenced command; prior commercial truth is not deleted or rewritten.

## 7. BP Relay And Ledger Sovereignty

BP may map an opaque WBE resource reference to a relationship-scoped public ID and relay the customer-language meaning with WBE provenance. BP must not:

- recalculate actual, allowance, remaining allowance, budget, ceiling, forecast, threshold, assumption, validity, pacing, price, or commercial consequence;
- derive customer units from provider tokens, model units, request counts, runtime measures, procurement cost, or technical telemetry;
- soften, rank, suppress, or reinterpret a WBE consequence as commercial truth;
- create a second wallet, allowance counter, commercial event store, reconciliation ledger, forecast, or billing ledger; or
- treat a cached browser or BP value as current after WBE validity expires or a material projection version changes.

WBE does not own BP's public relationship-governance state, public attention order, customer role/rights projection, constitutional authority, domain outcome attribution, or professional execution state. Composition preserves both ownerships.

## 8. Privacy And Minimisation

The WBE relationship projection includes only commercial meanings necessary for BP to serve the selected relationship purpose. It uses opaque relationship and command references and excludes customer content, prompts, deliverables, conversation data, professional reasoning, evidence payloads, identity-provider detail, contact data, provider secrets, platform procurement detail, raw ledger entries, and unrelated tenant or relationship facts.

Errors and outcomes are privacy-indistinguishable across inaccessible and non-existent commercial resources. They expose no customer enumeration, tenant identity, private URL, stack trace, ledger coordinate, bucket/wallet identifier, provider detail, platform margin, or internal reconciliation control. Correlation and reconciliation references are opaque, BP-only, purpose-bound, and time-limited where appropriate.

No WBE Relationship Workspace contract is browser-accessible. BP is the sole public mediator and returns only the minimised relationship projection and customer-safe effect.

## 9. Preserved Founder Commercial Policy Blocks

This owner acceptance does not resolve or infer any Founder policy in `F4-POL-01` through `F4-POL-06`. In particular:

- `F4-POL-03` remains blocked for threshold/ceiling treatment, pause/degrade/continue behavior, paid additions, purchase/increase eligibility, and customer consequence;
- `F4-POL-05` remains blocked for pause, resume, renewal, termination, billing/allowance treatment, scheduled-work effect, retained evidence, re-entry, and fresh-assurance policy; and
- `F4-POL-06` remains blocked for permissible customer action while a required projection or multi-owner outcome is stale, unknown, partial, unavailable, or unresolved.

Where another policy among `F4-POL-01`, `F4-POL-02`, or `F4-POL-04` affects a commercial command, acknowledgement, evidence export, or authority consequence, that command remains blocked as well. WBE may report authoritative actuals, thresholds, forecasts, assumptions, validity, and already-approved consequences, but it must not offer purchase/increase, invent degradation, finalize lifecycle commercial treatment, or choose customer rights without the routed Founder and accountable-owner decision.

## 10. Gate Decision And Exclusions

`CR-GOAL-005-INST-005-07` closes G-F4-08 contribution evidence only by recording the logical WBE owner's acceptance of `WbeRelationshipCommercialProjectionV1`, commercial command/receipt/outcome families, commercial semantics, service authorization, compatibility, freshness, idempotency, reconciliation, minimisation, and ledger sovereignty. Fresh INST-004 technical review remains required by Amendment 3 before independent package acceptance.

This record does not close G-F4-07, G-F4-09, G-F4-10, or G-F4-11 and does not authorize implementation G-F4-12 or deployment G-F4-13. It supplies no DMA evidence, canonical OpenAPI, generated client, source, test, migration, implementation, deployment, F5-F8, self-review, or integrated review.

## 11. Controlling Inputs

- `goals/GOAL-005-execution-plan.md` — Amendment 3 `GEP-GOAL-005-INST-013-04`, `GOA-GOAL-005-INST-005-03`, and `ACC-GOAL-005-INST-005-03`
- `reviews/R-062-wc034-f4-amendment3-ca-readiness.md` — R-062 / `CR-GOAL-005-INST-002-05`
- `goals/GOAL-005-f4-business-contribution.md` — Order 1 `CR-GOAL-005-INST-003-04`
- `architecture/reference/product/f4-relationship-workspace-release-contract.md` — Order 1 `CR-GOAL-005-INST-011-05` and unresolved `F4-POL-01` through `F4-POL-06`
- `architecture/reference/components/relationship-workspace.md` — Order 2 `CR-GOAL-005-INST-004-08`
- `architecture/reference/data/relationship-workspace-data-contract.md` — Order 2 `CR-GOAL-005-INST-006-04`
- `architecture/reference/security/relationship-workspace-security-contract.md` — Order 2 `CR-GOAL-005-INST-007-05`
- `architecture/reference/components/relationship-workspace-solution-contract.md` — Order 3 proposal and `CR-GOAL-005-INST-005-05`
- `architecture/reference/billing/wbe-component-spec.md` — existing WBE ownership boundary