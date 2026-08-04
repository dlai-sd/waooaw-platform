# Implements: WC-036 — WC036-01
# constitutional_basis: C-082 (Build Validation), ADR-039 §5.2
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from runner.constants import REPO_ROOT

_DEFAULT_SYS_PATH_ROOTS: list[str] = [
    "src/billing-engine",
    "src/professional-runtime",
    "src/ai-runtime",
    "scripts",
]

# Third-party and stdlib module roots that are never in the workspace index
_EXTERNAL_ROOTS: frozenset[str] = frozenset({
    "fastapi", "pydantic", "sqlalchemy", "redis", "httpx", "uvicorn",
    "starlette", "jose", "passlib", "celery", "anthropic", "openai",
    "google", "requests", "pytest", "pytest_asyncio", "hypothesis",
    "unittest", "typing", "typing_extensions",
    "abc", "ast", "os", "sys", "re", "json", "pathlib", "datetime",
    "dataclasses", "enum", "uuid", "logging", "time", "io", "collections",
    "itertools", "functools", "contextlib", "asyncio", "inspect",
    "importlib", "textwrap", "copy", "hashlib", "hmac", "base64",
    "urllib", "http", "email", "struct", "socket", "threading", "warnings",
    "operator", "math", "decimal", "string", "random", "statistics",
    "subprocess", "tempfile", "shutil", "glob", "fnmatch", "zipfile",
    "csv", "configparser", "argparse", "traceback", "weakref",
})


class PTRValidationError(ValueError):
    pass


class WorkspaceSymbolIndex:
    """
    AST-based workspace symbol index.
    Rebuilt per task call so symbols created by earlier tasks in the same sprint
    are visible to subsequent tasks (ADR-039 §5.2).
    """

    def __init__(
        self,
        sys_path_roots: list[str] | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.repo_root = repo_root or REPO_ROOT
        self.sys_path_roots: list[Path] = [
            self.repo_root / r for r in (sys_path_roots or _DEFAULT_SYS_PATH_ROOTS)
        ]
        self._index: dict[str, set[str]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def index_workspace(self) -> dict[str, set[str]]:
        """Walk all .py files reachable from sys_path_roots and build symbol map."""
        self._index = {}
        visited: set[Path] = set()
        for root in self.sys_path_roots:
            if not root.is_dir():
                continue
            for py_file in root.rglob("*.py"):
                if py_file in visited:
                    continue
                visited.add(py_file)
                module_str = self._file_to_module_string(py_file)
                if module_str is None:
                    continue
                try:
                    self._index[module_str] = self._extract_exports(py_file)
                except SyntaxError:
                    pass
        return self._index

    def validate_tis(self, tis: dict[str, Any]) -> list[str]:
        """
        Returns list of error strings (empty = valid).
        Checks every import in every target_artifact against the workspace index.
        Rebuilds index on first call so freshly generated files are included.
        """
        if not self._index:
            self.index_workspace()

        errors: list[str] = []
        for artifact in tis.get("target_artifacts", []):
            for imp in artifact.get("imports", []):
                module = imp.get("from", "")
                names: list[str] = imp.get("import", [])
                if not module:
                    # Bare 'import X' statement — no module path to validate
                    continue
                if _is_external(module):
                    continue
                if module not in self._index:
                    errors.append(
                        f"PTR_GATE: module '{module}' not found in workspace index"
                    )
                    continue
                available = self._index[module]
                if "*" in available:
                    # Wildcard re-export — individual names unverifiable (ADR-039 §7.2)
                    continue
                for name in names:
                    if name not in available:
                        errors.append(
                            f"PTR_GATE: symbol '{name}' not exported by '{module}' "
                            f"(available: {sorted(available)[:10]})"
                        )
        return errors

    # ── Private helpers ───────────────────────────────────────────────────────

    def _file_to_module_string(self, py_file: Path) -> str | None:
        for root in self.sys_path_roots:
            try:
                rel = py_file.relative_to(root)
            except ValueError:
                continue
            parts = list(rel.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                return None
            return ".".join(parts)
        return None

    @staticmethod
    def _extract_exports(py_file: Path) -> set[str]:
        source = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(py_file))  # may raise SyntaxError

        exports: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                exports.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        exports.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                exports.add(node.target.id)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    exports.add(name)  # "*" is preserved per ADR-039 §7.2
        return exports


def _is_external(module: str) -> bool:
    return module.split(".")[0] in _EXTERNAL_ROOTS
