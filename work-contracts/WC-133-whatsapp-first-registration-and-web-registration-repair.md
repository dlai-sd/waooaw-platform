# WC-133 - WhatsApp-First Registration And Web Registration Repair

## 1. Record Control And Authority

| Field | Value |
|---|---|
| Work Contract ID | WC-133 |
| Authoring and assigned implementation office | Platform IT Expert (INST-010) |
| Founder assignment | Current conversation, 2026-11-03 |
| Status | IMPLEMENTATION AUTHORIZED; REPOSITORY REGRESSIONS VALIDATED; PR GATES AND LIVE ACCEPTANCE PENDING |
| Observed deployed baseline | `c9e614715bb98ddcaff72b07c94957d94fa1901e` |
| Related contracts | WC-120; WC-121 Demo WhatsApp provider-enablement component; WC-123 identity; WC-115 employment |
| Delivery | One combined corrective PR for this contract; Founder review and merge |
| Requirements ledger | [WC-133-requirements.yaml](./WC-133-requirements.yaml) |
| Constitutional basis | C-023, C-026, C-039, C-059, C-063; accepted identity/assurance and tenant-isolation controls |

The Founder identified direct inbound WhatsApp as the highest-value entry path, accepted the
web-registration repair proposal, and requested a new precise contract covering these defects.
This request authorizes this document and its evidence ledger, not fresh implementation, cloud
mutation, deployment, messaging or activation. Before implementation begins, obtain explicit
current-session implementation confirmation. Existing narrowly authorized work is not expanded
by this contract.

Do not repeat bootstrap in this continuous conversation. Do not invoke another office or reviewer
agent without Founder direction. Do not amend immutable constitutional documents or create an ADR.
If an accepted owner contract cannot support the required admission path, stop only that
conflicting action and present the exact conflict for Founder disposition; do not invent policy.

## 2. Objective And Non-Negotiable User Journey

### Current-Session Founder Amendment - 2026-11-03

The Founder explicitly authorized implementation, thorough tests and one new PR, without the
Release Qualification run. Skip only Release Qualification for this PR; all other applicable
mandatory checks remain. The Founder selected **provisional phone-verified onboarding**:
no email or Portal prerequisite to begin, but full account completion/linking and consequential
actions retain existing stronger proof. Earlier authoring-only language describes the prior state.
This does not authorize live cloud changes, deployment, traffic, activation, self-approval or merge.

The provisional identity is an Identity-owned onboarding record, not a completed customer
account, OWNER membership or employment relationship. An independently approved Demo activation
reserves its isolated tenant scope and one protected pilot binding before first contact. The
opaque pilot binding may precede the provisional identity; it must not identify an existing
account by phone. Shared BP interaction contexts/messages own pre-employment history and replies;
relationship conversation/outbox invariants remain unchanged for existing users. Any extension
of shared delivery scope must explicitly distinguish onboarding from relationship authority,
preserve scoped foreign keys/RLS and retain existing budget, ordering, reconciliation and Stop
controls. Provisional state cannot create a Web session or acquire full-account permissions.

A consenting, previously unregistered person messages the Demo business number directly.
WAOOAW verifies the provider event, admits the person through existing shared identity/onboarding
owners, and begins a useful two-way registration/discovery conversation. Neither a marketing
invitation, a portal account, an existing employment relationship nor a manually seeded contact is
a prerequisite to this first-contact journey.

WhatsApp, Web and future clients retain one canonical identity/tenant/membership model and shared
conversation/business owners. A new phone identity must never attach to an existing account or
relationship based only on phone possession, supplied names, payload hints or email equality.
Existing account linking requires the accepted protected proof. Onboarding is not employment
contract creation, payment authority or unconditional professional execution.

Web registration must complete and enter the application reliably when first-load requests run
concurrently. A preferences-initialization race must not misrepresent successful registration as
an unknown registration outcome.

## 3. Verified Evidence And Limits

| ID | Observation, 2026-11-03 UTC | Evidence and interpretation |
|---|---|---|
| E1 | Accepted WhatsApp design includes first-contact admission. | [ADR-023](../adr/ADR-023-whatsapp-phone-identity-c042-agents.md), unknown-contact flow; [solution Section 7.1](../architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md), valid first-contact admission; WC120-R008. Later assurance/owner controls still apply. |
| E2 | Live-provider implementation cannot admit an unknown contact. | [WhatsAppJourneyService](../src/business-platform/Services/WhatsAppJourneyService.cs), `ReceiveVerifiedAsync`: with conversation options present, unknown contact returns `WHATSAPP_IDENTITY_NOT_BOUND`; active channel binding and attached relationship are also required. Legacy auto-registration is not proof of live-provider onboarding. |
| E3 | Protected provider binding assumes prior contact admission. | [WC-121 component Section 10.5](./WC-121-demo-whatsapp-provider-enablement-work-component.md) and [binding schema](../infrastructure/conversation-whatsapp/provider-binding.schema.json) bind one recipient telephone to an existing canonical digest. Completing this unchanged cannot solve first-contact admission. |
| E4 | At 07:19:41-42, concurrent workspace-preference reads caused duplicate insertion. | Demo Log Analytics `ContainerAppConsoleLogs_CL`, BP: two `GetWorkspaceLayoutPreferencesAsync` actions, PostgreSQL SQLSTATE `23505`, constraint `customer_portal_preferences_actor_tenant_unique`, table `customer_portal_preferences`. [IdentityService](../src/business-platform/Services/IdentityService.cs) checks for absence, adds a row and saves without conflict-safe initialization. |
| E5 | The application shell, not a proven failed account-creation transaction, emitted the visible error. | Same window, Web trace: `IdentityApi.getWorkspaceLayoutPreferences` -> `ApplicationLayout`, HTTP 503, error digest `2930745294`. Registration-completion action precedes this. Account existence/completion must be reconciled through the owner; do not ask the user to register again on this evidence alone. An earlier 409 registration-start event is not established as this failure's cause. |
| E6 | At 07:24:35, webhook GET failed before verification. | BP console: `InvalidOperationException: Multiple constructors accepting all given argument types ... WhatsAppJourneyController`. [Controller](../src/business-platform/Controllers/WhatsAppJourneyController.cs) has production and compatibility constructors. Direct constructor unit tests do not prove ASP.NET route activation. |
| E7 | Dedicated callback is not ready. | Read-only probe: `whatsapp-demo.waooaw.com` unresolved; Azure BP custom domains list only `api.demo.waooaw.com`; existing-host webhook GET without challenge parameters returns HTTP 500. No valid-token challenge was performed. |
| E8 | Human-reported Meta progress, not independent provider API verification. | Sender registered; business verification complete; payment added. Body-only English Marketing invitation `waooaw_demo_invitation_v1` submitted, In review when last observed. Exact locale and approval remain unverified. No messages sent or account subscription proven. |

Live log queries were bounded to the reported failure window and named services in Demo workspace
`law-waooaw-demo-validation`. Preserve only redacted time/service/error/constraint/request
correlation evidence. No customer identity, raw phone number, provider account ID, secret, OTP,
payment data or full provider payload belongs in this contract or its implementation evidence.
These observations establish defects, not successful reproduction tests or post-fix acceptance.

## 4. Surgical Scope And Owner Boundaries

In scope:

- BP WhatsApp route activation, verified first-contact identity admission, onboarding and canonical
  conversation integration; necessary protected binding, configuration and activation validation.
- Shared identity registration/membership and linking surfaces only where required for this path.
- BP preference initialization and its shared callers; Web shell handling of explicit API failure.
- Existing generated API clients/specifications only if their public contract actually changes.
- Demo callback DNS/TLS, credential-version admission and registration-only preparation through
  existing deployment/configuration mechanisms, under exact separate live-action authority.
- Focused regression tests, requirement evidence, operator runbook corrections and one combined PR.

Out of scope: media/voice enablement, a new identity service or conversation engine, arbitrary
users/unbounded traffic, Production/UAT mutation, credential-read expansion, automatic account
merging, payment/contract/Stop-release completion through WhatsApp, new marketing infrastructure,
deployment-performance redesign, and unrelated application defects. The earlier cleanup retry
milestone remains separately tracked; this contract does not silently expand into runner work.

Existing local uploader-helper edits are paused, unqualified work, not a deployed feature or an
accepted prerequisite. Reuse only if necessary for the corrected binding model, after validation.
Do not make the Founder repeat intake of the three already-stored credentials unless a specific
validity/version defect requires it. Do not rotate or regenerate secrets as a troubleshooting step.

## 5. Requirements And Executable Acceptance

| ID | Required behavior | Required evidence |
|---|---|---|
| WC133-R001 | A fresh, authorized real-format inbound TEXT event from an approved Demo pilot with no existing contact, portal account, membership or employment relationship reaches the shared admission/onboarding owner and produces a registration/discovery response. No invitation or portal signup prerequisite. | Real-provider-envelope integration test with production dependency registration and empty user state; assert owner calls, canonical persisted identity/state and reply eligibility, not merely HTTP 200. |
| WC133-R002 | Admission establishes only the minimal policy-authorized identity, tenant/membership and onboarding state, with required evidence and consent scope. No random adapter-created tenant/token shortcut, manufactured employment relationship, or implicit marketing opt-in. Concurrent first contact and authenticated provider retries create one logical admission and no duplicate reply/business effect. | Real PostgreSQL uniqueness/concurrency tests; evidence-owner failure, partial commit/crash/retry and idempotent recovery cases; assert no orphan or cross-tenant state. |
| WC133-R003 | Provider binding and bounded pilot authorization can identify an eligible first-time sender before a canonical contact digest exists; after admission they resolve to the canonical binding. Existing-contact replies retain current identity. No circular requirement to pre-register the pilot. | Closed schema/config/runtime/preparer tests together, including first-contact authorization, unauthorized number, ambiguity, reassignment, revocation, expired window and wrong environment/app/WABA/sender; zero authority expansion on denial. |
| WC133-R004 | WhatsApp onboarding/discovery uses existing shared owners and canonical history. Later protected operations obey current assurance floors. A returning user resumes the same state; later proven Portal linking neither duplicates nor transfers accounts/relationships. | Fresh/returning WhatsApp and cross-channel integration tests; unproven linking, wrong tenant/relationship and stale proof denials; Tier 4 operations remain portal-only, including contract creation/payment changes/Stop release. |
| WC133-R005 | ASP.NET activates the actual webhook controller unambiguously through production DI. Disabled GET/POST fail closed without HTTP 500. Authorized GET returns the exact challenge only after correct host/query/token checks, while business POST/dispatch remain independently off. | Host-level HTTP tests, not only `new Controller(...)`; valid challenge, wrong token/host, duplicate or missing query keys, unavailable credential and independent disabled flags; keep legacy compatibility only where needed. |
| WC133-R006 | Shared workspace-preference initialization is atomic or handles only the exact expected uniqueness race safely, preserving actor/tenant scoping and forced RLS. Concurrent initial reads/writes converge to one row; existing preferences, versions and optimistic write conflicts are preserved. | Real PostgreSQL simultaneous first-load tests and read/write race tests, one durable row, consistent returned state, no 23505/503 for expected contention, and unrelated DB errors still surfaced. Do not remove the unique constraint or globally retry writes. |
| WC133-R007 | Web distinguishes registration outcome from post-registration shell/preferences failure. Known registration/session state is preserved; explicit localized retry/unavailable UI replaces an uncaught preferences exception. No silent defaults, swallowed backend errors or duplicate registration submission. | Web API/shell unit tests plus browser journey: fresh registration, concurrent shell requests, preference outage and retry/reload, existing account sign-in, session expiry and registration completion replay. Assert visible output and registration effects. |
| WC133-R008 | Dedicated Demo callback DNS, ownership verification and TLS bind the approved hostname to BP through the existing managed path. Four required protected versions/configuration are validated consistently with the repaired admission model; no public-vault bypass or secret disclosure. | Configuration/infra negative tests; separately authorized live DNS/TLS and exact-version metadata evidence, valid Meta challenge and subscription receipt. Keep POST acceptance, dispatch and provider egress off during registration-only setup. |
| WC133-R009 | A user-initiated conversation does not require the Marketing invitation template. Reply eligibility respects consent, the actual service window and current provider policy. Business-initiated invitations separately require approval, exact locale/body/version, marketing opt-in and bounded spend/traffic authority. STOP prevents further ordinary messages; release remains protected. | In-window reply without invitation, expired-window denial/template path, unapproved or mismatched template and absent marketing consent tests; inbound STOP, repeated STOP and no automatic restart/dispatch. No claim that all operations can complete within WhatsApp. |
| WC133-R010 | One combined PR delivers these repairs with exact-head author review, traceable requirements and wired Docker-only regressions. Provider preparation, deployment, activation and live acceptance remain distinct. All claims name their actual evidence level. | Prepared repository PR template/prechecks, focused tests and required selected gates; separate deployed fresh-user scenario and Web registration acceptance, exact release/configuration evidence and cleanup/rollback receipts before go-live. |

The existing invitation's preview includes `Hello,` before the invitation text. Do not reconstruct
its content or infer an API locale from the display label "English"; retrieve approved metadata
through the authorized provider path before admitting it. Template approval is not a gate for
testing the direct, user-initiated entry path. Payment presence alone is not traffic authority.

## 6. Ordered Execution And Stops

1. **Implementation gate:** obtain explicit current-session authorization; freeze actual branch
   baseline and existing changes. Map the shared admission, membership, conversation and evidence
   owner calls. Identify any missing policy/owner capability before coding.
2. **Reproduce:** write failing production-host webhook activation, fresh-contact provider and
   real-PostgreSQL preference-race tests. Preserve legacy and already-bound behavior.
3. **Repair as one coherent unit:** resolve controller activation; integrate owner-based admission
   and canonical conversation continuation; remove the circular binding prerequisite across all
   validators; make shared preference creation concurrency-safe and Web failure state explicit.
4. **Qualify and deliver one PR:** run focused Docker tests, actual DB races, browser journeys and
   repository-selected mandatory gates. Wire new tests into a command actually run by CI. Complete
   exact-head author review and prepared PR body; Founder reviews/merges. No self-merge.
5. **Registration-only cloud stage:** validate existing credentials, finish approved DNS/TLS and
   protected configuration, deploy the reviewed release under separate authority, then verify the
   Meta challenge and `messages`/account subscription with acceptance/dispatch still off.
6. **Bounded live acceptance:** obtain exact consenting pilot, tenant/admission scope, UTC window,
   count/rate/spend ceilings, incident owner, alert destination and rollback tuple. Activate only
   that approved tuple. Fresh user initiates TEXT; prove onboarding/discovery, response, returning
   continuity and Stop. Separately prove Web registration/first application load. Disable at expiry.
7. **Close:** preserve redacted receipts; remove staged intake material, revoke temporary intake
   assignments and scale down the private import helper once no longer needed. Update current
   state truthfully. Invite additional users only after acceptance and explicit audience expansion.

Prepare independent Meta-side actions before implementation where feasible; do not loop through
already-completed number, business-verification, payment or credential steps. Callback verification
cannot pass against the currently crashing/unconfigured endpoint, so stop that action until the
corrected release and ingress are ready. No unapproved template send, secret in a query-tool
argument, ad-hoc production database seed, policy bypass or cloud drift to simulate success.

## 7. Validation Plan And Completion

Use the existing immutable Docker runners and repository test commands; no host test execution or
new dependencies solely for this repair. Exact new selectors are recorded when authored:

- BP `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj` with focused
  WhatsApp/identity/preferences selectors first; production-host integration and actual PostgreSQL
  concurrency are required, not EF in-memory substitutes.
- Existing Web test gate `sh scripts/validation_control/run_web_test_gate.sh`, with focused API,
  application-shell and registration browser journeys before escalation to the selected full gate.
- Relevant pipeline/contract tests for provider config, binding schema, activation, infrastructure,
  shared uploader if retained, and ledger consistency.
- Mandatory build/type/lint, secret, authorization and exact-head PR gates remain in force.
  Release Qualification is OFF under the explicit Founder amendment in Section 2, not a
  self-issued waiver.

Each requirement stays PLANNED/BLOCKED until its exact acceptance evidence exists. Local tests
cannot prove Meta ownership, subscription, live identity admission, DNS/TLS or user-visible Demo
success. PR merge/deployment cannot substitute for fresh-user live acceptance. Any unknown send
outcome is reconciled, never blindly replayed.

**Definition of Done:** R001-R010 have their required evidence; a genuinely new approved pilot can
start through WhatsApp without portal registration or invitation; returning/cross-channel identity
is preserved; the new Web user reaches the application without the preference race; Stop and
bounded rollback pass; one combined corrective PR is Founder-merged; required live gates and
acceptance are separately recorded. This draft claims none of those outcomes as completed.

## 8. Repository Implementation And Evidence

The current-session amendment implements a bounded pre-employment path, not phone-only full
account registration. `identity.phone_onboarding` retains the approved tenant/pilot tuple,
stable participant, first verified observation and CE evidence reference. A durable pending row
confers no admission or outbound eligibility; evidence failures retry with identical evidence
inputs. STOP is irreversible through this path and can latch before admission. No account,
login method, OWNER membership, relationship or Web session is manufactured.

This explicitly amends WC-121 Section 10.5's prior-admission prerequisite for the approved
provisional mode: the protected opaque pilot digest is reserved before first contact. The
closed provider-binding document remains unchanged. The independently approved activation
bundle must explicitly set `AllowProvisionalOnboarding`; omission remains OFF. Exact sender,
provider/environment, recipient, expiry, authority and traffic limits still apply.

The existing shared Portal interaction owner stores canonical customer/guide turns in its
MARKETPLACE surface, uses the existing professional catalogue for discovery, and serializes
concurrent sequences/idempotency. Its public API surface enum is unchanged. Full-account linking
and cross-tenant history transfer are not inferred from phone possession; the existing protected
proof requirements remain. No successful provisional-to-full-account link is claimed here.

The existing shared outbox, worker, provider transport, traffic budget and delivery reconciliation
are reused. Nullable relationship fields are legal only in the explicit onboarding scope, with
tenant-bound Portal context/message foreign keys and separate uniqueness constraints. Existing
relationship foreign keys remain. Canonical GUIDE content, evidence-confirmed admission, service
window and STOP are checked before egress; business-initiated templates are not admitted for this
scope. Unknown/reserved attempts cannot be blindly resent.

Migration `67-wc133-phone-onboarding.sql` is additive, transactional and repeatable. The existing
managed provisioner's lexical SQL chain and Demo startup apply it; auth-preview explicitly reapplies
it for persisted volumes. No deployed database was modified during these tests.

Shared preference initialization uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` followed by
the existing scoped row under `FOR UPDATE`, preserving settings and expected-version semantics.
The Web shell logs preference-load failure, preserves the valid session, hides protected children,
and offers a localized workspace retry without requesting another registration.

### Recorded Docker Validation

All commands ran in the existing immutable runners, not on the host. The .NET runner receives
the Docker socket, `TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal` and
`GITHUB_WORKSPACE=/workspace`; the last setting is required by existing repository fixtures.
An initial full-suite invocation without that setting failed repository-file discovery; the
corrected invocation below passed. No product or test guard was weakened.

| Exact runner command | Result |
|---|---|
| `sh scripts/validation_control/run_dotnet_test_gate.sh business-platform tests/business-platform.Tests/business-platform.Tests.csproj` | PASS: 1,217 tests, no skips; 90.49% lines and 80.17% branches, above 90%/80% thresholds. |
| `sh scripts/validation_control/run_web_test_gate.sh` | PASS: TypeScript and ESLint; 720 tests, three existing skips; global coverage thresholds passed. |
| `python -m pytest -p no:cacheprovider tests/pipeline/test_wc091_environment_readiness.py tests/pipeline/test_wc120_whatsapp_activation.py -q` | PASS: 156 tests. |
| `python -m pytest -p no:cacheprovider tests/validation_control/test_catalog_contract.py tests/validation_control/test_gate_equivalence.py -q` | PASS: 75 tests. |
| `sqlfluff lint infrastructure/postgres/init/67-wc133-phone-onboarding.sql --config .sqlfluff` | PASS; existing configuration deprecation warnings remain. |
| `sh scripts/validation_control/run_dotnet_quality_gate.sh src/business-platform business-platform` | PASS: formatting and strict build, zero warnings/errors on the final implementation. |
| `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj -warnaserror --filter "FullyQualifiedName~ConversationWhatsAppFitness\|FullyQualifiedName~WhatsAppWebhookHostTests\|FullyQualifiedName~PortalInteraction\|FullyQualifiedName~IdentityPreferenceConcurrencyTests\|FullyQualifiedName~IdentityWorkspaceLayoutTests" --verbosity minimal` | PASS: 139 final-diff regressions after the full-suite run, including wrong-host rejection and final admission-authority recheck. |
| `pnpm exec jest --runInBand --runTestsByPath __tests__/app/application/layout.test.tsx lib/i18n.test.ts` | PASS: 16 final-diff tests, including successful same-session retry after preferences recover. |
| `pnpm exec tsc --noEmit --incremental false` | PASS on the final Web diff; focused ESLint and Biome checks also pass. |

The new PostgreSQL regression exercises actual MVC routing and a signed provider envelope for a
previously unknown sender, replay, evidence failure/recovery, concurrent turns, canonical reply
queueing, no full-account/membership side effects, forced-RLS isolation, service expiry and STOP.
Provider tests exercise canonical onboarding egress, shared budget, no resend and delivery
reconciliation. New C# tests are collected by the existing BP project gate; protected-intake and
activation regressions are also wired into `quality-scripts`, independently of Release Qualification.

The branch also retains the previously authorized, independently tested WC-120/WC-121 private
cleanup retry milestone. It is disclosed separately, not claimed as WC-133 admission evidence.

Release Qualification was NOT run. Exact-head signing, author-review and prepared-PR checks must
still pass before submission. DNS/TLS, the fourth protected binding, reviewed deployment, Meta
challenge/subscription, fresh-user Demo/browser acceptance and intake teardown remain independently
gated and pending. These local results do not authorize go-live or audience expansion.

### PR #577 Precheck Correction

The Founder requested correction of the PR precheck failure. CodeQL reported a useless
null-coalescing expression in delivery correlation, an undisposed test `StringContent`,
mixed Python module-import styles and two unformatted UUID string conversions. Correlation
now selects the message reference explicitly from its declared relationship/Portal scope.
The test owns/disposes its request content; Python uses consistent from-import syntax; SQL
tenant parameters retain explicit canonical UUID text rather than changing parameter types.

Docker validation: `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj
-warnaserror --filter "FullyQualifiedName~ConversationWhatsAppFitness|FullyQualifiedName~WhatsAppWebhookHostTests|FullyQualifiedName~IdentityPreferenceConcurrencyTests"
--verbosity minimal` PASS, 112 tests; CSharpier check PASS.
`python -m pytest -p no:cacheprovider tests/pipeline/test_goal006_runner_lifecycle.py -q`
PASS, 59 tests; focused Ruff PASS. This correction changes neither onboarding authority nor
traffic configuration. Release Qualification remains OFF. Hosted CodeQL confirmation follows
the updated head; no passing hosted result is claimed from local tests.

### Post-Merge Migration-Chain Regression

PR #577 merged as `2d249ec`. Main CI run `41606247862` failed Release Qualification:
`test_application_migrations_cover_the_whole_sql_chain_after_the_principal_bootstrap`
hardcoded migration 61 as the final SQL file, while the unchanged runtime loader correctly
included WC-133 migration 67. The group reported 557 passed/1 failed; Test Champion
blocked downstream. PR qualification OFF does not disable mandatory main qualification.

The Founder authorized this follow-up correction. The original test reproduces red in
Docker. The corrected test asserts complete SQL-file coverage, bootstrap exclusion,
byte ordering and required migrations including WC-133, without fixing the final suffix.
A synthetic future-migration regression verifies later SQL inclusion and non-SQL exclusion.
`python -m pytest -p no:cacheprovider tests/pipeline/test_wc124_db_provisioner.py -q`
PASS, 41 tests; focused `ruff check --no-cache` and `ruff format --check --no-cache`
PASS in the immutable Python runner. No runtime, migration, dependency or workflow changes.
Full Release Qualification was not rerun locally; the follow-up PR retains Founder OFF
authority, and post-merge qualification remains mandatory.

### Consolidated Provider Completion Authority

After deployment and human credential intake, the Founder explicitly directs one PR to
find and repair the missing completion steps. All four exact credential versions are
metadata-confirmed; the dedicated callback CNAME, ownership TXT and Azure-managed TLS
are verified. These facts do not enable business callbacks or outbound traffic.

The approved repair adds protected Demo-only registration, status, bounded activation,
stop and intake-cleanup operations through the existing private runner/deployment identities.
It must reuse runner start/terminal cleanup and the shared activation validator, accept
only closed non-secret registration/activation documents, pin the deployed image and
configuration/catalog tuple, conditionally update the private configuration with ETags,
preserve unrelated configuration and runtime settings, and retain redacted operation evidence.
Registration must explicitly disable business callbacks, dispatch and provider availability;
activation still requires the separate independently approved exact bundle digest and all
existing receipts. No workflow may fabricate receipt completion or send a test message.
Stop must close runtime traffic without requiring a currently valid activation bundle.
Intake cleanup must target only the dedicated intake app and four temporary secret grants.
No database reset, full environment redeployment, new identity/service/network access,
raw credential export, automatic Meta subscription or new runtime authority is authorized.
The uploader must retry an invalid field without discarding earlier protected input.

#### Operator Completion Path (one existing Environment Deployment workflow)

Use the existing Founder-dispatched **Environment Deployment** workflow on current main,
environment `demo`, execution `plan`, with `provider_operation` set as below. The provider
operation bypasses Terraform/image application and the Demo database-reset lifecycle.
The existing private broker, environment-bound OIDC identities, deployment concurrency
and terminal runner cleanup remain mandatory. `none` preserves ordinary plan/apply behavior.

| Operation | Input | Result / independent next gate |
|---|---|---|
| `register` | `provider_document`: closed registration object (`callback_host`, four `secret_versions`, `authority_reference`, `verification_enabled: true`); no raw Meta IDs, numbers or credentials | Back up the prior private configuration, ETag-conditionally persist registration only, grant BP read access on the four exact purposes, set its explicit managed-identity client ID and pinned version references; verify ready revision, valid HTTPS, invalid-token GET401 and callback-disabled POST503. Callback, dispatch and provider-availability flags remain OFF. |
| `status` | `{}`; no approval digest | Inspect current deployed image/flags and TLS/invalid-token rejection; no mutation. It does not assert Meta registration, delivery or live acceptance. |
| `activate` | Closed existing activation bundle in `provider_document`, exact separately approved `provider_approved_digest` | Reuse the activation validator; require current registration/image/catalog, valid credential-version metadata, distinct traffic/activation approvals, receipts, consent, tenant/pilot, policies, templates, limits/window. Apply only those runtime settings; on failure attempt traffic closure and explicitly mark unconfirmed containment. No test message is sent. |
| `stop` | `{}`; no approval digest | Disable callback acceptance, dispatch and provider availability and latch revocation; no current activation bundle or private configuration download is required. |
| `cleanup-intake` | `{}`; no approval digest | Revoke only the dedicated intake identity's four temporary declared-secret-provisioner assignments, set the dedicated intake app minimum to zero and deactivate its revisions; verify grants/revisions closed. It does not remove BP credential access. |

Registration requires the dedicated DNS/TXT/SNI binding already to be present; no automatic
DNS mutation is added. After registration, the Founder enters the callback URL and retained
verify token directly into Meta, verifies/saves and subscribes the appropriate webhook field.
These external-account steps cannot be inferred from GET401 or a registration setting.
Activation is never implied by registration, subscription, deployment or this PR.
Activation documents contain only the existing closed authority/evidence/policy/template
metadata, not secrets or raw provider/contact identifiers. Do not put credentials in Actions
inputs. Only redacted per-phase evidence is retained as Actions artifacts; private operation
files are removed on all terminal paths. Partial registration leaves a recoverable staged
configuration and private before-snapshot, not traffic permission; rerun the same operation
after correcting the explicit failure. A later full deployment adopts existing callback
TLS/domain and exact BP secret roles into Terraform state rather than recreating them,
and deliberately returns runtime traffic to the normal registration-only OFF defaults.
Reactivation after stop/full deployment must register the current tuple and obtain a fresh
independently approved activation bundle; do not reuse stale receipts or windows.

#### Consolidated Author Validation

The deployed BP uses Multiple revision mode with latest-revision ingress. Runtime
operations therefore reuse the existing Demo revision reconciler, restricted to BP,
and retire zero-traffic obsolete workers before reporting success. Failed activation
reports traffic closed only after the OFF revision is ready and obsolete workers have
zero replicas; otherwise containment is explicitly unconfirmed. Intake cleanup likewise
requires zero replicas. Other Demo apps are not inspected or changed by selected-app cleanup.
The authoritative configuration is rechecked immediately before runtime application;
concurrent configuration drift fails before settings are mutated.

Focused immutable Docker Python validation passes **446 tests**, including registration,
exact activation approval, ETag conflicts/readback/drift, credential metadata validity,
TLS negative probes, settings preservation, old-worker retirement, containment failures,
intake closure, Terraform adoption, uploader retries and deployment/gate compatibility.
Ruff check/format and repository-pinned actionlint pass. New operations and selected-app
cleanup regressions are wired into the explicit quality-scripts gate.
No new helper has been executed against live configuration, roles, revisions or Terraform
state. Meta challenge verification/subscription, actual registration application and bounded
live/browser acceptance remain gated. No messages, full deployment or database reset occurred.

### Registration Failure RCA And Surgical Recovery - 2026-11-03

The Founder reported registration run
[41636191635](https://github.com/dlai-sd/waooaw-platform/actions/runs/41636191635)
failed and explicitly authorized watching terminal cleanup, evidence-backed repair,
downstream simulation/audit, tests and a new PR. Current-session implementation authority
was explicitly reconfirmed. The deferred configure-once deployment/activation design review
is not reopened by this correction.

| Evidence | Observed result / limit |
|---|---|
| Completed run at `a380afb089f9573c82fb176223b67713d58568ea` | Authorization, environment resolution and private broker succeeded; provider preparation failed; Terraform, verification and URL publication skipped. |
| Provider job `125919176046`, failed prepare step | `OPERATION=register`, closed registration metadata, blank activation digest; `KeyError` before persistence/application. No incorrect input or credential value is established. |
| `whatsapp-operation-41636191635-1/evidence-prepare.json` | `phase=prepare`, `operation=register`, `status=FAILED`, `error_type=KeyError`. The old artifact deliberately omitted the missing key and stack; it does not independently identify the key. |
| Existing deployment producer | `goal006_deployment_inputs.add_key_vault_references` derives runtime vault maps from foundation metadata before workload input validation; those derived maps are not required in the stored source blob. |
| New original-code regression with the stored pre-hydration shape | Reproduces `KeyError: key_vault_secret_uris` through `prepare -> planned_settings -> deployment -> whatsapp_provider_inputs -> whatsapp_provider_configuration`. Previous tests supplied already-hydrated maps and missed this producer/consumer boundary. |
| Terminal cleanup job and `goal006-private-runner-cleanup-41636191635-1/cleanup-record.json` | Cleanup succeeded, `producer_status=Succeeded`, with original private-job conclusion `failure`. No runner cleanup failure is being conflated with registration RCA. |

The proven defect is consuming persisted source configuration as though it were generated
deployment inputs. The surgical fix reuses `add_key_vault_references` when resolving the
provider deployment view, deriving only the canonical Demo vault root from the observed
BP ARM resource ID. It rejects a different group/app or conflicting stored vault maps.
Derived maps stay in memory: source snapshots, CAS readback and unrelated numeric fields
remain unchanged, and only the closed provider registration is persisted. The later
registration RBAC scope also uses the resolved view, preventing the next missing-map
failure after persistence. Activation revalidation and Terraform adoption use the same path.

Downstream audit also removes implicit Microsoft Graph lookups from all provider role
queries: use the known principal object ID plus `--fill-principal-name false`. Installed
Azure CLI help documents this contract; a read-only query on the exact live BP secret scope
succeeds without Graph (no existing role returned; no role was created). Source-only
failure file/function/line is now retained in redacted evidence without exception arguments,
private keys/values or frame locals, so a later structural failure is diagnosable.

Stateful no-network simulations execute the real prepare/persist/apply entry points and
revision reconciler across raw-source registration, repeat registration, status, separately
approved synthetic activation, stop, intake cleanup and Terraform adoption. They assert
four exact role grants, CAS/backups, no Graph query, unchanged source configuration,
unrelated runtime secret-reference preservation and obsolete-worker zero-replica closure.
Three additional simulations inject activation-update, old-worker-retirement and
containment failures, proving explicit failure and confirmed closure versus operator escalation.
Synthetic authority/receipt fixtures are test-only, not live approvals.

Validation: the original missing-reference regression fails before the fix; **456 focused
Docker Python regressions pass** afterward, including the four full lifecycle simulations.
Ruff check/format and diff hygiene pass. Existing explicit quality-scripts wiring already
collects the changed tests; no new gate or dependency is added. No workflow form, runtime
source, credential, network policy or live setting is changed. Full Release Qualification
remains OFF under continuing Founder authority; other mandatory PR checks remain required.
Actual registration must be retried only after Founder review/merge and separate execution
authority; Meta Verify/Save/subscription and activation are not completed by these simulations.

### Safe Webhook Verification Diagnostics - 2026-11-03

The Founder explicitly authorizes safe verification diagnostics, disposable local simulation,
tests and one PR after Meta continues rejecting the callback. Current-session implementation
authority is confirmed; this does not authorize deployment, activation or weakening validation.

Registration run41669336013 at4fc35e7 succeeded with verification enabled and business traffic
OFF. Scheduled cost-stop41675256742 later stopped BP; the Founder started applications again.
The Founder retrieved the exact pinned verify-token value privately through the existing intake
terminal. The newly granted intake token-read assignment was revoked and absence verified after
human retrieval; no assistant secret read occurred. WABA subscription POST returned success,
and the Founder confirmed the app in the subsequent subscription GET.

Two human private tests returned HTTP200 with an exact plain-text challenge; the second also
confirmed the Meta-field token matched exactly with no surrounding whitespace. Existing Azure
telemetry shows a fresh verification action at17:26:04 UTC returning ProblemDetails in roughly0.5ms,
but records no status or rejection reason. ProblemDetails is not proof of503: a dummy-token
probe also returns401 with ProblemDetails. The earlier credential-unavailable interpretation
is withdrawn. Exact Meta rejection cause remains unproven; extra query fields are a hypothesis,
not permission to relax the closed query contract.

The controller now emits one structured verification record per final result, with only
StatusCode, a fixed safe Reason, distinct QueryCount and counts for the three documented keys.
Do not log parameter names supplied by callers, values, query/URL, hostname, headers, challenge,
exception arguments, body, secret length/digest or provider credential data. Safe reasons cover
disabled verification, host mismatch, oversized target, closed query shape, missing/duplicate/
empty/oversized parameters, wrong mode, unavailable expected token, token mismatch, credential
unavailability and successful challenge. Exact host/token comparison, query limits, status
semantics, response body and business gates are preserved. Successful preflight does not emit
a misleading success record before credential verification.

Disposable TestServer hosts simulate fifteen synthetic request variants through actual MVC,
including Meta-style User-Agent/Accept, unknown query/header canaries, duplicates, missing/large
values, disabled/host gates and credential failure. The oversized-target simulation explicitly
supplies RawTarget because TestServer does not populate it like live Kestrel. Tests assert exactly
one log record, the closed seven-field structured payload (including logger format), no private
canary values or exception, no credential reads after preflight rejection, exact text/plain
success and callback-disabled POST behavior. These test-only hosts are the throwaway local
probe; no second public callback or live credential utility is introduced.

Immutable Docker .NET targeted host/provider/journey validation passes131 tests with no skips,
including fifteen new diagnostic simulations; CSharpier formatting and diff hygiene pass.
Signed milestone983e5277 passes all six mandatory staged gates, including full Business Platform
1,233 tests with zero skips/failures and90.49% line/80.19% branch coverage, plus the Web gate.
GitHub verifies the signature; exact-head preparation passes and PR581 is open for Founder review.
No live diagnostic code has been deployed. After Founder review/merge/deployment, keep traffic
OFF, perform one Meta Verify/Save attempt and query only this safe log category to identify the
actual rejection before deciding on a behavioral correction. Do not enable broad request logs.
