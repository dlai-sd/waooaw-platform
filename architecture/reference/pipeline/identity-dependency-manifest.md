# Signed Identity Dependency Manifest Contract

**Document type:** Release dependency contract
**Owning office:** INST-005 - Solution Architect
**Enterprise decision:** ADR-048, Proposed - Founder acceptance required for Identity Edge entries
**Work Contract:** WC-077 focused architecture remediation
**Status:** FOUNDER REVIEW CANDIDATE; WC-123 BOUNDED PACKAGE ENTRY ACCEPTED; NOT DEPLOYMENT AUTHORITY

## 1. Purpose

This contract binds identity runtime dependencies and normalized configuration to an existing signed
exact-six application release. It does not add application members, authorize mutable tags, or create
a second release stream. The application release manifest and this dependency manifest together form
one deployable tuple for Demo, UAT, Production, and rollback.

## 2. Canonical signed payload

The canonical payload is UTF-8 JSON with deterministic key ordering and no insignificant whitespace.
Its schema requires these fields and rejects unknown fields:

```json
{
  "schema_version": "1.1",
  "manifest_id": "idm-<uuid>",
  "release_manifest_digest": "sha256:<64-hex>",
  "source_commit": "<40-hex>",
  "created_at": "<RFC3339 UTC>",
  "dependencies": {
    "keycloak": {
      "image_repository": "quay.io/keycloak/keycloak",
      "image_digest": "sha256:<64-hex>",
      "version": "25.0.6",
      "normalized_realm_digest": "sha256:<64-hex>",
      "sbom_digest": "sha256:<64-hex>",
      "provenance_digest": "sha256:<64-hex>"
    },
    "identity_edge": {
      "decision": "ADR-048",
      "image_repository": "docker.io/library/nginx",
      "image_digest": "sha256:<64-hex>",
      "version": "1.27.5-alpine",
      "route_policy_digest": "sha256:<64-hex>",
      "sbom_digest": "sha256:<64-hex>",
      "provenance_digest": "sha256:<64-hex>"
    },
    "web_runtime_packages": {
      "postgres": {
        "name": "postgres",
        "version": "3.4.9",
        "registry": "https://registry.npmjs.org",
        "tarball": "https://registry.npmjs.org/postgres/-/postgres-3.4.9.tgz",
        "integrity": "sha512-GD3qdB0x1z9xgFI6cdRD6xu2Sp2WCOEoe3mtnyB5Ee0XrrL5Pe+e4CCnJrRMnL1zYtRDZmQQVbvOttLnKDLnaw==",
        "resolved_bytes_digest": "sha512:<lockfile-equal-base64>",
        "source_repository": "https://github.com/porsager/postgres.git",
        "license": "Unlicense",
        "node_engine": ">=12",
        "declared_runtime_dependencies": [],
        "lockfile_digest": "sha256:<64-hex>",
        "sbom_digest": "sha256:<64-hex>",
        "provenance_status": "<verified|unavailable-with-reviewed-disposition>",
        "vulnerability_evidence_digest": "sha256:<64-hex>"
      }
    }
  },
  "identity_configuration": {
    "schema_version": "1.0",
    "environment_projection_digest": "sha256:<64-hex>",
    "keycloak_client_projection_digest": "sha256:<64-hex>",
    "provider_readiness_projection_digest": "sha256:<64-hex>"
  },
  "database": {
    "engine_major": 16,
    "schema_watermark": "<ordered migration identifier>",
    "migration_set_digest": "sha256:<64-hex>",
    "minimum_compatible_application_release_digest": "sha256:<64-hex>"
  },
  "qualification": {
    "openapi_digest": "sha256:<64-hex>",
    "test_evidence_digest": "sha256:<64-hex>",
    "security_evidence_digest": "sha256:<64-hex>",
    "compatibility_evidence_digest": "sha256:<64-hex>"
  },
  "signing": {
    "key_id": "<approved non-secret signing-key identifier>",
    "algorithm": "<approved signing algorithm>",
    "signature": "<detached-or-envelope signature value>"
  }
}
```

`identity_edge` is required only after ADR-048 acceptance and before any environment uses the edge.
Once present in a qualified release, it cannot be omitted during promotion. Secrets, credentials,
provider tokens, secret values, environment state coordinates, mutable tags, and unsigned URLs are
prohibited from the payload.

For WC-123, `web_runtime_packages.postgres` is the sole accepted new Web runtime-package entry and
is required before AUTH-WC-03 qualification. Its exact identity is governed by CSA-AUTH-001 Section
12.8 and `AUTHZ-SD-14`. It is a package artifact inside the existing Web image, not a seventh
application image or infrastructure dependency. A different version, tarball, integrity, resolved
graph, install-script behavior, owner, license, or material vulnerability requires a new accepted
amendment. No Auth.js adapter, ORM, query builder, generic database-session schema, or second
PostgreSQL package is implied.

## 3. Identity configuration projection

The environment projection is separately canonicalized and digest-bound. It contains only reviewed
non-secret configuration defined by the Identity Boundary contract: exact issuer/audience/JWKS,
realm/client identifiers, exact redirect/origin arrays, provider enabled state and permitted scopes,
secret-reference names, dependency references, token/cookie policy, internal Phone Identity audience,
and accepted readiness-evidence identifiers.

Demo, UAT, and Production each have a distinct environment projection digest because hostnames, client
identities, secret references, and readiness differ. This allowed configuration variance does not
permit application or dependency digest variance during promotion. Secret values are independently
resolved in the target environment and are never promoted as manifest content.

## 4. Build, qualification, and signing

1. Build the exact-six application images once and produce the existing signed release manifest.
2. Resolve every dependency by immutable OCI digest. Verify provenance, SBOM, license, vulnerability,
   and platform compatibility; never build or retag a third-party dependency as a promotion step.
   For an npm package entry, use a frozen lockfile and verify exact registry tarball, SRI/resolved
   bytes, registry signature, complete graph and install scripts, source/release/maintainer identity,
   SBOM inclusion, provenance availability, license, malware/secrets, vulnerabilities, and Node/Web
   compatibility. Missing provenance is an explicit reviewed disposition, not an inferred PASS.
3. Normalize the Keycloak realm and Identity Edge route policy from reviewed source, then record their
   content digests. Generated timestamps, exported secrets, and environment-only values are excluded
   from normalized realm content.
4. Apply additive database migrations in Docker and prove the preceding application release remains
   compatible with the resulting schema before qualification.
5. Bind OpenAPI, tests, security checks, dependency compatibility, source commit, and exact-six release
   digest into the canonical dependency payload.
6. Sign with the approved workload identity/key boundary and verify the signature before any cloud
   mutation. Signing authority and deployment authority remain separate where the delivery contract
   requires separation.

Any unresolved mutable reference, missing evidence, digest mismatch, unaccepted ADR-048 edge entry,
unknown schema field, stale provider readiness, or signature failure stops qualification.

## 5. Promotion

Promotion is by immutable reference in this order:

1. Demo deploys one signed exact-six manifest, one signed dependency manifest, and the Demo environment
   projection. Runtime digest attestation and Docker/real-environment identity journeys must pass.
2. Founder Demo acceptance is recorded against those exact manifest digests.
3. UAT references the same exact-six and dependency manifest digests with only the reviewed UAT
   environment projection and UAT-local secret resolution changed. There is no rebuild or retag.
4. Production remains plan-only/dark until separately authorized. When authorized, it references the
   same accepted application and dependency digests with the Production projection and Production-local
   secrets.

Digest strings have no chronological ordering. Promotion compares equality with the qualified source
manifests and verifies recorded acceptance; it never uses lexical or tag-based "newer" logic.

## 6. Rollback and database compatibility

Every deployment retains the immediately previous qualified tuple. Rollback verifies its signatures,
restores its exact application and dependency digests, applies its compatible environment projection,
and resolves only target-environment secret references. It performs no rebuild, retag, realm export,
issuer substitution, or cross-environment data/secret copy.

Identity migrations are expand-and-contract and forward-compatible. Destructive down-migrations,
dropping identity bindings, deleting verification/evidence history, or reducing the live schema
watermark during rollback are prohibited. An older application tuple may be restored only when its
`minimum_compatible_application_release_digest` and compatibility evidence prove it runs against the
current schema. Otherwise rollback stops and recovery follows the approved forward-fix/restore path.

## 7. Verification and audit evidence

Before deploy, the verifier proves signature validity, trusted key identity, exact-six release binding,
source commit binding, required member completeness, digest syntax and registry resolution, policy/realm
content equality, environment-schema validity, schema compatibility, and evidence freshness. After
deploy, runtime attestation proves each image digest and configuration digest matches the manifests.

The release record stores both manifest digests, signature verification result, target projection
digest, migration watermark, runtime attestation, deploy result, identity smoke-journey evidence,
approver/authority references, and rollback tuple. Evidence is append-only and contains no identity PII
or secrets.

## 8. Author review

**Result:** PASS as a proposed release dependency contract. It preserves exact-six membership, immutable
promotion, target-environment isolation, additive database safety, and Founder-controlled Demo to UAT
to Production gates. It grants no build, cloud, provider, deployment, or Production authority.
