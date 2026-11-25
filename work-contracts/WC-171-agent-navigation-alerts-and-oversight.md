# WC-171 - Agent Navigation, Alerts And Oversight (Roadmap Iteration 4, Milestone M4) - GROOMED

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-171 |
| Office | Platform IT Expert (INST-010), with a single-pass Solution Architect review of the navigation declaration and the alert policy contract before build |
| Initiative | IB-171 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 4 of 6, milestone M4 |
| Founder assignment | 2026-11-25: customers get a main menu after login and then context menus for the selected agent; DMA has its own menus and screens and so does every other agent; the current common menus (marketplace, my agents, settings, alerts) stay common; "Blend this now and i will like this to go in WC171 which any ways work on alerts, along with carry-ins from earlier PRs." |
| Status | **GROOMED. Not authorized to build.** The Founder accepts the stories by merging this pull request; the build needs his explicit authorization in the session that starts it (BOOTSTRAP implementation gate). Every ledger row is PLANNED |
| Depends on | WC-170 merged (#644). The WC-170 Demo deployment and its read-back come first, because the WC-170 proof reports BLOCKED-BY-FLAG on gap B1 until this contract wires it |
| Controlling documents | [agent-experience-platform-architecture.md](../architecture/reference/agent-experience-platform-architecture.md) (sections 6.2, 6.4, 6.5: the agent declares, the server sends semantics and never layout), [hybrid-application-shell.md](../architecture/reference/ux/hybrid-application-shell.md), [hybrid-ui-acceptance-contract.md](../architecture/reference/ux/hybrid-ui-acceptance-contract.md), [PG-24 in the gap register](../architecture/reference/product/waooaw-product-gap-register.md), [WC-170](./WC-170-real-agent-work-end-to-end.md) gaps B1 to B10 |
| Agent instructions | [WC-170-agent-execution-instructions.md](./WC-170-agent-execution-instructions.md) apply unchanged (gate, plan first, technical decisions by the author, one Docker pass at the end, no sub-agent implementation) |
| Requirement ledger | [WC-171-requirements.yaml](./WC-171-requirements.yaml) |
| Constitutional basis | C-001, C-002, C-005, C-007, C-023, C-042, C-049, C-059, C-063, C-065, C-088 |
| Deployment | One Environment Deployment of Demo after the build merges |

## Why This Contract Exists

Three things block "problems are seen, alerted and resolved without database access" (M4), and one structural choice must be made before more agents arrive.

1. **There is no agent-specific navigation.** Every customer sees the same menu. Inside a hired agent, the workbench tabs are fixed by code (Overview, Goals, Capabilities, Decisions, Monitor, Work, Wallet, Evidence). The agent declaration has no field for menus or screens, and its schema refuses unknown top-level fields. The Founder wants a global customer menu plus an agent context menu, and wants DMA, and every later agent, to have its own entries and screens.
2. **There is no common alert behavior (PG-24).** Alerts exist as pieces: a customer alert feed, a billing threshold policy with its own deduplication, agent-declared alerts with their own channel lists, and operations alerts. Nothing decides materiality, channel, deduplication and escalation once for all of them. The 30 proactive messages a month are counted in the billing engine but nothing is allowed to send them yet.
3. **Operators still need the database.** The Founder cannot read or resolve a blocked WhatsApp message (one has been paging every 30 seconds on Demo, Meta error 131026), cannot read the work timeline or spend reconciliation, and has no operations screen.
4. **Carried-in defects.** WC-170 left the execution stream unwired (B1), the stop fences per process (B2), and two billing engine faults were found by the log scan (WC-169 G14).

The milestone is **M4: the Founder and administrators see, are alerted to, and resolve problems on Demo without database access, and a customer reaches an agent's own screens through a global menu and an agent context menu.** Platform-led rule: everything is stated agent-neutrally and proved with DMA plus one declaration-only fixture agent.

## What Grooming Found (verified in the repository on 2026-11-25)

| Area | Finding |
|---|---|
| Global menu | `web/components/shell/ProtectedAppShell.tsx` defines the customer links: My Agents, Marketplace, Alerts, Connections, Settings, and staff links (Key Vault, Pricing, Providers, Access) in the same list. Mobile bottom navigation shows only My Agents, Marketplace and Alerts. The account drawer holds Profile, Billing, Settings, Staff access, Switch account, Sign out. The Founder has a separate shell with two links |
| Agent context | `web/app/(application)/relationships/[relationshipId]/page.tsx` chooses the workbench or the employment workspace by relationship state. `WorkbenchShell.tsx` builds the tool list in code. Nothing reads a declaration |
| Declaration | `agent-experience-contract.v1.schema.json` has goal types, plan, operate, monitor, domain blocks, components, audiences, modalities, channel support and conformance scenarios, and `additionalProperties: false`. No navigation or surface field |
| Architecture rule | Section 6.5: tiers E0 kernel, E1 declarative, E2 registered domain block, E3 sandboxed embedded surface. Prohibitions: agent code in the kernel, **agent-defined layout**, model-generated markup. Section 6.4: the server sends semantics, never layout |
| Older navigation text | `constitutional-ux-vocabulary.md` (about lines 531 to 579) describes a Home and Profile primary navigation that differs from today's shell. It must be reconciled |
| Customer alerts | `CustomerAlertService` lists tenant alerts with versioned, idempotent read and acknowledge. The `/alerts` page and `AlertFeed` exist. Workbench Overview and Monitor show projection alerts |
| Alert policy | The billing alert policy deduplicates by customer, bucket, threshold and period and is billing-only. DMA declares three alerts (`MID_MONTH_PACE_BELOW_TARGET`, `CONSECUTIVE_MONTHLY_MISSES`, `COMPONENT_NEARING_EXHAUSTION`) each with its own channels. No common materiality or escalation |
| Proactive allowance | `src/billing-engine/meter/proactive_messages.py` counts a versioned 30 units per period idempotently, answers "deliver in portal" when exhausted, and records replies, capacity notices and emergency alerts as uncounted. Its own text says it does not enable sending; the thread rate `whatsapp_template_utility` is still awaiting the Founder's authorization (WC168-R015) |
| Blocked messages | `WhatsAppOutboxService` sets `BlockedReason` (provider reason or `PROVIDER_REJECTED`). `ConversationOperationsService` counts blocked rows and raises PAGE alerts at 15 and 30 minutes. **No route reads or resolves a blocked row** |
| Operator screens | No Founder or administrator screen shows signals, blocked rows, delivery or reconciliation. WC-134 monitoring is a Demo-only query and action group with no proof that a human received the alert |
| Carry-ins | WC-170 B1, B2, B6, B7, B8 (this contract); B3 accepted design; B4 named delegate (PG-07) and B9 Hindi wording are not carried unless the Founder places them; B5 and B10 go to WC-172. WC-169 G14: `audit_evidence_log` is written by a nightly reconciliation and no init file creates it; the scheduler's own `meter/daily-scan` call returned 503 |

## Objectives

| Id | Objective |
|---|---|
| O1 | A customer has one global menu for the platform and, after choosing an agent, a context menu for that agent: platform surfaces first, then the agent's declared entries |
| O2 | Navigation is declared by the agent as data and rendered by the platform; no agent changes shared web code, and no agent defines layout |
| O3 | One alert policy decides materiality, channel, deduplication, escalation and allowance for every alert source |
| O4 | The Founder and administrators run an operations console on Demo: blocked messages, signals, delivery, work and spend |
| O5 | The carried-in defects are closed, or each has a named owner and date |
| O6 | Slice 5 of the acceptance harness proves the above on Demo for a synthetic customer |

## Authority And Scope

In scope: the customer menu and agent context menu; the navigation declaration (an additive E1 field) and its admission validation; the DMA declaration and a declaration-only fixture agent; the alert policy contract and its enforcement for portal and WhatsApp; the proactive allowance wiring behind a Founder gate; customer alert controls; the operations console; the governed blocked-message read and resolve route; work and spend oversight read routes; the carried-in defects; slice 5 acceptance; documents the above change.

Out of scope: lifecycle and real money (WC-172), a real second agent (WC-173), email and SMS channels, a mobile app, real customers, UAT and production, `AD_BOOST`, changing prices.

Authority limits: no secret value is read or printed; no row is deleted (blocked messages are closed with a reason, never removed); no alert is muted to stop a page; WhatsApp proactive sending stays in sandbox recipients on Demo; the author does not merge or self-approve; any story that needs a shared-kernel change only DMA needs stops for the Founder.

## Proposed Navigation Model (for the Founder to confirm, decisions N1 to N3)

| Level | Content | Owner |
|---|---|---|
| **Global menu** (every customer, every agent) | My Agents, Marketplace, Alerts (all agents), Settings. Account drawer: Profile, Billing, Staff access, Switch account, Sign out. Mobile bottom bar: My Agents, Marketplace, Alerts, Menu | Platform |
| **Operations group** (staff and Founder only, by grant, never shown to customers) | Founder Home, Operations (new), Pricing, Providers, Key Vault, Access | Platform |
| **Agent context menu** (after choosing an agent) | Fixed platform surfaces, same order and wording for every agent: Overview, Plan, Decisions, Work, Results, Usage and budget, Alerts for this agent, Rights and control (Evidence, Stop). Then the agent's declared entries in its own words | Platform renders; agent declares |
| **DMA declared entries (proposed)** | Profile and maturity, Campaigns and calendar, Platform accounts (the Facebook, Instagram and WhatsApp connections), Business results | DMA declaration |

Rules: the agent supplies labels from its vocabulary, an icon from a closed set, an order hint and a surface kind; it never supplies markup, layout or code (architecture section 6.5). A declared entry opens one of: a kernel view, a composition of existing blocks (STATUS, METRIC, PLAN, DECISION, FORM, EVIDENCE), a registered domain block (E2), or a sandboxed surface (E3, needs a security review and is not built here). Founder decisions needed: **N1** accept the declared-entry model (the alternative, agent-owned web modules per agent, conflicts with section 6.5 and with M6); **N2** where Connections lives (proposed: inside the agent context for DMA, because it is DMA's required accounts; a platform "Connected accounts" overview stays under Settings); **N3** the staff links leave the customer menu for the Operations group.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC171-R001 | The global customer menu is identical for every agent, lists only platform concerns (My Agents, Marketplace, Alerts, Settings, account drawer), has mobile parity, and carries no staff link; staff and Founder links appear only in a separate Operations group shown by grant; old URLs keep working; a test proves a customer, a staff member and the Founder see exactly their own set |
| WC171-R002 | Choosing an agent opens a context menu with the fixed platform surfaces in a fixed order and wording, followed by the agent's declared entries; the surface is chosen per relationship, deep links address a surface, and the existing workbench tabs map onto the fixed surfaces with no lost function |
| WC171-R003 | The Agent Experience Contract gains an additive optional `navigation` field (entry id, vocabulary label key, closed icon set, order hint, surface kind, audience, availability gate); admission validation refuses unknown surface kinds, free text markup, duplicate ids and entries that open nothing; the schema, both copies of any affected specification, the generated client and the admission digest are updated together; a legacy declaration without the field still admits and shows only the fixed surfaces |
| WC171-R004 | DMA declares its entries (proposed: Profile and maturity, Campaigns and calendar, Platform accounts, Business results) over the WC-170 artifacts and the connection screens; a declaration-only fixture agent from another profession declares different entries and renders through the same code with no agent name in shared web or Business Platform code (the neutrality test also serves WC-173) |
| WC171-R005 | One alert policy contract (PG-24) states materiality classes, channel eligibility per class, deduplication keys, escalation ladder with timings, quiet hours as conversation policy, and which classes are uncounted floor alerts; every alert source (agent-declared, billing threshold, operations, spend discrepancy, stop) is classified into it; tests prove one material event produces one primary message and no conflicting second one, and that an agent cannot declare a class or channel the policy does not allow |
| WC171-R006 | Delivery follows the policy: portal always, WhatsApp only when the class, consent, quiet hours and allowance allow; the 30 proactive messages per subscription per month are consumed on send, idempotently, with "deliver in portal" when exhausted; replies, capacity notices and emergency alerts stay uncounted; sending is behind a Founder-controlled gate, to sandbox recipients on Demo, and only after the thread rate is authorized and a template is approved; STOP is respected |
| WC171-R007 | The customer alert experience: one inbox across agents with a per-agent filter inside the agent context, acknowledge, snooze and per-category mute, where floor alerts (Emergency Stop, authority and safety) can never be muted; read state survives retries; links open the surface the alert is about |
| WC171-R008 | An Operations console for the Founder and administrators, behind separate grants and tenant scoping, shows open signals, queue and blocked counts with ages, alert delivery outcomes and service health (replica readiness), with no database access and no payload content beyond what the role may see |
| WC171-R009 | A governed route reads and resolves blocked outbound WhatsApp messages: minimized read, resolution actions RETRY, CLOSE_WITH_REASON and MARK_UNDELIVERABLE, each audited, idempotent, step-up protected for the Founder role, tenant and environment scoped, never deleting; resolving the Demo message behind the repeating PAGE alert stops the alert without muting it, read back on Demo |
| WC171-R010 | The Founder and administrators can read a relationship's work timeline and the spend chain (authorizations, reservations, charges, reconciliation per item, open discrepancies) and resolve a discrepancy with evidence, through read routes and screens (closes WC-170 B7) |
| WC171-R011 | The Professional Runtime calls the execution stream, the Constitutional Engine step gate and the spend client from its running dispatch path so a Demo run produces timeline events (B1); the ingest compares the signed envelope's tenant with the body (B6); stop and unknown-outcome fences survive a restart and a second replica through the existing durable stop barrier (B2); the customer-route and ingest-route controllers have unit tests (B8) |
| WC171-R012 | The two billing engine faults of WC-169 G14 are investigated and fixed or recorded with an owner: the missing `audit_evidence_log` table and the 503 on the scheduler's own daily scan call |
| WC171-R013 | Every page or component changed here follows the visual system and UX vocabulary and passes the WC-167 R006 layers (Jest, Playwright at 360, 768 and 1440 in light and dark, axe, lint, strict types, production build, 90 percent changed-line coverage); UX-SHELL-03 and UX-RESP-03 pass for the new menus; `constitutional-ux-vocabulary.md` navigation text is reconciled with the shell |
| WC171-R014 | Acceptance slice 5 runs on Demo for a synthetic customer and an operator: global menu, agent context menu with DMA and fixture entries, an alert from each source delivered once, allowance exhausted to portal, a blocked message resolved, a discrepancy resolved, and one calibration report whose every NOT-WITNESSED or FAIL item has an owner; the coverage ratchet rises and never falls |
| WC171-R015 | Close-out: after the Demo deployment the WC-168 to WC-171 ledger rows are set from their read-backs, the `ROADMAP.md` progress record is refreshed, and PG-24 moves to SPEC_CLOSED with the proof pending |

## Epics And Groomed Stories

Size: S small, M medium, L large (relative). "Proof" is the slice 5 step in Epic H.

### Epic N. Navigation (R001 to R004, R013)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| N1 | As a customer I see the same global menu whatever agent I hired | My Agents, Marketplace, Alerts, Settings and the account drawer; no staff links; same on mobile; unknown or retired links redirect | Web | M | R001 |
| N2 | As a staff member or the Founder I find operator tools in one Operations group | Shown only by grant; Founder shell and customer shell never leak each other's links (UX-SHELL-03); Key Vault, Pricing, Providers, Access move here | Web, BP | M | R001 |
| N3 | As a customer I open an agent and see its context menu | Fixed surfaces in fixed order (Overview, Plan, Decisions, Work, Results, Usage and budget, Alerts, Rights and control) plus declared entries; deep link per surface; wallet hidden for a beneficiary audience as today | Web | L | R002 |
| N4 | As the platform I accept navigation as declared data | Additive `navigation` field; admission refuses unknown kinds, markup, duplicates, empty targets; legacy declarations still admit; specifications, generated client and digest updated together | BP, specs | M | R003 |
| N5 | As the DMA customer I reach profile and maturity, campaigns and calendar, platform accounts and results from the DMA context menu | DMA declares the four entries over WC-170 artifacts and the connection screens; Connections leaves the global menu per decision N2 | DMA declaration, Web | M | R004 |
| N6 | As the platform I prove another agent needs no shared-code change | A fixture agent from another profession declares different entries; the same code renders them; a grep test finds no agent name in shared web or BP navigation code | BP, Web | S | R004 |
| N7 | As a user on a phone, keyboard or screen reader I can use every menu | The WC-167 R006 layers at 360, 768, 1440, light and dark; focus returns to the opener; the older navigation text is reconciled | Web | M | R013 |

### Epic P. Alert policy and delivery (PG-24; R005 to R007)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| P1 | As the platform I classify every alert once | A policy contract with materiality classes, channels per class, deduplication keys, escalation ladder, quiet hours and the uncounted floor classes; the five sources are mapped; an agent declaring a forbidden class or channel is refused at admission | BP, specs | L | R005 |
| P2 | As a customer I get one message per event, not several | Deduplication across sources and channels; a spend discrepancy and its billing threshold do not both page; tests per scenario | BP | M | R005 |
| P3 | As the Founder I control proactive WhatsApp sending | Gate off by default; on only after rate authorization and template approval; sandbox recipients on Demo; the allowance is consumed on send, idempotently, with portal fallback when exhausted; STOP honored | BP, billing engine | L | R006 |
| P4 | As a customer I manage my alerts | One inbox, per-agent filter, acknowledge, snooze, per-category mute; floor alerts cannot be muted; deep links | BP, Web | M | R007 |
| P5 | As the platform I route DMA's three declared alerts through the policy | Each is classified, deduplicated, and delivered by the policy, with a test per alert | BP, DMA declaration | S | R005, R006 |

### Epic O. Operator oversight (R008 to R010)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| O1 | As the Founder or an administrator I see what needs attention | Operations overview: open signals, queue and blocked counts with ages, alert delivery outcomes, service readiness; separate grants; tenant scoped; no payload beyond role | BP, Web | L | R008 |
| O2 | As the Founder I read and resolve a blocked message | Minimized read; RETRY, CLOSE_WITH_REASON, MARK_UNDELIVERABLE; audited, idempotent, step-up, never deletes; the Demo message is resolved and the PAGE alert stops by itself | BP, Web | L | R009 |
| O3 | As the Founder I read the work timeline and the spend chain | Read routes and screens for events, authorizations, reservations, charges, reconciliation per item; discrepancy resolution with evidence | BP, billing engine, Web | L | R010 |
| O4 | As the Founder I am told when something pages me | Page delivery outcome is recorded and visible (delivered, failed, acknowledged); acknowledgement stops the escalation, not the signal | BP | M | R008 |

### Epic C. Carry-ins from earlier pull requests (R011, R012, R015)

| Story | Gap | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| C1 | WC-170 B1 | `SessionExecutor` dispatch calls the execution stream, step gate and spend client; a Demo run produces timeline events | PR | L | R011 |
| C2 | WC-170 B2 | Stop and unknown-outcome fences use the durable stop barrier; restart and second replica tests; a late success after a recorded stop is rewritten to HALTED by BP | PR, BP | M | R011 |
| C3 | WC-170 B6, B8 | Ingest compares the signed tenant with the body; unit tests for the customer-route and ingest-route controllers | BP | S | R011 |
| C4 | WC-169 G14 | Cause of the `audit_evidence_log` insert and the `meter/daily-scan` 503 read from Demo logs, then fixed or recorded with an owner | Billing engine, init chain | M | R012 |
| C5 | Close-out | After the deployment read-back the WC-168 to WC-171 ledger rows and the roadmap progress record are refreshed | Docs | S | R015 |

### Epic H. Proof

| Story | As the harness I ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| H1 | Run slice 5 on Demo | Steps: S21 global menu; S22 agent context menu (DMA and fixture); S23 alert from each source delivered once; S24 allowance exhausted to portal; S25 blocked message resolved by the operator; S26 discrepancy resolved; S27 operator sees page delivery | Harness | L | R014 |
| H2 | Report | One calibration report with an owner for every NOT-WITNESSED or FAIL; coverage ratchet rises; PG-24 SPEC_CLOSED with proof pending | Harness, docs | M | R014, R015 |

## Founder-Reserved Items

The author decides every technical point. Only these need the Founder:

| Item | When | What |
|---|---|---|
| Authorize the build | Before any code | Explicit words in the session that starts the build |
| N1 to N3 | At grooming acceptance | Confirm the declared-entry model, where Connections lives, and that staff links move to an Operations group |
| DMA entry wording | During the build | He is the DMA domain authority: labels of the four DMA entries |
| Rate and template | Before the proactive proof | Authorize `whatsapp_template_utility` on Pricing (Rates); choose and submit the WhatsApp utility template (his Meta login) |
| Who resolves blocked messages | At grooming acceptance | Proposed: the Founder resolves; administrators read only |
| Alert class wording and escalation timings | During the build | Proposed by the author, confirmed by him once on a single page |
| Deploy | After the build merges | One Environment Deployment of Demo |

## PR And Deployment Plan

| Step | What | Who |
|---|---|---|
| 1 | This grooming pull request (docs only) merges | Founder |
| 2 | WC-170 Demo deployment and read-back (slice 4 proof reports B1 as BLOCKED-BY-FLAG) | Founder deploys, author reads back |
| 3 | WC-171 build pull request: all stories, one Docker pass, state refresh, bound PR body | Author builds, Founder authorizes and merges |
| 4 | One Environment Deployment of Demo | Founder |
| 5 | Read back each requirement, run slice 4 again (B1 closed) and slice 5, record the calibration report and ledger rows in a short follow-up commit | Author |

## Journey Simulation (grooming review)

| Step | Expectation after the build | Risk found in grooming | Response |
|---|---|---|---|
| Customer signs in with two agents hired | Global menu is the same; each agent opens its own context menu | Menu is one list today, and staff links are mixed in | N1, N2, N3 |
| Opens DMA | Fixed surfaces, then DMA entries in the business's own words | No declaration field, schema refuses it | N4, N5 |
| A second agent is added | Different entries, no shared-code change | Agent-specific branches could creep into the web | N6 and the grep test |
| A campaign falls behind pace | One message in the portal, one on WhatsApp if allowed, none twice | Each source has its own channel and dedup today | P1, P2, P5 |
| The 31st proactive message | Delivered in the portal only | Accounting exists but nothing sends | P3 |
| A message is blocked | Operator sees it, resolves it, the page stops | No read or resolve route | O1, O2 |
| A spend discrepancy | Operator reads the chain and resolves with evidence | No read route | O3 |
| The agent works on Demo | Timeline events appear | Execution stream not wired | C1 |

## Gaps Found In Grooming And How They Were Fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The Founder's "DMA has its own screens" could be read as agent-owned web code | Architecture section 6.5 prohibits agent-defined layout and agent code in the kernel | FIXED: declared entries over platform surfaces and registered blocks, E3 only after review; decision N1 |
| G2 | The declaration schema refuses a navigation field | `additionalProperties: false` | FIXED: additive field and ripple in N4 |
| G3 | Staff links share the customer menu | `ProtectedAppShell.tsx` | FIXED: Operations group, N2 |
| G4 | The UX vocabulary navigation text is out of date | Older text describes Home and Profile | FIXED: reconciled in N7 |
| G5 | Alerts have no common policy | Five sources, separate dedup and channels | FIXED: P1 |
| G6 | The allowance counts but cannot send | Module text and release policy | FIXED: P3 gate; rate and template are Founder items |
| G7 | A blocked message can only be counted | No route in `WhatsAppOutboxService` or the operations service | FIXED: O2 |
| G8 | Page delivery to a human is not proved | WC-134 limits | FIXED: O4 |
| G9 | Ledgers of WC-167 to WC-170 still show PLANNED after merge | Ledger files on main | FIXED: C5 after read-back |
| G10 | The size is large | Four epics and the carry-ins | RECORDED: one pull request is planned; if the build proves larger, the author asks for a split at that point, in this order: Epic N and Epic C first, Epic P and O second |
| G11 | `ROADMAP.md` current-iteration lines are stale | Still say Iteration 1 | RECORDED: refreshed by C5 with the progress record |

## Stop Conditions

- The Founder has not authorized the build: no code.
- A story needs a shared-kernel change that only DMA needs: stop and ask the Founder.
- A proactive WhatsApp message would reach a non-sandbox recipient, or would send before the rate is authorized and the template approved: do not send.
- A fix would delete a blocked row, mute a page, or hide a symptom: stop.
- An operator view would show payload content beyond the viewer's role or another tenant's data: do not display it.
- An E3 embedded surface is needed: stop; it needs its own security review.

## Definition Of Done

Build pull request: every requirement has a ledger row with executable evidence; the single Docker validation pass is green on the commit gate commands; the pull request body is bound to the final commit. Post-merge qualification: the Founder deploys once, the Demo read-back is recorded, the slice 4 and slice 5 calibration report is attached to the ledger in a short follow-up commit; `ROADMAP.md`, README and PROJECT_STATE are updated at close; the Founder merges.

## Implementation Record

Groomed 2026-11-25 on branch `ib/171/groomed-alerts-menus-and-real-money` from `origin/main` at `1519cc8a` (PR #644 merged). Facts above were read from the repository by a read-only pass; no Demo read and no code was done. Not yet built.
