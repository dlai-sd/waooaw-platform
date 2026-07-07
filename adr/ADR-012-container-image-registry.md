# ADR-012: Container Image Registry

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Platform Architect (build and release pipeline) + Enterprise Architect (cloud portability alignment)
**Constitutional Basis:** GENESIS Engineering Quality Mandate (image promotion — build once, tag `:sha`, retag through environments; a new build must never be created for each environment); ADR-010 (Cloud Provider Portability — registry must not create Azure dependency)

---

## Context

Every service is packaged as a container image. Images must be stored in a registry that:
- Is accessible during CI builds (push)
- Is accessible during deployments to dev, QA, UAT, and production environments (pull)
- Supports the image promotion model (single `sha`-tagged image retagged through environments)
- Does not add unnecessary cost or Azure dependency

## Decision

**GitHub Container Registry (GHCR) as the single image registry for all environments.**

```
Build (GitHub Actions):
  docker build → ghcr.io/dlai-sd/waooaw-business-platform:sha-abc123
  docker build → ghcr.io/dlai-sd/waooaw-constitutional-engine:sha-abc123
  docker build → ghcr.io/dlai-sd/waooaw-professional-runtime:sha-abc123
  docker build → ghcr.io/dlai-sd/waooaw-ai-runtime:sha-abc123
  docker build → ghcr.io/dlai-sd/waooaw-web:sha-abc123

After dev tests pass:
  docker tag sha-abc123 → :dev

After QA tests pass:
  docker tag :dev → :qa

After UAT approval:
  docker tag :qa → :uat
  docker tag :uat → :prod   ← production deployment
```

**Image naming convention:**
```
ghcr.io/dlai-sd/waooaw-{service-name}:{tag}

Tags:
  sha-{7-char-git-sha}   — immutable, created once at build
  dev, qa, uat, prod     — environment pointers (mutable, always point to latest promoted sha)
```

**Authentication:**
- GitHub Actions uses `GITHUB_TOKEN` (automatic, zero configuration) to push to GHCR
- Azure Container Apps pulls from GHCR using a GitHub Personal Access Token (PAT) with `read:packages` scope, stored as an Azure Container Apps secret (see ADR-014)

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Azure Container Registry (ACR) | ~₹400-1,600/month (Basic/Standard tier). Creates Azure dependency for a non-Azure-specific concern. GHCR is free for public and private repos on the current GitHub plan. ADR-010 prohibits new Azure-specific dependencies where a portable alternative exists. |
| Docker Hub | Free tier has pull rate limits (100 pulls/6 hours for unauthenticated). Rate limits on CI/CD pipelines cause intermittent failures. Paid tier is ~$7/month/user. GHCR has no pull rate limits for authenticated users. |
| Self-hosted registry | Operational burden. Storage, availability, and security management. Zero justification at MVI. |

## Consequences

**Benefits:**
- Free — zero cost at MVI scale
- No Azure dependency — the registry works with any cloud provider (portability alignment with ADR-010)
- Integrated with GitHub Actions authentication — no secrets needed for CI to push images
- Image immutability at `sha` level — the `sha-abc123` tag is never overwritten

**Trade-offs:**
- Azure Container Apps requires a PAT or service account to pull from GHCR (not as seamless as ACR's managed identity)
- PAT has an expiry — must be rotated before expiry (managed in ADR-014)
- If the repository is made private, GHCR images are private by default — pull authentication is required in all environments including dev

**Registry access in dev:**
```bash
# Developers authenticate once:
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```
The `.env.example` file includes the instruction but never the token value.
