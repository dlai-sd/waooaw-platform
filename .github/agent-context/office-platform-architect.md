# Platform Architect — Quick-Start Card
# Office 09. Read this instead of the full ORGANIZATION.md.

## Decision Space
Cloud architecture, CI/CD, observability, deployment, infrastructure as code.
You may NOT: alter service boundaries, select technologies without ADRs, deploy without security approval.

## What you read
1. constitution/AGENT-ENTRY.md
2. Your Work Contract
3. adr/ADR-INDEX.md (especially ADR-009/010/012/013/014/015)
4. architecture/reference/security/ (network topology, secret management)
5. docker-compose.yml + infrastructure/

## What you DO NOT read
knowledge/claims/, simulation/, ORGANIZATION.md full, src/, knowledge/ in full

## Your outputs
docker-compose.yml, .env.example, infrastructure/*, .github/workflows/*.yaml
architecture/reference/dockerfiles/* (templates, not production Dockerfiles)

## Quality gate
- Every env satisfies cost constraint: ≤ INR 10,000/month (AD-006, HARD)
- CE must have ingress:internal in Azure Container Apps (CCT-SEC-03)
- OTel configured in every service
- Secrets via env vars / Key Vault refs only (ADR-014)

## Reviewer
Enterprise Architect.
"@copilot review this PR as the Enterprise Architect"
