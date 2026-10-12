# C4 Level 1 — System Context

**Produced by:** Enterprise Architect (Sprint 003)
**Date:** 2026-07-07 (updated 2026-10-12)
**Constitutional Basis:** AD-004 (multi-tenant isolation), AD-009 (security by design), capability domains 1–6, ADR-051, proposed ADR-052 and ADR-053

---

## Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Customer (Organisation)                                                   │
│   A business that hires digital professionals                               │
│   [ Dental clinic / Beauty artist / Trader / Enterprise ]                   │
│                     │                                                       │
│          REST HTTPS + WebSocket (Emergency Stop)                            │
│                     │                                                       │
│         ┌───────────▼────────────────────────────┐                         │
│         │          WAOOAW Platform               │                         │
│         │                                        │                         │
│         │  Constitutional governance of          │                         │
│         │  autonomous digital professionals      │                         │
│         └───────────────────┬────────────────────┘                         │
│                             │                                               │
│              ┌──────────────┼──────────────┐                               │
│              │              │              │                               │
│       Google OAuth    LLM Providers    NSE/Market Data                     │
│       (Identity)     (AI inference)   (Trading: Case 003)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Actors

| Actor | Type | Description |
|---|---|---|
| Customer | Person / Organisation | Hires, governs, and manages digital professionals |
| Meta WhatsApp Cloud API | External System | Transports environment-bound WhatsApp messages, media, templates and delivery statuses; never owns relationship or constitutional truth |
| Google OAuth | External System | Identity provider (federated through Keycloak — ADR-008) |
| LLM Provider | External System | AI inference (OpenAI / Azure OpenAI — provider-agnostic via AI Runtime) |
| NSE Market Data | External System | Real-time market data feed (Acceptance Scenario 003 — trading) |
| WAOOAW Platform | Software System | This system |

## Key Interactions

**Customer → Platform:**
- Hire, configure, and govern digital professionals (REST API)
- Continue one relationship conversation through web, WhatsApp and, when separately authorized, mobile
- Converse with the professional through Onboard/Induct/Groom, Goal/Plan/Milestone/Calendar, and
  Operations/Billing/Performance phases
- View authoritative progress, completed, in-progress and pending work with reasons, owners,
  blocked effects, evidence and next actions
- Review proposed actions and exercise approvals (REST API)
- Emergency Stop (persistent WebSocket, ≤250ms — AD-001)
- View evidence ledger and performance dashboards (REST API)

The three conversational phases share one Employment Relationship, durable conversation and
Business Platform relationship workspace. They do not create new system actors or deployable
services.

**Platform ↔ Meta WhatsApp Cloud API:**
- Receive environment-bound, signature-validated messages, interactive responses, media references
  and delivery statuses through the Business Platform WhatsApp boundary.
- Submit only canonical Business Platform messages or typed command outcomes through the approved
  environment number and provider authority.
- Keep provider acceptance, delivery and read state separate from professional execution, customer
  decision and constitutional evidence.

**Platform → LLM Provider:**
- AI inference for professional reasoning and content generation
- All calls are governed by Decision Space — the AI layer does not define scope

**Platform → NSE Market Data:**
- Real-time price feeds for PAAS trading execution
- Read-only — platform never places market orders directly; orders go through broker API

**Platform → Google OAuth:**
- Customer identity verification (federated via Keycloak — customers never interact with Google directly from the platform's perspective)
