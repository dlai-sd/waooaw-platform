# WC-170 - Real Agent Work End To End (Roadmap Iteration 3, Milestone M3) - GROOMED

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-170 |
| Office | Platform IT Expert (INST-010), with a single-pass Solution Architect review of the data contracts |
| Initiative | IB-170 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 3 of 6, milestone M3 |
| Founder assignment | 2026-11-24: "WC-170 as the gated skeleton ... Yes." 2026-11-25: "groom 170 to full extent and give it on new PR with agent instructions to plan and proceed as per plan, to do docker testing at end of implementation instead of after each story" |
| Status | **BUILT in one pull request (this one), awaiting the Founder's review and merge.** Founder authorization to build: 2026-11-25, in the session that built it. The one Demo deployment, the read-back and the slice 4 calibration report follow the merge; until then every row of the ledger is PLANNED, not PASS |
| Depends on | The Demo environment as left by WC-168 and WC-169. The one Demo deployment now happens after the build merges (Founder, 2026-11-25), so the WC-169 follow-ups ride in it |
| Controlling specification | [ae02-real-work-solution-contract.md](../architecture/reference/product/ae02-real-work-solution-contract.md) |
| Agent instructions | [WC-170-agent-execution-instructions.md](./WC-170-agent-execution-instructions.md) |
| Requirement ledger | [WC-170-requirements.yaml](./WC-170-requirements.yaml) |
| Constitutional basis | C-001, C-002, C-005, C-007, C-023, C-049, C-059, C-063, C-065, C-088, C-089 |
| Deployment | One Environment Deployment of Demo after the build merges |

## Why This Contract Exists

The customer pays for agent work: a profile and maturity baseline, a campaign brief they approve, drafts they decide on, a status timeline, spend that reconciles, and results they can trace to work (AE-02, PG-17 to PG-23). The milestone is **M3: DMA does approved, reconciled work for a synthetic customer on Demo**, in sandbox and test mode only.

The DMA domain authority is the Founder himself (`goals/GOAL-005-f4-dma-domain-authority-input.md`); Sujay joins after the platform is operational. The platform-led rule applies: every capability is stated agent-neutrally and proved by DMA, and nothing that only DMA needs enters a shared owner without the Founder's written approval.

## What Grooming Found (verified in the repository on 2026-11-25)

The skeleton assumed most of this had to be built. Most of the **agent** side is built and dark; the **platform** side is partly built and switched off. WC-170 is therefore mainly activation, three missing platform capabilities, and proof.

| Area | On `main` today | Dark or missing | Evidence |
|---|---|---|---|
| Employment workspace (phases, readiness, plan versions, commands) | Built (WC-113 to WC-115): `getEmploymentWorkspace`, phases, readiness, `plans/current`, `commands`; web page "Induct, plan, operate and review" | **Off.** `EmploymentProtocol:Enabled=false`; Demo never sets it; the page says "Conversational employment is not available" | `appsettings.json`; `ConversationalEmploymentController.cs` (gate); `ConversationalEmploymentWorkspace.tsx` |
| DMA Skills 0, 1, 2: profile, maturity (ten dimensions), planning, calendar | Built (WC-116): manifest, induction, plan validation, maturity scoring, outcome adapter | Default off; never run on Demo | `employment-interface-manifest.v1.json`; `digital_marketing/employment.py` |
| DMA content production and publication | Built (WC-117 B1, B2) and a simple Page publish proven by acceptance slice 2 plan | Agent-driven publication never run on Demo | `content_service.py`; `slice-2-publish.v1.yaml` |
| Paid demand, leads, scale (WC-118) | Code present; contract status still "candidate" | No sandbox proof; `AD_BOOST` is UNAVAILABLE; real spend belongs to Iteration 5 | `paid_demand.py`, `lead_management.py`; `experience-components.v1.json` |
| Locked artifact | Runtime Intent Crystallizer and `LockedArtifact` (ADR-043) | No customer read model of the artifact that controls execution | `professional-runtime/intent_crystallizer.py` |
| Approval and scope confirmation | Commands `SUBMIT_PLAN_FOR_REVIEW`, `ACCEPT_PLAN_VERSION` | Scope-boundary confirmation is not a separate closed command or record | `ConversationalEmploymentService.cs` |
| Domain vocabulary | `vocabularyRef` (contract, version, digest) in the manifest | No runtime resolution of `{DVE.*}` tokens found in code | `employment-interface-manifest.v1.json`; search of `src` |
| Execution timeline | A conversation timeline exists | No execution action timeline with the six states | `ConversationExperience.tsx`, `PortalInteractionService.cs` |
| Evidence | Relationship evidence service and an evidence window | No outcome-claim to work to evidence trace | `RelationshipEvidenceService`, `WorkbenchProjectionService.cs` |
| Monitor tiles | Declared in the DMA manifest (`experience.monitor.tiles`) | Web does not render them | manifest; search of `web/components/relationships` |
| Spend | WBE wallet, reservation and charge exist; `ad_spend_meta` is a thread | No authorization-to-reconciliation chain for external spend | WC-134, WC-118; `billing-engine/reconciliation` |
| Stop | Proven for the relationship (AE-01-S10) | Not proven while agent work is executing | acceptance baseline |

## Objectives

| Id | Objective |
|---|---|
| O1 | The employment protocol is switched on for Demo behind a measured, reversible gate, and the agent, model key and capacity are read back |
| O2 | The customer receives and confirms a profile and a maturity baseline, in business language, from locked artifacts |
| O3 | The customer approves a campaign brief and, separately, confirms the scope boundary; no consequential step runs without both for the exact version |
| O4 | The customer sees execution status and an action timeline in six states, including unknown outcomes and halts |
| O5 | The customer traces every outcome claim to work and evidence; activity is never shown as outcome |
| O6 | Spend is authorized, attributable, reconciled and funded; sandbox only; a discrepancy blocks new spend |
| O7 | Business measures lead the monitor view; technical metrics support |
| O8 | A synthetic customer completes the whole chain on Demo and one calibration report records it |

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC170-R001 | Demo switches the employment protocol on and off through a gate with a rollback epoch, with a read-back from the deployed app; raising the epoch blocks in-flight commands with evidence and rewrites no history (A1) |
| WC170-R002 | The agent is provably able to run: exact admitted inventory and protocol bound, a model provider key configured and reported without its value, runtime capacity ready; any miss is a named BLOCKED-BY-FLAG reason (A2) |
| WC170-R003 | The conversation stories run: the web switch is on by the Founder's decision and a read-only catalog read confirms the four tables granted by WC169-R003 (A3) |
| WC170-R004 | Domain vocabulary resolves for each agent from its own bound vocabulary and digest with no agent branch in shared code, proven with a second profession (B1, DC-1) |
| WC170-R005 | The customer sees and governs locked artifacts (profile, maturity report, campaign brief, calendar): immutable versions, successor on change, approval bound to the exact digest, and every execution step names the artifact it runs under (B2, B3, C1, DC-2) |
| WC170-R006 | Approval and scope-boundary confirmation are two separate steps with two records; a consequential step needs both for the exact version; drafts and corrections never inherit approval (C2, C3, DC-3) |
| WC170-R007 | One execution timeline per relationship shows six states, unknown outcomes reconciled, and publication as completed only after verified provider evidence (D1, D2, D3, DC-4) |
| WC170-R008 | Every outcome claim traces to work items and evidence; agent-stated figures are labelled; activity is never shown as a business result; business outcomes that cannot be measured yet say so (E1, E2, DC-5) |
| WC170-R009 | External spend is authorized before dispatch, reserved before spend, charged on verified proof, funded by the right account, and reconciled; a discrepancy blocks new spend; sandbox only (F1 to F4, DC-6) |
| WC170-R010 | Emergency Stop halts agent work mid-execution, the timeline shows it, no late success appears, evidence exists, and other relationships are unaffected (G1, C-001) |
| WC170-R011 | Monitor tiles declared by the agent render with business measures first, stale tiles marked, and audience rules applied (E3, DC-7) |
| WC170-R012 | Acceptance slice 4 runs on Demo with the synthetic customer and produces one calibration report with an owner for every failure (H1) |
| WC170-R013 | Coverage and the gap register are updated honestly: the acceptance ratchet may rise and never fall, and PG-17 to PG-23 move to SPEC_CLOSED with proof pending until the report (H2) |

## Epics And Groomed Stories

Size: S small, M medium, L large (relative). Every story names the one owner of its data and what the customer sees. "Proof" is the acceptance step in the new slice 4 plan (see Epic I).

### Epic A. Activation and readiness (prerequisite for everything)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| A1 | As the Founder I switch the employment protocol on for Demo and off again without losing data | With `EmploymentProtocol__Enabled=true` and the expected gate id, a hired DMA relationship's workspace returns phases and readiness; with it `false` the route returns the closed not-accessible answer and the page says so; raising `RollbackEpoch` makes an in-flight command resolve to a closed blocked outcome with evidence and rewrites no history; read-back from the deployed app, not from a setting | BP | M | R001 |
| A2 | As the Founder I know the agent can actually run | The compatibility start binds the exact admitted agent inventory and protocol version and fails closed on mismatch; AIR reports that a provider key is configured without revealing it; PR, AIR and the DMA app report ready replicas; any miss is a named `BLOCKED-BY-FLAG` reason in the report, never a silent pass | BP, AIR, PR | M | R002 |
| A3 | As the Founder I turn the conversation stories on | The web `WC120_CONVERSATION_ENABLED` switch is on by the Founder's decision; a read-only catalog read after deployment shows the four tables granted by WC169-R003; acceptance conditional stories AE-02-S02 and S03 run instead of staying blocked | Web, BP | S | R003 |

### Epic B. Profile and maturity baseline (AE-02-S02; PG-17, PG-18, PG-23)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| B1 | As a customer I read the agent's output in my business's own words | `{DVE.TOKEN}` references resolve from the vocabulary bound to the admitted agent version; a digest mismatch fails closed; an unknown token shows as a named gap with a recorded limitation, never blank; a second profession fixture resolves a different vocabulary through the same code with no agent branch | PR, shared runtime | M | R004 |
| B2 | As a customer I see and confirm my business profile | A `PROFILE_CONFIRMATION` work item produces a locked artifact projection (id, version, digest, status, summary, limitations); I confirm it; a change creates a successor that does not inherit confirmation | BP, PR | M | R005 |
| B3 | As a customer I receive a maturity baseline I can trust | The ten-dimension scorecard shows scores 1 to 10 only for dimensions with evidence; missing evidence reads "not enough information", never a low score; publication of the score needs coverage of at least seven dimensions (WC116-R011); the screen shows evidence and limitations per dimension; the block is `MARKETING_MATURITY_SUMMARY` with its text fallback | DMA adapter, BP | M | R005 |

Founder note recorded for later (not built here): the maturity scorecard is what will tell a customer which monthly package (Starter, Runner or Winner) suits them. WC-170 only shows the score; mapping a score to a package is a Founder decision and part of the pricing roadmap.

### Epic C. Campaign brief and decisions (AE-02-S03, S04; PG-18, PG-19)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| C1 | As a customer I approve a campaign brief that controls the work | The agent proposes a `CAMPAIGN_BRIEF` as a locked artifact; the screen shows the exact brief the work will run under; approving binds that version's digest; any edit is a successor version needing a new approval; every execution step names the artifact id and digest and CE refuses a step whose artifact is not locked or whose digest differs | BP, PR, CE | L | R005 |
| C2 | As a customer I make two separate decisions: approve, then confirm scope | Approval ("do you approve this exact version?") and scope-boundary confirmation ("is it within what this agent may do, and who may do it?") are two steps with two labels, two states and two evidence records; the new closed command `CONFIRM_SCOPE_BOUNDARY` is added to the command discriminator; a consequential step runs only when both exist for the exact version | BP, CE | M | R006 |
| C3 | As a customer I review drafts and assets and correct them | Drafts and assets show as immutable versions with digests; a correction creates a successor and never inherits approval; approval binds the exact draft digest; the authority boundary of each action is shown (WC-117 R014 to R015) | BP, DMA adapter | M | R006 |

### Epic D. Execution status and timeline (AE-02-S04, S05; PG-20)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| D1 | As a customer I see what the agent is doing and has done | One timeline per relationship, one plain sentence per event, six states (proposed, approved, executing, completed, failed, halted); events carry artifact id and digest and evidence references; replay and reorder resolve to one logical event; reads are tenant-scoped | PR (stream), BP (projection) | L | R007 |
| D2 | As a customer I am told when the outcome is unknown | `UNKNOWN_OUTCOME` is a visible state that is reconciled, never retried blindly; the reconciled result replaces it with evidence | PR | M | R007 |
| D3 | As a customer I see publication as work, with proof | A published post appears on the timeline as completed only after verified provider evidence (the provider's post reference); accepted or receipt-only stays "in progress"; no token appears in any response | PR, BP | M | R007 |

### Epic E. Outcomes and evidence (AE-02-S05; PG-21, PG-23)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| E1 | As a customer I trace a result claim to the work behind it | Selecting a claim (for example "4 posts published this month") lists its work items and evidence; a claim with no work item and no evidence is not shown as an outcome; an agent-stated figure is labelled as agent-stated and never shown as a business result | BP, DMA adapter | L | R008 |
| E2 | As a customer I never mistake activity for a business result | Work completed (posts published, plans approved) is shown separately from business outcomes; business outcomes that need integrations that do not exist yet (qualified enquiries, confirmed visits, conversion) show "not measurable yet", never a number | BP, DMA adapter | M | R008 |
| E3 | As a customer I see business measures first | Monitor tiles declared in the manifest render: outcome tiles first, professional-performance second, technical telemetry only behind a details control; a stale tile shows as stale; a tile the audience may not see is absent | Web, BP | M | R011 |

### Epic F. Spend and funding (PG-22; C-088, C-089)

Sandbox and test mode only. `AD_BOOST` stays unavailable; WC-170 never spends real money.

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| F1 | As the platform I authorize spend before any spend | A `SpendAuthorization` (ceiling, funding account, window, artifact id and digest) exists only after approval and scope confirmation for the exact version; no authorization means no dispatch | WBE, CE | M | R009 |
| F2 | As the platform I reserve before I spend and charge on proof | A reservation exists before dispatch; a charge is written only after verified provider evidence; a provider-reported figure is stored as an observation with its reference | WBE, PR | M | R009 |
| F3 | As the Founder I see spend reconcile or break | A `ReconciliationResult` per relationship and period is `MATCHED`, `WITHIN_TOLERANCE` or `DISCREPANCY`; a discrepancy blocks new spend for that relationship until resolved and shows to the Founder; proven with the provider emulator | WBE | M | R009 |
| F4 | As the platform I never run unfunded work | Platform-owned work is funded from the platform account and hired work from the customer's; a work item with no funding account does not run and says why | WBE, PR | M | R009 |

### Epic G. Stop while working (C-001)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| G1 | As a customer I stop the agent mid-work | Emergency Stop during an executing work item halts it; the timeline shows `HALTED` with `EMERGENCY_STOP`; no late success is shown afterward; evidence exists; another relationship is unaffected | PR, CE, BP | M | R010 |

### Epic H. Proof

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| H1 | As the Founder I get one honest report of the synthetic customer's real-work journey | Acceptance slice 4 (new plan) runs steps S12 to S20 below on Demo with the synthetic customer and witnesses; the calibration report lists every step PASS, FAIL or BLOCKED-BY-FLAG with an owner for each failure | Harness | L | R012 |
| H2 | As the Founder I see coverage and gaps close honestly | `live-scope.yaml` and the coverage baseline add AE-02-S02, S03 and S04 once their steps pass (the ratchet may rise, never fall); the gap register moves PG-17 to PG-23 from UNGROOMED to SPEC_CLOSED with the proof pending until the report | Harness, docs | S | R013 |

Slice 4 steps (the plan file is written in the build): S12 confirm profile; S13 read the maturity baseline; S14 approve the campaign brief; S15 confirm the scope boundary; S16 review a draft; S17 execute and read the timeline; S18 trace an outcome claim; S19 authorize, reserve, charge and reconcile sandbox spend; S20 stop mid-work and read the monitor tiles.

## Founder-Reserved Items

The author decides every technical point. Only these need the Founder:

| Item | When | What |
|---|---|---|
| Authorize the build | Before any code | Explicit words in the session that starts the build (BOOTSTRAP gate) |
| AI provider key | Before the proof | Save an AI provider key on Providers after step-up; the platform funds platform-owned model use |
| Switch the web conversation flag | Before the proof | Decision recorded in the build pull request (A3) |
| Domain input | During the build | Confirm the wording of the ten maturity dimensions and the campaign brief fields as the customer sees them; the Founder is the domain authority |
| `AD_BOOST` | Not in this contract | Stays unavailable; any change is a separate Founder decision |
| Deploy | After the build merges | One Environment Deployment of Demo |

## Build Plan (one pull request)

Work packages are in dependency order. They are implemented together; Docker validation runs once at the end (see the agent instructions).

| WP | Content | Stories |
|---|---|---|
| WP1 | Activation settings, admission and readiness checks | A1, A2, A3 |
| WP2 | Vocabulary resolution, artifact projection, decision steps and drafts | B1, B2, B3, C1, C2, C3 |
| WP3 | Timeline, unknown outcomes, publication as work, stop while working | D1, D2, D3, G1 |
| WP4 | Outcome trace, activity versus outcome, monitor tiles | E1, E2, E3 |
| WP5 | Spend authorization, reservation, charge, reconciliation, funding | F1, F2, F3, F4 |
| WP6 | Slice 4 acceptance plan and steps, coverage ratchet, gap register, calibration report, documents | H1, H2 |

## Journey Simulation (grooming review)

Customer: connected, agent proposes, customer confirms and approves, agent works, customer sees status and spend, results, stops.

| Step | Expectation after the build | Risk found in grooming | Response |
|---|---|---|---|
| Open the workspace | Phases and readiness show | Protocol is off on Demo | A1 |
| Confirm profile, read maturity | Locked artifacts and a scorecard with limitations | No vocabulary resolution; missing evidence could read as a low score | B1, B3 |
| Approve a brief | Exact version bound | No customer view of the artifact that controls execution | B2, C1 |
| Confirm scope | A separate step | Not a separate command or record | C2 |
| Agent works | Timeline events | No execution timeline | D1 |
| Publish | Completed only on provider proof | Receipt could be shown as success | D3 |
| Results | Claims trace to evidence | No trace; activity could be shown as outcome | E1, E2 |
| Spend | Authorized, reserved, charged, reconciled | No chain; discrepancy handling undefined | F1 to F4 |
| Stop mid-work | Halted, no late success | Not proven while executing | G1 |

## Gaps Found In Grooming And How They Were Fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The skeleton assumed the agent side had to be built | WC-113 to WC-118 are merged and the DMA code exists | FIXED: the scope is activation, three missing platform capabilities (timeline, trace, spend chain) and proof |
| G2 | The employment workspace is off on Demo and nobody owned switching it on | `EmploymentProtocol:Enabled=false`; no Demo setting | FIXED: A1 |
| G3 | No runtime vocabulary resolution | No `{DVE.*}` resolution in `src` | FIXED: B1 with a two-profession proof |
| G4 | Approval and scope confirmation are not separate | Only plan commands exist | FIXED: C2 |
| G5 | No execution timeline or outcome trace | Searches of `src` and `web` | FIXED: D1, E1 |
| G6 | Monitor tiles are declared and not rendered | Manifest versus web components | FIXED: E3 |
| G7 | Business outcomes (qualified enquiry, confirmed visit, conversion) need integrations that do not exist | Domain input and WC-118 status | FIXED: E2 shows "not measurable yet", never a number |
| G8 | Funding per step was undecided | R009 of the skeleton | FIXED: F4 |
| G9 | The sequence changed: one Demo deployment after the build | Founder, 2026-11-25 | FIXED: the proof runs after that deployment; WC-169 follow-ups ride in it |
| G10 | The size is large | Twenty-two stories | RECORDED: one pull request is planned (Founder prefers sizable PRs); if the build proves larger, the author asks for a split at that point, not before |

## Stop Conditions

- The Founder has not authorized the build: no code.
- Any step would spend real money, contact a real customer or use a provider account the Founder has not approved (approved test assets and the configured AI provider are allowed): stop.
- A story needs a change to the shared kernel for DMA only: stop and ask the Founder (platform-led rule).
- A claim cannot be traced to work and evidence: do not display it.
- Protocol activation would run without the rollback epoch and a read-back plan: do not switch it on.

## Definition Of Done

Build pull request: every requirement has a ledger row with executable evidence; the single Docker validation pass at the end of the build is green on the commit gate commands; the pull request body is bound to the final commit. Post-merge qualification: the Founder deploys once, the Demo read-back is recorded and the slice 4 calibration report is attached to the ledger in a short follow-up commit; `ROADMAP.md`, README and PROJECT_STATE are updated at close; the Founder merges.

## Implementation Record

Grooming completed 2026-11-25 on branch `ib/170/groomed-stories` from the repository state at `main` after PR #641. The data contracts are in the controlling specification. A single-pass Solution Architect review of the data contracts is recorded below.

Review record (single-pass Solution Architect review, 2026-11-25, read-only): ten findings, all repaired in this pull request.

| Finding | Repair |
|---|---|
| Vocabulary reference may not point at the vocabulary; no business-domain selector | DC-1 now requires the build to confirm the section and adds a tenant-scoped domain selector; test with two businesses on one agent |
| `LockedArtifact` has no version, digest or status; stub approval possible; artifact-for-every-step is circular | DC-2 adds an owner-side version lifecycle, refuses stub approval, and exempts the artifact-creating steps |
| Scope confirmation bound only to the Decision Space; `ACCEPT_PLAN_VERSION` accepts plans only | DC-3 binds both records to artifact id and digest, adds `ACCEPT_ARTIFACT_VERSION`, states schemas and owner checks |
| Emergency Stop did not fence dispatch | DC-4 fences dispatch in PR and records late provider results as evidence, never as success |
| Spend ceiling, replay and uncertain reservation unspecified | DC-6 makes ceiling check and reservation one atomic wallet operation, idempotent, uncertain reservations settled by reconciliation |
| Outcome claim allowed with only work or only evidence | DC-5 requires both; activity versus outcome and "not measurable yet" are testable |
| Six states versus an unknown seventh; append-only versus replace | DC-4 keeps six states, makes unknown a reason code, reconciliation appends |
| Definition of done required deployment before merge | Split into build pull request and post-merge qualification |
| Stop condition banned every provider account | Approved test assets and the configured AI provider are allowed |
| Ledger digest stale | Recomputed after the repairs |

### Build record (2026-11-25, one pull request, Docker validation once)

The Founder authorized the build in the session that did it, delegated every technical decision to the author, allowed one single-pass office review and no sub-agent implementation, and set the order: all stories first, one consolidated Docker pass, no CI watching, no Azure or Demo change, no merge. The work is on branch `ib/170/real-agent-work-end-to-end`, cut from `main` at `843719eb`.

**Preconditions read before coding (read-only; nothing assumed)**

| Precondition | What was read | Result |
|---|---|---|
| Employment protocol setting | `appsettings.json`, Terraform feature settings, `infrastructure/platform-settings/demo.json` | Default `false` and Demo never set it. The build adds three closed settings (S9 of the settings policy) and Demo sets them. The deployed value is read back only after the Founder's deployment |
| Admitted DMA version | The admission fixture the deployment workflow digests, and the offerable projection the readiness route reads | The fixture is `digital-marketing-local-service-v1.0.0`. Whether Demo has it offerable is read back from the readiness route, never assumed |
| Model provider key | Not readable by this session and not read | Reported as `MODEL_KEY_NOT_CONFIGURED` until the Founder saves the key on Providers (Founder-reserved); the readiness route reports presence only |
| Conversation tables | `99zzzzzzzz-wc169-01-conversation-context-media-runtime-access.sql` | The four grants are in the repository; the Demo catalog read-back is after the deployment |

**Technical decisions (author's; the Founder was not asked)**

| Area | Decision and why |
|---|---|
| One record store | One append-only table `business.real_work_records` (artifact, lock, supersession, decision, timeline event, claim) with forced row-level security and an advisory lock per relationship, instead of five tables: nothing is updated, so no history can be rewritten, and projections fold records in sequence order |
| Decisions use the one command pipeline | `ACCEPT_ARTIFACT_VERSION` and `CONFIRM_SCOPE_BOUNDARY` are added to the closed command discriminator and the generated web client; BP checks the exact artifact digest, CE records the evidence, the approval locks the version, and scope confirmation needs the locked version first. The web posts them through the same fresh-strong-sign-in command route |
| Rollback epoch | The epoch a command was accepted under is stored on its reservation; any later read of a non-terminal command accepted under an older epoch appends a BLOCKED outcome with evidence. History is never rewritten |
| Vocabulary | The manifest pointed at section 3.22 (the communication standard), not the vocabulary. The build repaired the reference first: `domain-vocabulary.v1.json` was generated from section 3.1 and the manifest now names it with its real digest. Resolution is shared code keyed by data, with the business domain as a data selector |
| Artifact binding | Enforced in three places: BP refuses a timeline event for a step whose artifact is not LOCKED with both decisions for the exact digest; PR refuses to dispatch it and asks CE (`ArtifactBindingEvaluator`) before the provider call; the stub approval that CE-less sessions produced can no longer lock anything |
| Timeline | PR owns the stream, BP ingests it over an ADR-046 signed workload call (route grant added to `registry.yaml`) and projects it. Unknown outcome is a reason code on `EXECUTING`; reconciliation appends; a receipt without the provider's reference stays `EXECUTING`; Emergency Stop fences the stream and rewrites a late success to `HALTED` with its evidence kept |
| Outcomes | Activity counts are computed by BP from completed work with evidence; an agent-reported figure is always stored as agent-stated and labelled; a business outcome never shows a number and reads "Not measurable yet" |
| Spend | A sandbox-only chain on the existing wallet ledger: authorization (exact artifact and two evidence ids), atomic ceiling and reservation, charge only on verified provider proof, reconciliation per item, a discrepancy blocks new spend until resolved with evidence. Four private routes with route grants |
| Monitor tiles | Grouped in the web by the declared evidence source (business outcomes first, performance second, telemetry behind a details control); a tile that is not current is marked stale. No wire change, so no specification change |
| Web | One Work tab in the workbench: your decisions (two steps), what the agent is doing, results. The panel reads in English for every locale until the Founder confirms Hindi wording |

**Single-pass review and repairs.** One read-only Solution Architect review of the data contracts and code returned 21 findings. Repaired in this pull request: refusal of the artifact-creating exemption for steps with a binding or provider proof (BP and PR); a stop is re-checked immediately before the provider call; a scope confirmation given under an older Decision Space is stale; a predecessor is superseded by the fact that its successor is locked; a command already blocked by the rollback epoch goes no further; per-relationship serialization of timeline writes; credential-like references refused; an event id reused with different content is a conflict; Unicode-safe request digest between PR and BP; reservation replay under a race; reconciliation per item so opposite differences cannot cancel and an earlier break stays until resolved; tenant-scoped spend item reads; the exact artifact content and its fingerprint shown before approval; an unreadable section reads as unavailable, not empty.

**Gaps found in the build and not closed here (recorded, not fixed silently)**

| Id | Gap | Owner and next step |
|---|---|---|
| B1 | The PR execution stream, the CE step gate and the spend client are built and tested as modules but no running PR code path calls them yet; `SessionExecutor` still dispatches tools the old way. Until a caller is wired, a Demo run produces no timeline events | WC-171 or a repair pull request; Founder to confirm before the proof run (slice 4 S17 reports BLOCKED-BY-FLAG with the reason) |
| B2 | The stop and unknown-outcome fences are per process. A restart or a second replica forgets them; BP still rewrites a late success after a recorded stop | Wire to the existing durable stop barrier when B1 is wired |
| B3 | CE checks the shape of the binding (ids, digest, status, two different evidence ids) but cannot read BP's records, so BP ingest is the authoritative check of "locked and both decisions" | Accepted design; a CE read of BP records would be a new owner link |
| B4 | The decision owner check is the existing "active participant" check used by every employment command; a named-delegate refinement from the Decision Space (PG-07) is not added | Decision Space contract |
| B5 | WBE trusts the signed callers (BP authorizes, PR reserves and charges) for the evidence ids and the "verified" flag; it does not verify them with the evidence owner | WC-172 (real money) must close this before real spend |
| B6 | The ingest route proves the caller is PR but the body names the tenant and relationship; the signed envelope's own tenant scope is not compared | Close with B1 when PR's relationship context is wired |
| B7 | No read route exposes the spend chain to the harness, so slice 4 S19 reports NOT-COVERED; the Founder reads the reconciliation result after deployment | WC-171 oversight screens |
| B8 | Customer-route and ingest-route controllers have no unit tests; their behavior is covered through the services they call and the web route tests | Add with B1 |
| B9 | The Work tab reads in English for every locale | Founder's domain-wording confirmation |
| B10 | The workload trust bundle is at its Key Vault size limit (25,600 bytes; the existing issuer test fails with five more grants). Only one grant was added (professional-runtime to business-platform `ingestRealWorkEvent`). The four Billing Engine spend routes are built and tested but have no route grants, so no service can call them on Demo yet | Split or slim the trust bundle before WC-172 (real money) |

**Known failures that are not this change (shown on a tree without it or unrelated to any file touched).** Eleven billing-engine tests (component units, lifecycle commands, baseline seed, export and import, WC-124 authority); `tests/validation_control/test_wc115_generated_clients.py` for the AI runtime client digest (the AI runtime specification is untouched); `tests/constitutional` failures about WC-027 to WC-034 task tables, DCM specifications and the ADR-046 private operation inventory (none touches a file changed here); `test_workload_credentials` failed once under parallel load and passes alone (43 passed twice).

**Validation.** The one consolidated Docker pass is recorded in the pull request body with every command and its result. The Demo read-back, the slice 4 calibration report and the defect list start after the Founder's single deployment.
