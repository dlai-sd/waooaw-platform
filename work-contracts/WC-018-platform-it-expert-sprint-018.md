# Work Contract 018 — Sprint 018: All CCTs + QA Promotion + Pilot Prep

**Office:** WAOOAW AI Agent — QA + WAOOAW AI Agent — Platform IT Expert
**Sprint:** 018
**Backlog Item:** IB-009 (Foundation complete) → MVI Gate
**Sprint Track:** Track 8 — Quality + Launch (PMO §2.1 M9-M18)
**Reviewer:** Ojal Khandge (ethics/constitutional review) + Sujay (output quality)
**Constitutional Basis:** C-071 (Quality), C-076 (Coverage), C-001, C-059, C-065

**Depends on:** WC-017 (AS-001 Grade A in dev)
**Authorization:** Requires WC-017 complete

---

## Sprint Goal

Promote platform to QA environment and run full quality suite:
1. All 50 CCTs pass in QA
2. All acceptance scenarios (AS-001 to AS-005) Grade A in QA
3. Performance: P99 latencies within SLA (Emergency Stop ≤250ms, CE ≤40ms)
4. DAST: 0 OWASP ZAP critical/high findings
5. Blue-green QA deploy working (C-067)
6. Pilot onboarding: 5 customers configured (Sujay drives)

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| All WC-012 to WC-017 complete | `src/` running in dev | ⏳ PENDING |
| Azure QA credentials | GitHub Secrets | ❌ PENDING FA-NNN |
| WABA live | WhatsApp Business Account | ❌ PENDING FA-002 chain |
| Razorpay test keys | GitHub Secrets | ❌ PENDING PMO-007 |
| 5 pilot customers | Sujay outreach | ❌ PENDING |

**Readiness: BLOCKED** — multiple dependencies

---

## Tasks (abbreviated — detail added when WC-017 is DONE)

### WC018-01 — QA environment Terraform apply
### WC018-02 — Full 50 CCT suite in QA
### WC018-03 — All AS acceptance scenarios Grade A
### WC018-04 — DAST scan (OWASP ZAP)
### WC018-05 — k6 performance baseline (50 VUs)
### WC018-06 — 5 pilot customers onboarded (Sujay + Platform Operations)
### WC018-07 — First payment received (Razorpay)

**Status:** WAITING — detailed task breakdown added when WC-017 complete
