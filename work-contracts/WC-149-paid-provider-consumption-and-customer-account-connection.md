# WC-149 - Paid Provider Consumption And Customer Account Connection

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-149 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-149 (replaces the earlier CI-health content of this number, which the Founder scrapped and parked) |
| Founder assignment | Current conversation: "scrap 149 ... and repurpose it to cover" paid-provider key consumption, Gemini and Anthropic adapters, the Sarvam key test and customer account connection (PG-16); "get these functionalities working for founder and customer - end to end. So dont tell me its demo so left for other pr, only api implemnted etc."; Founder approved the ADR-029 amendment for hosted models and will supply the Meta developer app |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at WC-148 (`6dcecc9e`) |
| Related contracts | WC-148 (provider registry and Founder screen); WC-147 (cloud workload credentials); WC-134 (governed conversation generation); ADR-021 (customer OAuth), ADR-029 (multi-provider strategy), ADR-042 (provider registry and tool gateway), ADR-046 (workload identity) |
| Requirement ledger | [WC-149-requirements.yaml](./WC-149-requirements.yaml) |
| Constitutional basis | C-023, C-042, C-059, C-063, C-083, C-084 |

## Problem And Evidence

A Founder can save a provider key (WC-148) but no running service uses it, and a customer cannot connect a marketing account. Evidence at the baseline:

- The AI runtime mounts only the governed conversation generation route. Its provider, `InstitutionalOllamaProvider`, raises `IMMUTABLE_MODEL_DISPATCH_UNAVAILABLE` on every call, no Ollama is deployed, and the Provider Selection Engine router that knows Sarvam is not mounted. `_dispatch_frontier` is a stub, so Gemini, Anthropic and OpenAI have no adapter.
- The AI runtime already has an ADR-046 mTLS identity towards Business Platform (resolve, reserve, settle), but no route to read a provider credential reference, and `GET /api/v1/providers` expects a user token.
- Sarvam is seeded without a test endpoint, so the Founder cannot confirm the key. Live probing showed `GET /v1/models` returns 200 for an invalid key, while `POST /v1/chat/completions` with an empty body returns 403 for an invalid key.
- No customer provider connection table, controller, screen or token custody exists. The Facebook and Instagram agent services are emulators that report PUBLISHED without calling Meta.

## Authority And Scope

### In scope

1. **Sarvam key test.** The Founder Test for Sarvam sends an empty-body `POST` to the chat completions endpoint with the `api-subscription-key` header. A 400 or 422 means the key authenticated; 401 or 403 means rejected; anything else is inconclusive and reported as such. The tester gains the method and header style as seeded settings, still SSRF-limited and secret-free in output.
2. **Hosted adapters.** The AI runtime gets one hosted-provider interface with adapters for Sarvam, OpenAI, Anthropic and Google Gemini. Each maps a bounded prompt to text and input and output token counts, reports the model name the provider returned, and never logs or returns the key.
3. **Key consumption.** The AI runtime resolves the active credential version for a provider through a new Business Platform internal route (`POST /internal/v1/provider-credentials/resolve`, ADR-046 route grant, AI runtime to Business Platform), then reads that pinned version from Key Vault with its own identity. A new or rolled-back version is used without a restart.
4. **Fallback.** A bounded ordered provider chain tries the next provider when one fails with a provider error, a timeout or a rejected key, and returns which provider answered and a sanitized reason for each skipped one.
5. **Founder end-to-end proof.** The Founder screen gets a "Test answer" action per saved provider. Business Platform (Founder only, fresh step-up) calls a new AI runtime internal route (`POST /internal/v1/provider-generations/probe`, ADR-046 route grant, Business Platform to AI runtime) with a fixed short prompt, a 64-token ceiling and no customer data. The AI runtime resolves the key as in item 3 and returns the real model answer, provider, model and token counts. This is a diagnostic and is not billed to a customer.
6. **Governed hosted binding.** An ADR-029 amendment defines a hosted-model binding as provider, pinned model identifier and tokenizer family, with the provider-reported model recorded as evidence on every call and rates set by the Founder. The governed generation binding admits MID and FRONTIER hosted adapters on an allowlist of provider hosts, and a governed provider for those adapters counts tokens conservatively, honours the permit authorize and settle steps, and uses the credential from item 3.
7. **Customer account connection (Meta).**
   - Schema: a tenant-isolated connection record with status (CONNECTED, NEEDS_REPAIR, REVOKED), provider account identity, granted scopes, expiry and secret reference, plus single-use OAuth state records. Row-level security applies.
   - Flow: the customer starts the authorization-code flow, Meta redirects to a same-origin web route, which forwards the code and state to Business Platform. Business Platform validates the state, exchanges the code for a long-lived token and stores the token only in Key Vault under a `customer-connection-` secret name. No endpoint, log or agent-visible object ever returns a token.
   - Repair and revoke: the customer can see status, reconnect when the token expired or was withdrawn, and revoke, which deletes the secret version and marks the record REVOKED.
   - Meta app: the Meta developer app id and secret are entered by the Founder on the provider screen under the `meta` provider; the secret value is JSON holding the app id and secret, and Test performs the app-token check.
8. **Real publish through a broker.** An approval-gated Business Platform route publishes one text post to the customer's connected Facebook Page through the Graph API. It fetches the token inside Business Platform at call time, requires an explicit customer approval in the request, and returns the provider post identifier. The agent and the model never receive the token. The customer screen offers "Publish an approved post" with the result.
9. **Customer screen and menu.** A customer page at `/connections` with a menu entry for customers, a same-origin proxy with a write limit, WAOOAW portal styling, accessibility and responsive behaviour like the Founder screens.
10. **Infrastructure.** Terraform for every environment: route grants in the workload registry, Business Platform may write and read secrets whose names begin `customer-connection-`, the AI runtime may read `provider-` secrets (already granted), settings for the Business Platform to AI runtime address and the Meta redirect address. The AI runtime becomes an ADR-046 cloud workload with a private mTLS listener (port 5444, one minimum replica) and Business Platform gains an inbound mTLS listener (port 5445) serving only `/internal/v1/*`, because neither could be reached by the other in the cloud before.
11. **Tests and gates.** New tests run in the release-qualification gate; the contract records what is proven and what only a real Meta session or Demo deployment can prove.

### Out of scope

- Publishing the per-relationship governed inference binding rows and their approval evidence that customer conversation replies need; those are approval artefacts under WC-134 and are not created by this contract. This contract delivers the adapters, binding admission and credential path they need.
- Instagram publishing and Meta Ads (the Facebook Page post is the first real publish); Meta app review for public customers (test users and app roles work in development mode).
- Changing the Facebook and Instagram emulator services in the digital marketing agent.
- Real provider keys and the Meta app, which the Founder supplies on the screen.
- Weight-based digests, Ollama deployment, plan-to-tier policy and customer billing of generation.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-149-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC149-R001 | The Sarvam test is an empty-body POST with the subscription-key header that treats 400 or 422 as authenticated, 401 or 403 as rejected and everything else as inconclusive, with no secret in any output |
| WC149-R002 | Sarvam, OpenAI, Anthropic and Gemini adapters share one bounded interface, return text, token counts and the provider-reported model, and never log or return the key |
| WC149-R003 | The AI runtime resolves the active credential version through an authorized Business Platform internal route and reads that pinned Key Vault version, so a new or rolled-back version is used without a restart |
| WC149-R004 | A bounded ordered fallback chain skips a failing provider and reports which provider answered and a sanitized reason for each skip |
| WC149-R005 | The Founder "Test answer" action reaches a real provider through Business Platform and the AI runtime under Founder-only fresh step-up and returns the answer, provider, model and token counts without customer data |
| WC149-R006 | The ADR-029 amendment defines the hosted binding and the governed generation binding and provider admit hosted MID and FRONTIER adapters on a host allowlist with conservative token counting and permit authorize and settle |
| WC149-R007 | The customer connection schema is tenant-isolated, the OAuth state is single-use, tokens exist only in Key Vault under `customer-connection-` names, and no endpoint, log or agent-visible object returns a token |
| WC149-R008 | A customer can connect, see status, reconnect after expiry or withdrawal, and revoke a Meta connection, and revoke deletes the secret version |
| WC149-R009 | An approval-gated broker publishes a Facebook Page post through the Graph API using a token fetched inside Business Platform at call time and returns the provider post identifier |
| WC149-R010 | The `/connections` customer screen and its menu entry follow WAOOAW portal styling and accessibility, and the Founder `meta` provider row stores the app id and secret with a working Test |
| WC149-R011 | Terraform and the workload registry grant exactly the new routes, secret prefix and addresses for demo, uat and prod and validate |
| WC149-R012 | New tests run in the release-qualification gate and the contract records what is proven by tests and what only a real Meta session or Demo deployment can prove |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Not provable before a Demo deployment with real keys: the Sarvam response to a valid key on an empty body, Key Vault role conditions for both prefixes, Business Platform and AI runtime managed-identity secret access, the AI runtime reaching provider hosts through the environment network, and Meta accepting the app, redirect address and test user.
