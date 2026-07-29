# SIM-PL-002 — WC015-04 Prompt Injection Defence + CCT-PI-01
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC015-04 — 50-attack prompt injection defence (C-062), 100% pass rate
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Implements input sanitisation layer that blocks 50 known prompt injection attack patterns.
50 attack vectors exist in tests/conftest.py (PROMPT_INJECTION_ATTACKS).
C-062 mandates 100% block rate for known attacks. Pattern: regex + semantic checks.
Stack: Python 3.12. Constitutional: C-062 (AI security), C-063 (PII minimisation).

## Subtask Decomposition
WC015-04a (llm, reasoning) — prompt_guard.py: 50-pattern defence rules → ruff → PASS
WC015-04b (llm, reasoning) — CCT-PI-01: parametrised pytest over all 50 attacks → ruff → PASS

## Dependency Graph
WC015-04a: depends_on=[WC015-01b]
WC015-04b: depends_on=[WC015-04a]

## Risk Assessment
- Attack patterns in tests/conftest.py: PROMPT_INJECTION_ATTACKS list exists — LLM has context
- 100% block rate: defence uses allow-list + regex deny-list approach — deterministic
- C-062 compliance: `# constitutional_basis: C-062` required in every defence file — checked by ANNOTATION gate
- PII scrubber (C-078): defer to WC015-05 if needed, scope bounded to prompt guard here

## Verdict

**VERDICT: ✅ PASS**
