# AE-01 Solution and Interface Contract

**Producing Institution:** INST-005 — Solution Architect
**Authorization:** GOA-GOAL-005-INST-005-02
**Status:** D-06 CONTRIBUTED — implementation-neutral
**Applies to:** WC-057 through WC-060

## Component Ownership

| Component | Owns | Must not own |
|---|---|---|
| Business Platform | Relationship, participant roles, context/configuration, contract, activation choreography, continuity checkpoints, customer Evidence Reader | LLM reasoning, professional execution, constitutional ledger writes |
| Professional Runtime | Evaluation/PAAS workflow, channel delivery/session state, relationship-scoped Stop fan-out | Relationship lifecycle truth, contract/payment state |
| AI Runtime | Local/provider inference selected by existing PSE/CTG | Trial entitlement or customer authority |
| Billing Engine | Trial allocation/quota/expiry and payment/subscription billing outcomes | Employment lifecycle or contract acceptance |
| Constitutional Engine/Audit Sink | Validation, immutable evidence, Stop evidence | Customer payload or BP relationship state |
| Web PWA | Presentation, Keycloak session, Tier-4 actions, generated API client | Business truth or hand-written API contracts |

DMA trial adapters belong to the DMA professional package and Skill Runtime configuration. Shared BP/PR code consumes generic `ProfessionalEvaluationAdapter` contracts; it contains no DMA skill branching. Future professionals supply their own adapter without changing AE-01 lifecycle code.

## Canonical API and Compatibility

The source is `architecture/reference/api-specs/business-platform.openapi.yaml`; TypeScript clients are generated per ADR-017.

Canonical endpoints:

- `POST /api/v1/employment/relationships` with `evaluation_intent_id`, participant, professional type; returns created or replayed relationship.
- `GET /api/v1/employment/relationships/{relationshipId}` and `/timeline`.
- `GET /api/v1/professionals?outcome=...`; `GET /api/v1/professionals/{type}/disclosure`.
- `POST /api/v1/employment/relationships/{id}/interview/messages`.
- `PUT /api/v1/employment/relationships/{id}/context/{field}` and `/context/confirm`.
- `POST /api/v1/employment/relationships/{id}/trial`; `GET .../trial`.
- `PUT /api/v1/employment/relationships/{id}/configuration`; `POST .../configuration/accept`.
- `POST /api/v1/employment/relationships/{id}/contracts`; `POST .../contracts/{version}/accept`.
- `POST /api/v1/employment/relationships/{id}/activation-intents`; `GET .../activation-intents/{id}`.
- `POST /api/v1/employment/relationships/{id}/handoffs`; `POST .../handoffs/{id}/activate`.
- `GET /api/v1/employment/relationships/{id}/evidence`; `GET .../evidence/export`.

Existing `POST /api/v1/employment/contracts`, `GET /api/v1/employment/contracts/{id}`, `POST /api/v1/agents/hire`, and `POST /api/agents/hire` remain compatibility adapters during AE-01. All call the canonical services. They emit `Deprecation: true` and a `Link` to the canonical endpoint; no duplicate business logic remains. Removal requires a later versioned contract and is outside AE-01.

## Evaluation Workflow

States: `DISCLOSING → INTERVIEWING → CONTEXT_ENRICHMENT → TRIAL_PLANNING → TRIAL_DEMONSTRATING → CONFIGURING → COMPLETE`, with `DECLINED`, `EXPIRED`, and `STOPPED` exits. Relationship lifecycle remains D-03; these are workflow states only.

Every interview response contains typed segments with server-assigned tags: `CUSTOMER_CONFIRMED_FACT`, `PUBLIC_EVIDENCE` (source URI/time), `INFERENCE` (confidence), `RECOMMENDATION` (basis), and `LIMITATION`. The LLM may propose tags, but deterministic validation verifies source presence, forbids customer-controlled tags, strips unsupported claims, and fails to a limitation response. Customer text is delimited as data, passed through existing injection/PII controls, and cannot alter system or professional policy.

## Professional Evaluation Adapter

```text
describe_suitability(outcome, confirmed_context) -> disclosure
answer_interview(question, evidence_context) -> typed_answer
plan_trial(days=14, applicable_skills) -> activities
demonstrate(skill_id, goal, context, trial_capabilities) -> simulated_artifact
propose_configuration(goals, measures, skills) -> configuration
```

The shared runtime enforces rights, trial limits, evidence, authority, and lifecycle. The DMA adapter maps its 19 skills to this interface and may use only trial-approved local/free/synthetic capabilities.

## Neutral Continuity Envelope

The canonical JSON/OpenAPI schema carries: `schema_version`, `tenant_id`, `relationship_id`, `participant_id`, `participant_role`, `authentication_assurance`, `authority_snapshot_id`, `source_channel`, `source_conversation_id`, `target_channel`, `target_conversation_id`, `command_purpose`, `correlation_id`, `causal_marker`, `sequence_number`, `idempotency_key`, `evidence_commitment_id`, `continuity_checkpoint_id`, and `issued_at`.

Tenant/relationship/participant/authority values are server-resolved and signed or integrity-protected; channel payload hints cannot override them. Source remains active until target authentication and checkpoint evidence commit. Same envelope/key/hash replays prior outcome; same key with different hash conflicts.

## Activation Choreography

1. BP validates exact accepted contract and creates/loads activation intent.
2. BP confirms WC-042 payment event is activation-eligible; it never treats payment alone as activation.
3. BP transitions relationship to `ACTIVATION_PENDING` with evidence.
4. BP invokes WBE paid activation idempotently using the activation intent correlation.
5. BP commits `ACTIVE` only after WBE success and constitutional evidence commitment.
6. WBE trial billing status may become `CONVERTED` only as the billing projection of the successful activation outcome. It is not a D-03 relationship state.
7. Uncertainty leaves the same intent retryable and pre-active; compensation never creates a second charge or relationship.

## Web PWA Contract

WC-057 completes, rather than replaces, WC-016. Required structure: `web/app/(public)`, `web/app/(authenticated)/relationships/[id]`, `web/components/constitutional/EmergencyStop`, `web/lib/api/generated`, and tests. Keycloak uses secure httpOnly session handling. UI meets WCAG 2.1 AA, zero critical axe violations, responsive 360px through desktop, TypeScript strict, Jest/Testing Library, Playwright, and ≥90% changed-line coverage. Emergency Stop remains fixed and one action away on authenticated screens.

## Failure Contract

Identity, CE/evidence, tenant, contract, or activation uncertainty halts progression. WBE/PR/channel unavailability returns explicit unresolved/degraded state without fabricating success. Retry reuses correlation and intent. No implementation edits generated `obj/`, `bin/`, generated clients, or copied proto files directly.