# R-054 — WC-034 F2 Security Architecture Consultation

| Field | Value |
|---|---|
| `institution_id` | INST-007 |
| `work_contract` | WC-034 / IB-014 / F2 |
| `record_type` | Security Consultation Record |
| `produced_at` | 2026-08-09 |
| `scope` | Identity, authentication, authorization, threat model, assurance, linking, tenant isolation, retry, and privacy-safe errors |
| Decision | **CONCUR WITH BLOCKERS** |

INST-007 independently reviewed the F2 decision surface against ADR-008, ADR-023, the AE-01 security contract, the D-03 identity model, the hybrid shell and acceptance contracts, the canonical Business Platform OpenAPI, and the Founder decision requiring verified email and mobile identity.

## Concurrence

INST-007 concurs that the F2 contract may make the following controls normative:

- Keycloak remains the sole web credential authority; provider integration is brokered and application services never verify credentials.
- ADR-023 remains the authority for WhatsApp identity; its internal session cannot self-upgrade into a portal session.
- Complete registration requires mandatory verified email and verified mobile and remains separate from Employment Relationship creation.
- Existing-account linking requires fresh portal assurance, explicit approval, a 15-minute single-use challenge, and fresh Meta validation.
- Duplicate detection is proof-gated, deterministic, and non-enumerating; unsafe split-account matches never auto-merge.
- Tenant identity is server-derived, mutations are idempotent, uncertain outcomes remain unresolved, and identity errors disclose no account existence or identity value.
- High-risk actions require fresh or stronger assurance without losing authorized context; refresh alone does not satisfy freshness.
- Next.js owns presentation and server-session handling only; BP is the sole public REST facade and consumes the logical Identity Boundary.

These controls are incorporated in `architecture/reference/components/identity-boundary.md` and the F2 operations in `architecture/reference/api-specs/business-platform.openapi.yaml`.

## Blocking Conditions

| ID | Condition | Owner | Missing artifact |
|---|---|---|---|
| `R054-01` | ADR-008 v2 defers Meta/Facebook while later Founder-approved F2 records and FA-018 require it | INST-004, with Founder decision if policy changes | ADR-008 corrigendum or amendment fixing Meta login disposition and separation from DMA Business OAuth |
| `R054-02` | Independent architecture approval is not yet recorded | INST-004 | Independent review of the complete F2 package |
| `R054-03` | Meta environment activation is not ready | Founder | FA-002 Meta Business Manager verification and FA-018 login app credentials/configuration evidence |

The F2 contract addresses the consultation's API, anti-enumeration, link-proof, assurance, tenant, retry, and privacy requirements. `R054-01` is not within INST-005 or INST-007 authority to resolve silently.

## Boundary

This consultation does not authorize implementation, resolve the Meta contradiction, approve the Solution Architect's package, authorize deployment, or extend WC-034 into F3–F8. Independent INST-004 review remains mandatory.