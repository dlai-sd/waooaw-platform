# ADR-050 - AI-Operated Docker Validation

**Status:** Accepted by Founder - 2026-09-19
**Date:** 2026-09-19
**Author:** Chief Enterprise Architect (INST-004)
**Work Contract:** WC-101
**Constitutional Basis:** C-059, C-065, C-071, C-076, C-077, C-080 and C-086
**Related Decisions:** ADR-012, ADR-013, ADR-037, ADR-038 and ADR-045
**Amends:** ADR-045 execution and evidence model; preserves its per-stack image boundaries

## Context

ADR-045 reduced image size and dependency blast radius by separating Python, .NET and TypeScript
test runners. WAOOAW's remaining delay is above that image boundary: runners are rebuilt repeatedly,
source changes and environment changes are not separate identities, test impact is encoded in several
places, some workflows bypass Docker-only execution, and failures are primarily returned as raw logs.

WAOOAW is operated by AI agents. Its test architecture must minimize repeated environment work and
return deterministic failure evidence without weakening constitutional gates or allowing local,
cached or stale state to authorize PASS.

## Decision

WAOOAW adopts the following validation architecture:

1. **One validation catalog.** A versioned machine-readable catalog owns path ownership, direct
   gates, reverse dependencies, runner identity, command identity, resources and evidence format.
   Unknown impact fails closed to the current full applicable gate set.
2. **Environment images are independent of source edits.** Per-stack runner images are published by
   immutable digest from Dockerfile, base image and dependency inputs. Application source does not
   trigger runner rebuild.
3. **Two modes use one test definition.** Focused mode mounts the current workspace into a disposable
   runner and produces local feedback. Qualification mode executes the same catalogued command for
   an exact commit with clean state and produces trusted PR/release evidence.
4. **Caches accelerate but never authorize.** Package and compiler caches may persist by namespace.
   Databases, fixtures, browser state and test processes are disposable. Prior results are reusable
   only as immutable evidence when every declared input identity matches.
5. **Every node emits structured evidence.** Framework-native artifacts are accompanied by a bounded,
   sanitized result envelope naming the exact source, runner digest, gate, duration, result, first
   causal failure class and raw-artifact references.
6. **Gates run by cost and dependency.** Static and focused checks precede affected integration,
   browser, security and CCT checks. Independent nodes may run concurrently with isolated resources.
   Full clean qualification runs once for the frozen candidate and remains mandatory on `main` and
   release paths.
7. **Docker-only execution is machine-enforced.** Host test commands, test dependency installation,
   virtual environments and unapproved root execution fail a policy gate. Docker socket access is
   limited to explicitly classified Testcontainers runners.
8. **Selective PR validation activates only after shadow proof.** Current full PR CI remains
   authoritative while impact selection is compared against it. Enforced selection requires zero
   unresolved false negatives and separate Founder approval.

The detailed contract is `architecture/reference/docker-only-validation-strategy.md`.

## Alternatives Considered

| Alternative | Decision |
|---|---|
| Keep rebuilding Compose runners for each command | Rejected: simple but repeats dependency and image work unrelated to source changes |
| One persistent runner per agent using `docker exec` or `docker cp` | Rejected: fastest warm loop but retained process, filesystem, environment and database state can create false passes |
| Bake every source revision into every test-runner image | Rejected: conflates environment and source identity and forces image rebuild after each edit |
| Run language tools directly on the Codespace or GitHub host | Rejected: violates C-080 and creates a second execution environment |
| Adopt a third-party test-impact platform | Deferred: adds cost, authority and supply-chain complexity before existing GitHub Actions, GHCR and Docker capabilities are exhausted |
| Run only the complete suite after every edit | Rejected: safe but wasteful; focused feedback plus one clean frozen-candidate qualification preserves safety with lower turnaround |

## Consequences

### Positive

- Code-only changes do not rebuild runner images.
- Agents receive the first causal failure and exact reproduction identity from the original run.
- Local speed cannot be confused with trusted qualification evidence.
- Test applicability has one reviewable, fail-closed source instead of duplicated path logic.
- Full constitutional, coverage, security and release gates remain intact.

### Negative

- The validation catalog and evidence schema become governed artifacts that require maintenance.
- Runner publication and cache namespaces add CI lifecycle work.
- Shadow evaluation delays activation of selective CI.
- Some currently fast host commands become containerized and may initially expose hidden dependency
  or networking defects.

### Risks And Controls

| Risk | Control |
|---|---|
| Incorrect impact selection | Transitive reverse dependencies, global triggers, shadow comparison and full fallback |
| Stale or poisoned cache | Cache is acceleration only; exact identities and clean correctness state |
| Evidence substitution | Full source SHA, runner digest, schema validation and trusted CI boundary |
| Concurrent collision | Unique Compose project, network, volume, port and output namespaces |
| Docker socket escalation | Socket only for classified Testcontainers runners; non-root default and bounded resources |
| Faster feedback weakens gates | Same catalogued commands and thresholds; complete `main` and release safety nets |

## Compatibility And Migration

ADR-050 does not change service APIs, runtime containers, customer data or deployment architecture.
It retains ADR-045's lean runners and ADR-013's build-once immutable release model.

Migration proceeds through compliance repair, digest-addressed runner supply, common evidence,
shadow impact selection and separately approved enforcement. Every phase can roll back to full clean
qualification without accepting stale evidence.

## Acceptance Evidence

The implementation Work Contract must require executable proof that:

- all tests and test-language tooling execute in Docker;
- code-only changes cause zero runner rebuilds;
- focused and qualification modes resolve to the same catalogued test definitions;
- every declared identity input invalidates the correct cache or evidence;
- unknown impact selects full applicable validation;
- structured failure evidence is emitted without secrets or customer data;
- concurrent runs cannot collide; and
- shadow selection has zero unresolved false negatives before activation.

## Decision Authority

The Founder accepted this ADR on 2026-09-19. Enterprise Architecture author review remains
self-verification, not approval. Acceptance of this decision does not authorize implementation under
ADR-050 or WC-101.
