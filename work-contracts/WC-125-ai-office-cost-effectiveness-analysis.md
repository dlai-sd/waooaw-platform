# Work Contract 125 — AI Office Cost And Effectiveness Analysis

**Office:** Enterprise Architect (INST-004)
**Assigned by:** Founder instruction, 2026-10-24
**Status:** GOVERNANCE IMPLEMENTATION IN PROGRESS — NOT UNIVERSAL RUNTIME ENFORCEMENT
**Authority:** Founder-approved analysis scope in this session
**Baseline context:** Founder reports more than USD 5,000 spent and more than 500 PRs; these figures are not independently verified in this analysis.

## 1. Objective

Assess repository-defined AI-office guidance and token/resource-economy architecture. Recommend a
zero-cost-first strategy where quality permits, preserving office effectiveness while making
cost, quality, rework, and elapsed time measurable. This work component parks the analysis for
continuation after the Codespace resumes.

## 2. Authority And Scope

This contract authorizes read-only analysis and recording its findings in this work component.
The scope covers relevant office cards and shared agent guidance, token-economy principles,
model-routing standards, and repository evidence relevant to the Founder’s objectives.

It does not authorize:

- changing office cards, agent prompts, model assignments, routing policy, or runtime behavior;
- changing code, configuration, architecture, constitutional claims, or other Work Contracts;
- implementing or deploying recommendations, using paid providers, or incurring expenditure;
- asserting measured savings or independently verified historical spend/PR totals.

Any implementation, including code or operational configuration changes, requires a separate
bounded Work Contract and explicit per-session implementation authorization where applicable.

## 3. Founder Objectives

1. Prefer zero-cost AI models when they can meet the task’s quality requirements; use paid or
   advanced models only when justified by demonstrated task needs.
2. Reduce spend without diluting the effectiveness of office outcomes. Treat elapsed time as a
   potential trade-off to measure and manage.
3. Use experience from more than 500 reported PRs and the Founder’s agent-interaction learnings
   to improve office performance.
4. Revisit office performance continuously for cost, effectiveness, and efficiency.

## 4. Evidence Reviewed

- [Enterprise Architect office card](../.github/agent-context/office-enterprise-architect.md)
- [Platform IT Expert office card](../.github/agent-context/office-platform-it-expert.md)
- [Runtime Professional office card](../.github/agent-context/office-runtime-professional.md)
- [Solution Architect office card](../.github/agent-context/office-solution-architect.md)
- [Platform Architect office card](../.github/agent-context/office-platform-architect.md)
- [Product Owner office card](../.github/agent-context/office-product-owner.md)
- [Shared Copilot instructions](../.github/copilot-instructions.md)
- [C-051 claim](../knowledge/claims/C-051.md)
- [Knowledge claim index](../knowledge/index.md)
- [AD-022 and AD-023](../knowledge/architectural-drivers.md)
- [DP-020](../knowledge/design-principles.md)
- [Token Economy component](../architecture/reference/components/token-economy.md)
- [Agent Authoring Guide, model-tier assignment](../architecture/reference/agents/AGENT-AUTHORING-GUIDE.md)
- [Reasoning trace instrumentation](../architecture/reference/agent-reasoning-trace.md)
- [C-095 claim](../knowledge/claims/C-095.md)

This was a targeted guidance review, not an exhaustive audit of every office file, historical PR,
provider invoice, model call, or outcome record.

## 5. Analysis Findings

1. **Sound product-agent foundation exists.** C-051, AD-022, AD-023, and DP-020 already define
   resource boundaries, task-specific model tiers, caching, and quality-preserving economy for
   customer-facing professional agents.
2. **Internal development offices are not yet governed consistently by measured cost/outcome
   evidence in the compact guidance reviewed.** The Platform IT Expert card explicitly calls for
   compact context, deterministic tools, and no model/provider calls for deterministic work.
   The reviewed office cards do not present a common scorecard tying model usage to accepted work,
   rework, defects, and elapsed time.
3. **Do not transfer customer-agent tier rules mechanically to development offices.** The
   customer-agent taxonomy is not itself a measured office-specific model-routing policy.
4. **Two repository consistency issues merit resolution before changing routing policy:**
   - [AD-022](../knowledge/architectural-drivers.md) prohibits going below a prompt’s declared
     minimum tier; the [Token Economy router](../architecture/reference/components/token-economy.md)
     describes downgrading frontier work on later iterations.
   - [C-051](../knowledge/claims/C-051.md) labels the claim `LAW`, while the
     [knowledge index](../knowledge/index.md) lists it under `CONFIRMED`.
5. **There is evidence for targeted efficiency interventions, not universal savings claims.**
   [C-095](../knowledge/claims/C-095.md) records a simulation in which skeleton-based task
   preparation reduced tokens from 24,000 to 6,000 per simulated task and improved first-attempt
   compilation. This is not a measured result across all offices or historical PRs.
6. **Historical spend and PR totals remain Founder-provided context.** No provider billing or
   historical task-level usage/outcome dataset was examined; actual savings cannot yet be claimed.

## 6. Proposed Points And Expected Outcomes

| Proposed point | Expected outcome | Measure / quality guard |
|---|---|---|
| Adopt zero-cost-first routing for internal office tasks only where a candidate model or deterministic path passes task-specific quality gates. Escalate when complexity, uncertainty, safety, or observed failure requires it. | Reduce paid-model use without disguising quality loss as savings. | Cost per accepted task; acceptance/rework and defect rates by task class and model tier. No tier reduction based on cost pressure alone. |
| Establish a common office scorecard: model/provider, input/output tokens where available, direct cost where available, first-pass validation, retries, rework, defects, accepted outcome, and elapsed time. | Make spend and effectiveness visible together; identify genuine optimization opportunities. | Baseline and trend by office/task class; disclose missing usage or cost data instead of estimating as fact. |
| Standardize compact, task-relevant context, deterministic-first work, reusable validated artifacts, and focused checks across office guidance. | Reduce repeated prompt/context work and avoidable retries. | Context and retry trends plus unchanged or improved task acceptance and defect outcomes. |
| Separate development-office model policies from customer-agent model-tier declarations; record explicit escalation criteria for each office/task class. | Avoid misapplying product-runtime policy to architecture, coding, testing, and governance work. | Approved task-to-tier matrix with rationale and quality evidence before operational adoption. |
| Resolve the AD-022/router and C-051/index consistency discrepancies through their authorized governance path before policy implementation. | Ensure cost optimization follows one coherent authority and quality baseline. | Reconciled source-of-truth artifacts and approval recorded by the authorized owner. |
| Review performance at a regular Founder-selected cadence, using cost, accepted outcome, rework/defects, and time together. | Keep the operating strategy adaptive as models, offices, and work mix change. | Period-over-period scorecard; any change is evidence-backed and reversible. |

No numerical savings target is proposed because no office-level usage, provider-cost, or outcome
baseline was measured in this analysis.

## 7. Definition Of Done

- Review relevant office and shared agent guidance and token-economy sources.
- Record findings with repository traceability and distinguish evidence from Founder-provided
  context and unverified assumptions.
- Present a concise proposal table with expected outcomes, measures, and quality safeguards.
- Preserve a clear boundary between analysis and implementation.

**Completion:** Analysis and summary table are recorded in Sections 5–6. No implementation or
repository configuration changes are authorized by this contract.

## 8. Resume Checkpoint

On Codespace restart, resume by reading this Work Contract first. The analysis is complete; the
next Founder decision is whether to authorize a separate strategy-design or implementation
Work Contract. Do not infer implementation authority from this checkpoint.

## 9. Founder-Authorized Governance Implementation Addendum

On 2026-10-24 the Founder requested implementation of the proposed points and explicitly answered
the current-session implementation authorization question affirmatively. The Founder selected an
isolated branch/worktree from freshly fetched main. This addendum supersedes the analysis-only
boundary for the following delivery; Sections 1-8 retain the original analysis as historical context.

**Branch:** `ib/125/ai-office-resource-governance`
**Implementation baseline:** `origin/main` at `7c64918b`
**Scope:** A shared resource-governance standard, universal entry-point inheritance, corrections
to the two documented consistency issues, a typed deterministic execution-record/inheritance
validator, regression tests, and wiring into the existing global Docker scripts-quality gate.
Class 1 constitutional texts remain unchanged; no new claim is fabricated or self-ratified.

The refreshed baseline includes C-077 development budget requirements, Goal Orchestrator vNext
cheapest-capable routing/budget states, and WC-106/108/121 validation controls. Reuse these rather
than introducing another test orchestration system or treating the older checkout as current.

### Acceptance and Stops

| ID | Required outcome | Validation |
|---|---|---|
| WC125-R001 | One standard applies to all current and future offices/agents without changing authority or protected floors | Entry-point inheritance checker and regression tests |
| WC125-R002 | Free-model preference is capability-qualified; provider/privacy authority and paid escalation remain explicit | Standard author review and execution-record negative tests |
| WC125-R003 | Compact context, deterministic/reuse-first work, bounded repairs, and monthly/event-triggered review are specified | Standard author review |
| WC125-R004 | Unknown usage/cost is disclosed, accepted work cites evidence, repair escalation is recorded, and nonfinite/invalid metrics fail | Execution-record tests |
| WC125-R005 | Existing global Docker quality path checks inheritance and regression tests | Catalog wiring regression test |
| WC125-R006 | C-051 index type and minimum-tier retry contradiction are corrected without altering claim authority | Targeted consistency tests |
| WC125-R007 | No claim of universal runtime compliance, measured savings, or free-provider qualification without evidence | Author review and explicit enforcement boundary |
| WC125-R008 | Every execution channel has qualified pre-dispatch model/cost controls and measured usage/outcome integration | OPEN: dispatcher/client integrations and qualification remain unavailable in this delivery |

Stop rather than modify an immutable constitutional text, waive an existing quality gate, use a
new external provider, spend funds, or claim enforcement unavailable in a client/dispatcher.

### Delivery Boundary

This delivery implements policy inheritance and deterministic contract checks, not model dispatch
adapters or provider billing integration. Existing dispatchers and external clients need separately
qualified integration for enforceable model selection and per-call budget/usage capture.
Universal automated runtime compliance therefore remains an explicit open requirement, not a
completed or self-attested outcome. The Founder retains review, activation, and merge authority.

## 10. Qualification Evidence And Current Resume Point

The Section 9 addendum supersedes the original Section 8 resume decision. Continue on
`ib/125/ai-office-resource-governance` in `/workspaces/waooaw-platform-wc125`, not the original
dirty web branch. Continuous-session bootstrap remains valid; do not repeat it without explicit
Founder approval. A new session follows the bootstrap authorization rules, not a checkpoint shortcut.

Local diagnostic validation used the existing Docker Python runner image
`sha256:c1514644b3979e421b166fa26030ae5acff1ea80b721454cde992ea33134aec1`.
Source mounts remained read-only; legacy writer fixtures ran from a disposable `/tmp` copy.

Command prefix for the checks below:

```sh
WAOOAW_RUNNER_PYTHON_IMAGE=waooaw-platform-test-runner-python:latest \
docker compose -p wc125-validation --profile test-python run --rm --no-deps --pull never \
test-runner-python sh -c '<check>'
```

| Check inside the Docker runner | Result |
|---|---|
| `ruff check scripts/ai_resource_governance.py tests/scripts/test_ai_resource_governance.py` | PASS |
| `ruff format --check scripts/ai_resource_governance.py tests/scripts/test_ai_resource_governance.py` | PASS |
| `mypy --strict --follow-imports=silent --cache-dir=/tmp/wc125-mypy scripts/ai_resource_governance.py` | PASS; installed jsonschema has no typing stubs, so only its import uses a narrow import-untyped suppression |
| `python scripts/ai_resource_governance.py --repository /workspace` | PASS for instruction inheritance, not provider-routing or billing assurance |
| `COVERAGE_FILE=/tmp/wc125.coverage pytest tests/scripts/test_ai_resource_governance.py tests/validation_control/test_unified_execution_contract.py tests/validation_control/test_pilot.py -q --cov=ai_resource_governance --cov-branch --cov-fail-under=90 --cov-report=term-missing` | 102 passed; validator combined line/branch coverage 97.08% |
| `mkdir /tmp/wc125-regression && cp -a scripts tests pyproject.toml /tmp/wc125-regression/ && cd /tmp/wc125-regression && PYTHONPATH=/tmp/wc125-regression:/tmp/wc125-regression/scripts pytest tests/pipeline/test_magic_llm_context_evaluator.py tests/pipeline/test_magic_llm_end_to_end.py -q` | 55 passed; no live model calls |
| Catalog-qualified full gate, hosted CI, provider/model qualification, deployment, Founder activation | NOT RUN / NOT CLAIMED |

Initial validation discovered two additional current-main office cards (Founder support and QA);
both now inherit the standard. The first legacy regression attempt had 110 passes and one failure
because its fixture attempted a source write into the read-only Docker mount. The disposable
workspace rerun passed all 55 legacy regressions without changing application code or weakening
read-only source isolation.

The first Compose invocation attempted to build the unavailable default `:local` runner tag and
was stopped; subsequent checks explicitly reused the existing `:latest` image without rebuilding.
An initial mypy invocation failed with its default cache configuration; the disposable writable
cache exposed and allowed repair of a local exception-variable typing issue. No host Python,
package installation, live provider call, deployment, or unrelated web edit was used.

Author review covers authority, quality floors, context minimization, missing metrics, escalation,
private-data isolation, instruction links, negative tests, and rollback. Deterministic contract
checks validate shape and inheritance, not the truth of qualifications or universal adoption.
Rollback is reverting the governance delivery while retaining historical execution evidence;
no database, infrastructure, customer allowance, or deployed provider configuration changed.

**Remaining blocker:** WC125-R008 is not satisfied. Repository guidance cannot force an external
client's model or meter its bill, and legacy dispatchers still require separately qualified
pre-dispatch enforcement/exporter integration. Do not declare universal compliance, cost savings,
or this overall request DONE from the passing local tests.
