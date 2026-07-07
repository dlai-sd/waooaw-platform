# ADR-013: CI/CD Pipeline Structure

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Platform Architect (pipeline design) + Enterprise Architect (quality gate sequence)
**Constitutional Basis:** GENESIS Engineering Quality Mandate (zero manual testing; build once, image promotion; Constitutional Compliance Tests are a required gate); GENESIS Part 02 — "Every deployment is a formal act of institutional judgment"

---

## Context

The platform needs a CI/CD pipeline that:
- Builds and tests every pull request
- Promotes images through dev → QA → UAT → production without rebuilding
- Runs Constitutional Compliance Tests as a mandatory gate
- Never deploys to the next environment unless the current environment's gates pass
- Supports the cost constraint (no always-on QA infrastructure — scaled to zero when idle)

## Decision

**GitHub Actions as the CI/CD platform. Trunk-based development (main branch only). Image promotion via `docker tag` retagging. Constitutional Compliance Tests are a required gate before any environment promotion.**

### Branch Strategy

```
Trunk-based development:
  - main branch is always deployable
  - Feature work: short-lived feature branches (max 2 days)
  - PRs merge into main after: build passes + tests pass + code review
  - No long-lived release branches
  - No staging branches
```

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│ PR Pipeline (runs on every PR to main)                          │
│  1. Build all 5 images (tag: sha-{git-sha})                     │
│  2. Unit tests (.NET xUnit, Python pytest)                      │
│  3. OpenAPI spec conformance (Spectral lint)                    │
│  4. Security scan (Trivy — image vulnerability scan)            │
│  5. Push images to GHCR (tag: sha-{git-sha})                    │
│  PR is blocked from merge if any step fails                     │
└─────────────────────────────────────────────────────────────────┘
           ↓ PR merged to main
┌─────────────────────────────────────────────────────────────────┐
│ Dev Deployment (automatic on merge to main)                     │
│  1. Retag: sha-{git-sha} → :dev                                 │
│  2. Deploy to dev Container Apps environment                    │
│  3. Run EF Core Migrations (init container)                     │
│  4. Integration tests against live dev stack                    │
│  5. Constitutional Compliance Tests (CCTs) — mandatory gate     │
│     - Evidence First: validate evidence recorded before return  │
│     - Human Override ≤250ms: measure Emergency Stop round-trip  │
│     - PAAS Boundary: verify no out-of-space actions executed    │
│     - Audit Ledger Immutability: verify no update/delete on ledger│
│     - Multi-tenant isolation: cross-tenant data access = 0      │
│  Dev deployment status posted to PR comments                    │
└─────────────────────────────────────────────────────────────────┘
           ↓ All CCTs pass
┌─────────────────────────────────────────────────────────────────┐
│ QA Promotion (automatic after dev CCTs pass)                    │
│  1. Retag: :dev → :qa                                           │
│  2. Deploy to QA Container Apps environment                     │
│  3. Run EF Core Migrations                                      │
│  4. Full test suite (integration + CCTs + contract tests)       │
│  5. schemathesis OpenAPI contract tests against live QA API     │
└─────────────────────────────────────────────────────────────────┘
           ↓ Manual approval gate (Founder or designated reviewer)
┌─────────────────────────────────────────────────────────────────┐
│ UAT Promotion (manual approval required)                        │
│  1. Retag: :qa → :uat                                           │
│  2. Deploy to UAT Container Apps environment                    │
│  3. Run EF Core Migrations                                      │
│  4. CCTs (constitutional compliance must pass in UAT)           │
└─────────────────────────────────────────────────────────────────┘
           ↓ Manual approval gate (Founder)
┌─────────────────────────────────────────────────────────────────┐
│ Production Promotion (manual approval required)                 │
│  1. Retag: :uat → :prod                                         │
│  2. Deploy to production Container Apps environment             │
│  3. Run EF Core Migrations                                      │
│  4. Smoke tests only (CCTs run in UAT, not repeated in prod)    │
└─────────────────────────────────────────────────────────────────┘
```

### GitHub Actions Workflow Files

```
.github/workflows/
  pr.yml           — PR pipeline (build, test, push sha image)
  deploy-dev.yml   — Dev deployment (triggered by merge to main)
  deploy-qa.yml    — QA promotion (triggered by dev CCT pass)
  promote-uat.yml  — UAT promotion (manual approval)
  promote-prod.yml — Production promotion (manual approval)
```

### Constitutional Compliance Tests (CCTs)

CCTs are a WAOOAW-specific test category. They live in `tests/constitutional/` and run as a separate step in every environment deployment. A deployment is not "successful" until CCTs pass. CCTs are not unit tests — they test the constitutional guarantees of the running system.

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| GitFlow (develop/release/hotfix branches) | Long-lived branches cause integration debt. Violates trunk-based development discipline. |
| Azure DevOps | Redundant. GitHub Actions is already available and integrated with GHCR and the repository. |
| Jenkins | Operational overhead. Self-hosted build infrastructure. Zero justification at MVI. |
| ArgoCD / Flux (GitOps) | Kubernetes-specific. Not applicable to Container Apps at MVI. Revisit if platform migrates to Kubernetes. |

## Consequences

**Benefits:**
- Every merge to main produces a deployable, tested artifact
- Constitutional Compliance Tests are architecturally enforced as a gate — they cannot be skipped
- Image promotion guarantees the exact artifact tested in dev is what runs in production
- Manual approval gates for UAT and production satisfy constitutional governance requirement

**Trade-offs:**
- CCT runtime adds ~2-3 minutes to every dev deployment
- Trunk-based development requires discipline — long-running features need feature flags
- Manual approval gates for UAT and production require a human to be available for every release

**Cost:**
- GitHub Actions free tier: 2,000 minutes/month for private repos. At MVI commit frequency (10-20 commits/day), estimated at ~400 minutes/month. Well within free tier.
