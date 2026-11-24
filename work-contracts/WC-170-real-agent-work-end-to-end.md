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

The customer pays for agent work: a campaign brief, a proposal and approval, a status timeline, ad spend that reconciles, and results traced to work (AE-02, PG-17 to PG-23). The gap register lists PG-17 to PG-23 as UNGROOMED, and the GOAL-005 program records that AE-02 depends on DMA domain-authority input. Building before grooming would repeat the "specification closed, proof pending" pattern. This contract is therefore a grooming contract first and an implementation contract only after the Founder accepts the stories.

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
| WC170-R008 | The conversation stories run on Demo with `WC120_CONVERSATION_ENABLED` on |
| WC170-R009 | The platform funds platform-owned work and the customer funds hired work; no work runs unfunded |
| WC170-R010 | Stop halts agent work mid-execution and evidence shows it (C-001) |

## Journey Simulation (gaps found)

Customer: connected, agent proposes a campaign brief, customer approves, agent works, customer sees status, ad spend, results, approve or stop.
- Real agent work needs an AI provider credential on the Providers screen and runtime capacity, and each step needs a decision on who funds it (R009).
- DMA domain-authority input is an outside dependency and is part of the phase A exit.
- Real ad spend stays in sandbox or test mode until Iteration 5.
- The iteration is large. Two pull requests are possible, only with the Founder's agreement at the A exit.

## Stop Conditions

- The stories are not accepted at the A exit: no build.
- Any step would spend real money or contact a real customer: stop.
- A story needs a change to the shared kernel for DMA only: stop and ask the Founder, because it breaks the platform-led rule.

## Implementation Record

Skeleton written 2026-11-24. Grooming not started.
