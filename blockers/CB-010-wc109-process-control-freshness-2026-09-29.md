# CB-010 - WC-109 Process-Control Freshness Failure

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-010` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-09-29` |
| Status | **OPEN** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-109 Stage 0 intake, strategic plan and implementation |
| Constitutional basis | C-023, C-059, C-065, C-080; Platform IT Expert v1.3.6 process intake |
| Resolution authority | Founder for scope; Platform IT Expert for an explicitly authorized deterministic repair |

## Blocking Fact

The authorized branch `wc/109-agentic-validation-implementation` was created cleanly from
`origin/main` at `b55e1323ea1a83997ad13e604a77999536bebb43`. The merged Platform IT Expert
v1.3.6 compact card requires every source declared by `validation/process-control.yaml` to match
its recorded SHA-256 before an implementation plan or story may begin.

The process-control check fails for the compact office card:

| Source | Recorded SHA-256 | Actual SHA-256 at WC-109 base |
|---|---|---|
| `.github/agent-context/office-platform-it-expert.md` | `ad2ddfec073d06173b4410425ee29a93500edbfa74e15130f6df684d3ebd4a74` | `29cd9fc931988755cdfdc872b0a716b71a9aa589411779469c6ca43f8ee879b4` |

The recorded digest identifies the office card at `ff09197debf331a75d8f50bb6a817a683544ed33`.
PRs #476 and #480 subsequently changed the card without updating the process-control digest. The
other two declared source digests pass.

## Gate Effect

- WC-109 requirements remain `PLANNED`.
- Docker ledger validation, baseline recording and implementation stories have not started.
- No host test tooling, virtual environment, image build, cloud action or selective hosted validation
  was used.
- The unrelated dirty worktree at `/workspaces/waooaw-platform` remains untouched.

## Required Resolution

Authorize and merge a bounded process-control baseline repair, or explicitly include that deterministic
repair in WC-109 Stage 0. The repair must update the compact-card digest to the exact accepted v1.3.6
content, preserve the other declared digests, pass the process-intake and requirement-ledger gates through
the catalog-controlled Docker route, and establish freshness before the strategic implementation plan is
published.

Changing or bypassing the check silently is prohibited.