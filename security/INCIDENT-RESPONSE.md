# WAOOAW — Incident Response Plan

**Version:** 1.0
**Date:** 2026-07-13
**Authority:** Founder
**Constitutional Basis:** Constitution Article IX; GENESIS AI Security Mandate
**Regulatory Basis:** CERT-IN Directions 2022 (mandatory 6-hour reporting); DPDPA India 2023 (72-hour breach notification); POCSO India 2012 (CSAM immediate reporting)

---

## 1. Incident Severity Classification

| Severity | Definition | Examples | Response Time |
|---|---|---|---|
| **P0 — CRITICAL** | Constitutional violation; CSAM detected; data breach with PII exposure; service completely unavailable | CSAM_DETECTED event; multi-tenant data leak; Emergency Stop failure; production database compromised | **Immediate (within 15 minutes)** |
| **P1 — HIGH** | Security control bypass; significant vulnerability; partial service disruption | Prompt injection success; SSRF successful; auth bypass; MPIN brute force success | **Within 1 hour** |
| **P2 — MEDIUM** | Suspicious activity; potential vulnerability; degraded service | Unusual access patterns; MPIN lockout storm; rate limit triggered repeatedly | **Within 4 hours** |
| **P3 — LOW** | Minor security events; informational alerts | Failed login attempts within normal range; dependency vulnerability (not exploitable) | **Within 24 hours** |

---

## 2. Incident Response Phases

### Phase 1 — Detect and Classify (0-15 minutes for P0, proportional for others)

**Automated detection sources:**
- Constitutional Audit Ledger (CAL): SECURITY_EVENT records → SIL signal → platform operations alert
- GitHub Actions: build failures, secret detection alerts
- Azure Defender for Containers: runtime anomalies
- Gitleaks/CodeQL: alerts in GitHub Security tab
- Trivy: CVE alerts in GHCR

**Manual detection:**
- Responsible disclosure reports (security@waooaw.com)
- Customer reports (unusual agent behavior)
- CERT-IN advisories

**Classify the incident:**
```
Is this CSAM? → Immediately → Phase 3 CSAM Protocol
Is customer PII exposed? → P0 → Immediate CERT-IN + DPDPA notification
Is the platform unavailable? → P0/P1 → Emergency Stop if agent-related
Is this a suspected breach? → P0 → Containment immediately
```

### Phase 2 — Contain (within the response time for the severity)

**For any security breach:**
1. **Isolate affected component** — scale Container App to 0 replicas
2. **Revoke compromised credentials** — rotate in Azure Key Vault immediately
3. **Preserve evidence** — download logs before any remediation (CERT-IN requires 180-day retention)
4. **Block attack vector** — update rate limits, add WAF rules, revoke JWT tokens if needed

**Do not:**
- Delete any logs or evidence before preservation
- Communicate breach details on any unsecured channel
- Attempt to remediate before containment is complete

### Phase 3 — Notify (legally mandatory for P0)

#### CERT-IN (mandatory within 6 hours of detecting any P0 incident)

Under CERT-IN Directions 2022, the following incidents require reporting within **6 hours**:
- Data breaches involving personal information
- Attacks on critical information infrastructure
- Ransomware attacks
- Unauthorized access to IT systems

```
CERT-IN Report submission: https://www.cert-in.org.in/Report.jsp
Email backup: incident@cert-in.org.in
Phone: 1800-11-4949

Required information:
  - Date and time of detection
  - Nature of incident
  - Systems/services affected
  - Estimated number of users affected
  - Actions taken so far
```

#### DPDPA India 2023 (mandatory within 72 hours for personal data breach)

For any breach involving Indian personal data:
- Notify affected data principals (customers)
- Notify Data Protection Board (once established)
- Maintain breach record with: nature of breach, categories of data, approximate number of data principals affected, likely consequences, measures taken

#### POCSO India 2012 — CSAM Protocol (IMMEDIATE — no delay permitted)

If CSAM is detected (CCT-SEC triggered, C-061 protocol):
1. **Do not store** — purge immediately
2. **Report to NCMEC CyberTipline:** https://www.missingkids.org/gethelpnow/cybertipline
3. **Report to CBI Cyber Crime:** www.cybercrime.gov.in or 1930
4. **No delay permitted** — POCSO reporting is a legal obligation, not a policy choice

### Phase 4 — Remediate

1. Identify root cause (architectural review)
2. Implement fix (if code: PR + CI/CD pipeline; if config: Key Vault update)
3. Verify fix in dev environment
4. Deploy through normal promotion pipeline (CCTs must pass)
5. Post-incident review within 5 business days

### Phase 5 — Post-Incident

**Required artifacts:**
- Incident timeline (exact timestamps from CAL and system logs)
- Root cause analysis
- What controls failed / what controls worked
- Remediation actions taken
- Constitutional Blocker file: `blockers/INC-[date]-[type].md`
- PROJECT_STATE.md update noting the incident

**For P0/P1 incidents:** Publish sanitized incident report (no PII, no technical exploit details) as part of WAOOAW's transparent governance model. Store in `security/incidents/` (redacted version).

---

## 3. Contact Matrix

| Role | Primary | Backup |
|---|---|---|
| Incident Commander | Founder | — |
| Technical Lead | Assigned AI agent (EA office) | — |
| Legal/Compliance | Founder + Legal advisor | — |
| CERT-IN Contact | Founder | — |

---

## 4. Log Retention (CERT-IN Compliance)

CERT-IN Directions 2022 require 180-day log retention:

```yaml
log_retention:
  azure_monitor: 180 days (Azure Monitor log retention configured)
  constitutional_audit_ledger: PERMANENT (CAL is append-only, C-007 immutability)
  application_logs: 180 days minimum
  security_events: 365 days (extended — security events are higher value)
  
  ntp_synchronization:
    requirement: "All system clocks synchronized to NTP (CERT-IN requirement)"
    implementation: "Azure Container Apps use Azure time service (synced to NTP pool)"
    verification: "Check: all log timestamps within ±1 second of NTP time"
```

---

## 5. Annual Review

This plan is reviewed annually or after any P0/P1 incident, whichever comes first. Changes require Founder authorization and are committed to this repository.

**Last reviewed:** 2026-07-13 (v1.0 — initial)
**Next review due:** 2027-07-13
