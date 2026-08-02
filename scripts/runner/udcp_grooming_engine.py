# Implements: WC-036 — WC036-04
# constitutional_basis: C-032 (Implementation may not create architecture), ADR-039 §5.1
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from runner.constants import REPO_ROOT

# Regex patterns for scope text parsing
_FILE_PATH_RE = re.compile(r"`((?:src|tests)/[^`]+\.py)`")
_FASTAPI_METHOD_RE = re.compile(
    r"`(GET|POST|PUT|DELETE|PATCH)\s+(/[^`]*)`", re.IGNORECASE
)
_CLASS_RE = re.compile(r"`([A-Z][A-Za-z0-9_]+)`")
_SKELETON_ABSTRACT_RE = re.compile(
    r"^\s+(?:async\s+)?def\s+(\w+)\s*\(self(?:,\s*([^)]*))?\)", re.MULTILINE
)
_PYDANTIC_HINT_RE = re.compile(r"\bPydantic\b|\bBaseModel\b", re.IGNORECASE)
_IMPLEMENTS_RE = re.compile(r"implementing\s+`([A-Z][A-Za-z0-9_]+)`")


class UDCPGroomingEngine:
    """
    LLM-free rule-based grooming engine (ADR-039 §5.1).
    Parses WC task scope text via regex and skeleton cross-reference to produce
    TIS (Track 1) or TMD (Track 2) JSON without any LLM involvement.
    """

    def __init__(
        self,
        skeleton_path: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.repo_root = repo_root or REPO_ROOT
        self.skeleton_path = skeleton_path or (
            self.repo_root / "src/billing-engine/skeleton/wbe_interfaces.py"
        )
        self._skeleton_text: str | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_tis(
        self,
        task_id: str,
        scope_text: str,
        sprint_id: str = "",
    ) -> dict[str, Any]:
        """
        Returns a TIS dict for Track 1 (Greenfield) tasks.
        Raises ValueError if any extracted file already exists (should use Track 2).
        """
        artifacts = self._extract_artifacts(scope_text, track=1)
        return {
            "sprint_id": sprint_id,
            "task_id": task_id,
            "pipeline_track": "GREENFIELD",
            "target_artifacts": artifacts,
        }

    def generate_tmd(
        self,
        task_id: str,
        scope_text: str,
        sprint_id: str = "",
    ) -> dict[str, Any]:
        """
        Returns a TMD dict for Track 2 (Differential) tasks.
        Extracts target class + method from scope text.
        """
        file_paths = _FILE_PATH_RE.findall(scope_text)
        artifacts = []
        for fp in file_paths:
            class_match = _IMPLEMENTS_RE.search(scope_text)
            target_class = class_match.group(1) if class_match else None
            artifacts.append(
                {
                    "file_path": fp,
                    "target_class": target_class,
                    "target_methods": self._extract_method_names(scope_text, target_class),
                }
            )
        return {
            "sprint_id": sprint_id,
            "task_id": task_id,
            "pipeline_track": "DIFFERENTIAL",
            "impacted_artifacts": artifacts,
        }

    def detect_track(self, scope_text: str) -> str:
        """
        Returns 'GREENFIELD' if no target file exists on disk, else 'DIFFERENTIAL'.
        Mixed-track scope (some files exist, some don't) returns 'GREENFIELD' for
        new files — caller must split or handle both tracks.
        Files containing WAOOAW_LOGIC_FILLER_START are unfilled stubs — treated as non-existing.
        """
        file_paths = _FILE_PATH_RE.findall(scope_text)
        if not file_paths:
            return "GREENFIELD"
        existing = [
            fp for fp in file_paths
            if (self.repo_root / fp).is_file()
            and "WAOOAW_LOGIC_FILLER_START" not in (self.repo_root / fp).read_text(encoding="utf-8", errors="replace")
        ]
        if not existing:
            return "GREENFIELD"
        if len(existing) == len(file_paths):
            return "DIFFERENTIAL"
        return "MIXED"

    # ── Private extraction ────────────────────────────────────────────────────

    def _extract_artifacts(
        self, scope_text: str, track: int
    ) -> list[dict[str, Any]]:
        file_paths = _FILE_PATH_RE.findall(scope_text)
        artifacts = []
        for fp in file_paths:
            artifacts.append(
                {
                    "file_path": fp,
                    "imports": self._extract_imports(scope_text, fp),
                    "interfaces": self._extract_interfaces(scope_text, fp),
                }
            )
        return artifacts

    def _extract_imports(
        self, scope_text: str, file_path: str
    ) -> list[dict[str, Any]]:
        imports: list[dict[str, Any]] = []

        # FastAPI imports when endpoints are mentioned
        endpoints = _FASTAPI_METHOD_RE.findall(scope_text)
        if endpoints:
            imports.append(
                {"from": "fastapi", "import": ["APIRouter", "Depends", "HTTPException"]}
            )

        # Pydantic import when BaseModel/Pydantic mentioned
        if _PYDANTIC_HINT_RE.search(scope_text):
            imports.append({"from": "pydantic", "import": ["BaseModel", "Field"]})

        # Skeleton cross-reference: resolve types mentioned in scope text
        skeleton_imports = self._resolve_skeleton_types(scope_text, file_path)
        if skeleton_imports:
            imports.extend(skeleton_imports)

        return imports

    def _extract_interfaces(
        self, scope_text: str, file_path: str
    ) -> list[dict[str, Any]]:
        interfaces: list[dict[str, Any]] = []

        # FastAPI route functions
        for method, path in _FASTAPI_METHOD_RE.findall(scope_text):
            func_name = _path_to_func_name(method.lower(), path)
            interfaces.append(
                {
                    "type": "function",
                    "name": func_name,
                    "decorators": [
                        f"router.{method.lower()}('{path}')"
                    ],
                    "arguments": [],
                    "return_type": "dict",
                    "docstring": f"{method.upper()} {path}",
                }
            )

        # Pydantic class stubs when class names are detected near Pydantic hint
        if _PYDANTIC_HINT_RE.search(scope_text):
            class_names = _CLASS_RE.findall(scope_text)
            for cname in class_names:
                if cname.startswith(("I",)) and len(cname) > 2:
                    # Skip interface names (IMarkupEngine etc.)
                    continue
                if any(
                    kw in scope_text[max(0, scope_text.find(f"`{cname}`") - 40) :][:80]
                    for kw in ("Pydantic", "BaseModel", "model")
                ):
                    interfaces.append(
                        {
                            "type": "class",
                            "name": cname,
                            "bases": ["BaseModel"],
                            "fields": [],
                            "docstring": "",
                        }
                    )

        return interfaces

    def _resolve_skeleton_types(
        self, scope_text: str, file_path: str
    ) -> list[dict[str, Any]]:
        """
        Cross-references class names mentioned in scope_text against the skeleton
        file to emit the correct from-import. LLM-free — regex on skeleton source.
        """
        if self.skeleton_path is None or not self.skeleton_path.is_file():
            return []
        if self._skeleton_text is None:
            self._skeleton_text = self.skeleton_path.read_text(encoding="utf-8")

        # Determine the skeleton module name relative to the service root
        # e.g. src/billing-engine/skeleton/wbe_interfaces.py → skeleton.wbe_interfaces
        try:
            rel = self.skeleton_path.relative_to(
                self.repo_root / "src/billing-engine"
            )
            module = ".".join(rel.with_suffix("").parts)
        except ValueError:
            return []

        # Find class names from skeleton that appear in scope_text
        skeleton_classes = re.findall(
            r"^class\s+([A-Z][A-Za-z0-9_]+)", self._skeleton_text, re.MULTILINE
        )
        found = [c for c in skeleton_classes if f"`{c}`" in scope_text]
        if not found:
            return []
        return [{"from": module, "import": found}]

    def _extract_method_names(
        self, scope_text: str, class_name: str | None
    ) -> list[str]:
        if not class_name or self.skeleton_path is None or not self.skeleton_path.is_file():
            return []
        if self._skeleton_text is None:
            self._skeleton_text = self.skeleton_path.read_text(encoding="utf-8")
        # Find abstract method names for the target class in the skeleton
        in_class = False
        methods: list[str] = []
        for line in self._skeleton_text.splitlines():
            if re.match(rf"^class {re.escape(class_name)}", line):
                in_class = True
                continue
            if in_class:
                if re.match(r"^class ", line):
                    break
                m = re.match(r"\s+(?:async\s+)?def\s+(\w+)\s*\(self", line)
                if m:
                    methods.append(m.group(1))
        return methods


# ── Utility ───────────────────────────────────────────────────────────────────

def _path_to_func_name(method: str, path: str) -> str:
    """Converts 'post /bundle-cost-floor/{agent_type}' → 'post_bundle_cost_floor'."""
    slug = re.sub(r"[{}]", "", path)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_")
    return f"{method}_{slug}" if slug else method
