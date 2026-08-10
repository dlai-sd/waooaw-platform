# WC-034 F4 Relationship Workspace Compatibility Evidence Specification

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-005 - Solution Architect |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-005-09 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T14:33:15+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-005-05 |
| `acceptance_record` | ACC-GOAL-005-INST-005-05 |
| Date | 2026-08-10 |
| Gate contribution | G-F4-10 - canonical BP OpenAPI and generated-client compatibility evidence specification |
| Decision | SPECIFICATION CONTRIBUTION SATISFIED - the future executable evidence package is fully defined; no executable compatibility evidence is claimed |
| Authority boundary | Evidence specification only; no canonical OpenAPI edit, generator execution, generated client, source, test, migration, build artifact, implementation, provider activation, deployment, F5-F8 work, integrated review, self-review, or customer-proof authority |

Repository search found no prior use of `CR-GOAL-005-INST-005-09`. This record was produced after `ACC-GOAL-005-INST-005-05` at `2026-08-10T14:24:54+00:00` and within the accepted Order 5 participation window.

## 1. Purpose And Normative Language

This record defines the evidence that a future separately authorized implementation contribution must produce to demonstrate that the canonical Business Platform (BP) OpenAPI and generated TypeScript Relationship Workspace client conform to the approved F4 architecture package. It does not create or validate the future canonical contract and does not generate a client.

The words **MUST**, **MUST NOT**, **REQUIRED**, and **PROHIBITED** are normative. A future evidence result is valid only when every required input, command, output, version, hash, and provenance label is retained in a reviewable manifest. A static architecture assertion is never executable evidence.

The controlling compatibility boundary is:

- BP is the sole ordinary public Relationship Workspace facade and public relationship-governance projection owner.
- Web consumes only the generated BP public contract for F4. Emergency Stop remains separately governed and is not part of the F4 generated surface.
- WBE, PR, CE, professional/domain adapters, providers, and ledgers remain private.
- Server-derived tenant authority and separately authorized Employment Relationship binding apply to every operation.
- BP preserves source ownership, exact authoritative attention order, Evidence First, idempotency, expected-version conflict, and partial/unknown reconciliation semantics.

## 2. Future Canonical BP Public Inventory

The future canonical BP OpenAPI update MUST contain exactly the following F4 public operation IDs and path families. The inventory is additive to the existing BP contract; it does not remove or rename existing operations.

All F4 paths are rooted at `/api/v1/employment/relationships/{relationshipId}/workspace`.

| Operation ID | Method and path | Primary response schema family | Required public purpose |
|---|---|---|---|
| `getRelationshipWorkspace` | `GET /api/v1/employment/relationships/{relationshipId}/workspace` | `RelationshipWorkspaceV1` | Complete authorized relationship snapshot |
| `getRelationshipWorkspaceChanges` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/changes` | `RelationshipWorkspaceChangePageV1` | Cursor-bound incremental reconciliation |
| `getRelationshipPlan` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/plan` | `RelationshipPlanV1` | Plan, goals, Priority Work, dependencies, review points, and commands |
| `getRelationshipAttention` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/attention` | `RelationshipAttentionPageV1` | Complete qualifying attention list in exact BP order |
| `getRelationshipWork` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/work` | `RelationshipWorkPageV1` | Work, deliverables, decisions, schedules, effects, evidence, and commands |
| `getRelationshipResults` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/results` | `RelationshipResultsV1` | BP-composed business outcomes with domain provenance and attribution limits |
| `getRelationshipUsageBudget` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/usage-budget` | `RelationshipUsageBudgetV1` | WBE-authored actual, allowance, budget, forecast, threshold, and consequence relay |
| `getRelationshipRightsControls` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/rights-controls` | `RelationshipRightsControlsV1` | Scope, authority, lifecycle, rights, evidence access, and Stop reachability |
| `submitRelationshipCommand` | `POST /api/v1/employment/relationships/{relationshipId}/workspace/commands` | `RelationshipCommandReceiptV1` | Submit or replay one generated typed governance command |
| `getRelationshipCommand` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/commands/{commandId}` | `RelationshipCommandOutcomeV1` | Reconcile one pending, partial, or unknown command |
| `listRelationshipEvidence` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence` | `RelationshipEvidencePageV1` | List BP-authorized evidence summaries without ledger access |
| `getRelationshipEvidence` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence/{evidenceId}` | `RelationshipEvidenceDetailV1` | Read one permitted evidence projection and its limitations |
| `requestRelationshipEvidenceExport` | `POST /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports` | `RelationshipEvidenceExportReceiptV1` | Request or replay an assurance-controlled export |
| `getRelationshipEvidenceExport` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports/{exportId}` | `RelationshipEvidenceExportOutcomeV1` | Reconcile export preparation and authorized retrieval |

No other F4 public operation ID is permitted without a later approved architecture amendment. In particular, there is no generic action, callback, proxy, destination, service-routing, ranking, reordering, ledger, provider, or internal-owner operation.

## 3. Future Public Schema Inventory

The dependency closure for the operations in Section 2 MUST include these schema families. Concrete component factoring may add supporting schemas only when they preserve these names, meanings, and ownership boundaries and introduce no forbidden surface.

### 3.1 Workspace And Provenance

- `RelationshipWorkspaceV1`, `RelationshipWorkspaceChangePageV1`, `RelationshipWorkspaceSectionV1`, and `RelationshipContextV1`;
- `RelationshipCurrencyStateV1` representing `CURRENT`, `STALE`, `UNKNOWN`, `UNAVAILABLE`, and `BLOCKED` with source-owned validity and recovery meaning;
- snapshot state representing `CONSISTENT`, `PARTIAL`, `STALE`, and `UNKNOWN`;
- opaque relationship-bound cursor and change-entry schemas;
- source provenance carrying accountable owner, schema/contract version, source projection version, produced/observed/confirmed times, validity, freshness, binding, and correction lineage; and
- `GovernedRelationshipItemV1` with owner, state, effect, evidence status, item/source versions, relationship binding, available commands or no-action reason, currency, provenance, and limitation.

### 3.2 Plan, Attention, Work, And Results

- `RelationshipPlanV1`, `RelationshipGoalV1`, and Priority Work/dependency/review-point schemas;
- `RelationshipAttentionPageV1` and `RelationshipAttentionItemV1`, including opaque authoritative sequence but no public rank or score;
- `RelationshipWorkPageV1`, `RelationshipWorkItemV1`, `RelationshipDeliverableV1`, approval/decision, and schedule schemas;
- `RelationshipResultsV1`, `BusinessOutcomeResultV1`, and explicitly subordinate `TechnicalMetricV1`; and
- baseline, measure, review period, evidence support, attribution basis/limits, uncertainty, accountable domain source, dispute, and supersession schemas.

### 3.3 Usage, Budget, Rights, And Evidence

- `RelationshipUsageBudgetV1`, `UsageActualV1`, `AllowanceV1`, `BudgetCeilingV1`, `UsageForecastV1`, `UsageThresholdV1`, and `UsagePacingChoiceV1`;
- typed assumptions, validity, customer-language units, commercial consequences, and WBE provenance;
- `RelationshipRightsControlsV1`, `RelationshipScopeV1`, `RelationshipAuthorityV1`, and `RelationshipLifecycleV1`;
- approval rule, scope-boundary rule, assurance need, evidence access, export eligibility, and Emergency Stop reachability projections;
- `RelationshipEvidencePageV1`, `RelationshipEvidenceSummaryV1`, `RelationshipEvidenceDetailV1`, `RelationshipEvidenceExportReceiptV1`, and `RelationshipEvidenceExportOutcomeV1`; and
- evidence state support for `PENDING`, `RECORDED`, `FAILED`, `UNKNOWN`, `STALE`, `DISPUTED`, `SUPERSEDED`, and `UNAVAILABLE`, with `RECORDED` requiring authority-confirmed evidence provenance.

### 3.4 Commands, Outcomes, And Errors

- `SubmitRelationshipCommandRequestV1` as a generated discriminated union over every approved Plan, goal, approval, distinct scope-boundary, work, deliverable, schedule, lifecycle, authority, commercial, and result-dispute command kind in the solution contract;
- command-specific payload schemas with expected workspace, subject, scope, authority, lifecycle, assurance, evidence, WBE, and adapter versions where applicable;
- `RelationshipCommandReceiptV1`, `RelationshipCommandOutcomeV1`, and owner-step/reconciliation schemas supporting `COMPLETED`, `PENDING`, `PARTIAL`, `UNKNOWN`, `REJECTED`, `CONFLICT`, and `BLOCKED`;
- a reusable required `Idempotency-Key` header component on every public POST operation; and
- RFC 9457 `RelationshipWorkspaceProblemDetailV1` with `type`, `title`, `status`, stable `code`, `correlationId`, safe relationship reference when permitted, `reconciliationRequired`, and BP-only recovery/reconciliation links.

Free-form command names, `Record<string, unknown>`, arbitrary service destinations, generic action URLs, untyped payload maps, and open-ended callback fields fail compatibility.

## 4. Internal Contracts Excluded From The Public Specification

The dependency closure and generated public client MUST NOT contain paths, operation IDs, schemas, parameters, links, security schemes, examples, or server entries for these internal contracts.

| Private owner | Excluded contract family |
|---|---|
| WBE | `getRelationshipCommercialProjection`, `submitRelationshipCommercialCommand`, `getRelationshipCommercialCommand`; `WbeRelationshipCommercialProjectionV1`, commercial command/receipt/outcome types; wallet, bucket, meter, pricing, procurement, reconciliation, or billing-ledger surfaces |
| PR | `getRelationshipExecutionProjection`, `submitRelationshipExecutionControl`, `getRelationshipExecutionControl`; PR execution projection/control types; PR hosts, sessions, execution IDs, controls, or streams |
| Professional/domain adapter | `RelationshipOutcomeAdapterV1.GetProjection`, `.ValidateGoalChange`, and `.GetCommandOutcome`; adapter host, registry, service-routing, domain command, and provider-specific types |
| CE | Every gRPC RPC and message, including `ValidateAction`, `EvaluatePolicy`, `RecordEvidence`, authority-license operations, and `TriggerEmergencyStop`; CE hosts and constitutional metadata headers |
| Ledgers and evidence stores | Constitutional Audit Ledger, Customer Evidence Ledger, billing/usage ledger, wallet rows, object-store coordinates, raw evidence locators, and direct ledger query/mutation contracts |
| Providers and internal topology | Provider URLs, credentials, API keys, tokens, model/provider IDs, provider costs, internal DNS names, arbitrary URLs, callback destinations, and generic proxy/service selectors |

The existing dedicated Emergency Stop client is outside the F4 generation input. F4 may project Stop reachability but MUST NOT add a workspace Stop command, CE Stop RPC, PR Stop route, or replacement Stop transport.

## 5. Backward-Compatible BP OpenAPI Versioning

The canonical BP OpenAPI currently reports version `1.2.0`. F4 is an additive public operation and schema family. The future BP owner MUST select a backward-compatible semantic increment from `1.2.0`, expected to be the next minor release (`1.3.0`) when no unrelated compatible BP release has advanced the canonical version first.

If the canonical BP version has advanced before the authorized F4 edit, the owner MUST:

1. use the then-current canonical version as the baseline;
2. select the next available minor version for additive F4 operations and schemas;
3. preserve every existing public operation ID, path, required-field meaning, security requirement, and response semantic;
4. record the actual baseline and selected version in the evidence manifest; and
5. block the contribution if F4 requires a removal, rename, type change, required-field change, changed ordering meaning, weakened security, or other breaking behavior rather than silently using a minor increment.

Public F4 schema families begin at semantic schema version `1.0`. Optional additive fields may advance a supported minor. Removing, renaming, retyping, changing required state semantics, weakening provenance, changing command meaning, or changing authoritative ordering interpretation requires a new schema major with explicit coexistence and migration rules. Unknown public or owner major versions fail closed for dependent behavior.

## 6. Dependency-Closed OpenAPI Validation

The future evidence run MUST use a clean dependency-closed copy derived from the canonical BP OpenAPI at the exact reviewed commit. It MUST preserve all dependencies needed by the Section 2 operations while excluding unrelated operations from generated F4 inventory reporting. Bundling, filtering, or extraction MUST be reproducible and MUST NOT rewrite contract meaning.

The validation report MUST prove all of the following with zero errors:

1. **Parse:** the canonical document and dependency-closed generation input parse as the declared OpenAPI version using a standards-aware parser.
2. **Reference closure:** every local or approved external `$ref` resolves; there are no dangling, cyclicly unresolvable, case-mismatched, or environment-dependent references.
3. **Unique operation IDs:** every operation ID is globally unique in the canonical BP document and the fourteen Section 2 IDs appear exactly once.
4. **Inventory equality:** generated F4 operation inventory equals Section 2 with no missing or additional F4 operation.
5. **Security:** every F4 operation inherits or declares the approved customer BP security scheme; no anonymous alternative, API-key alternative, browser-to-internal credential, or weakened override exists.
6. **Tenant authority:** `tenantId`, `tenant_id`, or an equivalent customer-selectable tenant authority is absent from public paths, queries, headers, cookies, and request bodies.
7. **Relationship binding:** `relationshipId` is required where specified, remains opaque, and never substitutes for authenticated authorization.
8. **Idempotency:** every F4 POST requires the shared `Idempotency-Key` header; request and outcome schemas preserve command identity, replay, expected versions, request-hash conflict, and reconciliation semantics.
9. **RFC 9457:** every documented F4 error response references `RelationshipWorkspaceProblemDetailV1`; required stable codes cover invalid, session-required, assurance-required, inaccessible, state conflict, idempotency conflict, unresolved, expired, not allowed, stopped, owner dependency failed, rate-limited, projection unavailable, owner unavailable, CE unavailable, and unsupported schema outcomes.
10. **Discriminators:** command unions and polymorphic outcomes generate deterministically with complete discriminator mappings and no untyped fallback.
11. **Read semantics:** aggregate and family reads retain currency, provenance, authoritative ordering, partial composition, correction, and source-version meanings.
12. **No manual semantic rewrite:** the generation input is mechanically derived from the reviewed canonical document and its derivation hash is recorded.

Warnings MUST be classified and retained. A warning that can affect serialization, discriminator mapping, requiredness, security, operation inventory, idempotency, errors, ordering, provenance, or generated compile behavior is blocking; it cannot be waived as cosmetic.

## 7. Pinned Generator Selection Rule

The future evidence run MUST use the repository-approved OpenAPI Generator pin, not `latest`, a floating container tag, an unversioned global install, or a developer-local binary. At the time of this specification the approved baseline used by the preceding generated-client contract is OpenAPI Generator `7.17.0`.

Selection follows this deterministic rule:

1. Resolve the exact generator version from the repository's authoritative dependency lock or approved generation configuration at the reviewed commit.
2. If that pin remains `7.17.0`, use `7.17.0` exactly.
3. If an approved repository change has advanced the pin, use the single exact replacement version and cite the approving record and compatibility evidence.
4. If authoritative files disagree, the pin is absent, the image/package is mutable, or the binary cannot report the exact expected version, stop with `BLOCKED`; do not choose a version locally.
5. Record generator name, exact semantic version, distribution coordinate, immutable package checksum or container digest, template set/version, generator target, complete options, runtime version, locale, timezone, and invocation in the manifest.

A generator upgrade and the F4 contract change MUST NOT be combined unless a later authorization explicitly includes both and provides isolated before/after compatibility evidence.

## 8. Clean Two-Run Deterministic Generation

The future generation evidence MUST perform two independent clean runs from the same reviewed input and pinned toolchain.

For each run:

1. start from a newly created empty output directory outside tracked production client paths;
2. use identical dependency-closed input bytes, generator digest, templates, options, runtime, locale, timezone, and environment allowlist;
3. prohibit network-fetched templates or dependencies during generation unless their immutable digests are part of the approved input manifest;
4. retain raw generator stdout, stderr, exit code, and generated file inventory;
5. remove only an approved explicit list of nondeterministic metadata fields such as generation timestamps; do not normalize source semantics, identifiers, ordering, or content;
6. normalize path separators to `/`, file modes to the approved portable mode set, line endings to LF, and manifest ordering by bytewise relative path;
7. compute a SHA-256 for every normalized generated file; and
8. compute a tree SHA-256 over ordered records of `relative-path`, file length, and file SHA-256.

The evidence package MUST contain both per-file manifests and both tree hashes. Compatibility passes only when:

- the relative file inventories are identical;
- every normalized per-file hash is identical;
- the normalized tree hashes are identical; and
- any raw difference is fully attributable to a pre-approved removed metadata field and is shown in the normalization report.

Deletion, patching, formatting, import repair, model editing, or post-generation semantic rewriting before hash comparison is prohibited.

## 9. Strict TypeScript Compile And Generated Inventory

Each clean generated tree MUST compile in the repository-approved web TypeScript environment with strict mode enabled and with generated-code errors unsuppressed. The evidence MUST record the exact compiler version, configuration path and hash, command, exit code, diagnostics, and source-file set.

Compatibility requires:

- zero TypeScript errors;
- no `skipLibCheck`, `noCheck`, blanket exclusion, `@ts-ignore`, `@ts-nocheck`, generated-directory diagnostic suppression, or weakening of strict options introduced for the run;
- no unresolved import, duplicate symbol, discriminator mismatch, impossible required field, or unsafe untyped command payload;
- all fourteen Section 2 operations present in the generated `RelationshipWorkspaceApi` inventory; and
- every Section 3 schema family represented by generated model/type inventory or by an explicitly documented generated inline type with stable deterministic naming.

The evidence manifest MUST list each generated operation with method name, HTTP method, path, request type, response type, security requirement, idempotency requirement, and error type. It MUST list every generated model/type, discriminator, enum, required property set, and source OpenAPI component. Inventory diffs against the normative Sections 2 and 3 are blocking.

## 10. No-Manual-Patch Proof

The future evidence MUST prove that the compile and inventory results came directly from the pinned generator:

1. generated outputs are produced only in the two clean empty directories;
2. the normalized hash manifest is captured immediately after each generator exits;
3. strict TypeScript compile and scans run against those exact hashed bytes;
4. a clean rerun reproduces the same bytes without copying from another output;
5. no patch, formatter, codemod, import fixer, text replacement, editor save, generated-file allowlist mutation, or handwritten shim runs between generation, hashing, compile, and scan; and
6. the evidence manifest records the ordered process steps and asserts that generated tracked production paths were not modified by the evidence-only run.

Any manual or automated post-generation source change fails the proof, even if compilation then passes. The remedy is to correct the approved canonical OpenAPI, approved templates, or pinned configuration under proper authority and repeat both clean runs.

## 11. Forbidden-Surface Scans

Scans MUST inspect the dependency-closed OpenAPI input, generated source, generated documentation, generated configuration, operation/model inventory, server wrapper types if in authorized scope, and emitted string literals. Matching is case-insensitive where identifiers permit and includes common separators and casing variants.

| Forbidden family | Minimum prohibited evidence |
|---|---|
| PR | PR base URLs, internal PR paths, sessions, execution controls/IDs, streams, service credentials, or ordinary browser-to-PR operations |
| WBE | WBE URLs; wallet, bucket, meter, pricing, procurement, reconciliation, customer/billing IDs, raw commercial rows, ledger locators, or operational controls |
| CE | CE hosts, gRPC-web, CE RPCs/messages, constitutional metadata headers, authority-license internals, or audit operations |
| Ledgers | Constitutional Audit Ledger, Customer Evidence Ledger, billing/usage ledgers, raw evidence queries, database/object-store coordinates, or reusable private locators |
| Providers and internals | Provider/model URLs, IDs, API keys, tokens, costs, credentials, internal DNS, private ports, callback URLs, generic proxies, arbitrary destinations, service names, or command routing fields |
| Tenant authority | `tenantId`, `tenant_id`, tenant query/path/body fields, browser-selected tenant headers, or any generated parameter that could establish tenant authority |
| Ordering authority | rank, score, weight, priority score, reorder, drag-order persistence, sort/order/filter query, personalization, local urgency, secondary sort, or cross-relationship aggregate operations |
| Arbitrary command routing | free-form command/action name, service selector, endpoint field, route field, destination URL, callback URL, generic payload map, or command union fallback |

The scan rule set, exact patterns, exclusions, file inventory, raw findings, and adjudication MUST be versioned in the evidence manifest. An exclusion is permitted only for an approved customer-language field whose semantics cannot route, rank, authorize, or disclose an internal boundary. Every exclusion requires a cited schema property and human-reviewable reason. A forbidden operation, parameter, credential, route, or authority field has no waiver path under this specification.

## 12. Fixture And Contract Outcome Matrix

Future fixture/contract evidence MUST exercise at least the following matrix against the canonical contract and exact generated client. Fixtures are deterministic, relationship-bound, provenance-labelled, and free of real customer data. Each row records request, response, generated serialization/deserialization, authoritative source versions, expected public state, prohibited claim, and reconciliation action.

| Outcome family | Minimum fixture or contract case | Required observable result | Must not occur |
|---|---|---|---|
| Success | Current authorized aggregate read and one completed typed command with all required owner and CE confirmations | Typed `RelationshipWorkspaceV1` or `COMPLETED`; exact source versions; required evidence is `RECORDED`; authoritative links are BP-only | Transport acceptance, PR completion, or pending evidence shown as success |
| Conflict | Stale workspace/subject/owner version and same idempotency key with a different canonical request hash | `409` RFC 9457 with `RELATIONSHIP_STATE_CONFLICT` or `RELATIONSHIP_IDEMPOTENCY_CONFLICT`; fresh BP reconciliation reference; zero new owner mutation | Blind overwrite, new semantic mutation, leaked owner state |
| Stale | Expired WBE, domain, evidence, or BP projection with previously valid values | Section remains `STALE`, last confirmation and prohibited use are explicit; dependent command unavailable | Prior value presented as current or used to authorize action |
| Unavailable | WBE, PR, domain adapter, evidence reader, or owner contract unavailable while independent BP truth remains readable | Affected family is `UNAVAILABLE`; aggregate may be `PARTIAL`; unaffected sections remain truthful; owner-safe recovery is explicit | Whole-workspace fabricated failure, cached substitution, private fallback call |
| Blocked | Missing assurance, unresolved Founder policy, absent owner contract, active Stop, or unavailable required authority | `BLOCKED` section/command or appropriate RFC 9457 response; exact safe business consequence; zero governed mutation | Hidden right, invented default, optimistic command availability |
| Partial | One required owner authoritatively commits and another remains unresolved | `PARTIAL` command outcome with committed and unresolved owner steps, frozen incompatible commands, and accountable reconciliation | Generic success, automatic rollback, prior evidence deletion |
| Unknown | Transport loss after possible owner commit or indeterminate evidence outcome | `UNKNOWN` and **Success not confirmed** semantics; reconcile existing command ID before any new mutation | Failure assumed, success assumed, duplicate semantic command |
| CE unavailable | Governed write attempted while CE is unavailable; unaffected read also exercised | Write returns `503` with `CONSTITUTIONAL_ENGINE_UNAVAILABLE`; no governed success; read carries accurate constitutional/evidence currency; Stop remains independent | Bypass, degraded governed write, fabricated recorded evidence, delayed Stop |
| Unsupported version | Unknown public schema major, internal owner major, or DMA adapter major | Dependent family is `UNAVAILABLE` or command `BLOCKED`; `503 RELATIONSHIP_SCHEMA_UNSUPPORTED` where request-level failure applies; unaffected compatible sections remain truthful | Best-effort coercion, field-by-field cross-major merge, fallback to technical metric |

The matrix MUST cover aggregate read, at least one family read, typed command submission, command reconciliation, evidence read, and evidence export where the outcome applies. It MUST include privacy-safe inaccessible/cross-relationship variants and prove no protected existence, tenant, role, owner, or internal topology disclosure.

## 13. F4 Acceptance Mapping

All seven F4 acceptance IDs MUST trace to static contract assertions, generated operation/model inventory, applicable fixture rows, and later executable scenarios. A missing cell fails the future package.

| Acceptance ID | Required generated-contract evidence | Required fixture/contract evidence | Later evidence not supplied here |
|---|---|---|---|
| UX-CONV-06 | Governed item, Plan, goal, Work, deliverable, approval/decision, Results, owner/state/effect/evidence, and typed command models are complete | Every selected item type covers current, pending, stale, unknown, disputed, superseded, and unavailable command states without technical metrics becoming business effects | Browser keyboard/pointer behavior and live owner integration |
| UX-CONV-07 | Every path, cursor, item, command, outcome, export, idempotency binding, and source version is relationship-bound; no public tenant authority exists | Two relationships and unauthorized cross-tenant/cross-relationship substitutions show complete context replacement, privacy-safe denial, and zero carry-over | Browser switching, cache/history inspection, and live authorization integration |
| UX-CONV-08 | `RelationshipAttentionPageV1` preserves exact array order and opaque stable sequence; no ranking/sort/filter/reorder surface exists | Full, paged, cursor, refresh, and reconnect fixtures preserve exact order and stable ties | Desktop/mobile browser presentation across supported environments |
| CCT-UX-BOUNDARY-01 | `CONFIRM_SCOPE_BOUNDARY` is a distinct discriminated-union variant with expected versions, assurance, typed acknowledgement, CE evidence outcome, and dedicated errors | Ordinary approval cannot satisfy scope confirmation; stale boundary/assurance/version produces zero confirmation and no reusable acknowledgement | Live BP-CE evidence integration and browser step-up flow |
| CCT-UX-RIGHTS-01 | Rights, scope, authority, lifecycle, evidence access/export, approval/boundary distinction, and Stop reachability remain independently typed | Every included lifecycle and degraded-owner state retains mandatory rights/control families and honest unavailable alternatives | Browser reachability/accessibility and live Stop independence |
| CCT-UX-EF-01 | Evidence states and command outcomes distinguish pending from recorded and preserve dispute/supersession lineage | Pending-to-recorded, pending-to-unavailable, recorded-to-disputed, recorded-to-superseded, delayed CE, partial, and unknown cases show zero fabricated success | Live CE/evidence integration and executable Evidence First tests |
| UX-SHELL-06 | Mandatory view schemas, unavailable/blocked states, RFC 9457 errors, and BP-only recovery links exist with no internal/private surface | Each owner/source/version class is removed or invalidated in turn; no private route, stale-as-current value, mock result, fallback calculation, or fabricated command appears | Browser honest-state presentation and deployment/customer evidence |

## 14. Evidence Provenance Labels

Every future evidence item MUST carry exactly one primary provenance label and may link to stronger later evidence without changing its own label.

| Label | What it proves | What it does not prove |
|---|---|---|
| `STATIC_SPEC` | OpenAPI text, reference closure, operation/schema inventory, security/idempotency/error declarations, and static forbidden-surface assertions at a named commit | Generated compilation, runtime behavior, integration, browser behavior, deployment, or customer outcome |
| `GENERATED_COMPILE` | Pinned deterministic generation, normalized hashes, generated inventory, no-manual-patch chain, and strict TypeScript compile for exact input bytes | Service behavior, owner interaction, browser behavior, deployment, or customer outcome |
| `FIXTURE_BEHAVIOR` | Deterministic fixture/contract serialization and expected outcome semantics for named cases | Live service integration, browser behavior, deployed operation, or customer outcome |
| `LIVE_INTEGRATION` | Executed interaction among named live BP and internal owner test instances with retained environment/version evidence | Browser acceptance, deployment to a release environment, production operation, or customer outcome |
| `BROWSER` | Executed supported-browser behavior, accessibility, isolation, presentation order, privacy, and interaction against a named backend provenance | Production deployment, provider activation, or customer outcome unless separately proven |
| `DEPLOYMENT` | A named authorized environment received and passed the approved release/deployment verification | Customer activation, customer use, business result, attribution, or customer proof |
| `CUSTOMER_PROOF` | Authorized real-customer use and outcome evidence with customer, period, attribution, consent, and evidence provenance | Broader deployment, general efficacy, or claims beyond the evidenced customer and scope |

Static, generated, fixture, live integration, browser, deployment, and customer-proof records MUST be reported separately. A higher-level report may aggregate them only by retaining each original label, exact commit/input, environment, time, tool/version, actor, and limitation. Simulation, repository tests, generated compilation, provider capability, Activation Gate status, or deployment must never be relabelled as customer proof.

## 15. Future Evidence Manifest And Pass Rule

The future G-F4-10 executable evidence manifest MUST include:

- canonical BP OpenAPI path, commit, byte hash, declared baseline version, and selected backward-compatible version;
- dependency-closed input path, derivation procedure, byte hash, and complete resolved-reference inventory;
- parser/validator names, exact versions/digests, commands, outputs, warnings, and exit codes;
- generator selection evidence from Section 7 and both clean-run environments;
- both raw and normalized generated inventories, per-file SHA-256 manifests, tree hashes, and normalization report;
- strict TypeScript compiler version/configuration/hash, command, diagnostics, and exit code for both runs;
- generated operation, model, discriminator, enum, required-property, security, idempotency, and RFC 9457 inventories;
- no-manual-patch ordered process proof;
- forbidden-surface rule set, findings, exclusions, and zero-unwaived-result statement;
- every fixture/contract matrix case with source versions and primary provenance label;
- all seven acceptance mappings; and
- explicit statements of which live integration, browser, deployment, and customer-proof evidence remain absent.

Executable compatibility passes only when every mandatory Section 6-13 check passes with no blocking warning, inventory difference, hash difference, compile error, manual patch, forbidden surface, missing fixture row, or acceptance gap. Partial pass is not G-F4-10 executable closure.

## 16. Gate Decision And Preserved Open Gates

**G-F4-10 contribution under Amendment 3 Order 5 is SATISFIED AS AN EVIDENCE SPECIFICATION ONLY by `CR-GOAL-005-INST-005-09`.** This record defines the complete future canonical OpenAPI, generated-client, deterministic-generation, compile, scan, fixture, acceptance, and provenance evidence contract required by `GOA-GOAL-005-INST-005-05`.

The executable G-F4-10 compatibility result remains **OPEN/BLOCKED** until a later separately authorized implementation contribution edits the canonical BP OpenAPI and produces the complete passing evidence manifest in Section 15. This record supplies no canonical contract bytes, generated client, generator execution, compile result, hash, fixture execution, live integration, browser, deployment, or customer-proof evidence.

| Gate | State after this record |
|---|---|
| G-F4-10 - compatibility evidence specification contribution | SATISFIED AS SPECIFICATION ONLY; executable compatibility closure remains OPEN/BLOCKED for future implementation evidence |
| G-F4-11 - independent constitutional and integrated technical review | OPEN/BLOCKED - requires fresh C-065-compliant INST-002 and INST-004 contexts after Orders 1-5; INST-005 does not self-review |
| G-F4-12 - implementation authorization and evidence | OPEN/BLOCKED - requires a later Execution Plan amendment, CA readiness, Registrant acknowledgement, GOA issuance, and INST-010 acceptance |
| G-F4-13 - deployment authorization | OPEN/BLOCKED - requires separate release/deployment authority and evidence |
| F5-F8 | EXCLUDED |

Architecture/specification completion is not implementation authority. No downstream office may treat this record as executable proof, implementation readiness, deployment approval, provider activation, production operation, or customer proof.

## 17. Controlling Inputs

- `goals/GOAL-005-execution-plan.md` - Amendment 3, `GOA-GOAL-005-INST-005-05`, and `ACC-GOAL-005-INST-005-05`
- `architecture/reference/components/relationship-workspace.md` - `CR-GOAL-005-INST-004-08`
- `architecture/reference/components/relationship-workspace-solution-contract.md` - `CR-GOAL-005-INST-005-05`
- `architecture/reference/components/relationship-workspace-bp-owner-contract.md` - `CR-GOAL-005-INST-005-06`
- `architecture/reference/billing/relationship-workspace-wbe-owner-contract.md` - `CR-GOAL-005-INST-005-07`
- `architecture/reference/components/relationship-workspace-dma-adapter-conformance.md` - `CR-GOAL-005-INST-005-08`
- `architecture/reference/data/relationship-workspace-data-contract.md` - `CR-GOAL-005-INST-006-04`
- `architecture/reference/security/relationship-workspace-security-contract.md` - `CR-GOAL-005-INST-007-05`
- `architecture/reference/product/f4-relationship-workspace-release-contract.md` - `CR-GOAL-005-INST-011-05`
- `goals/GOAL-005-f4-dma-domain-authority-input.md` - `CR-GOAL-005-INST-011-06`
- `goals/GOAL-005-f4-dma-business-validation.md` - `CR-GOAL-005-INST-003-05`
- ADR-001, ADR-002, ADR-003, ADR-017, ADR-031, ADR-034, and ADR-035