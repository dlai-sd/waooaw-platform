# WC-170 - Real Agent Work End To End (Roadmap Iteration 3, Milestone M3) - GATED SKELETON

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-170 |
| Office | Platform IT Expert (INST-010), with Business and Enterprise Architecture input for grooming |
| Initiative | IB-170 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 3 of 6, milestone M3 |
| Founder assignment | Current conversation, 2026-11-24: "WC-170 as the gated skeleton ... Yes." |
| Status | GATED SKELETON. **Grooming first. Implementation is unauthorized until the Founder accepts the groomed stories** |
| Depends on | WC-169 merged, deployed and read back; one valid calibration report |
| Requirement ledger | [WC-170-requirements.yaml](./WC-170-requirements.yaml) |
| Constitutional basis | C-001, C-002, C-005, C-007, C-023, C-049, C-063, C-065, C-088, C-089 |
| Deployment | One Environment Deployment of Demo after the build merges |

## Why This Contract Exists

The customer pays for agent work: a campaign brief, a proposal and approval, a status timeline, ad spend that reconciles, and results traced to work (AE-02, PG-17 to PG-23). The gap register lists PG-17 to PG-23 as UNGROOMED. The DMA domain authority is the Founder himself (`goals/GOAL-005-f4-dma-domain-authority-input.md`: "Yogesh will do this. Sujay will come in picture once waooaw is operational"), and `goals/GOAL-005-D06-dma-domain-authority-synthesis.md` is an input awaiting incorporation, so phase A needs the Founder's time. Building before grooming would repeat the "specification closed, proof pending" pattern. This contract is therefore a grooming contract first and an implementation contract only after the Founder accepts the stories.

## Phases

| Phase | Content | Exit |
|---|---|---|
| A Groom | Turn PG-17 to PG-23 and AE-02-S01 to S05 into implementation-ready stories with acceptance, data contracts and owners; record what already exists (AE-02-S01 connect and AE-02-S05 publish are covered by WC-149 and WC-162); record the DMA domain-authority input | The Founder accepts the stories |
| B Build | One pull request for the accepted stories; two only if the Founder agrees at the A exit | Docker tests; no activation without authorization |
| C Prove | A synthetic customer completes brief, approval, execution, reconciliation and results trace on Demo | Calibration report |

## Candidate Requirement Index (confirmed or replaced at the phase A exit)

| Id | Requirement |
|---|---|
| WC170-R001 | Domain vocabulary specializes without agent branching in the shared kernel (PG-17) |
| WC170-R002 | The customer sees and governs the locked intent artifact that controls execution (PG-18, AE-02-S02 and S03) |
| WC170-R003 | Proposal and approval are visibly distinct from scope-boundary confirmation (PG-19) |
| WC170-R004 | The execution status and action timeline show proposed, approved, executing, completed, failed and halted (PG-20) |
| WC170-R005 | A customer traces an outcome claim to work and evidence (PG-21) |
| WC170-R006 | Ad spend is authorized, attributable and reconciles to the provider and the wallet (PG-22, C-088, C-089) |
| WC170-R007 | Business KPIs lead and technical metrics support (PG-23) |
| WC170-R008 | The conversation stories run on Demo with `WC120_CONVERSATION_ENABLED` on, after the five WC-120 conversation tables the Business Platform uses (`conversation_context_observations`, `conversation_context_summaries`, `conversation_data_right_requests`, `conversation_migration_watermarks`, `whatsapp_media`) are granted to the application role with a per-table privilege analysis and matching row-level-security policies; WC-168 measured these as unreadable on Demo |
| WC170-R009 | The platform funds platform-owned work and the customer funds hired work; no work runs unfunded |
| WC170-R010 | Stop halts agent work mid-execution and evidence shows it (C-001) |

## Journey Simulation (gaps found)

Customer: connected, agent proposes a campaign brief, customer approves, agent works, customer sees status, ad spend, results, approve or stop.
- Real agent work needs an AI provider credential on the Providers screen and runtime capacity, and each step needs a decision on who funds it (R009).
- DMA domain-authority input comes from the Founder, not an outside party, so phase A needs his time (see the review record).
- Real ad spend stays in sandbox or test mode until Iteration 5.
- The iteration is large. Two pull requests are possible, only with the Founder's agreement at the A exit.

## Critical Review And Simulation Record (2026-11-24)

Method: the skeleton was checked against the gap register, the GOAL-005 grooming records, the acceptance architecture and the existing DMA code and tests; the customer journey was then walked from "connected" to "results" and each step compared with what exists. Findings that changed this contract are marked FIXED.

### Customer journey run from "connected" to "results"

| Step | What exists today | Gap | Contract response |
|---|---|---|---|
| Agent proposes a campaign brief | DMA release-1 skills and a conversation protocol exist behind `WC120_CONVERSATION_ENABLED` (default off) | Flag off; brief is not a governed, locked artifact | R002, R008 |
| Customer approves | Approval ladder is specified in the agent experience architecture | Approval and scope-boundary confirmation are not shown as distinct | R003 |
| Agent works | Publish is proven by WC-162 (AE-02-S05); campaign execution beyond publishing is not | Real AI provider credential and capacity needed; sandbox only | R009 |
| Customer sees status | A shared timeline is specified | Not built | R004 |
| Ad spend | Spend accounts and a pricing engine exist | Authorization, attribution and reconciliation to the provider are not proven | R006 |
| Results | KPI framework specified | Outcome-to-evidence trace not built | R005, R007 |
| Stop mid-work | Stop is proven for the relationship (AE-01-S10) | Not proven while agent work is executing | R010 |

### Gaps found and how they were fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The skeleton called DMA domain input an outside dependency | The DMA domain authority is the Founder; Sujay is deferred until the platform is operational | FIXED: the dependency is the Founder's time in phase A |
| G2 | Part of the scope already exists | AE-02-S01 (connect) is covered by WC-149 and AE-02-S05 (publish) by WC-162 | FIXED: phase A must inventory existing coverage before writing stories |
| G3 | The platform-led rule could be broken inside this contract | DMA is the only agent in play | FIXED: stop condition already forbids a DMA-only kernel change; phase A states each story as a platform capability |
| G4 | Funding of each step is undecided | Funding model accepted 2026-11-20; per-step account not mapped | FIXED: R009 |
| G5 | The size is unknown until grooming | PG-17 to PG-23 are ungroomed | FIXED: two pull requests only with the Founder's agreement at the A exit; contract stays a gated skeleton |

## Stop Conditions

- The stories are not accepted at the A exit: no build.
- Any step would spend real money or contact a real customer: stop.
- A story needs a change to the shared kernel for DMA only: stop and ask the Founder, because it breaks the platform-led rule.

## Implementation Record

Skeleton written 2026-11-24. Grooming not started.
