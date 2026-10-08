#!/usr/bin/env bash
# Implements: WC-115 R096-R099 deterministic generated-client boundary
# Constitutional basis: C-023, C-059, C-065, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
generator_image="openapitools/openapi-generator-cli:v7.17.0"

generate() {
  docker run --rm --user "$(id -u):$(id -g)" -v "${repo_root}:/local" \
    "${generator_image}" generate "$@"
}

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml \
  -g typescript-fetch \
  -o /local/web/lib/api/generated/employment \
  --additional-properties=supportsES6=true,npmName=@waooaw/employment-client,npmVersion=1.0.0-candidate.2,withInterfaces=true

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-wbe.openapi.yaml \
  -g csharp \
  -o /local/src/business-platform/Clients/Generated/EmploymentWbe \
  --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
  --additional-properties=packageName=Waooaw.Generated.WbeEmployment,packageVersion=1.0.0-candidate.2,library=httpclient,targetFramework=net9.0

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml \
  -g csharp \
  -o /local/src/business-platform/Clients/Generated/EmploymentDomainAdapter \
  --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
  --additional-properties=packageName=Waooaw.Generated.DomainEmployment,packageVersion=1.0.0-candidate.2,library=httpclient,targetFramework=net9.0

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-ai-runtime.openapi.yaml \
  -g python \
  -o /local/src/professional-runtime/clients/generated/employment_ai_runtime \
  --additional-properties=packageName=employment_air_client,packageVersion=1.0.0-candidate.2,generateSourceCodeOnly=true

sed -i \
  '/if not re.match(r".*readiness/c\        if value.split("/", 2)[1] in {"readiness", "billing", "authority", "evidence", "tenant", "relationship"} or not re.fullmatch(r"/[a-z][a-zA-Z0-9]*(?:/[a-zA-Z0-9_-]+)*", value):' \
  "${repo_root}/src/professional-runtime/clients/generated/employment_ai_runtime/employment_air_client/models/proposal_operation.py"

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml \
  -g python \
  -o /local/src/professional-runtime/clients/generated/employment_domain_adapter \
  --additional-properties=packageName=employment_domain_client,packageVersion=1.0.0-candidate.2,generateSourceCodeOnly=true

generate \
  -i /local/architecture/reference/api-specs/conversational-employment-compatibility-scan.openapi.yaml \
  -g csharp \
  -o /local/src/business-platform/Clients/Generated/EmploymentCompatibility \
  --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
  --additional-properties=packageName=Waooaw.Generated.EmploymentCompatibility,packageVersion=1.0.0-candidate.2,library=httpclient,targetFramework=net9.0
