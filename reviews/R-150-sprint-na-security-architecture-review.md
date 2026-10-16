# R-150 - Security Architecture Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #520 |
| Office | Security Architect (INST-007) |
| Initial reviewed head | `93ba109fae10b674ee8088622a521d187645767f` |
| Initial disposition | `CHANGES_REQUIRED` |
| Re-reviewed head | `a06026895628b288b33d4e6832417b83a989e6d5` |
| Re-review disposition | `CHANGES_REQUIRED` |
| Follow-up repair | Work Component `1.1.0-candidate.2`; exact-head author verification required |

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
| Lifecycle evidence and holds were not independently protected | Require hash chains, writer/verifier separation, exact evidence/emergency test criteria, hold classes and independent traffic admission | Sections 9.4, 12 and 14.1 add signed chains, uniquely named tests, forgery tests, holds and independent admission/sleep/restore/rollback signatures |

## Constitutional Boundaries

No security or C-001 hold may be released by deployment code, an alert receiver or the author.
Secret values never enter source, Terraform plan or evidence. Failed attempts remain retained.

## Re-review Findings And Follow-up Repair

The re-review closed tenant isolation and network denial but identified three remaining issues:
Demo authorization could be read as reusable for UAT, the secret-catalog digest was not in every
authorization/admission tuple, and bare `CCT-SEC-04/05` identifiers conflicted with the
constitutional test catalogue.

Candidate 2 makes provider authorization environment-specific, binds the secret-catalog digest to
every provider/lifecycle/rollback tuple and negative gate, and replaces ambiguous identifiers with
`PST-SEC-EVIDENCE-01` and `PST-SEC-EMERGENCY-01` plus exact governing test names and records. The
Chief Solution Architect exact-head author review must verify these repairs before submission.
