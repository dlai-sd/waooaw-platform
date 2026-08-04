# Implements: WC-036 — WC036-02
# constitutional_basis: C-082 (Build Validation), ADR-039 §5.2
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runner.constants import REPO_ROOT


class Track1ScaffoldError(ValueError):
    pass


class Track1Scaffolder:
    """
    Parses a TIS JSON contract and scaffolds compilable stub files before any
    LLM call. Guarantees a 100% syntax baseline via compile() gate before write.

    Conditional APIRouter: emitted only when at least one interface carries a
    'router.' decorator — prevents NameError in non-router modules.
    Supports both 'function' and 'class' interface types (ADR-039 §5.2).
    """

    def __init__(self, tis: dict[str, Any], repo_root: Path | None = None) -> None:
        self.tis = tis
        self.repo_root = repo_root or REPO_ROOT

    @classmethod
    def from_file(cls, tis_path: Path, repo_root: Path | None = None) -> Track1Scaffolder:
        tis = json.loads(tis_path.read_text(encoding="utf-8"))
        return cls(tis, repo_root)

    # ── Public API ────────────────────────────────────────────────────────────

    def scaffold_artifacts(self) -> list[Path]:
        """Scaffold all target_artifacts to disk. Returns list of written paths."""
        written: list[Path] = []
        for artifact in self.tis.get("target_artifacts", []):
            source = self._render_artifact(artifact)
            _compile_gate(source, artifact["file_path"])
            out_path = self.repo_root / artifact["file_path"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(source, encoding="utf-8")
            written.append(out_path)
        return written

    def scaffold_preview(self) -> dict[str, str]:
        """Render all target_artifacts in memory (no write). Returns {rel_path: content}."""
        result: dict[str, str] = {}
        for artifact in self.tis.get("target_artifacts", []):
            source = self._render_artifact(artifact)
            _compile_gate(source, artifact["file_path"])
            result[artifact["file_path"]] = source
        return result

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_artifact(self, artifact: dict[str, Any]) -> str:
        lines: list[str] = []
        sprint_id = self.tis.get("sprint_id", "")
        task_id = self.tis.get("task_id", "")
        lines.append(f"# Implements: {sprint_id} — {task_id}")
        lines.append("# constitutional_basis: C-059, C-082")
        lines.append("from __future__ import annotations")
        lines.append("")

        for imp in artifact.get("imports", []):
            names = ", ".join(imp["import"])
            if imp.get("from"):
                lines.append(f"from {imp['from']} import {names}")
            else:
                lines.append(f"import {names}")

        interfaces: list[dict[str, Any]] = artifact.get("interfaces", [])

        # Conditional APIRouter — only when at least one route decorator is present
        if _needs_router(interfaces):
            lines.append("")
            lines.append("router = APIRouter()")

        lines.append("")

        for iface in interfaces:
            itype = iface.get("type", "function")
            if itype == "function":
                lines.extend(_render_function(iface))
            elif itype == "class":
                lines.extend(_render_class(iface))

        return "\n".join(lines) + "\n"


# ── Module-level helpers ──────────────────────────────────────────────────────

def _needs_router(interfaces: list[dict[str, Any]]) -> bool:
    return any(
        any("router." in d for d in iface.get("decorators", []))
        for iface in interfaces
    )


def _render_function(iface: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for dec in iface.get("decorators", []):
        lines.append(f"@{dec}")
    args_str = _render_args(iface.get("arguments", []))
    ret = iface.get("return_type", "None")
    prefix = "async def" if iface.get("async") else "def"
    lines.append(f"{prefix} {iface['name']}({args_str}) -> {ret}:")
    doc = iface.get("docstring", "")
    if doc:
        lines.append(f'    """{doc}"""')
    lines.append("    # [WAOOAW_LOGIC_FILLER_START]")
    lines.append("    pass")
    lines.append("    # [WAOOAW_LOGIC_FILLER_END]")
    lines.append("")
    return lines


def _render_class(iface: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    bases = iface.get("bases", ["BaseModel"])
    lines.append(f"class {iface['name']}({', '.join(bases)}):")
    doc = iface.get("docstring", "")
    if doc:
        lines.append(f'    """{doc}"""')
    fields: list[dict[str, Any]] = iface.get("fields", [])
    if fields:
        for field in fields:
            fname = field["name"]
            ftype = field.get("type", "Any")
            if "default" in field:
                lines.append(f"    {fname}: {ftype} = {field['default']}")
            else:
                lines.append(f"    {fname}: {ftype}")
    else:
        # Field-less class body — LLM fills in fields
        lines.append("    # [WAOOAW_LOGIC_FILLER_START]")
        lines.append("    pass")
        lines.append("    # [WAOOAW_LOGIC_FILLER_END]")
    lines.append("")
    return lines


def _render_args(arguments: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for arg in arguments:
        s = f"{arg['name']}: {arg['type']}"
        if "default" in arg:
            s += f" = {arg['default']}"
        parts.append(s)
    return ", ".join(parts)


def _compile_gate(source: str, label: str) -> None:
    try:
        compile(source, label, "exec")
    except SyntaxError as exc:
        raise Track1ScaffoldError(
            f"Track1 compile gate failed for '{label}': {exc}"
        ) from exc
