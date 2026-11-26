# WAOOAW Roadmap

**This is the only roadmap and the only progress record for platform delivery. Read it before proposing, planning or starting any work that is not already assigned by a Work Contract.**
Any change to the iterations, milestones, order, scope or Work Contract numbers below is a deviation and needs the Founder's written approval in the current conversation or on the pull request (section 8). Agents and offices never edit this file to suit their own plan.

| Field | Value |
|---|---|
| Authority | Founder (Yogesh Khandge), decisions of 2026-11-24 (section 6) |
| Document class | Class 3 Governed (GENESIS Decision Classification). Changes need Founder approval on top of normal pull request review. It cannot override a Class 1 or Class 2 decision |
| Strategy | **Platform-led, DMA-proved** |
| Current iteration | **Iteration 1 (WC-168)**: implementation authorized 2026-11-24, in progress |
| Last updated | 2026-11-26 |

## 1. The landscape in one page

- **WAOOAW is a platform where businesses employ autonomous digital professionals (agents) under constitutional governance.** The Founder and administrators run the platform; customers hire agents; agents perform inside the platform's rules.
- **Platform-led, DMA-proved.** We build the platform (operator screens, plumbing, monitoring, alerts, billing, lifecycle) one capability per iteration. Each iteration is done only when the Digital Marketing agent (DMA) runs through it end to end on Demo for a synthetic customer. A later iteration adds a second agent using declarations only, to prove the shared layer stayed agent-neutral.
- **Agents declare, the platform provides.** An agent supplies a declaration (goals, measures, packages such as Starter, Runner and Winner, alerts, conformance scenarios). The platform supplies everything else. Adding an agent must not need a change to the shared kernel.
- **Customer journey:** discover, trial or interview, hire and pay, connect accounts, the agent works, approve, see results, renew or stop.
- **One Work Contract per iteration, one sizable pull request per iteration, one Environment Deployment per iteration.** A repair pull request is allowed only when the Demo read-back fails.
- **A second track, Agent Operation (section 10), makes every agent usable by a customer: three modes (Induct, Goal Setting, Operations), a calendar as the background screen, and agent menus beside the WAOOAW menu. DMA is the first agent and the model stays generic.** It does not renumber or replace iterations 1 to 6.

### Which document governs what (do not invent another)

| Concern | Governing document |
|---|---|
| What an agent must declare, and what the shared platform provides | `architecture/reference/agent-experience-platform-architecture.md` (Agent Experience Contract, section 6.2; kernel and extension tiers, sections 5 and 6) |
| Customer rights and relationship across channels | `architecture/reference/product/agent-employment-experience-contract.md` |
| Behavior every agent inherits | `architecture/reference/agents/AGENT-BASE-SPEC.md` |
| Signals the platform sends to agents | `adr/ADR-035-platform-agent-contract-standard.md` |
| How the runtime calls an admitted agent | `adr/ADR-049-agent-runtime-adapter-transport-and-isolation.md` |
| Packages and pricing for DMA | `architecture/reference/billing/dma-bundle-definitions.md` |
| Shared product gaps PG-01 to PG-37 | `architecture/reference/product/waooaw-product-gap-register.md` |
| Customer journey acceptance on Demo | `architecture/reference/acceptance/customer-journey-acceptance-architecture.md`, ADR-054, ADR-055 |
| Settings, flags, staff roles | `standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md` |
| What each Work Contract delivers | `SPRINT-REGISTRY.md`, then the Work Contract file |
| Agent modes, calendar and the DMA customer journey | `work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md` (section 10 of this file) |
| Where the institution stands right now | `constitution/PROJECT_STATE.md` |

Historic planning (the GOAL files, WC-064 to WC-069 "Iteration 1 to 5" for the Founder commercial governance program, the August 2026 platform-first and customer-first sessions) is preserved and is **not** this roadmap. Its numbering is untouched. In this file "Iteration" always means the six iterations below.

## 2. Roadmap

| Iteration | Work Contract | Platform capability | Milestone | Status |
|---|---|---|---|---|
| 1 | WC-168 | One roadmap and a working operator console on Demo | **M1** Founder signs in and every operator screen works with DMA data | Implementation authorized 2026-11-24, in progress |
| 2 | WC-169 | Paid hire and connected accounts | **M2** Synthetic customer completes discover to connected accounts; one valid calibration report | In progress: built and verified locally in one Docker pass: conversation-table grants (R003), Founder step-up return fix (R016), package description, build-up and per-package margin (R017 to R019), one price source for the hire and no anonymous price (R013, R021). Waiting on the one WC-169 deployment: Meta secret save, acceptance run, coupon, Key Vault screen retirement. On hold by the Founder: R014 |
| 3 | WC-170 | Real agent work end to end (AE-02, PG-17 to PG-23) | **M3** DMA does approved, reconciled work for a synthetic customer | **Build authorized by the Founder 2026-11-25 and implemented in one pull request** (twenty-two stories, one Docker validation pass); one Demo deployment after it merges, then the slice 4 read-back and calibration report |
| 4 | WC-171 | Agent navigation, alerts and oversight (global customer menu plus agent context menus declared by each agent; PG-24 common alert policy; 30 proactive alerts a month; a governed route to read and resolve blocked WhatsApp messages; operations console; carry-ins WC-170 B1, B2, B6, B7, B8 and WC-169 G14) | **M4** Founder and administrators see, are alerted to, and resolve problems without database access, and a customer reaches an agent's own screens through a global menu and an agent context menu | **Groomed 2026-11-25** (docs only, build not authorized) |
| 5 | WC-172 | Safe to charge real customers (PG-26 lifecycle, tax invoices, payer and funder, price-change policy, closed money path WC-170 B5 and B10, UAT promotion, production readiness and the go-live gate) | **M5** Founder approval to take real money | **Groomed 2026-11-25** (docs only, build not authorized; real money needs the Founder's separate written go-live approval) |
| 6 | WC-173 | Platform proven by a second agent (PG-25, PG-31 to PG-34) | **M6** Second agent plays with no kernel change | Number reserved, contract not written |

Work Contract numbers WC-168 to WC-173 are reserved for this roadmap. All other work takes WC-174 or higher.

Later, after M6: more agents, multi-agent workplace, mobile, retiring legacy projections (PG-27 to PG-30, PG-35 to PG-37).

The Agent Operation track (WC-174, milestone AO-M1) sits beside this table, not inside it: see section 10.

## 3. What each milestone means

| Milestone | Done when (all of these) |
|---|---|
| M1 | WC-168 requirements read back on Demo; Providers lists providers; the Founder sets package names, features and prices at run time on the Pricing screen and authorizes them there (nothing seeded or hard-coded); Key Vault page follows the platform Founder grant; this file is the only roadmap and is pointed to from README, PROJECT_STATE, AGENT-ENTRY and BOOTSTRAP |
| M2 | Acceptance slices 1 and 2 run on Demo; the hire price comes from the Founder's authorized package, not the agent descriptor; vault holds 12 of 12 secrets; one calibration report with every NOT-WITNESSED or FAIL item owned; WhatsApp STOP can resume; Meta App Review and WhatsApp template submissions made |
| M3 | Founder accepted the groomed stories; a synthetic customer completes brief, approval, execution, spend reconciliation and results trace on Demo |
| M4 | Alerts, monitoring and exception handling work for Founder and administrators on Demo without database access; a customer reaches each agent's own screens through the global menu and the agent context menu, with the agent's entries declared as data and no shared-code change per agent |
| M5 | Lifecycle rights, pro-rata billing, payer and funder, tax invoices proven on Demo and UAT; the money path closed (evidence verified at its owner, key guards, reconciliation); UAT promotion done; production readiness checklist complete; Founder approves taking real money in writing and the capped rehearsal is read back |
| M6 | A second agent runs the same journey from declarations only |

## 4. How every iteration runs

1. **Groom ahead.** The next iteration's Work Contract lands as a docs-only commit inside the current pull request.
2. **Build.** All stories in one branch and one pull request, tested in Docker, hooks as usual. Implementation starts only after the Founder authorizes it for that iteration.
3. **Deploy.** The Founder runs one Environment Deployment of Demo after merge.
4. **Read back.** The agent reads Demo (logs, Azure CLI, Founder screenshots) and records each requirement as pass or fail in the Work Contract ledger.
5. **Prove.** A DMA synthetic-customer run through the acceptance harness.
6. **Close.** The progress record below, the ledger, README and PROJECT_STATE are refreshed in the same pull request or the repair pull request.

## 5. Progress record (update at iteration close, not in between)

| Iteration | Merged | Deployed | Read back | Proof run |
|---|---|---|---|---|
| 1 | no | no | no | no |
| 2 to 6 | no | no | no | no |

## 6. Founder decisions behind this roadmap (all 2026-11-24)

| Decision | Founder words |
|---|---|
| Strategy | "i will go with Platform-led, DMA-proved ... The shared layer stays agent-neutral, and every capability is tested by a real agent before it counts as done." |
| Direction | "I want to approach this from WAOOAW founder+administrator side ... we will build features and automation from founder+Administrative side ... and each agent will come and perform using this features and boundries." |
| One roadmap | "any waooaw office/agent session understand one clear and loud landscape of waooaw and it must understand only one roadmap and its current progress. Any deviation from it will need founders approval." |
| Size of work | "Lets not do small PRs and go after sizable work on in single PR" |
| Numbering | "lets not tourch historic stuff ... you will use next available number for work contract" |
| Order | "Does the ordering fit ... yes i am good" and "i am good with this" |
| Authorization to commit contracts | "Approve committing WC-168 and WC-169 in full and WC-170 as the gated skeleton ... Yes." |
| Agent operation: credentials (2026-11-26) | Consent and test instead of stored passwords: "yes" |
| Agent operation: modes (2026-11-26) | "gates but customer can easily hop among them" |
| Agent operation: calendar events (2026-11-26) | "the agent from research based on customer business profile. Customer can put their own events/placeholders" |
| Agent operation: scope and roadmap (2026-11-26) | "create a work contract covering full scope we are discussing" and "Approved. add next section in roadmap called WAOOAW Agent operation with DMA and create first milestone under it among with other required details in milestone document" |
| Agent operation: layout and conversation (2026-11-26) | Reference screens supplied "for inspiration on grouping, layout flow etc"; "dma agent conversation handy/visible all the time and context driven, guided dialouge. We expect maximum time customer to use AI driven outcomes." |

## 7. Constitutional compliance check of how this roadmap was decided

Run 2026-11-24 by the Platform IT Expert (INST-010) before committing. Result: **PASS with two stated limits.**

| Check | Finding |
|---|---|
| Who decided | The Founder, in conversation, with the words recorded in section 6. The agent proposed options with trade-offs and did not choose the strategy (C-064 Three-Human Institution; C-065 SDLC Separation of Duties) |
| Authority level | A roadmap is Class 3 Governed. It sets order of work, not architecture, so it needs no ADR and changes no Class 1 or Class 2 decision. The Founder's approval requirement for deviation is stricter than normal Class 3 review, by his decision |
| Authorization tier | Writing contracts and documents needs Founder approval, which was given. Writing implementation code is a separate gate (C-066, BOOTSTRAP implementation gate) and is not granted by this file |
| Separation of duties | The author does not approve or merge. The Founder merges (C-065) |
| Traceability | Every iteration maps to a Work Contract number and existing identifiers (PG, AE, WC, ADR) with no new vocabulary (C-059) |
| Evidence | Each iteration ends with a Demo read-back and a ledger, not an assertion (C-023 Evidence First) |
| Honest limits | Milestones M3 to M6 depend on ungroomed gaps (PG-17 to PG-37) and on outside lead times (Meta App Review, WhatsApp template, DMA domain input). They are plans, not promises (C-049 Honest Limitation) |
| Docker-only | All validation runs in Docker (C-080) |
| Limit 1 | Iteration 3 onward are outlines until groomed; the Founder must accept stories before build |
| Limit 2 | The single-source rule is enforced by a test for pointers and Work Contract files, not for the content of decisions; deviation control still depends on agents reading the pointer |

## 8. Deviation procedure

A deviation is any change to iteration order, scope, Work Contract numbers, milestones, the strategy, or starting work that is not in a listed Work Contract.

1. Stop. Do not start the deviating work.
2. Tell the Founder in one sentence what differs and why, with the cost of not deviating.
3. Proceed only on the Founder's written approval. Record it in section 6 and in the Work Contract.
4. If the Founder declines, continue on the roadmap.

Emergencies (security, production incidents, Founder-assigned urgent fixes) are handled under their own governance and recorded here afterwards as a one-line entry in section 9.

## 9. Deviation and change log

| Date | Change | Approved by |
|---|---|---|
| 2026-11-24 | Roadmap created | Founder |
| 2026-11-24 | Critical review of WC-168 to WC-170 (Founder asked for gaps to be fixed): a governed route for blocked WhatsApp messages placed in Iteration 4 (WC-171); WC-168 gains a Founder-reserved pricing input (R015); WC-169 gains a read-back of the Keycloak provisioning client (R012). Iteration order and numbers unchanged | Founder instruction to fix gaps; confirmation requested |
| 2026-11-24 | Founder confirmed the review changelog entry above, authorized WC-168 implementation including the temporary read-only Demo database catalog job, and decided that package names, features and prices are run-time Founder choices on the Pricing screen, never seeded or hard-coded ("include this in PR documentation and i approve PR") | Founder |
| 2026-11-24 | WC-169 work started while the Founder deploys WC-168. Founder decisions: the conversation tables the code uses are granted in WC-169 (R003; WC-170 R008 now only reads that back); reading the blocked WhatsApp message approved ("approved"; its cause is Meta error 131026 for one real number, parked as log noise and handed to WC-171 by WC-169 R015); production Meta secret reset chosen ("ok"); package names, features and prices stay Founder run-time choices and the price is to be derived from ingredient costs through a price calculator, discussed before WC-169 R013 code starts; no pull request until the Founder has seen the WC-168 deployment | Founder |
| 2026-11-24 | WC-169 work is bundled into one pull request and one Demo deployment (the step-up fix, R016, ships in it). Pricing decisions for the calculator design: packs and riders are top-ups on a hired agent only, no rollover for now, target margin set per pack; the hierarchy agent, skill, component with the skill pack as the thing sold awaits confirmation; `AD_BOOST` and the components to sell are on hold. WC-169 R015 was cut back to recording the blocked-message cause because its governed route belongs to WC-171 | Founder |
| 2026-11-24 | Pricing pivot: WAOOAW sells monthly hires of digital employees under maturity packages (Starter, Runner, Winner; names vary), not individual outcomes, packs or top-ups. A package has a name, a description, cost lines each with a margin, and one more margin on the total. Agent wiring is out of scope for now: the hire amount is picked from the Pricing screen (WC-169 R013). The earlier top-up, rider and expiry decisions are parked | Founder |
| 2026-11-25 | WC-170 groomed in full on a separate pull request: twenty-two stories, thirteen requirements, a controlling specification and agent execution instructions. The build is a later pull request needing the Founder's explicit authorization; Docker validation runs once after all stories; the Founder runs one Demo deployment only after the WC-170 build merges (not after the WC-169 follow-up pull request) | Founder (2026-11-25 instruction) |
| 2026-11-25 | WC-169 gains R022 (package editor usable in one view) and R023 (pricing writes survive a dead database connection) after the Founder's Demo read-back: the package screen was one 6,000-pixel column and creating a coupon draft returned 503 on a dead pooled connection that also recurs in the billing engine's scheduled sweep. Founder priority for the synthetic tester: the coupon and the price. Two further billing engine faults found by the log scan (a missing `audit_evidence_log` table, a 503 on the scheduler's own daily scan call) are recorded in the contract (G14) and not fixed. Founder delegated technical decisions to the author and allowed single-pass review by an office where needed | Founder |
| 2026-11-25 | Founder authorized the WC-170 build for this session ("I authorize the WC-170 build for this session"), with technical decisions delegated to the author, at most one single-pass office review, no sub-agent implementation, Docker validation once after the last story, no CI watching, no Azure or Demo change, no merge, and one Demo deployment by the Founder after the merge. Iteration order, scope and numbers are unchanged | Founder |
| 2026-11-25 | Founder asked to groom WC-171 and WC-172. WC-171 scope widened to include agent-scoped navigation (a global customer menu for every agent plus an agent context menu whose entries each agent declares, so DMA and later agents have their own menus and screens) together with the alert policy, the operations console and the carried-in defects of WC-170 (B1, B2, B6, B7, B8) and WC-169 (G14). WC-172 groomed as safe to charge real customers: PG-26 lifecycle, tax invoices, payer and funder, price-change policy, WC-170 B5 and B10, UAT promotion, production readiness and a separate written Founder go-live approval. Both contracts are docs only and build is not authorized. Iteration order and numbers are unchanged; WC-173 scope is reviewed later | Founder (2026-11-25 instruction) |
| 2026-11-26 | New track "WAOOAW Agent Operation with DMA" added as section 10, with its first milestone AO-M1 and Work Contract WC-174 (groomed, docs only, build not authorized). Scope: three modes for every agent (Induct, Goal Setting, Operations) with context menus, a calendar as the background screen, and the DMA customer journey as the first agent. Iterations 1 to 6, their order and their numbers are unchanged; WC-174 is the first number after the reserved range | Founder (2026-11-26: "Approved. add next section in roadmap called WAOOAW Agent operation with DMA and create first milestone under it") |

## 10. WAOOAW Agent Operation with DMA

**Purpose.** Iterations 1 to 6 build the platform around an agent. This track builds what a customer lives with: being known by the agent, setting goals skill by skill, and watching the agent work. It follows the platform-led, DMA-proved rule: the model is generic, DMA is the first agent, and a second agent proves it with a declaration only.

**Founder's model (2026-11-26).**

| Idea | Meaning |
|---|---|
| Three modes for every agent | **Induct** (the agent learns the customer and the sources it works from), **Goal Setting** (goals skill by skill, plans on a calendar), **Operations** (the agent works, the customer approves, results are watched and improved) |
| Gates, not locked doors | A mode shows what it still needs; the customer can open any mode at any time; a gate blocks only an action with a side effect, such as publishing |
| Calendar as the background screen | Each relationship has a calendar of events that matter to that customer; the agent proposes them from the business profile and the customer adds their own events and placeholders |
| Menus of the agent's own | The WAOOAW menu stays; the agent's context menu changes with the mode; every agent declares its entries as data |
| The agent's conversation always in view | The agent's conversation is docked beside the workspace in every mode, knows the context and guides the customer; customers are expected to spend most of their time on AI-driven outcomes, can hand any item over or take it back, and agent changes wait for acceptance |
| A grouped, planner-style workspace | Tools grouped in build order, choices that appear only when needed, one clear next step, a view switcher over one plan (month, week, platforms, storyboard) |
| Consent, never stored passwords | Platforms are connected by consent and tested; each platform is present, not present or not yet connectable |

**How it sits beside the iterations.**

| Question | Answer |
|---|---|
| Does it change iterations 1 to 6? | No. Order, numbers and milestones M1 to M6 are unchanged |
| What does it build on? | WC-171 (menus, alerts, operations console), WC-149 (customer account connection), WC-170 (real work and spend), WC-172 (lifecycle and billing) |
| Does it replace the second agent (WC-173)? | No. WC-174 proves the model with a declaration-only fixture agent; WC-173 later runs a real second agent on the same modes |
| Who decides what is in it? | The Founder, in the contract's reserved items (MD1 to MD5, lawful public sources, platforms, media providers, package activation) |

### Track table

| Milestone | Work Contract | Capability | Status |
|---|---|---|---|
| **AO-M1** | WC-174 | Modes, calendar and the DMA customer journey: induct, goals, plan, create, approve, publish, results | **Groomed 2026-11-26** (docs only, build not authorized) |

Later candidates, not planned and not promised: more connectors (YouTube, LinkedIn, Google Business Profile, the customer's own WhatsApp Business account), video and audio at scale, the second measurement bucket for work done outside WAOOAW, and a real second agent on the modes (with WC-173). Each needs the Founder to place it here first.

### Milestone AO-M1: what it means

| Part | Done when (all of these) |
|---|---|
| Contract | WC-174 groomed with 32 requirements and a ledger; the Founder confirmed MD1 to MD9 |
| Workspace and conversation | The workspace follows the grouped layout; the DMA conversation is docked and context driven in every mode and view; every outcome can be reached by asking or by tools with the same evidence; suggestions wait for acceptance; items can be handed over and taken back; the share of AI-driven outcomes is measured |
| Modes and menus | Any agent declares three modes as data; the customer opens any mode at any time with a readiness line; gates block only side-effect actions; a declaration-only fixture agent renders its own modes through the same code |
| Calendar | A shared calendar is the base screen; DMA proposes events from the confirmed profile; the customer adds, edits and hides events and placeholders; sensitive categories stay off until chosen |
| Induct | A focused conversation confirms the business as labels; every platform is answered (present, not present, connected and tested, or not yet connectable); a connected tester account is tested; the maturity report is read and confirmed |
| Goal setting | Goals for Profile, Content Planner, Content Creation, Publishing and Operations, each with baseline, target, evidence source, cadence and authority state; a month planned as master theme, weekly themes, individual themes and stories |
| Operate | Approved content is created per platform, approved by exact version and published to a connected sandbox account within the package; results are read against the goals; a monthly digest is produced |
| Proof | The build merged, one Demo deployment, every requirement read back, acceptance slice 6 passed for a synthetic customer with one calibration report whose open items have owners |
| Limits | No real customers and no real money (WC-172's separate written go-live approval still governs); connectors beyond Meta, media providers and public registries only where the Founder's decisions and outside approvals exist; anything not yet possible says so on screen |

### How the track runs

The same six steps as section 4 apply: groom ahead, build in one sizable pull request (the contract states a clean split order if the build proves too large), one Environment Deployment of Demo, read back, prove, close. The build starts only when the Founder authorizes it for this contract.

### Track progress record (update at milestone close, not in between)

| Milestone | Merged | Deployed | Read back | Proof run |
|---|---|---|---|---|
| AO-M1 | no | no | no | no |
