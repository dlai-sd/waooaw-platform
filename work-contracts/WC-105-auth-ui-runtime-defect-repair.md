# WC-105 - Authentication, Guide, Session, And Landing Defect Repair

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-010), Skills 1-7, 11, 12, 14 and 16 |
| Authorized by | Founder instructions in the 2026-09-21 working session |
| Status | IMPLEMENTATION AUTHORIZED - LOCAL SOURCE, TESTS, PREVIEW, AND UNMERGED PR |
| Baseline | `818ec26441d39b3f13cb75a7650d9389b8cff462` |
| Delivery unit | One bounded defect-repair PR |

## Authority And Scope

The Founder authorized repair and complete testing of the reported authentication, customer portal,
identity-session, Guide, and landing-page defects. The Founder accepted the revised landing preview
on 2026-09-21 and authorized conversion of that preview into durable requirements and executable
evidence.

Authorized changes are limited to the existing Business Platform and Web Application components,
focused tests, this Work Contract and ledger, local Docker validation, the Codespace preview, and one
unmerged PR. Google consent-screen configuration and Google branding are deferred. No cloud mutation,
deployment, provider configuration, customer traffic, Production action, approval, or merge is
authorized.

## Inputs

- Founder defect list and accepted landing-page screenshots from the 2026-09-21 working session.
- WC-093 public/authentication presentation and WC-103 multi-tenant authentication contracts.
- Existing identity security data contract and customer portal membership boundary.
- Exact `origin/main` baseline and repository Docker runners.

## Canonical Requirement Index

| Requirement | Required observable behavior | Executable evidence |
|---|---|---|
| WC105-R001 | Google and other enabled providers launch directly without a WAOOAW intermediate disclosure; Google retains explicit account selection. | Provider command component tests. |
| WC105-R002 | An authenticated customer with an incomplete profile is routed to registration with a sanitized return destination from both login and application-shell entry. | Auth view and application layout tests. |
| WC105-R003 | Concurrent observations of one broker session produce one account-scoped session and one idempotent establishment event without serialization failures or Marketplace `500` responses. | Real PostgreSQL eight-request concurrency test and identity HTTP regression. |
| WC105-R004 | Guide interaction GET and POST resolve customer membership before service execution so a valid customer does not receive a route-owned `401`. | Portal interaction controller tests. |
| WC105-R005 | The Guide composer contains an accessible icon-only up-arrow Send command; a microphone appears only when voice is backend-enabled and browser-supported. | Guide component tests and TypeScript validation. |
| WC105-R006 | Identity security-event persistence remains idempotent for replayed deterministic event keys and does not create duplicate establishment events. | Real PostgreSQL concurrency/event-count assertion and security-event tests. |
| WC105-R007 | Identity-event persistence failure remains bounded and cannot silently be represented as successful durable evidence. | Existing timeout/failure tests or an explicit blocked result when the reported runtime response cannot be reproduced locally. |
| WC105-R008 | Session revocation permits the owning account, remains idempotent, rejects inaccessible sessions, and does not weaken authorization to hide an unexplained `403`. | Session lifecycle and HTTP authorization tests; observed external `403` remains blocked without its response evidence. |
| WC105-R009 | The accepted landing hero uses equal-height cards, card frames 20% wider than the prior `93.6%` width without widening the stage, rear cards dimmed by a further 20%, and the desktop showcase moved down 20%. | Production browser geometry at desktop and mobile. |
| WC105-R010 | DMA copy reads `Watch chaos turn into clarity - You only step in when it matters.` and `Digital Marketing on fire`; problem cards use staggered focus motion while reduced-motion behavior remains respected. | Component copy/timer tests and production browser inspection. |
| WC105-R011 | The revised hero has no horizontal overflow, content clipping, CTA collision, runtime error, or unsupported mobile/desktop layout. | Production Chromium geometry at 1365x720 and 390x844 plus configured browser regression where available. |
| WC105-R012 | The complete changed surface passes focused tests, type checking, production build, diff review, requirement-ledger validation, and exact-head PR prechecks. | Docker test/build output, author review, and prepared PR evidence. |
| WC105-R018 | Demo dependency readiness prevents Web from accepting a customer journey while Business Platform is cold and unavailable. | Terraform mapping test plus separately authorized retained Demo cold-start journey. |
| WC105-R019 | Tenant RLS context is transaction-local for every EF command, warning-free, tenant-isolated, and cleared before pooled connection reuse. | Real PostgreSQL interceptor, protected HTTP, and cross-tenant negative tests. |
| WC105-R020 | One privacy-safe shared trace spans Web, Business Platform, identity, Guide, Marketplace, and resulting status in Azure. | Runtime propagation test plus retained Azure span query. |
| WC105-R021 | Facebook OAuth 191 is safely diagnosed and the approved deployed callback completes through the real provider. | Sanitized verifier tests plus separately authorized provider acceptance. |
| WC105-R022 | Idempotent Hire and Trial actions create correct tenant-bound relationships that persist under My Agents across sessions. | Browser and real-service lifecycle journeys with second-tenant denials. |
| WC105-R023 | Hired and trial DMA relationships support configuration, verified goals, and truthful governed operation state while failing closed. | Relationship workspace browser and service journeys. |
| WC105-R024 | Three exact platform features appear one at a time below `Control remains yours.` with accessible controls, swipe, keyboard, pause, and reduced motion. | Component and responsive browser assertions. |
| WC105-R025 | Section `02` uses the exact approved small-business trust and owner-control copy across required presentation modes. | Copy, locale, RTL, zoom, and responsive browser assertions. |
| WC105-R026 | The top-left logo renders exactly 50% larger with preserved ratio and no control or layout regression. | Component dimension and responsive browser geometry assertions. |

## Definition Of Done

- Every requirement is recorded in `work-contracts/WC-105-requirements.yaml` with source, owner,
  evidence class, direct test path, completion rule, result, and residual risk.
- Every in-scope behavior has executable evidence; blocked external observations remain explicitly
  blocked and are not represented as fixed.
- Relevant Business Platform and Web tests, TypeScript, production build, browser geometry, and
  repository PR prechecks pass against the final committed head.
- Author review covers correctness, concurrency, authorization, privacy, accessibility, responsive
  layout, rollback, and scope.
- The branch is pushed and one unmerged PR is submitted for Founder review.

## Stop Conditions

Stop on any requirement to weaken membership or revocation authorization, suppress persistence
failure, change provider/cloud configuration, add a dependency, deploy, access customer data, mutate
Demo/UAT/Production, bypass a quality gate, self-approve, or self-merge. An unreproduced event timeout
or revocation `403` must remain blocked rather than receive a speculative repair.

## Rollback

Revert the bounded commits. No schema, migration, provider, secret, cloud, or customer-data rollback
is required.

## Post-Deployment RCA And Follow-Up Requirements

PR #470 was deployed from merge commit `e9c8726f41ba594ee7897ea76b8aab19cdbe2da1` to the intended
Demo revisions and image digests. The deployment was correct, but retained Azure telemetry from
2026-09-22 disproved customer-journey completion and established the following bounded follow-up.

| Requirement | Unresolved point | RCA | Azure evidence | Authorized fix | Closure evidence |
|---|---|---|---|---|---|
| WC105-R013 | Marketplace / My Agents unavailable | One protected render fans out through layout and page identity-session calls. Session locking ends before establishment-event persistence, so a shared identity dependency can fail while the marketplace and relationship APIs succeed. | Marketplace and relationships returned `200`; concurrent identity-session requests returned `200`, `403`, and `409`, with PostgreSQL `40001` and `23505`. | Deduplicate identity resolution within one server render and keep session observation plus establishment-event outcome inside one serialized, idempotent boundary. | Protected-render component tests and a concurrent real-PostgreSQL service test complete without duplicate session observations, database command failures, or incorrect protected content. |
| WC105-R014 | Duplicate identity events | Concurrent callers insert the same deterministic source event. Exception recovery depends on one direct wrapper shape and allows a wrapped unique violation to escape. | Repeated `23505` for `identity_security_events_source_unique` wrapped in `DbUpdateException`. | Persist with atomic PostgreSQL conflict handling and return the existing outcome without exception-driven duplicate control flow. | Parallel same-source writes all complete, exactly one event is stored, and no database error is emitted. |
| WC105-R015 | WAOOAW Guide initial `503` | Guide membership/session middleware can fail before controller execution; first-use context creation also uses a check-then-insert sequence. | Guide GET returned `503` beside the identity-event `23505`; a later request returned `200`. | Remove the identity-event failure path, make Guide context creation atomic under concurrent first use, and preserve downstream problem code and correlation ID. | Simultaneous first Guide loads return `200`, share one context, and expose typed diagnostics for an injected downstream failure. |
| WC105-R016 | Security-event timeout | The Web waits five seconds for event persistence while duplicate writes and database contention prevent a durable response. | Repeated Web `TimeoutError`; backend event requests included `499` and duplicate-key failures. | Use bounded atomic persistence and distinguish accepted duplicate, dependency failure, timeout, and caller cancellation without reporting false durable success. | Concurrent persistence completes within the bounded test deadline with one event; timeout and failure tests preserve truthful typed outcomes. |
| WC105-R017 | Identity / alerts `403` | The Web maps every identity `403` to step-up although the backend distinguishes step-up from action denial and other typed identity outcomes. | Demo identity and alerts requests returned `403`; the client projected a generic or misleading state. | Classify identity responses by the backend problem `code`, reserve step-up for `IDENTITY_STEP_UP_REQUIRED`, and preserve the correlation ID for diagnostics. | Contract tests cover each supported `403` code and the alerts/protected-route presentation receives the correct typed state. |

The follow-up remains limited to Business Platform and Web source, focused tests, this Work Contract
and its requirement ledger, Docker validation, and one unmerged PR. It does not authorize deployment,
provider mutation, customer traffic, approval, or merge.

## PR #471 Post-Deployment Residual Defects

PR #471 merged as `5c8c2ac12a9943b146fe11b8b1686f9e922fd3f8` and was deployed to Demo as
Business Platform revision `ca-demo-business-platform--0000047` and Web revision
`ca-demo-web--0000052`. Azure telemetry from 2026-09-23 confirms that the WC105-R013 through
WC105-R017 concurrency repairs removed the observed `40001`, `23505`, Guide `503`, and customer-route
`5xx` failures. The same telemetry identifies the following residual defects and evidence gaps.

| Defect | RCA | Impact | Azure evidence | Miss | Why earlier contract did not catch it |
|---|---|---|---|---|---|
| WC105-R018 - Cold-start dependency availability | Demo Web and Business Platform can scale to zero independently. Web accepted the journey before Business Platform and its PostgreSQL sidecar became ready. | Identity-provider readiness was unavailable for about two minutes. Four Web security-event attempts timed out and six backend event requests ended with caller-cancelled `499`; durable evidence resumed only after the dependency became ready. | Web became ready at `09:01:56Z`. Business Platform image pull began at `09:02:13Z`, startup probes still failed through `09:04:08Z`, and Web recorded repeated `FetchError` and `TimeoutError` through `09:04:16Z`. Eight later security-event requests returned `201`. | No cold-start journey | Docker qualification exercised already-running services. The contract prohibited deployment and did not require an authenticated scale-to-zero recovery scenario or dependency-readiness evidence. |
| WC105-R019 - Tenant RLS context is not transaction-safe on every query | `TenantDbConnectionInterceptor` prepends `SET LOCAL app.current_tenant_id` to commands without guaranteeing that the command runs inside an explicit transaction. PostgreSQL therefore cannot retain the local setting for affected queries. | The database RLS tenant context is not guaranteed on non-transactional paths, weakening a required defense-in-depth boundary. The observed journey returned the correct tenant data; no cross-tenant disclosure is established by this evidence. | Business Platform emitted 25 `SET LOCAL can only be used in transaction blocks` warnings across two PostgreSQL processes from `09:04:42Z` to `09:04:48Z` during successful protected-route requests. | HTTP/RLS boundary not exercised | Service concurrency tests created explicit transactions and did not execute a real protected HTTP request through the global tenant interceptor. Qualification also lacked a PostgreSQL warning-free assertion and a cross-tenant negative check for this path. |
| WC105-R020 - Distributed trace evidence is absent | Demo sends Container App console and system logs to Log Analytics, but no end-to-end OpenTelemetry request, dependency, or span records are ingested for Web-to-Business-Platform calls. | Operators cannot correlate a Web request to its backend calls, prove request-scoped identity deduplication, or distinguish dependency latency from application failure using a shared trace identifier. | The post-deployment workspace contained `ContainerAppConsoleLogs_CL`, `ContainerAppSystemLogs_CL`, and `Usage` only; no request, dependency, `AppTraces`, or span table contained PR #471 traffic. | Correlation payload mistaken for tracing | WC105-R015 and WC105-R017 required problem-code and correlation-ID preservation in responses, but the contract did not require telemetry export, Azure ingestion, cross-service trace continuity, or a retained trace query. |
| WC105-R021 - Facebook login fails with OAuth error 191 | The callback URL domain or a required subdomain is absent from the Facebook application's App Domains and valid OAuth redirect URI configuration. This is external provider configuration, not a Web button or broker-code failure. | A customer who selects Facebook cannot authenticate or continue to registration. | Facebook returns `OAuthException` code `191`: `Can't load URL: The domain of this URL isn't included in the app's domains.` The reported response includes provider trace ID `Ay0Rs_U51GedAwMZYGVEbY8`; this identifier is diagnostic evidence only and must not become a durable application dependency. | Real Facebook-domain acceptance was deferred | Earlier qualification validated local redirect construction and provider selection but did not execute the deployed callback through the real Facebook application configuration. |
| WC105-R022 - Marketplace hire/trial journey is not end-to-end proven | Existing marketplace, relationship, trial, and My Agents surfaces were validated independently; no deployed story proved that one customer action creates the correct durable relationship and immediately projects it under My Agents. | A customer may see an apparently successful Hire or Start Trial action without finding the agent in My Agents, or may receive the wrong commercial state. | Not yet collected for this assumed-post-fix story. Required evidence is one retained Demo journey for Hire and one for Trial, bound to relationship IDs and privacy-safe traces. | Cross-surface lifecycle omitted | Earlier WC-105 scope repaired access and concurrency failures; it did not make Hire/Trial-to-My-Agents projection a completion criterion. |
| WC105-R023 - Hired/trial DMA operation is not customer-journey proven | Configuration, goal setting, and DMA operation exist as separate governed capabilities, but the deployed customer path has not been proven from the My Agents relationship context for both hired and trial models. | Customers may see DMA in My Agents but be unable to configure it, set a goal, start governed work, or see an honest resulting state. | Not yet collected. Required evidence is a privacy-safe Demo trace and visible state transition for each operation without cross-tenant or cross-relationship access. | Visibility treated as completion | Earlier checks proved agent listing and bounded relationship APIs, not the complete configure-to-goal-to-operation journey from the customer UI. |
| WC105-R024 - Platform feature presentation is missing below the hero | The existing `Control remains yours.` section explains governance but does not present the platform's agent-agnostic customer features in a focused, progressive format. | Small and medium businesses cannot quickly understand how they will communicate with and employ WAOOAW professionals. | Visual evidence not yet collected. | Landing validation focused on hero geometry | WC105-R009 through WC105-R011 bounded the accepted hero and responsive layout but did not specify the content or interaction of the sections below it. |
| WC105-R025 - Trust section uses academic language | The current copy emphasizes constitutional and governance terminology instead of everyday business outcomes and owner control. | Indian small and medium business owners may not understand what the service does, what they can review, or how they remain in control. | Copy and comprehension evidence not yet collected. | Technical truth was not translated for the audience | Earlier requirements checked exact copy and layout but did not include plain-language acceptance for the target customer. |
| WC105-R026 - Header logo is undersized | The current top-left brand mark lacks sufficient visual prominence relative to navigation and first-viewport content. | WAOOAW brand recognition is weak on initial desktop and mobile entry. | Visual evidence not yet collected. | Header brand scale was outside hero checks | Earlier geometry assertions covered hero cards, overflow, clipping, and CTA placement, not logo prominence. |

### CMMI Five-Whys Causal Analysis

The causal chains separate the observed defect, its technical cause, the verification escape, and the
process change needed to prevent recurrence. A local source repair closes only the technical branch;
deployment and provider branches remain open until separately authorized acceptance evidence exists.

| Requirement | Why 1 | Why 2 | Why 3 | Why 4 | Why 5 / systemic root | Preventive control |
|---|---|---|---|---|---|---|
| R018 | Web was ready before BP. | Both workloads could scale to zero. | Web readiness did not represent dependency readiness. | Qualification began with warm services. | The contract lacked a cold-start dependency scenario. | Keep Demo BP warm and require retained first-request cold-start evidence. |
| R019 | PostgreSQL warned that `SET LOCAL` had no transaction. | EF read commands can execute without an explicit transaction. | The interceptor assumed every command inherited one. | Service tests opened transactions themselves. | The global interceptor boundary lacked real PostgreSQL negative and leak checks. | Own a transaction for otherwise non-transactional commands and test warning-free cleanup. |
| R020 | No queryable cross-service spans existed. | OTel packages were referenced but never registered or exported. | Phase2 supplied logs but no trace exporter destination. | Correlation IDs were accepted as diagnostic evidence. | The completion gate did not require one retained shared trace ID. | Require runtime registration, cloud ingestion configuration, privacy assertions, and bounded KQL proof. |
| R021 | Meta rejected the callback with code 191. | The deployed host was absent from provider domain/redirect configuration. | Local checks verified URL construction only. | Real-provider acceptance was explicitly deferred. | Provider-owned configuration had no authorized acceptance gate before availability was advertised. | Classify 191 safely and require separately authorized real-provider callback evidence. |
| R022 | Hire/Trial-to-My-Agents was not proven as one journey. | UI and relationship services were tested independently. | Durable confirmation and projection were separate assertions. | New-session and second-tenant checks were omitted. | Completion was measured by component coverage instead of a customer lifecycle. | Add one idempotent cross-surface journey per commercial model with isolation checks. |
| R023 | DMA visibility did not prove usable governed work. | Configuration, goal, and operation controls were tested separately. | Tests did not begin from the acquired My Agents relationship. | Trial limits and fail-closed states were not combined in one scenario. | The evidence model treated capability presence as operational completion. | Add hired and trial configure-to-operation journeys with cross-relationship denials. |
| R024 | Core platform features were not prominent. | The post-hero section contained governance copy only. | Landing acceptance concentrated on hero geometry. | Feature comprehension was not a requirement. | Target-customer understanding was absent from the UX completion model. | Require exact feature content plus keyboard, swipe, motion, and responsive assertions. |
| R025 | Trust copy sounded academic. | Constitutional terms were exposed without customer translation. | Copy checks asserted fidelity, not comprehension. | The target SMB audience was not an acceptance dimension. | Content review lacked a plain-language owner-control criterion. | Pin approved practical copy and test exact visible content at responsive/zoom modes. |
| R026 | The logo lacked first-viewport prominence. | Its dimensions were constrained to the earlier header baseline. | Hero checks excluded brand scale. | Responsive tests checked overflow without an exact logo ratio. | Brand prominence had no measurable acceptance rule. | Assert a 1.5x source/computed size and browser geometry across responsive/locale modes. |

## Residual Defect Definition Of Done And Success Scenarios

These residual defects are not DONE from source changes or local tests alone. Closure requires a
separately authorized Demo deployment of the exact candidate images and retained Azure evidence for
all scenarios below.

1. **WC105-R018 - cold-start success:** With Web, Business Platform, and the Demo PostgreSQL sidecar
  at their configured zero/idle state, the first authenticated customer journey does not claim
  provider or application readiness before required dependencies are ready. Registration, identity
  session, Marketplace, My Agents, alerts, and Guide complete within their configured bounded
  timeouts. Security-event persistence produces no unexplained `499`, `TimeoutError`, or lost durable
  outcome; accepted duplicates remain distinguishable from new `201` inserts.
2. **WC105-R019 - RLS success:** A real PostgreSQL test enters through the protected HTTP middleware
  and executes both transactional and previously non-transactional EF Core paths. Every command sees
  the expected `app.current_tenant_id`, a second tenant cannot read or mutate the first tenant's rows,
  and PostgreSQL emits zero `SET LOCAL can only be used in transaction blocks` warnings. The test must
  fail when transaction-scoped tenant context is absent.
3. **WC105-R020 - trace success:** One authenticated protected render exports a privacy-safe trace from
  Web through Business Platform, identity-session resolution, Guide/Marketplace dependencies, and the
  resulting status. Azure retains queryable spans with one shared trace identifier, service/revision
  identity, latency, typed failure status, and correlation ID, without tokens, customer identifiers,
  SQL parameters, or other sensitive values.
4. **Regression success:** The exact deployed candidate records zero PostgreSQL `40001` and `23505`,
  zero unexpected identity or Guide `5xx`, correct pre-registration `409`, correct post-revocation
  `403`, successful Marketplace, relationships, alerts, and Guide responses, and no crash or
  probe-driven restart during the retained observation window.
5. **Evidence and review success:** `work-contracts/WC-105-requirements.yaml` records WC105-R018 through
  WC105-R026 with direct test paths, exact image digests and revisions, bounded KQL queries, raw
  retained results, and residual risks. Author review and exact-head PR gates pass, and Founder review
  remains separate from author verification and deployment execution.
6. **WC105-R021 - Facebook login success:** From the deployed Login dialog, selecting Facebook reaches
  the real Facebook authorization or account-selection screen and returns only to the exact approved
  WAOOAW callback. The Facebook App Domains and valid OAuth redirect URI include the deployed host,
  error `191` does not occur, state and PKCE checks pass, and cancellation or denial returns a bounded,
  customer-safe result. Evidence records hostnames, status classes, and provider trace identifiers but
  no authorization code, token, account identifier, or secret. Provider configuration mutation and
  real-account acceptance require separate current Founder authority.
7. **WC105-R022 - Marketplace Hire and Trial success:** Starting from Marketplace, an eligible customer
  can Hire one agent and start a Trial for another. Each action creates exactly one tenant-bound,
  idempotent relationship with the correct `HIRED` or `TRIAL` commercial state. Both agents then appear
  under My Agents without refresh races or duplicates, survive a new authenticated session, and remain
  invisible to a second tenant. The UI must not claim success before durable relationship confirmation.
8. **WC105-R023 - My Agents and DMA operation success:** My Agents lists only the current customer's
  hired and trial relationships and clearly distinguishes their model and lifecycle state. From a DMA
  relationship, the customer can configure permitted settings, create and confirm a goal, start one
  governed operation, and see its evidence-backed status. Trial limits, decision-space restrictions,
  validation failures, Emergency Stop, and unavailable capabilities remain truthful and fail closed.
  A second agent or tenant cannot read or mutate the DMA relationship, configuration, goal, or evidence.
9. **WC105-R024 - platform feature section success:** Keep the existing heading `Control remains yours.`
  and supporting line `Clear scope, evidence-backed states, and persistent Emergency Stop.` Directly
  beneath it, present one prominent horizontal feature card at a time in an accessible left-to-right
  sequence for these three agent-agnostic features:
  - **Work with your WAOOAW professional on WhatsApp:** Use a familiar channel for written and voice
    conversations while governed records remain connected to the professional relationship.
  - **Built for real business growth:** Every WAOOAW professional supports a clear journey from hiring
    and induction through ongoing grooming and earning business outcomes, within declared authority.
  - **Your language, written or spoken:** WAOOAW professionals communicate in the customer's selected
    supported language through text and voice without overstating unsupported languages or channels.
  The sequence supports swipe, keyboard, and explicit previous/next controls; announces position to
  assistive technology; pauses automatic movement on interaction; respects reduced motion; and never
  clips, overlaps, or creates page-level horizontal overflow on desktop or mobile.
10. **WC105-R025 - small-business trust copy success:** Replace the section labelled `02` with concise,
  practical language for Indian small and medium businesses. The approved content intent is:
  - Heading: **Trust grows when you can see the work**
  - Supporting copy: **Know what your WAOOAW professional is doing, what needs your approval, and what
    result was delivered. Clear updates and work records help you stay confident and in control.**
  - Journey label: **How your professional works with you**
  - Governance heading: **Clear rules. Your business stays in control.**
  - Governance copy: **Every WAOOAW professional works within an agreed role and limits. You can review
    important actions, ask for changes, or stop the work at any time.**
  Browser assertions verify this exact visible copy at desktop and mobile widths, 200% text zoom, and
  supported locale/RTL modes without retaining the replaced academic headings in visible content.
11. **WC105-R026 - logo prominence success:** Increase the rendered top-left logo dimensions by exactly
  50% from the current computed baseline while preserving aspect ratio. The header, navigation, Login
  and Register controls remain aligned and usable without clipping, overlap, wrapping regressions, or
  horizontal overflow at desktop, mobile, 200% zoom, and the longest supported localized navigation.