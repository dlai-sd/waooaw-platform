# R-047 — WC-034 Solution Architecture Review

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `work_contract` | WC-034 |
| `pull_request` | PR #239 |
| `record_id` | R-047 |
| `record_type` | Architecture Review Record |
| `produced_at` | 2026-08-09 |
| Decision | **APPROVED** |

## Scope

INST-005 independently reviewed component ownership, API and stream boundaries, server/client rendering ownership, failure semantics, F0-F8 separability, and omnichannel continuity against the AE-01 solution, security, data, and continuity contracts. This approval covers WC-034 Phase A architecture only. It does not approve product decisions, implementation, source changes, deployment, or WC-058 through WC-060 execution.

## Findings and Corrections

| ID | Severity | Finding | Correction |
|---|---|---|---|
| SA-01 | Critical | F7 could be read as authorizing generated web clients against internal-only WBE management APIs. | BP is now the sole public Founder facade; WBE owns internal billing behavior and remains unreachable from the browser. UX-CONTRACT-01 makes this executable. |
| SA-02 | Significant | F3 jointly named BP and PR without assigning customer ingress, durable command/read ownership, and internal execution-stream ownership. | BP now owns the public conversation and stream boundary; PR owns internal execution/session streaming. Ordinary browser-to-PR traffic is prohibited except the dedicated Emergency Stop path. |
| SA-03 | Significant | F1 inherited the complete visual matrix, including routes owned by later components, so it could not close independently. | F1 visual evidence is limited to F1-owned routes and states; F8 retains the complete cross-component matrix. |
| SA-04 | Significant | Voice and cross-channel replay were described as unconditional first-release invariants despite F6 and WC-060 gates. | Voice is conditional on F6; committed handoff and exactly-once claims are conditional on F5/WC-060. Pre-gate controls remain absent or honestly unavailable. |
| SA-05 | Moderate | The AI SDK dependency decision remained delegated to future implementation. | `@ai-sdk/react` is not approved as an F3 architecture dependency. Reconsideration requires an approved canonical stream contract and a presentation-only adapter review. |
| SA-06 | Moderate | F5 referenced backend adversarial CCTs but lacked browser-visible checkpoint, failure, replay, downgrade, and Stop acceptance. | UX-CONT-01 through UX-CONT-06 now define the required UI and contract evidence. |

## Ownership Decision

- **Business Platform:** sole public REST/stream ingress; relationship truth; public conversation, continuity, consumption, and Founder facade contracts.
- **Professional Runtime:** internal professional execution, channel delivery, and session stream behavior; dedicated Emergency Stop path remains the only browser exception in this package.
- **Billing Engine:** internal billing, markup, trial-budget, and coupon behavior called through BP-owned public operations.
- **Web PWA:** server-authorized presentation and client interaction islands only; no business truth, private service URLs, model dispatch, or cross-channel commit.

## Remaining Gates

- INST-011 Product Owner review remains required.
- Missing service contracts keep F2, F3, F4, F5, F6, and F7 blocked as named in the decomposition.
- Platform IT Expert frontend skill lifecycle and independent EA activation review remain required.
- A separate Founder Action is required before any Phase B implementation.

## Verdict

After the corrections above, the architecture gives implementation offices unambiguous component and interface ownership without requiring them to invent service behavior. **WC-034 Phase A is APPROVED by INST-005. Implementation remains unauthorized.**