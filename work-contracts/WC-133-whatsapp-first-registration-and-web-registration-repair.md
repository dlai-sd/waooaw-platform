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
milestone remains separately tracked; runner work requires separate explicit authority, recorded
for WC133-R011 in Section 8 below.

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
| WC133-R011 | Explicitly authorized 2026-11-06 runner recovery pins supported version 2.338.2, enforces a fail-fast exact-version check, refreshes bootstrap hashes and preserves the existing toolchain/private lifecycle. | Original-pin regression failure, rebuilt exact-container toolchain/Terraform/Storage lease checks, runner lifecycle tests and wired catalog regression. Main-only attested publication, actual environment-pin adoption and live job/cleanup acceptance remain separate downstream steps; no application deployment or database reset. |

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

### Registered-Provider Deployment Inventory Repair - 2026-11-04

The Founder authorizes the current-session implementation, regression validation and one PR
for failed Environment Deployment run41769569756, not a deployment retry or activation.
At commit a559caf, step26 Check credential inventory fails at03:56:38 UTC:
goal006_deployment_credentials.py:62 calls whatsapp_provider_configuration, whose line85 reads
key_vault_secret_uris from the persisted source and raises KeyError. Step42 would generate
these foundation-derived maps, but cannot run before inventory. Existing shell tests supplied
already generated maps and therefore missed registered-provider source configuration.

Resolve the inventory's configuration view in memory with the existing add_key_vault_references
helper and the current job's trusted foundation vault ID/URI. The CLI must accept those inputs
as a pair, reject inconsistent supplied runtime maps rather than silently overwrite them, and
preserve the existing closed Demo provider/vault/secret-version validation. Do not persist the
generated view, change pinned versions, log secrets, seed external credentials, weaken expiry
checks or infer provider activation. Disabled providers and existing hydrated callers retain
their established selection behavior. The normal deployment must need neither a prior separate
WhatsApp deployment nor another provider-registration operation merely to pass inventory.

Regression evidence must exercise the actual workflow inventory shell and Python CLI with raw
registered source configuration, not mock the parser or hand it generated maps. Cover absent
and already resolved maps, enabled/disabled verification, invalid/foreign vault/provider
configuration, missing/disabled/expired credentials, no-expiry outbound rules, argument-pair
errors, unchanged source bytes, exact pinned reads, and continuation into workload-input
generation with the same provider version binding and business gates OFF.

The failed run did start the persistent database; reset steps31-33, workload generation,
Terraform workload plan/apply and activation were skipped. Terminal database-authority cleanup
and private-runner cleanup succeeded. Diagnostics from PR581 were merged but not deployed.
This repair does not claim that every possible later live stage has been qualified; fresh
deployment and Meta verification remain separate Founder actions.

Author regression evidence: the actual inventory shell with raw configured provider reproduces
the live KeyError before the repair (one selected test fails). After repair, immutable Docker
validation passes309 tests across environment readiness, workload inputs, Demo deployment
workflow and provider operations. This includes raw/resolved source, both verification states,
credential validity and continuation into workload-input generation, plus17 CLI positive/
negative cases. Ruff check/format, dedicated actionlint1.7.7 and diff hygiene pass. An initial
actionlint invocation in the general runner failed because it does not contain that binary;
the repository's dedicated actionlint image succeeds. Existing quality-scripts wiring already
collects the modified readiness test file. No dependency or gate is added; mandatory signed
commit and exact-head preparation still apply. Release Qualification remains OFF under the
continuing Founder authority; main qualification remains unchanged.

### PR582 Image-Scan Precheck Repair - 2026-11-04

The Founder requests repair of PR582 precheck failures. CI41776122680 builds both .NET images,
then their Trivy steps exit1; Test Champion blocks only on the failed build aggregate. A local
scan of the existing Business Platform image reproduces HIGH GHSA-p3jp-9v83-76w9 against
Microsoft.NETCore.App.Runtime.linux-x64 9.0.21, with9.0.22 listed as fixed. Both affected
Dockerfiles pin the same9.0.21 runtime; direct code-scanning alert retrieval is denied403, so
do not claim access to the private hosted SARIF details.

Patch only Business Platform and Constitutional Engine runtime pins to ASP.NET9.0.22 at
registry-resolved immutable manifest digest
sha256:8bbd3f6fcc157792d96f0932107d9d435df814a2c058ce2891a267fe341dea1a.
Update the existing packaging regression, rebuild both images and require zero fixable
HIGH/CRITICAL scan findings. Preserve scanner policy, SDK, business behavior and provider
gates. This is a patch-runtime refresh within the existing Docker packaging specifications,
not new functionality, permission, deployment or activation.

Both patched production images build successfully. Trivy0.73.0 image scans with
--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 pass with zero findings for both.
The deployment-shaped Business Platform image smoke passes; Constitutional Engine reports
Microsoft.AspNetCore.App and Microsoft.NETCore.App9.0.22. Packaging regressions pass16 tests.
Mandatory staged/exact-head checks and hosted rerun remain required before final handoff.

### Provider State Adoption Repair - 2026-11-04

The Founder authorizes the current-session adoption repair, secret-safe retained evidence,
executable regression validation and one PR. Do not change deployment database handling,
reset ordering, schema, activation, runner lifecycle or cost policy. No deployment retry,
remote Terraform state mutation or Azure resource mutation is authorized.

Run41780407025 at04ecb40 fails step43 before actual Terraform validation/plan. The adoption
helper captures a RuntimeError but discards subprocess stderr and reports only its type;
evidence-adopt.json is not included in the normal deployment artifact. The four Demo databases
were already reset, consumers remain quiesced, and terminal database-authority/private-runner
cleanup succeeds. This repair must not change that workflow's database behavior.

Read-only Azure metadata confirms BP's ID uses Microsoft.App/containerapps, while AzureRM4.14
custom-domain imports require Microsoft.App/containerApps. Existing adoption forwards the raw
ID; its tests mock all Terraform imports as successful. The existing
goal006_azure_resource_id.canonical_container_app_id helper already defines the required
scope/name validation and canonical static segments. Reuse it for provider-domain imports.

The actual Terraform1.9.8/AzureRM4.14 CLI against an isolated LOCAL backend reproduces the raw
ID failure: parsing staticContainerApps, expected literal containerApps. Repeating the same
custom-domain import with the canonical ID succeeds. Existing CLI authentication is copied
only into ephemeral container storage; these experiments read Azure metadata and write only
isolated local state, not Azure resources or shared Terraform state. Earlier read-only CLI
cache mounting failed on local index writes; ephemeral copying resolves that test limitation.
The original suppressed command output is unavailable, so distinguish this deterministic
reproduction from a recovered original stderr.

Add typed safe subprocess failure metadata: tool, allowlisted command stage, exit code and
closed reason class. Never emit raw stderr/stdout, credential values, command arguments,
access tokens or Terraform variable/state contents. Retain the adoption evidence in the
normal deployment artifact and print only this closed diagnostic payload. Preserve existing
fail-closed behavior and independent provider gates. Regression cases must include actual
Azure casing, scope/name rejection, repeat adoption, import/state/Azure failures, terminal
evidence privacy and unchanged database-handling workflow steps.

Validation: the new adoption casing regression against original code fails for lower/upper
Azure static segments (two failures, canonical case passes); the patched focused Docker suite
passes302 tests across provider operations, shared ID canonicalization, deployment workflow and
credential inventory. Ruff check/format, actionlint1.7.7 and diff hygiene pass. The sole workflow
change adds workload/evidence-adopt.json to the existing always-upload artifact list; every
job/step run command, condition, environment, database reset and ordering remains unchanged.

The isolated real-provider experiment also imports all four existing exact-scope role
assignments successfully. terraform validate succeeds and terraform plan -detailed-exitcode
returns0, with no changes for the five adopted resources. This is not a full workload plan,
not deployment-identity permission validation and not proof of later migration/activation
stages. Test hosts use the actual Terraform1.9.8/AzureRM4.14 provider, with local-only state
and provider registration disabled. No remote state write, apply or credential-value read
occurs. Raw/canonical import and role/plan logs remain in the session evidence.

For future failure diagnosis, inspect evidence-adopt.json command_failure fields and source
location. RESOURCE_ID_CASE_MISMATCH identifies the verified provider-parser defect;
AUTHORIZATION_DENIED, STATE_LOCK_FAILED, REMOTE_OBJECT_NOT_FOUND, RESOURCE_ALREADY_MANAGED,
CONFIGURATION_INVALID and COMMAND_FAILED identify bounded alternatives without printing raw
provider output. Do not retry a full deployment based on COMMAND_FAILED alone. Release
Qualification stays OFF under continuing Founder authority; other mandatory gates remain.

### Meta Verification Query Compatibility - 2026-11-04

Deployment41787273567 atda79da4 completes successfully, including Demo apply, verification
and private-runner cleanup. The next human Meta Verify/Save attempt fails. The deployed
revision ca-demo-business-platform--0000101 logs at08:20:01.9981802 UTC:
StatusCode=401, Reason=QUERY_SHAPE_INVALID, QueryCount=6, ModeCount=1, TokenCount=1,
ChallengeCount=1. This proves the closed three-key query rule rejects the actual request
before protected token matching; it does not establish the token or extra parameter values.
No raw query, headers or credential values were retrieved.

The Founder explicitly confirms current-session implementation/tests/one-PR authority.
Allow additional query parameters without maintaining a provider-specific allowlist.
Ignore their values for verification and never log them. Preserve exactly one nonempty,
bounded mode/token/challenge; exact subscribe mode, constant-time pinned token comparison,
expected callback host, the inclusive8192-byte total request-target limit, existing status
semantics and exact plain-text challenge. Missing or duplicate required fields must still
fail even if extra keys bring the distinct query count to six. Required values remain
bounded to1024 UTF-8 bytes. POST authenticity/acceptance/dispatch and all business gates
remain unchanged. Earlier closed-query diagnostic observations above are historical.

Validate through disposable real MVC/TestServer hosts with synthetic six-key requests,
additional-key variations, required-field negative cases with extra keys, exact size
boundaries, private canaries and no credential access on preflight failure. Record actual
RED/GREEN and mandatory gate results before handoff. No deployment, reset, activation,
workflow/database change, credential rotation or hosted-check watching is authorized.
Release Qualification remains OFF under continuing Founder authority. Successful local
verification does not substitute for a successful later human Meta Verify/Save attempt.

Executable evidence: before the controller change, the new MVC regressions fail14/pass23,
including the six-key challenge rejected with401 and negative cases masked by the closed
query rule. After the fix and expanded missing/oversized-field matrix,96 focused
host/journey/provider tests pass with zero skips. Tests cover8192-byte acceptance and
8193-byte rejection, repeated/empty unrelated keys, six-key success, required-field
negative cases with extras and unchanged host/credential/disabled gates. Exact response
text/plain, one closed diagnostic record, private-canary exclusion and preflight
credential-read behavior are asserted. CSharpier format/check passes for all three
changed C# files; build with warnings-as-errors passes. Mandatory gates and exact-head
PR preparation remain required; no deployment or live Meta success claimed.

### Private Activation Status Evidence - 2026-11-04

Meta verification and messages subscription are now human-confirmed; the deployed revision
returns200 CHALLENGE_RETURNED with six keys at09:30:12 UTC. The Founder approves a personal
30-minute test, ten total messages/replies and INR10 spend, then authorizes a narrowly scoped
tested PR if an actual tool gap requires it. No broader customer consent is implied.

The existing provider-only status route starts the sanctioned private runner but does not
download registered configuration or validate its exact credential-version metadata. Local
storage access is denied by expected private networking; no firewall exception is permitted.
Extend existing status to inspect registered configuration with conditional downloads and
revalidate its image, identity and metadata at application time without resource mutation.
Export only verified registration release/configuration/catalog digests, fixed registration
alignment outcomes, credential metadata readiness and missing activation field groups.
Never export the stored document, caller-controlled configuration fields, raw Meta IDs,
telephone/contact/tenant values, tokens, secret values, policies or template bodies.

Status PASS means the read-only inspection completed, never activation or qualification.
Report absent activation authority, policy inventory, template inventory and rollback tuple
as explicit missing groups. Counts/presence are not proof of consent, approved templates,
healthy alert delivery, pricing or rollback effectiveness. Reject configuration/image drift
and invalid metadata explicitly. No writes to Azure, source blobs, Terraform state, RBAC,
database schema/data or runtime settings; temporary private files are removed by the existing
workflow cleanup. Reuse existing status dispatch and artifact upload; no workflow change.
Do not invent independent receipts or an approved activation-bundle digest. Qualification
OFF continues for this repair, with mandatory author review/tests/preparation required.

Validation:275 focused Docker provider-operation/activation/readiness tests pass; Ruff
check/format and diff hygiene pass. New configured/unconfigured status scenarios execute
prepare/persist/apply through the real entry point, asserting conditional private reads,
metadata readiness, private-canary exclusion, mode0600 private downloads and no storage,
runtime or role mutation. Image/configuration drift and invalid metadata are rejected.
The existing full lifecycle simulation still covers registration, activation, containment,
Stop, adoption and intake cleanup. Status before registration remains supported, with an
explicit NOT_CONFIGURED result. No live private status run or activation claimed by these
local tests; the existing Founder-dispatched provider-only status workflow is the next
operator step after review/merge, not a full deployment or database reset.

### Consolidated Activation Package - 2026-11-04

The Founder requests one complete tested PR for remaining preparation and operator steps,
then approves proceeding. Existing implementation authority continues. Status run41829928432
passes privately: pinned credential metadata READY and registration matches runtime.
Authority, policies, rollback and template groups are absent. Do not equate this successful
inspection, the earlier bounded personal-test consent or passing tests with exact activation
approval or fabricate real provider templates, policies, pilot identity or readiness receipts.

Provide one existing-provider workflow path from assembly to activation and Stop. Add a
read-only-runtime assemble operation that takes a closed non-secret input profile containing
actual authority/consent/limits/window, binding digests, policy versions, approved template
inventory, rollback digest and all prerequisite receipt references/digests/expiry. Derive
release, registration configuration, catalog and activation configuration digests from the
current registered private deployment, not hand-entered guesses. Validate through the same
activation rules without self-approving the output. Store exact candidate bytes create-only
under the private operation/run prefix; publish only candidate reference/digest and expiry.
This is the only new storage write; never change registered configuration or runtime.

Activate may use the private candidate reference plus the independently approved exact digest.
Resolve with ETag-conditional read; rerun all existing tuple/window/metadata/runtime checks.
Reject wrong digest, image/configuration/identity drift, malformed references, absent/expired
receipts, unsupported templates and missing policies before effects. The assembler cannot
prove external receipt truth, alert delivery, pricing or provider template approval; operator
instructions must require actual accepted evidence. No sample fixture is live configuration.

Preserve legacy inline activation and registration/status/Stop/cleanup behavior. Expand only
provider-operation selectors; prove all other workflow jobs/commands/database handling
structurally unchanged. Runtime source, database handling and schemas remain unchanged.
Provider secrets are never accessed. Network rules and existing permissions remain unchanged.
No new public endpoint, application rebuild or full redeployment is permitted. Tests
must execute assemble/private storage/exact approval/activate/Stop, no-write denials and
failure containment. Document one complete operator runbook with exact inputs, approval,
expiry, reply/continuity/Stop evidence and cost review; do not promise live readiness from PR.
For renewed assembly/activation after Stop, compare actual provider registration fields as
status already does, excluding the effective `WhatsAppCapability__ConfigurationDigest`
that a previous activation intentionally overwrote. The activation validator still recomputes
and binds the exact registration and effective configuration digests; no stale provider,
release, catalog, secret-version or identity mismatch is accepted. Test a new independently
approved candidate after Stop without requiring a reset or re-registration.

**Local validation:** Docker-owned immutable Python runner
`sha256:0e0f86ee4e41c88e983b2d084bef97a6c1fd67b4c5015cb3152c36a634cc832e`
executes `pytest tests/pipeline/test_goal006_runner_bootstrap.py
tests/pipeline/test_wc132_demo_reset_recovery.py tests/pipeline/test_wc091_environment_readiness.py
tests/pipeline/test_wc120_whatsapp_activation.py tests/pipeline/test_wc133_whatsapp_operations.py
tests/pipeline/test_goal006_demo_revision_cleanup.py -q -p no:cacheprovider
--junitxml=/evidence/provider-controls.xml`: **380 passed, zero skipped**. Includes activation67
and operations98, both legacy-inline and candidate-reference activation, simulated Azure
assembly/create-only storage/conditional exact readback/activation/Stop, rollout/retirement/
containment failures, expired/wrong approval and image/identity/source/runtime/metadata/input/
candidate drift, closed malformed references/profiles, numeric precision, no public profile
export and private0600 files. Simulated cloud/provider paths are not live delivery evidence.
`ruff check` and `ruff format --check` on the two changed scripts and their two test files
pass; exact contract/ledger validator passes all ten requirements. Workflow diff changes only
provider admission selectors and the input description; database/Terraform jobs unchanged.
Mandatory staged/exact-head prechecks remain separate PR evidence.

#### Complete Operator Sequence (Single PR; Provider-Only)

**Actual baseline:** #585 merged asd8dce9c9; full deployment41823001424 completed.
Private provider-only status41829928432 passed, cleanup passed, and Terraform/verification/
publication were skipped. Exact registered BP release is
`sha256:401545767c9d2546731accbaa6949347a796ef7ff2c8eba402a47f7835dec126`;
registration configuration is
`sha256:630580cc2328798bab67e6fbbc1e5ab8938c7b13778794cf9ae22de175f65855`;
catalog is `sha256:4eae197a81784d04201b06af90ce329c898350d5691be5aeb5108e859579e599`.
Credential metadata READY, runtime matches registration, verification enabled; missing
groups AUTHORITY/POLICIES/ROLLBACK/TEMPLATES. Earlier tests and green CI with qualification
skipped are not an activation qualification receipt for this exact image.

1. **Obtain real inputs once, privately.** Use the accepted conversation/identity/provider
   owners and current evidence, not test fixtures. The closed assembly profile has exactly
   `authority`, `binding_digests`, `policies`, `templates`, `prerequisites`. No credentials,
   complete telephone numbers, raw app/WABA/sender identifiers or personal message bodies.
   The workflow dispatch document is **not a secret channel**. If approved template BODY
   text itself is confidential, do not put it in workflow inputs.

   | Group | Required fields and source |
   |---|---|
   | authority | `ActivationReference`, distinct `ExternalTrafficReference`, `ConsentReference`, `IncidentOwnerReference`, `AlertRouteReference`, `RollbackDigest`, `TenantId`, `RecipientBindingDigest`, `StartsAt`, `ExpiresAt`, `MaximumMessages`, `MaximumMessagesPerMinute`, `MaximumSpendInr`, `MaximumCostPerMessageInr`; optional explicit boolean `AllowProvisionalOnboarding`. Use actual independent decisions, Identity-owned pilot tenant, canonical consenting-contact digest, current incident/alert route and accepted compatible rollback tuple. Do not invent a tenant or reuse sender digest as contact consent. |
   | binding_digests | `AppBindingDigest`, `WabaBindingDigest`, `RecipientBindingDigest` from the exact protected environment binding under authorized access; the last is the sender Phone Number ID binding, not authority's contact digest. Never export raw protected binding/credential values. |
   | policies | Current accepted `PolicyVersion`, `InstitutionalPolicyVersion`, `InteractionPolicyVersion`, `ChannelRenderingPolicyVersion` from conversation owners. Empty runtime defaults are not accepted versions. |
   | templates | 1-16 actual approved BODY-only `{Name,Version,Locale,Category,Body}` records; Meta name/locale/category and approved body/version must match. No guessed `hello_world`, fabricated approval or fixture `demo_test`. |
   | prerequisites | Exactly `qualification`, `zero_traffic_deployment`, `provider_registration`, `credential_scope`, `consent`, `stop`, `alerts`, `rollback`, `pricing`, each `{reference,digest,expires_at}`. Digest the actual accepted receipt bytes, record its durable reference and honest validity; cover the entire pilot window. |

   Omit `schema`, `registration_configuration_digest`, and authority's
   `Environment/ReleaseDigest/ConfigurationDigest/CatalogDigest/Revoked`: assembly derives
   these from the current registered deployment, policies, bindings and templates. Keep the
   existing approved boundary: Founder's own recipient only, at most 30 minutes, **10 inbound
   plus outbound combined**, INR10, no other customer; rate and conservative cost/message
   within those limits. Provisional onboarding requires explicit permission and its isolated
   Identity-owned pilot scope. No marketing or business-initiation expansion.

   Verify each receipt's actual truth before submitting it: exact-image qualification,
   deployed no-traffic tuple, registration, pinned metadata validity, consent, real Stop/
   recovery evidence, delivered alert test/owner route, compatible rollback and current
   account/provider/model pricing. Shape/digest checks do not prove these external facts.
   Current full qualification, approved template inventory/policies, pilot identity/binding,
   accepted alert/rollback/pricing receipts have **not** been established by the status run.
   If missing, stop with the complete missing-input list; do not mint success receipts.

2. **Assemble without deploying.** After Founder merge, dispatch trusted `main`, environment
   `demo`, execution `plan`, image home `azure`, provider operation `assemble`, profile as
   `provider_document`, **blank** `provider_approved_digest`. Existing private control identity
   creates the candidate under
   `deployment-config/demo/whatsapp-operations/{run-id}-{attempt}/activation.bundle.json`
   with overwrite disabled. Existing deployment identity checks metadata/runtime/source and
   ETag-conditionally reads back identical candidate bytes. No registered-source, application,
   database, RBAC or firewall write occurs. Both normal application deployment and database
   reset are skipped. Redacted `evidence-apply.json` must PASS and report only
   `candidate.reference/digest/expires_at/approval_verified=false`, plus normal safe fields.
   Candidate JSON and input profile stay out of public artifacts.

   Example for an authorized operator with an already completed **non-secret** profile:

   ```sh
   gh workflow run deploy.yaml --ref main \
     -f environment=demo -f execution=plan -f image_home=azure \
     -f provider_operation=assemble -F provider_document=@/private/activation-profile.json
   ```

3. **Independent exact review.** Founder reviews the actual private candidate, accepted
   receipts, pilot limits, incident/alert route and rollback, then separately authorizes
   activation and external traffic for its exact published digest. Assembly, prior personal
   test consent, PR merge and a computed checksum are not this decision. The operator must
   not manufacture `provider_approved_digest` by hashing the candidate as self-authorization.
   If the window expires or evidence/configuration changes, reassemble under a new run,
   obtain the new digest decision and leave the old candidate unactivated. Storage is
   create-only for this tool, not claimed WORM; changed bytes always invalidate approval.

4. **Activate the same bytes.** Same trusted-main/demo/plan/azure inputs, operation `activate`,
   `provider_document={"candidate_reference":"<assembly-run-id>-<attempt>"}`, and exact
   `provider_approved_digest` from that independent decision. The existing private path
   conditionally downloads the candidate, preserves raw bytes, verifies the approved digest,
   recomputes registered tuple, checks window/receipts/limits/bindings/templates and pinned
   metadata, then applies existing runtime environment settings and retires stale workers.
   No full image deployment or database reset. Legacy inline bundles remain supported.
   Require apply PASS, expected traffic flags and exactly the intended ready worker.
   Failed rollout attempts existing fail-closed containment; if containment is unconfirmed,
   treat as an incident, not a successful activation.

5. **Prove the user's outcome.** Within the approved window, Founder sends fresh `Hi`;
   confirm signed provider ingress, canonical Identity/conversation admission, one correlated
   outbound delivery and Founder actually receiving the reply. Continue the conversation and
   check canonical continuity/authorized channel linkage without duplicate identities.
   Provider HTTP acknowledgement or an outbox row alone is not delivery. Keep bodies,
   telephone numbers and tokens out of retained evidence. Verify off-scope contact rejection,
   replay/idempotency and budget/window behavior under the accepted evidence plan. Stop
   immediately on failure, unexpected recipient, missing alert or budget risk.

6. **Stop and expiry.** Send conversational `STOP`; verify repeated STOP is idempotent and
   cannot restart dispatch. Independently dispatch existing operation `stop` with document
   `{}` and blank approval; require all business traffic/provider flags closed, revoked=true,
   authority settings removed and obsolete workers retired. STOP works without candidate or
   private configuration blob. Expiry gates deny work; no claim is made that expiry itself
   automatically clears environment variables. Re-enable only through a newly reviewed,
   independently approved unrevoked tuple; never replay a stale authority to roll back.
   Do not use a normal full deployment as the Stop procedure.

7. **Evidence and actual cost review.** Record run IDs, exact candidate/release/configuration,
   approval refs, sanitized ingress/delivery/continuity/Stop/alert outcomes, remaining budget
   and cleanup result. Reconcile Azure runner/application resource duration/usage, Meta
   delivered-message categories/account billing and actual model tokens/rates; distinguish
   pilot runtime spend from recurring resources, tax and coding-assistant fees. Estimates
   are not receipts. Call Demo **ready only after** accepted live exchange, continuity,
   Stop/recovery/alert evidence and costs; this PR or status PASS alone cannot claim it.

#### Private Runner Version Recovery (WC133-R011) - 2026-11-06

Founder authorizes the runner infrastructure repair, Docker validation and a new PR in the
current session. Provider-only status run
[42157701546](https://github.com/dlai-sd/waooaw-platform/actions/runs/42157701546)
queued after successful broker startup. Its exact Azure runner execution registered and
created a GitHub session, then reported
`Runner version v2.336.0 is deprecated and cannot receive messages.` The listener terminated
and Azure marked the execution Succeeded at 03:41:01 UTC; this process-level result was not
runner readiness. Normal cancellation completed `cleanup-private` successfully; no provider
operation, application deployment or database reset executed.

The authorized repair pins the official `actions/actions-runner` 2.338.2 OCI index
`sha256:759a1d94a15b05941aba5196974ff43fe15b4cbba29b694b35cbc32a1166b232`,
updates the existing real-container version assertion with fail-fast shell behavior, refreshes
the two affected bootstrap-manifest hashes, and wires its regression into
`quality:scripts`. Exact upstream container execution confirms version 2.338.2 and Ubuntu
24.04. The existing Azure CLI, extension and Terraform pins, private identities, command
entrypoint, ephemeral registration, disabled self-update and cleanup boundaries are preserved.
Validate the complete built runner toolchain and runner lifecycle/lease contracts; version
output alone does not prove GitHub job acceptance or Azure deployment compatibility.

Application builds/publication use GitHub-hosted runners and application base images are
unchanged. Private Azure deployment/qualification and provider-operation jobs depend on this
runner. Broker, cleanup and reconciler consumers share its blueprint image, so the replacement
must preserve their tools and scripts as well. UAT/Prod carry the old pin but their activation
and deployment authorities do not change.

Publication remains restricted to `ci.yaml` on merge to trusted main. This first PR upgrades
and qualifies the runner build; it does not fabricate a published digest or change the
environment pins to a local image ID. After merge and successful attested publication, use
the exact `goal006-runner-image-goal006-private-runner-<merge-sha>` manifest and verify its
source/digest attestation. Prepare the follow-up environment-pin PR using those actual bytes,
then perform separately authorized runner-infrastructure qualification and retry provider-only
status. A new runner must be online, accept the exact job and pass terminal cleanup before
claiming operational recovery. Do not retry the deprecated image, merge either PR yourself,
redeploy applications or reset databases as part of this repair.

Local validation: the original pin fails the new regression; the repaired dependency closure
passes 211 tests. The repaired private image builds and verifies runner 2.338.2, Azure CLI 2.79.0,
containerapp extension 1.2.0b5, log-analytics, Terraform 1.9.8, PostgreSQL client and required
broker/provisioner/handoff/qualification entrypoints. Terraform foundation init/validate and the
existing real Azurite lease/stale-probe workflow pass. A deliberately mismatched version fails
with exit 1 before subsequent commands. No live GitHub runner acceptance or Azure deployment
qualification was executed.
