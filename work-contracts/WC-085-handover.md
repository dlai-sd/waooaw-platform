# WC-085 Start-Here Handover

**Date:** 2026-09-09. **State:** PARTIAL engineering work; no full story accepted.
**Executor:** Platform IT Expert, INST-010. **PR:** https://github.com/dlai-sd/waooaw-platform/pull/409 (draft).
**Authoritative plan:** [WC-085 Section 18](WC-085-wc084-remediation-and-evidence-closure.md#18-controlling-handover-and-execution-packages---2026-09-09).

## Location And Current Scope

- Worktree `/workspaces/waooaw-wc085`, branch `ib/085/remediation`.
- Original editor worktree `/workspaces/waooaw-platform` is on `ib/083/auth-dialog`; preserve its unrelated work.
- Pre-parking HEAD: `bff1bc7cd68252534071ec847be221b021cfdf5f`. Obtain final parked SHA from #409 and its Author Review.
- Founder authorized handover, deletion of Java experiment, and saving existing work only. No further feature implementation in the parking step.
- New session needs explicit bootstrap authorization, office assignment, package selection and implementation authorization. Neither this document nor G5 grants it.

## Fixed Decisions

Stock Keycloak authenticates. Existing C# BP provisions account/organisation/OWNER membership atomically.
Validated issuer/subject resolves current database membership. Each enabled downstream service validates
the original bearer and trusted service channel independently and uses its own database identity.
No custom Java, Keycloak writer, app-issued token, browser tenant authority, email-only relinking,
shared customer tenant, silent data reset or new membership service. C#/Python/JS/TS stack; Docker only.

The Java source/provider/probe has been deleted. Historical Java/security findings are retained only
as rejected-approach evidence. Never reconstruct that experiment from historical paragraphs.
Use CURRENT amendments in ADR-003, ADR-008, identity boundary, architecture/data/security contracts.
Section 18 of WC-085 overrides the older publication and pending-authoring instructions.

## What Is And Is Not Proven

Current local milestone: 203 backend tests passed, then 11 Program-host tests separately; 81 web tests
and TypeScript passed. Synthetic identity proofs and restricted-role PostgreSQL, not real Google.
See [attributed evidence](../test-results/wc085/final-evidence.md). Older build/browser/security evidence
belongs to its older source freeze. Do not reuse it as final current-source qualification.

Still open: full migration chain/recovery, real stock reader/TLS/claim configuration, supported portal
and downstream membership adoption, cross-tab cleanup, recreated identity continuity, current images/
scans, real Google acceptance and release gates. Unsupported customer endpoints currently deny.
Google readiness remains disabled. Facebook/email are Founder-deferred, not removed from all26 scope.
D-GOAL/D-BILLING/D-IDENTITY remain unaccepted. No deployment or cloud change was performed for parking.

## Next Session Prompt

The Founder may use the following prompt to authorize bootstrap and planning, without inadvertently
authorizing more implementation than selected:

> Occupy Platform IT Expert INST-010 for WC-085. I authorize bootstrap for this new session. Work in
> /workspaces/waooaw-wc085 on ib/085/remediation and existing draft PR #409; preserve the original
> worktree. Complete bootstrap once, declare Decision Space and obligations, then read WC-085 Section
> 18 and this handover. Use the compact office guidance and only the selected skill and task-owning
> files. Present H1 as the proposed first package and wait for my selection and explicit current-session
> implementation authorization. No Java, architecture invention, delegates or institutional reviewers.
> Docker-only execution. One bounded package at a time, immediate focused validation and at most two
> repair attempts after an initial failure. No broad rediscovery or repeated suite runs without new
> evidence. No cloud mutation, secrets through chat, expenditure, merge or provider activation.

After selection, the implementation authorization question remains: "This would begin writing
implementation code. Do you authorize this for the current session?" Do not infer that answer from
the bootstrap prompt. H1-H9, exact anchors, checks, dependencies and stop conditions are in Section 18.

## Cost Discipline

One primary implementer; ask a stronger model or another office only for a precise unresolved decision
and only with Founder approval. Verify the touched code, not the whole repository. Report concise
results and retain logs separately. Missing contract/credentials/authority is a named blocker, not an
invitation to design an alternative. Preserve draft status until the applicable gates and Founder
decision permit progression.