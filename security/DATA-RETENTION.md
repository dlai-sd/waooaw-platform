# WAOOAW — Data Retention and Deletion Policy

**Version:** 1.0
**Date:** 2026-07-13
**Authority:** Founder
**Regulatory Basis:** DPDPA India 2023; CERT-IN Directions 2022; POCSO India 2012

---

## Principle

WAOOAW retains data only as long as necessary for its stated purpose. When a customer terminates their subscription or requests deletion, their data is deleted within the timelines below. Immutable constitutional audit records are an exception — they cannot be deleted (C-007 Audit Ledger Immutability) but they contain no PII.

---

## Retention Schedule

### Customer Data

| Data Category | Retention Period | Deletion Trigger | Notes |
|---|---|---|---|
| Customer profile (name, business, contact) | Duration of subscription + 30 days | Subscription termination + 30-day grace period | 30-day grace allows re-subscription without losing setup |
| Employment Contract and Decision Space | Duration of subscription + 30 days | Same as above | |
| Agent session transcripts | 12 months | Rolling 12-month window | Older sessions deleted automatically |
| Uploaded media (images, videos, audio) | 90 days after last use | Auto-expiry after 90 days of non-reference | Customer can delete immediately via portal |
| Platform reports and analytics | 24 months | Rolling; older reports deleted automatically | |
| WhatsApp session tokens | 30 minutes | Session expiry (ADR-023) | |

### Security and Audit Data

| Data Category | Retention Period | Notes |
|---|---|---|
| Constitutional Audit Ledger (CAL) | **Permanent** | Append-only, immutable (C-007). No PII — contains organisation_id + action_type + timestamps only. |
| Application logs | 180 days | CERT-IN Directions 2022 minimum requirement |
| Security event logs | 365 days | Extended — security events are higher-value for forensics |
| MPIN lockout events | 90 days | Used for fraud detection patterns |
| Content safety scan results | 90 days | PASS results only; CSAM events → see below |
| CSAM detection records | **Permanent** | Legal obligation — cannot be deleted. Contains only: timestamp, org_id, content_hash (not content), report IDs submitted to NCMEC/CBI |

### Special Categories

| Category | Retention | Override |
|---|---|---|
| **Minor student data** (Private Tutor) | Duration of subscription + 7 days | Parent can request immediate deletion — completed within 72 hours (C-060, DPDPA) |
| **Voice clones** (Digital Twin) | Duration of subscription + 30 days | Customer can delete immediately; ElevenLabs deletion requested simultaneously |
| **Health-related content** (dental/medical DMA) | Duration of subscription + 30 days | Standard healthcare data handling |
| **Demo/trial session data** | 7 days if no conversion | Auto-deleted if customer does not subscribe (C-060) |

---

## Deletion Process

### On Customer Request (Right to Erasure — DPDPA)

1. Customer submits deletion request via portal (authenticated)
2. System initiates cascade delete within **72 hours** (DPDPA requirement)
3. Deleted: profile, transcripts, media, reports, session data
4. **NOT deleted:** Constitutional Audit Ledger records (C-007 — immutable; contain no PII)
5. **NOT deleted:** CSAM incident records (legal obligation)
6. Customer receives confirmation with list of what was deleted and what was retained (with legal reason)

### On Subscription Termination (Without Request)

- 30-day grace period: data retained, subscription inactive
- Day 30: automatic deletion cascade begins
- Day 37: deletion confirmed; customer notified

### Minor Student Data (C-060 — 72 hours)

Any deletion request for student data is treated as the highest priority:
- Must complete within 72 hours regardless of queue
- Includes: session transcripts, quiz performance, engagement data, story bank interactions
- Excludes: CAL records with organisation_id (no student name or PII in CAL)

---

## Third-Party Processor Deletion

When WAOOAW deletes customer data, it also triggers deletion at third-party processors:

| Processor | Data type | Deletion method |
|---|---|---|
| ElevenLabs | Voice clone model | API call: `DELETE /v1/voice-generation/voice/{voice_id}` |
| HeyGen | Digital Twin avatar | API call: `DELETE /v2/avatar/{avatar_id}` |
| Azure Blob Storage | Uploaded media | Azure SDK: `BlobClient.DeleteAsync()` |
| Brevo (Email) | Customer email list | API call: `DELETE /v3/contacts/{email}` |

Evidence: THIRD_PARTY_DELETION_CONFIRMED event in CAL for each processor.

---

## Audit Trail

Every deletion event is recorded in the Constitutional Audit Ledger:
```
action_type: DATA_DELETION_INITIATED
action_type: DATA_DELETION_COMPLETED (with record counts per category)
action_type: THIRD_PARTY_DELETION_CONFIRMED (per processor)
constitutional_basis: C-007 (ledger is immutable); DPDPA erasure right
```

The CAL records the deletion but not the deleted data — this satisfies both the DPDPA erasure right and C-007 immutability simultaneously.
