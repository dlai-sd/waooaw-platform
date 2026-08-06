# Work Contract 039 — Trust Layer Sprint 3: Constitutional Tool Gateway Library + AIR Refactor

**Office:** Platform IT Expert (INST-010)  
**Sprint:** WC-039  
**Backlog Item:** IB-010 — Trust Layer & Open Platform Integration (pending Founder ratification)  
**Sprint Track:** Track DIFFERENTIAL (AIR refactor) + Track GREENFIELD (CTG library)  
**Gate:** G5 CLEAR  
**Reviewer:** Enterprise Architect (INST-004)  
**Constitutional Basis:** C-031 (ADR-042 — satisfied), C-041 (every tool call governed by Decision Space — CTG is the structural enforcer), C-059 (Traceability — CTG writes evidence record for every external call)  
**Authorization:** Founder must authorize — *"Authorize WC-039"*

**Depends on:** WC-037 DONE (Audit Sink exists), WC-038 DONE (oauth-vault + Provider Registry exist)  
**Blocks:** All agent external-call work (DMA, etc.) — no external calls before CTG exists  
**Breaking change:** AIR's direct LLM SDK calls are replaced — as declared in ADR-042 §3  
**Service scope:** new `src/trust-layer/ctg/` (Python library), AI Runtime Python (`src/ai-runtime/`)

---

## Sprint Goal

Produce the Constitutional Tool Gateway as a Python package importable by Professional Runtime and AI Runtime. Refactor AI Runtime's PSE router to route all LLM provider calls through CTG instead of calling LLM SDKs directly.

After this sprint:
- Every external call (LLM + OAuth-protected API) goes through: CE.ValidateAction → oauth-vault → execute → Audit Sink
- AI Runtime's LLM calls have constitutional evidence records for budget enforcement (C-043)
- Token injection happens at socket boundary — LLM prompt history never contains a credential
- Exception Translator structurally prevents token leakage in error responses

---

## Tasks

| task_id | scope | model_hint | status |
|---|---|---|---|
| WC039-01 | `src/trust-layer/ctg/models.py` — dataclasses: `SessionContext` (tenant_id, agent_id, contract_id, skill_id, decision_space), `GatewayResult` (decision_id, result, error), `MCPToolError` (code: Literal[CONSTITUTIONAL_BLOCKED, PROVIDER_ERROR, TOKEN_DEGRADED, TIMEOUT], message: str, retry_eligible: bool). All fields typed, no raw exception propagation. | `auto` | pending |
| WC039-02 | `src/trust-layer/ctg/registry_client.py` — `ProviderRegistryClient` with 60-second in-memory TTL cache. `async get_config(tenant_id, provider_name) → ProviderConfig`. Calls BP `GET /api/v1/providers/{provider_name}` with internal service JWT. Cache key: `(tenant_id, provider_name)`. On cache miss or stale: refresh from BP. | `reasoning` | pending |
| WC039-03 | `src/trust-layer/ctg/exception_translator.py` — `ExceptionTranslator`. `translate(raw_exc, provider_name) → MCPToolError`. Maps known HTTP status codes and exception types to MCPToolError codes. Raw exception written to `logger.warning()` with `extra={"secure": True}` — NOT returned to caller. Token value must never appear in the MCPToolError message (enforced by: token is a local variable in `gateway.py`, never passed into this function). | `auto` | pending |
| WC039-04 | `src/trust-layer/ctg/gateway.py` — `ConstitutionalToolGateway`. `async call(tool_name: str, args: dict, session_ctx: SessionContext) → GatewayResult`. Pipeline per ADR-042 §2: (1) `registry_client.get_config()`; (2) CE.ValidateAction via gRPC — `ConstitutionalBlockError` on DENY; (3) oauth-vault `GET /tokens/{contract_id}/{provider_name}` → token held as local variable; (4) inject token at socket boundary (Authorization header for OAuth2, x-api-key header for API_KEY); (5) execute (MCP SDK call or direct HTTPS for LLM); (6) `exception_translator` on failure; (7) write evidence record to Audit Sink; (8) clear token local variable; (9) return `GatewayResult`. | `reasoning` | pending |
| WC039-05 | AIR refactor — `src/ai-runtime/pse/router.py`: after `route_and_dispatch()` selects provider+model, replace direct LLM SDK call with `gateway.call("llm.complete", {"provider": provider, "model": model, "messages": messages, ...}, session_ctx)`. Build `session_ctx` from the PSE session state (tenant_id, agent_id, contract_id). PSE router now has constitutional evidence for every LLM call. | `reasoning` | pending |
| WC039-06 | Tests — `tests/trust-layer/test_ctg.py`: CCT-CTG-01 (CE.ValidateAction called before any external call — mock CE, assert called with correct tool_name + dcm_category); CCT-CTG-02 (token absent from MCPToolError on failure — inject mock exception containing token string, assert MCPToolError.message does not contain token); CCT-CTG-03 (evidence record written after every successful call — mock Audit Sink writer, assert called with decision_id + args_hash); CCT-CTG-04 (DENY from CE → ConstitutionalBlockError raised, no external call made). `tests/ai-runtime/test_pse_router.py` updated: replace direct LLM mock with CTG mock, verify existing tier-selection CCTs still pass. | `auto` | pending |

---

## Required Inputs

| Input | File |
|---|---|
| ADR-042 CTG spec | `adr/ADR-042-provider-registry-constitutional-tool-gateway.md` |
| ADR-044 Audit Sink spec | `adr/ADR-044-constitutional-audit-trail-sink.md` |
| AIR PSE router (refactor target) | `src/ai-runtime/pse/router.py` |
| CE gRPC client in Python | `src/professional-runtime/` (reference for existing gRPC client setup) |
| Existing AIR test suite | `tests/ai-runtime/test_pse_router.py` |

---

## Definition of Done

- [ ] CTG library package structure: `src/trust-layer/ctg/__init__.py`, `models.py`, `registry_client.py`, `exception_translator.py`, `gateway.py`
- [ ] CCT-CTG-01: CE called before every external call (mock CE verifies)
- [ ] CCT-CTG-02: token absent from all caller-visible error output (inject token-containing exception, assert sanitized output)
- [ ] CCT-CTG-03: evidence record written after successful call
- [ ] CCT-CTG-04: DENY from CE stops execution before any external call
- [ ] AIR PSE router routes through CTG — no direct LLM SDK calls remain in `router.py`
- [ ] Existing AIR CCT-TRIAL-02/02b/02c pass unchanged (tier selection logic unaffected)
- [ ] `ruff` clean, `pytest` clean on trust-layer + ai-runtime tests
- [ ] VERSION bumped, CHANGELOG, PROJECT_STATE updated
