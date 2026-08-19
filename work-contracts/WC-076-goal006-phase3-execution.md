# WC-076 - GOAL-006 Phase 3 Execution

| Field | Value |
|---|---|
| Goal | GOAL-006 - Secure Autonomous Cloud Delivery Capability |
| Accountable owner | INST-009 - Platform Architect |
| Implementation executor | INST-010 - Platform IT Expert, Skill 17 |
| Authority | FA-052; requires an INST-013 authorization naming INST-010 and a later INST-010 Acceptance |
| Scope | P3-EX01 through P3-EX11 in dependency order |
| Status | BLOCKED - INST-010 authorization and Acceptance not yet recorded |

## Outcome

Deliver one signed exact-six release, qualify Demo and UAT with immutable-digest promotion, and
produce a dark-Production handover plan without activating customer traffic or Platform Operations.

## Execution

| Order | Work | Executor | Gate |
|---|---|---|---|
| 1 | P3-EX01 release-scan repair; P3-EX02 durable configuration; P3-EX03 Terraform identity outputs | INST-010 | Focused tests, impacted regression, independent review, Founder merge |
| 2 | P3-EX04 bootstrap OIDC verification | INST-009 with INST-007 review | Least privilege, exact subject, no client secret |
| 3 | P3-EX05 protected GitHub environments | Founder/admin | Orders 1-2 accepted; six protected environments |
| 4 | P3-EX06 signed exact-six release | INST-010 | Trusted-current-main release and immutable attestations |
| 5 | P3-EX07 through P3-EX10 Demo then UAT deployment and qualification | INST-009; independent QA confirms | Cost, recovery, security, digest and acceptance gates pass in sequence |
| 6 | P3-EX11 dark-Production plan and handover | INST-009 | No apply, traffic, activation or final Goal acceptance |

## Lightweight Evidence Rule

Code, tests and executable CI output are the primary evidence. Record only task status, immutable
commit/run/digest references and independent verdicts in this Work Contract or the PR; do not create
per-task evidence documents, duplicate pass reports or narrative handoff records.

## Definition Of Done

P3-EX01 through P3-EX11 are complete only when their executable gates and independent acceptance
pass. Founder-reserved actions remain unexercised. The executor may not self-review, approve or merge.