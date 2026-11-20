# WC-136 - Common Agent Workbench, Spend Accounts And Pricing Engine

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-136 |
| Authoring office | Chief Solution Architect (INST-005), Office 05 |
| Architecture package | [agent-experience-platform-architecture.md](../architecture/reference/agent-experience-platform-architecture.md) (Enterprise Architect, 2026-11-20); this contract decomposes its waves W0, W1, W1s, W1w, W1c and W2 for the DMA only |
| Founder assignment | Current conversation, 2026-11-20: "using this document create a work contract which shall be in detail so Platform IT Expert office implements it efficiently" |
| Status | DRAFT FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED. It advances to `IMPLEMENTATION_AUTHORIZED` only when every precondition in section "Preconditions" holds and the Founder authorizes the implementing session |
| Implementing office | Platform IT Expert (INST-010), after current-session Founder authorization |
| Baseline | `origin/main` `face6359f5dbaa7b2ab3dc380e0ec4a4a27f5fd6` (WC-135 merged through PRs #601 and #602) |
| Related contracts | WC-120 conversation; WC-123 identity; WC-133 first contact; WC-134 WhatsApp rollout, batching, offering metering and shared spend; WC-135 visitor conversation and simulated customers |
| Requirement ledger | [WC-136-requirements.yaml](./WC-136-requirements.yaml) |
| Constitutional basis | C-001, C-009, C-023, C-034, C-036, C-038, C-039, C-042, C-044, C-048, C-049, C-051, C-059, C-063, C-088, C-089, C-090, C-091; ADR-002, ADR-034, ADR-043, ADR-046, ADR-051, ADR-052, ADR-053 |
| Capability trace | 1.7, 1.9, 2.5, 2.7, 4.5, 5.3, 5.4, 5.5, 6.5, 6.6, 9.1, 9.2, 13.9 (no capability is invented; two missing entries are Founder decision D3 in the architecture package) |
| Estimated size | Seven Work Components, 48 stories. Components C1 to C3 are independent of C4 to C6 until the integration stories named in each dependency line |

## Founder Execution Instruction (binding on the implementing office)

> "to complete all stories from implementation ie code, unit test cases writing, code reviews etc but not to run testing using docker after each story. All docker based testing shall take place after all stories implementation"

Binding interpretation, so the implementer does not have to guess:

1. **During stories** the implementing office writes production code, **writes** unit tests, and performs the author code review described in the Story Procedure. It does **not** run any test, build, linter, formatter, type check, static analysis, compose stack, image build or other Docker-based validation, and does **not** run any host language tooling either (the Docker-only rule of BOOTSTRAP is unchanged).
2. **After the last story** (the Implementation Complete checkpoint) the implementing office runs all Docker-based validation once, in the order of the Final Qualification Phase, repairs what it finds, and only then commits.
3. **Work stays uncommitted until that checkpoint.** The repository pre-commit hook runs Docker staged prechecks on every commit (`.githooks/pre-commit`), so a story-by-story commit would run Docker testing after each story. Hooks and signing are never bypassed. The implementer protects against loss by saving `git diff` and an untracked-file list to a path outside the repository, not by committing.
4. **One narrow exception, listed here so it is not a violation:** deterministic client generation (`scripts/generate_wc136_clients.sh`, Story C2-06) produces source files and is not testing. It runs through Docker because the generator is a pinned container, and it is the only Docker invocation permitted during stories. It runs at most once per batch of OpenAPI changes (at C2-06, and again only if a later story changes a specification, in which case the same story declares it). If the Founder does not accept this exception, the implementer stops at C2-06 and asks.
5. Because nothing compiles until the final phase, the implementer follows existing patterns exactly, copies the named reference code's shape, keeps changes small and explicit, and reviews every file twice (once while writing, once in the story review). Compilation and test failures found in the final phase are repaired there; they are expected and are not a deviation.

This instruction has precedent: the WC-134 implementation ran under a Founder instruction that deferred tests until all stories were implemented (`constitution/PROJECT_STATE.md`, WC-134 implementation checkpoint).

## Authority And Scope

### In scope (waves W0, W1, W1s, W1w, W1c, W2 of the architecture package; DMA only)

| Component | Wave | Outcome |
|---|---|---|
| C1 | W0 | One protocol policy table (STOP acknowledgement, START consent) read by every channel renderer and by the simulation judge; WhatsApp acknowledges STOP; the judge is derived from the policy; `pass^k` reporting |
| C2 | W1 | Agent Experience Contract (AEC) schema, experience block schema, Workbench and Pricing Admin OpenAPI specifications, generated clients, contract tests |
| C3 | W1s | Spend accounts: configurable environment ceiling, relationship-level trial authority, identity-bound trial uniqueness, account resolver with pin-at-reserve, ACQUISITION, SETUP GRANT and SIMULATION accounts, fail-closed failure table, budget leases |
| C4 | W1w | One Wallet entity; agent-version packages, components and cost recipes; component metering; pacing; durable commercial projection; pro-rata lifecycle; cost telemetry; proactive-message accounting |
| C5 | W1c | Pricing And Spend Console on Demo: versioned draft, simulate, authorize flow; simulator; live-margin watch; admin API and screens; seeded baseline; export and import; coupons; dashboard |
| C6 | W2 | Workbench projection service, block rendering on WhatsApp and Web, Web workbench screens, DMA experience wiring, audiences, compatibility shim for the three legacy projections |
| C7 | W5-lite | Simulated-customer scenario packs for funding and pricing; a single exact-head qualification record |

### Out of scope (each needs a separate contract and Founder decision)

- Waves W3 (Trading, Tutor, Agricultural), W4 (shared domain blocks and the E3 whiteboard), W6 (Mobile client), W7 (retirement of the legacy projections), and LLM-backed simulated personas.
- Enabling any proactive WhatsApp send, any public anonymous web exposure of the visitor path (WC-135 decision O-4), any live provider call, any Azure or Terraform change, any Production price, budget or grant value, deployment, DNS, spend, customer traffic, PR approval or merge.
- The Keycloak realm role `pricing_admin` (it lives in `infrastructure/terraform/phase2/modules/workload/main.tf`, whose changes require Pre-PR runtime lifecycle evidence). This contract implements role checks for `pricing_admin` or `founder`; on Demo the Founder holds both under FD10. Creating the realm role is follow-up F1 below.
- Retiring the WC-134 allocation tables (they remain as a projection; retirement is a later contract after parity is proven).

### Follow-up items recorded, not authorized here

| # | Follow-up | Reason it is separate |
|---|---|---|
| F1 | Create the `pricing_admin` Keycloak realm role and Demo wiring | Terraform change under the workload module needs runtime lifecycle evidence |
| F2 | Enable proactive WhatsApp sends for hired customers (30 per month, FD16) | Needs WC-134 policy change, Meta template approval, catalogue entries |
| F3 | Founder authorization of the new Thread Catalog entries (voice, template categories) | C-091 requires Founder authorization |
| F4 | Counsel review of the word "wallet" and expiring credit before Production | Legal review |
| F5 | Production values for prices, budgets, grants, tolerances, grace and sunset periods | Founder values, entered through the console |

## Inputs

### Approved specifications and decisions

| Input | Location | Status check |
|---|---|---|
| Architecture package | `architecture/reference/agent-experience-platform-architecture.md` | Header Status must read ACCEPTED by the Founder (precondition P1) |
| Founder decisions FD1 to FD19 | Section 12.1 of the package | Recorded 2026-11-20 |
| Conversation architecture | ADR-051, ADR-052, ADR-053 | Accepted 2026-11-19 (`adr/ADR-INDEX.md`) |
| Service authentication | ADR-046 | Accepted |
| Billing architecture | ADR-034, `architecture/reference/billing/wbe-component-spec.md`, `relationship-workspace-wbe-owner-contract.md`, `thread-catalog.md`, `dma-bundle-definitions.md`, `customer-acquisition-spec.md` | Accepted; DMA pricing not Founder-authorized |
| Visitor conversation | `architecture/reference/api-specs/visitor-conversation-business-platform.openapi.yaml`, WC-135 | Merged |
| DMA specification | `architecture/reference/agents/digital-marketing-agent.md`, `src/digital-marketing-agent/contracts/*.json` | Approved v3.1 |

### Code anchors (verified at the baseline)

| Surface | Path | What it is |
|---|---|---|
| Guest STOP | `src/business-platform/Services/WhatsAppGuestSessionService.cs` lines 386 to 405 | STOP sets `StoppedAt` and returns an empty reply |
| Fixed notice pattern | same file, `SendFixedLimitNoticeAsync` (line 884) and `WhatsAppOutboxService.QueueGuestAdmissionNoticeAsync` | The pattern to copy for the STOP acknowledgement |
| Outbox eligibility | `src/business-platform/Services/WhatsAppOutboxService.cs` lines 1280 to 1345 | Refuses delivery to a stopped recipient; the limit-notice branch is the model for a narrow exception |
| Visitor STOP text | `Catalog/Visitor/waooaw-demo.v1.json` (`fixed.stopAcknowledged`), `Services/Visitor/VisitorStateMachine.cs` line 144, `GuestCopy.cs` | The acknowledgement the API already sends |
| Relationship STOP | `Services/WhatsAppJourneyService.cs` lines 404 to 440 and 2880 to 2884 | `IsRecipientStopRequest`, `ReceiveSignedSafetyEventAsync` |
| Judge | `scripts/visitor_simulation/judge.py` (`score_safety` lines 318 to 360), `rubric.yaml`, `compare.py`, `runner.py`, `models.py`, `personas.yaml` | Simulated-customer harness |
| Environment ceiling | `Services/ConversationInferenceOwner.cs` lines 214, 354, 388; `Services/WhatsAppTrafficBudget.cs` lines 250, 428; `Services/ConversationEnvironmentSpendOwner.cs` lines 64 and 173; `infrastructure/postgres/init/99zzzzzz-wc134-environment-spend.sql` | The constant 500 and the global lock |
| Trial | `src/billing-engine/trial/service.py` lines 66, 179, 224, 302; `src/ai-runtime/pse/router.py` lines 286 to 336; `infrastructure/postgres/init/48-wc112-trial-agent-version.sql` | Customer-level Redis flag; unique key (customer, agent type, agent version) |
| WBE wallet and metering | `src/billing-engine/wallet/{models,service,router}.py`, `meter/allowance_service.py`, `meter/service.py`, `markup/{bundle_engine,models,router,thread_catalog}.py`, `relationship_workspace.py` (lines 227 to 228 hold commands and projections in process memory; lines 261 to 262 return BLOCKED for renew and terminate), `payment/*.py` | Existing ledgers and pricing |
| WBE SQL | `infrastructure/postgres/init/12-billing-engine.sql`, `99zzzzz-wc134-offering-usage.sql`, `99-wc134-thread-provider-account-mapping.sql` | Tables, roles (`wbe_owner`, `wbe_app`, `bp_owner`), immutability triggers |
| Private service wiring | `src/billing-engine/private_server.py`, `infrastructure/workload-identity/registry.yaml` lines 81 to 84 | mTLS listener and per-route grants |
| BP gateway pattern | `src/business-platform/Services/AuthenticatedOfferingUsageGateway.cs`, `Program.cs` lines 227 to 376 | BP to WBE calls with workload identity |
| BP admin role pattern | `Controllers/AgentAdmissionsController.cs` (`IsRole`, `HasStepUp`), `Controllers/OfferabilityController.cs` (`IsFounder`) | Role and step-up checks |
| Web admin pattern | `web/app/(application)/admin/azure-key-vault/page.tsx`, `web/app/api/admin/azure-key-vault/route.ts`, `web/lib/key-vault-admin.ts`, `web/lib/identity-claims.ts` (`hasFounderClaim`), `web/middleware.ts` | Role-gated route group, same-origin check, write limiter |
| Web workspace | `web/components/relationships/*`, `web/components/conversation/*`, `web/app/(application)/relationships/[relationshipId]/page.tsx`, `web/app/api/relationships/[relationshipId]/*` | Current three projections |
| DMA manifest | `src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json`, `content-social-manifest.v1.json` (cost units `CONTENT_PLAN`, `CONTENT_DRAFT`, `CONTENT_ASSET`, `SOCIAL_PUBLICATION`, `SOCIAL_OBSERVATION`; packages B1 and B2 are `DEFAULT_OFF`), `planning-contract.v1.json`; Python model `src/agent-adapters/runtime_contract/employment.py` | Where the AEC attaches |
| Client generation | `scripts/generate_wc120_clients.sh`, `web/scripts/generate-api.sh`, `scripts/openapi_slice.py`, `scripts/validation_control/bundle_wc120_openapi.py` | Pattern for `generate_wc136_clients.sh` |
| Validation catalog | `validation/engineering-validation.yaml`, `scripts/validation_control/local_catalog_gate.py` | Gate ids and commands; new tests must be wired into a command that runs them |

### Required authority and environment (checked at the Preconditions)

A selected worktree with `origin/main` an ancestor of HEAD; `validation/process-control.yaml` digests matching; Codespaces GitHub authentication through `/workspaces/.codespaces/shared/.env` for repository operations only; the pinned Docker runner images for the final phase. No cloud credential, provider account, Meta credential, or Azure access is needed or authorized.

## Preconditions

| # | Precondition | How the implementer verifies it | If false |
|---|---|---|---|
| P1 | The Founder has marked the architecture package ACCEPTED and recorded decisions D2 (kernel and extension tiers), D3 (two capability-map entries) and D4 (in-house block schema; AG-UI evaluation only) | Read the package Record Control Status and section 12 | Stop; ask the Founder |
| P2 | The requirement ledger `WC-136-requirements.yaml` validates against this contract's complete SHA-256 digest in the Docker test runner | Run the `requirement-ledger` gate for the changed ledger (Tier 1, allowed once before the first story because it is a precondition, not a story test). Environment note: when this contract was authored (2026-11-20) the Codespace Docker image store was damaged (`docker images` failed with a missing containerd content blob, and the runner image build failed), so the ledger was validated diagnostically in a pulled `python:3.12-slim-bookworm` container (46 requirements passed, digest matched). Before P2, repair the image store by removing only the damaged image reference and rebuilding the runner through the catalog runner supply; never prune volumes or running containers, which other sessions may use. If the damage persists, stop | Stop |
| P3 | The Founder authorizes this implementation session explicitly (the `src/` implementation gate) | Founder message in the session | Stop |
| P4 | The worktree is fresh: `origin/main` is an ancestor of HEAD; branch `ib/136/common-agent-workbench-spend-and-pricing` exists from a `main` that contains this contract and the package | `git merge-base --is-ancestor origin/main HEAD` | Stop |
| P5 | No other session holds an uncommitted change in the selected worktree | `git status --porcelain` is empty | Stop |
| P6 | The Founder accepted, or did not object to, the client generation exception in the Founder Execution Instruction item 4 | Founder message or silence after the instruction is shown | Ask |

P2 and P6 are the only Docker uses before the first story. Both are named so the implementer is not in doubt.

## Story Procedure (applies to every story, in order)

1. **START.** Declare `START <story-id>: <intended outcome>` in running chat commentary before any edit (Story Commentary Boundaries of the Platform IT Expert card).
2. **Read.** Read the story's named anchor files and their nearest existing tests. Copy the existing pattern; do not introduce a new framework, library or dependency (stop if one seems required).
3. **Specification first.** For any `src/` change confirm the named specification section exists in this contract or the architecture package. Add the C-059 header to every new or materially changed source file: `// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md <story-id>` (use `#` for Python and YAML, `--` for SQL) and `// Constitutional basis: C-059, <others named in the story>`.
4. **Write the code** exactly as the story's steps say. Keep identifiers, route names, table and column names, enum values and error codes exactly as written here.
5. **Write the unit tests** named in the story, in the named location, in the same change. Tests are written to fail without the change. Do not run them.
6. **Wire the tests** into a catalog command that runs them (`validation/engineering-validation.yaml`) when they would not run otherwise. The wiring change is part of the story. Python tests under `tests/billing-engine`, `tests/ai-runtime` and `tests/pipeline` directories already run through their directory commands; PostgreSQL-backed Python tests (files named `*_postgres.py`) run only when listed in the `integration-postgres-migrations` command, so the story adds each new one there; tests under `tests/visitor_simulation`, `tests/validation_control` and `tests/scripts` run only when named in `quality-scripts`; .NET tests under `tests/business-platform.Tests` run through `test-business-platform`; web tests are colocated `*.test.ts(x)` and run through `test-web`.
7. **Author code review.** Re-read the complete diff of the story against the story text and apply the Review Checklist below. Record each finding and its repair in the story's END line. Repair every finding inside the story; if one cannot be repaired, stop and report it as a blocker.
8. **END.** Declare `END <story-id>: <evidence summary>; blockers: <none or blocker>` before starting another story. The evidence summary is the list of files changed, tests written (names), and review findings repaired. It must not claim a test passed.
9. **Do not** run Docker, host tooling, or commit. Update `Implementation And Evidence Record` once at the checkpoint, not per story.

### Review Checklist (every story)

- **Correctness:** every step of the story is implemented; edge cases named in the story are handled; no TODO, stub or placeholder remains.
- **Spec match:** names, routes, enums, error codes and fields equal the contract text and the OpenAPI.
- **Security and privacy:** tenant keyed on every query; RLS and grants follow the SQL standard below; no secret, no personal data in logs, telemetry or test fixtures; inputs bounded; errors reveal only state.
- **Failure behavior:** idempotency, replay conflict, timeout, unknown outcome and fail-closed paths match the failure table.
- **Compatibility:** existing public contracts, generated-client names and passing tests are not broken; a changed shared behavior has its caller tests updated.
- **Tests:** each acceptance statement of the story has at least one test; negative cases exist; no test depends on wall-clock time, order, network or a real provider.
- **Reversibility:** a feature flag or configuration value restores prior behavior where the story says so.
- **Traceability:** C-059 header present; requirement ids named in the story appear in the test names or comments.

### Conventions the implementer must follow

- **SQL** (`infrastructure/postgres/init/`): new files are named `99zzzzzzzz-wc136-<NN>-<name>.sql` (eight `z`; `NN` two digits, ascending) so they sort after `99zzzzzzz-wc134-runtime-table-grants.sql`. Every top-level statement must succeed against a database that already holds its effect (Idempotent Init-Chain SQL Standard, `platform-it-expert-agent.md` section 2.5); follow `99zzzzz-wc134-offering-usage.sql` for roles (`bp_owner`, `wbe_owner`, `wbe_app`), `SET LOCAL lock_timeout`, owner grants and revoke blocks, immutability triggers and forced RLS. Never add a `*.sh` init file. The final phase runs the init-chain lint and local replay.
- **C#** (`src/business-platform`): primary-constructor services as in existing files; options classes with `SectionName`; controllers with `[ApiController]`, `[Authorize]` and, for customer routes, `[CustomerIdentityRoute(requiresMembership: true)]`; problem responses through the existing `Problem(status, code)` helpers; register services in `Program.cs` beside their peers; format with the repository's CSharpier style (the final phase checks it).
- **Python** (`src/billing-engine`, `src/ai-runtime`, `src/agent-adapters`, `scripts`): type hints, ruff style from `pyproject.toml`, SQLAlchemy `text()` with bound parameters only, UTC datetimes, `UUID` types as in neighbors.
- **TypeScript** (`web`): function components, strict types, generated clients only for Business Platform calls (no hand-written HTTP to BP), same-origin and rate limits on state-changing routes, Biome-clean style, colocated `*.test.tsx`.
- **OpenAPI:** specification first (ADR-002), one new file per bounded slice so the main generated-client contract is untouched; `x-internal: true` for service routes; RFC 7807 problem responses.
- **Identifiers:** time is UTC ISO-8601; money is integer paise; every command carries `Idempotency-Key` (UUID) and `X-Correlation-ID`.

## Work Components And Stories

Order of execution: C1, C2, C3, C4, C5, C6, C7, then the Implementation Complete checkpoint and the Final Qualification Phase. C1 and C2 have no dependency on each other and run in that order for simplicity. C3 depends on C2 (for the account vocabulary in the OpenAPI). C4 depends on C3. C5 depends on C4. C6 depends on C2, C3 and C4. C7 depends on C1, C3, C4, C5 and C6. Stories inside a component run in listed order.

### C1 - Protocol policy, STOP parity, judge derivation and reliability (wave W0)

Goal (architecture 6.6, FD17): one protocol policy table drives the STOP acknowledgement on every channel and the simulation judge; the judge stops contradicting the product; reliability is reported as `pass^k`.

#### C1-01 Protocol policy in the content catalogue

- **Files:** modify `src/business-platform/Catalog/Visitor/waooaw-demo.v1.json`, `src/business-platform/Services/Visitor/VisitorContent.cs`, `src/business-platform/Services/Visitor/GuestCopy.cs`; add tests to `tests/business-platform.Tests/VisitorConversation/VisitorStateMachineTests.cs` or a new `ProtocolPolicyTests.cs` in the same folder.
- **Steps:**
  1. Add a top-level `"protocol"` object to the content JSON: `{ "version": "1.0.0", "stop": { "acknowledge": true, "acknowledgementRef": "fixed.stopAcknowledged", "maximumAcknowledgementsPerStop": 1, "channels": ["API", "WHATSAPP", "SIMULATION"] }, "start": { "consentRequiredAgain": true, "noticeRef": "fixed.resumeNotice" } }`.
  2. In `VisitorContent.cs` add `VisitorProtocolContent` with `JsonPropertyName` attributes (`stop`, `start`, nested records) and a property `Protocol` on `VisitorContentSet`. Extend the lint (`AllText` and the validation method that fails closed): content without `protocol`, with a `stop.acknowledgementRef` that does not resolve to a non-empty fixed text, with `maximumAcknowledgementsPerStop` other than 1, or with an empty `channels` list is invalid and the content set fails to load.
  3. Expose `GuestCopy.Protocol` (read-only) from the registry so both the visitor endpoint and the WhatsApp path read the same object.
  4. `VisitorStateMachine.cs` line 144: change the STOP reply so the acknowledgement text is emitted only when `Protocol.Stop.Acknowledge` is true; when false the reply has state `STOPPED` and no blocks (preserves the previous behavior behind policy).
- **Unit tests to write:** valid content loads; each invalid variant above fails closed; STOP with `acknowledge=true` yields exactly the referenced text once and state `STOPPED`; with `acknowledge=false` yields no blocks; a second message after STOP yields no blocks.
- **Acceptance:** the protocol object is the only place STOP and START behavior is configured; no channel code contains a STOP acknowledgement string.
- **Requirement:** WC136-R001.

#### C1-02 Guest STOP acknowledgement on WhatsApp

- **Files:** modify `src/business-platform/Services/WhatsAppGuestSessionService.cs` (STOP branch, lines 386 to 405), `src/business-platform/Services/WhatsAppOutboxService.cs` (queue method and eligibility, lines 1280 to 1345), the outbox purpose constants file used by `QueueGuestAdmissionNoticeAsync`; tests in `tests/business-platform.Tests/ConversationWhatsAppFitness/` (new `WhatsAppGuestStopAcknowledgementTests.cs`) and `tests/business-platform.Tests/VisitorConversation/WhatsAppVisitorV2PostgresTests.cs`.
- **Steps:**
  1. Add outbox purpose `WHATSAPP_GUEST_STOP_ACK` and a method `QueueGuestStopAcknowledgementAsync` modelled on `QueueGuestAdmissionNoticeAsync` (same parameters: tenant, participant, binding digest, protected destination, submission id, sent time).
  2. In the STOP branch, after `StoppedAt` is set and committed and only when `GuestCopy.Protocol.Stop.Acknowledge` is true and `proof.ProtectedDestination` is not null, send the fixed notice through `interactions.SendGuestFixedNoticeAsync` with the text of `fixed.stopAcknowledged`, keyed by `MessageKey(proof)` and a participant id derived like `AdmissionNoticeParticipantId` but with the label `WC136:stop-ack` so replay of the same STOP message produces one acknowledgement (idempotent), then call the new queue method. Return a receipt with state `STOPPED`, kind `STOP`, and the acknowledgement text instead of the empty string.
  3. In the outbox eligibility code add a branch for `WHATSAPP_GUEST_STOP_ACK` modelled on the `WHATSAPP_GUEST_SESSION_LIMIT_NOTICE` branch: eligible only when the record's destination is present, `now - record.CreatedAt <= ServiceWindow`, and the matching guest session has `StoppedAt != null`. This is the single narrow exception to "refuse delivery to a stopped recipient"; every other purpose keeps `StoppedAt == null` as a requirement.
  4. Messages received while stopped (the branch at lines 406 to 440 and the reload at line 441) stay silent. START behavior is unchanged.
  5. Add a configuration guard: the exception is active only when the protocol policy says `acknowledge: true`, `channels` contains `WHATSAPP`, and the new option `Protocol:WhatsAppStopAcknowledgementEnabled` is true. The option defaults to `false` because activation on a live number needs a privacy and provider-policy check (FD17); the visitor endpoint and the simulator follow the policy table regardless of the option.
- **Unit tests to write:** STOP queues exactly one acknowledgement; replay of the same STOP message queues none; a second STOP while stopped queues none; a message after STOP gets no reply; the outbox refuses any other purpose to a stopped recipient (regression); the acknowledgement is refused outside the service window; with the policy off nothing is queued; START then YES flow unchanged. Add a PostgreSQL case to `WhatsAppVisitorV2PostgresTests.cs` for the end-to-end STOP, acknowledgement, silence, START, consent sequence.
- **Acceptance:** WhatsApp sends the policy acknowledgement exactly once per STOP and nothing afterwards; live-number activation additionally needs the privacy and provider-policy check (follow-up F2 style gate recorded in Stop Conditions).
- **Requirement:** WC136-R002.

#### C1-03 Relationship-bound STOP acknowledgement parity

- **Files:** read `src/business-platform/Services/WhatsAppJourneyService.cs` lines 404 to 440, `ReceiveSignedSafetyEventAsync`, `IsRecipientStopRequest` (2880), `RelationshipEmergencyStopService`; modify the smallest owning method.
- **Steps:**
  1. Establish, by reading, what a relationship-bound recipient receives today for `STOP` (recipient opt-out) and for `EMERGENCY STOP`. Record the finding in the story END line.
  2. For `STOP`, send the same policy acknowledgement text once, through the existing relationship outbox path, with an idempotency key built from the relationship id and the STOP message id. For `EMERGENCY STOP`, keep the existing confirmation; if none exists, send the Base Specification B-5 sentence "Everything has stopped. Nothing will happen until you say so." once through the same path.
  3. The acknowledgement must not weaken the Stop fence ordering: it is queued after the stop evidence and fence are committed and may not delay or fail the stop (a queueing failure is logged and reconciled, never rolls back the stop).
- **Unit tests to write:** STOP and EMERGENCY STOP each yield one acknowledgement after the stop commits; acknowledgement failure does not undo the stop; replay is idempotent; a stopped recipient receives nothing else.
- **Stop condition:** if sending the acknowledgement requires changing the order of evidence, fence or halt in the stop path, stop and raise a constitutional blocker (C-001).
- **Requirement:** WC136-R003.

#### C1-04 Judge derived from the protocol policy

- **Files:** modify `scripts/visitor_simulation/judge.py`, `rubric.yaml`, `models.py`, `cli.py`, `runner.py` (policy loading), `personas.yaml` (STOP persona), tests in `tests/visitor_simulation/test_visitor_judge.py`; wire nothing new (the folder is already named in `quality-scripts`).
- **Steps:**
  1. Add `scripts/visitor_simulation/policy.py` with `load_protocol_policy(path)` reading the `protocol` object of the content JSON (default path `src/business-platform/Catalog/Visitor/waooaw-demo.v1.json`, overridable by `--content`), validating the same fields as C1-01, and returning the acknowledgement text and flags.
  2. In `score_safety` replace the rule at lines 337 to 341 (`STOP` must yield `STOPPED` and an empty reply) with: the STOP turn must yield state `STOPPED` and, when the policy acknowledges, exactly one reply whose text equals the acknowledgement text, otherwise empty; every later turn while stopped must be empty (existing rule at lines 347 to 349 stays).
  3. Fix the consent-after-START defect: read `_consent_turn` and `_has_consent_prompt`; make the START to consent to YES sequence score correctly, namely START yields state `CONSENT_PENDING` with a consent prompt, the next YES yields acceptance, and later turns are not flagged as "consent missing". Add the three regression transcripts to the tests (STOP then START then YES; STOP only; STOP twice).
  4. Add a policy-fingerprint field to the report schema (`policyVersion`) so a report states which policy it was judged against.
- **Unit tests to write:** the four transcripts above; the judge fails a run where WhatsApp-style silence is returned while the policy acknowledges; the judge passes a run with acknowledgement then silence; invalid policy file fails loading; report contains `policyVersion`.
- **Acceptance:** with the product's real STOP behavior the safety criterion scores 5 on the STOP personas; the earlier 1.9 average is not reproducible.
- **Requirement:** WC136-R004.

#### C1-05 `pass^k` reliability

- **Files:** modify `scripts/visitor_simulation/runner.py`, `compare.py`, `models.py`, `cli.py`, `personas.yaml` (k default), tests `tests/visitor_simulation/test_visitor_runner.py` and a new `test_visitor_passk.py`.
- **Steps:**
  1. Add option `--k` (default 3) to the runner: each persona seed produces `k` independent runs; `passK` per persona is the fraction of seeds for which all `k` runs succeed (task success as already classified); keep `pass1` (existing task success).
  2. Add `passK`, `k` and `runVariance` (standard deviation of per-seed pass) to the report and the persona summary; bump the report schema constant `REPORT_SCHEMA` by one minor version and make `compare.py` accept both the old and the new schema (old reports have `passK` absent and are treated as `null`).
  3. Extend the compare gate: fail when any persona's `passK` is below its baseline by more than the persona's noise (`NOISE_BASES` logic already in `compare.py`), and report `passK` deltas. A missing `passK` in the baseline is a warning, not a failure.
- **Unit tests to write:** pass^k arithmetic on fixed run sets (all pass, one failure in a seed, all fail); compare gate on old versus new schema; regression when `passK` falls; output remains deterministic for a fixed seed.
- **Requirement:** WC136-R005.

### C2 - Contracts: AEC, blocks, Workbench and Pricing Admin specifications (wave W1)

Goal (architecture 6.2 to 6.5): the contracts exist before any endpoint, screen or table depends on them (ADR-002). Appendix B lists the required fields; this component turns them into files.

#### C2-01 Agent Experience Contract schema and Python model

- **Files:** create `architecture/reference/api-specs/schemas/agent-experience-contract.v1.schema.json`; modify `src/agent-adapters/runtime_contract/employment.py` (add models); create tests `tests/contract/test_wc136_experience_contract.py`.
- **Steps:**
  1. Write the JSON Schema (draft 2020-12) for the `experience` section defined in Appendix B.1: required `contractVersion`, `vocabularyRef` (an `ImmutableContractReference`), `goalTypes`, `plan`, `operate`, `monitor`, `domainBlocks`, `components`, `audiences`, `modalities`, `channelSupport`, `conformanceScenarios`; closed `additionalProperties: false` everywhere; enums as in Appendix B.1 (component `kind`: `COUNTED`, `SELECTED`, `TIME_ACCESS`, `CAPACITY`; `availability`: `AVAILABLE`, `DEFAULT_OFF`, `UNAVAILABLE`).
  2. In `employment.py` add pydantic models `ExperienceComponent`, `ExperienceGoalType`, `ExperienceMonitor`, `ExperienceManifest` with the same constraints (`EmploymentModel` base, frozen, `extra="forbid"`), and add an optional field `experience: ExperienceManifest | None = None` to `EmploymentInterfaceManifest` (optional so existing agents still validate; the compatibility scan reports a missing section as a gap).
- **Unit tests to write:** DMA example validates; each required field removed fails; unknown field fails; component kind and availability enums enforced; duplicate `componentId` fails; a component whose `skillId` is absent from the manifest's operations fails.
- **Requirement:** WC136-R006.

#### C2-02 DMA experience declaration

- **Files:** modify `src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json` (bump `manifestVersion` to `1.1.0`, add `experience`); create `src/digital-marketing-agent/contracts/experience-components.v1.json` (component catalogue, below) referenced by the manifest; update the conformance scenario references; tests in `tests/contract/test_wc136_experience_contract.py` and the existing DMA employment tests.
- **Steps:** author the declaration from existing contracts, inventing nothing:
  - `goalTypes` from `planning-contract.v1.json`: `UNDERSTAND_CURRENT_POSITION` (measures `PROFILE_COVERAGE`, `MATURITY_EVIDENCE_COVERAGE`), `PRIORITIZE_MARKETING_IMPROVEMENTS` (`PRIORITY_ACTION_PROGRESS`), `PLAN_CONTENT_AND_CAMPAIGNS` (`PLAN_REVIEW_TIMELINESS`, `CALENDAR_READINESS`); measure units and evidence sources from `outcome-contract.v1.json`.
  - `components` (ids are the existing `costUnit` values so metering and catalogue agree): `CONTENT_PLAN` (COUNTED, skill `CONTENT_STRATEGY_AND_CALENDAR`, availability `DEFAULT_OFF`, package B1), `CONTENT_DRAFT` (COUNTED, `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`, `DEFAULT_OFF`, B1), `CONTENT_ASSET` (COUNTED, `VISUAL_AND_VIDEO_CONTENT`, `DEFAULT_OFF`, B1), `SOCIAL_PUBLICATION` (COUNTED, `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`, `DEFAULT_OFF`, B2, activation `FOUNDER_SEPARATE_DECISION`), `SOCIAL_OBSERVATION` (SELECTED with `selectableDimension {kind: SOCIAL_PLATFORM, maximum: 8}`, skill `MARKETING_PERFORMANCE_AND_IMPROVEMENT`, `DEFAULT_OFF`, B2), `AD_BOOST` (COUNTED, availability `UNAVAILABLE`, packages C to E are excluded), `PROACTIVE_MESSAGE` (COUNTED, platform component with no skill, availability `DEFAULT_OFF` until follow-up F2). Labels use the DMA vocabulary of spec section 3.22.
  - `monitor.tiles` for each customer outcome measure; `monitor.narratives` with the five-part structure of DMA 3.14.3 (what happened, what I learned, what I tried, what changes next month, what I need from you) and channels portal and WhatsApp text; `operate.approvalModes` `CUSTOMER_APPROVAL`, `EXCEPTION_APPROVAL`, `SYNTHETIC_APPROVAL` with the ladder from 3.14.1; `audiences` `customer_owner`, `delegate`, `steward`; `modalities` `text`.
  - `conformanceScenarios` list the C7 scenario ids.
- **Honest availability:** every sale-relevant component is `DEFAULT_OFF` or `UNAVAILABLE` today (the content-social manifest keeps B1 and B2 default-off and publication needs a separate Founder decision). The declaration must say so; a package may be priced and authorized but cannot go on sale until its components are available (C5-01 rule).
- **Unit tests to write:** the manifest validates against the C2-01 schema and model; component ids equal the content-social `costUnit` values; `AD_BOOST` is `UNAVAILABLE`; manifest digest references still resolve.
- **Requirement:** WC136-R006.

#### C2-03 Experience block schema v2

- **Files:** create `architecture/reference/api-specs/schemas/experience-blocks.v2.schema.json`; modify `src/business-platform/Services/Visitor/VisitorReply.cs` only to add the `schemaVersion` literal `"2.0"` acceptance while keeping `"1.0"`; tests `tests/contract/test_wc136_experience_contract.py` and `tests/business-platform.Tests/VisitorConversation/VisitorStateMachineTests.cs`.
- **Steps:** define `ExperienceReplyV2` `{schemaVersion: "2.0", state, cursor, blocks[]}` where every block is `{id, type, version, sensitivity, data, fallback[], spoken?, label?}`. Types and `data` shapes are in Appendix B.2: `TEXT`, `CHOICES`, `LIST`, `LINK` keep their v1 shapes; new `STATUS`, `METRIC`, `PLAN`, `DECISION`, `FORM`, `EVIDENCE`, `DOMAIN`. Rules encoded in the schema: at most 6 blocks, at most 3 choices, at most 10 list rows, at most one link, `fallback` contains only v1 types, `sensitivity` is `PUBLIC`, `CUSTOMER` or `SENSITIVE`, `DOMAIN` requires `domainBlockId` and a non-empty `fallback`, no block carries an authority field. The server never sends layout.
- **Unit tests to write:** every type validates with a minimal example; each limit violation fails; a v1 reply still validates as v1; unknown block type or version degrades through `fallback` in a pure function `render_with_fallback` (written in the contract test helper as the reference behavior).
- **Requirement:** WC136-R007.

#### C2-04 Workbench OpenAPI

- **Files:** create `architecture/reference/api-specs/agent-experience-workbench.openapi.yaml`.
- **Steps:** write the specification for every operation in Appendix B.3 with schemas, `Idempotency-Key` on commands, `X-Correlation-ID`, request header `X-Experience-Capabilities` (channel class, modality and highest supported block versions), RFC 7807 responses with the fixed error codes of Appendix B.5, security `bearerAuth`, `x-capability` trace on every operation (1.7, 2.5, 2.7, 4.5, 5.3, 5.4, 5.5, 6.5, 6.6, 9.1, 9.2), pagination (`cursor`, `limit` at most 100), and `ETag` or `expectedVersion` on every state-changing operation. Reuse existing component schemas by `$ref` to `conversational-employment-business-platform.openapi.yaml` and `customer-engagement-workspace-business-platform.openapi.yaml` rather than copying them.
- **Unit tests to write:** the contract test loads the file with a YAML parser, checks every operation has `operationId`, `x-capability`, an idempotency header for POST, the error responses, and that every `$ref` resolves; a negative-fixture file `architecture/reference/api-specs/agent-experience-negative-fixtures.yaml` (same schema as `conversational-employment-negative-fixtures.yaml`) with at least ten invalid payloads, each with `expected_invalid_reason`.
- **Requirement:** WC136-R008.

#### C2-05 Pricing Admin and WBE internal OpenAPI

- **Files:** create `architecture/reference/api-specs/pricing-admin-business-platform.openapi.yaml` (public admin slice) and `architecture/reference/api-specs/wbe-pricing-admin.openapi.yaml` (internal, `x-internal: true`, ServiceBearerAuth, same delegated-context text as `wbe-relationship-workspace.openapi.yaml`).
- **Steps:** specify every operation of Appendix B.4 for both slices; the admin slice requires role `pricing_admin` or `founder` on reads and drafts and `founder` plus step-up on authorize and activate; the safety operations require `pricing_admin` or `founder`. Money is integer paise; prices carry `taxTreatment: "GST_INCLUSIVE"`; every version object carries `effectiveFrom`, `supersedes`, `authorizedBy`, `evidenceId`. Add the new internal routes to `infrastructure/workload-identity/registry.yaml` as `business-platform -> billing-engine` grants, one line per route, with `operation` and the contract reference, following lines 81 to 84.
- **Unit tests to write:** contract test as C2-04; a test that every internal route in the new specification has a matching registry grant and no extra grant exists (extend `tests/contract/test_wc123_identity_contract.py` style).
- **Requirement:** WC136-R009.

#### C2-06 Deterministic client generation (the one permitted Docker use)

- **Files:** create `scripts/generate_wc136_clients.sh` modelled on `scripts/generate_wc120_clients.sh`; extend `web/scripts/generate-api.sh` only if a slice is not otherwise generated; generated output under `web/lib/api/generated/workbench-v1` and `web/lib/api/generated/pricing-admin-v1`; Python client under `src/professional-runtime/clients/generated/` is **not** needed (no Python caller).
- **Steps:** write the script (bundle each specification with the existing bundler script, generate `typescript-fetch` with `npmName=@waooaw/workbench-client` and `@waooaw/pricing-admin-client`, same additional properties as the WC-120 script, clean output directories first). Run it once. Commit nothing. Record the generator image tag and output file list in the story END line.
- **Unit tests to write:** none run; add `tests/contract/test_wc136_generated_clients.py` which asserts the generated directories contain an API file per tag and a model per named schema and that the script pins `openapitools/openapi-generator-cli:v7.17.0`.
- **Requirement:** WC136-R010.

#### C2-07 Contract test suite wiring and negative fixtures

- **Files:** `tests/contract/test_wc136_experience_contract.py` (completed across C2-01 to C2-05), `validation/engineering-validation.yaml`.
- **Steps:** add a catalog command `wc136-experience-contract: {shell: "pytest tests/contract/test_wc136_experience_contract.py tests/contract/test_wc136_generated_clients.py -q"}` and a gate `wc136:experience-contract` copying the `wc123:identity-contract` gate definition; add the gate to the same dependency lists where `wc123:identity-contract` appears so qualification includes it.
- **Unit tests to write:** extend `tests/validation_control/test_catalog_contract.py` expectations only if that test enumerates gates (read it; update the expected set accordingly).
- **Requirement:** WC136-R011.

### C3 - Spend accounts: ceilings, trial authority, resolver, fail-closed behavior, leases (wave W1s)

Goal (architecture 6.10, 6.10.2, 6.10.3): every metered call has exactly one account chosen on the server and pinned at reserve; the environment ceiling is configuration; trial is per relationship and per agent version; spending fails closed and does not serialize on one global lock. The wallet entity and the platform-owned account scopes arrive in C4; C3 builds the selection, configuration and enforcement logic they plug into.

#### C3-01 Configurable environment ceiling

- **Files:** create `src/business-platform/Services/EnvironmentSpendOptions.cs`; modify `Services/ConversationInferenceOwner.cs` (lines 214, 354, 388), `Services/WhatsAppTrafficBudget.cs` (lines 250, 428), `Services/ConversationEnvironmentSpendOwner.cs`, `Program.cs` (bind and validate options), `appsettings.json`; create SQL `infrastructure/postgres/init/99zzzzzzzz-wc136-01-environment-spend-ceiling.sql`; tests in `tests/business-platform.Tests/Conversation/` (new `EnvironmentSpendOptionsTests.cs`) and a PostgreSQL case in the existing environment spend tests (search `tests/business-platform.Tests` for `environment_spend`).
- **Steps:**
  1. `EnvironmentSpendOptions { SectionName = "EnvironmentSpend"; decimal HardMaximumInr { get; set; } = 500m; }` validated at startup: greater than 0 and at most `999_999_999_999m`, six decimal places at most, fail startup otherwise.
  2. Replace each `Math.Min(500m, x)` with `Math.Min(options.HardMaximumInr, x)` (the options object is injected; the static helper methods receive it as a parameter). Default stays 500 so Demo behavior is unchanged.
  3. SQL: drop the table check that limits `maximum_paise` to 50000 (look up the constraint by its definition in a `DO` block, as `48-wc112-trial-agent-version.sql` does) and replace it with `CHECK (maximum_paise >= 0)`. Idempotent per the SQL standard. The deploy-time maximum is enforced by BP; the database no longer encodes Demo's number.
  4. Add `EnvironmentSpend__HardMaximumInr` documentation to `src/business-platform/README.md` (a configuration table row). Terraform wiring for Production is follow-up F5.
- **Unit tests to write:** default 500 reproduces existing reservations; a configured 2,000 raises the ceiling; invalid values fail startup; the reservation never exceeds `min(hardMaximum, authority.MaximumSpendInr)`; no literal `500m` remains in `src/business-platform` (a source-scan test in `tests/scripts` style is acceptable).
- **Requirement:** WC136-R012.

#### C3-02 Remove the customer-level trial flag

- **Files:** modify `src/billing-engine/trial/service.py` (lines 66, 176 to 180, 224, 302), `src/ai-runtime/pse/router.py` (lines 330 to 336); update tests `tests/billing-engine/test_trial.py`, `tests/billing-engine/test_trial_postgres.py`, `tests/ai-runtime/test_pse_router.py`; update `architecture/reference/billing/customer-acquisition-spec.md` section 6 with a short superseded note.
- **Steps:** delete every read, write and delete of the Redis key `wbe:customer:{id}:mode` and the `redis` constructor dependency if nothing else uses it in `TrialService`; in `route_and_dispatch` keep only `if trial_entitled: tier = LlmTier.LOCAL` and remove the Redis branch (keep the `customer_id` and `redis_client` parameters accepted and unused for caller compatibility, with a comment naming this story). Trial status remains in PostgreSQL (`business.trial_allocations`).
- **Verification step (read only):** find how the governed generation path (`ConversationInferenceOwner`, `src/ai-runtime/conversation_generation*.py`) obtains a model for a TRIAL relationship. `route_and_dispatch` has no production caller (only tests). If the governed path does not force the free tier for `authority_kind = 'TRIAL'`, do not invent a design: record the finding in the END line and in the Implementation Record as an open constitutional note for the Founder; trial cost remains bounded by the trial units.
- **Unit tests to write:** trial start, expiry and conversion no longer touch Redis (a fake Redis records zero calls); a TRIAL-entitled dispatch uses LOCAL; a non-entitled dispatch ignores any Redis state; one customer's trial never changes another agent's tier.
- **Requirement:** WC136-R013.

#### C3-03 Trial per agent version, bound to verified identity

- **Files:** modify `src/business-platform/Controllers/SubscriptionsController.cs` (`TrialStartRequest` line 12 and `TrialStartAsync` line 50), `src/billing-engine/trial/router.py` (`TrialStartRequest`, `start_trial`), `trial/service.py` (`start_trial`), create SQL `99zzzzzzzz-wc136-02-trial-identity-claims.sql`; tests in `tests/business-platform.Tests/AcquisitionControllerTests.cs`, `tests/billing-engine/test_trial.py`, `tests/billing-engine/test_trial_postgres.py`.
- **Steps:**
  1. BP `TrialStartRequest` gains `string AgentVersion` (required, pattern `^[0-9]+\.[0-9]+\.[0-9]+$`, matching the existing `trial_allocations_agent_version_check`) and is forwarded to WBE; today BP sends only the agent type and WBE defaults the version to `1.0.0`, which defeats the per-version rule (FD6). Update the OpenAPI that describes it if one does.
  2. WBE request gains optional `identity_subject_hash` (the verified phone subject hash BP already holds for the customer, never the number). Create table `business.trial_identity_claims (identity_subject_hash TEXT NOT NULL, agent_type TEXT NOT NULL, agent_version TEXT NOT NULL, trial_id UUID NOT NULL REFERENCES business.trial_allocations(trial_id), claimed_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (identity_subject_hash, agent_type, agent_version))` owned by `wbe_owner`, granted to `wbe_app`, per the C3 SQL conventions.
  3. Add setting `TRIAL_IDENTITY_BINDING_MODE` (`OFF`, `RECORD`, `ENFORCE`; default `RECORD`). `RECORD` inserts the claim after the existing uniqueness check and never refuses; `ENFORCE` refuses a second trial for the same identity, agent type and version with HTTP 409 `TRIAL_ALREADY_USED_BY_IDENTITY`; `OFF` does nothing. Existing flows are unchanged under `RECORD`.
  4. Hiring never touches `trial_allocations` uniqueness (regression test): a customer with an ACTIVE hire of a version can still start that version's one trial.
- **Unit tests to write:** BP forwards the version; invalid version is rejected 400; WBE records the claim; ENFORCE refuses the second identity claim; a new version of the same agent is allowed; hire does not block trial; PostgreSQL constraint test for the claim key.
- **Requirement:** WC136-R014.

#### C3-04 Account classes and the resolver

- **Files:** create `src/business-platform/Services/Spend/SpendAccountClass.cs`, `SpendPurpose.cs`, `SpendAccountResolver.cs`, `Catalog/Spend/purpose-map.v1.json`; modify `Services/ConversationInferenceOwner.cs` (reserve path), `Services/WhatsAppTrafficBudget.cs`, `Program.cs`; create SQL `99zzzzzzzz-wc136-03-spend-account-pin.sql`; tests `tests/business-platform.Tests/Spend/SpendAccountResolverTests.cs` (new folder).
- **Steps:**
  1. Define enums `SpendAccountClass { Acquisition, SetupGrant, Trial, Subscription, PlatformFloor, Simulation }` and `SpendPurpose { AgentWork, Onboarding, PresalesOrMarketplace, PlatformSupport, SafetyFloor, Simulation }`.
  2. `purpose-map.v1.json` maps registered interaction contexts (`contextKey`, `phase`) to purposes. Enumerate the registered keys by reading `Services/ConversationContextProfileService.cs` and the context registry it uses; induction and onboarding phases map to `Onboarding`, portal guide and marketplace contexts map to `PresalesOrMarketplace`, billing and rights and Stop contexts map to `PlatformSupport` or `SafetyFloor`, all other relationship contexts to `AgentWork`. An unmapped context resolves to no account and the call is refused (`SPEND_PURPOSE_UNMAPPED`).
  3. `SpendAccountResolver.Resolve(RelationshipSpendInput input)` where the input carries `relationshipId?`, `authorityKind` (`TRIAL`, `ACCEPTED_OFFERING`, `NONE`, read from WBE through the existing gateway), `purpose`, `channel` and `isSimulation`. Output `SpendAccountDecision(AccountClass, RelationshipId?, SkillId?)` by the table: `SafetyFloor` -> PlatformFloor always; `Simulation` -> Simulation; `PresalesOrMarketplace` or `PlatformSupport` or no relationship -> Acquisition; `Onboarding` with a relationship -> SetupGrant; `AgentWork` with `TRIAL` -> Trial; with `ACCEPTED_OFFERING` -> Subscription; `AgentWork` with `NONE` -> refused (`SPEND_AUTHORITY_UNAVAILABLE`). A customer works in one agent at a time (FD5): the relationship is the focused relationship from the server-resolved context, never a client value.
  4. SQL: add nullable column `account_class TEXT` and `pinned_wallet_account_id UUID` to `business.conversation_inference_spend_coordinators` and `business.environment_spend_attempts` (idempotent `ADD COLUMN IF NOT EXISTS`), populated at reserve and never updated afterwards (extend the existing immutability guard only if one exists on those tables; otherwise add a trigger refusing updates to these two columns once set).
  5. Pin at reserve: `ConversationInferenceOwner.ReserveAsync` calls the resolver once, stores the decision on the coordinator row, and settlement, release and reconcile read the stored class and never call the resolver again.
- **Unit tests to write:** every row of the resolution table; unmapped context refused; client-supplied relationship ignored; decision stored at reserve and unchanged after a simulated trial-to-subscription conversion; two relationships of one customer resolve to their own accounts; marketplace purpose with a hired relationship resolves to Acquisition.
- **Requirement:** WC136-R015.

#### C3-05 Fail-closed behavior and the Base Specification B-3 amendment

- **Files:** modify `src/business-platform/Services/ConversationInferenceOwner.cs`, `Services/AuthenticatedOfferingUsageGateway.cs` (typed unavailability), `architecture/reference/agents/AGENT-BASE-SPEC.md` (section B-3, bump to version 1.1 with a version-history row), tests `tests/business-platform.Tests/Conversation/` (new `SpendFailClosedTests.cs`).
- **Steps:** implement the failure table of the architecture package 6.10.2 exactly: WBE unavailable means no metered dispatch and the call returns a typed result `SPEND_COMMERCIAL_UNAVAILABLE` that the conversation layer renders as the free-path disclosure (existing honest-limitation text, no new customer copy invented); breaker unavailable or exhausted means no money-spending dispatch while `PlatformFloor` calls continue; unknown outcome keeps the reservation on the pinned account and reports the work as unconfirmed; pricing configuration unavailable uses the last authorized pinned version. Amend B-3: the WBE row becomes "metered spending stops; free path with disclosure; no uncounted spend" and `wbe_unavailable` default becomes `fail_closed_free_path`; record the amendment in the Base Specification version history and in `tests/pipeline` if a test pins the old default (search for `continue_silent`).
- **Unit tests to write:** WBE unavailable produces zero provider dispatches and the typed result; PlatformFloor call succeeds with WBE down; unknown outcome keeps the reservation; the old default string is gone from the specification and from any compatibility scan expectation.
- **Requirement:** WC136-R019.

#### C3-06 Budget leases for the per-call spend path

- **Files:** create `src/business-platform/Services/Spend/EnvironmentSpendLeaseService.cs`; modify `Services/ConversationEnvironmentSpendOwner.cs`, `ConversationInferenceOwner.cs`, `WhatsAppTrafficBudget.cs`, `Program.cs`; create SQL `99zzzzzzzz-wc136-04-environment-spend-leases.sql`; tests `tests/business-platform.Tests/Spend/EnvironmentSpendLeaseTests.cs` plus PostgreSQL concurrency tests.
- **Steps:**
  1. Table `business.environment_spend_leases (lease_id UUID PRIMARY KEY, environment TEXT NOT NULL REFERENCES business.environment_spend_authorities(environment), holder TEXT NOT NULL, granted_paise BIGINT NOT NULL CHECK (granted_paise > 0), consumed_paise BIGINT NOT NULL DEFAULT 0, state TEXT NOT NULL CHECK (state IN ('ACTIVE','RETURNED','EXPIRED')), granted_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL)`, owner `bp_owner`.
  2. `EnvironmentSpendLeaseService` grants a lease under the existing advisory lock (the lock is now taken once per lease, not once per call): grant size is `min(options.LeaseSizeInr, remaining headroom)` where headroom counts settled actuals, all unresolved reservations and all active unexpired leases; add `EnvironmentSpend:LeaseSizeInr` (default 25) and `LeaseSeconds` (default 120) to the options and validate them.
  3. A per-call reservation draws from the holder's active lease in process memory guarded by a semaphore, writes its attempt row without taking the environment lock, and renews the lease when exhausted. Expired or returned leases release their unused amount; an unknown outcome still retains its reservation and the lease cannot return that amount.
  4. The ceiling stays strict: the sum of active leases plus unresolved reservations plus settled actuals never exceeds the ceiling (the invariant is tested on PostgreSQL under concurrency).
  5. Add option `EnvironmentSpend:Mode` = `GLOBAL_LOCK` (current behavior, default) or `LEASES`; Demo can switch without a code change; the default does not change behavior.
- **Unit tests to write:** invariant under 50 concurrent reservations; lease expiry returns headroom; unknown outcome blocks return; `GLOBAL_LOCK` mode produces exactly the previous results (regression); lease size never exceeds headroom.
- **Requirement:** WC136-R020.

### C4 - One Wallet, agent-version packages, metering and commercial lifecycle (wave W1w)

Goal (architecture 6.10.1, 6.11.1, 6.11.2): WBE keeps one balance entity, the Wallet; packages are keyed by agent version and made of components with cost recipes; component units and wallet credit are metered together; the commercial projection is durable; pro-rata exists. WBE follows its own existing SQL pattern: tenant id in every key and every query, no row-level-security policies, privileges revoked from `PUBLIC` and `business_app` and granted to `wbe_app` (see `99zzzzz-wc134-offering-usage.sql`).

Convergence mode: add setting `WALLET_AUTHORITY` to WBE configuration with values `LEGACY` (default; current allowance and bucket behavior), `SHADOW` (current behavior stays authoritative; every reserve, settle and release is mirrored into the wallet and compared) and `WALLET` (wallet authoritative; allocation tables become a projection). This contract delivers `LEGACY` and `SHADOW` and the code for `WALLET`; switching Demo to `WALLET` is a Founder-gated rollout step recorded in Rollout And Rollback.

#### C4-01 Wallet schema

- **Files:** create `infrastructure/postgres/init/99zzzzzzzz-wc136-05-wallet-entity.sql`; tests `tests/billing-engine/test_wc136_wallet_schema.py` (pure SQL-text checks) and `tests/billing-engine/test_wallet_entity_postgres.py` (real PostgreSQL, same fixture style as `test_offering_usage_postgres.py`).
- **Steps:** create, owned by `wbe_owner` and granted to `wbe_app` (SELECT, INSERT on append-only tables; UPDATE only on `wallet_reservations`): `business.wallet_accounts`, `business.wallet_lots`, `business.wallet_entries`, `business.wallet_reservations` exactly as Appendix A.1, with the unique, check and foreign-key constraints listed there; add immutability triggers on `wallet_lots` and `wallet_entries` (no UPDATE or DELETE) following `guard_offering_usage_immutable`; add the function `business.wallet_available(p_tenant UUID, p_account UUID, p_at TIMESTAMPTZ) RETURNS BIGINT` computing credits minus settled minus reserved minus expired lots at the instant, `STABLE`, `SECURITY INVOKER`.
- **Unit tests to write:** SQL text contains no non-idempotent statement; PostgreSQL: duplicate account key refused; lot immutability; entry immutability; `wallet_available` excludes expired lots and counts reservations; foreign tenant read returns nothing when queried with another tenant id.
- **Requirement:** WC136-R021.

#### C4-02 Wallet service

- **Files:** create `src/billing-engine/wallet/ledger.py` (new module; the existing `wallet/service.py` is not rewritten), `src/billing-engine/wallet/entity_models.py`; modify `src/billing-engine/config.py` (setting `WALLET_AUTHORITY`); tests `tests/billing-engine/test_wallet_ledger.py`.
- **Steps:** implement `WalletLedger` with `open_account(...)` (idempotent by the account key), `credit(account, lot_kind, paise, valid_from, valid_until, source_ref, pinned_versions, idempotency_key)`, `reserve(account, component_id, paise, expires_at, identity, idempotency_key)` which picks lots oldest-expiry first and fails with `WALLET_INSUFFICIENT` when `wallet_available` is lower, `settle(reservation_id, actual_paise, evidence_id)` (records actual overrun as an `ADJUST` entry and fences further admission on overrun beyond the configured tolerance), `release(reservation_id, non_dispatch_evidence_id)`, `expire(account, at)` (writes `EXPIRE` entries for lots past `valid_until`; no rollover and no refund), and `balance(account, at)`. Every operation is idempotent on `(tenant_id, idempotency_key, entry_kind)` and refuses a changed payload with `WALLET_IDEMPOTENCY_CONFLICT`. Reservation rows store `pinned_account_class` and `pinned_versions` at creation and later operations read them, never re-resolve. Lot kinds are exactly `PERIOD_CREDIT`, `TOPUP_CREDIT` and `GRANT`; there is no refundable kind (FD9).
- **Unit tests to write:** credit, reserve, settle, release, expire arithmetic; oldest-expiry lot order; insufficient balance; exact replay returns the stored receipt; changed replay conflicts; unknown outcome retains the reservation; expiry never moves value to another period; overrun beyond tolerance fences admission.
- **Requirement:** WC136-R021.

#### C4-03 Shadow mirroring and parity of the allocation tables

- **Files:** modify `src/billing-engine/meter/allowance_service.py` (reserve, settle, release, reconcile call a mirror hook when `WALLET_AUTHORITY` is `SHADOW` or `WALLET`), create `src/billing-engine/wallet/parity.py` and a read-only internal route in the new private router (C4-09) `GET /internal/v1/wallet/parity`; tests `tests/billing-engine/test_wallet_parity.py`, extend `tests/billing-engine/test_offering_usage_postgres.py`.
- **Steps:** for each allocation operation write the equivalent wallet operation (account = the relationship's SUBSCRIPTION or TRIAL scope, resolved from `relationship_commercial_authorities.authority_kind`) in the same database transaction; `parity.py` computes, per relationship and component, the allowance balance and the wallet balance and returns differences; in `SHADOW` a nonzero difference raises a metric and a log line but never fails the customer path; in `WALLET` mode the allowance tables are written as a projection of wallet entries and the same parity check guards them. Under `LEGACY` nothing changes (regression test).
- **Unit tests to write:** parity zero after a reserve-settle-release sequence; parity difference detected when a mirror write is dropped; `LEGACY` makes zero wallet writes; `SHADOW` mirrors every operation including replays exactly once.
- **Requirement:** WC136-R022.

#### C4-04 Platform-owned accounts: ACQUISITION, SETUP GRANT, TRIAL grants, SIMULATION, PLATFORM FLOOR

- **Files:** create `src/billing-engine/wallet/platform_accounts.py`, SQL `99zzzzzzzz-wc136-06-platform-accounts.sql`; modify `src/billing-engine/trial/service.py` (trial start credits a `GRANT` lot to the TRIAL account from the effective trial grant, C5), `src/business-platform/Services/Spend/SpendAccountResolver.cs` consumers, and the BP gateway (`Services/AuthenticatedOfferingUsageGateway.cs` adds `ReserveAccountAsync(accountClass, ...)` for non-relationship classes); tests `tests/billing-engine/test_platform_accounts.py`.
- **Steps:**
  1. `platform_accounts.py` opens platform-owned wallet accounts: ACQUISITION keyed (marketplace tenant, campaign reference or `DEFAULT`, optional lead reference), SETUP GRANT keyed (tenant, relationship), SIMULATION keyed (environment), PLATFORM FLOOR keyed (environment). Owner kind is `PLATFORM`; `owner_ref` is null.
  2. ACQUISITION enforces hierarchical caps from the effective BUDGET version (C5): environment breaker (BP) above marketplace tenant above campaign above lead; a reserve checks every level in one transaction and refuses with `ACQUISITION_BUDGET_EXHAUSTED` naming the exhausted level; the lead reference is a pseudonymous id, never a phone, name or email. Exhaustion makes the visitor path fall back to scripted replies (existing behavior; no new customer text).
  3. SETUP GRANT is created with the relationship (hook: where BP creates the relationship workspace, call WBE `POST /internal/v1/relationships/{id}/setup-grant` idempotently) from the effective setup grant for the agent version; onboarding turns draw only on it (resolver, C3-04); on exhaustion the call is allowed to continue on the SUBSCRIPTION scope only after the customer is told, through the typed result `SETUP_GRANT_EXHAUSTED` that the conversation layer renders with the existing honest-limitation text.
  4. TRIAL start credits the grant to the relationship TRIAL account (replacing `settings.TRIAL_FREE_UNITS` reads with the effective trial grant for the exact agent version; keep the settings value as the fallback when no grant version exists so existing tests and Demo do not break).
  5. SIMULATION has its own cap from the BUDGET version; PLATFORM FLOOR is never gated but every use is recorded and counted in telemetry.
  6. Simulated traffic is identified only by the server-verified `visitor-simulator` role or channel `SIMULATION` (the existing HMAC path), never by a client field.
- **Unit tests to write:** each account class opens idempotently; hierarchical cap exhaustion names the level; SIMULATION draws never touch ACQUISITION; PLATFORM FLOOR succeeds at zero balances; setup grant created once per relationship (replay creates none); a second relationship of the same customer gets its own; trial start credits the versioned grant and falls back to settings when none exists.
- **Requirement:** WC136-R016, WC136-R017, WC136-R018.

#### C4-05 Pricing versions and package tables

- **Files:** create `infrastructure/postgres/init/99zzzzzzzz-wc136-07-pricing-versions.sql`; tests `tests/billing-engine/test_wc136_pricing_schema.py`, `tests/billing-engine/test_pricing_versions_postgres.py`.
- **Steps:** create `institutional.pricing_versions` as in Appendix A.2 (append-only, one row per version of any kind, states `DRAFT, SIMULATED, SUBMITTED, AUTHORIZED, EFFECTIVE, SUPERSEDED, DISCARDED`; only the `state` and the three authorization columns of the current row may change, by an owner function, and every transition appends a row to `institutional.pricing_version_events`); alter `institutional.bundle_profiles`: add `agent_version TEXT`, `package_version_id UUID`, widen `bundle_tier` to `VARCHAR(64)` (package code, free-form), replace the unique key `uq_bundle_profile` by `(agent_type, agent_version, bundle_tier, bundle_version)` with a backfill of `agent_version` from the seeded rows (`1.0.0` for the DMA seed) before the new constraint is added, all idempotent; add `business.component_units` and `business.component_unit_entries` as in Appendix A.3.
- **Unit tests to write:** SQL text idempotency check; PostgreSQL: version uniqueness, illegal state transitions refused, only owner function can transition, widened tier accepts `STARTER`, backfill leaves the seeded DMA rows valid, new key refuses duplicates.
- **Requirement:** WC136-R023.

#### C4-06 Package projection and cost floor service

- **Files:** create `src/billing-engine/markup/package_engine.py`, `src/billing-engine/markup/package_models.py`; modify `markup/bundle_engine.py` (read agent version), `markup/router.py` (existing routes keep working); tests `tests/billing-engine/test_package_engine.py`.
- **Steps:** pydantic models for the PACKAGE version body (Appendix A.2): `agentType`, `agentVersion`, `packageCode`, `displayName`, `billingPeriodDays`, `priceInclGstPaise`, `gstRatePercent` (default 18), `infrastructureSharePaise`, `components[]` (`componentId`, `kind`, `quantity`, `cadence`, `selectableMaximum`, `priceAllocationPaise`, `recipe[]` of `{threadId, unitsPerUnit}`, `topupAllowed`). `package_engine.py` computes: base price excluding GST (`round(priceInclGst / (1 + rate/100))`), cost floor (sum over components of `quantity` times recipe unit costs from the effective thread catalogue entries plus infrastructure share), margin on revenue, and the minimum compliant price (`ceil(costFloor / (1 - minimumMarginPct/100))` then re-add GST); validates the rules of the architecture package 6.11.1: allocations sum exactly to the package price, every recipe thread has an ACTIVE Founder-authorized catalogue entry (C-091), the agent version has an authorized billing profile (C-088), every `componentId` exists in the agent version's declaration and its kind matches, cadence consistent with quantity over the period (rule 1), `PROACTIVE_MESSAGE` present with quantity 30 (FD16) in every package, and sale readiness: a package may be AUTHORIZED while its components are `DEFAULT_OFF` or `UNAVAILABLE`, but it cannot be activated for sale until every component is `AVAILABLE` (returns `PACKAGE_COMPONENT_NOT_AVAILABLE` naming the component). Authorizing a package writes the derived `bundle_profiles` row (projection) with `thread_rations` computed from the recipes so the existing allowance code keeps working.
- **Unit tests to write:** the DMA illustration (floor 19,628 paise excluding proactive messages, base 169,492 paise, margin about 88 percent); below-floor price rejected with the minimum compliant price; allocation mismatch; missing recipe thread; unknown component id; kind mismatch; cadence contradiction; availability gate; derived `thread_rations`; rounding is deterministic.
- **Requirement:** WC136-R023.

#### C4-07 Thread catalogue entries for voice and template messages

- **Files:** create `infrastructure/postgres/init/99zzzzzzzz-wc136-08-thread-catalogue-pending.sql`; tests `tests/billing-engine/test_thread_catalog.py` additions.
- **Steps:** insert, idempotently (`ON CONFLICT DO NOTHING`), catalogue rows with `status = 'PENDING_FOUNDER_AUTH'` and `founder_authorized_at = NULL`: `stt_audio_minute` (speech to text, unit per audio minute), `tts_character_1k` (text to speech, per 1,000 characters), `whatsapp_template_utility`, `whatsapp_template_marketing`, `whatsapp_template_authentication` (unit per message). Raw cost values are `0` with a `notes` text "value to be entered through the Pricing Console by the Founder", so no price is invented. Existing code refuses to price against entries that are not ACTIVE and authorized, which is the intended fail-closed behavior.
- **Unit tests to write:** rows exist after replay; none is ACTIVE; a package referencing one cannot be authorized (`RECIPE_THREAD_NOT_AUTHORIZED`).
- **Requirement:** WC136-R024.

#### C4-08 Component units, kinds and pacing

- **Files:** create `src/billing-engine/meter/component_units.py`, modify `src/billing-engine/relationship_workspace.py` (private router adds routes in C4-09), create BP gateway `src/business-platform/Services/AuthenticatedComponentUnitGateway.cs`; BP hook at the owner-confirmed work-item completion point (find by searching `ConversationalEmploymentService.cs` and `EmploymentCommandCoordinator.cs` for the transition to COMPLETED); tests `tests/billing-engine/test_component_units.py`, `tests/business-platform.Tests/ComponentUnitGatewayTests.cs`.
- **Steps:**
  1. `component_units.py` implements the four kinds: COUNTED consumes one unit on `consume(relationship, component, completion_evidence_id)`, idempotent on the evidence id, and only when the owner-confirmed outcome is COMPLETED (transport acceptance, model output and optimistic UI state never count; ADR-051); SELECTED occupies a slot on `select(relationship, component, item_ref, connection_proof)` only with a verified connection proof, refuses beyond the maximum, allows a configurable number of swaps per period; TIME_ACCESS consumes nothing per use and records period access; CAPACITY counts at `close(session_ref)`.
  2. Pacing: units are released on the declared cadence (default SPREAD): `available_units(relationship, component, at)` is `min(quantity, floor(quantity * elapsed/period))` rounded up to the next cadence boundary; a consume beyond the released amount returns `COMPONENT_NOT_YET_RELEASED` (the agent defers; no cost).
  3. Counting a unit and settling its wallet cost are separate operations: a deliverable that fails and is retried consumes no unit, its cost still settles against the wallet within the configured tolerance, and an actual cost above the tolerance falls back to the cheaper path (the tolerance is the `GRANT`-independent configuration value of the PACKAGE version, default 20 percent over recipe cost, alert at 10 percent, FD19).
  4. BP hook: when a work item reaches the owner-confirmed COMPLETED state and its declared component id is known from the agent declaration, call the gateway (`POST /internal/v1/relationships/{id}/component-units/consume`) with the completion evidence id; a gateway failure never blocks the work item (queued for retry through the existing outbox pattern).
- **Unit tests to write:** each kind's happy and refusal paths; idempotent consume; retry does not double count; pacing curve for 4 units in 30 days; consume before release refused; SELECTED slot swaps limit; failed connection consumes no slot; BP hook calls once per completion and survives gateway failure.
- **Requirement:** WC136-R025, WC136-R026.

#### C4-09 Durable commercial projection and commands

- **Files:** modify `src/billing-engine/relationship_workspace.py` (replace the in-memory `self._projections` and `self._commands` at lines 227 to 228), create SQL `99zzzzzzzz-wc136-09-commercial-projection.sql`; tests `tests/billing-engine/test_relationship_workspace.py` additions and a PostgreSQL test file `tests/billing-engine/test_commercial_projection_postgres.py`.
- **Steps:** persist projections and commands in two tables `business.commercial_projections (tenant_id, relationship_id, projection_version, body JSONB, produced_at, valid_until, PRIMARY KEY (tenant_id, relationship_id, projection_version))` and `business.commercial_commands (command_id UUID PRIMARY KEY, tenant_id, relationship_id, idempotency_key UUID, request_digest, command_kind, status, receipt JSONB, outcome JSONB, accepted_at, resolved_at, UNIQUE (tenant_id, relationship_id, idempotency_key))`, owned by `wbe_owner`; the in-process dictionaries are removed; replay and conflict behavior is preserved exactly (`WBE_COMMERCIAL_CONFLICT`); the projection body is built from the wallet (components remaining, period end, wallet scope balance in business language, never provider units; WBE owner contract section 2 text) and replaces the placeholder "Budget unavailable" (line 239); `Zero is not unknown` rule stays.
- **Unit tests to write:** state survives a service restart (new service instance reads the stored rows); replay returns the stored receipt; changed replay conflicts; projection reflects reserve and settle; stale projection blocks consequential commands (`UNAVAILABLE`).
- **Requirement:** WC136-R027.

#### C4-10 Pro-rata and lifecycle commands

- **Files:** create `src/billing-engine/payment/prorata.py`, modify `src/billing-engine/relationship_workspace.py` (command handling for `PAUSE_RELATIONSHIP`, `RESUME_RELATIONSHIP`, `RENEW_RELATIONSHIP`, `TERMINATE_RELATIONSHIP`, plus new `UPGRADE_PACKAGE`, `DOWNGRADE_PACKAGE`), `payment/paid_activation.py` (credit the wallet on activation), `wallet/service.py` (`renew`); tests `tests/billing-engine/test_prorata.py`, `tests/billing-engine/test_lifecycle_commands.py`.
- **Steps:** implement the rules of architecture 6.11.2 and FD9, FD18: hire credits a `PERIOD_CREDIT` lot to the SUBSCRIPTION scope (and per-skill sub-wallets) sized from the package recipes at the pinned versions and sets the period; renewal credits a new lot and lets the old lapse; payment failure starts a grace period (`PAYMENT_GRACE_DAYS` read from the effective POLICY version, no default in code beyond Demo seed in C5-06) then moves the relationship commercially to suspended; upgrade is immediate with a pro-rated fee difference and pro-rated new components; downgrade is recorded to take effect at the next renewal; pause and terminate compute `refund_fee_paise = round(allocated_fee_share * remaining_seconds / period_seconds)` for the paused skill's components (pause) or the whole package (terminate), recorded as a billing adjustment through the existing Razorpay path and never as a wallet refund; remaining wallet credit lapses; delivered work is kept. The renew and terminate commands no longer return BLOCKED when the effective POLICY version permits them; if no policy version exists they still return BLOCKED with the reason (fail closed).
- **Unit tests to write:** property tests that allocations sum to the price and that pro-rata refund equals the time-pro-rated allocation to the paisa; pause of one skill touches only its share; terminate on day 12 of 30; upgrade and downgrade timing; grace expiry; BLOCKED when policy absent; no wallet refund entry is ever written.
- **Requirement:** WC136-R028.

#### C4-11 Cost telemetry with pseudonymous leads

- **Files:** modify `src/billing-engine/telemetry.py`, `src/business-platform/Services/Visitor/VisitorTelemetry.cs`, `Services/ConversationInferenceOwner.cs`; tests `tests/billing-engine/test_wc107_telemetry.py` additions, `tests/business-platform.Tests/VisitorConversation/VisitorOperationsTests.cs` additions.
- **Steps:** emit structured events and metrics per account class: `spend_reserved`, `spend_settled`, `spend_released`, `spend_denied` with fields `accountClass`, `tenantId`, `relationshipId?`, `skillId?`, `componentId?`, `campaignRef?`, `leadRef?` (pseudonymous), `paise`, `reasonCode`; metric names `waooaw_spend_paise_total{class}`, `waooaw_spend_denied_total{class,reason}`, `waooaw_wallet_parity_difference`, `waooaw_live_margin_floor_breach`. No phone, name, email, message text or token appears in any field (C-063).
- **Unit tests to write:** event schema; log-capture test asserting no personal data across all outcomes; metrics increment once per operation and not on replay.
- **Requirement:** WC136-R029.

#### C4-12 Proactive-message component accounting

- **Files:** create `src/billing-engine/meter/proactive_messages.py`; BP `Services/WhatsAppOutboxService.cs` classification only (no send enablement); tests `tests/billing-engine/test_proactive_messages.py`, `tests/business-platform.Tests/ConversationWhatsAppFitness/ProactiveClassificationTests.cs`.
- **Steps:** define the classification of an outbound message as `PROACTIVE_COUNTED` (agent alert, reminder or narrative sent outside an open customer-service window, needs a template), `PROACTIVE_UNCOUNTED` (capacity notice or emergency alert; funded by PLATFORM FLOOR) or `REPLY` (inside the window); implement the counter against the `PROACTIVE_MESSAGE` component of the relationship's package (30 per period, FD16); after the included quantity the typed result `PROACTIVE_ALLOWANCE_EXHAUSTED` makes the caller deliver in the portal and the next turn instead; trial relationships have no allowance. **Nothing in this story enables a proactive send**: the WC-134 release policy still refuses proactive messages, and the classification and counter run only when a caller asks (tests call them directly); enabling sending is follow-up F2.
- **Unit tests to write:** classification table; counter increments only for `PROACTIVE_COUNTED`; the 31st message is refused with the typed result; capacity notices never count and never block; trial has none; an attempt to send proactively while the WC-134 policy is off is still refused (regression).
- **Requirement:** WC136-R030.

#### C4-13 Customer-facing package and wallet reads

- **Files:** BP `Controllers/PackagesController.cs` (new), `Controllers/WorkbenchController.cs` additions in C6, `Services/PackageCatalogService.cs`, WBE internal read routes in the C4-09 private router; modify `web/app/api/acquisition/hire-preview/route.ts` and the BP acquisition hire-preview to include components, period and the GST-inclusive price; tests `tests/business-platform.Tests/PackagesControllerTests.cs`, `web/app/api/acquisition/hire-preview/route.test.ts`.
- **Steps:** `GET /api/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages` returns only EFFECTIVE packages whose state is for-sale, with price including GST, base, GST, period, and components in agent vocabulary (label, quantity, cadence, selectable maximum); never provider units, costs, margins or recipes. The customer wallet read returns components remaining and period end only.
- **Unit tests to write:** only for-sale packages listed; no cost or recipe field present (schema test); hire preview includes components; unauthorized wallet read refused; foreign relationship refused.
- **Requirement:** WC136-R023.

### C5 - Pricing And Spend Console on Demo (wave W1c)

Goal (architecture 6.11): an administrator configures rates, packages, grants, budgets, ceilings and coupons through screens; every change is a versioned draft that is simulated, authorized by the Founder, and then effective; nothing is a constant in code. The console is a web admin route group; Business Platform is the only public facade; WBE is reached only through the ADR-046 private boundary.

#### C5-01 Pricing engine core in WBE

- **Files:** create `src/billing-engine/pricing/__init__.py`, `engine.py`, `validators.py`, `models.py`, `service.py`; tests `tests/billing-engine/test_pricing_engine.py`, `tests/billing-engine/test_pricing_validators.py`.
- **Steps:**
  1. `engine.py` implements the state machine of Appendix A.2 (`DRAFT -> SIMULATED -> SUBMITTED -> AUTHORIZED -> EFFECTIVE -> SUPERSEDED`, plus `DISCARDED` from any non-effective state); transitions only through the owner database function created in C4-05; each transition appends an event row. Editing is allowed only in `DRAFT`; a changed draft returns to `DRAFT` and loses its simulation. Versions are never edited in place (DP-005).
  2. `validators.py` holds one validator per kind (`RATE`, `PACKAGE`, `POLICY`, `GRANT`, `BUDGET`, `COUPON`) returning machine-readable violations: RATE (catalogue entry exists, non-negative components, total markup computed); PACKAGE (C4-06 rules); POLICY (`minimumMarginPct` Founder only; `paymentGraceDays`, `sunsetNoticeDays`, `costToleranceFraction`, `costAlertFraction`, `upgradeTiming`, `downgradeTiming`, `changeSizeGuardPercent`, `priceMultipleGuard`); GRANT (kind `TRIAL` or `SETUP`, agent type and version, thread units or paise, duration); BUDGET (scope `ENVIRONMENT_CEILING`, `ACQUISITION_TENANT`, `ACQUISITION_CAMPAIGN`, `ACQUISITION_LEAD`, `SIMULATION`; the ceiling must not exceed the deploy-time maximum passed by BP in the request); COUPON (reuse `business.coupon_codes`; discount never below the cost floor, C-089).
  3. Authorization rules (service layer, independent of the HTTP role check): `authorizedBy` must hold the Founder role in the signed context and the context must carry step-up; an administrator can create, edit, simulate, submit and discard but never authorize or activate; **safety-direction operations** (lower a ceiling, close a package to new customers, disable a grant) are separate operations allowed to `PRICING_ADMIN` or `FOUNDER` that take effect immediately, append an event with `direction = SAFETY`, and raise a Founder notification event.
  4. Change-size guard: a draft that moves a price, rate or ceiling by more than `changeSizeGuardPercent` from the current effective version, or prices a package above `priceMultipleGuard` times its cost floor, is marked `NEEDS_SECOND_CONFIRMATION`; submit requires the explicit confirmation flag.
  5. Effective dating: authorizing sets `effectiveFrom` (default now, or a future instant); at `effectiveFrom` the previous effective version of the same subject becomes `SUPERSEDED`; existing customers keep the version pinned at their activation or last renewal (C-090).
  6. Constitutional evidence: every authorization records evidence through the existing CE validator (`ce_validator.py`) before the transition commits; unavailability of CE fails the authorization closed.
- **Unit tests to write:** every legal and illegal transition; admin cannot authorize; authorize without step-up refused; safety operations immediate and logged; change-size guard; effective dating and supersession; ceiling above the deploy maximum refused; margin policy changes only by Founder; CE unavailable fails closed; versions immutable (no update path).
- **Requirement:** WC136-R031.

#### C5-02 Simulator and live-margin watch

- **Files:** create `src/billing-engine/pricing/simulator.py`, `src/billing-engine/pricing/margin_watch.py`; tests `tests/billing-engine/test_pricing_simulator.py`.
- **Steps:** `simulate(draft)` returns for a PACKAGE draft: cost floor, base price, GST, margin, minimum compliant price, the diff from the current effective version, and per-profile expected monthly cost for three built-in usage profiles (`BEST_CASE` uses 20 percent of every quantity, `TYPICAL` 60 percent, `WORST_CASE` uses everything on day one then terminates on day two, and shows that pacing limits the day-one exposure and what the pro-rata refund would be), plus any persona from a supplied usage profile file; it also reports `NEEDS_SECOND_CONFIRMATION` and `PACKAGE_COMPONENT_NOT_AVAILABLE` warnings. For RATE drafts it lists every EFFECTIVE package whose floor would change. `margin_watch.recompute()` recomputes every effective package at current rates and returns packages below their floor or the minimum margin; run after every RATE authorization and on a daily schedule (use the existing scheduler module `scheduler.py` pattern) and emit `waooaw_live_margin_floor_breach`.
- **Unit tests to write:** the DMA illustration numbers; best, typical and worst profiles; rate change flags affected packages; breach detected after a rate rise and cleared after repricing; simulation never writes state.
- **Requirement:** WC136-R032.

#### C5-03 Admin API: WBE internal routes, workload grants, BP gateway and controller

- **Files:** create `src/billing-engine/pricing_admin.py` (private router and `configure_pricing_admin(app)` modelled on `relationship_workspace.py`); modify `src/billing-engine/main.py` (include the router next to `relationship_workspace_router`); modify `infrastructure/workload-identity/registry.yaml` (one grant line per internal route, C2-05); create BP `Services/AuthenticatedPricingAdminGateway.cs` (modelled on `AuthenticatedOfferingUsageGateway.cs`), `Controllers/PricingAdminController.cs`, `Services/PricingAdminService.cs`; modify `Program.cs`; tests `tests/billing-engine/test_pricing_admin_router.py`, `tests/business-platform.Tests/PricingAdminControllerTests.cs`, `tests/business-platform.Tests/PricingAdminGatewayTests.cs`.
- **Steps:**
  1. WBE: every route verifies the delegated context through a copy of `_authorize` that does not bind a relationship (it binds route, operation, method, digest, correlation id, idempotency key and requires `effective_role` in `PRICING_ADMIN` or `FOUNDER`); authorize and activate additionally require `FOUNDER`. The BP signer sends the nil relationship id `00000000-0000-0000-0000-000000000000` and `subject_reference` equal to the draft or subject key. If the BP signer cannot express a non-relationship context without changing the ADR-046 envelope fields, stop and raise a blocker (do not alter ADR-046).
  2. BP controller `[ApiController] [Authorize] [Route("api/v1/admin/pricing")]`: copy `AgentAdmissionsController.IsRole` and `HasStepUp`; reads and drafts require `pricing_admin` or `founder`; authorize and activate require `founder` and step-up; every state-changing call requires `Idempotency-Key` and `X-Correlation-ID`; responses are RFC 7807 with the error codes of Appendix B.5; the controller never returns raw WBE errors. No customer route attribute is used (this is not a customer route).
  3. Rate-limit state-changing admin calls per subject (reuse the middleware pattern in Program.cs near `AddPolicy`).
- **Unit tests to write:** role matrix (anonymous, customer, `pricing_admin`, `founder`) on every operation; step-up required for authorize; idempotent replay; WBE error mapping; registry grant set equals route set (extend the C2-05 test); delegated-context binding failure paths.
- **Requirement:** WC136-R033.

#### C5-04 Environment ceiling and budget administration

- **Files:** modify `src/business-platform/Services/PricingAdminService.cs`, `ConversationEnvironmentSpendOwner.cs` (read effective BUDGET version into `environment_spend_authorities` through an owner function), SQL `99zzzzzzzz-wc136-10-budget-authority-function.sql`; tests `tests/business-platform.Tests/Spend/BudgetAdministrationTests.cs`.
- **Steps:** authorizing a BUDGET version with scope `ENVIRONMENT_CEILING` updates `business.environment_spend_authorities.maximum_paise` through an owner-defined `SECURITY DEFINER` function that refuses a value above `EnvironmentSpendOptions.HardMaximumInr * 100` (passed in) and refuses lowering below currently reserved and settled amounts in the window (it would otherwise strand open reservations; the response names the blocking amount); safety-direction lowering is immediate. ACQUISITION and SIMULATION budgets are read by the C4-04 account code. Demo is seeded at INR 500 (C5-06).
- **Unit tests to write:** raise within maximum; raise above maximum refused; lower below open reservations refused with the amount; lowering is immediate and reported; scope mapping to `environment_spend_authorities` versus platform account caps.
- **Requirement:** WC136-R033.

#### C5-05 Console screens

- **Files:** create `web/app/(application)/admin/pricing/page.tsx`, `.../pricing/rates/page.tsx`, `.../pricing/packages/page.tsx`, `.../pricing/packages/[draftId]/page.tsx`, `.../pricing/policy/page.tsx`, `.../pricing/grants/page.tsx`, `.../pricing/budgets/page.tsx`, `.../pricing/coupons/page.tsx`, `.../pricing/dashboard/page.tsx`; components `web/components/admin/pricing/*` (`PackageEditor.tsx`, `ComponentRow.tsx`, `RecipeEditor.tsx`, `SimulatorPanel.tsx`, `VersionDiff.tsx`, `AuthorizeDialog.tsx`, `SafetyControls.tsx`, `BudgetEditor.tsx`, `GrantEditor.tsx`, `CouponEditor.tsx`, `LiveMarginBanner.tsx`, `ExportImport.tsx`), each with a colocated `*.test.tsx`; API routes `web/app/api/admin/pricing/[...path]/route.ts` (one catch-all that maps an allow-list of paths to the generated pricing-admin client), `web/lib/pricing-admin.ts` (role helpers), `web/lib/identity-claims.ts` (add `hasPricingAdminClaim` for realm role `pricing_admin` or `founder`).
- **Steps:**
  1. Pages follow the pattern of `web/app/(application)/admin/azure-key-vault/page.tsx`: server component gets the access token, redirects to `/home` when the role is absent, renders the client component. `middleware.ts` already protects the `admin` prefix; add nothing there.
  2. API route follows `app/api/admin/azure-key-vault/route.ts`: `sameOrigin` check, role check, per-subject write limiter, body size cap, generated client only, no secret or token in logs; only the allow-listed paths of the pricing-admin specification pass through.
  3. The package editor shows: agent type and version selectors (from the AEC component catalogue: component availability badges `AVAILABLE`, `DEFAULT_OFF`, `UNAVAILABLE`), package code and name, price including GST with the derived base, GST and margin, billing period, component table (kind, quantity, cadence, selectable maximum, price allocation with a running sum against the price, recipe rows with catalogue thread pickers and live unit cost), the proactive message row fixed at 30, and the simulator panel (cost floor, margin, three usage profiles, warnings). Authorize is available only to the Founder role and opens `AuthorizeDialog` (diff against the current version, floor, margin, availability and billing-profile gates, a second confirmation for guarded changes, then the step-up flow). Safety controls (lower ceiling, close to new customers, disable grant) are separate buttons visible to both roles with a clear "takes effect now" notice. Catalogue ids may appear on these admin pages only; customer pages never show provider units.
  4. Accessibility: every control labelled, keyboard operable, focus returns after dialogs, errors announced (`aria-live`), no color-only meaning.
- **Unit tests to write:** per component (render, role gating, validation messages, sum-of-allocations indicator, authorize disabled for administrator, guarded change requires confirmation, error rendering); route tests (origin check, role check, allow-list, limiter, size cap); `hasPricingAdminClaim` cases.
- **Requirement:** WC136-R034.

#### C5-06 Seeded Demo baseline, export and import

- **Files:** create `infrastructure/postgres/init/99zzzzzzzz-wc136-11-demo-pricing-baseline.sql`; create WBE `pricing/export_import.py`; BP admin operations `GET /api/v1/admin/pricing/versions/export` and `POST /api/v1/admin/pricing/versions/import`; web `ExportImport.tsx`; tests `tests/billing-engine/test_pricing_export_import.py`.
- **Steps:**
  1. The baseline SQL inserts, idempotently, versions flagged `seed = true`: EFFECTIVE for a POLICY version (`minimumMarginPct` 55 as the architecture's suggested value marked `SEED_UNCONFIRMED`, `paymentGraceDays` 7, `sunsetNoticeDays` 30, `costToleranceFraction` 0.20, `costAlertFraction` 0.10, `changeSizeGuardPercent` 30, `priceMultipleGuard` 20, upgrade immediate, downgrade at renewal; FD18 and FD19), a BUDGET version for `ENVIRONMENT_CEILING` of 50,000 paise (INR 500, FD3), BUDGET versions for ACQUISITION tenant and SIMULATION with small caps, and a TRIAL and a SETUP grant for the DMA version `1.0.0`; and one illustrative DMA PACKAGE `STARTER` priced INR 2,000 including GST, inserted as a `DRAFT` with `seed = true` and the note `ILLUSTRATIVE_NOT_FOR_SALE`, whose components are those of C2-02. It stays a draft on purpose: its proactive-message recipe references pending catalogue entries (C4-07) and its publication components are default-off, so it cannot be authorized yet, which is the intended honest state and lets the simulator and the validators be demonstrated on Demo without any price becoming effective. Production values are never seeded; Production is configured only through the console (follow-up F5).
  2. Export returns a signed, versioned JSON bundle of all EFFECTIVE and AUTHORIZED versions with digests; import validates every entry through the same validators and creates them as `DRAFT` versions (never directly effective), so a Demo reset is recovered by import then Founder authorization.
- **Unit tests to write:** baseline replays idempotently; seed rows are flagged; export round trip; import creates drafts only; tampered digest refused; import of a below-floor package is refused by the validator.
- **Requirement:** WC136-R035.

#### C5-07 Coupons as the goodwill mechanism

- **Files:** modify `src/billing-engine/promotions/` (existing coupon service) to read COUPON versions; BP admin operations in the C5-03 controller; tests `tests/billing-engine/test_promotions.py` additions.
- **Steps:** a COUPON version carries code, agent type and version, percentage or amount, cap, expiry, reason and maximum redemptions; validation refuses a price below the cost floor (C-089); redemption applies at hire or renewal only, is recorded with the reason, and is the only goodwill path: there is no operation that credits a wallet outside the `PERIOD_CREDIT`, `TOPUP_CREDIT` and platform `GRANT` lots created by the flows in this contract (add a test that scans the wallet service for any credit entry point not named in the contract).
- **Unit tests to write:** below-floor coupon refused; expiry and cap; redemption at renewal; no support credit path exists.
- **Requirement:** WC136-R036.

#### C5-08 Funding and margin dashboard

- **Files:** create WBE `pricing/dashboard.py` read functions and internal routes; BP `GET /api/v1/admin/pricing/dashboard/funding` and `.../margin`; web `dashboard/page.tsx` and `FundingDashboard.tsx`; tests `tests/billing-engine/test_pricing_dashboard.py`, `FundingDashboard.test.tsx`.
- **Steps:** read-only views from the C4-11 telemetry tables and wallet entries: spend per account class, tenant and campaign; cost per lead and per conversation; trial-to-hire conversion; trial and setup grant consumption; actual versus recipe cost per component with implied margin and tolerance state; exhaustion and top-up events; breaker state; live-margin breaches. Aggregates only; no personal data; lead references are pseudonymous.
- **Unit tests to write:** aggregates on fixed ledger data; no personal fields in the response schema; empty states; role gating.
- **Requirement:** WC136-R037.

### C6 - Workbench projection, blocks, Web workbench and DMA wiring (wave W2, DMA only)

Goal (architecture 6.1 to 6.6): one Business Platform workbench projection and command set that Web, WhatsApp and the future Mobile client render; DMA is the first agent to declare it. The three existing projections keep working through a shim (retirement is wave W7, out of scope).

#### C6-01 Workbench projection service

- **Files:** create `src/business-platform/Services/Workbench/WorkbenchProjectionService.cs`, `WorkbenchModels.cs`, `WorkbenchAudience.cs`, `ExperienceDeclarationReader.cs`; modify `Program.cs`; tests `tests/business-platform.Tests/Workbench/WorkbenchProjectionServiceTests.cs`.
- **Steps:**
  1. Compose, never copy: `WorkbenchProjectionService` reads from the existing owners only: `RelationshipWorkspaceController`'s underlying services for plan, goals, business outcomes, performance, operations, work, results, usage and budget, rights (`GET plan`, `goals`, `business-outcomes`, `performance`, `operations`, `work`, `results`, `usage-budget`, `rights-controls`, `attention`; reuse the services behind them, do not call controllers), `ConversationalEmploymentService` for phases, readiness and commands, `CustomerEngagementWorkspaceService.GetProgressAsync` for progress items and focus, and the WBE commercial projection (C4-09) for components remaining and period end.
  2. `ExperienceDeclarationReader` loads the admitted immutable experience declaration of the relationship's exact agent version (from the admitted manifest, never from repository text at request time) and supplies goal types, measures, monitor tiles, narratives, components and audiences.
  3. Output `WorkbenchProjectionV1` per Appendix B.3: phase and readiness, current goal and plan version, decisions queue (each with effect, authority, cost, confirm and cancel as typed fields), monitor tiles with value against target and freshness, components remaining and period end, alerts, evidence state and source freshness, `limitations`, `recommendedNextAction`, `availableCommands`. Every item carries owner and freshness; progress is derived from declared requirements, never an unexplained percentage (ADR-051 section 3).
  4. Audience filtering: `WorkbenchAudience` (`customer_owner`, `delegate`, `beneficiary`, `steward`) is derived from the authenticated membership and the declaration; a beneficiary projection omits every money, price, top-up and purchase field and replaces exhaustion with "ask the account owner" semantics; a steward receives trace references; this is enforced in the projection service, not in the client.
  5. Money in the projection is customer language only (components remaining, period end); provider units, costs, margins and recipes never appear (WBE owner contract section 2).
- **Unit tests to write:** composition from fake owner services; missing owner yields `limitations` and `UNAVAILABLE` item state, not a thrown error; audience filtering matrix including beneficiary money exclusion; freshness and owner on every item; no percentage field without declared basis; no provider-unit field in the serialized output (schema test).
- **Requirement:** WC136-R038, WC136-R042.

#### C6-02 Workbench controller and commands

- **Files:** create `src/business-platform/Controllers/WorkbenchController.cs`; modify `Program.cs`; tests `tests/business-platform.Tests/Workbench/WorkbenchControllerTests.cs`, extend `tests/contract/test_business_platform_openapi_regressions.py` for the new specification.
- **Steps:** `[ApiController] [Authorize] [CustomerIdentityRoute(requiresMembership: true)] [Route("api/v1/employment/relationships/{relationshipId:guid}/workbench")]`; implement every operation of the C2-04 specification by delegating to existing owners: goal create and revise through the existing goal endpoints' services, plan accept through `ConversationalEmploymentService` commands, capability commands through the skill decision services, decisions resolve through the existing skill and contract decision commands, `controls/stop` through `RelationshipEmergencyStopService`, `controls/pause` through the relationship lifecycle service, evidence through the existing evidence endpoints, `handoffs` through the WC-135 handoff service. Commands require `Idempotency-Key` and `X-Correlation-ID`, carry expected versions, return an operation reference, and never decide success from a model or transport result. Read the `X-Experience-Capabilities` header and pass it to the block builder (C6-03). Feature flag `Workbench:Enabled` (default false) returns 404 `WORKBENCH_DISABLED` when off.
- **Unit tests to write:** each route delegates and propagates idempotency; flag off returns 404; membership required (403 for a token without membership); cross-relationship access refused; replay returns the stored receipt; changed replay conflicts; Stop works with credit at zero (PLATFORM FLOOR).
- **Requirement:** WC136-R038.

#### C6-03 Experience block builder, capability negotiation and WhatsApp rendering

- **Files:** create `src/business-platform/Services/Workbench/ExperienceBlockBuilder.cs`, `ChannelCapabilities.cs`; modify `Services/Visitor/VisitorWhatsAppRenderer.cs` (extend, keep v1 behavior), `Services/Visitor/VisitorReply.cs` (v2 acceptance already added in C2-03), the authenticated WhatsApp reply path in `Services/WhatsAppJourneyService.cs` only where it formats replies; tests `tests/business-platform.Tests/Workbench/ExperienceBlockBuilderTests.cs`, `tests/business-platform.Tests/VisitorConversation/WhatsAppRendererV2Tests.cs`.
- **Steps:**
  1. `ChannelCapabilities` parses `X-Experience-Capabilities` (`channel=WEB|WHATSAPP|MOBILE|API|SIMULATION;modality=text,voice;blocks=TEXT:1,CHOICES:1,...`) and reads channel limits (buttons, label length, rows, body length) from configuration `ChannelLimits`, defaults 3 buttons, 20-character labels, 10 rows, 1,024-character body (Meta reply-button limits confirmed from Meta's own documentation; list, Flow and window rules come from secondary sources and stay configuration until verified, WC-135 F-S11).
  2. `ExperienceBlockBuilder` turns a projection item into blocks and attaches a `fallback` built only from v1 types and a `spoken` form; unknown or unsupported block types, or versions above the client's maximum, are replaced by their `fallback`. It enforces the schema limits of C2-03 (at most 6 blocks, 3 choices, 10 rows, one link).
  3. WhatsApp rendering: `STATUS`, `METRIC`, `PLAN`, `EVIDENCE` render as one concise text line plus a `LINK` to the web page; `DECISION` renders as up to three reply buttons (decision approve, decline, ask me later) and a handoff link when more is needed; `FORM` renders as sequential questions through the conversation (no Flow in this contract); `DOMAIN` renders its fallback. Inbound `button_reply` and `list_reply` already map to `CHOICE` content (WC-135) and must continue to.
  4. P0 behaviors are never degraded: Stop, consent, START, approval of a consequential action and honest limitation render on every channel with the same meaning; a consequential approval that WhatsApp cannot safely perform returns the single-use handoff link instead of a button (architecture 6.6).
  5. Voice: every block carries `spoken`; the builder never produces text longer than the configured body limit; inbound voice continues through the existing transcription path (no new provider call).
- **Unit tests to write:** negotiation matrix; fallback on unknown type and on higher version; limits; every block type to WhatsApp output; P0 parity (STOP, consent, approval) across WEB, WHATSAPP and API renderings; a parity test over fixed fixtures asserting the same semantic blocks for the same input on every channel that supports the class; `spoken` present and bounded.
- **Requirement:** WC136-R039.

#### C6-04 Web API routes for the workbench

- **Files:** create `web/app/api/relationships/[relationshipId]/workbench/[...path]/route.ts`, `web/lib/api/workbench.ts`, `web/lib/api/workbench.test.ts`; route tests colocated.
- **Steps:** follow the existing routes under `web/app/api/relationships/[relationshipId]/` (access token from the request, generated client, `withServerFailureBoundary`, same-origin check on state-changing methods, idempotency key and correlation id generated per call). `workbench.ts` exposes typed loaders for server components (`getWorkbench`, `getGoals`, `getDecisions`, `getMonitor`, `getWallet`) that return `unavailable` states, never throw to the page.
- **Unit tests to write:** loaders map 404 `WORKBENCH_DISABLED` to a disabled state; route forwards idempotency and correlation headers; origin check; failures produce portal-safe messages.
- **Requirement:** WC136-R040.

#### C6-05 Web workbench screens

- **Files:** create `web/components/workbench/` with `WorkbenchShell.tsx`, `StartPanel.tsx`, `GoalPlanPanel.tsx`, `CapabilitiesPanel.tsx`, `DecisionQueue.tsx`, `MonitorPanel.tsx`, `WalletPanel.tsx`, `EvidencePanel.tsx`, `ControlsBar.tsx`, `BlockRenderer.tsx`, `blocks/*.tsx` (one renderer per block type and a `FallbackBlock.tsx`), each with a colocated `*.test.tsx`; modify `web/app/(application)/relationships/[relationshipId]/page.tsx` to render `WorkbenchShell` when the flag returns the projection and the existing three components otherwise.
- **Steps:**
  1. `WorkbenchShell` implements the three-region composition of `customer-engagement-workspace-solution-contract.md` section 6.1 (context, conversation, progress) using the existing `PersistentConversationDock` for the conversation, and a stable tool rail with the kernel primitives Start, Goal and Plan, Capabilities, Operate, Decide, Monitor, Evidence, Control. Stop is reachable in every composition (reuse `RouteAwareEmergencyStop`). Compact widths keep the conversation primary and turn the rail into accessible sheets.
  2. `StartPanel` offers "Ask the professional", "Guided form", and "Use a starter" (from `experience.goalTypes[].starters`), all issuing the same goal command. `GoalPlanPanel` shows the goal, measures, plan version, milestones and calendar with editing as an accelerator on the same commands. `DecisionQueue` shows each decision's effect, authority, cost, confirm and cancel. `MonitorPanel` shows tiles and the five-part narrative. `WalletPanel` shows components remaining and period end in business language (hidden for the `beneficiary` audience; the page never reads money fields for that audience). `EvidencePanel` reuses `EvidenceWindow`.
  3. `BlockRenderer` maps block `type` and `version` to a component and renders `fallback` for anything unknown; it never injects HTML; text is escaped; links are validated against the handoff allow-list.
  4. Accessibility and localization: labelled landmarks, keyboard operation, focus management, live regions for operation status, copy from the declaration's vocabulary and the existing `portal-i18n` mechanism (no hard-coded profession text in kernel components, fitness A9).
- **Unit tests to write:** per component render and interaction tests; `BlockRenderer` fallback on unknown type; beneficiary projection hides the wallet; Stop present in every composition; no raw enum or provider string visible; the page falls back to the legacy components when the projection is disabled.
- **Requirement:** WC136-R040.

#### C6-06 DMA experience wiring and conformance scenarios

- **Files:** modify `src/digital-marketing-agent/integration/business-platform/` (admission and manifest publication, find the module that publishes the employment manifest), `src/business-platform/Services/EmploymentCompatibilityService.cs` (scan reports the experience section: missing, unsupported major, unresolved component ids, `AVAILABLE` components lacking a recipe-capable thread), tests `tests/business-platform.Tests/EmploymentCompatibilityServiceTests.cs` additions, `tests/digital-marketing-agent` additions and conformance scenario fixtures `tests/fixtures/wc136/dma-experience-scenarios.yaml`.
- **Steps:** publish the DMA manifest v1.1.0 so BP admits and reads its `experience` section; extend the compatibility scan (read-only report; unknown parsing, missing references or mixed versions fail closed) with the experience checks; add the conformance scenario fixtures named in the declaration (one per walk-through that concerns DMA).
- **Unit tests to write:** scan passes for DMA v1.1.0; scan reports a gap for a manifest without `experience`; unresolved component id fails; admission still accepts v1.0.0 manifests (compatibility).
- **Requirement:** WC136-R041.

#### C6-07 Compatibility shim and flag

- **Files:** modify `src/business-platform/Controllers/RelationshipWorkspaceController.cs`, `ConversationalEmploymentController.cs`, `CustomerEngagementWorkspaceController.cs` only to add a response header `Deprecation: true` and `Link: <.../workbench>; rel="successor-version"` when `Workbench:Enabled` is true; tests alongside the controller tests.
- **Steps:** no behavior change to the three legacy projections; add the headers; add a unit test per controller asserting existing bodies are byte-identical with the flag on and off (golden-file test over a fixed relationship fixture).
- **Unit tests to write:** the three golden-file tests; headers present only with the flag on.
- **Requirement:** WC136-R043.

### C7 - Playground scenario packs and qualification record (wave W5-lite)

Goal (architecture 7 and 16): the funding and pricing walk-throughs become executable simulated-customer scenarios so they run again after every change.

#### C7-01 Funding scenario pack

- **Files:** create `scripts/visitor_simulation/scenarios/funding.yaml`, `scripts/visitor_simulation/scenario_runner.py`; modify `cli.py`; tests `tests/visitor_simulation/test_funding_scenarios.py`, fixtures `tests/fixtures/wc136/funding-walkthroughs.yaml`.
- **Steps:** express walk-throughs 1 to 12 of architecture 6.10 and the second-round scenarios S1 to S14 that concern funding as scripted scenarios against the fake server and the real API: each step names the actor, channel, relationship state, purpose, expected account class (read from a test-only response header `X-Spend-Account-Class` emitted only when the simulator role is authenticated and the simulation flag is on, never to customers), expected wallet movement and expected customer-visible outcome. Add the fake-server behavior needed so the loopback reproduces the same classes.
- **Unit tests to write:** scenario file validates; fake-server run passes all scenarios; a deliberately wrong class makes the run fail; the header is absent for non-simulator callers (BP test in C7-02).
- **Requirement:** WC136-R044.

#### C7-02 Pricing scenario pack and simulator-only header

- **Files:** create `scripts/visitor_simulation/scenarios/pricing.yaml`; modify BP to emit the simulator-only header; tests `tests/business-platform.Tests/Spend/SimulatorHeaderTests.cs`, `tests/visitor_simulation/test_pricing_scenarios.py`.
- **Steps:** scenarios for the administrator and Founder journeys (A1 to A13): draft, below-floor refusal, simulate, authorize, effective date, price change with an existing customer pinned, ceiling raise and lower, export and import, safety-direction actions, live-margin alert. The BP emits `X-Spend-Account-Class` only when the authenticated principal has role `visitor-simulator` and `SimulatorHeaders:Enabled` is true (default false).
- **Unit tests to write:** header only for the simulator role and flag; scenario run against a fake pricing server passes; wrong expectation fails.
- **Requirement:** WC136-R044.

## Appendix A - Data contracts

All tables are in database `waooaw`, schema `business` unless stated, owned by `wbe_owner` (WBE tables) or `bp_owner` (BP tables), with privileges revoked from `PUBLIC` and `business_app` and granted only as listed in each story. Every key and every query carries `tenant_id` (marketplace tenant for platform scopes). All files are idempotent per the SQL standard. Money is `BIGINT` paise.

### A.1 Wallet (C4-01)

| Table | Columns and constraints |
|---|---|
| `wallet_accounts` | `account_id UUID PK`, `tenant_id UUID NOT NULL`, `owner_kind TEXT CHECK IN ('CUSTOMER','PLATFORM')`, `owner_ref UUID` (customer organisation id; null for `PLATFORM`), `account_class TEXT CHECK IN ('ACQUISITION','SETUP_GRANT','TRIAL','SUBSCRIPTION','PLATFORM_FLOOR','SIMULATION')`, `scope_kind TEXT CHECK IN ('RELATIONSHIP','MARKETPLACE','ENVIRONMENT')`, `relationship_id UUID`, `skill_id TEXT`, `campaign_ref TEXT`, `lead_ref TEXT` (pseudonymous), `environment TEXT`, `agent_type TEXT`, `agent_version TEXT`, `status TEXT CHECK IN ('ACTIVE','CLOSED')`, `created_at TIMESTAMPTZ NOT NULL`. Coherence checks: `SUBSCRIPTION` implies owner `CUSTOMER` and scope `RELATIONSHIP`; `TRIAL`, `SETUP_GRANT` imply owner `PLATFORM`, scope `RELATIONSHIP`, `relationship_id`, `agent_type` and `agent_version` not null; `ACQUISITION` implies owner `PLATFORM`, scope `MARKETPLACE`; `PLATFORM_FLOOR`, `SIMULATION` imply owner `PLATFORM`, scope `ENVIRONMENT`, `environment` not null; `owner_ref` is null exactly when owner is `PLATFORM`. Unique index on `(tenant_id, account_class, COALESCE(relationship_id, nil UUID), COALESCE(skill_id, ''), COALESCE(campaign_ref, ''), COALESCE(lead_ref, ''), COALESCE(environment, ''))`. |
| `wallet_lots` | `lot_id UUID PK`, `tenant_id`, `account_id` (FK on `(tenant_id, account_id)`), `lot_kind TEXT CHECK IN ('PERIOD_CREDIT','TOPUP_CREDIT','GRANT')`, `credited_paise BIGINT CHECK (> 0)`, `valid_from`, `valid_until CHECK (> valid_from)`, `source_kind TEXT CHECK IN ('PACKAGE_PERIOD','TOPUP','TRIAL_GRANT','SETUP_GRANT','ACQUISITION_BUDGET','SIMULATION_BUDGET')`, `source_ref TEXT NOT NULL`, `pinned_versions JSONB NOT NULL` (ids of the rate, package, grant and policy versions in force), `evidence_id UUID NOT NULL`, `created_at`. Immutable (trigger). There is no refundable lot kind and no rollover (FD9). |
| `wallet_entries` | `entry_id UUID PK`, `tenant_id`, `account_id`, `lot_id UUID`, `entry_kind TEXT CHECK IN ('CREDIT','RESERVE','SETTLE','RELEASE','EXPIRE','ADJUST')`, `amount_paise BIGINT CHECK (> 0)` (direction follows the kind), `reservation_id UUID`, `idempotency_key UUID NOT NULL`, `request_digest TEXT CHECK (~ '^[0-9a-f]{64}$')`, `component_id TEXT`, `invocation_id UUID`, `evidence_id UUID`, `occurred_at TIMESTAMPTZ NOT NULL`. `UNIQUE (tenant_id, idempotency_key, entry_kind)`. Immutable (trigger). |
| `wallet_reservations` | `reservation_id UUID PK` (equals the caller's idempotency key), `tenant_id`, `account_id`, `lot_id`, `component_id TEXT`, `reserved_paise BIGINT CHECK (> 0)`, `actual_paise BIGINT`, `state TEXT CHECK IN ('RESERVED','SETTLED','RELEASED','UNKNOWN')`, `pinned_account_class TEXT NOT NULL`, `pinned_versions JSONB NOT NULL`, `expires_at`, `created_at`, `resolved_at`. State and `actual_paise` coherence follows `environment_spend_attempts` (`SETTLED` requires actual; `RELEASED` requires zero; `RESERVED` and `UNKNOWN` require none). Only `state`, `actual_paise` and `resolved_at` may change. |
| function `wallet_available(tenant, account, at)` | credits of unexpired lots minus settled minus reserved minus expired, `BIGINT`, `STABLE`. |

### A.2 Pricing versions (C4-05, C5-01)

`institutional.pricing_versions`: `version_id UUID PK`, `kind TEXT CHECK IN ('RATE','PACKAGE','POLICY','GRANT','BUDGET','COUPON')`, `subject_key TEXT NOT NULL`, `version_no INTEGER CHECK (> 0)`, `state TEXT CHECK IN ('DRAFT','SIMULATED','SUBMITTED','AUTHORIZED','EFFECTIVE','SUPERSEDED','DISCARDED')`, `body JSONB NOT NULL`, `body_digest TEXT NOT NULL`, `seed BOOLEAN NOT NULL DEFAULT false`, `effective_from TIMESTAMPTZ`, `supersedes UUID`, `created_by TEXT NOT NULL`, `created_at`, `authorized_by TEXT`, `authorized_at`, `evidence_id UUID`, `needs_second_confirmation BOOLEAN NOT NULL DEFAULT false`, `second_confirmed_by TEXT`. `UNIQUE (kind, subject_key, version_no)`. The three authorization columns are all null or all set; states `AUTHORIZED`, `EFFECTIVE`, `SUPERSEDED` require them. `institutional.pricing_version_events`: `event_id UUID PK`, `version_id`, `from_state`, `to_state`, `direction TEXT CHECK IN ('NORMAL','SAFETY')`, `actor TEXT NOT NULL`, `occurred_at`, `reason TEXT`. Both tables are append-only except the permitted state and authorization columns, changed only by an owner function.

Legal transitions: `DRAFT -> SIMULATED -> SUBMITTED -> AUTHORIZED -> EFFECTIVE -> SUPERSEDED`; `SUBMITTED -> DRAFT` (returned); `DRAFT|SIMULATED|SUBMITTED -> DISCARDED`; any edit returns the version to `DRAFT`. Subject keys: RATE `thread:<thread_id>`; PACKAGE `package:<agentType>|<agentVersion>|<packageCode>`; POLICY `policy:platform`; GRANT `grant:<TRIAL|SETUP>|<agentType>|<agentVersion>`; BUDGET `budget:<ENVIRONMENT_CEILING|ACQUISITION_TENANT|ACQUISITION_CAMPAIGN|ACQUISITION_LEAD|SIMULATION>|<ref>`; COUPON `coupon:<code>`.

Body essentials: RATE `{threadId, provider, unit, rawCostPaise, fxBufferPct, opsOverheadPct, riskPremiumPct}`; PACKAGE as C4-06; POLICY as C5-01 step 2 plus `minimumMarginPct`; GRANT `{kind, agentType, agentVersion, units{threadId: n} or paise, durationDays or windowDays}`; BUDGET `{scope, ref, maximumPaise, perVisitorMessages?, perDayNewSessions?}`; COUPON `{code, agentType, agentVersion, percent or amountPaise, capPaise, expiresAt, reason, maxRedemptions}`.

### A.3 Component units (C4-05, C4-08)

`business.component_units`: `tenant_id`, `relationship_id`, `agent_instance_id`, `package_version_id`, `component_id`, `kind`, `period_start`, `period_end`, `quantity`, `released_cadence TEXT`, `PRIMARY KEY (tenant_id, relationship_id, component_id, period_start)`. `business.component_unit_entries`: `entry_id UUID PK`, `tenant_id`, `relationship_id`, `component_id`, `period_start`, `entry_kind TEXT CHECK IN ('CONSUME','SELECT','SWAP','DESELECT','CLOSE')`, `units INTEGER`, `item_ref TEXT`, `completion_evidence_id UUID`, `idempotency_key UUID NOT NULL`, `occurred_at`. `UNIQUE (tenant_id, relationship_id, idempotency_key)` and a partial unique index on `(tenant_id, relationship_id, component_id, completion_evidence_id) WHERE completion_evidence_id IS NOT NULL` so a confirmed outcome counts once.

## Appendix B - API and schema essentials

### B.1 Agent Experience Contract (`experience` section)

`contractVersion`; `vocabularyRef` (`ImmutableContractReference`: `contractRef`, `contractVersion`, `contractDigest`); `goalTypes[]` `{goalTypeId, parameters[], measures[{measureId, unit, evidenceSource, freshnessSeconds}], constraints[], starters[]}`; `plan` `{milestoneTypes[], calendarWindows[]}`; `operate` `{workItemTypes[], cadence[{skillId, trigger, window}], approvalModes[{mode, escalation}]}`; `monitor` `{tiles[{tileId, measureId, blockType, audiences[]}], narratives[{narrativeId, cadence, channels[], structure[]}], alerts[{signal, threshold, severity, channels[]}]}`; `domainBlocks[{blockId, version, fallbackBlocks[]}]`; `components[{componentId, label, unit, kind, skillId?, countedOn, selectableDimension?{kind, maximum}, availability, activationAuthority?}]`; `audiences[]`; `modalities[]`; `channelSupport{web[], whatsapp[], mobile[]}`; `conformanceScenarios[]`.

### B.2 Experience blocks (`schemaVersion` 2.0)

Common fields: `id`, `type`, `version` (integer), `sensitivity` (`PUBLIC|CUSTOMER|SENSITIVE`), `data`, `fallback[]` (v1 types only), `spoken` (string, optional), `label` (accessible name, optional).

| Type | `data` |
|---|---|
| `TEXT` | `{text}` (v1) |
| `CHOICES` | `{choices[{choiceId, label}]}`, at most 3, unique labels (v1) |
| `LIST` | `{rows[{rowId, title, description?}]}`, at most 10 (v1) |
| `LINK` | `{label, destinationRef}`, destination is an opaque handoff reference (v1) |
| `STATUS` | `{itemRef, state, owner, freshness}` using the item states of ADR-051 section 4.2 |
| `METRIC` | `{measureId, value, unit, target?, trend?, freshness}` |
| `PLAN` | `{planVersion, milestones[{milestoneId, title, dueMeaning}], calendar[{date, title}]}` |
| `DECISION` | `{decisionId, effect, authority, cost?, confirmLabel, cancelLabel, expiresAt?}` (cost in business language, never provider units) |
| `FORM` | `{formId, fields[{fieldId, label, type, required, options?}]}` |
| `EVIDENCE` | `{evidenceRef, summary, producedAt}` |
| `DOMAIN` | `{domainBlockId, payload}` plus required non-empty `fallback` |

### B.3 Workbench operations (base `/api/v1/employment/relationships/{relationshipId}/workbench`)

`GET ""` projection; `GET /goals`, `POST /goals`, `GET /goals/{goalId}`, `POST /goals/{goalId}/revisions`, `GET /goals/{goalId}/versions`; `GET /plans/current`, `POST /plans`, `POST /plans/{planVersion}/accept`; `GET /capabilities`, `POST /capabilities/{skillId}/commands`; `GET /work-items`; `GET /decisions`, `POST /decisions/{decisionId}/resolve`; `GET /monitor`, `GET /monitor/narratives`; `GET /wallet`, `POST /topups`; `GET /evidence`, `POST /evidence/exports`; `POST /controls/stop`, `POST /controls/pause`; `POST /handoffs`; and `POST /api/v1/employment/relationships/{relationshipId}/subscription/changes` (kinds `UPGRADE`, `DOWNGRADE`, `PAUSE`, `RESUME`, `TERMINATE`), `GET /api/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages`.

`WorkbenchProjectionV1`: `schemaVersion`, `relationshipRef`, `audience`, `phase`, `readiness{induction, plan, operations, performance}`, `currentGoalRef?`, `currentPlanVersion?`, `decisions[]`, `tiles[]`, `components[{componentId, label, remaining, quantity, periodEnd}]` (omitted for `beneficiary`), `alerts[]`, `evidenceState`, `sourceFreshness`, `limitations[]`, `recommendedNextAction?`, `availableCommands[]`, `blocks[]` (negotiated).

### B.4 Pricing admin operations (base `/api/v1/admin/pricing`)

`GET /drafts`, `POST /drafts` (body `kind`, `subjectKey`, `body`), `GET /drafts/{draftId}`, `PUT /drafts/{draftId}`, `POST /drafts/{draftId}/simulate`, `POST /drafts/{draftId}/submit`, `POST /drafts/{draftId}/authorize` (Founder, step-up), `POST /drafts/{draftId}/discard`; `GET /versions?kind=&subjectKey=`; `POST /packages/{packageId}/activate-for-sale` (Founder, step-up, availability gate); safety operations `POST /safety/lower-ceiling`, `POST /safety/close-package`, `POST /safety/disable-grant`; `GET /live-margin`; `GET /dashboard/funding`, `GET /dashboard/margin`; `GET /versions/export`, `POST /versions/import`. The WBE internal mirror lives under `/internal/v1/pricing/...` with one registry grant per route.

### B.5 Fixed error codes

`WORKBENCH_DISABLED` (404), `WORKBENCH_REQUEST_INVALID` (400), `WORKBENCH_VERSION_CONFLICT` (409), `WORKBENCH_IDEMPOTENCY_CONFLICT` (409), `WORKBENCH_UNAVAILABLE` (503), `PRICING_FORBIDDEN` (403), `PRICING_STEP_UP_REQUIRED` (403), `PRICING_DRAFT_INVALID` (422 with violations), `PRICING_BELOW_FLOOR` (422 with `minimumCompliantPricePaise`), `PRICING_NEEDS_SECOND_CONFIRMATION` (409), `PRICING_ILLEGAL_TRANSITION` (409), `PRICING_CEILING_ABOVE_MAXIMUM` (422), `PRICING_CEILING_BELOW_OPEN_RESERVATIONS` (409 with `blockingPaise`), `PACKAGE_COMPONENT_NOT_AVAILABLE` (422), `RECIPE_THREAD_NOT_AUTHORIZED` (422), `SPEND_PURPOSE_UNMAPPED` (403), `SPEND_AUTHORITY_UNAVAILABLE` (403), `SPEND_COMMERCIAL_UNAVAILABLE` (503), `ACQUISITION_BUDGET_EXHAUSTED` (429), `SETUP_GRANT_EXHAUSTED` (200 typed result), `WALLET_INSUFFICIENT`, `WALLET_IDEMPOTENCY_CONFLICT`, `COMPONENT_NOT_YET_RELEASED`, `PROACTIVE_ALLOWANCE_EXHAUSTED`, `TRIAL_ALREADY_USED`, `TRIAL_ALREADY_USED_BY_IDENTITY`. All HTTP errors are RFC 7807 with `title`, `status`, `code` and `correlationId`; no body reveals more than the state.

## Failure And Degradation Matrix

| Failure | Behavior | Test owner |
|---|---|---|
| WBE unavailable | No metered dispatch; free path with disclosure; PLATFORM FLOOR continues | C3-05 |
| BP breaker or lease unavailable or exhausted | No money-spending dispatch; free path; PLATFORM FLOOR continues | C3-06 |
| CE unavailable | Consequential actions halt (ADR-031); pricing authorization fails closed | C5-01 |
| Wallet scope empty or component quantity reached | Free path with honest limitation; top-up offered where allowed | C4-02, C4-08 |
| Outcome unknown after dispatch | Reservation retained on the pinned account; work shown unconfirmed | C3-04, C4-02 |
| Pricing configuration unavailable | Last pinned version used; no new package authorized | C5-01 |
| Gateway failure counting a component unit | Work item not blocked; retry through outbox | C4-08 |
| Acknowledgement queue failure on STOP | Stop already committed; failure reconciled, never rolls back the stop | C1-03 |
| Capability header absent or unknown block version | Fallback blocks render | C6-03 |

## Observability Contract

Structured log events and metrics named in C4-11, plus: `pricing_version_transition` (kind, subject, from, to, direction, actor role only), `workbench_projection_built` (relationship hash, audience, duration, limitations count), `protocol_stop_acknowledged` (channel). No personal data, no message text, no token. SLOs reuse `architecture/reference/slo.md`: workbench reads and commands stay inside the Business Platform read and write operation targets; admin screens have no separate SLO. Alerts: `waooaw_live_margin_floor_breach > 0`, `waooaw_wallet_parity_difference != 0` in `SHADOW`, `spend_denied{reason="SPEND_COMMERCIAL_UNAVAILABLE"}` rate.

## Architecture Fitness Contract (mapping to the architecture package section 10)

A4, A5, A6: C1-01 to C1-04, C6-03 parity tests. A7: C6-03 fallback tests. A8, A15: C3-04, C4-04 tenant tests. A9: C6-05 static guard test. A13, A14: C3-04, C4-02. A16, A19: C3-01 source scan and the C5 static guard test that scans `src` for monetary literals in pricing paths. A17: C3-03. A18: C4-02. A20: C5-01. A21: C4-02 pinned versions replay test. A22: C4-01 schema guard. A23, A24: C4-06. A25, A26: C4-08, C4-10. A27: C3-05. A28: C6-01. A29, A30: C3-06. A31: C5-02. A32: C4-04. A33: C4-11. A34, A35: C4-12, C5-07. A1 to A3, A10 to A12 and the W3 to W6 checks belong to later contracts or to the qualification phase (A12 flag-off rollback is tested in C6-02 and C6-07).

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-136-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest and a revalidated ledger.

| ID | Obligation | Stories |
|---|---|---|
| WC136-R001 | One protocol policy table (STOP and START behavior) is read by the visitor endpoint and the WhatsApp path and fails closed when invalid | C1-01 |
| WC136-R002 | A WhatsApp guest STOP is acknowledged exactly once after the stop commits, silence follows, and the outbox keeps refusing every other purpose to a stopped recipient | C1-02 |
| WC136-R003 | Relationship-bound STOP and EMERGENCY STOP are acknowledged once without changing the order of evidence, fence or halt | C1-03 |
| WC136-R004 | The simulation judge derives STOP and START expectations from the protocol policy and the consent-after-START defect is fixed | C1-04 |
| WC136-R005 | `pass^k` reliability is reported and gated in the simulated-customer harness | C1-05 |
| WC136-R006 | The Agent Experience Contract schema and model exist and the DMA declares its experience from existing contracts with honest component availability | C2-01, C2-02 |
| WC136-R007 | The experience block schema v2 defines types, fallback, spoken form and limits | C2-03 |
| WC136-R008 | The Workbench OpenAPI is complete, capability-traced, idempotent and has negative fixtures | C2-04 |
| WC136-R009 | The Pricing Admin and WBE internal OpenAPI slices exist with one workload grant per internal route | C2-05 |
| WC136-R010 | Client generation is deterministic and pinned | C2-06 |
| WC136-R011 | The contract tests are wired into the validation catalog | C2-07 |
| WC136-R012 | The environment spend ceiling is configuration, Demo stays INR 500, no monetary constant remains | C3-01 |
| WC136-R013 | Trial is relationship-level authority with no customer-level Redis flag | C3-02 |
| WC136-R014 | Trial is carried per exact agent version end to end and bound to a verified identity under a mode flag; hire never blocks the trial | C3-03 |
| WC136-R015 | Every metered call resolves to exactly one account class on the server and is pinned at reserve | C3-04 |
| WC136-R016 | ACQUISITION accounts enforce hierarchical caps with pseudonymous leads | C4-04 |
| WC136-R017 | A SETUP GRANT exists once per relationship and funds onboarding turns only | C4-04 |
| WC136-R018 | The SIMULATION account is isolated from ACQUISITION and customer scopes | C4-04 |
| WC136-R019 | Metered spending fails closed per the failure matrix and the Base Specification B-3 default is amended | C3-05 |
| WC136-R020 | The per-call spend path uses budget leases and keeps the ceiling strict | C3-06 |
| WC136-R021 | One Wallet entity with owner, scope and non-refundable, non-rolling lots is implemented | C4-01, C4-02 |
| WC136-R022 | The WC-134 allocation tables are a projection of the wallet with proven parity in `SHADOW` mode | C4-03 |
| WC136-R023 | Packages are keyed by agent version with components, cost recipes, floor, GST-inclusive price, allocation, availability gate and customer reads | C4-05, C4-06, C4-13 |
| WC136-R024 | Voice and template-message Thread Catalog entries exist as pending Founder authorization and cannot be priced against | C4-07 |
| WC136-R025 | Component kinds meter on owner-confirmed outcomes, selected items need verified connections | C4-08 |
| WC136-R026 | Component units are paced so consumption cannot be front-loaded | C4-08 |
| WC136-R027 | The commercial projection and commands are durable in PostgreSQL | C4-09 |
| WC136-R028 | Pro-rata and lifecycle commands implement hire, renewal, grace, upgrade, downgrade, pause and terminate with no wallet refund | C4-10 |
| WC136-R029 | Spend and cost telemetry carries no personal data | C4-11 |
| WC136-R030 | Proactive messages are classified and counted against the 30 included per period without enabling any send | C4-12 |
| WC136-R031 | The pricing engine state machine, authorization, step-up, safety-direction operations, change-size guard and CE evidence work | C5-01 |
| WC136-R032 | The simulator and the live-margin watch work | C5-02 |
| WC136-R033 | The admin API, delegated context, workload grants, roles and ceiling administration work | C5-03, C5-04 |
| WC136-R034 | The Pricing And Spend Console screens and routes work and are accessible | C5-05 |
| WC136-R035 | The Demo baseline is seeded and versions can be exported and imported as drafts | C5-06 |
| WC136-R036 | Coupons are the only goodwill mechanism | C5-07 |
| WC136-R037 | The funding and margin dashboard is read-only and free of personal data | C5-08 |
| WC136-R038 | The Workbench projection service and controller compose existing owners behind a flag | C6-01, C6-02 |
| WC136-R039 | Blocks, capability negotiation, fallback and WhatsApp rendering preserve P0 parity | C6-03 |
| WC136-R040 | The Web routes and workbench screens render the projection with fallback to the legacy view | C6-04, C6-05 |
| WC136-R041 | The DMA experience declaration is admitted and the compatibility scan checks it | C6-06 |
| WC136-R042 | Audience projections exclude money and purchase controls for a beneficiary | C6-01 |
| WC136-R043 | The three legacy projections are unchanged and carry deprecation headers when the flag is on | C6-07 |
| WC136-R044 | Funding and pricing scenario packs run in the simulated-customer harness | C7-01, C7-02 |
| WC136-R045 | Exact-head Docker qualification passes after all stories, with author review bound to the exact head | Final Qualification Phase |
| WC136-R046 | Every new or changed source file carries the C-059 header and directly related documentation is updated | All stories, Final Qualification Phase |

## Final Qualification Phase (runs once, after the Implementation Complete checkpoint)

The Implementation Complete checkpoint is reached when every story has its END declaration and no story is open. Only then does the implementing office run Docker. The phase follows the catalog-owned four-tier sequence of the Platform IT Expert card; this contract adds the ordering and the stories' test wiring.

| Step | Action | Gates or commands |
|---|---|---|
| Q0 | Cheap preflight, no image build: worktree absolute path, exact HEAD, `bash`, Docker CLI, daemon, Compose, Buildx, `jq`, socket, writable output, safe directory; remove stale dangling images; run the preparation tool with `--preflight-only` | `scripts/prepare_pr_body.sh --preflight-only` per Skill 7 |
| Q1 | Generation drift check: if any OpenAPI file changed after C2-06, regenerate once and review the diff | `scripts/generate_wc136_clients.sh` |
| Q2 | Static and contract | `spec-lint`, `contract:rest`, `wc136:experience-contract`, `quality:sql` plus `python scripts/wc124_init_chain_lint.py` (zero findings) and `scripts/wc124_init_chain_local.sh`, `quality:scripts`, `quality:traceability`, `quality:constitutional-naming`, `quality:observability`, `requirement-ledger` |
| Q3 | Builds | `build:business-platform`, `build:billing-engine`, `build:ai-runtime`, `build:agent-runtime-adapter-digital-marketing`, `build:web` |
| Q4 | Unit tests and quality per stack | `test-dotnet:business-platform`, `test-python:billing-engine`, `test-python:ai-runtime`, `test-python:digital-marketing-agent`, `test-web`, `quality:dotnet:business-platform` (includes CSharpier), `quality:python:ai-runtime`, `quality:typescript` |
| Q5 | Integration | `integration:postgres-migrations` (the command in `validation/engineering-validation.yaml` lists PostgreSQL test files explicitly, so every new PostgreSQL test from C4 and C3 must already be named there by the story that wrote it), `integration:multi-tenant`, `integration:dotnet`, `integration:python`, `sh scripts/validation_control/run_wc123_session_contract.sh` |
| Q6 | Security | `sast:csharp`, `sast:python`, `sast:javascript`, `dep-scan:python`, `dep-scan:dotnet`, `dep-scan:typescript`, `secrets`, `license-check` |
| Q7 | Simulated customers | The harness tests inside `quality:scripts` and a full scenario run of `funding.yaml` and `pricing.yaml` against the loopback fake (never against Demo; no deployment is authorized) |
| Q8 | Release qualification | `release-qualification` (it runs an explicit file list; confirm every new test is in a gate command) |
| Q9 | Constitutional gates | `constitutional-commit-gate`, `author-review-gate`, `authorization-tier-check` |

Rules for the phase: run each command through `scripts/validation_control/local_catalog_gate.py` (`--gate <id> --head <full sha> --base origin/main --git-common-dir <path>`, mode `focused` while repairing and `qualification` for the final run); direct `docker run` is diagnostic only. Classify the first failure as `RUNNER`, `TEST`, `PRODUCT` or `INFRASTRUCTURE`; repair only the owning code or test; rerun the narrowest falsifying check, then the exact failed gate once; never lower a threshold, widen an exclusion, suppress a finding or restart passing stages; never retry an unchanged infrastructure failure. A repair after the final candidate is frozen creates a new candidate and reruns the affected dependency closure. Expected first-run findings (compile errors, formatter differences, test failures) are repaired here and recorded in the Implementation Record.

After Q9 passes at one exact head: author review per the mandatory technique, bound to the 40-character head; then, and only then, commit in dependency-complete scopes in this order (each commit passes the pre-commit hook, which is allowed now): C1 and C2; C3; C4 and the SQL files; C5; C6; C7 and the record. Use the commit format of the repository (`commitlint.config.js`, C-059 subjects such as `feat(bp): ...`, `feat(db): ...`, `feat(web): ...`). Set `core.hooksPath` through `scripts/install_git_hooks.sh`, run `git checkout -- test-results` before PR preparation (hooks rewrite tracked files), do not edit `WC-*.md` after the ledger digest is set (a stale digest fails `CONTRACT_STALE`), prepare the PR body with `scripts/prepare_pr_body.sh --body-file <path inside the worktree> --base origin/main --expected-worktree <path> --expected-head <sha>` using `.github/pull_request_template.md`, push, and submit one PR. The Founder reviews and merges; the implementing office never self-approves or self-merges.

## Rollout And Rollback

Nothing in this contract deploys, activates a provider, changes Azure, DNS or Production, or serves customer traffic. Every behavior change ships behind a default-off or default-equivalent setting:

| Setting | Default | Effect |
|---|---|---|
| `Workbench:Enabled` | `false` | Workbench routes 404 and the web page renders the legacy components |
| `EnvironmentSpend:HardMaximumInr` | `500` | Same as today |
| `EnvironmentSpend:Mode` | `GLOBAL_LOCK` | Current serialization; `LEASES` is opt-in |
| `WALLET_AUTHORITY` (WBE) | `LEGACY` | `SHADOW` and `WALLET` are opt-in; `WALLET` is a Founder-gated rollout |
| `TRIAL_IDENTITY_BINDING_MODE` (WBE) | `RECORD` | Records claims, refuses nothing |
| `Protocol:WhatsAppStopAcknowledgementEnabled` | `false` | The visitor endpoint and the simulator follow the protocol policy; the WhatsApp acknowledgement exception is inactive until the privacy and provider-policy check passes (FD17) |
| `SimulatorHeaders:Enabled` | `false` | Test-only response header absent |
| Proactive sending | disabled by the WC-134 policy | Unchanged; classification and counting run only when called |

Rollback: set the flags to their defaults; all SQL is additive and idempotent and no data is deleted. The one non-additive change is replacing the unique key on `institutional.bundle_profiles` (C4-05); keep a reviewed compensating SQL in the Implementation Record that restores the previous key and may run only while no second agent version exists. The WC-134 allocation tables remain intact, so `LEGACY` is always available.

## Definition Of Done

1. Every story has START and END commentary, an author code review recorded in its END line, and its tests written and wired.
2. The Implementation Complete checkpoint was reached before any Docker validation (the Founder instruction), and the Final Qualification Phase passed at one exact head with every gate in Q0 to Q9 recorded with its result.
3. All requirements WC136-R001 to WC136-R046 are `PASS` in the ledger with evidence references, or `BLOCKED` with a named external reason that this contract lists (live-number STOP acknowledgement activation, proactive sends, Founder authorization of catalogue entries, production values, counsel review of "wallet").
4. Author review is complete per the mandatory technique, bound to the exact head, with every finding repaired.
5. The PR is open for Founder review with the template completed, exact commands and results listed, and untested stages stated (no deployment, no live provider, no Demo acceptance, no real-phone acceptance).
6. `constitution/PROJECT_STATE.md` is updated once at closure with the externally meaningful state transition only.

## Stop Conditions

Stop and raise a blocker, do not improvise, when any of these holds: a precondition fails; the architecture package is not ACCEPTED; a story would require a new dependency, a new deployable service, an ADR, or a change to ADR-046 envelope fields (C5-03); the STOP acknowledgement would change the order of evidence, fence or halt (C1-03); a read-only verification step finds the governed generation path does not force the trial tier (C3-02, record it, do not design a fix); the `institutional` or `business` SQL cannot be made idempotent; a Constitutional Engine, evidence or tenant-isolation test fails and the repair would weaken it; any request to run Docker or host tooling before the Implementation Complete checkpoint other than the two named exceptions; any need to commit before the checkpoint; any provider call, Azure change, Terraform change under the workload module, deployment, spend, DNS, customer traffic or Production action; two reproducible infrastructure failures in the final phase; an exact-head mismatch or conflicting user changes; a quality-gate exception.

## Implementation And Evidence Record

To be completed by the implementing office at the checkpoint and at closure. Rows are not pre-filled with results.

| Item | Value |
|---|---|
| Implementing session authorization (Founder message) | |
| Selected worktree, branch, full HEAD at start | |
| Process-control version and digests verified | |
| Ledger validation result (P2) | |
| Client generation run (C2-06): image tag and output files | |
| Story ledger: story id, files, tests written, review findings and repairs (one row per story, 48 rows) | |
| Implementation Complete checkpoint time and diff statistics | |
| Final Qualification: gate, command, exact head, result (Q0 to Q9) | |
| First-run findings repaired in the final phase | |
| Open notes for the Founder (for example C3-02 trial-tier finding) | |
| Compensating SQL for the `bundle_profiles` key | |
| PR number, exact head, prepared body path | |

## Review Records

### Chief Solution Architect (INST-005) author review and implementation-readiness test, 2026-11-20

| # | Check | Result |
|---|---|---|
| 1 | Every component traces to the architecture package and to a capability; no capability, ADR or service was invented | Pass. Two capability-map entries remain Founder decision D3 (precondition P1) |
| 2 | Interfaces specify identity, authorization, idempotency, errors, limits, versioning, failure behavior | Pass for the specifications in Appendix B and C2; field-level schemas are produced in C2 from Appendix B, which is the specification the implementer must follow |
| 3 | State machines and failure matrix | Pass. Pricing version states in Appendix A.2; failure matrix in this contract; resolver table in C3-04 |
| 4 | Security, privacy and tenant isolation | Pass. Roles, step-up, Founder-only authorization, no personal data in telemetry, tenant key on every table, beneficiary projection filtering, no new public WBE surface |
| 5 | Dependency order and ownership | Pass. Components C1 to C7 ordered; each story names owning files and tests |
| 6 | Founder execution instruction | Pass. Stated verbatim, interpreted, and enforced by the Story Procedure, the no-commit rule, the single generation exception and the Final Qualification Phase |
| 7 | Implementation-readiness test: could an implementer proceed without inventing design | Pass with four named read-and-confirm steps, each with a stop rule rather than discretion: C1-03 (what a relationship recipient receives today), C3-02 (trial tier on the governed path), C3-04 step 2 (enumerate registered context keys), C6-01 step 1 (reuse the services behind the existing controllers). Each tells the implementer exactly what to read and what to do on each outcome |
| 8 | Known limits | The contract was written without compiling or running anything. Code anchors and line numbers were read at the baseline commit and may shift by a few lines; story text names methods as well as lines. DMA publication, ad boost and proactive messages are not deliverable today; the contract encodes that as component availability rather than assuming delivery. The Meta list, Flow and window limits come from secondary sources and stay configuration |

Author review is self-verification, not approval. The Founder decides whether an institutional review is wanted.




