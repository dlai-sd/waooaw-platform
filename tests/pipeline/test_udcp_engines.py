# Implements: WC-036 — WC036-06
# constitutional_basis: C-076 (≥90% test coverage), C-082 (Build Validation),
#                       C-097 (Property-Based Testing), C-098 (Architectural Fitness)
from __future__ import annotations

import ast
import json
import sys
import textwrap
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ensure scripts/ is on path for runner.* imports
_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from runner.ptr_validation_gate import WorkspaceSymbolIndex, _is_external
from runner.track1_scaffolder import (
    Track1ScaffoldError,
    Track1Scaffolder,
    _compile_gate,
    _needs_router,
    _render_args,
    _render_class,
    _render_function,
)
from runner.track2_polymorphic_engine import (
    Track2PolymorphicEngine,
    Track2SpliceError,
    _signature_string,
)
from runner.udcp_grooming_engine import UDCPGroomingEngine, _path_to_func_name


# ── WorkspaceSymbolIndex ──────────────────────────────────────────────────────

class TestWorkspaceSymbolIndex:
    def test_index_finds_classes_and_functions(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "models.py").write_text(
            "class MyModel:\n    pass\n\ndef my_func():\n    pass\n"
        )
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        assert "mypkg.models" in result
        assert "MyModel" in result["mypkg.models"]
        assert "my_func" in result["mypkg.models"]

    def test_index_resolves_reexports(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "from pkg.models import Foo\nfrom pkg.models import Bar as Baz\n"
        )
        (pkg / "models.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        assert "Foo" in result["pkg"]
        assert "Baz" in result["pkg"]

    def test_validate_tis_passes_on_known_symbols(self, tmp_path: Path) -> None:
        pkg = tmp_path / "markup"
        pkg.mkdir()
        (pkg / "models.py").write_text("class BundleProfile:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [
                {
                    "file_path": "markup/bundle_engine.py",
                    "imports": [{"from": "markup.models", "import": ["BundleProfile"]}],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        assert errors == []

    def test_validate_tis_rejects_invented_symbol(self, tmp_path: Path) -> None:
        pkg = tmp_path / "markup"
        pkg.mkdir()
        (pkg / "models.py").write_text("class BundleProfile:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [
                {
                    "file_path": "markup/bundle_engine.py",
                    "imports": [
                        {"from": "markup.models", "import": ["PriceDeriveResponse"]}
                    ],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        assert any("PriceDeriveResponse" in e for e in errors)

    def test_validate_tis_rejects_missing_module(self, tmp_path: Path) -> None:
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [
                {
                    "file_path": "x.py",
                    "imports": [{"from": "nonexistent.module", "import": ["Thing"]}],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        assert any("nonexistent.module" in e for e in errors)

    def test_skips_external_modules(self, tmp_path: Path) -> None:
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [
                {
                    "file_path": "x.py",
                    "imports": [
                        {"from": "fastapi", "import": ["APIRouter", "Depends"]},
                        {"from": "pydantic", "import": ["BaseModel"]},
                        {"from": "os", "import": ["path"]},
                    ],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        assert errors == []

    def test_wildcard_reexport_skips_name_check(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("from pkg.models import *\n")
        (pkg / "models.py").write_text("class Foo:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [
                {
                    "file_path": "x.py",
                    "imports": [{"from": "pkg", "import": ["Foo", "Bar"]}],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        # Wildcard present — names not individually verifiable, no errors expected
        assert errors == []

    def test_is_external(self) -> None:
        assert _is_external("fastapi") is True
        assert _is_external("fastapi.routing") is True
        assert _is_external("markup.models") is False
        assert _is_external("os") is True


# ── Track1Scaffolder ──────────────────────────────────────────────────────────

class TestTrack1Scaffolder:
    def _minimal_tis(self, file_path: str, interfaces: list) -> dict:
        return {
            "sprint_id": "WC-027",
            "task_id": "WC027-01",
            "target_artifacts": [
                {
                    "file_path": file_path,
                    "imports": [
                        {"from": "fastapi", "import": ["APIRouter"]},
                    ],
                    "interfaces": interfaces,
                }
            ],
        }

    def test_scaffold_produces_compilable_file(self, tmp_path: Path) -> None:
        tis = self._minimal_tis(
            "markup/router.py",
            [
                {
                    "type": "function",
                    "name": "derive_price",
                    "decorators": ["router.post('/derive')"],
                    "arguments": [],
                    "return_type": "dict",
                    "docstring": "Derive price.",
                }
            ],
        )
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        assert len(paths) == 1
        content = paths[0].read_text()
        compile(content, "test", "exec")  # must not raise

    def test_router_emitted_when_route_decorator_present(self, tmp_path: Path) -> None:
        tis = self._minimal_tis(
            "markup/router.py",
            [
                {
                    "type": "function",
                    "name": "get_catalog",
                    "decorators": ["router.get('/catalog')"],
                    "arguments": [],
                    "return_type": "list",
                    "docstring": "",
                }
            ],
        )
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        content = paths[0].read_text()
        assert "router = APIRouter()" in content

    def test_no_router_when_no_route_decorators(self, tmp_path: Path) -> None:
        tis = self._minimal_tis(
            "markup/models.py",
            [
                {
                    "type": "function",
                    "name": "helper",
                    "decorators": [],
                    "arguments": [],
                    "return_type": "None",
                    "docstring": "",
                }
            ],
        )
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        content = paths[0].read_text()
        assert "router = APIRouter()" not in content

    def test_filler_markers_present_in_function_stub(self, tmp_path: Path) -> None:
        tis = self._minimal_tis(
            "markup/service.py",
            [
                {
                    "type": "function",
                    "name": "cost_floor",
                    "decorators": [],
                    "arguments": [{"name": "agent_type", "type": "str"}],
                    "return_type": "int",
                    "docstring": "Returns cost floor.",
                }
            ],
        )
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        content = paths[0].read_text()
        assert "# [WAOOAW_LOGIC_FILLER_START]" in content
        assert "# [WAOOAW_LOGIC_FILLER_END]" in content

    def test_class_scaffold_with_fields(self, tmp_path: Path) -> None:
        tis = {
            "sprint_id": "WC-027",
            "task_id": "WC027-01a",
            "target_artifacts": [
                {
                    "file_path": "markup/models.py",
                    "imports": [{"from": "pydantic", "import": ["BaseModel"]}],
                    "interfaces": [
                        {
                            "type": "class",
                            "name": "BundleProfile",
                            "bases": ["BaseModel"],
                            "fields": [
                                {"name": "agent_type", "type": "str"},
                                {"name": "cost_floor_paise", "type": "int", "default": "0"},
                            ],
                            "docstring": "Bundle pricing profile.",
                        }
                    ],
                }
            ],
        }
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        content = paths[0].read_text()
        compile(content, "test", "exec")
        assert "class BundleProfile(BaseModel):" in content
        assert "agent_type: str" in content
        assert "cost_floor_paise: int = 0" in content

    def test_class_scaffold_no_fields_has_filler_markers(self, tmp_path: Path) -> None:
        tis = {
            "sprint_id": "WC-027",
            "task_id": "WC027-01a",
            "target_artifacts": [
                {
                    "file_path": "markup/models.py",
                    "imports": [{"from": "pydantic", "import": ["BaseModel"]}],
                    "interfaces": [
                        {
                            "type": "class",
                            "name": "ThreadEntry",
                            "bases": ["BaseModel"],
                            "fields": [],
                            "docstring": "",
                        }
                    ],
                }
            ],
        }
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        content = paths[0].read_text()
        assert "# [WAOOAW_LOGIC_FILLER_START]" in content

    def test_compile_gate_raises_on_bad_source(self) -> None:
        with pytest.raises(Track1ScaffoldError):
            _compile_gate("def bad(:\n    pass", "test.py")

    def test_needs_router_true(self) -> None:
        ifaces = [{"decorators": ["router.get('/x')"]}]
        assert _needs_router(ifaces) is True

    def test_needs_router_false(self) -> None:
        ifaces = [{"decorators": ["staticmethod"]}]
        assert _needs_router(ifaces) is False

    def test_render_args_with_defaults(self) -> None:
        args = [
            {"name": "x", "type": "int"},
            {"name": "y", "type": "str", "default": "'hello'"},
        ]
        result = _render_args(args)
        assert result == "x: int, y: str = 'hello'"


# ── Track2PolymorphicEngine ───────────────────────────────────────────────────

class TestTrack2PolymorphicEngine:
    def _make_service_file(self, tmp_path: Path) -> Path:
        src = textwrap.dedent("""\
            from __future__ import annotations

            class BundleEngine:
                @staticmethod
                def cost_floor(agent_type: str, bundle_tier: str) -> int:
                    \"\"\"Returns cost floor in paise.\"\"\"
                    return 0

                def derive_price(self, agent_type: str) -> int:
                    return 100
        """)
        path = tmp_path / "bundle_engine.py"
        path.write_text(src)
        return path

    def _make_test_file(self, tmp_path: Path) -> Path:
        src = textwrap.dedent("""\
            import pytest

            def test_cost_floor():
                assert True

            def test_derive_price():
                pass
        """)
        path = tmp_path / "test_bundle.py"
        path.write_text(src)
        return path

    def test_find_class_method(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        node = eng.find_target_node("cost_floor", "BundleEngine")
        assert node.name == "cost_floor"

    def test_find_top_level_function(self, tmp_path: Path) -> None:
        path = self._make_test_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        node = eng.find_target_node("test_cost_floor")
        assert node.name == "test_cost_floor"

    def test_find_raises_when_not_found(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        with pytest.raises(Track2SpliceError):
            eng.find_target_node("nonexistent", "BundleEngine")

    def test_extract_node_strips_decorators(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        result = eng.extract_node_for_llm("cost_floor", "BundleEngine")
        assert "staticmethod" not in result
        assert "def cost_floor" in result

    def test_extract_node_does_not_permanently_remove_decorators(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        # Extract once — should not mutate the on-disk AST
        eng.extract_node_for_llm("cost_floor", "BundleEngine")
        # Reload and verify decorators are still present in source
        content = path.read_text()
        assert "@staticmethod" in content

    def test_splice_method_with_new_logic(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        new_logic = textwrap.dedent("""\
            def derive_price(self, agent_type: str) -> int:
                return 999
        """)
        eng.splice_node_safely("derive_price", new_logic, "BundleEngine")
        new_content = path.read_text()
        compile(new_content, "test", "exec")
        assert "return 999" in new_content

    def test_splice_preserves_decorators(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        new_logic = textwrap.dedent("""\
            def cost_floor(agent_type: str, bundle_tier: str) -> int:
                return 500
        """)
        eng.splice_node_safely("cost_floor", new_logic, "BundleEngine")
        content = path.read_text()
        assert "@staticmethod" in content
        assert "return 500" in content

    def test_splice_top_level_function(self, tmp_path: Path) -> None:
        path = self._make_test_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        new_logic = textwrap.dedent("""\
            def test_cost_floor():
                assert 1 + 1 == 2
        """)
        eng.splice_node_safely("test_cost_floor", new_logic)
        content = path.read_text()
        assert "assert 1 + 1 == 2" in content

    def test_splice_rejects_signature_mutation(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        new_logic = textwrap.dedent("""\
            def derive_price(self, agent_type: str, extra_arg: int) -> int:
                return 0
        """)
        with pytest.raises(Track2SpliceError, match="mutated signature"):
            eng.splice_node_safely(
                "derive_price",
                new_logic,
                "BundleEngine",
                locked_signature="def derive_price(self, agent_type: str) -> int:",
            )

    def test_splice_compile_gate_rejects_bad_logic(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        bad_logic = "def derive_price(self, agent_type: str) -> int:\n    return !!!"
        with pytest.raises(Track2SpliceError, match="parse error|compile gate"):
            eng.splice_node_safely("derive_price", bad_logic, "BundleEngine")

    def test_splice_preserves_surrounding_methods(self, tmp_path: Path) -> None:
        path = self._make_service_file(tmp_path)
        eng = Track2PolymorphicEngine(path)
        new_logic = textwrap.dedent("""\
            def derive_price(self, agent_type: str) -> int:
                return 42
        """)
        eng.splice_node_safely("derive_price", new_logic, "BundleEngine")
        content = path.read_text()
        # cost_floor method must still be present
        assert "def cost_floor" in content

    def test_signature_string(self) -> None:
        src = "def f(x: int, y: str = 'a') -> bool:\n    return True\n"
        tree = ast.parse(src)
        node = tree.body[0]
        sig = _signature_string(node)
        # ast.unparse() omits spaces around = in keyword defaults
        assert sig == "def f(x: int, y: str='a') -> bool:"


# ── UDCPGroomingEngine ────────────────────────────────────────────────────────

class TestUDCPGroomingEngine:
    _WC027_01B_SCOPE = (
        "`src/billing-engine/markup/router.py` — FastAPI router prefix `/pricing`: "
        "`GET /thread-catalog` (delegates to thread_catalog.py), "
        "`GET /bundle-cost-floor/{agent_type}/{bundle_tier}`, "
        "`POST /validate` (422 body includes minimum_compliant_price_paise), "
        "`POST /derive`; mount router in `src/billing-engine/main.py`"
    )

    def test_detect_track_greenfield_no_files(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        assert groom.detect_track(["src/billing-engine/markup/router.py", "src/billing-engine/main.py"]) == "GREENFIELD"

    def test_detect_track_differential_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "src/billing-engine/markup").mkdir(parents=True)
        (tmp_path / "src/billing-engine/markup/router.py").write_text("# existing")
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        assert groom.detect_track(["src/billing-engine/markup/router.py", "src/billing-engine/main.py"]) in ("DIFFERENTIAL", "MIXED")

    def test_generate_tis_contains_file_paths(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01b", self._WC027_01B_SCOPE, "WC-027")
        file_paths = [a["file_path"] for a in tis["target_artifacts"]]
        assert "src/billing-engine/markup/router.py" in file_paths

    def test_generate_tis_detects_fastapi_imports(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01b", self._WC027_01B_SCOPE, "WC-027")
        router_artifact = next(
            a for a in tis["target_artifacts"]
            if "router.py" in a["file_path"]
        )
        import_froms = [i["from"] for i in router_artifact["imports"]]
        assert "fastapi" in import_froms

    def test_generate_tis_detects_fastapi_endpoints(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01b", self._WC027_01B_SCOPE, "WC-027")
        router_artifact = next(
            a for a in tis["target_artifacts"]
            if "router.py" in a["file_path"]
        )
        interface_names = [i.get("name") for i in router_artifact["interfaces"]]
        # At least some endpoints detected
        assert len(interface_names) > 0

    def test_pydantic_hint_triggers_basemodel_import(self, tmp_path: Path) -> None:
        scope = (
            "`src/billing-engine/markup/models.py` — Pydantic: "
            "`ThreadEntry`, `BundleProfile`, `PriceConfig`"
        )
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01a", scope, "WC-027")
        artifact = tis["target_artifacts"][0]
        import_froms = [i["from"] for i in artifact["imports"]]
        assert "pydantic" in import_froms

    def test_path_to_func_name(self) -> None:
        assert _path_to_func_name("get", "/thread-catalog") == "get_thread_catalog"
        assert _path_to_func_name("post", "/validate") == "post_validate"
        assert _path_to_func_name("get", "/bundle-cost-floor/{agent_type}/{bundle_tier}") == (
            "get_bundle_cost_floor_agent_type_bundle_tier"
        )

    def test_tis_structure_matches_schema(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01b", self._WC027_01B_SCOPE, "WC-027")
        assert tis["pipeline_track"] == "GREENFIELD"
        assert tis["sprint_id"] == "WC-027"
        assert tis["task_id"] == "WC027-01b"
        assert isinstance(tis["target_artifacts"], list)

    def test_skeleton_cross_reference(self, tmp_path: Path) -> None:
        skel_dir = tmp_path / "src/billing-engine/skeleton"
        skel_dir.mkdir(parents=True)
        skel_path = skel_dir / "wbe_interfaces.py"
        skel_path.write_text(
            "class IMarkupEngine:\n"
            "    def derive_price(self): ...\n"
        )
        scope = (
            "`src/billing-engine/markup/bundle_engine.py` — "
            "`BundleEngine` implementing `IMarkupEngine`"
        )
        groom = UDCPGroomingEngine(skeleton_path=skel_path, repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01a", scope, "WC-027")
        artifact = tis["target_artifacts"][0]
        import_froms = [i["from"] for i in artifact["imports"]]
        assert "skeleton.wbe_interfaces" in import_froms

    def test_generate_tmd_structure(self, tmp_path: Path) -> None:
        skel_dir = tmp_path / "src/billing-engine/skeleton"
        skel_dir.mkdir(parents=True)
        skel_path = skel_dir / "wbe_interfaces.py"
        skel_path.write_text(
            "class IMarkupEngine:\n"
            "    def derive_price(self): ...\n"
            "    def validate_price(self): ...\n"
        )
        scope = (
            "`src/billing-engine/markup/bundle_engine.py` — "
            "`BundleEngine` implementing `IMarkupEngine`"
        )
        groom = UDCPGroomingEngine(skeleton_path=skel_path, repo_root=tmp_path)
        tmd = groom.generate_tmd("WC027-01a", scope, "WC-027")
        assert tmd["pipeline_track"] == "DIFFERENTIAL"
        assert len(tmd["impacted_artifacts"]) == 1
        artifact = tmd["impacted_artifacts"][0]
        assert artifact["file_path"] == "src/billing-engine/markup/bundle_engine.py"
        assert "derive_price" in artifact["target_methods"]

    def test_generate_tmd_no_skeleton(self, tmp_path: Path) -> None:
        scope = "`src/billing-engine/markup/bundle_engine.py` — fix bug"
        groom = UDCPGroomingEngine(skeleton_path=None, repo_root=tmp_path)
        tmd = groom.generate_tmd("WC027-01a", scope, "WC-027")
        assert tmd["pipeline_track"] == "DIFFERENTIAL"
        assert tmd["impacted_artifacts"][0]["target_methods"] == []

    def test_detect_track_mixed(self, tmp_path: Path) -> None:
        (tmp_path / "src/billing-engine/markup").mkdir(parents=True)
        (tmp_path / "src/billing-engine/markup/router.py").write_text("# existing")
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        assert groom.detect_track(["src/billing-engine/markup/router.py",
                                    "src/billing-engine/markup/models.py"]) == "MIXED"

    def test_detect_track_no_files_in_scope(self, tmp_path: Path) -> None:
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        assert groom.detect_track([]) == "GREENFIELD"

    def test_resolve_skeleton_types_no_match(self, tmp_path: Path) -> None:
        skel_dir = tmp_path / "src/billing-engine/skeleton"
        skel_dir.mkdir(parents=True)
        skel_path = skel_dir / "wbe_interfaces.py"
        skel_path.write_text("class IMarkupEngine:\n    pass\n")
        scope = "`src/billing-engine/markup/models.py` — create Pydantic models"
        groom = UDCPGroomingEngine(skeleton_path=skel_path, repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01a", scope, "WC-027")
        # No skeleton classes mentioned in scope — no skeleton import
        import_froms = [
            i["from"] for a in tis["target_artifacts"] for i in a["imports"]
        ]
        assert "skeleton.wbe_interfaces" not in import_froms

    def test_resolve_skeleton_path_outside_billing_engine(self, tmp_path: Path) -> None:
        # Skeleton in a non-standard location → ValueError caught → returns []
        skel_path = tmp_path / "other/wbe_interfaces.py"
        skel_path.parent.mkdir(parents=True)
        skel_path.write_text("class IFoo:\n    pass\n")
        scope = "`src/billing-engine/markup/models.py` — `IFoo`"
        groom = UDCPGroomingEngine(skeleton_path=skel_path, repo_root=tmp_path)
        tis = groom.generate_tis("T01", scope, "WC-027")
        # Should not raise; skeleton cross-reference skipped gracefully
        assert isinstance(tis, dict)

    # ── Test-file-aware skeleton (Level 1 fix for WC027-02 failure) ───────────

    _WC027_02_SCOPE = (
        "`tests/billing-engine/test_markup.py` — test: cost_floor reads, "
        "derive_price formula uses margin-on-revenue `floor / (1 - margin/100)`, "
        "`POST /pricing/validate` 200 path (APPROVED), "
        "`POST /pricing/validate` 422 path (REJECTED), "
        "`GET /pricing/thread-catalog` response shape; "
        "property-based tests using hypothesis: @given strategy on derive_price"
    )

    def test_test_file_gets_pytest_imports_not_fastapi(self, tmp_path: Path) -> None:
        """Test files must not receive FastAPI imports — they should get pytest imports."""
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis(
            "WC027-02", self._WC027_02_SCOPE, "WC-027",
            required_output_files=["tests/billing-engine/test_markup.py"],
        )
        artifact = tis["target_artifacts"][0]
        import_keys = [list(i.keys()) for i in artifact["imports"]]
        import_froms = [i.get("from", "") for i in artifact["imports"]]
        import_names = [n for i in artifact["imports"] for n in i.get("import", [])]
        # Must NOT have FastAPI
        assert "fastapi" not in import_froms
        # Must have pytest (bare import — no 'from' key)
        assert "pytest" in import_names
        # Must have httpx for async client
        assert "httpx" in import_froms
        # Must have hypothesis (because @given mentioned in scope)
        assert "hypothesis" in import_froms

    def test_test_file_gets_async_test_stubs_not_router_stubs(self, tmp_path: Path) -> None:
        """Test files must receive async test function stubs, not FastAPI router handlers."""
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis(
            "WC027-02", self._WC027_02_SCOPE, "WC-027",
            required_output_files=["tests/billing-engine/test_markup.py"],
        )
        artifact = tis["target_artifacts"][0]
        interfaces = artifact["interfaces"]
        func_names = [i["name"] for i in interfaces]
        # Must have test_* function names (not route handler names)
        assert all(n.startswith("test_") for n in func_names)
        # Must NOT have router decorators
        decorator_strings = [d for i in interfaces for d in i.get("decorators", [])]
        assert not any("router." in d for d in decorator_strings)
        # Must be async
        assert all(i.get("async") is True for i in interfaces if not i["name"].startswith("test_property"))
        # Must have pytest.mark.asyncio decorator for HTTP test stubs
        assert any("pytest.mark.asyncio" in d for d in decorator_strings)
        # Deduplication: POST /pricing/validate appears twice but only one test stub
        post_validate_stubs = [n for n in func_names if "pricing_validate" in n]
        assert len(post_validate_stubs) == 1

    def test_test_file_hypothesis_stub_emitted(self, tmp_path: Path) -> None:
        """Hypothesis scope trigger generates property-based test stub."""
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis(
            "WC027-02", self._WC027_02_SCOPE, "WC-027",
            required_output_files=["tests/billing-engine/test_markup.py"],
        )
        artifact = tis["target_artifacts"][0]
        func_names = [i["name"] for i in artifact["interfaces"]]
        assert "test_property_based" in func_names

    def test_src_file_still_gets_fastapi_imports(self, tmp_path: Path) -> None:
        """Regression: source (router.py) files must still get FastAPI imports."""
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("WC027-01b", self._WC027_01B_SCOPE, "WC-027")
        router_artifact = next(
            a for a in tis["target_artifacts"] if "router.py" in a["file_path"]
        )
        import_froms = [i.get("from", "") for i in router_artifact["imports"]]
        assert "fastapi" in import_froms


# ── Additional PTR coverage ───────────────────────────────────────────────────

class TestWorkspaceSymbolIndexExtra:
    def test_index_skips_syntax_error_files(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "bad.py").write_text("def (:\n    pass\n")  # invalid syntax
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        # bad.py should be silently skipped
        assert "pkg.bad" not in result

    def test_index_handles_annotated_assign(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "consts.py").write_text("MY_CONST: int = 42\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        assert "MY_CONST" in result["pkg.consts"]

    def test_index_handles_plain_assign(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "consts.py").write_text("MY_CONST = 42\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        assert "MY_CONST" in result["pkg.consts"]

    def test_index_handles_async_function(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "service.py").write_text("async def my_service():\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx.index_workspace()
        assert "my_service" in result["pkg.service"]

    def test_validate_tis_auto_indexes_when_empty(self, tmp_path: Path) -> None:
        pkg = tmp_path / "markup"
        pkg.mkdir()
        (pkg / "models.py").write_text("class Foo:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        # Don't call index_workspace() first — validate_tis should auto-build it
        tis = {
            "target_artifacts": [
                {
                    "file_path": "x.py",
                    "imports": [{"from": "markup.models", "import": ["Foo"]}],
                    "interfaces": [],
                }
            ]
        }
        errors = idx.validate_tis(tis)
        assert errors == []

    def test_file_to_module_string_init(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        result = idx._file_to_module_string(pkg / "__init__.py")
        assert result == "mypkg"

    def test_file_to_module_string_not_in_any_root(self, tmp_path: Path) -> None:
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path / "nonexistent")], repo_root=tmp_path)
        result = idx._file_to_module_string(tmp_path / "some.py")
        assert result is None


# ── C-097 Property-Based Tests ────────────────────────────────────────────────

_VALID_MODULE_NAME = st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True)
_VALID_SYMBOL_NAME = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,20}", fullmatch=True)
_VALID_FILE_PATH = st.from_regex(
    r"src/billing-engine/[a-z_]{2,12}/[a-z_]{2,12}\.py", fullmatch=True
)
_VALID_FUNC_NAME = st.from_regex(r"[a-z][a-z0-9_]{2,15}", fullmatch=True)
_VALID_RETURN_TYPE = st.sampled_from(["int", "str", "bool", "None", "dict", "list"])
_VALID_DECORATOR = st.sampled_from([
    "router.get('/x')", "router.post('/y')", "staticmethod", "classmethod",
])


@st.composite
def _tis_artifact(draw, file_path=None):
    fp = file_path or draw(_VALID_FILE_PATH)
    n = draw(st.integers(min_value=0, max_value=3))
    interfaces = []
    for _ in range(n):
        name = draw(_VALID_FUNC_NAME)
        decorators = draw(st.lists(_VALID_DECORATOR, min_size=0, max_size=2))
        ret = draw(_VALID_RETURN_TYPE)
        interfaces.append({
            "type": "function", "name": name, "decorators": decorators,
            "arguments": [], "return_type": ret, "docstring": "",
        })
    return {
        "file_path": fp,
        "imports": [{"from": "fastapi", "import": ["APIRouter"]}],
        "interfaces": interfaces,
    }


@st.composite
def _valid_tis(draw):
    fp = draw(_VALID_FILE_PATH)
    artifact = draw(_tis_artifact(file_path=fp))
    return {
        "sprint_id": "WC-TEST", "task_id": "TEST-01",
        "pipeline_track": "GREENFIELD", "target_artifacts": [artifact],
    }


class TestPropertyBasedPTRGate:
    """C-097: property-based invariants for WorkspaceSymbolIndex."""

    @given(
        mod=_VALID_MODULE_NAME,
        symbols=st.frozensets(_VALID_SYMBOL_NAME, min_size=1, max_size=10),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_validate_tis_deterministic(self, tmp_path, mod, symbols):
        """PTR gate is deterministic: same TIS + same index → same errors list."""
        pkg = tmp_path / mod
        pkg.mkdir(exist_ok=True)
        src = "\n".join(f"class {s}:\n    pass" for s in symbols)
        (pkg / "models.py").write_text(src)
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [{
                "file_path": "x.py",
                "imports": [{"from": f"{mod}.models", "import": list(symbols)[:3]}],
                "interfaces": [],
            }]
        }
        assert idx.validate_tis(tis) == idx.validate_tis(tis)

    @given(invented=st.from_regex(r"Invented[A-Z][a-z]{3,8}", fullmatch=True))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_invented_symbol_always_rejected(self, tmp_path, invented):
        """Any symbol not exported by a module is always rejected."""
        pkg = tmp_path / "mymod"
        pkg.mkdir(exist_ok=True)
        (pkg / "models.py").write_text("class RealSymbol:\n    pass\n")
        idx = WorkspaceSymbolIndex(sys_path_roots=[str(tmp_path)], repo_root=tmp_path)
        tis = {
            "target_artifacts": [{
                "file_path": "x.py",
                "imports": [{"from": "mymod.models", "import": [invented]}],
                "interfaces": [],
            }]
        }
        errors = idx.validate_tis(tis)
        assert any(invented in e for e in errors)


class TestPropertyBasedTrack1Scaffolder:
    """C-097: property-based invariants for Track1Scaffolder."""

    @given(tis=_valid_tis())
    @settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_any_valid_tis_produces_compilable_scaffold(self, tmp_path, tis):
        """Any structurally valid TIS must yield compilable output (no LLM needed)."""
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        for p in paths:
            src = p.read_text()
            try:
                compile(src, str(p), "exec")
            except SyntaxError as exc:
                pytest.fail(f"Scaffold non-compilable for {p.name}: {exc}")

    @given(tis=_valid_tis())
    @settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_router_emitted_iff_route_decorator(self, tmp_path, tis):
        """router = APIRouter() emitted ↔ at least one router. decorator present."""
        scaffolder = Track1Scaffolder(tis, repo_root=tmp_path)
        paths = scaffolder.scaffold_artifacts()
        for artifact, path in zip(tis["target_artifacts"], paths):
            has_dec = any(
                any("router." in d for d in iface.get("decorators", []))
                for iface in artifact.get("interfaces", [])
            )
            has_line = "router = APIRouter()" in path.read_text()
            assert has_dec == has_line


class TestPropertyBasedTrack2Engine:
    """C-097: property-based invariants for Track2PolymorphicEngine."""

    @given(
        func_name=st.from_regex(r"[a-z][a-z0-9_]{2,12}", fullmatch=True),
        return_val=st.integers(min_value=-1000, max_value=1_000_000),
    )
    @settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_extract_then_splice_preserves_parseability(self, tmp_path, func_name, return_val):
        """Round-trip: extract → splice → file is still parseable AST."""
        src = textwrap.dedent(f"""\
            class MyService:
                def {func_name}(self) -> int:
                    return 0
        """)
        path = tmp_path / "service.py"
        path.write_text(src)
        engine = Track2PolymorphicEngine(path)
        new_logic = f"def {func_name}(self) -> int:\n    return {return_val}"
        engine.splice_node_safely(func_name, new_logic, "MyService")
        try:
            ast.parse(path.read_text())
        except SyntaxError as exc:
            pytest.fail(f"File not parseable after splice: {exc}")
        assert str(return_val) in path.read_text()

    @given(func_name=st.from_regex(r"[a-z][a-z0-9_]{2,12}", fullmatch=True))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_extract_never_permanently_mutates_source(self, tmp_path, func_name):
        """try/finally invariant: decorator_list always restored after extract."""
        src = textwrap.dedent(f"""\
            class S:
                @staticmethod
                def {func_name}() -> None:
                    pass
        """)
        path = tmp_path / "s.py"
        path.write_text(src)
        engine = Track2PolymorphicEngine(path)
        for _ in range(3):
            result = engine.extract_node_for_llm(func_name, "S")
            assert "@staticmethod" not in result
        assert "@staticmethod" in path.read_text()


class TestPropertyBasedGroomingEngine:
    """C-097: property-based invariants for UDCPGroomingEngine."""

    @given(
        file_path=st.from_regex(
            r"src/billing-engine/[a-z]{3,10}/[a-z]{3,10}\.py", fullmatch=True
        )
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_tis_always_contains_extracted_file_path(self, tmp_path, file_path):
        """Every file path in scope text appears in TIS target_artifacts."""
        scope = f"`{file_path}` — create new module"
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        tis = groom.generate_tis("T01", scope, "WC-TEST")
        paths = [a["file_path"] for a in tis["target_artifacts"]]
        assert file_path in paths

    @given(
        file_path=st.from_regex(
            r"src/billing-engine/[a-z]{3,10}/[a-z]{3,10}\.py", fullmatch=True
        )
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_greenfield_when_file_absent(self, tmp_path, file_path):
        """File not on disk → always GREENFIELD."""
        groom = UDCPGroomingEngine(repo_root=tmp_path)
        assert groom.detect_track([file_path]) == "GREENFIELD"


# ── Gap-fix regression tests ─────────────────────────────────────────────────

class TestOrchestratorGapFixes:
    """Regression tests for the 3 gaps found in simulation (2026-08-02)."""

    def test_mixed_track_does_not_overwrite_existing_file(self, tmp_path: Path) -> None:
        """Gap 1 fix: MIXED track must not overwrite an existing file with a stub."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        # Create the first file (simulating a prior sprint result)
        existing_dir = tmp_path / "src/billing-engine/markup"
        existing_dir.mkdir(parents=True)
        original_content = "# ORIGINAL CONTENT — must not be overwritten\nclass BundleEngine:\n    pass\n"
        (existing_dir / "bundle_engine.py").write_text(original_content)

        scope = (
            "`src/billing-engine/markup/bundle_engine.py` and "
            "`src/billing-engine/markup/models.py`"
        )
        orch = UDCPOrchestrator(repo_root=tmp_path)
        # detect_track sees one existing file → MIXED
        assert orch.groom.detect_track(["src/billing-engine/markup/bundle_engine.py",
                                         "src/billing-engine/markup/models.py"]) == "MIXED"

        # The TIS would normally scaffold both; the fix skips the existing one
        tis = orch.groom.generate_tis("T01", scope, "WC-TEST")
        # Filter as the orchestrator now does for skip_existing=True
        new_artifacts = [
            a for a in tis["target_artifacts"]
            if not (tmp_path / a["file_path"]).is_file()
        ]
        # Only models.py is new
        assert all("bundle_engine" not in a["file_path"] for a in new_artifacts)
        # Original file is untouched
        assert (existing_dir / "bundle_engine.py").read_text() == original_content

    def test_write_boundary_check_rejects_path_outside_allowed_roots(
        self, tmp_path: Path
    ) -> None:
        """Gap 2 fix: paths returned by LLM outside ALLOWED_WRITE_ROOTS must be rejected."""
        from runner.constants import ALLOWED_WRITE_ROOTS

        bad_paths = [
            "constitution/PROJECT_STATE.md",
            "../secrets/.env",
            "adr/ADR-039.md",
        ]
        for bad in bad_paths:
            allowed = any(bad.startswith(root) for root in ALLOWED_WRITE_ROOTS)
            assert not allowed, (
                f"Path '{bad}' should be outside write boundary but was allowed"
            )

        good_paths = ["src/billing-engine/markup/models.py", "tests/billing-engine/test_markup.py"]
        for good in good_paths:
            allowed = any(good.startswith(root) for root in ALLOWED_WRITE_ROOTS)
            assert allowed, f"Path '{good}' should be inside write boundary"

    def test_track1_skips_all_existing_artifacts(self, tmp_path: Path) -> None:
        """Gap 1 fix: all-existing-files TIS → empty artifact list → success with no writes."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        markup_dir = tmp_path / "src/billing-engine/markup"
        markup_dir.mkdir(parents=True)
        (markup_dir / "router.py").write_text("# existing\n")

        scope = "`src/billing-engine/markup/router.py` — existing file only"
        orch = UDCPOrchestrator(repo_root=tmp_path)

        # Simulate what _run_track1 does with skip_existing=True
        tis = orch.groom.generate_tis("T01", scope, "WC-TEST")
        filtered = [
            a for a in tis["target_artifacts"]
            if not (tmp_path / a["file_path"]).is_file()
        ]
        assert filtered == [], "All files exist → no artifacts to scaffold"


class TestForceGreenfieldAndAppendSkipFixes:
    """Regression tests for D-9 pre-cursor fixes (2026-08-03):
    1. force_greenfield=True bypasses detect_track even when output files exist.
    2. test/* files containing APIRouter mocks do not trigger APPEND SKIP.
    """

    def test_force_greenfield_bypasses_differential(self, tmp_path: Path) -> None:
        """execute_task(force_greenfield=True) must use GREENFIELD even when file exists."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        tests_dir = tmp_path / "tests/billing-engine"
        tests_dir.mkdir(parents=True)
        existing = (
            "# EA mock scaffold — wrong content\n"
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        )
        (tests_dir / "test_markup.py").write_text(existing)

        orch = UDCPOrchestrator(repo_root=tmp_path)

        # Without force_greenfield → file exists → DIFFERENTIAL
        assert orch.groom.detect_track(["tests/billing-engine/test_markup.py"]) == "DIFFERENTIAL"

        # With force_greenfield=True → track is forced to GREENFIELD before any LLM call
        track_seen: list[str] = []

        def capture_llm(**kwargs: object) -> str:  # type: ignore[override]
            track_seen.append("called")
            # Track 1 fill step expects <file path="..."> XML blocks
            return (
                '<file path="tests/billing-engine/test_markup.py">\n'
                "# generated\ndef test_placeholder() -> None:\n    pass\n"
                "</file>\n"
            )

        orch2 = UDCPOrchestrator(repo_root=tmp_path, llm_fn=capture_llm)
        result = orch2.execute_task(
            task_id="T-fg",
            scope_text="`tests/billing-engine/test_markup.py` — full pytest suite",
            required_output_files=["tests/billing-engine/test_markup.py"],
            force_greenfield=True,
        )
        # Track must be GREENFIELD regardless of file existence
        assert result.track == "GREENFIELD"
        assert result.success

    def test_append_skip_not_triggered_for_test_file_with_mock_router(
        self, tmp_path: Path
    ) -> None:
        """A test file that defines router = APIRouter() must NOT hit APPEND SKIP."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        tests_dir = tmp_path / "tests/billing-engine"
        tests_dir.mkdir(parents=True)
        mock_content = (
            "from __future__ import annotations\n"
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n\n"
            "def test_placeholder() -> None:\n"
            "    pass\n"
        )
        (tests_dir / "test_markup.py").write_text(mock_content)

        appended: list[str] = []

        def stub_llm(**kwargs: object) -> str:  # type: ignore[override]
            appended.append("called")
            return "def test_new_case() -> None:\n    assert True\n"

        orch = UDCPOrchestrator(repo_root=tmp_path, llm_fn=stub_llm)
        result = orch._append_module_lines(
            task_id="T-as",
            fp=tests_dir / "test_markup.py",
            rel_path="tests/billing-engine/test_markup.py",
            scope_text="add test cases",
            model_hint="auto",
            max_tokens=1000,
        )
        # APPEND SKIP must NOT fire — LLM must have been called
        assert appended, "LLM was never called — APPEND SKIP incorrectly fired for test file"
        assert result.success

    def test_append_skip_still_fires_for_src_router_file(self, tmp_path: Path) -> None:
        """src/ router files still trigger APPEND SKIP (idempotency guard must stay)."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        router_dir = tmp_path / "src/billing-engine/markup"
        router_dir.mkdir(parents=True)
        router_content = (
            "from fastapi import APIRouter\n"
            "router = APIRouter(prefix='/pricing')\n"
        )
        (router_dir / "router.py").write_text(router_content)

        called: list[str] = []

        def stub_llm(**kwargs: object) -> str:  # type: ignore[override]
            called.append("called")
            return "app.include_router(router)\n"

        orch = UDCPOrchestrator(repo_root=tmp_path, llm_fn=stub_llm)
        result = orch._append_module_lines(
            task_id="T-sr",
            fp=router_dir / "router.py",
            rel_path="src/billing-engine/markup/router.py",
            scope_text="mount router",
            model_hint="auto",
            max_tokens=1000,
        )
        # APPEND SKIP must fire — src/ router files must still be protected
        assert not called, "APPEND SKIP should have fired for src/ router file"
        assert result.success


class TestClosedWorldImportPrevention:
    """CCT: preventive fix for LLM inventing imports during logic-fill (CMMI L5 RCA 2026-08-04)."""

    def test_tis_artifact_contains_allowed_imports_field(self, tmp_path: Path) -> None:
        """TIS artifact must carry allowed_imports as flat import strings (import budget)."""
        from runner.udcp_grooming_engine import UDCPGroomingEngine

        engine = UDCPGroomingEngine(repo_root=tmp_path)
        scope = (
            "Implement `src/billing-engine/markup/router.py` with "
            "`GET /pricing/thread-catalog` and `POST /pricing/validate`. "
            "Pydantic BaseModel for request/response."
        )
        tis = engine.generate_tis("T-cwi", scope, "WC-TEST",
                                   required_output_files=["src/billing-engine/markup/router.py"])

        artifact = tis["target_artifacts"][0]
        assert "allowed_imports" in artifact, "TIS artifact must have allowed_imports field"
        budget = artifact["allowed_imports"]
        assert isinstance(budget, list)
        # Every entry must be a valid import statement string
        for stmt in budget:
            assert stmt.startswith(("import ", "from ")), (
                f"allowed_imports entry is not a valid import statement: {stmt!r}"
            )

    def test_allowed_imports_matches_imports_field(self, tmp_path: Path) -> None:
        """allowed_imports must be the string-rendered form of the imports dicts."""
        from runner.udcp_grooming_engine import UDCPGroomingEngine

        engine = UDCPGroomingEngine(repo_root=tmp_path)
        imports = [
            {"from": "fastapi", "import": ["APIRouter", "Depends"]},
            {"import": ["pytest"]},
        ]
        result = engine._imports_to_strings(imports)
        assert "from fastapi import APIRouter, Depends" in result
        assert "import pytest" in result

    def test_detect_invented_imports_catches_hallucination(self) -> None:
        """_detect_invented_imports must flag import lines absent from the scaffold."""
        from runner.udcp_orchestrator import _detect_invented_imports

        scaffold = (
            "from __future__ import annotations\n"
            "import pytest\n"
            "from httpx import AsyncClient\n"
            "\n"
            "def test_foo() -> None:\n"
            "    pass\n"
        )
        # LLM invents two extra imports
        llm_output = (
            "from __future__ import annotations\n"
            "import pytest\n"
            "from httpx import AsyncClient\n"
            "from database import get_db\n"
            "from config import settings\n"
            "\n"
            "def test_foo() -> None:\n"
            "    assert True\n"
        )
        invented = _detect_invented_imports(scaffold, llm_output)
        assert "from database import get_db" in invented
        assert "from config import settings" in invented

    def test_detect_invented_imports_passes_clean_output(self) -> None:
        """_detect_invented_imports must return empty list when LLM adds no new imports."""
        from runner.udcp_orchestrator import _detect_invented_imports

        scaffold = "import pytest\nfrom httpx import AsyncClient\n\ndef test_x() -> None:\n    pass\n"
        llm_output = "import pytest\nfrom httpx import AsyncClient\n\ndef test_x() -> None:\n    assert True\n"
        assert _detect_invented_imports(scaffold, llm_output) == []

    def test_invented_import_causes_llm_import_violation(self, tmp_path: Path) -> None:
        """execute_task must return LLM_IMPORT_VIOLATION if LLM adds imports beyond scaffold."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        tests_dir = tmp_path / "tests/billing-engine"
        tests_dir.mkdir(parents=True)

        def hallucinating_llm(**kwargs: object) -> str:  # type: ignore[override]
            # LLM invents a non-existent module during logic-fill
            return (
                '<file path="tests/billing-engine/test_router.py">\n'
                "import pytest\n"
                "from httpx import AsyncClient\n"
                "from database import get_db\n"  # ← invented — not in scaffold
                "\n"
                "async def test_get_catalog(client: AsyncClient) -> None:\n"
                "    response = await client.get('/pricing/thread-catalog')\n"
                "    assert response.status_code == 200\n"
                "</file>\n"
            )

        orch = UDCPOrchestrator(repo_root=tmp_path, llm_fn=hallucinating_llm)
        result = orch.execute_task(
            task_id="T-hal",
            scope_text=(
                "Implement `tests/billing-engine/test_router.py` with "
                "`GET /pricing/thread-catalog` endpoint tests."
            ),
            required_output_files=["tests/billing-engine/test_router.py"],
            force_greenfield=True,
        )
        assert not result.success
        assert result.error_type == "LLM_IMPORT_VIOLATION"
        assert "database" in (result.error_snippet or "")
        # Scaffold exists but must NOT contain the LLM's invented import
        written = (tmp_path / "tests/billing-engine/test_router.py").read_text()
        assert "from database import get_db" not in written

    def test_closed_world_rule_appears_in_prompt(self, tmp_path: Path) -> None:
        """Logic-fill prompt must include the closed-world import constraint text."""
        from runner.udcp_orchestrator import UDCPOrchestrator

        tests_dir = tmp_path / "tests/billing-engine"
        tests_dir.mkdir(parents=True)

        captured_prompt: list[str] = []

        def capture_llm(**kwargs: object) -> str:  # type: ignore[override]
            captured_prompt.append(str(kwargs.get("prompt", "")))
            return (
                '<file path="tests/billing-engine/test_x.py">\n'
                "import pytest\n\n"
                "def test_placeholder() -> None:\n"
                "    pass\n"
                "</file>\n"
            )

        orch = UDCPOrchestrator(repo_root=tmp_path, llm_fn=capture_llm)
        orch.execute_task(
            task_id="T-cp",
            scope_text="Implement `tests/billing-engine/test_x.py` with `GET /health` tests.",
            required_output_files=["tests/billing-engine/test_x.py"],
            force_greenfield=True,
        )
        assert captured_prompt, "LLM was never called"
        prompt_text = captured_prompt[0]
        assert "CLOSED-WORLD IMPORT CONSTRAINT" in prompt_text, (
            "Prompt must contain the closed-world import constraint header"
        )
        assert "Permitted imports" in prompt_text, (
            "Prompt must list the permitted imports from the scaffold"
        )
