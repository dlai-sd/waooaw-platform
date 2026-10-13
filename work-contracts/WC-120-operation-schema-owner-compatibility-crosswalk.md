# WC-120 Operation, Schema, Store, And Owner Compatibility Crosswalk

## Control

| Field | Value |
|---|---|
| Owner | Chief Solution Architect, INST-005 |
| Purpose | Close WC120-R007/R029/R036/R037/R039 and PR #499 findings without creating a parallel owner |
| Source precedence | Founder-accepted ADR-051/052/053 and PR #498; existing Conversation Core/BP and WC-114/WC-115 owner contracts; repaired PR #499 candidate only where compatible |
| Existing Core | `conversation-core.md` blob `1004255bbd01e3d10dd53a64a2b115ac059ad631` |
| Existing BP API | `business-platform.openapi.yaml` blob `406153fec469a5bf6b5919000110a6af1dfa6a46` |
| WC-114/WC-115 | blobs `11ba639efa43d3288ba1eb39fd2e05308c42e6c0` / `337fcef0a51a4c2ef2ff72423a7afc64969d8914` |
| Employment BP API/profile | blobs `bf7d3466c4113049f9f61200583811a25e454951` / `9c7ccecd64791010f1ba15b69d9b8a128d466d66` |
| Repaired candidate | `channel-neutral-conversation-business-platform.openapi.yaml` `1.0.0-candidate.2` |

“Compatible successor” below means the same BP owner, canonical store, identity, authorization,
idempotency record, and generated-client boundary. It never means another implementation or store.
Where the existing operation is complete, it remains the implementation target and the candidate is
an additive contract view. A conflict stops; an implementer does not choose between operations.

## Operation Compatibility

| Candidate operation | Controlling existing surface | Disposition | Owner/store and compatibility predicate | Generated-client owner |
|---|---|---|---|---|
| `getCanonicalConversation` | Core `GET .../conversation/messages` | Compatible aggregate view | BP reads the same canonical message timeline, sequence and authoritative cursor; no candidate store | BP API generator; Web uses generated BP client |
| `streamCanonicalConversationEvents` | Core `GET .../conversation/stream` | Compatible naming view | BP SSE only; `Last-Event-ID`/reconciliation rules remain controlling; no durable read mutation | BP API generator |
| `updateConversationReadPosition` | Core `PUT .../conversation/read-position` | Reused compatible successor | BP participant read-position row; monotonic visible-message advance, backward/unseen denial, identical replay | BP API generator |
| `submitConversationContribution` | Core `POST .../conversation/messages`; accepted WC-062 voice boundary | Additive typed facade | BP creates/replays one canonical contribution; exactly-one text or accepted reviewed-voice reference; PR is not called before durable BP acceptance | BP API generator; private voice client remains service-owned |
| `submitConversationCommand` | WC-114 `submitEmploymentCommand` at `.../workspace/employment/commands` | Delegating alias, not a new command owner | Request is exactly external `EmploymentCommandRequestV1`; BP writes the existing command/idempotency records and routes to existing owners | Employment BP API generator owns request types; candidate client references them |
| `getConversationOperation` | Core retry/reconciliation; WC-114 `getEmploymentCommand` | Additive aggregate reconciliation | BP reads existing operation/command outcome; unresolved is not success and never permits blind retry | BP API generator |
| `requestConversationCancellation` | Core `DELETE .../conversation/executions/{executionId}` | Compatible additive request | BP preserves history and sends the existing PR cancellation command; never releases Stop | BP API generator; BP-owned PR client is private |
| `listAvailableInteractionContexts` | ADR-052 server context; WC-114 workspace `availableCommands` | Additive discovery view | BP resolves contexts and command descriptors from existing owner projections; descriptors name `submitEmploymentCommand` and its closed schema | BP API generator; command schemas remain employment-client-owned |
| `getConversationContextProfile` | WC-115 accepted data/AIR profile | Additive projection | BP reads reproducible relationship projection; sources remain owner records and erasable payload boundary | BP API generator |
| `correctConversationContextProfile` | WC-115 append-only owner facts and correction controls | Additive command | BP records CAS-guarded correction intent; accountable source owner validates; no overwrite or candidate store | BP API generator; owner clients private |
| `prepareConversationHandoff` | ADR-052 channel binding | Additive channel-state operation | BP handoff record references one canonical conversation and preserves source binding | BP API generator |
| `activateConversationHandoff` | ADR-052 fresh target authentication | Additive channel-state operation | BP mutates only existing channel binding after fresh assurance; relationship/conversation identity unchanged | BP API generator |
| `revertConversationHandoff` | ADR-052 source-preserving revert | Required additive closure | BP idempotently returns PREPARED/UNKNOWN handoff to the recorded source binding; no new authority; divergent replay conflicts | BP API generator |
| `getConversationMessageStates` | Core independent message state projection | Compatible additive view | BP reads existing delivery/execution/customer-decision/evidence facts; state dimensions are never collapsed | BP API generator |
| `requestConversationDataRight` | WC-115 data profile and owner records | Additive orchestration only | BP accepts/reconciles a request; Data/Legal owners decide holds, erasure and evidence; no direct deletion authority | BP API generator; owner-specific clients private |
| `verifyWhatsAppWebhook` / `acceptWhatsAppWebhook` | ADR-053 BP adapter boundary | Additive provider ingress | Environment-isolated BP adapter; GET challenge bounded; POST `application/json` authenticated over exact raw bytes before parse, then atomic claim | Server stub/configurator only; never browser client |

The candidate contains 16 path entries and 17 operations because the webhook path has GET and POST.
This inventory is exhaustive for `1.0.0-candidate.2`.

## Schema And Store Compatibility

| Candidate schema family | Controlling schema/profile | Owner/store predicate | Compatibility result |
|---|---|---|---|
| Canonical conversation/message/state | Core `ConversationMessageV1`, timeline, stream, idempotency | BP canonical conversation/message/outbox/inbox records only; sequence and state dimensions preserved | Compatible additive projection |
| Durable read position | Existing `UpdateConversationReadPositionRequestV1` / `ConversationReadPositionV1` | BP participant read-position record; no SSE cursor substitution | Reused |
| Contribution union | Core text plus accepted WC-062 reviewed voice reference | BP canonical append; union has exactly one non-null discriminator-matched payload and rejects the other | Repaired, compatible |
| Interaction context/policy/source versions | ADR-052 and WC-115 accepted AI/freshness profiles | BP resolves policy/context; AIR consumes bounded references; channel/client cannot select policy/model | Compatible additive |
| Registered command descriptor/request | WC-114 `AvailableCommandV1` and closed `EmploymentCommandRequestV1` nine-variant union | WC-114 owners and command stores remain authoritative; no free-form type/map | Repaired by direct owner reference |
| Operation receipts/outcomes | Core idempotency/reconciliation and WC-114 owner outcomes | BP outcome/idempotency records; independent states and `UNAVAILABLE` retained | Compatible aggregate |
| Context profile/correction | WC-115 `data_profile` and `ai_profile` | BP projection from owner facts; append-only corrections, lineage, expiry, erasure propagation | Compatible additive |
| Handoff prepare/activate/revert | ADR-052 channel binding | BP channel-binding records only; source binding survives failure; revert is idempotent | Repaired, additive |
| Data-right request | WC-115 retention/erasure/hold profile | BP orchestration receipt; owner records remain with Data/Legal-governed systems | Compatible additive |
| WhatsApp callback | ADR-053 and WC-120 security profile | Environment BP claim/inbox plus erasable exact-byte payload; no separate conversation store | Repaired, additive |

## Owner And Generated-Client Rules

1. BP is the only public API and canonical conversation, sequence, unread/read-position,
   idempotency, reconciliation, context projection, and channel-binding owner.
2. PR owns execution, cancellation realization, and Emergency Stop. Ordinary public/generated
   clients never call PR. The dedicated accepted Stop routes remain unchanged.
3. AIR owns bounded provider-neutral reasoning; only private BP/PR/AIR generated clients cross that
   boundary. Browser/provider clients cannot select a model, prompt, policy, or tool.
4. WC-114 employment command types are generated from
   `conversational-employment-business-platform.openapi.yaml`; the candidate references that closed
   union and does not regenerate a divergent copy.
5. The WhatsApp callback generates server/configurator surfaces only. It is excluded from Web,
   Mobile, and customer SDKs.
6. Specialist profiles remain controlling: `data_profile`, `security_profile`,
   `freshness_profile`, `emergency_stop_profile`, `ai_profile`, Product matrix, and WC-120 Platform
   targets. Candidate generation cannot weaken them.

## Stop And Evidence Predicates

Stop `READY_FOR_STRATEGIC_PLAN` if an implementation introduces a second store/owner, directly uses
an alias and its controlling operation as separate mutations, copies the employment command union
inconsistently, generates provider callback methods into a public client, or cannot prove one
idempotency identity and outcome across a compatible view.

Implementation-phase contract fixtures must prove all operation dispositions above, both generated
client builds, external command-schema resolution, no browser/private-owner coupling, exactly-one
contribution validation, durable read-position semantics, command discovery, source-preserving
handoff revert, raw-byte webhook authentication, and zero duplicate owner/store mutation. No such
implementation evidence is claimed by this specification crosswalk.
