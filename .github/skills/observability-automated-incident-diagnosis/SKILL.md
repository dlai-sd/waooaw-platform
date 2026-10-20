---
name: observability-automated-incident-diagnosis
description: "Use when: a GitHub Actions or Azure deployment failure lacks its underlying exception, execution identity, sanitized logs, endpoint metadata, or deterministic failure classification."
---

# Observability and Automated Incident Diagnosis

## Required method

1. Correlate GitHub run, job, step, Azure resource, ACA execution, replica, and image digest.
2. Capture execution state and bounded container/system logs before cleanup.
3. Emit the execution ID immediately when an asynchronous job starts.
4. On failure, print sanitized underlying logs in the owning GitHub step and upload structured evidence.
5. Classify the first causal failure as workflow, identity, secret, DNS, TCP, TLS, database, product, or evidence.
6. Preserve failed evidence through always-run cleanup and artifact upload paths.

## Evidence

- Correlation tuple for GitHub and Azure execution
- Sanitized container traceback or platform error
- Structured status, endpoint, and health-check record
- First-cause classification and owning component

## Stop conditions

Stop if only an aggregate status such as `Failed` is available. Retrieve the owning execution evidence
before proposing a root cause or retrying the deployment.
