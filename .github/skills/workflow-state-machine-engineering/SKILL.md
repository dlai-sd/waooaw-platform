---
name: workflow-state-machine-engineering
description: "Use when: changing or diagnosing GitHub Actions control flow, YAML/Bash conditions, dependency graphs, transition outputs, cache branches, reruns, or required reconciliation steps."
---

# Workflow Control-Flow and State-Machine Engineering

## Required method

1. Enumerate the states and boolean outputs that control the affected path.
2. Build a truth table covering fresh, interrupted, completed, rerun, cache-hit, cache-miss, apply, and plan states.
3. Separate one-time transition actions from reconciliation actions that must run on every deployment.
4. Trace every state to the exact workflow job and step conclusion: success, failure, or skipped.
5. Add executable contract tests for every meaningful branch, including the completed-transition rerun.
6. Lint the workflow and run the smallest affected test suite before any hosted run.

## Evidence

- State table and owning conditions
- Expected step conclusion for each state
- Tests that fail when a required reconciliation step is skipped
- Workflow lint result

## Stop conditions

Stop if a required action depends on an unrelated transition flag, an unknown state is treated as success,
or the workflow can reach migration or activation without its prerequisites.
