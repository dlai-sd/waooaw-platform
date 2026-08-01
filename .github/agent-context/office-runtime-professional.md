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

## MagicLLM Pipeline Gates (ADR-038 — what the platform does to your output)
Every file the LLM writes passes through 5 gates IN ORDER before being accepted:

| Gate | What it checks | Failure → |
|------|---------------|-----------|
| FORMAT | `<file path="...">` block present | rejected immediately, no retry |
| PATH | file written to exact path in TASK spec | rejected immediately |
| COMPILE | stack tool exits 0 (see table below) | 2 retries with error injected |
| ANNOTATION | `# Implements:` + `# constitutional_basis:` in first 10 lines | retry |
| SPEC_ALIGN | no types invented outside SPEC block | retry |

### COMPILE gate per stack

| Stack | Inner (inside 3-retry loop) | Outer (after GoalExecutor) |
|-------|-----------------------------|---------------------------|
| Python `.py` | py_compile (syntax) + ruff check (style) | ruff check + --fix |
| .NET C# `.cs` | dotnet build | dotnet_build gate |
| TypeScript `.ts/.tsx` | tsc --noEmit --strict + biome check | none |
| SQL `.sql` | sqlfluff lint --dialect postgres | sqlfluff gate |
| YAML `.yaml/.yml` | yamllint -d relaxed | yamllint gate |
| Terraform `.tf` | hcl2 parse (syntax) | terraform_validate gate |

### Python ruff constraints (enforced automatically — see context_builder.py `_PYTHON_FORBIDDEN_PATTERNS`)
- `ANN201` Every public function needs `-> ReturnType`
- `ANN001` Every parameter needs a type annotation
- `B017` Never `pytest.raises(Exception)` — use specific type
- `B006` Never mutable defaults — use `| None = None` sentinel
- `F841` Never unused variables — prefix with `_` or use in assertion
- `B018` Never bare expressions as statements
- `G004` Never f-strings in logging — use lazy `%s` format

### Lint-violations learning cache
Failed violations are written to `sprint-context/lint-violations.json`.
The pipeline reads this file at prompt time and injects violation history into the SYSTEM slot.
First violation occurrence creates the entry. Subsequent sprints see it in SYSTEM and avoid it.
Zero-cost self-improvement: no extra LLM call required.

### work_item_type field in SubTaskDef
The `work_item_type` field on SubTaskDef controls context injection:
- `GREENFIELD` — empty file, full spec injected (new service files)
- `DEFECT_FIX` — existing file content injected as EXISTING_FILE slot (bug fixes)
- `ENHANCEMENT` — existing file + diff hints injected (adding to existing code)
- `PRODUCTION_FIX` — hot-path: reasoning model forced, max_tokens=8000

## Commit format
feat(ce|bp|pr|ai|web|infra|db|cct): description
constitutional(service): implements a constitutional principle
cct(service): CCT-XX-NN passing
Update constitution/PROJECT_STATE.md IN-PROGRESS CHECKPOINT after each commit.

## PR checklist
Use .github/pull_request_template.md. Fill all sections. Request review:
"@copilot review this PR as the Enterprise Architect"
Never merge your own PR.
