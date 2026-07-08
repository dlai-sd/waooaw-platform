# R-013 — Enterprise Architect Review: Agricultural Advisory Agent

**Review ID:** R-013
**Reviewer Office:** Enterprise Architect
**Date:** 2026-07-08
**Agent Spec:** `architecture/reference/agents/agricultural-advisor-agent.md` v1.0
**Constitutional Basis of Review:** GENESIS Part 05 (Agent Definition Protocol), C-036–C-042
**Prior Reviews Referenced:** R-011 (Digital Marketing), R-012 (Trading Agent)

---

## Review Summary

| Dimension | Assessment |
|---|---|
| C-042 Vocabulary Mandate compliance | STRONG — most thorough implementation of any spec to date |
| Progressive Crop State Model | STRONG — Tier 2 RAG design is sound and implementable |
| PMFBY evidence chain | STRONG — architecturally elegant use of C-023 as insurance infrastructure |
| Weather ensemble design | STRONG — 5-source architecture with seasonal weighting is credible |
| MCP server inventory | INCONSISTENT — orphaned dependency and missing stub (see R013-02) |
| Emergency Stop mechanism | INCOMPLETE — WhatsApp pathway not specified (see R013-03) |
| Always-ask actions | GAP — `FARMER_LAND_PROFILE_CONFIRMED` described in checklist, absent from template (see R013-01) |
| **Overall verdict** | **CHANGE REQUEST — 3 P0 gaps must be fixed before Founder approval** |

---

## P0 Gaps — CHANGE REQUEST

### R013-01: `FARMER_LAND_PROFILE_CONFIRMED` absent from `always_ask_actions`

**Finding:**
The constitutional checklist (Section 11) states:
> "R012-01 pattern applied: FARMER_LAND_PROFILE_CONFIRMED as implicit evidence record during onboarding"

But the Professional Template's `always_ask_actions` list does not include `FARMER_LAND_PROFILE_CONFIRMED`. The action exists only as a checklist claim — it has no constitutional enforcement path.

**Why this is P0:**
This is the exact gap type that caused R011-01 (patient image consent) and R012-01 (broker API auth) to be filed. The checklist now explicitly warns against it. The land profile — village, acres, irrigation type, soil type, language — is the foundational context on which every single advisory this agent gives is based. If the farmer did not explicitly confirm this profile, and the agent later gives wrong advice (e.g., recommends drip irrigation on a farm that was entered with wrong water availability), there is no evidence record showing the farmer approved the configuration. This is both a constitutional gap (no CAL record of farmer consent to their profile) and a practical liability gap (no audit trail for advisory basis).

**Required fix:**
Add to `always_ask_actions` in the Professional Template:
```yaml
- { actionType: "FARMER_LAND_PROFILE_CONFIRMED",
    description: "Farmer confirms their land profile (village, acres, irrigation type,
                  soil type, language preference) — the basis for all advisory.
                  Creates an immutable CAL record with confirmed_at timestamp.
                  Constitutional basis: C-023 (Evidence First), C-039 (conversational
                  configuration is a constitutional obligation)." }
```

This CAL record becomes the audit foundation for: "All advice given to this farmer was calibrated to this land profile, confirmed by the farmer on [date]."

---

### R013-02: `soil-data-mcp` — orphaned dependency in Section 9

**Finding:**
Section 9 (New MCP Servers Required) lists `soil-data-mcp` as a new MCP server with this description:
> "NBSS&LUP soil database, PM Soil Health Card — New — WAOOAW-built"

However:
- `soil-data-mcp` does not appear in the MCP Tools table of any Skill (Skills 1–6)
- No Skill has a Decision Space action that would invoke it
- There is no MCP tool call with `soil-data-mcp` as the server

**Why this is P0:**
An MCP server in the required list but absent from all Skill tool tables means one of:
(a) A Skill that requires it is missing from the spec, OR
(b) The server was listed speculatively and soil data is actually served by RAG Tier 1 (ICAR suitability matrices, loaded at startup — a static dataset, not a real-time API call)

Option (b) is architecturally sound: NBSS&LUP soil data is a static national database, not a per-request API. It can be loaded into the institutional RAG Tier 1 store (like ICAR data) and retrieved without an MCP server. The farmer's specific soil type is captured in `farmer_profiles.soil_type` during onboarding — no MCP call needed.

**Required fix:** Remove `soil-data-mcp` from Section 9. Add a note to Skill 4 (Crop Planning) RAG Sources:

```
| 1 — Domain | NBSS&LUP soil suitability database (loaded into Tier 1 RAG at agent init) | Soil-crop compatibility check |
```

This eliminates an unnecessary MCP server (5 servers → 5 servers, soil-data-mcp never existed in containers.md — good), resolves the orphaned dependency, and correctly characterises soil data as static Tier 1 knowledge.

---

### R013-03: Emergency Stop via WhatsApp — architectural path not specified

**Finding:**
Section 5 specifies:
> "The Emergency Stop via WhatsApp: farmer sends 'STOP' or calls out 'bandh kar' — the agent immediately stops all communications."

This does not specify the architectural path from WhatsApp message to Constitutional Engine Emergency Stop handler. For all other agents (web PWA), Emergency Stop travels: customer → WebSocket → Professional Runtime → CE.EmergencyStop → CAL record. For this agent, the customer channel is WhatsApp — there is no WebSocket.

**Why this is P0:**
Emergency Stop is an AD-001 constraint (≤250ms) and a constitutional primitive (ART-XI). If the Emergency Stop path is not specified for this agent's primary channel, the Constitutional Compliance Test (CCT for Emergency Stop) cannot be written and the implementation team has no clear design to follow. An underspecified Emergency Stop is not a constitutional Emergency Stop.

**Required fix:**
Replace Section 5 with a fully specified Emergency Stop path:

```
WhatsApp Emergency Stop path:
  1. Farmer sends "STOP" (text) or voice message containing "bandh kar" / "stop"
  2. whatsapp-voice-mcp receives webhook → detects STOP keyword via transcription
  3. whatsapp-voice-mcp calls AI Runtime /emergency-stop endpoint (HTTP POST)
     [Note: this is NOT a normal tool call — it is a priority interrupt path]
  4. AI Runtime immediately calls Professional Runtime /emergency-stop (skips CE.ValidateAction
     — Emergency Stop is unconditional per ART-XI; no validation gate permitted)
  5. Professional Runtime calls CE.EmergencyStop(employment_contract_id)
  6. CE records: {action_type: EMERGENCY_STOP_EXECUTED, initiated_by: FARMER_WHATSAPP}
  7. Professional Runtime halts all queued tasks for this farmer's agent
  8. whatsapp-voice-mcp sends acknowledgment in farmer's language:
     "समजलं — मी थांबतो. 'सुरू कर' म्हणाल तेव्हा परत सुरू होईन."
     ["Understood — I'm stopping. Say 'start again' when ready."]

Latency target: ≤250ms from webhook receipt to CE record (AD-001 applies).
Resume: farmer sends "SURU KAR" / "start" / "resume" → new EMERGENCY_STOP_LIFTED event.
```

---

## P1 Findings — Non-blocking, fix in v1.1

### R013-04: `enam-mcp` and `policy-data-mcp` not in docker-compose.yml

Section 9 lists `enam-mcp` and `policy-data-mcp` as required MCP servers. The v0.12.0 docker-compose.yml stubs only include: weather-ensemble-mcp, agmarknet-mcp, whatsapp-voice-mcp, broker-api-mcp, whatsapp-business-mcp. Both `enam-mcp` and `policy-data-mcp` are marked DEGRADABLE in all Skill MCP Tools tables, so local dev can proceed without them.

**Resolution path:** Add enam-mcp (port 8105) and policy-data-mcp (port 8106) stubs to docker-compose.yml when implementing Skills 3 and 5 respectively. Update containers.md MCP inventory at that time.

---

### R013-05: `PMFBY_REPORT_GENERATE` should be in `always_ask_actions`

The Skill 6 decision space (text) says:
> "Always-ask: Generating a formal PMFBY Evidence Report for submission (this is a legal document — farmer must explicitly request it)"

But the Professional Template has `PMFBY_REPORT_GENERATE` in `authorized_actions`, not `always_ask_actions`.

The intent is clear (explicit request = the approval), but the CE needs to see an APPROVED state record before generating a legal document. The fix: move `PMFBY_REPORT_GENERATE` to `always_ask_actions`. The farmer's WhatsApp request triggers the always-ask → farmer confirms → CE records APPROVED → document generated.

---

## Positive Findings

### C-042 Vocabulary Mandate — strongest implementation to date
The vocabulary translation table (Section 3) is the most detailed and actionable C-042 implementation in any spec. The distinction between "Humidity 87%, 23mm cumulative rain 4 days" (internal) and "Your cotton has high risk of grey mildew. Spray Carbendazim tomorrow before 8 AM." (farmer output) is exactly the implementation pattern DP-013 requires. The v0.12.0 AI Runtime component spec's VTL processing pipeline (6 steps) is directly implementable from this spec.

### Progressive Crop State Model — sound Tier 2 RAG design
The `CropStateModel` JSON structure in Skill 2 is concrete and implementable. The `agent_progressive_state` table added in v0.12.0 maps directly to this structure. The morning check-in conversation pattern demonstrates that the model drives proactive rather than reactive advisory — this is the intended behavior of C-039 (conversational interface as constitutional obligation, not just a UX choice).

### PMFBY evidence chain — constitutional architecture at its best
The 4-step evidence chain (alert issued → acknowledged → weather confirmed → damage reported → report) is an exemplary application of C-023. This is the first agent spec where a constitutional compliance mechanism (Evidence First) directly creates a material financial benefit for the customer without any additional implementation effort. This should be documented as a constitutional design pattern for future agents.

### Section 9 (New MCP Servers) — proactive gap disclosure
The explicit Section 9 listing of all required MCP servers is a positive addition to the spec format. It should be standardized into the AGENT-AUTHORING-GUIDE template. (Note: AGENT-AUTHORING-GUIDE Section 9.1 Architecture Chain Update Checklist now includes this requirement.)

### Pricing model — realistic and graded
Section 10 (Pricing) is the first agent spec to include a detailed unit economics model. The ₹8-12/farmer/month infrastructure cost estimate and the multiple revenue paths (direct, FPO, government, input co-marketing) are credible for a B2B2C agricultural platform. This should become a standard section in all future specs.

---

## Required Actions Before Founder Approval

| ID | Finding | Action | Owner |
|---|---|---|---|
| R013-01 | `FARMER_LAND_PROFILE_CONFIRMED` missing from `always_ask_actions` | Add to Professional Template | Business Architect |
| R013-02 | `soil-data-mcp` orphaned in Section 9 | Remove from Section 9; add NBSS&LUP to Skill 4 Tier 1 RAG | Business Architect |
| R013-03 | WhatsApp Emergency Stop path not specified | Replace Section 5 with full WhatsApp path spec | Business Architect |

---

## Recommended: Add Section 10 (Pricing) to AGENT-AUTHORING-GUIDE Template

The agricultural agent's Section 10 (Pricing) is the first credible unit economics model in any agent spec. Recommend standardising this as a required section in AGENT-AUTHORING-GUIDE, placed after Section 8 (Learning Loop). Without pricing, future agent specs will not be investment-ready for Founder approval.

---

## Verdict

**CHANGE REQUEST** — address R013-01, R013-02, R013-03 and resubmit as v1.1.

The spec is otherwise the strongest in the platform portfolio. C-042 compliance is thorough, the Progressive Crop State Model is well-specified, and the PMFBY evidence chain is a constitutional design landmark. Three targeted fixes are needed — none require rethinking the architecture.

---

*EA Office — WAOOAW*
*R-013 | 2026-07-08*
