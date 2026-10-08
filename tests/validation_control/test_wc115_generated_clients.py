# Implements: WC-115 R096-R099 deterministic generated-client evidence
# Constitutional basis: C-023, C-059, C-065, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "web/lib/api/generated/employment/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml",
        "typescript-fetch",
    ),
    "src/business-platform/Clients/Generated/EmploymentWbe/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-wbe.openapi.yaml",
        "csharp",
    ),
    "src/business-platform/Clients/Generated/EmploymentDomainAdapter/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml",
        "csharp",
    ),
    "src/professional-runtime/clients/generated/employment_ai_runtime/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-ai-runtime.openapi.yaml",
        "python",
    ),
    "src/professional-runtime/clients/generated/employment_domain_adapter/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml",
        "python",
    ),
    "src/business-platform/Clients/Generated/EmploymentCompatibility/generation-manifest.json": (
        "architecture/reference/api-specs/conversational-employment-compatibility-scan.openapi.yaml",
        "csharp",
    ),
}


def test_wc115_generated_clients_pin_generator_and_input_digest() -> None:
    for manifest_path, (input_path, language) in EXPECTED.items():
        manifest = json.loads((ROOT / manifest_path).read_text())
        digest = hashlib.sha256((ROOT / input_path).read_bytes()).hexdigest()

        assert manifest["generator"] == "openapi-generator-cli"
        assert manifest["generatorVersion"] == "7.17.0"
        assert manifest["language"] == language
        assert manifest["input"] == input_path
        assert manifest["inputSha256"] == digest
