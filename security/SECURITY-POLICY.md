# WAOOAW Platform — Security Policy Index

**Version:** 1.0
**Date:** 2026-07-13
**Authority:** Founder (Constitutional Authority — Constitution Article IX)
**Applicable to:** All AI agents, platform components, data processing activities, and personnel (human or AI) operating under WAOOAW's institutional governance.

---

## What makes WAOOAW's security model unusual

WAOOAW's security policies are not Word documents that sit in a SharePoint folder. They are version-controlled in this repository, enforced by automated tests (Constitutional Compliance Tests), and auditable through the same git history that auditors can inspect for every policy change.

Every security decision is an Architectural Decision Record (ADR). Every constitutional security requirement is a ratified Claim. Every security control is tested in CI/CD via a CCT. The evidence trail is the repository itself.

---

## Policy Documents

| Document | Location | What it covers |
|---|---|---|
| Constitutional Security Foundation | `constitution/CONSTITUTION.md` Article IX | Security as a constitutional floor |
| Engineering Security Mandate | `constitution/GENESIS.md` §AI Security Mandate | AI security, prompt injection, SSRF, log sanitization |
| Secret Management | `adr/ADR-014-secret-management.md` | 3-tier secret management |
| Identity and Authentication | `adr/ADR-008-keycloak-identity-broker.md` v2 | IDP strategy, RBAC, JWT claims |
| WhatsApp Authentication Tiers | `adr/ADR-023-whatsapp-phone-identity-c042-agents.md` v2 | MPIN, action risk tiers |
| API Rate Limiting | `adr/ADR-006-api-rate-limiting.md` | DDoS protection |
| Service-to-Service mTLS | `adr/ADR-007-grpc-mtls-certificates.md` | Internal network security |
| Content Safety (CSAM + media) | `knowledge/claims/C-061.md` | Content moderation, POCSO |
| AI Security (Prompt Injection) | `knowledge/claims/C-062.md` | OWASP LLM Top 10 |
| Data Protection (DPDPA) | `constitution/GENESIS.md` §DPDPA | India data protection |
| Minor Student Protection | `knowledge/claims/C-060.md` | Children's data (highest tier) |
| **Incident Response Plan** | `security/INCIDENT-RESPONSE.md` | Breach response, CERT-IN |
| **Vulnerability Disclosure** | `security/VULNERABILITY-DISCLOSURE.md` | Responsible disclosure |
| **Data Retention Policy** | `security/DATA-RETENTION.md` | Retention periods, deletion |
| **Third-Party Vendor Risk** | `security/THIRD-PARTY-RISK.md` | MCP vendors, cloud providers |
| **Security Headers** | `security/SECURITY-HEADERS.md` | HTTP security headers |

---

## Security Compliance Status

| Framework | Status | Evidence |
|---|---|---|
| OWASP Top 10 | ✅ Addressed | ADR-006/007/008/014; CCTs; SAST/DAST |
| OWASP LLM Top 10 | ✅ Addressed | C-062; GENESIS AI Security Mandate; CCT-SEC-01/02/03 |
| DPDPA India 2023 | ✅ Addressed | GENESIS DPDPA section; C-060; Azure India Central |
| POCSO India 2012 | ✅ Addressed | C-061 (CSAM mandatory reporting pipeline) |
| IT Act India 67/67A/67B | ✅ Addressed | C-061 (content moderation) |
| IT Rules 2021 (Intermediary) | ✅ Addressed | C-061; content moderation; grievance officer (pending) |
| CERT-IN Directions 2022 | ✅ Addressed | `security/INCIDENT-RESPONSE.md` (6-hour reporting) |
| ISO 27001 (controls) | ⚠️ Partial | Controls implemented; formal certification pending |
| SOC 2 Type II | ⚠️ Planned | Evidence collection begins with first customer |
| PCI DSS | ✅ Scoped out | Payment processing via Razorpay (ADR-022) — platform is not in PCI scope |

---

## Security Contact

**Grievance Officer:** Founder (designated before commercial launch — DPDPA requirement)
**Security Reports:** security@waooaw.com (to be set up)
**CERT-IN Contact:** cert-in@icert.gov.in (for mandatory breach reporting)
