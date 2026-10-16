# R-150 - Security Architecture Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #520 |
| Office | Security Architect (INST-007) |
| Initial reviewed head | `93ba109fae10b674ee8088622a521d187645767f` |
| Initial disposition | `CHANGES_REQUIRED` |
| Re-review candidate | Work Component `1.1.0-candidate.1` |
| Final disposition | `PENDING SAME-OFFICE RE-REVIEW` |

## Scope

Review of provider authority, identity/RBAC, secrets, tenant isolation, private networking,
cryptographic evidence, traffic admission and emergency/recovery holds.

## Initial Findings And Repair Disposition

| Finding | Required correction | Candidate repair |
|---|---|---|
| Provider authorization was not immutable end-to-end | Bind environment, OIDC subject/audience, Azure scope, backend key, runner, release, plan and lease | Sections 5 and 11.1 define and negatively test the complete authorization tuple |
| Principal and secret separation was incomplete | Bind one secret-catalog digest and separate bootstrap, migration, workload, deployment and verifier identities | Sections 5, 7.2, 9.4 and 14.1 separate all principals, secret access and signatures |
| Tenant isolation lacked an executable matrix | Require FORCE RLS, NOBYPASSRLS, transaction-local context and pool reset tests | Sections 7.2 and 12 make the matrix blocking before and after restore |
| Network isolation did not prove every denied source | Add direct-app, runner, public, foreign-environment, DNS/TLS and egress denial | Section 7.4 defines the source matrix, hostname-validating TLS, no public fallback and default-deny egress |
| Lifecycle evidence and holds were not independently protected | Require hash chains, writer/verifier separation, CCT-SEC-04/05, hold classes and independent traffic admission | Sections 9.4, 12 and 14.1 add signed chains, forgery tests, holds and independent admission/sleep/restore/rollback signatures |

## Constitutional Boundaries

No security or C-001 hold may be released by deployment code, an alert receiver or the author.
Secret values never enter source, Terraform plan or evidence. Failed attempts remain retained.

## Re-review Requirement

The Security Architect must verify that the repaired candidate is fail-closed and that no principal
can self-authorize or self-verify. Only that same-office re-review may replace the pending final
disposition.
