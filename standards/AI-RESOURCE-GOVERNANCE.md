# AI Resource Governance

**Owner:** Enterprise Architect
**Authority:** Founder instruction and session authorization, 2026-10-24; WC-125
**Basis:** C-001, C-023, C-049, C-051, C-059, C-065, C-070, C-077; DP-020; AD-022/023
**Status:** Implemented proposal; activation remains subject to Founder review and merge
**Applies to:** Every WAOOAW office, internal/customer agent, contributor, and execution channel

## 1. Universal execution contract

All agents inherit this standard through the shared entry point and Constitutional DNA.
It supplements existing authority, quality, privacy, and model-tier floors; it does not amend
immutable constitutional texts, grant a new Decision Space, or waive protected approvals.
Customer runtime allowances remain distinct from internal development costs and C-077 budgets.

Before execution, identify the owner, authorized outcome, acceptance checks, selected skill,
required input versions, and resource envelope. Use the existing Work Contract or execution
record; do not create another planning document or ask for approval already valid for this scope.
On close, append a compact execution record using Section 4. Author review is mandatory, not
independent approval. Cost savings never replace acceptance evidence.

## 2. Cheapest capable route

Evaluate these routes in order, within the approved minimum capability tier:

1. Deterministic tools for parsing, retrieval, transformations, builds, tests, and factual counts.
2. Reuse approved artifacts whose scope, versions, hashes, privacy boundary, and freshness match.
3. A qualified zero-inference-price model when it satisfies the task's capability and data rules.
4. A paid model only with an explicit reason that earlier routes cannot deliver the accepted outcome.

Price is not capability. A free model can be frontier-capable; a paid model can be inadequate.
Do not label hosted local inference zero-total-cost: record compute, hosting, CI, and latency
separately where available. Do not assume consumer free access provides an authorized API or that
a provider's current free quota, privacy terms, residency, and availability are permanent.
Never transmit repository or customer data to a new provider without applicable authority.

Qualify each model for the actual office/task class using pinned representative inputs and the
same acceptance tests as the incumbent. Record model/version, data boundary, comparison evidence,
failures, quality verdict, and validity assumptions. Self-reported confidence is not qualification.
No model/provider is newly qualified or activated by this standard.

Retain AD-022 minimum tiers, BREAKING/protected-decision floors, and Steward Assistant's existing
frontier requirement. Never downgrade on retries, budget pressure, free quota exhaustion, or outages.
After one bounded repair fails, contradictory evidence, unresolved ambiguity, or a high-consequence
decision appears, stop and escalate to a capable model and the proper authority. A stronger model
does not supply missing authority. No silent paid fallback: disclose the reason and respect the
approved spend envelope. If no compliant route exists, report BLOCKED.

Emergency Stop and constitutional evidence paths remain exempt from commercial resource controls;
they must never wait for this standard's scorecard, model routing, or budget consolidation.

### 2.1 Office activation model notice

When occupying any office in an interactive client, include exactly one bold recommendation line
before substantive task execution. Use the known task and its minimum capability, not office name
alone. If the task is not assigned yet, explicitly label the recommendation provisional.

- Start the line with `Model recommendation:`; name the selectable model or setting, a short reason,
  and any material availability/qualification uncertainty.
- Name a free option only from currently verified picker/account evidence, such as the Founder's
  supplied model-picker list or screenshot. Distinguish zero premium-request multiplier from
  zero total subscription cost. Availability and pricing may differ by account.
- If picker details are unavailable, do not invent a list or claim a named model is free. Use:
  **Model recommendation: Check Copilot's model picker for a zero-premium-request option; availability
  and task suitability are unverified here, and Auto is not guaranteed free.**
- If a qualified available model is known, recommend it explicitly with the task reason. Otherwise
  identify qualification as pending; do not present a trial candidate as already quality-qualified.
- If a stronger model is required, name it only when selectable options are known; otherwise specify
  the required capability and request picker options using the client's question mechanism.
- Office activation does not change the selected model. Never claim to observe or switch it unless
  the client actually exposes that control. Do not infer that an "Auto agent" label identifies a model,
  a billing rate, or even the Auto model-selection setting.

Give the notice once per office activation, including when bootstrap is not requested. Do not start
bootstrap automatically to produce it. Repeat only when the task's capability requirement changes
or an escalation is needed. Do not delay emergency action to display a recommendation.

## 3. Context, execution, and reuse discipline

- Load only the task's compact office card, skill section, owning files, and nearest tests.
  Expand when evidence requires it; token limits must not cause omission of required inputs.
- Reuse the valid bootstrap for the continuous conversation; do not rerun it after compaction.
- Batch independent reads/checks; prefer deterministic tooling to model calls for deterministic work.
- Reuse compiled contracts, generated clients, templates, and approved evidence instead of invention.
- Run focused validation first and final qualification for the exact candidate using the existing
  Docker validation control plane. Do not lower coverage, skip gates, or substitute cached stale tests.
- Use stable, version-pinned context where supported. Never share private tenant context.
- Keep output concise and decision-oriented. Preserve evidence references and unresolved findings,
  not private chain-of-thought, secrets, full prompts, or unnecessary customer data.
- Reuse the accountable office context. Additional agents/roles require existing Founder authority
  and a material decision need; do not create agents to perform deterministic lookups or duplicate work.
- Follow the existing Goal Orchestrator budget states: consolidate at 80 percent or repeated context;
  stop and replan for forecast overruns or failed repair. Unknown usage is UNKNOWN, not zero.

## 4. Execution record and performance review

Use one JSON record per execution; an existing telemetry exporter may supply it. Keep records in
the owning evidence store and cite them from the Work Contract. Do not commit fabricated baseline
measurements. The deterministic validator is:

```sh
# Run inside an approved Docker validation runner, never a host Python environment:
python scripts/ai_resource_governance.py --record /path/to/execution.json
python scripts/ai_resource_governance.py --repository /workspace
```

Required shape (null means unavailable, not zero):

```json
{
  "execution_id": "unique-attempt-id",
  "office": "INST-004",
  "work_contract": "WC-125",
  "task_class": "architecture",
  "route": "PAID",
  "model": "actual-model-version-or-null",
  "selection_reason": "Why cheaper compliant routes cannot satisfy this task",
  "qualification_ref": "pinned-task-class-quality-evidence-or-null",
  "escalation_reason": null,
  "limitations": ["Client does not expose metered cost"],
  "input_tokens": null,
  "output_tokens": null,
  "cached_tokens": null,
  "cost": null,
  "currency": null,
  "cost_basis": "UNKNOWN",
  "elapsed_seconds": 120,
  "repair_count": 0,
  "accepted": false,
  "validation_refs": [],
  "escaped_defects": null
}
```

Routes: DETERMINISTIC, REUSE, FREE, PAID, CLIENT_CONTROLLED.
FREE and PAID require an actual model; FREE requires qualification evidence. CLIENT_CONTROLLED
means the external client does not expose routing control; disclose that limitation rather than
pretending the selected model is compliant or changing settings without authority.
Cost basis: METERED, ESTIMATED, UNKNOWN. Cost always carries a currency and basis; missing cost,
tokens, defect tracking, or qualification is explicitly disclosed in limitations.
An accepted outcome requires executable validation or domain-appropriate acceptance references.
Zero cost is a measured or clearly bounded estimate, never the default for absent telemetry.

Review monthly and after a material escaped defect, model/provider change, or repeated escalation.
Compare like-for-like office/task classes using cost per accepted outcome, first-pass acceptance,
repair/rework, escaped defects, and elapsed time. Include failed attempts in cost totals. Separate
currencies, estimates, unknown coverage, and customer/internal spend; do not infer causation from
PR count or mixed work. Suspend an optimization on quality regression and retain the previous
qualified route. Report lessons once in the owning record and propose changes through its owner.

## 5. Enforcement boundary and adoption

The repository checker and its regression tests run in the existing global scripts quality gate.
They enforce shared instruction inheritance and the execution-record contract. They do not meter
external clients, inspect provider bills, enforce model selection in every dispatcher, validate the
truth of a cited qualification, or install new provider adapters. Instruction compliance is not a
runtime security boundary.

Every execution channel must disclose whether routing, usage capture, and pre-dispatch budget
enforcement are actually available. Until a channel is integrated and qualified, record that gap;
do not claim universal automated compliance. Existing runtime and protected-authority enforcement
remain in place. A channel needing new provider/routing code requires its own approved design and
qualification, not a policy-only assertion of full enforcement.
