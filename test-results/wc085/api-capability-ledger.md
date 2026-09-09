# WC-085 API Capability Disposition

Status: BLOCKED for full WC-085 closure. Code freeze: `14a28c18aa8774d8b2f956c475e2e60a245f4ddd`.
No OpenAPI, generated client, `src/` service, billing calculation, or Identity mutation operation was added.

| Capability | Owner / Existing Boundary | This Candidate | Remaining Approval / Evidence |
|---|---|---|---|
| Auth provider projection | BP `GET /api/v1/identity/providers` | Optional private verifier checks GOOGLE AVAILABLE; public deployment verifier does not bypass API IP restrictions | Live manifest/realm/endpoint/UI parity and fail-closed outage qualification |
| Google broker | Identity, Keycloak OIDC authorization endpoint | Terraform realm/provider/client/default roles recreated from Key Vault environment references; public PKCE redirect verified | Real registration, subject mapping, return, repeat, denial, failure and rollback |
| Customer profile/settings/login methods | Accepted BP surfaces named in WC-085 Section 14 | Existing code retained | Three new Identity operations await Identity/Security/INST-005 acceptance |
| Marketplace browse/detail/trial/hire | BP operations named in WC-085 Section 6.1 | Existing code retained; no invented continuation | S1/S7 acceptance and idempotency/negative/deployed browser proof |
| Customer-global billing | WBE `getCustomerBillingPortalProjection` through BP `getBillingPortalSummary` | Not implemented; no browser aggregation | WBE/BP formal contract acceptance and owner truth |
| Goal verification | BP `submitRelationshipCommand`, proposed `VERIFY_GOAL` discriminator | Not implemented | BP/professional/INST-005 formal acceptance |
| Operations reassessment | BP `getRelationshipOperations`, owner eligibility/history | Existing lock preserved | Goal amendment/verification acceptance and deployed reassessment proof |
| Text, voice, alerts, onboarding, outcomes, Stop | Existing generated BP consumers | Full existing Jest suite passes; no semantic API amendment | Exact deployed acceptance and channel equivalence not requalified |

The canonical WC-084 capability ledger and WC-085 Section 6 remain the owner mapping. Web, WhatsApp
and future-mobile semantic equivalence is not asserted for the unaccepted additions. No private
service URL was added to browser code. Generated-client regeneration was NOT_RUN because schemas
and generated clients were unchanged; this does not complete SP-19.