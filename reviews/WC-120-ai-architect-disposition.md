# WC-120 AI Architect Disposition

## Review Control

| Field | Value |
|---|---|
| Work Contract | WC-120 |
| Reviewing office | AI Architect (INST-008) |
| Review mode | Founder-requested single-pass specialist review and owner-controlled repair |
| Scope | WC-120 and AI-relevant accepted AIR/Core/WC-114/WC-115/PR #498/PR #499 surfaces only |
| Reviewed candidate | PR #499 solution blob `224d8f43f2a46e810eb5b13aac35570b6f0ebcda`; API blob `77b7875a0d294be3aba21534bf33cd92c7527e15` |
| Accepted AIR profile | `conversational-employment-specialist-profiles.yaml` blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66`, `ai_profile` |
| Accepted Core/AIR APIs | BP employment API blob `bf7d3466c4113049f9f61200583811a25e454951`; AIR API blob `bfa447520302a950f81a8f525c954f871e22bfec` |
| Accepted contracts | WC-114 blob `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`; WC-115 blob `337fcef0a51a4c2ef2ff72423a7afc64969d8914` |
| Enterprise input | PR #498 merged commit `4a4420af6ee132623d6b87eb3863d700e56c9b86`, especially §§8-10, 16-17, 22-24 |
| Disposition | **PASS — specification PASS after the repairs below; implementation remains gated and unauthorized** |

## Validation Result

The repaired WC-120 boundary preserves BP authority for server-side context and policy resolution,
PR responsibility for execution/reconciliation, and AIR responsibility for bounded,
provider-neutral reasoning. The channel supplies neither policy nor model/provider authority.
Context, policy, source, and Decision Space versions are bound before AIR use. Every untrusted
segment retains provenance/trust metadata and is structurally separated from instructions.

Research, inference, recommendation, and confirmed fact now remain explicit separate states.
Unavailable service, pending reconciliation, and customer-visible unknown are not success and do
not authorize mutation or blind retry. The accepted AIR profile—not implementer defaults—controls
canonicalization, digest identity, catalogue identity, provenance, result variants, material
uncertainty, transient content, and the evaluation corpus.

## Findings, WC120-R Mapping, And Repairs

| Finding | WC120-R mapping | Exact finding | Repair made in this pass | Result |
|---|---|---|---|---|
| WC120-AI-001 | R005, R040 | R040 referred generally to the AIR profile but did not carry its mandatory digest tuple, BP-owned non-caller-selectable semantic catalogue, provenance fields, closed result states, transient-content limits, or 100% immutable-corpus oracle. That allowed an implementer to satisfy a weaker interpretation. | Added WC-120 §3.1.1 and expanded the R040 contract row and ledger entry with the exact accepted profile controls and evidence predicates. | CLOSED |
| WC120-AI-002 | R006, R040 | Research-versus-inference separation existed in PR #498/PR #499 but was not an explicit R040 completion condition. Promotion, expiry, and invalidation behavior could therefore be lost at the AIR handoff. | §3.1.1 now requires typed research/inference/recommendation/confirmed states, attributable source/capture/expiry or inference basis, no confidence-based promotion, accountable-owner confirmation, and invalidation on correction/expiry/material version change. | CLOSED |
| WC120-AI-003 | R005, R040 | Prompt-injection coverage named hostile input but did not enumerate indirect injection, retrieval/tool output, quoted-policy imitation, cross-segment contamination, or protected policy/catalogue/tenant/relationship/operation targets. | §3.1.1 and the R040 test plan now require these adversarial classes, structural trust separation, and independent authorization of every proposed command/tool/patch/context change. | CLOSED |
| WC120-AI-004 | R002, R005, R040 | Minimum-necessary content and provider neutrality were outcomes but lacked a precise boundary: no explicit prohibition on unrelated history/provider credentials and no statement that the public client/channel cannot select model/provider. | §3.1.1 limits the handoff to bounded contributions and server references; prohibits raw identity, provider credentials, unrelated/unbounded history, and channel-selected model/provider; binds provider choice behind AIR model policy. | CLOSED |
| WC120-AI-005 | R003, R005, R040 | AIR/model unavailable, unresolved in-flight, and customer-visible unknown behavior could be conflated, permitting synthetic success or unsafe retry. | §3.1.1 distinguishes AIR `PENDING`, customer-visible `UNKNOWN`, and `UNAVAILABLE`; each prohibits synthetic success and consequential authority, and unresolved outcomes prohibit blind retry. R040 now requires direct no-mutation fixtures. | CLOSED |

## Accepted AIR Profile And Source Mapping

| Accepted control | WC-120 binding |
|---|---|
| WC-115 §7.3 and R095-R101 | §3.1.1; R040 |
| Accepted `ai_profile.canonicalization`, `digest`, and `idempotency_identity` | §3.1.1 digest verification; R040 corpus plan |
| Accepted BP-owned `semantic_catalogue` identity and entry fields | §3.1.1 catalogue control; R040 allow-list evidence |
| Accepted prompt/model/model-decision provenance | §3.1.1 provenance control; R040 reconciliation evidence |
| Accepted `PENDING` / `PROPOSED` / `UNREPRESENTABLE` / `FAILED` constraints | §3.1.1 result control; R040 state fixtures |
| Accepted confidence/material-uncertainty behavior | §3.1.1 no-authority/unresolved-question rule; R040 corpus |
| Accepted transient-content encryption, PT1H terminal deletion, PT24H maximum, and no logging | §3.1.1 retention boundary; R040 evidence |
| PR #498 §§8.6, 9.2-9.6, 10, 16-17 and PR #499 §§6.3, 8-9 / CSA-CEWA-004..006 | §3.1.1 context, trust, lineage, policy, unavailable/unknown, and conclusion controls; R005/R006/R040 |

## Review Evidence

- Accepted source blob identities were resolved directly from merged WC-114, WC-115, PR #498,
  and PR #499 history and match the references above.
- `sha256sum` plus a shell equality assertion confirmed that the exact WC-120 contract digest is
  `d12b0187ee42f2ecc72256f410dfe88f1140d6ec5f9ccda7772a0653bff6223c` and matches the
  requirement ledger.
- `git diff --check -- reviews/WC-120-ai-architect-disposition.md
  work-contracts/WC-120-conversation-engine-whatsapp-implementation.md
  work-contracts/WC-120-requirements.yaml
  work-contracts/WC-120-fitness-evidence-matrix.yaml` — PASS.
- Python ledger and YAML validation — **BLOCKED for this pass**. The compose configuration exposes
  no dedicated repository test-runner service. Starting an application/AIR service or using host
  Python would violate the review authority and explicit execution constraint. No Python,
  environment, provider, or model process was invoked. This does not change the specification
  disposition; the Docker ledger gate remains a pre-implementation stop under WC120-R001.

## Required Stops And Blocked Behavior

This PASS is limited to the repaired WC-120 specification. It does not establish implementation
readiness. The affected work remains blocked if any of the following is absent or mismatched:

- the exact BP/PR/AIR handoff and operation/schema crosswalk to the accepted WC-114/WC-115 AIR
  candidate;
- any accepted `ai_profile` value, digest/catalogue/provenance field, result-state constraint, or
  transient-content control;
- an immutable digest-bound WC-115-R101 corpus with 100% passing direct predicates;
- source/version lineage, permitted-use metadata, or invalidation before consequential reuse;
- structural separation and adversarial evidence for direct/indirect/tool/retrieval/transcript
  prompt injection;
- proof that the payload is minimum necessary and excludes raw identity, unrelated/unbounded
  history, provider credentials, and public/channel provider selection; or
- explicit no-mutation/no-synthetic-success behavior for stale, ambiguous, unavailable, pending,
  unknown, failed-digest, failed-provenance, and unknown-authority cases.

No fallback model/provider, lower-trust context, cached authority, synthetic answer, guessed fact,
blind retry, or channel-specific downgrade is permitted. A missing owner contract or conflicting
accepted source stops for Founder direction; it is not an implementation choice.

## Final Disposition

**PASS.** WC-120 is AI-architecture-complete for this specialist pass after the recorded
owner-controlled repairs. This disposition neither accepts WC-120 on behalf of the Founder nor
authorizes implementation, model/provider access, prompt deployment, cloud/provider mutation,
traffic, activation, Production change, PR approval, or merge.
