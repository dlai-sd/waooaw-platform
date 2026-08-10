# WC-034 F4 Relationship Workspace BP Owner Contract

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-005-06 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T13:44:58+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-005-03 |
| `acceptance_record` | ACC-GOAL-005-INST-005-03 |
| Gate contribution | G-F4-07 — logical Business Platform owner contract |
| Order 3 decision | ACCEPTED — G-F4-07 contribution evidence SATISFIED within INST-005 logical component-owner Decision Space; fresh INST-004 review remains required |
| Authority boundary | Logical BP component and future contract ownership only; no DMA evidence, canonical OpenAPI edit, generated client, source, test, migration, implementation, deployment, F5-F8, self-review, or integrated-review authority |

After `GOA-GOAL-005-INST-005-03` was issued and `ACC-GOAL-005-INST-005-03` was recorded at `2026-08-10T13:41:01+00:00`, INST-005 produced this logical BP owner acceptance under Amendment 3 `GEP-GOAL-005-INST-013-04` and R-062 / `CR-GOAL-005-INST-002-05`. It relies on the published Order 1 records `CR-GOAL-005-INST-003-04` and `CR-GOAL-005-INST-011-05`, and the published Order 2 records `CR-GOAL-005-INST-004-08`, `CR-GOAL-005-INST-006-04`, and `CR-GOAL-005-INST-007-05`. Repository search found no Contribution Record identifier collision for `CR-GOAL-005-INST-005-06`.

## 1. Owner Acceptance

The logical Business Platform owner accepts BP as the sole ordinary public Relationship Workspace facade and the authoritative relationship-governance projection owner. BP accepts the public operation families, paths, and schema semantics proposed in `relationship-workspace-solution-contract.md` Sections 2-4, including aggregate and incremental workspace reads; Plan, attention, Work, Results, Usage & budget, and Rights & control reads; typed relationship commands and command reconciliation; and BP-mediated evidence reads and exports.

This acceptance creates no endpoint and changes no canonical specification. The proposed contracts remain normative architecture input to a future BP-owner OpenAPI task under separate authorization.

## 2. Public Governance Projection

BP accepts responsibility to:

1. compose one authorized relationship-bound projection from BP-owned governance truth and validated WBE, PR, CE/evidence, and professional/domain contributions without transferring source ownership;
2. own public Plan, goal, work, deliverable, approval, schedule, scope, authority, lifecycle, rights, Results-composition, evidence-reader, command, and reconciliation meanings;
3. qualify every **Needs your attention** item and return the complete authoritative order with stable tie sequence across snapshot, pagination, refresh, reconnect, and device;
4. expose no score, rank, secondary sort, reorder, personalization, or browser-owned qualification surface;
5. preserve current, stale, unknown, unavailable, blocked, pending, partial, disputed, and superseded meanings without local inference or fabricated success; and
6. keep capability distinct from authority, Plan from approval, completed work from result, forecast from actual, and pending evidence from recorded evidence.

The public array order is authoritative. Web presents it exactly and does not filter into authority, rank, or secondarily sort it.

## 3. Authorization And Isolation

Every read, cursor, item, command, command outcome, evidence view/export, and reconciliation operation is authorized before protected existence or state is disclosed. BP binds access to the authenticated actor, server-derived tenant, effective role, one selected Employment Relationship, current lifecycle, scope, authority, assurance, and relevant source versions.

`tenantId` is not accepted from a public path, query, request body, or browser-supplied authority header. Possession of a relationship ID, item ID, cursor, command ID, export ID, link, acknowledgement, or idempotency key grants no access. Missing, cross-tenant, wrong-role, and inaccessible relationship outcomes use the privacy-indistinguishable `RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE` contract.

Relationship switching requires a fresh authorized aggregate read. No prior relationship draft, cursor, selected item, attention order, authority, budget, evidence, command availability, or reconciliation state carries into the new context.

## 4. Command And Reconciliation Ownership

BP accepts the typed command families and discriminated request semantics in the solution contract. It will not expose a generic action name, arbitrary service destination, or free-form routing payload.

For every consequential command, BP owns:

- actor, tenant, relationship, role, purpose, subject, expected-version, authority, scope, lifecycle, assurance, acknowledgement, and owner-projection validation;
- idempotency binding across actor, tenant, relationship, operation family, key, canonical request hash, and initial expected versions;
- derived owner-scoped idempotency identities and one stable CE `action_instance_id` where constitutional evidence transitions apply;
- durable command identity and `COMPLETED`, `PENDING`, `PARTIAL`, `UNKNOWN`, `REJECTED`, `CONFLICT`, or `BLOCKED` public outcome;
- owner-by-owner outcome steps, committed and unresolved owner disclosure, incompatible-command freezing, and accountable reconciliation; and
- reconciliation before retry whenever an owner may have committed, with no blind duplicate or invented rollback.

HTTP or transport acceptance is not business success. `COMPLETED` is returned only when all owners required for the represented effect and every required Evidence First confirmation are authoritative. `PARTIAL` identifies each committed and unresolved owner. `UNKNOWN` withholds success, reconciles the existing command ID, and prohibits a second semantic mutation until commit status is known or the owner proves no commit.

## 5. Constitutional Evidence Mediation

BP accepts CE as the constitutional validation, authority-licensing, and constitutional-evidence authority. BP uses only approved internal CE gRPC contracts and creates no public or REST CE surface.

No public response states approved, scope-boundary confirmed, authority changed, lifecycle consequence completed, or evidence recorded before the required CE confirmation. Scope-boundary confirmation remains a distinct command and evidence action, not ordinary approval. CE unavailability fails closed for governed writes while unaffected reads retain accurate constitutional and evidence currency. Emergency Stop remains on its dedicated independent path and is not routed through a workspace command or delayed by workspace-owner availability.

## 6. Internal Owner Consumption

BP accepts the internal contracts proposed in the solution contract:

- WBE supplies `WbeRelationshipCommercialProjectionV1` and commercial command outcomes; BP relays them without recalculation or a second ledger;
- PR supplies `PrRelationshipExecutionProjectionV1` and approved internal control outcomes; PR facts do not become public governance truth until BP validates and incorporates them;
- professional/domain owners supply versioned `RelationshipOutcomeAdapterV1` contributions; BP validates binding, provenance, supported version, evidence-reference form, and completeness, then alone owns public incorporation and attention order; and
- CE supplies constitutional validation, evidence confirmation, and authority-license outcomes through existing gRPC contracts.

All owner calls are service-authenticated, purpose-delegated, tenant- and relationship-bound, versioned, privacy-minimised, and inaccessible from the browser. An absent or unsupported owner contract makes the affected public family `UNAVAILABLE` or `BLOCKED`; BP does not compensate with another source, a browser cache, technical telemetry, or mock success.

## 7. Errors And Privacy

BP accepts RFC 9457 `RelationshipWorkspaceProblemDetailV1` and the stable error codes in the solution contract. Public errors disclose only safe customer meaning, correlation, and BP-owned recovery or reconciliation links. They do not expose tenant identifiers, private service names or URLs, stack traces, internal IDs, ledger coordinates, acknowledgement text, evidence payload, provider detail, WBE internals, PR traces, or non-public CE rationale.

Public projections and exports are purpose-limited and relationship-minimised. Browser caches, service workers, durable storage, URLs, analytics, telemetry, history, sign-out, and relationship/account switching must not retain protected governance, evidence, commercial, assurance, or command truth beyond the approved customer purpose.

The browser must not directly access PR, WBE, CE, a professional/domain adapter, a provider, the Constitutional Audit Ledger, the Customer Evidence Ledger, or a billing ledger. The only F4 browser contract is the future generated BP public client; Emergency Stop remains separately governed.

## 8. Future Canonical OpenAPI Owner Task

Under a later explicit authorization, the logical BP owner must incorporate the accepted public operation families into `business-platform.openapi.yaml` as a backward-compatible version selected from the current `1.2.0`. That task must define dependency-closed schemas, discriminated command unions, security, idempotency headers, expected versions, all response/error components, and BP-only reconciliation links.

The later contract must then undergo parse, local-reference, operation-ID, pinned-generator, deterministic two-run generation, strict TypeScript, and forbidden-surface validation before G-F4-10 can be considered. This record performs none of that work and does not authorize a canonical OpenAPI edit, generated production client, manual client patch, code, test, migration, build, implementation, or deployment.

## 9. Gate Decision And Exclusions

`CR-GOAL-005-INST-005-06` closes G-F4-07 contribution evidence only by recording the logical BP owner's acceptance of the solution proposal and ownership obligations. Fresh INST-004 technical review remains required by Amendment 3 before independent package acceptance. G-F4-08, G-F4-09, G-F4-10, G-F4-11, implementation G-F4-12, and deployment G-F4-13 are not closed by this record.

This record supplies no DMA domain evidence, canonical OpenAPI, generated client, source, test, migration, implementation, deployment, F5-F8, self-review, or integrated review.

## 10. Controlling Inputs

- `goals/GOAL-005-execution-plan.md` — Amendment 3 `GEP-GOAL-005-INST-013-04`, `GOA-GOAL-005-INST-005-03`, and `ACC-GOAL-005-INST-005-03`
- `reviews/R-062-wc034-f4-amendment3-ca-readiness.md` — R-062 / `CR-GOAL-005-INST-002-05`
- `goals/GOAL-005-f4-business-contribution.md` — Order 1 `CR-GOAL-005-INST-003-04`
- `architecture/reference/product/f4-relationship-workspace-release-contract.md` — Order 1 `CR-GOAL-005-INST-011-05`
- `architecture/reference/components/relationship-workspace.md` — Order 2 `CR-GOAL-005-INST-004-08`
- `architecture/reference/data/relationship-workspace-data-contract.md` — Order 2 `CR-GOAL-005-INST-006-04`
- `architecture/reference/security/relationship-workspace-security-contract.md` — Order 2 `CR-GOAL-005-INST-007-05`
- `architecture/reference/components/relationship-workspace-solution-contract.md` — Order 3 solution proposal and `CR-GOAL-005-INST-005-05`