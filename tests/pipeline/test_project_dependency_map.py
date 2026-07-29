"""
test_project_dependency_map.py — Unit tests for ProjectDependencyMap

# Implements: scripts/project_dependency_map.py
# Constitutional basis: C-076 (≥90% coverage), C-082 (build validation)
# Office: Platform IT Expert (INST-010)
# IB: IB-009
"""
from __future__ import annotations

import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import project_dependency_map as pdm


# ── Fixtures ──────────────────────────────────────────────────────────────────

CE_CSPROJ = REPO_ROOT / "src/constitutional-engine/constitutional-engine.csproj"
CE_TESTS_CSPROJ = REPO_ROOT / "tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj"

# Synthetic BP csproj content for tests (mirrors what WC013-01 will create)
BP_CSPROJ_XML = textwrap.dedent("""\
    <Project Sdk="Microsoft.NET.Sdk.Web">
      <PropertyGroup>
        <TargetFramework>net9.0</TargetFramework>
        <RootNamespace>Waooaw.BusinessPlatform</RootNamespace>
        <AssemblyName>BusinessPlatform</AssemblyName>
      </PropertyGroup>
      <ItemGroup>
        <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="9.0.0" />
        <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="9.0.0" />
        <PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.0.1" />
        <PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" Version="9.0.4" />
        <PackageReference Include="Grpc.Net.Client" Version="2.67.0" />
        <PackageReference Include="Google.Protobuf" Version="3.28.0" />
        <PackageReference Include="Grpc.Tools" Version="2.67.0" />
        <PackageReference Include="OpenTelemetry.Extensions.Hosting" Version="1.11.2" />
      </ItemGroup>
      <ItemGroup>
        <Protobuf Include="Protos/constitutional_service.proto" GrpcServices="Client" />
      </ItemGroup>
    </Project>
""")

CE_CSPROJ_XML = textwrap.dedent("""\
    <Project Sdk="Microsoft.NET.Sdk.Web">
      <PropertyGroup>
        <RootNamespace>Waooaw.ConstitutionalEngine</RootNamespace>
        <AssemblyName>ConstitutionalEngine</AssemblyName>
      </PropertyGroup>
      <ItemGroup>
        <PackageReference Include="Grpc.AspNetCore" Version="2.67.0" />
        <PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.0.1" />
        <PackageReference Include="OpenTelemetry.Extensions.Hosting" Version="1.11.2" />
        <PackageReference Include="Temporalio" Version="0.1.0-beta1" />
      </ItemGroup>
      <ItemGroup>
        <Protobuf Include="Protos/constitutional_service.proto" GrpcServices="Server" />
      </ItemGroup>
    </Project>
""")

PROTO_CONTENT = 'option csharp_namespace = "Waooaw.ConstitutionalEngine.Grpc";'


# ══════════════════════════════════════════════════════════════════════════════
# Part 1: _namespaces_for_package
# ══════════════════════════════════════════════════════════════════════════════

class TestNugetNamespaceMapping:
    def test_known_grpc_client(self):
        result = pdm._namespaces_for_package("Grpc.Net.Client")
        assert "Grpc.Net.Client" in result

    def test_known_grpc_aspnetcore(self):
        result = pdm._namespaces_for_package("Grpc.AspNetCore")
        assert "Grpc.Core" in result

    def test_known_ef_core(self):
        result = pdm._namespaces_for_package("Microsoft.EntityFrameworkCore")
        assert "Microsoft.EntityFrameworkCore" in result

    def test_known_npgsql_efcore(self):
        result = pdm._namespaces_for_package("Npgsql.EntityFrameworkCore.PostgreSQL")
        assert "Npgsql" in result

    def test_grpc_tools_returns_empty(self):
        """Grpc.Tools is codegen only — no runtime namespace."""
        result = pdm._namespaces_for_package("Grpc.Tools")
        assert result == []

    def test_known_temporalio(self):
        result = pdm._namespaces_for_package("Temporalio")
        assert "Temporalio" in result

    def test_opentelemetry_prefix_match(self):
        result = pdm._namespaces_for_package("OpenTelemetry.Extensions.Hosting")
        assert "OpenTelemetry" in result

    def test_microsoft_aspnetcore_jwt(self):
        result = pdm._namespaces_for_package("Microsoft.AspNetCore.Authentication.JwtBearer")
        assert any("Microsoft.AspNetCore" in ns or "Microsoft.Extensions" in ns for ns in result)

    def test_unknown_package_heuristic_thirdparty(self):
        """Unknown third-party package: use first segment as prefix."""
        result = pdm._namespaces_for_package("Serilog.Sinks.Console")
        assert "Serilog" in result

    def test_unknown_package_microsoft_heuristic(self):
        """Unknown Microsoft package: use first two segments."""
        result = pdm._namespaces_for_package("Microsoft.Diagnostics.Runtime")
        assert "Microsoft.Diagnostics" in result

    def test_empty_package_id(self):
        result = pdm._namespaces_for_package("")
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# Part 2: _read_proto_namespace
# ══════════════════════════════════════════════════════════════════════════════

class TestReadProtoNamespace:
    def test_reads_csharp_namespace(self, tmp_path):
        proto = tmp_path / "test.proto"
        proto.write_text('option csharp_namespace = "My.Proto.Ns";')
        assert pdm._read_proto_namespace(proto) == "My.Proto.Ns"

    def test_missing_file_returns_none(self, tmp_path):
        assert pdm._read_proto_namespace(tmp_path / "missing.proto") is None

    def test_no_csharp_namespace_returns_none(self, tmp_path):
        proto = tmp_path / "test.proto"
        proto.write_text('package constitutional.v1;\nmessage Foo {}')
        assert pdm._read_proto_namespace(proto) is None


# ══════════════════════════════════════════════════════════════════════════════
# Part 3: find_csproj_for_file
# ══════════════════════════════════════════════════════════════════════════════

class TestFindCsprojForFile:
    def test_finds_csproj_in_parent(self, tmp_path):
        csproj = tmp_path / "myproject" / "myproject.csproj"
        csproj.parent.mkdir()
        csproj.write_text("<Project />")
        target = tmp_path / "myproject" / "Controllers" / "Foo.cs"
        target.parent.mkdir()
        target.write_text("// code")

        found = pdm.find_csproj_for_file(
            "myproject/Controllers/Foo.cs", tmp_path
        )
        assert found == csproj

    def test_returns_none_when_no_csproj(self, tmp_path):
        target = tmp_path / "src" / "Foo.cs"
        target.parent.mkdir()
        target.write_text("// code")
        result = pdm.find_csproj_for_file("src/Foo.cs", tmp_path)
        assert result is None

    def test_finds_ce_csproj_on_real_repo(self):
        """Integration: verify CE csproj is found for a CE source file."""
        if not CE_CSPROJ.exists():
            pytest.skip("CE csproj not present")
        found = pdm.find_csproj_for_file(
            "src/constitutional-engine/Evaluators/EvaluatorRegistry.cs",
            REPO_ROOT,
        )
        assert found is not None
        assert found.name == "constitutional-engine.csproj"


# ══════════════════════════════════════════════════════════════════════════════
# Part 4: get_reachable_prefixes (via synthetic csproj)
# ══════════════════════════════════════════════════════════════════════════════

class TestGetReachablePrefixes:
    def _make_csproj(self, tmp_path: Path, content: str, proto_ns: str = "") -> Path:
        """Write a synthetic .csproj and optional .proto file, return csproj path."""
        proj_dir = tmp_path / "myproj"
        proj_dir.mkdir(exist_ok=True)
        csproj = proj_dir / "myproj.csproj"
        csproj.write_text(content)
        if proto_ns:
            proto_dir = proj_dir / "Protos"
            proto_dir.mkdir(exist_ok=True)
            # Must match the Include path in BP_CSPROJ_XML
            (proto_dir / "constitutional_service.proto").write_text(
                f'option csharp_namespace = "{proto_ns}";'
            )
        return csproj

    def test_bp_scenario_grpc_reachable(self, tmp_path):
        """CE gRPC namespace IS reachable via Protobuf include."""
        csproj = self._make_csproj(
            tmp_path, BP_CSPROJ_XML, proto_ns="Waooaw.ConstitutionalEngine.Grpc"
        )
        # Clear lru_cache to avoid cross-test pollution
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(csproj)
        assert "Waooaw.ConstitutionalEngine.Grpc" in prefixes

    def test_bp_scenario_ce_evaluators_not_reachable(self, tmp_path):
        """CE.Evaluators is NOT reachable from BP (no ProjectReference to CE)."""
        csproj = self._make_csproj(
            tmp_path, BP_CSPROJ_XML, proto_ns="Waooaw.ConstitutionalEngine.Grpc"
        )
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(csproj)
        assert "Waooaw.ConstitutionalEngine.Evaluators" not in prefixes
        # Root CE namespace also not reachable (only Grpc sub-namespace via proto)
        assert "Waooaw.ConstitutionalEngine" not in prefixes

    def test_bp_self_namespace_reachable(self, tmp_path):
        csproj = self._make_csproj(tmp_path, BP_CSPROJ_XML)
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(csproj)
        assert "Waooaw.BusinessPlatform" in prefixes

    def test_implicit_prefixes_always_present(self, tmp_path):
        csproj = self._make_csproj(tmp_path, BP_CSPROJ_XML)
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(csproj)
        assert "System" in prefixes
        assert "Microsoft.Extensions.Logging" in prefixes

    def test_project_reference_namespaces_included(self, tmp_path):
        """ProjectReference to CE adds CE's RootNamespace to reachable set."""
        ref_proj = tmp_path / "ce"
        ref_proj.mkdir()
        (ref_proj / "ce.csproj").write_text(CE_CSPROJ_XML)

        test_xml = textwrap.dedent(f"""\
            <Project Sdk="Microsoft.NET.Sdk">
              <PropertyGroup>
                <RootNamespace>My.Tests</RootNamespace>
              </PropertyGroup>
              <ItemGroup>
                <ProjectReference Include="../ce/ce.csproj" />
              </ItemGroup>
            </Project>
        """)
        test_proj = tmp_path / "tests"
        test_proj.mkdir()
        csproj = test_proj / "tests.csproj"
        csproj.write_text(test_xml)

        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(csproj)
        assert "Waooaw.ConstitutionalEngine" in prefixes

    def test_real_ce_csproj(self):
        """Integration: verify CE csproj reachable prefixes are correct."""
        if not CE_CSPROJ.exists():
            pytest.skip("CE csproj not present")
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(CE_CSPROJ)
        assert "Waooaw.ConstitutionalEngine" in prefixes
        assert "Waooaw.ConstitutionalEngine.Grpc" in prefixes
        assert "Temporalio" in prefixes
        assert "Microsoft.EntityFrameworkCore" in prefixes

    def test_real_ce_tests_csproj(self):
        """Integration: CE.Tests has ProjectReference to CE — should see CE namespaces."""
        if not CE_TESTS_CSPROJ.exists():
            pytest.skip("CE Tests csproj not present")
        pdm.get_reachable_prefixes.cache_clear()
        prefixes = pdm.get_reachable_prefixes(CE_TESTS_CSPROJ)
        assert "Waooaw.ConstitutionalEngine" in prefixes
        assert "Moq" in prefixes
        assert "FluentAssertions" in prefixes


# ══════════════════════════════════════════════════════════════════════════════
# Part 5: is_namespace_reachable
# ══════════════════════════════════════════════════════════════════════════════

class TestIsNamespaceReachable:
    def _bp_csproj(self, tmp_path: Path) -> Path:
        proj_dir = tmp_path / "bp"
        proj_dir.mkdir()
        csproj = proj_dir / "bp.csproj"
        csproj.write_text(BP_CSPROJ_XML)
        proto_dir = proj_dir / "Protos"
        proto_dir.mkdir()
        # Must match Include path in BP_CSPROJ_XML
        (proto_dir / "constitutional_service.proto").write_text(
            'option csharp_namespace = "Waooaw.ConstitutionalEngine.Grpc";'
        )
        pdm.get_reachable_prefixes.cache_clear()
        return csproj

    def test_grpc_namespace_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert pdm.is_namespace_reachable("Waooaw.ConstitutionalEngine.Grpc", csproj)

    def test_evaluators_not_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert not pdm.is_namespace_reachable("Waooaw.ConstitutionalEngine.Evaluators", csproj)

    def test_services_not_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert not pdm.is_namespace_reachable("Waooaw.ConstitutionalEngine.Services", csproj)

    def test_emergency_stop_not_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert not pdm.is_namespace_reachable("Waooaw.ConstitutionalEngine.EmergencyStop", csproj)

    def test_self_namespace_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert pdm.is_namespace_reachable("Waooaw.BusinessPlatform.Controllers", csproj)

    def test_system_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert pdm.is_namespace_reachable("System.Threading.Tasks", csproj)

    def test_ef_core_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert pdm.is_namespace_reachable("Microsoft.EntityFrameworkCore", csproj)


# ══════════════════════════════════════════════════════════════════════════════
# Part 6: filter_using_map
# ══════════════════════════════════════════════════════════════════════════════

class TestFilterUsingMap:
    def _bp_csproj(self, tmp_path: Path) -> Path:
        proj_dir = tmp_path / "bp"
        proj_dir.mkdir()
        csproj = proj_dir / "bp.csproj"
        csproj.write_text(BP_CSPROJ_XML)
        (proj_dir / "Protos").mkdir()
        (proj_dir / "Protos" / "constitutional_service.proto").write_text(
            'option csharp_namespace = "Waooaw.ConstitutionalEngine.Grpc";'
        )
        pdm.get_reachable_prefixes.cache_clear()
        return csproj

    def test_removes_unreachable_types(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        using_map = {
            "EvaluationContext": "Waooaw.ConstitutionalEngine.Evaluators",
            "ConstitutionalServiceClient": "Waooaw.ConstitutionalEngine.Grpc",
            "DbContext": "Microsoft.EntityFrameworkCore",
        }
        filtered = pdm.filter_using_map(using_map, csproj)
        assert "EvaluationContext" not in filtered
        assert "ConstitutionalServiceClient" in filtered
        assert "DbContext" in filtered

    def test_preserves_all_reachable(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        using_map = {
            "GrpcChannel": "Grpc.Net.Client",
            "ILogger": "Microsoft.Extensions.Logging",
        }
        filtered = pdm.filter_using_map(using_map, csproj)
        assert filtered == using_map

    def test_empty_map_returns_empty(self, tmp_path):
        csproj = self._bp_csproj(tmp_path)
        assert pdm.filter_using_map({}, csproj) == {}


# ══════════════════════════════════════════════════════════════════════════════
# Part 7: get_boundary_injection_text
# ══════════════════════════════════════════════════════════════════════════════

class TestGetBoundaryInjectionText:
    def test_contains_project_name(self, tmp_path):
        proj_dir = tmp_path / "my-service"
        proj_dir.mkdir()
        csproj = proj_dir / "my-service.csproj"
        csproj.write_text("<Project><PropertyGroup><RootNamespace>My.Service</RootNamespace></PropertyGroup></Project>")
        pdm.get_reachable_prefixes.cache_clear()
        text = pdm.get_boundary_injection_text(csproj)
        assert "my-service" in text
        assert "PROJECT BOUNDARY" in text

    def test_contains_forbidden_instruction(self, tmp_path):
        proj_dir = tmp_path / "bp"
        proj_dir.mkdir()
        csproj = proj_dir / "bp.csproj"
        csproj.write_text(BP_CSPROJ_XML)
        pdm.get_reachable_prefixes.cache_clear()
        text = pdm.get_boundary_injection_text(csproj)
        assert "⛔" in text
        assert "ProjectReference" in text or "PackageReference" in text

    def test_lists_reachable_prefixes(self, tmp_path):
        proj_dir = tmp_path / "bp"
        proj_dir.mkdir()
        csproj = proj_dir / "bp.csproj"
        csproj.write_text(BP_CSPROJ_XML)
        pdm.get_reachable_prefixes.cache_clear()
        text = pdm.get_boundary_injection_text(csproj)
        assert "Waooaw.BusinessPlatform" in text
        assert "System" in text


# ══════════════════════════════════════════════════════════════════════════════
# Part 8: Integration with retry advisor generic handler
# ══════════════════════════════════════════════════════════════════════════════

class TestRetryAdvisorIntegration:
    """Verify diagnose_build_error routes CS0234 through OUT_OF_BOUNDARY when
    output_file is provided and csproj exists on disk."""

    def test_cs0234_evaluators_triggers_out_of_boundary(self, tmp_path):
        """CS0234 for CE.Evaluators in BP → OUT_OF_BOUNDARY handler fires."""
        # Set up synthetic BP project
        proj_dir = tmp_path / "business-platform"
        proj_dir.mkdir()
        csproj = proj_dir / "business-platform.csproj"
        csproj.write_text(BP_CSPROJ_XML)
        (proj_dir / "Protos").mkdir()
        (proj_dir / "Protos" / "svc.proto").write_text(
            'option csharp_namespace = "Waooaw.ConstitutionalEngine.Grpc";'
        )
        pdm.get_reachable_prefixes.cache_clear()

        from sprint_retry_advisor import diagnose_build_error, WRONG_NAMESPACE
        from project_dependency_map import REPO_ROOT as _orig_root
        import project_dependency_map as _pdm_mod

        orig_root = _pdm_mod.REPO_ROOT
        _pdm_mod.REPO_ROOT = tmp_path
        try:
            error = (
                "error CS0234: The type or namespace name 'Evaluators' "
                "does not exist in the namespace 'Waooaw.ConstitutionalEngine' "
                "(are you missing an assembly reference?)"
            )
            diag = diagnose_build_error(
                "WC013-03a:CustomersController.cs",
                error,
                [],
                output_file="business-platform/Controllers/CustomersController.cs",
            )
            assert diag.error_type == WRONG_NAMESPACE
            assert diag.confidence >= 0.90
            assert "boundary" in diag.fix_instruction.lower() or "reachable" in diag.fix_instruction.lower()
        finally:
            _pdm_mod.REPO_ROOT = orig_root

    def test_cs0234_fallback_when_no_csproj(self):
        """CS0234 with no output_file falls through to cs0234 specific handler."""
        from sprint_retry_advisor import diagnose_build_error, WRONG_NAMESPACE
        error = (
            "error CS0234: The type or namespace name 'Evaluators' "
            "does not exist in the namespace 'Waooaw.ConstitutionalEngine' "
            "(are you missing an assembly reference?)"
        )
        diag = diagnose_build_error(
            "WC013-03a:CustomersController.cs",
            error,
            [],
            output_file="",  # no output file → generic handler skips
        )
        # Falls through to the CS0234 specific handler
        assert diag.error_type == WRONG_NAMESPACE

    def test_reachable_namespace_does_not_trigger_out_of_boundary(self, tmp_path):
        """CS0246 for a bare type name (not a dotted namespace) should NOT fire
        OUT_OF_BOUNDARY even if the type doesn't exist — let type handlers deal with it."""
        proj_dir = tmp_path / "myproj"
        proj_dir.mkdir()
        csproj = proj_dir / "myproj.csproj"
        csproj.write_text(
            "<Project><PropertyGroup>"
            "<RootNamespace>My.Project</RootNamespace>"
            "</PropertyGroup>"
            "<ItemGroup><PackageReference Include=\"Moq\" Version=\"4.0\" /></ItemGroup>"
            "</Project>"
        )
        pdm.get_reachable_prefixes.cache_clear()

        from sprint_retry_advisor import diagnose_build_error
        import project_dependency_map as _pdm_mod
        orig_root = _pdm_mod.REPO_ROOT
        _pdm_mod.REPO_ROOT = tmp_path
        try:
            # 'Mock' is a bare type name (no dots) — boundary handler must NOT fire
            error = "error CS0246: The type or namespace name 'Mock' could not be found"
            diag = diagnose_build_error(
                "test:Foo.cs",
                error,
                [],
                output_file="myproj/Foo.cs",
            )
            # Generic boundary handler must be skipped for bare type names
            assert "OUT_OF_BOUNDARY" not in str(diag) or "boundary" not in diag.fix_instruction.lower()
        finally:
            _pdm_mod.REPO_ROOT = orig_root
