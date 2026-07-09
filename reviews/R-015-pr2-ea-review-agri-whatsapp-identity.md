# R-015 — Enterprise Architect Review: PR #2 — Agricultural Advisor WhatsApp Phone Identity (ADR-023)

**Review ID:** R-015
**Reviewer Office:** Enterprise Architect
**PR:** #2 — `agent/update/agri-whatsapp-identity`
**Subject:** ADR-023 + agricultural-advisor-agent.md v2.0 WhatsApp-native identity
**Files reviewed:** ADR-023, agricultural-advisor-agent.md, mcp-tool-catalogues.md, containers.md, docker-compose.yml, 03-enums-and-tables.sql, 04-rls-policies.sql
**Date:** 2026-07-09

---

## Overall Verdict: APPROVED WITH ONE NOTE

ADR-023 is architecturally sound and constitutionally well-grounded. The Phone Identity Service is the correct solution for C-042 agents — phone-as-SSO via Meta's verification, parallel to Keycloak for portal users, same RLS enforcement. The agricultural-advisor-agent.md v2.0 Skill 0 and WhatsApp-native onboarding are correctly specified. All Section 14 gate checks pass.

---

## Constitutional Traceability Verification

| Claim/Driver | Applied | Evidence |
|---|---|---|
| C-039 (conversational) | ✓ | WhatsApp-native onboarding distributed per AD-013 amendment |
| C-042 (Vocabulary Mandate) | ✓ | Preserved across all identity and onboarding exchanges |
| AD-004 (multi-tenant isolation) | ✓ | Phone → organisation_id → RLS — same enforcement as JWT path |
| C-023 (Evidence First) | ✓ | CE.RecordEvidence(FARMER_REGISTERED) on auto-registration |
| C-001 (human override) | ✓ | TRAI_OPT_IN_REQUIRED always-ask respects farmer's right not to receive messages |
| ADR-007 (mTLS) | ✓ | phone-identity-service requires mTLS from Business Platform |

---

## Security Model Assessment

**HMAC webhook validation (replay prevention):** ±5 minute timestamp check is correct and sufficient for WhatsApp use case. Meta's message_id uniqueness also provides natural replay protection.

**Session token (30 minutes):** Appropriate. Agricultural advisory conversations are typically 3–5 minutes. 30 minutes provides headroom for distributed multi-exchange conversations without creating long-lived attack surfaces.

**Phone number spoofing:** Correctly identified as impossible — Meta controls the `from` field. No WAOOAW-side phone verification needed.

**Pre-tenant session:** Correctly identified that `phone_identity_sessions.organisation_id` can be NULL during auto-registration. The RLS model handles this correctly — identity service writes with no RLS, then downstream services apply RLS after organisation_id is established.

---

## Section 14 Activation Gate Verification

| Section | Status | Notes |
|---|---|---|
| 1 — Spec Completeness | ✅ PASS | Skill 0 complete; constitutional basis updated with ADR-023 |
| 2 — Prompt Gate | ✅ PASS | WHATSAPP_PHONE_IDENTITY reuses OPENING_MESSAGE + INFERENCE_CONFIRM — no new prompts needed; already seeded |
| 3 — MCP Gate | ✅ PASS | phone-identity-service in containers.md + tool catalogue (5 tools) + docker-compose |
| 4 — Skill Runtime Gate | ✅ PASS | Skill 0 is PRODUCES_RECORD — no approval mode config required |
| 5 — Execution Loop Gate | ✅ PASS | WhatsApp webhook = event trigger; first-message → auto-registration → agent loop |
| 6 — Data Gate | ✅ PASS | phone_identity_sessions + whatsapp_trai_optins; RLS + GRANT |
| 7 — Constitutional Gate | ✅ PASS | C-042 preserved; TRAI_OPT_IN_REQUIRED; Evidence First on registration |
| 8 — Architecture Chain | ✅ PASS | containers.md + MCP catalogue + SQL + RLS + ADR-INDEX + README + PROJECT_STATE |
| 9 — Review Gate | ✅ PASS (this review) | |

---

## Note R015-01 (non-blocking — cleanup in next update)

**phone-identity-service is listed in the MCP Tool Catalogues file** (`mcp-tool-catalogues.md`) but is explicitly described as "NOT an MCP server — internal platform service." This creates a naming inconsistency: the file is called `mcp-tool-catalogues.md` but contains a non-MCP service.

**Recommended resolution (not blocking this PR):** Either rename `mcp-tool-catalogues.md` to `service-api-catalogues.md` or add a clear section header: "## Internal Platform Services (not MCP — no CE.ValidateAction)." This distinction matters for developer clarity — phone-identity-service does not go through the MCP C-041 validation path.

---

## Verdict: APPROVED

All Section 14 gate checks pass. R015-01 is non-blocking. PR #2 may be merged after Founder approval.
