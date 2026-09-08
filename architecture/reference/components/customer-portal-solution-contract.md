# WC-084 Customer Portal Solution Contract

**Office:** INST-005 Chief Solution Architect
**Work Contract:** WC-084
**Status:** COMPLETE - canonical solution/API closure only
**Canonical API:** `architecture/reference/api-specs/business-platform.openapi.yaml`
**Normative parents:** `work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md`, `architecture/reference/components/identity-boundary.md`, `architecture/reference/product/agent-employment-experience-contract.md`, `architecture/reference/product/f4-relationship-workspace-release-contract.md`, `architecture/reference/components/relationship-workspace-solution-contract.md`, `architecture/reference/components/relationship-workspace-bp-owner-contract.md`, `architecture/reference/billing/relationship-workspace-wbe-owner-contract.md`, `architecture/reference/data/relationship-workspace-data-contract.md`, `architecture/reference/security/relationship-workspace-security-contract.md`, `architecture/reference/components/conversation-core.md`, `architecture/reference/components/wc062-voice-solution-contract.md`

## 1. Decision Summary

This contract closes the WC-084 deferred Customer Portal rows without creating a new service boundary.
Business Platform remains the sole public facade. Conversation and voice remain the accepted WC-060
and WC-062 surfaces. Relationship Workspace remains the governing relationship-scoped read/command
surface. New WC-084 work is limited to additive public projections where portal-global or
portal-lifecycle semantics were not previously canonical.

The controlling terminology decision is:

`Onboard -> Induct -> Goal Verification -> Business Outcomes -> Operations`

- `Onboard` remains the lightweight, preference-oriented setup step and is the only configuration
  step that mutates portal presentation preferences directly.
- `Induct` is preserved exactly as WC-084 requires. It is not a new server lifecycle state and does
  not erase accepted onboarding or employment states. It is the universal customer-facing
  continuation surface that binds existing relationship truth, accepted disclosure/employment steps,
  and the existing conversation contract into one consultative induction experience.
- Goal verification, business outcomes, and Operations remain relationship-bound and evidence-bound.
  Operations never unlocks from browser inference.

## 2. Capability Closure

| Portal surface | Final disposition | Canonical BP surface |
|---|---|---|
| Session and sign-out | `REUSE + AMEND` | Reuse `GET /api/v1/identity/session`; no BP sign-out endpoint is introduced. Sign-out remains the Keycloak/NextAuth boundary from `identity-boundary.md`. |
| My Agents | `AMEND` | Add `GET /api/v1/employment/relationships` for tenant-derived relationship summaries and server-selected resume targets. |
| Conversation | `REUSE` | Reuse WC-060 conversation operations unchanged. |
| Voice | `REUSE` | Reuse WC-062 voice contribution operations unchanged. |
| Configuration: Onboard and Induct | `REUSE + CREATE` | Add relationship configuration read and Onboard preference mutation; Induct progression reuses relationship and conversation truth. |
| Goals | `REUSE + CREATE` | Add relationship goal read/history projection; goal mutations continue through existing typed workspace commands. |
| Business Outcomes | `CREATE` | Add a dedicated relationship business-outcomes read with explicit traceability and agent-performance separation. |
| Work and Operations eligibility | `REUSE + CREATE` | Reuse `GET /workspace/work`; add `GET /workspace/operations` for goal-gated eligibility and reassessment semantics. |
| Marketplace | `REUSE + CREATE` | Add paginated marketplace browse projection; reuse disclosure, trial, contract journey, onboarding order, and activation operations. |
| Alerts | `REUSE + CREATE` | Reuse relationship attention semantics; add a cross-relationship alerts feed with explicit read and acknowledge mutations. |
| Billing | `REUSE + CREATE` | Reuse billing statement, preference, and invoice operations; add a portal summary projection for allowance, forecast, payment state, and consequences. |
| Profile and settings | `REUSE + CREATE` | Add identity-owned profile, settings, and login-method summary reads/mutations; notification preferences remain reused. |

## 3. Cross-Cutting Rules

### 3.1 Authentication, assurance, and tenant derivation

- Public portal reads require the authenticated Keycloak customer session unless the existing
  operation is explicitly anonymous.
- `AAL2_ACCOUNT` is the default authenticated floor for portal reads.
- `AAL3_FRESH` is required only where the accepted identity or security contracts already require it,
  including login-method change, hiring, account linking, sensitive security action, or an owner
  declared consequential mutation.
- Tenant identity is always derived from the validated session/JWT and never from path, body, query,
  local storage, or adapter state.

### 3.2 Idempotency and conflict

- Every new mutation operation requires `Idempotency-Key` and binds it to actor, tenant, operation,
  canonical request hash, and the exact relationship or alert subject when applicable.
- Same key and same hash replays the prior outcome. Same key and different hash conflicts.
- Relationship-scoped mutations carry expected workspace or subject version and fail closed on
  authoritative version change.

### 3.3 Freshness, provenance, partial, and unavailable

- Every new relationship-scoped read inherits source provenance, freshness, correction lineage,
  partial projection, and unavailable semantics from the accepted Relationship Workspace data and
  security contracts.
- Portal-global reads explicitly distinguish `CURRENT`, `STALE`, `UNKNOWN`, `UNAVAILABLE`, and
  `BLOCKED` rather than collapsing them into empty success.
- Partial results are allowed only when still-authoritative families remain identified and the
  missing family is named explicitly.

### 3.4 Cache and channel security

- Authenticated HTML, RSC, API, conversation, voice, alerts, profile, billing, and relationship
  responses remain `no-store`.
- Protected portal truth is absent from service-worker caches and durable browser stores.
- Web, WhatsApp, and future mobile share BP-owned business semantics. Channels may change
  presentation and transport only.

## 4. Canonical BP Operations

### 4.1 Session, sign-out, profile, and settings

- `GET /api/v1/identity/session` remains the canonical authenticated session projection.
- No BP sign-out endpoint is introduced. Sign-out and account switch remain the accepted web and
  identity-boundary responsibility.
- `GET /api/v1/identity/profile`
- `PUT /api/v1/identity/profile`
- `GET /api/v1/identity/settings`
- `PUT /api/v1/identity/settings`
- `GET /api/v1/identity/login-methods`

`profile` owns customer display name, organization display, verified contact state, active role,
and switchable-account metadata. `settings` owns locale, theme, timestamp visibility, and channel
preferences. `login-methods` is a minimised summary only; it exposes neither provider subjects nor
secrets.

### 4.2 My Agents

- `GET /api/v1/employment/relationships`

The collection is tenant-derived, cursor-paginated, and server ordered. Each item returns the
relationship, professional identity, lifecycle, current goal summary or truthful absence, unread
state, availability, last authoritative confirmation, freshness state, and one server-selected
resume target.

### 4.3 Configuration, Goals, Business Outcomes, and Operations

- `GET /api/v1/employment/relationships/{relationshipId}/workspace/configuration`
- `PUT /api/v1/employment/relationships/{relationshipId}/workspace/configuration/onboard`
- `GET /api/v1/employment/relationships/{relationshipId}/workspace/goals`
- `GET /api/v1/employment/relationships/{relationshipId}/workspace/business-outcomes`
- `GET /api/v1/employment/relationships/{relationshipId}/workspace/operations`

`configuration` always returns exactly two items: `Onboard` and `Induct`. `Onboard` exposes only
accepted presentation and visibility preferences. `Induct` exposes consultative induction progress,
confirmed business context, correction lineage, and the conversation continuation target while
reusing the accepted relationship and conversation boundaries.

`goals` returns every active goal with declared skill, measure, review frequency, explicit customer
verification, version, amendment lineage, and history. Goal mutation remains on existing typed
workspace commands so the portal does not create a second command family.

`business-outcomes` returns every customer-facing outcome with a required trace to skill, goal,
measure, frequency, status, evidence state, agent-performance interpretation, external-outcome
interpretation, and attribution limits.

`operations` is the lock gate. It names the required goals, which goals are verified, why access is
locked or eligible, which work or results are affected by reassessment, and whether a material goal
change forced renewed verification.

### 4.4 Marketplace

- `GET /api/v1/professionals/marketplace`

This is the portal browse projection. It is cursor-paginated and filterable by type and free-text
query only. Suitability, offerability, trial availability, pricing source, and next authorized
action are server-projected facts. The portal reuses these existing operations unchanged for the
journey after browse:

- `GET /api/v1/professionals/{professionalType}/disclosure`
- `POST /api/v1/employment/relationships/{relationshipId}/trial`
- `GET /api/v1/employment/relationships/{relationshipId}/contract-journey`
- `POST /api/v1/employment/relationships/{relationshipId}/contracts/{version}/accept`
- `POST /api/v1/employment/relationships/{relationshipId}/contracts/{version}/payments/onboarding-order`
- `POST /api/v1/employment/relationships/{relationshipId}/activation`

### 4.5 Alerts

- `GET /api/v1/notifications/alerts`
- `POST /api/v1/notifications/alerts/{alertId}/read`
- `POST /api/v1/notifications/alerts/{alertId}/acknowledge`

The feed preserves server order and stable cursor lineage across relationships. `read` is not
approval. `acknowledge` is a feed-state mutation only and never substitutes for the underlying
relationship or commercial command.

### 4.6 Billing

- `GET /api/v1/billing/summary`

The portal summary is customer-global but remains a BP relay of WBE truth. It complements, not
replaces, these reused operations:

- `GET /api/v1/billing`
- `GET /api/v1/billing/preference`
- `PUT /api/v1/billing/preference`
- `GET /api/v1/billing/invoices`

## 5. Channel Mapping

| Surface | Web | WhatsApp | Future mobile |
|---|---|---|---|
| Session | Full session/profile/settings views | Uses the same session and role semantics behind channel-specific authentication; no Keycloak browser flow is implied | Full session/profile/settings views |
| My Agents | Relationship list + resume target | Relationship selection through channel continuation text or template actions using the same resume target semantics | Relationship list + resume target |
| Configuration | Onboard sheet/route + Induct conversation | Induct continues as conversation; Onboard preferences are reduced to supported channel controls | Full sheet/route composition |
| Goals and outcomes | Full goal and results routes/panels | Conversational summaries and explicit review/action links using the same BP semantics | Full routes/cards |
| Operations | Relationship work plus eligibility state | Same eligibility meaning before any consequential action | Full work/operations route |
| Marketplace | Browse/detail/trial/hire routes | Browse summaries and explicit continuation links; no divergent offerability logic | Browse/detail/trial/hire routes |
| Alerts | Global feed with read/ack | Ordered feed summaries and explicit action continuations | Global feed with read/ack |
| Billing | Billing summary + invoices | Summary and payment-state notifications only unless a later owner contract extends channel controls | Billing summary + invoices |

## 6. External Gates Remaining

No API ambiguity remains after this closure. Remaining external gates are only:

1. provider credentials and readiness evidence for Google, Facebook, and email where those slices
   are enabled;
2. authorized deployment and environment qualification for any runnable implementation; and
3. Founder substantive visual acceptance of the production portal experience.

## 7. Author Review

### Findings repaired

1. The terminology conflict was repaired by preserving `Induct` in the portal lifecycle while
   explicitly mapping it onto accepted relationship and conversation truth instead of inventing a
   new lifecycle service state.
2. The deferred portal rows now each have a concrete BP operation or an explicit reuse decision with
   no remaining unclassified AMEND/CREATE surface.
3. Outcome and Operations semantics now bind goal verification, evidence, and reassessment without
   browser-owned eligibility or success inference.
4. Billing, alerts, profile/settings, and marketplace now have concrete additive public surfaces so
   implementation is not forced to improvise cross-relationship or customer-global read models.

### Verdict

PASS for solution architecture scope. The contract is additive, channel-neutral, reuse-preserving,
and implementation-ready inside INST-005 authority. Remaining gates are external and not API-design
ambiguities.
