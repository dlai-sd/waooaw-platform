---
name: deployment-qualification-fault-injection
description: "Use when: qualifying deployment changes locally, testing failure paths, or reproducing skipped stages, stale secrets, placeholders, unreachable endpoints, and missing evidence before a full workflow run."
---

# Deployment Qualification and Failure-Injection Testing

## Required method

1. Convert the observed defect into a falsifiable local test before changing behavior.
2. Add state-path tests for skipped and executed workflow branches.
3. Inject stale versions, unresolved placeholders, denied identities, DNS failures, TCP timeouts, and absent artifacts.
4. Run static contracts first, then exact-container tests, dependency-complete rehearsal, and one frozen-candidate qualification.
5. Reject retries of unchanged failures; repair the owning input before rerunning.
6. Start a hosted deployment only after the complete affected closure passes locally.

## Evidence

- Reproducing test that fails before the fix
- Focused passing suite after the fix
- Workflow lint, Terraform validation, and manifest verification
- Exact frozen candidate SHA and affected dependency closure

## Stop conditions

Stop before a paid or hosted run when any local reproduction, negative-path test, manifest check, or
dependency-complete rehearsal is failing or has not been executed.
