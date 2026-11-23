# ADR-056 - Acceptance Evidence As A Promotion Input

**Status:** PROPOSED - awaiting Founder acceptance
**Date:** 2026-11-23
**Decision owner:** Platform IT Expert (INST-010) as author; acceptance and any promotion change are Founder decisions
**Authorization:** Founder instruction in the 2026-11-23 conversation to complete the deferred items; this ADR is authored, not accepted
**Work Contract:** WC-163
**Constitutional basis:** C-023, C-049, C-065, C-071
**Amends:** ADR-054 item 8 (report-only verdict), only if accepted
**Companion:** ADR-054, ADR-055

## Context

ADR-054 item 8 makes the acceptance verdict report-only and forbids any required check, deployment gate or branch rule
from depending on it until a later ADR amendment is accepted by the Founder. The Founder asked for promotion gating to be
completed. Accepting this ADR is the Founder's act, not the author's, so the gating is delivered as a decision record and an
evaluator that nothing consumes.

## Decision (proposed)

1. **Evidence, not authority.** A promotion decision may read an acceptance report as one input. It never replaces Founder
   approval (C-065) and never approves, merges or deploys by itself.
2. **Policy as data.** `validation/acceptance/promotion-policy.yaml` states what a report must show: verdict PASS, no
   NOT-WITNESSED, BLOCKED-BY-FLAG or FLAKY step, a fresh report, and a passing WC107-R019 rollup. It carries `enforced: false`.
3. **Evaluator.** `scripts/acceptance_promotion_evaluator.py` reads a report, the rollup result and the policy and answers
   ELIGIBLE or NOT_ELIGIBLE with reasons. It is a pure function and has no side effect.
4. **Not wired.** While this ADR is PROPOSED, the static gate (F17) fails if any workflow, catalog entry or rule references the
   evaluator or the acceptance workflow, and fails if the policy says `enforced: true`.
5. **Activation path.** Accepting this ADR, then a separate Work Contract that names the exact required check or promotion
   step, then a Founder-approved rollout, are all needed before any gate consults the evaluator. The first rollout should
   be advisory (a comment on the promotion record) before it is blocking.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| Gate promotion on the acceptance workflow's conclusion | The workflow is manual and can be red for an unavailable environment; ADR-054 item 8 forbids it today. |
| Let the author wire the gate now | Changes promotion rules; only the Founder may. |
| Do nothing | The Founder asked for the evaluator to exist so the decision can be made on evidence. |

## Consequences

- Positive: the promotion question becomes a data question with a tested answer.
- Negative: a stale or missing report makes a candidate NOT_ELIGIBLE, which is intended.
- Reversibility: deleting the policy and the evaluator removes everything; nothing else depends on them.
