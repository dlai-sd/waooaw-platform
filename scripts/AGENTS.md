# AGENTS.md — scripts/ Context
# FinOps Pattern 2: Scoped context for scripts/ work
# constitutional_basis: C-059 (Traceability), C-066 (Authorization), C-076 (Coverage)

## Your Role Here
You are WAOOAW AI Agent — Platform IT Expert working on automation scripts.

## Primary Spec Files (load these — nothing else)
- `standards/CODING-STANDARDS.md` §3 (Python) + §7.5 (Coverage C-076)
- `constitution/AGENT-ENTRY.md` — current sprint task context
- `sprint-context/index.json` — CURRENT TASK ONLY

## Script Conventions
All scripts in this directory must:
1. Have a header comment with `constitutional_basis:` and `ib_item:`
2. Never print secrets, tokens, or credentials
3. Be idempotent where possible (re-runnable without side effects)
4. Have ≥90% unit test coverage (C-076)

## Coverage Obligation (C-076)
- `seed-prompts.py`: idempotency path tested (run twice → same result)
- `autonomous_sprint_runner.py`: each task function tested
- `build_sprint_index.py`: index generation for each known task ID tested
- `scan-traceability.py`: tested against known-good and known-bad src/ fixtures

## Security Rules (OWASP)
```python
# NEVER: subprocess with shell=True and user-provided input
subprocess.run(f"git {user_input}", shell=True)  # FORBIDDEN — shell injection

# ALWAYS: use list form for subprocess
subprocess.run(["git", "commit", "-m", message], check=True)  # SAFE

# NEVER: hardcoded credentials or tokens
API_KEY = "sk-..."  # FORBIDDEN — use environment variables

# ALWAYS: secrets from environment
token = os.environ["GITHUB_TOKEN"]  # SAFE — validated at boundary
if not token:
    raise ValueError("GITHUB_TOKEN not set")
```

## Scripts Index
| Script | Purpose | Model Hint |
|---|---|---|
| `autonomous_sprint_runner.py` | Execute sprint tasks (Platform IT Expert Implementation hat) | reasoning |
| `autonomous_sprint_reviewer.py` | Review PR (Platform IT Expert PR Review hat) | reasoning |
| `build_sprint_index.py` | Pre-compute sprint context index (FinOps RAG) | auto |
| `sprint_state.py` | Update SPRINT_STATE_MACHINE fields | auto |
| `scan-traceability.py` | Verify C-059/C-073 annotations in src/ | auto |
| `seed-prompts.py` | Seed agent prompts from .md files to PostgreSQL | auto |
| `setup.sh` | Dev environment setup | — |
| `get-dev-token.sh` | Get dev Keycloak JWT | — |
