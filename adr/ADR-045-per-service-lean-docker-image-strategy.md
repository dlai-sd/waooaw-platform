# ADR-045 — Per-Service Lean Docker Image Strategy

**Status:** Accepted
**Date:** 2026-08-07
**Author:** Platform IT Expert (INST-010) + Enterprise Architect (INST-004)
**Constitutional Basis:** C-077 (Dev Cost Ceiling), C-069 (Self-Improvement), C-080 (Containerised Test Execution), C-049 (Forward-Compatible Architecture)
**Supersedes:** Implicit assumption in Dockerfile.test-runner that one image serves all test stacks

---

## Context

The platform runs tests via `docker compose run --rm test-runner` (C-080 mandate). The existing `Dockerfile.test-runner` installs three unrelated runtimes into one image:

| Runtime | Layer size | Required by |
|---|---|---|
| .NET SDK 9.0 | ~650 MB | C# Constitutional Engine tests only |
| Node.js 20.x | ~200 MB | TypeScript skeleton/web tests only |
| Python 3.12 + all pip deps | ~350 MB | Python service tests only |
| **Combined image** | **~1.5 GB** | **No sprint needs all three simultaneously** |

This caused a concrete failure on 2026-08-07: Codespaces disk at <5%, a full `--no-cache` rebuild consuming 419s, and a cache-invalidation bug where adding `respx` to `requirements-test.txt` did not bust the pip layer because BuildKit's overlay snapshot for `COPY --chown` invalidated `COPY requirements-test.txt` only when `exporting layers` committed. The bind mount at runtime masked the stale image.

More structurally, the monolithic image violates WAOOAW's customer delivery principle: **every change to any Python dep triggers a .NET SDK and Node.js download**, bloating CI time with zero-value work.

### WAOOAW Delivery Principles at Stake

- **Fastest delivery to customers**: 10-min full rebuilds block the developer feedback loop
- **Incremental builds**: one file change should rebuild only the affected stack's layer
- **Small blast radius**: a broken Node.js registry should never block a Python test run
- **Natural rollback**: rolling back a Python service image should not affect .NET or web images
- **Forward deployment**: progressive rollout requires per-service image boundaries

---

## Decision

### 1. One Dockerfile per runtime stack. No multi-runtime images.

Each Dockerfile encapsulates exactly one language runtime and its associated test/build dependencies.

**Test runners** (in `architecture/reference/dockerfiles/`):

| File | Installs | Used for |
|---|---|---|
| `Dockerfile.test-runner-python` | Python 3.12 + `requirements-test.txt` | All Python service tests (TL, AIR, BP, gateway) |
| `Dockerfile.test-runner-dotnet` | .NET SDK 9.0 + `requirements-dotnet-test.txt` | C# CE tests |
| `Dockerfile.test-runner-ts` | Node.js 20 + `package.json` | TypeScript/web tests |

The legacy `Dockerfile.test-runner` is **deprecated**. It may be retained for full-platform integration smoke tests only (profile: `test-integration`), and only when all three runtimes are exercised together.

**Production service images** already follow per-service Dockerfiles (`src/{service}/Dockerfile`). This ADR makes that pattern the explicit, mandatory standard — not coincidence.

### 2. BuildKit `--mount=type=cache` for all package managers.

Every `RUN pip install`, `RUN dotnet restore`, and `RUN npm ci` instruction MUST use a BuildKit cache mount:

```dockerfile
# Python
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-test.txt

# .NET
RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet restore

# Node
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline
```

This eliminates re-downloading packages on incremental rebuilds. The cache mount is NOT written into the image layer — it is a build-time volume shared across builds on the same host.

### 3. Registry-backed layer cache in CI (GitHub Actions).

All `docker build` calls in CI use:
```
--cache-from=type=registry,ref=ghcr.io/dlai-sd/waooaw-{image}:buildcache
--cache-to=type=registry,ref=ghcr.io/dlai-sd/waooaw-{image}:buildcache,mode=max
```

Local developer builds use the default BuildKit local cache (`mode=min`). This ensures `COPY requirements-test.txt` + `RUN pip install` layers are rebuilt only when the requirements file content changes — not due to workspace file changes.

### 4. Dependency layers before code layers (immutable ordering rule).

All Dockerfiles MUST follow this layer order:

```
1. FROM base image
2. RUN system packages (apt-get)          ← changes rarely
3. COPY requirements/manifests only       ← changes on dep updates
4. RUN install packages                   ← invalidated only by step 3
5. COPY --chown source/config             ← invalidated by any code change
6. RUN final setup (chmod, etc.)
7. USER non-root
8. CMD / ENTRYPOINT
```

Step 5 MUST never precede step 4. Violating this ordering wastes the package install cache.

### 5. Image tagging scheme (blue-green / rollback).

| Tag | Meaning | Written by |
|---|---|---|
| `{image}:{semver}` | Immutable build artifact | CI on every merge to main |
| `{image}:current` | Live production traffic | Deployment job, after health check passes |
| `{image}:current-1` | Previous live version | Deployment job, kept 24h minimum |
| `{image}:canary` | Canary traffic (5%) | Deployment job during progressive rollout |
| `{image}:buildcache` | BuildKit registry cache | CI build job |

Rollback = `docker tag {image}:current-1 {image}:current` + LB re-route. No rebuild required.
Forward deployment = `docker tag {image}:{new-semver} {image}:canary` → 5% → health check → 100%.

Registry retention policy: never auto-delete any tag matching `current*` or any semver within 24h of being `current`.

### 6. `docker-compose.yml` service profiles for test runners.

Test runner services are gated by profiles to prevent accidental full-stack image pulls:

```yaml
services:
  test-runner-python:
    profiles: [test, test-python]
    build:
      context: .
      dockerfile: architecture/reference/dockerfiles/Dockerfile.test-runner-python

  test-runner-dotnet:
    profiles: [test, test-dotnet]
    build:
      context: .
      dockerfile: architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet

  test-runner-ts:
    profiles: [test, test-ts]
    build:
      context: .
      dockerfile: architecture/reference/dockerfiles/Dockerfile.test-runner-ts
```

C-080 test invocation for Python sprints: `docker compose --profile test-python run --rm test-runner-python pytest ...`

---

## Consequences

### Positive

- **Disk footprint**: Python-only sprint builds ~350 MB instead of ~1.5 GB. Codespaces disk pressure eliminated.
- **Build speed**: pip layer rebuild takes ~90s. .NET and Node layers are not touched during Python sprints.
- **Cache stability**: `requirements-test.txt` change busts only the Python runner's pip layer. .NET and Node runners are unaffected.
- **Blast radius**: A broken Node registry outage cannot block Python test execution.
- **Deployment granularity**: CE v1.40.0 can roll forward while AIR remains at v1.39.0. Natural rollback per service.
- **Codespace developer experience**: `docker compose --profile test-python run ...` builds in <2 min after first pull. No .NET SDK download on Python-only work.

### Negative

- **More Dockerfiles to maintain**: 3 test runners instead of 1. Mitigated by each being ~30 lines and single-concern.
- **CI pipeline expansion**: 3 build jobs instead of 1 for full test suite. Mitigated by parallelism and profile-scoped execution.
- **Transition work**: `Dockerfile.test-runner` must be deprecated across all references in `docker-compose.yml` and CI YAML.

### Neutral

- The bind-mount pattern (`.:/workspace`) is retained in all runners. Source code is NEVER baked into test runner images — only the runtime environment.
- C-080 mandate is preserved: tests still execute inside containers. Only the container boundary definition changes.

---

## Migration Path

1. **Immediate (this sprint)**: Create `Dockerfile.test-runner-python` with `--mount=type=cache` pip install. Add `test-runner-python` service to `docker-compose.yml`.
2. **WC-040**: Create `Dockerfile.test-runner-dotnet` and `Dockerfile.test-runner-ts`. Deprecate monolithic runner.
3. **WC-041 or later**: Remove `Dockerfile.test-runner` after all CI references are migrated. Convert production service Dockerfiles to use `--mount=type=cache` where not already done.

---

## References

- ADR-013: CI/CD Pipeline Structure (image promotion model)
- ADR-030: Autonomous Sprint Code Generation (compile gate model)
- ADR-038: Multi-Stack Compile Gate Architecture (per-stack gate logic)
- C-080: All tests MUST run inside containers. Virtual environments are prohibited.
- C-077: Developer toolchain cost ceiling — build times count against this constraint.
