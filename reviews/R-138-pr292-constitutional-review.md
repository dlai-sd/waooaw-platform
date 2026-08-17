# R-138 - PR #292 Independent Constitutional Review

| Field | Value |
|---|---|
| `institution_id` | `INST-002` |
| `review_id` | `R-138` |
| `record_type` | Independent Constitutional Implementation Review |
| `reviewed_at` | `2026-08-17` |
| Pull request | `#292` - Fix CI workflow job conditions |
| Reviewed commit | `09e584755d4938f6073aaaa38fe9b4d505f8c79f` |
| Base | `main` at `c18a3d84db280f443c06f3520e89365e9bf06149` |
| Verdict | **REJECT** |
| Blocker | `CB-007` |

## Scope And Independence

This review was produced by a fresh, read-only INST-002 review context that did not author the
implementation, execute its repair campaign, approve the specification, deploy the result, or
exercise merge authority. The incorporating session changed only this review and its blocker
record. This preserves C-065 separation. The review does not approve or merge PR #292.

The exact reviewed range contains 123 files, 5,660 additions, 1,263 deletions, and 13 commits across
CI, dependency manifests, architecture reference files, proto configuration, production source,
tests, and Web migration work.

## Findings

### P0 - No Valid Implementation Authority Or Fail-Closed Authorization Gate

[WC-075](../work-contracts/WC-075-goal-007-qa-test-champion-intake.md) authorizes GOAL-007 intake
and planning only and expressly excludes test execution, source changes, PR approval, and merge.
[GOAL-007 execution plan](../goals/GOAL-007-execution-plan.md) requires separate explicit authority
for Phase 2 tooling changes and Phase 3 pilot testing. No co-committed Work Contract, GO
Authorization, Acceptance, or Founder current-session implementation authorization covers the
complete PR #292 implementation scope.

The C-066 workflow gate succeeds when authorization labels are absent. The C-059 gate validates
commit subjects and accepts a `FIX:` token without requiring both a governing work identifier and
constitutional claim. Therefore the green C-059 and C-066 jobs do not prove authorization or full
traceability for this PR. This violates C-059, C-066, BOOTSTRAP Step 10b, and GEOM G-7.

### P0 - C-080 Docker-Only Test Execution Is Violated

[CI](../.github/workflows/ci.yaml) correctly runs the Professional Runtime and AI Runtime Python
suites in the Docker test runner. It still runs both .NET test projects directly on the GitHub host,
installs cross-stack Python dependencies on that host, and runs Web Jest directly on the host.
C-080 applies to every automated test, including xUnit and Jest, on GitHub Actions runners. Green
results from a prohibited execution environment are not constitutionally admissible verification.

### P1 - Voice Orchestration Loses The Accepted AIR Transcription Identifier

In [voice orchestration](../src/professional-runtime/routers/voice_orchestration.py),
`HttpAirTranscriptionClient.start()` returns `AirTranscriptionResponse`, but that model has no
`transcriptionId` field. The route subsequently indexes the returned value as
`air["transcriptionId"]`. The real HTTP path therefore raises after AIR accepts the request and
before the orchestration is retained locally. Dict-returning route fakes conceal the mismatch.
This is a production regression and a C-023 reconciliation/evidence risk.

### P1 - PR Scope Declaration Is Materially Inaccurate

The PR body states that the change repairs workflow dispatch only. The reviewed range changes 123
files across runtime source, security dependency pins, architecture references, proto files, tests,
and a Next.js migration. The body does not provide an accurate traceability matrix or disclose the
actual risk surface. It must be corrected before informed Founder review.

### P2 - Security Exceptions Lack Governed Disposition

CodeQL, dependency checks, and all six Trivy image scans passed at the reviewed SHA. The workflow
nevertheless suppresses `PYSEC-2026-1325` and `PYSEC-2026-139` without recording a risk owner,
rationale, expiry, or remediation condition. One advisory was reported as ignored. C-062 requires
an explicit governed disposition rather than an unexplained permanent exception.

### No Blocking Proto Or Reference Drift Found

The dependency reference dotfiles align with runtime manifests. Proto edits preserve public message
names and field numbers, and the pinned Buf format, lint, and breaking checks passed. The co-commit
mechanics for these files are acceptable, subject to the missing authority above.

## Evidence Checked

- Git range `origin/main...09e584755d4938f6073aaaa38fe9b4d505f8c79f` and all 13 commits.
- GitHub Actions run `32015597413`, bound to the reviewed SHA: all jobs passed.
- Constitutional Engine: 176 tests; 90.45% line and 93.27% branch coverage.
- Business Platform: 426 tests; 90.46% line and 80.30% branch coverage.
- Professional Runtime: 178 tests; 90.08% line and 80.66% branch coverage.
- AI Runtime: 61 tests; 90.60% line and 82.09% branch coverage.
- Web: 111 tests; configured 90% line and 80% branch thresholds passed.
- Six image builds and six Trivy scans, CodeQL, dependency scan, secret scan, and Test Champion passed.
- Focused cursor boundary test was stress-run 100 consecutive times by the repair session.

## Completeness Ledger

| Obligation | Result | Basis |
|---|---|---|
| C-023 Evidence First | **FAIL** | AIR acceptance can escape local orchestration retention |
| C-059 Traceability | **FAIL** | No implementation authority; token-only commit gate |
| C-062 AI Security | **PASS WITH OPEN RISK** | Scans green; ignored advisories lack governed disposition |
| C-065 SDLC Separation | **PASS FOR REVIEW** | Fresh independent review; merge remains Founder-controlled |
| C-066 Authorization | **FAIL** | Missing authority and fail-open no-label behavior |
| C-076 Coverage | **PASS** | All five enumerated platform services meet the 90% line floor |
| C-080 Docker Execution | **FAIL** | .NET and Web tests execute on the host runner |
| ADR-013 CI/CD | **FAIL** | Passing jobs do not enforce the controlling constitutional gates |

The added 80% branch thresholds are permissible quality controls and do not weaken C-076. The
current C-076 text enumerates five services and does not include Billing Engine; extending that
constitutional obligation requires a claim amendment rather than reviewer inference.

## Required Resolution

1. Record explicit current-session implementation authority covering the complete PR scope, with
   valid Work Contract, GOA, Acceptance, and constitutional traceability.
2. Make C-059 and C-066 fail closed when required work identifiers, claims, labels, or approvals
   are absent.
3. Execute every automated test through Docker as required by C-080.
4. Repair and integration-test the AIR transcription identifier contract.
5. Rewrite the PR title/body and traceability matrix to describe the complete changed scope.
6. Record governed dispositions for ignored security advisories.
7. Obtain a fresh independent review against the repaired head SHA.

## Verdict

**REJECT.** CB-007 blocks merge of PR #292. The branch is technically green but is not
constitutionally merge-ready. The Founder must not merge until every required resolution is closed
and a fresh independent review approves the repaired SHA.