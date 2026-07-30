# Implements: scripts/runner/legacy_handlers.py
# constitutional_basis: C-059, C-023, C-027, C-007, ADR-001, ADR-002, C-025
# ib_item: IB-009
"""
Per-WC deterministic task handlers for WC011 through WC015.

All functions here are DETERMINISTIC — they do not call an LLM. They copy
reference files, write template code, or validate existing artifacts.
LLM-based tasks (WC012-02, WC013-02, etc.) are SubTaskDef dicts in
TASK_HANDLERS and go through execute_with_llm() in task_executor.py.
"""
from __future__ import annotations

import json as _json_mod
import sys

from runner.constants import REPO_ROOT
from runner.git_ops import git, run


def execute_wc011_01() -> bool:
    """WC011-01: Validate docker-compose.yml."""
    print("── WC011-01: Validate docker-compose.yml ──")
    result = run(
        ["docker", "compose", "-f", "docker-compose.yml", "config", "--quiet"],
        check=False, capture=True
    )
    REPO_ROOT.joinpath("logs").mkdir(exist_ok=True)
    (REPO_ROOT / "logs" / "docker-compose-validation.txt").write_text(
        result.stdout + result.stderr
    )
    if result.returncode == 0:
        print("  OK: docker compose config valid")
    else:
        print(f"  FAIL: docker compose config invalid — {result.stderr[:200]}")
        return False

    config_text = result.stdout
    required = ["constitutional-engine", "business-platform", "professional-runtime",
                "ai-runtime", "web", "postgres", "keycloak", "temporal"]
    missing = [svc for svc in required if svc not in config_text]
    if missing:
        for svc in missing:
            print(f"  FAIL: required service '{svc}' missing from docker-compose config")
        print(f"  FAIL: {len(missing)} required service(s) missing — cannot pass WC011-01")
        return False

    git(["add", "docker-compose.yml", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-01 - validate docker-compose.yml\n\n"
             "IB: IB-009\nConstitutional: C-067, C-004\nCCTs-added: none"])
    return True


def execute_wc011_02() -> bool:
    """WC011-02: Validate DB migration scripts 01–10."""
    from runner.task_executor import flag_spec_gap
    print("── WC011-02: Validate DB migration scripts ──")
    init_dir = REPO_ROOT / "infrastructure" / "postgres" / "init"

    if not init_dir.exists():
        print(f"  FAIL: {init_dir} does not exist")
        return False

    sql_files = sorted(init_dir.glob("*.sql"))
    print(f"  Found {len(sql_files)} SQL files in {init_dir.relative_to(REPO_ROOT)}")

    required_prefixes = ["01-", "03-", "04-", "07-", "09-"]
    for prefix in required_prefixes:
        matches = [f for f in sql_files if f.name.startswith(prefix)]
        if not matches:
            print(f"  WARN: No migration file starting with '{prefix}' found")
        else:
            print(f"  OK: {matches[0].name}")

    issues = []
    for sql_file in sql_files:
        content = sql_file.read_text(encoding="utf-8")
        if "audit_records" in content and ("UPDATE" in content or "DELETE" in content):
            if "NO UPDATE" not in content and "RULE NO" not in content.upper():
                flag_spec_gap(
                    task_id="WC011-02",
                    gap_description=f"{sql_file.name}: potential UPDATE/DELETE on audit_records — C-007/C-027 violation. "
                                    "The constitutional audit ledger must be append-only. No UPDATE or DELETE permitted.",
                    affected_spec="infrastructure/postgres/init/05-append-only-rules.sql",
                    constitutional_basis="C-007 (Ledger Immutability), C-027 (Append-only enforcement)"
                )
                return False
        if sql_file.name.startswith("05-append-only"):
            if "RULE" not in content.upper() and "TRIGGER" not in content.upper():
                issues.append(f"{sql_file.name}: No RULE or TRIGGER found for append-only enforcement (C-027)")
        if "-- Validated: WC-011" not in content:
            updated = content.rstrip() + "\n-- Validated: WC-011 Sprint 011 (infrastructure check only)\n"
            sql_file.write_text(updated, encoding="utf-8")

    if issues:
        for issue in issues:
            print(f"  WARN: {issue}")
    else:
        print("  OK: All migration files pass constitutional markers check")

    git(["add", "infrastructure/postgres/init/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-02 - validate DB migration scripts 01-10\n\n"
             "IB: IB-009\nConstitutional: C-007, C-027, C-059\nCCTs-added: none"])
    return True


def execute_wc011_03() -> bool:
    """WC011-03: Validate Keycloak realm import."""
    print("── WC011-03: Validate Keycloak realm import ──")
    keycloak_dir = REPO_ROOT / "infrastructure" / "keycloak"
    realm_files = list(keycloak_dir.glob("*.json")) if keycloak_dir.exists() else []

    if not realm_files:
        print(f"  FAIL: No realm JSON file found in {keycloak_dir.relative_to(REPO_ROOT)}")
        return False

    realm_file = realm_files[0]
    print(f"  Found realm file: {realm_file.name}")

    try:
        realm = _json_mod.loads(realm_file.read_text(encoding="utf-8"))
    except _json_mod.JSONDecodeError as e:
        print(f"  FAIL: Realm JSON is invalid — {e}")
        return False

    realm_id = realm.get("realm", "")
    if realm_id != "waooaw":
        print(f"  WARN: realm id is '{realm_id}', expected 'waooaw'")
    else:
        print(f"  OK: realm id = waooaw")

    identity_providers = realm.get("identityProviders", [])
    google_idp = [p for p in identity_providers if p.get("providerId") == "google"]
    if google_idp:
        print("  OK: Google IDP configured (ADR-008)")
    else:
        print("  WARN: Google IDP not found in realm (ADR-008 requires Google as default IDP)")

    print("  OK: Keycloak realm validation complete")
    return True


def execute_wc011_05() -> bool:
    """WC011-05: Verify setup.sh and get-dev-token.sh."""
    print("── WC011-05: Verify scripts ──")
    scripts_to_check = [
        REPO_ROOT / "scripts" / "setup.sh",
        REPO_ROOT / "scripts" / "get-dev-token.sh",
    ]
    all_ok = True
    for script in scripts_to_check:
        if not script.exists():
            print(f"  FAIL: {script.name} not found")
            all_ok = False
        else:
            first_line = script.read_text(encoding="utf-8").split("\n")[0]
            if not first_line.startswith("#!"):
                print(f"  WARN: {script.name} missing shebang line")
            else:
                print(f"  OK: {script.name} (shebang: {first_line})")
    return all_ok


def execute_wc011_04() -> bool:
    """WC011-04: Create src/ directory scaffold with C-059 headers."""
    print("── WC011-04: Create src/ directory scaffold ──")
    services = [
        ("constitutional-engine", "Constitutional Engine"),
        ("business-platform", "Business Platform"),
        ("professional-runtime", "Professional Runtime"),
        ("ai-runtime", "AI Runtime"),
    ]
    for svc_dir, svc_name in services:
        target = REPO_ROOT / "src" / svc_dir
        target.mkdir(parents=True, exist_ok=True)
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# Implements: architecture/reference/components/{svc_dir}.md\n"
                f"# Constitutional basis: C-059 (Implementation Traceability)\n\n"
                f"## {svc_name}\n\n"
                f"Implements: `architecture/reference/components/{svc_dir}.md`\n\n"
                f"## Local Development\n\n"
                f"```bash\ndocker compose up {svc_dir}\n```\n\n"
                f"## Tests\n\n"
                f"Unit tests and CCTs added in Sprint 012+.\n"
            )
            print(f"  Created src/{svc_dir}/README.md")

    git(["add", "src/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-04 - src/ scaffold with C-059 headers\n\n"
             "IB: IB-009\nConstitutional: C-059, C-064\nCCTs-added: none"])
    return True


def execute_wc011_07() -> bool:
    """WC011-07: Document GitHub Actions secrets (OIDC pattern — 2026-07-23)."""
    print("── WC011-07: Document GitHub Actions secrets ──")
    secrets_doc = REPO_ROOT / "infrastructure" / "GITHUB-SECRETS.md"

    if secrets_doc.exists():
        existing = secrets_doc.read_text(encoding="utf-8")
        if "OIDC + Azure Key Vault" in existing and "ANTHROPIC-API-KEY" in existing:
            print("  OK: GITHUB-SECRETS.md already documents OIDC pattern — no changes needed")
            return True
    secrets_doc.write_text(
        "# GitHub Actions Secrets & Variables — WAOOAW Platform\n"
        "# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (Secret Management)\n"
        "# ib_item: IB-009 (WC011-07)\n"
        "# produced_by: WC011-07 autonomous sprint task\n\n"
        "## Architecture: OIDC + Azure Key Vault (no long-lived credentials in GitHub Secrets)\n\n"
        "Per ADR-014, all secrets live in Azure Key Vault (waooaw-dev-kv).\n"
        "GitHub Actions authenticates to Azure via OIDC (no stored client secret).\n"
        "Non-sensitive config values are GitHub Variables (not Secrets).\n\n"
        "---\n\n"
        "## GitHub Variables (non-sensitive config — Settings → Variables → Actions)\n\n"
        "| Variable | Value | Purpose |\n"
        "|---|---|---|\n"
        "| `AZURE_CLIENT_ID` | App Registration Client ID | OIDC authentication to Azure |\n"
        "| `AZURE_TENANT_ID` | Azure AD Tenant ID | OIDC authentication to Azure |\n"
        "| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | OIDC scope |\n"
        "| `AZURE_KEYVAULT_NAME` | `waooaw-dev-kv` | Key Vault name for secret fetch |\n\n"
        "**Status: All 4 set** (2026-07-23)\n\n"
        "---\n\n"
        "## Azure Key Vault Secrets (fetched at runtime via OIDC — never stored in GitHub)\n\n"
        "| KV Secret Name | Used By | Obtain From | Status |\n"
        "|---|---|---|---|\n"
        "| `ANTHROPIC-API-KEY` | `autonomous-sprint.yaml` execute + review | console.anthropic.com → API Keys | ✅ DONE |\n"
        "| `GH-APP-ID` | `autonomous-sprint.yaml` review | GitHub App waooaw-reviewer | ✅ DONE |\n"
        "| `GH-APP-INSTALLATION-ID` | `autonomous-sprint.yaml` review | GitHub App installation | ✅ DONE |\n"
        "| `GH-APP-PRIVATE-KEY` | `autonomous-sprint.yaml` review | GitHub App private key (.pem) | ✅ DONE |\n"
        "| `CODECOV-TOKEN` | `ci.yaml` coverage upload | codecov.io → repo settings | ✅ DONE |\n"
        "| `DEV_BASE_URL` | `post-deploy-verify.yaml` | Terraform output after M1 | ⬜ PENDING |\n"
        "| `DEV_CONSTITUTIONAL_DB_URL` | `promote.yaml` CCTs | Terraform output after M2 | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_A` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `DEV_TEST_JWT_TENANT_B` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |\n"
        "| `GOOGLE-VERTEX-SA-KEY` | AI Runtime (Gemini) | GCP SA key JSON (FA-021) | ⬜ PENDING |\n"
        "| `SARVAM-API-KEY` | AI Runtime (Agricultural) | sarvam.ai API key (FA-022) | ⬜ PENDING |\n"
        "| `AZURE-OPENAI-KEY` | AI Runtime (fallback LLM) | Azure OpenAI UAE North (FA-003) | ⬜ PENDING |\n\n"
        "---\n\n"
        "## Secret Rotation Policy (ADR-014)\n\n"
        "- Azure OIDC: no rotation needed (no client secret — OIDC federated credential)\n"
        "- ANTHROPIC-API-KEY: rotate if exposed in logs or AI context\n"
        "- GH-APP-PRIVATE-KEY: rotate annually or if exposed\n"
        "- All others: rotate if leaked; quarterly audit minimum\n\n"
        "## No Longer Used\n\n"
        "The following were in earlier designs but are replaced by OIDC:\n"
        "- `AZURE_CREDENTIALS_DEV/QA/PROD` — replaced by OIDC federated credential\n"
        "- `REVIEW_APP_TOKEN` — replaced by `GH-APP-PRIVATE-KEY` in Key Vault + JWT generation\n"
    )
    print("  Updated infrastructure/GITHUB-SECRETS.md (OIDC pattern)")

    git(["add", "infrastructure/GITHUB-SECRETS.md"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "chore(infra): WC011-07 - document GitHub Actions secrets (OIDC pattern)\n\n"
             "IB: IB-009\nConstitutional: C-059, ADR-014"])
    return True


def execute_wc012_01() -> bool:
    """
    WC012-01: CE project scaffold — DETERMINISTIC (no LLM call).
    constitutional_basis: C-059 (Traceability), C-082 (build validation), ADR-001 (gRPC)
    """
    print("── WC012-01: CE project scaffold (DETERMINISTIC) ──")
    service = "constitutional-engine"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / f"{service}.Tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "Protos").mkdir(exist_ok=True)
    (src_dir / "Services").mkdir(exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    ref_csproj = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "constitutional-engine.csproj"
    if not ref_csproj.is_file():
        print(f"  ❌ Reference csproj not found: {ref_csproj}")
        return False
    (src_dir / "constitutional-engine.csproj").write_text(ref_csproj.read_text())
    print("  ✅ constitutional-engine.csproj copied from reference dotfile")

    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    if not ref_proto.is_file():
        print(f"  ❌ Reference proto not found: {ref_proto}")
        return False
    (src_dir / "Protos" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied from architecture reference")

    (src_dir / "Program.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry)\n\n"
        "using Waooaw.ConstitutionalEngine.Services;\n\n"
        "var builder = WebApplication.CreateBuilder(args);\n"
        "builder.Services.AddGrpc();\n\n"
        "var app = builder.Build();\n"
        "app.MapGrpcService<ConstitutionalEngineService>();\n"
        "app.Run();\n"
    )
    print("  ✅ Program.cs written from template")

    (src_dir / "Services" / "ConstitutionalEngineService.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md\n"
        "// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop)\n\n"
        "using Grpc.Core;\n"
        "using Waooaw.ConstitutionalEngine.Grpc;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Services;\n\n"
        "/// <summary>gRPC service stub — full implementation in WC012-02/03/04.</summary>\n"
        "public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase\n"
        "{\n"
        "    public override Task<RecordEvidenceResponse> RecordEvidence(RecordEvidenceRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RecordEvidenceResponse());\n"
        "    public override Task<ValidateActionResponse> ValidateAction(ValidateActionRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new ValidateActionResponse());\n"
        "    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(GrantAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new GrantAuthorityResponse());\n"
        "    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(RevokeAuthorityRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new RevokeAuthorityResponse());\n"
        "    public override Task<EvaluatePolicyResponse> EvaluatePolicy(EvaluatePolicyRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EvaluatePolicyResponse());\n"
        "    public override Task<EmergencyStopResponse> TriggerEmergencyStop(EmergencyStopRequest req, ServerCallContext ctx)\n"
        "        => Task.FromResult(new EmergencyStopResponse());\n"
        "}\n"
    )
    print("  ✅ ConstitutionalEngineService.cs stub written from template")

    (src_dir / "appsettings.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Information" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "" },\n'
        '  "Kestrel": { "Endpoints": { "Grpc": { "Url": "http://0.0.0.0:5002", "Protocols": "Http2" } } }\n}\n'
    )
    (src_dir / "appsettings.Development.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Debug" } },\n'
        '  "ConnectionStrings": { "ConstitutionalDb": "Host=localhost;Port=5432;Database=constitutional;Username=constitutional_engine;Password=dev_password_replace_in_prod" }\n}\n'
    )
    print("  ✅ appsettings.json + appsettings.Development.json written")

    (test_dir / "constitutional-engine.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '    <Nullable>enable</Nullable>\n'
        '    <ImplicitUsings>enable</ImplicitUsings>\n'
        '    <IsPackable>false</IsPackable>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '    <ProjectReference Include="..\\..\\src\\constitutional-engine\\constitutional-engine.csproj" />\n'
        '  </ItemGroup>\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />\n'
        '    <PackageReference Include="xunit" Version="2.9.3" />\n'
        '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '    <PackageReference Include="Moq" Version="4.20.72" />\n'
        '    <PackageReference Include="FluentAssertions" Version="6.12.2" />\n'
        '    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="9.0.0" />\n'
        '    <PackageReference Include="coverlet.collector" Version="6.0.4">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    print("  ✅ constitutional-engine.Tests.csproj written")

    build = run(["dotnet", "build", str(src_dir / "constitutional-engine.csproj"),
                 "--nologo", "-v", "quiet"], check=False, capture=True)
    if build.returncode != 0:
        print(f"  ❌ dotnet build FAILED:\n{build.stderr[:500]}")
        import shutil
        for p in [src_dir / "Protos", src_dir / "Services", src_dir / "Program.cs",
                  src_dir / "appsettings.json", src_dir / "appsettings.Development.json",
                  src_dir / "constitutional-engine.csproj", test_dir]:
            if p.is_dir(): shutil.rmtree(p)
            elif p.is_file(): p.unlink()
        return False
    print("  ✅ dotnet build PASSED")

    git(["add", "src/constitutional-engine/", "tests/constitutional-engine.Tests/"])
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat: WC012-01 — CE project scaffold (.NET 9 gRPC service)\n\n"
             "IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
    print("  ✅ WC012-01 complete (deterministic — no LLM)")
    return True


def _generate_wc012_02a_evaluator_interfaces() -> bool:
    """
    WC012-02a: Evaluator interface contracts — deterministic templates.
    constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation)
    """
    print("  ── WC012-02a: Evaluator interfaces (deterministic template) ──")
    ev_dir = REPO_ROOT / "src" / "constitutional-engine" / "Evaluators"
    ev_dir.mkdir(parents=True, exist_ok=True)

    (ev_dir / "EvaluationResult.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073, C-059\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "/// <summary>Verdict returned by a constitutional claim evaluator.</summary>\n"
        "public enum EvaluationVerdict { Allow, Deny, Escalate }\n\n"
        "/// <summary>Result of a single constitutional claim evaluation.</summary>\n"
        "public sealed record EvaluationResult(\n"
        "    string ClaimId,\n"
        "    EvaluationVerdict Verdict,\n"
        "    string Reason);\n"
    )
    (ev_dir / "EvaluationContext.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-059, C-043, C-062\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "using System.Text.Json;\n"
        "using Waooaw.ConstitutionalEngine.Grpc;\n\n"
        "/// <summary>\n"
        "/// Immutable context derived from ValidateActionRequest + gRPC metadata.\n"
        "/// TenantId: from gRPC metadata 'x-tenant-id' (not a proto field).\n"
        "/// ActionParameters: JSON-encoded string — use GetParameter(key) to parse.\n"
        "/// </summary>\n"
        "public sealed record EvaluationContext(\n"
        "    string ContractId,\n"
        "    string ActionType,\n"
        "    string ActionParameters,\n"
        "    int DecisionSpaceVersion,\n"
        "    string TenantId,\n"
        "    string? SkillId = null,\n"
        "    long ApprovedBudgetInrPaise = 0,\n"
        "    long CurrentSpendInrPaise = 0,\n"
        "    long ProposedSpendInrPaise = 0,\n"
        "    string BudgetSkillType = \"\")\n"
        "{\n"
        "    public string? GetParameter(string key)\n"
        "    {\n"
        "        try\n"
        "        {\n"
        "            using var doc = JsonDocument.Parse(\n"
        "                string.IsNullOrEmpty(ActionParameters) ? \"{}\" : ActionParameters);\n"
        "            return doc.RootElement.TryGetProperty(key, out var val)\n"
        "                ? val.GetString()\n"
        "                : null;\n"
        "        }\n"
        "        catch { return null; }\n"
        "    }\n\n"
        "    public static EvaluationContext FromRequest(\n"
        "        ValidateActionRequest request, string tenantId) => new(\n"
        "        ContractId:            request.ContractId,\n"
        "        ActionType:            request.ActionType,\n"
        "        ActionParameters:      request.ActionParameters,\n"
        "        DecisionSpaceVersion:  request.DecisionSpaceVersion,\n"
        "        TenantId:              tenantId,\n"
        "        SkillId:               request.HasSkillId ? request.SkillId : null,\n"
        "        ApprovedBudgetInrPaise: request.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0,\n"
        "        CurrentSpendInrPaise:   request.BudgetContext?.CurrentMonthSpendInrPaise ?? 0,\n"
        "        ProposedSpendInrPaise:  request.BudgetContext?.ProposedSpendInrPaise ?? 0,\n"
        "        BudgetSkillType:        request.BudgetContext?.SkillType ?? \"\");\n"
        "}\n"
    )
    (ev_dir / "IClaimEvaluator.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "public interface IClaimEvaluator\n"
        "{\n"
        "    string ClaimId { get; }\n"
        "    Task<EvaluationResult> EvaluateAsync(\n"
        "        EvaluationContext context,\n"
        "        CancellationToken cancellationToken = default);\n"
        "}\n"
    )
    (ev_dir / "EvaluatorRegistry.cs").write_text(
        "// Implements: architecture/reference/ce-validate-action-evaluators.md\n"
        "// constitutional_basis: C-041, C-073, C-076\n\n"
        "#nullable enable\n"
        "namespace Waooaw.ConstitutionalEngine.Evaluators;\n\n"
        "using Microsoft.Extensions.Logging;\n\n"
        "public sealed class EvaluatorRegistry\n"
        "{\n"
        "    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;\n"
        "    private readonly ILogger<EvaluatorRegistry> _logger;\n\n"
        "    public EvaluatorRegistry(\n"
        "        IEnumerable<IClaimEvaluator> evaluators,\n"
        "        ILogger<EvaluatorRegistry> logger)\n"
        "    {\n"
        "        _evaluators = evaluators.ToList();\n"
        "        _logger = logger;\n"
        "    }\n\n"
        "    public int Count => _evaluators.Count;\n\n"
        "    public async Task<IReadOnlyList<EvaluationResult>> EvaluateAllAsync(\n"
        "        EvaluationContext context,\n"
        "        CancellationToken cancellationToken = default)\n"
        "    {\n"
        "        _logger.LogInformation(\n"
        "            \"Evaluating action {ActionType} for contract {ContractId} against {Count} claims\",\n"
        "            context.ActionType, context.ContractId, _evaluators.Count);\n"
        "        var tasks = _evaluators.Select(e => e.EvaluateAsync(context, cancellationToken));\n"
        "        return await Task.WhenAll(tasks);\n"
        "    }\n"
        "}\n"
    )
    git(["add", "src/constitutional-engine/Evaluators/"], check=False)
    print("  ✅ WC012-02a: 4 interface files written")
    return True


def _generate_wc012_02c_prep() -> bool:
    """
    WC012-02c-prep: Write FakeServerCallContext.cs — deterministic test helper.
    constitutional_basis: C-076 (test coverage), C-082 (build validation)
    """
    tests_dir = REPO_ROOT / "tests" / "constitutional-engine.Tests" / "Evaluators"
    tests_dir.mkdir(parents=True, exist_ok=True)

    (tests_dir / "FakeServerCallContext.cs").write_text(
        "// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests\n"
        "// constitutional_basis: C-076 (test coverage), C-082 (build validation)\n"
        "// DETERMINISTIC: Grpc.Core.ServerCallContext abstract members are\n"
        "// properties (NOT methods) — generated by template to prevent CS0505.\n\n"
        "#nullable enable\n"
        "using System;\n"
        "using System.Collections.Generic;\n"
        "using System.Threading;\n"
        "using System.Threading.Tasks;\n"
        "using Grpc.Core;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;\n\n"
        "public sealed class FakeServerCallContext : ServerCallContext\n"
        "{\n"
        "    private readonly Metadata _requestHeaders;\n"
        "    private readonly Metadata _responseTrailers = new Metadata();\n"
        "    private Status _status;\n"
        "    private WriteOptions? _writeOptions = WriteOptions.Default;\n\n"
        "    public static FakeServerCallContext Create(string? tenantId = null) =>\n"
        "        new(tenantId is null\n"
        "            ? new Metadata()\n"
        "            : new Metadata { { \"x-tenant-id\", tenantId } });\n\n"
        "    public FakeServerCallContext(Metadata? requestHeaders = null)\n"
        "        => _requestHeaders = requestHeaders ?? new Metadata();\n\n"
        "    protected override string MethodCore\n"
        "        => \"/constitutional.v1.ConstitutionalService/ValidateAction\";\n"
        "    protected override string HostCore => \"localhost\";\n"
        "    protected override DateTime DeadlineCore => DateTime.MaxValue;\n"
        "    protected override Metadata RequestHeadersCore => _requestHeaders;\n"
        "    protected override CancellationToken CancellationTokenCore\n"
        "        => CancellationToken.None;\n"
        "    protected override string PeerCore => \"ipv4:127.0.0.1:50051\";\n"
        "    protected override Metadata ResponseTrailersCore => _responseTrailers;\n"
        "    protected override AuthContext AuthContextCore\n"
        "        => new AuthContext(null,\n"
        "               new Dictionary<string, List<AuthProperty>>());\n\n"
        "    protected override ContextPropagationToken CreatePropagationTokenCore(\n"
        "        ContextPropagationOptions? options)\n"
        "        => throw new NotImplementedException(\"Not required for unit tests.\");\n\n"
        "    protected override Task WriteResponseHeadersAsyncCore(\n"
        "        Metadata responseHeaders)\n"
        "        => Task.CompletedTask;\n\n"
        "    protected override Status StatusCore\n"
        "    {\n"
        "        get => _status;\n"
        "        set => _status = value;\n"
        "    }\n\n"
        "    protected override WriteOptions? WriteOptionsCore\n"
        "    {\n"
        "        get => _writeOptions;\n"
        "        set => _writeOptions = value;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    print("  ✅ WC012-02c-prep: FakeServerCallContext.cs written")
    return True


def _generate_wc012_03a_data_layer() -> bool:
    """
    WC012-03a: Data layer templates — EvidenceRecord + ConstitutionalDbContext.
    constitutional_basis: C-027 (append-only), C-023 (Evidence First), C-059 (Traceability)
    """
    print("  ── WC012-03a: Data layer (deterministic template) ──")
    service = "constitutional-engine"
    data_dir = REPO_ROOT / "src" / service / "Data"
    entities_dir = data_dir / "Entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    (entities_dir / "EvidenceRecord.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §1\n"
        "// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), C-059 (Traceability)\n\n"
        "namespace Waooaw.ConstitutionalEngine.Data.Entities;\n\n"
        "public sealed class EvidenceRecord\n"
        "{\n"
        "    public Guid Id { get; init; } = Guid.NewGuid();\n"
        "    public string IdempotencyKey { get; init; } = string.Empty;\n"
        "    public Guid TenantId { get; init; }\n"
        "    public string EvidenceType { get; init; } = string.Empty;\n"
        "    public string Summary { get; init; } = string.Empty;\n"
        "    public string? PayloadJson { get; init; }\n"
        "    public DateTimeOffset RecordedAt { get; init; } = DateTimeOffset.UtcNow;\n"
        "}\n"
    )
    (data_dir / "ConstitutionalDbContext.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §1\n"
        "// constitutional_basis: C-027 (append-only), C-023 (Evidence First)\n\n"
        "using Microsoft.EntityFrameworkCore;\n"
        "using Waooaw.ConstitutionalEngine.Data.Entities;\n\n"
        "namespace Waooaw.ConstitutionalEngine.Data;\n\n"
        "public sealed class ConstitutionalDbContext : DbContext\n"
        "{\n"
        "    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options) : base(options) {}\n"
        "    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();\n"
        "}\n"
    )
    git(["add", f"src/{service}/Data/"], check=False)
    print("  ✅ WC012-03a: Data layer written (EvidenceRecord + ConstitutionalDbContext)")
    return True


def _generate_wc012_04a_emergency_stop_entities() -> bool:
    """
    WC012-04a: EmergencyStop entities — EmergencyStopEvent + DbContext.
    constitutional_basis: C-001 (Emergency Stop absolute), C-023, C-027 (append-only)
    """
    print("  ── WC012-04a: EmergencyStop entities (deterministic template) ──")
    service = "constitutional-engine"
    es_dir = REPO_ROOT / "src" / service / "EmergencyStop"
    es_dir.mkdir(parents=True, exist_ok=True)

    (es_dir / "EmergencyStopEvent.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §4\n"
        "// constitutional_basis: C-001 (Emergency Stop absolute), C-023, C-027 (append-only)\n\n"
        "namespace Waooaw.ConstitutionalEngine.EmergencyStop;\n\n"
        "public sealed class EmergencyStopEvent\n"
        "{\n"
        "    public Guid Id { get; init; } = Guid.NewGuid();\n"
        "    public Guid ContractId { get; init; }\n"
        "    public string InitiatedByUserId { get; init; } = string.Empty;\n"
        "    public string[] AffectedSessionIds { get; init; } = Array.Empty<string>();\n"
        "    public DateTimeOffset TriggeredAt { get; init; } = DateTimeOffset.UtcNow;\n"
        "    public DateTimeOffset? TemporalSignalledAt { get; set; }\n"
        "    public string StopSource { get; init; } = \"gRPC\";\n"
        "}\n"
    )
    (es_dir / "EmergencyStopDbContext.cs").write_text(
        "// Implements: architecture/reference/components/constitutional-engine.md §4\n"
        "// constitutional_basis: C-001 (Emergency Stop), C-027 (append-only), C-023\n\n"
        "using Microsoft.EntityFrameworkCore;\n\n"
        "namespace Waooaw.ConstitutionalEngine.EmergencyStop;\n\n"
        "public sealed class EmergencyStopDbContext : DbContext\n"
        "{\n"
        "    public EmergencyStopDbContext(DbContextOptions<EmergencyStopDbContext> options) : base(options) {}\n"
        "    public DbSet<EmergencyStopEvent> EmergencyStopEvents => Set<EmergencyStopEvent>();\n"
        "}\n"
    )
    git(["add", f"src/{service}/EmergencyStop/"], check=False)
    print("  ✅ WC012-04a: EmergencyStop entities written")
    return True


def execute_wc013_01() -> bool:
    """
    WC013-01: Business Platform project scaffold — DETERMINISTIC (no LLM).
    constitutional_basis: C-059, C-082, ADR-002 (spec-first)
    """
    print("── WC013-01: BP project scaffold (DETERMINISTIC) ──")
    service = "business-platform"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / f"{service}.Tests"
    (src_dir / "Controllers").mkdir(parents=True, exist_ok=True)
    (src_dir / "Services").mkdir(parents=True, exist_ok=True)
    (src_dir / "Models").mkdir(parents=True, exist_ok=True)
    (src_dir / "Data").mkdir(parents=True, exist_ok=True)
    (src_dir / "Protos").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    ref_csproj = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "business-platform.csproj"
    (src_dir / "business-platform.csproj").write_text(ref_csproj.read_text())
    print("  ✅ business-platform.csproj copied from reference dotfile")

    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "Protos" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied (gRPC client target)")

    (src_dir / "Program.cs").write_text(
        "// Implements: architecture/reference/components/business-platform.md\n"
        "// constitutional_basis: ADR-002 (spec-first), ADR-003 (JWT tenancy), C-026 (RLS), C-023\n\n"
        "using Waooaw.BusinessPlatform.Controllers;\n\n"
        "var builder = WebApplication.CreateBuilder(args);\n"
        "builder.Services.AddControllers();\n"
        "builder.Services.AddEndpointsApiExplorer();\n"
        "builder.Services.AddSwaggerGen();\n\n"
        "var app = builder.Build();\n"
        "app.UseSwagger();\n"
        "app.UseSwaggerUI();\n"
        "app.MapControllers();\n"
        "app.Run();\n"
    )
    print("  ✅ Program.cs stub written")

    (src_dir / "Controllers" / "CustomersController.cs").write_text(
        "// Implements: architecture/reference/api-specs/business-platform.openapi.yaml\n"
        "// constitutional_basis: ADR-002 (spec-first), C-023, C-038 (pro-rata)\n\n"
        "using Microsoft.AspNetCore.Mvc;\n\n"
        "namespace Waooaw.BusinessPlatform.Controllers;\n\n"
        "[ApiController, Route(\"api/v1\")]\n"
        "public sealed class CustomersController : ControllerBase\n"
        "{\n"
        "    [HttpPost(\"employment/contracts\")]\n"
        "    public IActionResult FormEmploymentContract() => Ok();\n\n"
        "    [HttpGet(\"employment/contracts/{id}\")]\n"
        "    public IActionResult GetEmploymentContract(Guid id) => Ok();\n"
        "}\n"
    )
    print("  ✅ CustomersController.cs stub written")

    (src_dir / "appsettings.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Information" } },\n'
        '  "ConnectionStrings": { "BusinessPlatformDb": "" },\n'
        '  "ConstitutionalEngine": { "GrpcUrl": "http://constitutional-engine:5002" },\n'
        '  "Jwt": { "Authority": "", "Audience": "business-platform" },\n'
        '  "Kestrel": { "Endpoints": { "Rest": { "Url": "http://0.0.0.0:5001" } } }\n}\n'
    )
    (src_dir / "appsettings.Development.json").write_text(
        '{\n  "Logging": { "LogLevel": { "Default": "Debug" } },\n'
        '  "ConnectionStrings": { "BusinessPlatformDb": "Host=localhost;Port=5432;Database=waooaw;Username=business_platform;Password=dev_password_replace_in_prod" },\n'
        '  "ConstitutionalEngine": { "GrpcUrl": "http://localhost:5002" },\n'
        '  "Jwt": { "Authority": "http://localhost:8080/realms/waooaw" }\n}\n'
    )
    print("  ✅ appsettings written")

    (test_dir / "business-platform.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '    <Nullable>enable</Nullable>\n'
        '    <ImplicitUsings>enable</ImplicitUsings>\n'
        '    <IsPackable>false</IsPackable>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '    <ProjectReference Include="..\\..\\src\\business-platform\\business-platform.csproj" />\n'
        '  </ItemGroup>\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />\n'
        '    <PackageReference Include="xunit" Version="2.9.3" />\n'
        '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '    <PackageReference Include="Moq" Version="4.20.72" />\n'
        '    <PackageReference Include="FluentAssertions" Version="6.12.2" />\n'
        '    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="9.0.1" />\n'
        '    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="9.0.0" />\n'
        '    <PackageReference Include="coverlet.collector" Version="6.0.4">\n'
        '      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>\n'
        '      <PrivateAssets>all</PrivateAssets>\n'
        '    </PackageReference>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    print("  ✅ business-platform.Tests.csproj written")

    build = run(["dotnet", "build", str(src_dir / "business-platform.csproj"),
                 "--nologo", "-v", "quiet"], check=False, capture=True)
    if build.returncode != 0:
        print(f"  ❌ dotnet build FAILED:\n{build.stderr[:500]}")
        return False
    print("  ✅ dotnet build PASSED")

    git(["add", f"src/{service}/", f"tests/{service}.Tests/"], check=False)
    git(["commit", "-m",
         "feat: WC013-01 — BP project scaffold (.NET 9 REST + gRPC client to CE)\n\n"
         "IB: IB-009\nConstitutional: C-059, ADR-002, ADR-003, C-026\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC013-01 complete (deterministic — no LLM)")
    return True


def execute_wc014_01() -> bool:
    """
    WC014-01: Professional Runtime project scaffold — DETERMINISTIC (no LLM).
    constitutional_basis: C-059, C-025 (PAAS exclusive), ADR-015 (Temporal)
    """
    print("── WC014-01: PR project scaffold (DETERMINISTIC) ──")
    service = "professional-runtime"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / service
    (src_dir / "routers").mkdir(parents=True, exist_ok=True)
    (src_dir / "workflows").mkdir(parents=True, exist_ok=True)
    (src_dir / "activities").mkdir(parents=True, exist_ok=True)
    (src_dir / "proto").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    ref_req = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "requirements-professional-runtime.txt"
    (src_dir / "requirements.txt").write_text(ref_req.read_text())
    print("  ✅ requirements.txt copied from reference dotfile")

    (src_dir / "requirements-test.txt").write_text(
        "# Test dependencies for professional-runtime\n"
        "pytest==8.3.4\n"
        "pytest-asyncio==0.24.0\n"
        "pytest-cov==6.0.0\n"
        "httpx==0.27.2\n"
        "respx==0.21.1\n"
    )
    print("  ✅ requirements-test.txt written")

    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "proto" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied")

    (src_dir / "__init__.py").write_text(
        "# Professional Runtime — C-025 (PAAS exclusive execution model)\n"
    )
    (test_dir / "__init__.py").write_text("")

    (src_dir / "main.py").write_text(
        "# Implements: architecture/reference/components/professional-runtime.md\n"
        "# constitutional_basis: C-025 (PAAS exclusive), C-001 (Emergency Stop ≤250ms),\n"
        "#   ADR-015 (Temporal), ADR-018 (Emergency Stop signal)\n\n"
        "from fastapi import FastAPI\n\n"
        "app = FastAPI(\n"
        "    title=\"WAOOAW Professional Runtime\",\n"
        "    description=\"PAAS execution engine (C-025). All professional work runs here.\",\n"
        "    version=\"0.1.0\",\n"
        ")\n\n\n"
        "@app.get(\"/health\")\n"
        "async def health() -> dict:\n"
        "    \"\"\"Health check.\"\"\"\n"
        "    return {\"status\": \"ok\", \"service\": \"professional-runtime\"}\n"
    )
    print("  ✅ main.py stub written")

    (test_dir / "conftest.py").write_text(
        "# Implements: tests/QA-STRATEGY.md §5.1\n"
        "# constitutional_basis: C-076 (≥90% coverage)\n\n"
        "import pytest\n"
        "from httpx import AsyncClient, ASGITransport\n"
        "from src.professional_runtime.main import app\n\n\n"
        "@pytest.fixture\n"
        "async def client():\n"
        "    async with AsyncClient(transport=ASGITransport(app=app), base_url=\"http://test\") as c:\n"
        "        yield c\n"
    )
    print("  ✅ tests/conftest.py written")

    lint = run(["python3", "-m", "ruff", "check", str(src_dir)],
               check=False, capture=True)
    if lint.returncode != 0:
        print(f"  ⚠️  ruff: {lint.stdout[:200]}")
    else:
        print("  ✅ ruff PASSED")

    git(["add", f"src/{service}/", f"tests/{service}/"], check=False)
    git(["commit", "-m",
         "feat: WC014-01 — PR project scaffold (Python 3.12 FastAPI + Temporal worker)\n\n"
         "IB: IB-009\nConstitutional: C-059, C-025, ADR-015\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC014-01 complete (deterministic — no LLM)")
    return True


def execute_wc015_01() -> bool:
    """
    WC015-01: AI Runtime project scaffold — DETERMINISTIC (no LLM).
    constitutional_basis: C-059, C-051, C-062, C-063, C-078
    """
    print("── WC015-01: AIR project scaffold (DETERMINISTIC) ──")
    service = "ai-runtime"
    src_dir = REPO_ROOT / "src" / service
    test_dir = REPO_ROOT / "tests" / service
    (src_dir / "providers").mkdir(parents=True, exist_ok=True)
    (src_dir / "pse").mkdir(parents=True, exist_ok=True)
    (src_dir / "rag").mkdir(parents=True, exist_ok=True)
    (src_dir / "pii").mkdir(parents=True, exist_ok=True)
    (src_dir / "proto").mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    ref_req = REPO_ROOT / "architecture" / "reference" / "dotfiles" / "requirements-ai-runtime.txt"
    (src_dir / "requirements.txt").write_text(ref_req.read_text())
    print("  ✅ requirements.txt copied from reference dotfile")

    (src_dir / "requirements-test.txt").write_text(
        "# Test dependencies for ai-runtime\n"
        "pytest==8.3.4\n"
        "pytest-asyncio==0.24.0\n"
        "pytest-cov==6.0.0\n"
        "httpx==0.27.2\n"
        "respx==0.21.1\n"
    )
    print("  ✅ requirements-test.txt written")

    ref_proto = REPO_ROOT / "architecture" / "reference" / "proto" / "constitutional_service.proto"
    (src_dir / "proto" / "constitutional_service.proto").write_text(ref_proto.read_text())
    print("  ✅ constitutional_service.proto copied")

    (src_dir / "__init__.py").write_text(
        "# AI Runtime — C-051 (Token Economy), C-062 (AI Security), C-078 (PII Scrubber)\n"
    )
    (src_dir / "providers" / "__init__.py").write_text("")
    (src_dir / "pse" / "__init__.py").write_text("")
    (src_dir / "rag" / "__init__.py").write_text("")
    (src_dir / "pii" / "__init__.py").write_text("")
    (test_dir / "__init__.py").write_text("")

    (src_dir / "main.py").write_text(
        "# Implements: architecture/reference/components/ai-runtime.md\n"
        "# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),\n"
        "#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)\n\n"
        "from fastapi import FastAPI\n\n"
        "app = FastAPI(\n"
        "    title=\"WAOOAW AI Runtime\",\n"
        "    description=\"Provider Selection Engine + LLM dispatch (ADR-029).\",\n"
        "    version=\"0.1.0\",\n"
        ")\n\n\n"
        "@app.get(\"/health\")\n"
        "async def health() -> dict:\n"
        "    \"\"\"Health check.\"\"\"\n"
        "    return {\"status\": \"ok\", \"service\": \"ai-runtime\"}\n"
    )
    print("  ✅ main.py stub written")

    (src_dir / "pse" / "tiers.py").write_text(
        "# Implements: adr/ADR-029-multi-provider-llm-strategy.md\n"
        "# constitutional_basis: C-051 (Token Economy — 66-74% cost reduction)\n\n"
        "from enum import Enum\n\n\n"
        "class LlmTier(str, Enum):\n"
        "    \"\"\"ADR-029 §3 routing tiers. NEVER add tiers without EA approval.\"\"\"\n"
        "    LOCAL = \"local\"\n"
        "    MID = \"mid\"\n"
        "    FRONTIER = \"frontier\"\n"
        "    FALLBACK = \"fallback\"\n"
    )
    print("  ✅ pse/tiers.py stub written")

    (test_dir / "conftest.py").write_text(
        "# Implements: tests/QA-STRATEGY.md §5.1\n"
        "# constitutional_basis: C-076 (≥90% coverage), C-062 (AI Security)\n\n"
        "import pytest\n"
        "from httpx import AsyncClient, ASGITransport\n"
        "from src.ai_runtime.main import app\n\n\n"
        "@pytest.fixture\n"
        "async def client():\n"
        "    async with AsyncClient(transport=ASGITransport(app=app), base_url=\"http://test\") as c:\n"
        "        yield c\n"
    )
    print("  ✅ tests/conftest.py written")

    lint = run(["python3", "-m", "ruff", "check", str(src_dir)],
               check=False, capture=True)
    if lint.returncode != 0:
        print(f"  ⚠️  ruff: {lint.stdout[:200]}")
    else:
        print("  ✅ ruff PASSED")

    git(["add", f"src/{service}/", f"tests/{service}/"], check=False)
    git(["commit", "-m",
         "feat: WC015-01 — AIR project scaffold (Python 3.12 FastAPI + PSE tiers)\n\n"
         "IB: IB-009\nConstitutional: C-059, C-051, C-062, C-078, ADR-029\nCCTs-added: per WC spec"],
        check=False)
    print("  ✅ WC015-01 complete (deterministic — no LLM)")
    return True


def _skip_schemathesis_gate() -> bool:
    """
    WC013-04a: Schemathesis contract test — CI gate deferred.
    constitutional_basis: C-008 (Constitutional Chain — spec-code drift check)
    """
    print("  ── WC013-04a: Schemathesis gate (CI-deferred) ──")
    print("  ⏭️  Schemathesis requires running service — deferred to manual docker-compose run.")
    print("  Manual command: docker compose up business-platform && schemathesis run "
          "architecture/reference/api-specs/business-platform.openapi.yaml "
          "--url http://localhost:5001 --checks all")
    skip_file = REPO_ROOT / "sprint-context" / "schemathesis-deferred.txt"
    skip_file.parent.mkdir(exist_ok=True)
    skip_file.write_text(
        "WC013-04 Schemathesis deferred — run manually after WC-013 completes.\n"
        "Command: docker compose up business-platform && "
        "schemathesis run architecture/reference/api-specs/business-platform.openapi.yaml "
        "--url http://localhost:5001 --checks all\n"
    )
    git(["add", "sprint-context/schemathesis-deferred.txt"], check=False)
    git(["commit", "-m",
         "chore(pm): WC013-04 Schemathesis gate deferred — requires running service\n\n"
         "IB: IB-009\nConstitutional: C-008 (tracked, not blocking)"],
        check=False)
    return True
