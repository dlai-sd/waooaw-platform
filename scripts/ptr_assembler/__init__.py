# Implements: architecture/reference/ptr/architecture.md §2 Five-Layer PTR Structure
# Constitutional basis: C-059 (Traceability), C-032 (Spec-Code Drift Gate), C-085 (Idempotency)
"""
PTR 2.0 Assembler — Dynamic Constitutional Knowledge Asset.

Assembles the five-layer, stack-namespaced PTR from the repository's current
source files. Extends the existing platform_type_registry.py by adding:
  - .csproj PackageReference scanning (closes the key WC012-02 gap)
  - requirements.txt / pyproject.toml scanning
  - package.json scanning
  - Stack-namespaced output: {dotnet:{types,packages}, python:{types,packages}, ...}

Lifecycle (per PTR 2.0 architecture):
  - Born at Goal start (cold_start_for_goal())
  - Refreshed after each validated phase (refresh_after_phase())
  - Scoped to Impact Graph boundary
  - Discarded when Goal closes (runtime artifact — never committed)

Usage:
  assembler = PTR2Assembler(repo_root=Path('.'))
  ptr = assembler.assemble(scope=["src/constitutional-engine"])
  ptr = assembler.refresh(ptr, new_files=["src/constitutional-engine/*.cs"])
  task_ptr = assembler.extract_task_ptr(ptr, spec_sections=["§ValidateAction"])
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.parent

# Reuse existing extractors from platform_type_registry.py
_ptr_mod = None
def _ptr():
    global _ptr_mod
    if _ptr_mod is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "platform_type_registry",
            str(REPO_ROOT / "scripts" / "platform_type_registry.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ptr_mod = mod
    return _ptr_mod


# ── Layer 1: Current compiled state ──────────────────────────────────────────

def _scan_dotnet_types(scope_dirs: list[Path]) -> dict[str, Any]:
    """Extract types from all .cs files in scope."""
    types: dict[str, Any] = {}
    ptr = _ptr()
    for d in scope_dirs:
        for cs_file in d.rglob("*.cs"):
            try:
                content = cs_file.read_text(encoding="utf-8", errors="ignore")
                extracted = ptr.extract_dotnet_types(content)
                types.update(extracted)
            except Exception:
                pass
    return types


def _scan_dotnet_packages(scope_dirs: list[Path]) -> dict[str, str]:
    """Extract NuGet PackageReferences from all .csproj files in scope.
    Closes the key gap: WC012-02 failed because Npgsql/Moq not in PTR.
    """
    packages: dict[str, str] = {}
    for d in scope_dirs:
        for csproj in d.rglob("*.csproj"):
            try:
                content = csproj.read_text(encoding="utf-8", errors="ignore")
                # Parse <PackageReference Include="X" Version="Y" />
                for m in re.finditer(
                    r'<PackageReference\s+Include="([^"]+)"(?:[^>]*?Version="([^"]*)")?',
                    content,
                    re.IGNORECASE,
                ):
                    name = m.group(1)
                    version = m.group(2) or "latest"
                    packages[name] = version
            except Exception:
                pass
    return packages


def _scan_python_types(scope_dirs: list[Path]) -> dict[str, Any]:
    """Extract classes/TypedDict from all .py files in scope."""
    types: dict[str, Any] = {}
    ptr = _ptr()
    for d in scope_dirs:
        for py_file in d.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                extracted = ptr.extract_python_types(content)
                # Prefix with relative module path
                rel = py_file.relative_to(REPO_ROOT)
                module = str(rel).replace("/", ".").replace(".py", "")
                for k, v in extracted.items():
                    types[f"{module}.{k}"] = v
            except Exception:
                pass
    return types


def _scan_python_packages(repo_root: Path) -> dict[str, str]:
    """Extract packages from requirements.txt, pyproject.toml, Pipfile."""
    packages: dict[str, str] = {}

    # requirements.txt — any depth
    for req_file in repo_root.rglob("requirements*.txt"):
        try:
            for line in req_file.read_text(errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle: pkg==1.0, pkg>=1.0, pkg~=1.0, pkg
                m = re.match(r"^([A-Za-z0-9_\-\.]+)([>=<!~].*)?$", line)
                if m:
                    packages[m.group(1)] = (m.group(2) or "").strip() or "latest"
        except Exception:
            pass

    # pyproject.toml — simple regex (avoids toml dependency)
    for ppt in repo_root.rglob("pyproject.toml"):
        try:
            content = ppt.read_text(errors="ignore")
            # Find [project] dependencies or [tool.poetry.dependencies]
            for m in re.finditer(
                r'"([A-Za-z0-9_\-\.]+)\s*([>=<!~][^"]*)"',
                content,
            ):
                packages[m.group(1)] = m.group(2).strip()
        except Exception:
            pass

    return packages


def _scan_typescript_packages(scope_dirs: list[Path]) -> dict[str, str]:
    """Extract NPM packages from package.json files."""
    packages: dict[str, str] = {}
    for d in scope_dirs:
        for pkg_json in d.rglob("package.json"):
            if "node_modules" in str(pkg_json):
                continue
            try:
                data = json.loads(pkg_json.read_text(errors="ignore"))
                for section in ("dependencies", "devDependencies", "peerDependencies"):
                    for name, version in data.get(section, {}).items():
                        packages[name] = version
            except Exception:
                pass
    return packages


def _scan_typescript_types(scope_dirs: list[Path]) -> dict[str, Any]:
    """Extract interfaces/types from .ts/.tsx files."""
    types: dict[str, Any] = {}
    ptr = _ptr()
    for d in scope_dirs:
        for ts_file in list(d.rglob("*.ts")) + list(d.rglob("*.tsx")):
            if "node_modules" in str(ts_file) or ".d.ts" in ts_file.name:
                continue
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
                extracted = ptr.extract_typescript_types(content)
                types.update(extracted)
            except Exception:
                pass
    return types


def _scan_terraform_resources(scope_dirs: list[Path]) -> dict[str, Any]:
    """Extract Terraform resource types from .tf files."""
    resources: dict[str, Any] = {}
    providers: dict[str, str] = {}
    ptr = _ptr()
    for d in scope_dirs:
        for tf_file in d.rglob("*.tf"):
            try:
                content = tf_file.read_text(encoding="utf-8", errors="ignore")
                resources.update(ptr.extract_terraform_outputs(content))
                # Extract required_providers
                for m in re.finditer(
                    r'(\w+)\s*=\s*\{[^}]*source\s*=\s*"([^"]+)"[^}]*version\s*=\s*"([^"]+)"',
                    content,
                ):
                    providers[m.group(1)] = f"{m.group(2)} {m.group(3)}"
            except Exception:
                pass
    return {"providers": providers, "resources": resources}


# ── PTR 2.0 Assembler class ───────────────────────────────────────────────────

class PTR2Assembler:
    """
    Assembles the PTR 2.0 five-layer, stack-namespaced knowledge asset.
    Used by the Goal Orchestrator and MagicLLM Context Builder.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or REPO_ROOT

    def assemble(
        self,
        scope: list[str] | None = None,
        include_packages: bool = True,
    ) -> dict[str, Any]:
        """
        Assemble a fresh PTR from the repository's current source files.
        scope: list of directory paths relative to repo root. None = all src/
        Returns the stack-namespaced PTR dict.
        """
        if scope:
            scope_dirs = [self._root / p for p in scope if (self._root / p).exists()]
        else:
            # Default: src/ + scripts/ + web/ (exclude tests for brevity)
            scope_dirs = [
                d for d in [
                    self._root / "src",
                    self._root / "scripts",
                    self._root / "web",
                ]
                if d.exists()
            ]

        ptr: dict[str, Any] = {
            "dotnet": {"types": {}, "packages": {}},
            "python": {"types": {}, "packages": {}},
            "terraform": {"providers": {}, "resources": {}},
            "typescript": {"types": {}, "packages": {}},
            "_meta": {
                "assembled_at": __import__("datetime").datetime.utcnow().isoformat(),
                "scope": scope or ["src", "scripts", "web"],
                "version": "2.0",
            },
        }

        # Layer 1: Current compiled state
        ptr["dotnet"]["types"] = _scan_dotnet_types(scope_dirs)
        ptr["python"]["types"] = _scan_python_types(scope_dirs)
        ptr["typescript"]["types"] = _scan_typescript_types(scope_dirs)

        tf_data = _scan_terraform_resources(scope_dirs)
        ptr["terraform"]["providers"] = tf_data["providers"]
        ptr["terraform"]["resources"] = tf_data["resources"]

        if include_packages:
            # Package manifests — the key PTR 2.0 addition vs. PTR 1.0
            ptr["dotnet"]["packages"] = _scan_dotnet_packages(scope_dirs)
            ptr["python"]["packages"] = _scan_python_packages(self._root)
            ptr["typescript"]["packages"] = _scan_typescript_packages(scope_dirs)

        return ptr

    def refresh(self, ptr: dict[str, Any], new_files: list[str]) -> dict[str, Any]:
        """
        Incrementally refresh PTR after a phase compile gate passes.
        new_files: list of file paths relative to repo root.
        """
        for f_str in new_files:
            f = self._root / f_str
            if not f.exists():
                continue
            suffix = f.suffix.lower()
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if suffix == ".cs":
                    ptr["dotnet"]["types"].update(_ptr().extract_dotnet_types(content))
                elif suffix == ".csproj":
                    ptr["dotnet"]["packages"].update(_scan_dotnet_packages([f.parent]))
                elif suffix == ".py":
                    ptr["python"]["types"].update(_ptr().extract_python_types(content))
                elif suffix in (".txt",) and "requirements" in f.name:
                    ptr["python"]["packages"].update(_scan_python_packages(f.parent))
                elif suffix in (".ts", ".tsx"):
                    ptr["typescript"]["types"].update(_ptr().extract_typescript_types(content))
                elif suffix == ".tf":
                    tf_data = _scan_terraform_resources([f.parent])
                    ptr["terraform"]["resources"].update(tf_data["resources"])
            except Exception:
                pass
        ptr["_meta"]["last_refreshed"] = __import__("datetime").datetime.utcnow().isoformat()
        return ptr

    def extract_task_ptr(
        self,
        ptr: dict[str, Any],
        spec_sections: list[str],
        stack: str = "dotnet",
        max_types: int = 30,
    ) -> dict[str, Any]:
        """
        Extract a task-scoped PTR subset for MagicLLM Context Builder injection.
        Returns only types referenced in spec_sections + all packages for the stack.
        """
        # Find type name mentions in spec sections
        combined_spec = " ".join(spec_sections)
        type_names_mentioned = set(re.findall(r"\b([A-Z][a-zA-Z0-9]+)\b", combined_spec))

        stack_data = ptr.get(stack, {})
        all_types = stack_data.get("types", {})

        # Filter to relevant types
        relevant = {
            k: v for k, v in all_types.items()
            if any(t in k for t in type_names_mentioned)
        }

        # If under limit, add most recently added types as context
        if len(relevant) < max_types:
            remaining = max_types - len(relevant)
            for k, v in list(all_types.items())[:remaining]:
                if k not in relevant:
                    relevant[k] = v

        return {
            stack: {
                "types": relevant,
                "packages": stack_data.get("packages", {}),
            }
        }

    def to_prompt_block(self, task_ptr: dict[str, Any], stack: str = "dotnet") -> str:
        """Format task PTR as a prompt injection block (backward compatible with PTR 1.0)."""
        stack_data = task_ptr.get(stack, {})
        types = stack_data.get("types", {})
        packages = stack_data.get("packages", {})

        lines = ["## PLATFORM TYPE REGISTRY (PTR 2.0 — compiled state)"]

        if types:
            lines.append(f"\n### Types ({stack}):")
            for name, info in list(types.items())[:30]:
                props = info.get("properties", {})
                methods = info.get("methods", [])
                note = info.get("note", "")
                summary = ""
                if props:
                    summary = f" props={list(props.keys())[:5]}"
                if methods:
                    summary += f" methods={methods[:3]}"
                if note:
                    summary += f" NOTE: {note}"
                lines.append(f"  {name}:{summary}")

        if packages:
            lines.append(f"\n### Packages ({stack} — available for import):")
            for name, version in list(packages.items())[:20]:
                lines.append(f"  {name} {version}")

        return "\n".join(lines)

    def build_using_map(self, scope_dirs: list[Path] | None = None) -> dict[str, str]:
        """
        Build USING_MAP: class/type name → C# namespace.
        Injected into LLM prompts to prevent CS0246 (missing using) failures.
        Key industry practice: cross-file namespace index.
        """
        using_map: dict[str, str] = {}
        dirs = scope_dirs or [self._root / "src", self._root / "tests"]
        for d in dirs:
            if not d.exists():
                continue
            for cs_file in d.rglob("*.cs"):
                try:
                    content = cs_file.read_text(encoding="utf-8", errors="ignore")
                    ns_m = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
                    if not ns_m:
                        continue
                    namespace = ns_m.group(1)
                    for class_m in re.finditer(
                        r"(?:public|internal)\s+(?:class|interface|record|enum|struct)\s+(\w+)",
                        content,
                    ):
                        using_map[class_m.group(1)] = namespace
                except Exception:
                    pass
        return using_map

    def using_map_to_prompt_block(self, using_map: dict[str, str]) -> str:
        """Format USING_MAP as a prompt injection block."""
        if not using_map:
            return ""
        lines = ["## USING_MAP (namespace index — prevents CS0246 missing-using errors)"]
        lines.append("Add `using <namespace>;` for any type you reference from this map:")
        for type_name, ns in sorted(using_map.items())[:40]:
            lines.append(f"  {type_name} → using {ns};")
        return "\n".join(lines)


# ── Convenience function for sprint runner ────────────────────────────────────

_default_assembler: PTR2Assembler | None = None

def get_assembler() -> PTR2Assembler:
    global _default_assembler
    if _default_assembler is None:
        _default_assembler = PTR2Assembler()
    return _default_assembler
