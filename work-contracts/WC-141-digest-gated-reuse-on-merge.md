# WC-141 - Digest-Gated Reuse Of PR Validation On Merge To Main

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-141 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-139 (continuation) |
| Founder assignment | Current conversation: "how/what shall be reused in CI merge job so same pre checks dont run again on ci merge job"; "proceed to scope the digest-gated skipping" |
| Status | SCOPED - implementation not started. This PR records scope and decisions only |
| Baseline | `origin/main` `d2b75e03` (WC-139 merged) |
| Related contracts | WC-109 evidence envelope (dispositions `exact-candidate-reuse`, `verified-carry-forward`); WC-121 selective validation; WC-138 and WC-139 speed policy; WC-140 deploy-time reduction (no overlap: it changes `environment-deployment.yaml` and readiness scripts, not `ci.yaml`) |
| Requirement ledger | [WC-141-requirements.yaml](./WC-141-requirements.yaml) |
| Standing policy | [CI-VALIDATION-SPEED-POLICY](../standards/CI-VALIDATION-SPEED-POLICY.md) rules V6 and V7 |
| Constitutional basis | C-059, C-063 |

## Problem

On a push to `main`, `validation-plan.yaml` diffs `github.event.before..github.sha`. A merge commit's diff equals the PR's net change, so hosted CI selects and re-runs the same gates the PR run already passed (measured on #606: Business Platform tests 201 s on the PR and 247 s on the push; web 111 s and 121 s; license 153 s and 142 s). The repository already defines the proof model for reuse (WC-109 dispositions in `scripts/validation_control/evidence_controller.py`), and the local pre-check path uses it (`git_carry_forward_verifier`), but hosted CI does not.

## Decisions (made by the authoring office; the Founder may overrule)

| Decision | Choice | Reason |
|---|---|---|
| CodeQL on push | Keeps running on every push to `main` | It refreshes the code-scanning baseline of `main`; it is not a pass/fail repeat of the PR |
| Evidence age limit | Reuse only evidence from a PR run no older than 7 days (configurable in the catalog, not hard-coded in the workflow) | Bounds drift in runner images and base layers; artifacts are retained 90 days |
| First slice | Tests, quality, license and web gates only | Largest repeated cost with the lowest risk |
| Image retag instead of rebuild | Separate Work Contract | It touches attestation and signing |
| Release Qualification `az` speed-up | Not here; WC-140 already changes `goal006_activation_readiness.py` | Avoid overlap |

## Authority And Scope

### In scope

1. A reuse key per gate: gate id, gate input digest, runner image digest, graph or configuration version, and a digest of `.github/workflows/ci.yaml` and `.github/workflows/validation-plan.yaml`.
2. PR runs publish one evidence envelope per reusable gate, bound to the PR head commit and to the tree the run validated, using the WC-109 envelope and its HMAC.
3. A resolver step on pushes to `main` that finds the PR run for the merged head through the GitHub API and trusts only successful `pull_request` runs of this repository inside the age limit.
4. Disposition rules: tree equal to the validated tree gives `exact-candidate-reuse`; a different tree gives `verified-carry-forward` only when no changed path touches the gate's inputs; anything else runs fresh.
5. Visible reporting: a reused gate shows "reused from run N" in the push run, never a silent skip.
6. Never reused: gates marked `reusable: false` (dependency scans, gitleaks, Trivy), CodeQL, publish, attestation, and any gate whose evidence is missing, stale, forged or from the wrong tree.
7. A kill-switch repository variable that forces every gate to run, and fault-injection tests for stale, forged, expired and wrong-tree evidence.

### Out of scope

- Lowering any threshold, removing a gate or waiving a gate. The nightly full suite and the coverage gate (90% line, 80% branch) stay authoritative.
- Image retag, attestation and signing changes.
- Deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-141-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC141-R001 | A gate result is reused on a push to `main` only when its reuse key (gate id, input digest, runner image digest, graph version, workflow digest) equals the key of a passing PR-run envelope |
| WC141-R002 | Only a successful `pull_request` run of this repository, no older than the configured age limit, is trusted; fork, failed, cancelled, expired or unsigned evidence is ignored and the gate runs |
| WC141-R003 | Equal validated tree records `exact-candidate-reuse`; a different tree records `verified-carry-forward` only when no changed path touches the gate's inputs; otherwise the gate runs fresh |
| WC141-R004 | Every reused gate is reported in the push run with its source run and disposition; no gate is skipped silently |
| WC141-R005 | Gates marked `reusable: false`, CodeQL, publish and attestation always run on a push |
| WC141-R006 | A kill-switch variable forces every gate to run, and no threshold is lowered |
| WC141-R007 | Fault-injection tests prove stale, forged, expired, wrong-tree and missing evidence all fall back to running the gate |

## Implementation Plan (next PR, not this one)

1. Add the age limit and the reusable-gate list to `validation/engineering-validation.yaml`.
2. Add the reuse key and the resolver to `scripts/validation_control/` using `identity.py` and `evidence_controller.py`.
3. Wire the PR-run publisher and the push-run resolver into `.github/workflows/ci.yaml` and `validation-plan.yaml`, keeping `hosted_policy.py` green.
4. Add the fault-injection tests and wire them into the explicit gate list in `validation/engineering-validation.yaml`.

## Implementation Record

Not started. The implementation PR needs a separate authorization of the implementing session.
