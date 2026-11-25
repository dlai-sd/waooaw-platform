# WC-170 Agent Execution Instructions

**For:** any WAOOAW agent session that builds WC-170 after the Founder authorizes it.
**Status:** accepted when the Founder merges the WC-170 grooming pull request.
**Controlling documents:** [WC-170](./WC-170-real-agent-work-end-to-end.md), [ae02-real-work-solution-contract.md](../architecture/reference/product/ae02-real-work-solution-contract.md), [WC-170-requirements.yaml](./WC-170-requirements.yaml), [ROADMAP.md](../ROADMAP.md).

## 1. Gate before anything else

1. Do not start bootstrap or write code on your own. Follow `.github/copilot-instructions.md`: bootstrap runs only when the Founder asks for it.
2. Before creating any file in `src/`, ask exactly: "This would begin writing implementation code. Do you authorize this for the current session?" and wait. The grooming merge accepts the stories; it does not authorize the build.
3. Any change to iteration order, scope or numbering is a deviation: stop and follow `ROADMAP.md` section 8.

## 2. Plan first, then proceed

1. Read in this order: `constitution/AGENT-ENTRY.md`, `ROADMAP.md`, WC-170, the controlling specification, the ledger, then only the code in the work package you are on.
2. Create a todo list from the six work packages (WP1 to WP6) and their stories. Record dependencies between them. Do not infer dependencies from order.
3. Check preconditions read-only and write the result in the Implementation Record before coding: the employment protocol setting, the admitted DMA version, the model key status and the conversation tables. A precondition that cannot be read is reported, never assumed.
4. Implement **all** stories first. Tell the Founder briefly at each work package boundary, in plain language, what is done.

## 3. How to decide and whom to ask

- You decide every technical point. Do not ask the Founder technical questions. Pick the option that fits the specification and the repository's existing pattern, and record the decision in the Implementation Record.
- Ask the Founder only for the reserved items in WC-170 (build authorization, AI provider key, web conversation switch, domain wording, `AD_BOOST`, deploy).
- If you need other expertise, call an office once for a focused review and repair pass (Solution Architect or Enterprise Architect) with a single, specific request: what to review, which files, what to return. Do not delegate implementation to sub-agents, and review the diff yourself before you trust any returned work.
- Platform-led rule: if a story seems to need a shared-kernel change that only DMA uses, stop and ask the Founder.

## 4. Validation rule: Docker once, at the end

Do **not** run Docker tests after each story or work package. Run the consolidated pass **once** after the last story is implemented. Each repeated run costs time and money, and the one pass must be complete enough that the commit gate does not fail afterwards.

The pass must run the same commands as the commit gate and CI, in Docker only (never host Python or a virtual environment):

| Area | Commands | Notes |
|---|---|---|
| Web | `biome lint .`, `biome format .` over the whole `web` folder, `tsc --noEmit`, the full jest suite | The commit gate runs `biome format .`, not only lint. Format your changed files first: run `biome format --write <files>` as your own user so ownership is preserved |
| Business Platform | `dotnet test tests/business-platform.Tests/business-platform.Tests.csproj` with Testcontainers (`--user 0 --network host`, the Docker socket, `TESTCONTAINERS_RYUK_DISABLED=true`), then `csharpier check` on every changed C# file, then `chown` the tree back | Remove leftover test database containers before the final run |
| Billing Engine and contracts | `pytest tests/billing-engine tests/contract` plus the tests the release qualification lane lists in `scripts/run_release_qualification.sh` | If you change an API specification, run `tests/pipeline/test_wc123_impact_manifest.py` and update the recorded SHA-256 in `work-contracts/WC-123-impact-manifest.yaml`; this failed CI in PR #641 |
| Generated clients | Regenerate with the owning script when a specification changes, and run the contract tests | Both copies of a pricing specification change identically |
| Ledgers and guards | `python scripts/validate_requirement_ledger.py` for WC-170 and WC-169, `tests/pipeline/test_roadmap_single_source.py`, state refresh | Recompute `contract_digest` after every contract edit |
| Any screen you change | Render it once in Chromium from the TypeScript runner image at 1440 and 390 pixels and look at the picture | Jest cannot show layout |

Known failures that already exist on `main` and are not yours: eleven billing-engine tests (component units, lifecycle commands, baseline seed, export and import, WC-124 authority); the init-chain lint (15 findings in older files, none yours); the platform-state test that only fails inside a linked worktree. Show they fail without your change; do not hide them.

## 5. Commit and pull request

1. Run the state refresh in Docker before the final commit. In a linked worktree, mount the main `.git` at the same path and set `safe.directory=*`.
2. Commit with `git -c core.hooksPath=.githooks commit`. It runs the repository gates and takes about ten minutes; run it in the background. Use a conventional subject with a scope and the WC reference, lowercase after the colon.
3. Clean hook noise before staging again (`git checkout -- test-results`, remove untracked `test-results/wc104` and `wc109` run folders). Stage with `git add -u` plus new files, never `git add -A`.
4. Push with the token URL from the Codespace environment file without ever printing it; then unset the branch upstream.
5. Prepare the body with `scripts/prepare_pr_body.sh --body-file <absolute path> --base origin/main --expected-worktree <worktree> --expected-head <sha>`. The body follows `.github/pull_request_template.md` and states exactly what was run and what was not. It needs the Spec-Code Traceability Matrix because the build touches `src/`.
6. Open the PR, then rebind with `--update-pr N`. Do not watch CI. If CI fails, read the failing job log, fix in one commit, update the body, then push.
7. Never merge or approve. Say "Ready for Founder review and merge".

## 6. Honesty rules

- Never claim a test passed unless you ran it. State partial runs as partial.
- Never read, print or store a secret value. Never apply anything to Azure or Demo without the Founder's approval.
- Log analysis after each defect the Founder reports: read the Demo logs, append the defect to the defect list with its evidence, and confirm the list with the Founder before fixing (Founder, 2026-11-25).
- Record failures you find that are outside your scope in the contract as a gap; do not fix them silently.

## 7. Practical pitfalls from earlier work

- The edit tool replaces exact substrings. A truncated `old_str` silently drops neighbouring text, so check `git diff` after risky edits.
- Ledger YAML plain scalars must not contain `: `.
- Create a folder before creating files in it; parallel tool calls can race.
- Log Analytics caches identical queries for about two minutes; add a unique comment to each polled query.
- A Hire price, a coupon and a package are Founder run-time choices on screens; never seed or hard-code them.

## 8. Definition of done for the build

Every requirement in the ledger has executable evidence; the one Docker pass is green on the commit gate commands; the pull request body is bound to the final pushed commit; the Implementation Record lists decisions, review findings and repairs; the calibration report is produced after the Founder's single Demo deployment; the defect list is current.
