# WAOOAW — Third-Party Vendor Risk Assessment

**Version:** 1.0
**Date:** 2026-07-13
**Review Cycle:** Annual + on new vendor onboarding
**Authority:** Founder

---

## Vendor Classification

| Tier | Definition | Due Diligence |
|---|---|---|
| **Tier 1 — Critical** | Platform cannot function without this vendor | Full security review, DPA required, annual re-assessment |
| **Tier 2 — Significant** | Feature degradation without this vendor | Security questionnaire, DPA required |
| **Tier 3 — Non-critical** | Platform continues with fallback | Minimum review; contractual data processing terms |

---

## Tier 1 — Critical Vendors

### Microsoft Azure (Azure Container Apps, Azure Key Vault, Azure Monitor)

| Attribute | Assessment |
|---|---|
| Service category | Cloud infrastructure, secret management, observability |
| Data processed | All platform data (all tiers) |
| Location | Azure India Central (Pune) — data residency compliant |
| Security certifications | ISO 27001, SOC 2 Type II, CSA STAR, PCI DSS, FedRAMP |
| DPA status | Azure Data Processing Agreement — accepted via Azure subscription |
| Risk assessment | LOW — market-leading security; Azure India Central chosen specifically for DPDPA compliance |
| Incidents in 12 months | None affecting WAOOAW services |

### Meta (WhatsApp Business API)

| Attribute | Assessment |
|---|---|
| Service category | Primary customer communication channel |
| Data processed | Customer messages (text, voice), phone numbers, organisation_id mapping |
| Location | Meta's global infrastructure (international data transfer) |
| Security certifications | SOC 2, ISO 27001 |
| DPA status | Meta's WhatsApp Business Terms and Data Processing Agreement |
| DPDPA note | Customer messages transit Meta's infrastructure. WAOOAW processes phone-as-identity; message content is not stored beyond session window. |
| Risk assessment | MEDIUM — Meta is essential but represents concentration risk. Fallback: portal-only mode if WhatsApp unavailable. |

### Keycloak (Self-hosted on Azure)

| Attribute | Assessment |
|---|---|
| Service category | Authentication and authorization |
| Data processed | User credentials (hashed), JWT tokens, realm configuration |
| Location | Self-hosted in Azure India Central — full control |
| Security certifications | Open-source; WAOOAW is responsible for operation |
| Risk assessment | LOW — self-hosted = no external vendor risk. Operational risk managed via ADR-008 (version pinning, realm backup). |

---

## Tier 2 — Significant Vendors

### ElevenLabs (Voice synthesis / Digital Twin)

| Attribute | Assessment |
|---|---|
| Service category | AI voice generation (DMA Skill 8 — Digital Twin) |
| Data processed | Customer voice recordings (biometric-adjacent), synthesized audio |
| Location | US-based — international data transfer |
| Security certifications | SOC 2 Type I (as of 2026) |
| DPA status | ElevenLabs Terms of Service + GDPR-compliant data processing agreement |
| DPDPA note | **Cross-border transfer of voice data (biometric-adjacent).** Customer explicit consent required before Digital Twin setup. This is declared in the agent spec and in the customer onboarding flow. |
| Mitigations | Voice clone deleted within 30 days of subscription termination (see DATA-RETENTION.md) |
| Risk assessment | MEDIUM — voice data is sensitive; ElevenLabs has appropriate certifications; deletion API confirmed working |

### Azure Content Safety API (Content moderation — C-061)

| Attribute | Assessment |
|---|---|
| Service category | Content moderation (CSAM, explicit content detection) |
| Data processed | Media hashes and content for moderation (images, text) |
| Location | Azure India Central (same region as platform) |
| Security certifications | Part of Azure — inherits Azure security certifications |
| DPA status | Azure DPA — same as primary Azure agreement |
| Risk assessment | LOW — critical safety component; fallback is BLOCK (fail-safe per C-061) |
| Note | If unavailable, platform blocks all media uploads (fail-safe) — not degradable per C-061 |

### Brevo / Sendinblue (Email marketing for DMA Skill 15)

| Attribute | Assessment |
|---|---|
| Service category | Email delivery for customer campaigns |
| Data processed | Customer email lists (customer's patients/clients), email content |
| Location | EU-based; GDPR compliant; DPDPA cross-border transfer applicable |
| Security certifications | ISO 27001 |
| DPA status | Brevo Data Processing Agreement required before activation |
| DPDPA note | Customer's patient/client emails processed by Brevo. Customer must have consent from their own subscribers. WAOOAW verifies this at list import (Skill 15 onboarding). |
| Risk assessment | MEDIUM — contains customer's CRM data; deletion API available and tested |

---

## Tier 3 — Non-critical Vendors (Free APIs)

| Vendor | Service | Data | Risk |
|---|---|---|---|
| NCERT (Govt of India) | Curriculum data API | Public curriculum content | LOW — public data |
| Agmarknet (Govt of India) | Agricultural price data | Public mandi prices | LOW — public data |
| SFAC FPO Registry (Govt of India) | FPO database | Public FPO data | LOW — public data |
| PM-KISAN Portal (Govt of India) | Scheme eligibility | Public scheme data | LOW |
| IMD / Open-Meteo | Weather data | Weather forecasts (no PII) | LOW |
| CBSE (Govt of India) | Previous year papers | Public exam papers | LOW |
| Temporal (Self-hosted) | Workflow orchestration | Workflow inputs/outputs | LOW — self-hosted |

---

## Vendor Onboarding Checklist

For every new Tier 1 or Tier 2 vendor:

- [ ] Vendor's security certifications reviewed (ISO 27001, SOC 2, or equivalent)
- [ ] Data Processing Agreement (DPA) signed before any data is shared
- [ ] DPDPA cross-border transfer assessment (if vendor is outside India)
- [ ] Data retention and deletion capabilities confirmed (can WAOOAW trigger deletion?)
- [ ] Vendor security incident history reviewed (last 12 months)
- [ ] Fallback/degradation plan if vendor is unavailable
- [ ] Added to this document
- [ ] ADR created if vendor introduces new architectural dependencies

---

## Annual Review

This assessment is reviewed annually and upon:
- New vendor addition
- Significant vendor security incident
- Changes to DPDPA / IT Rules 2021 requirements
- Subscription or licensing changes

**Next review due:** 2027-07-13
