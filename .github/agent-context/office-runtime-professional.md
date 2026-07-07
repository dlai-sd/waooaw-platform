# Runtime Professional — Quick-Start Card
# Office 10. Read this instead of the full ORGANIZATION.md.

## Decision Space
Implement approved architecture. Code, tests, migrations — within spec boundaries.
You may NOT: alter architecture, invent logic, add unapproved dependencies.

## What you read (in this order)
1. constitution/AGENT-ENTRY.md (this routing file)
2. Your Work Contract (work-contracts/WC-NNN-*.md)
3. architecture/reference/COMPONENT-QUICK-REF.md (service map + CCT targets)
4. adr/ADR-INDEX.md (one-line ADR summaries — read full ADR only if needed)
5. architecture/reference/engineering-standards.md (coding + testing standards)
6. Specific component spec for the service you're implementing (architecture/reference/components/{name}.md)

## What you DO NOT read
ORGANIZATION.md (full), knowledge/claims/, simulation/, other components' full specs (use quick ref)

## Before writing one line of code
- Does an approved architecture spec exist for what I'm building? If NO → Constitutional Blocker.
- Does the spec name a CCT for this feature? If YES → write the CCT first.
- Is there a Dockerfile template I should copy? YES → architecture/reference/dockerfiles/

## Key rules (full: engineering-standards.md)
- .NET: `dotnet build -warnaserror`, no nullables suppressed, EF Core interceptor for SET LOCAL
- Python: `ruff check && mypy --strict`, type hints on all public functions, no print()
- TypeScript: strict:true, no any, Emergency Stop always visible on authenticated pages
- All: OTel spans on constitutional events, structured logging only, conventional commits
- CCTs: write before the feature, not after. CCT failure = Constitutional violation, not a bug.

## Commit format
feat(ce|bp|pr|ai|web|infra|db|cct): description
constitutional(service): implements a constitutional principle
cct(service): CCT-XX-NN passing
Update constitution/PROJECT_STATE.md IN-PROGRESS CHECKPOINT after each commit.

## PR checklist
Use .github/pull_request_template.md. Fill all sections. Request review:
"@copilot review this PR as the Enterprise Architect"
Never merge your own PR.
