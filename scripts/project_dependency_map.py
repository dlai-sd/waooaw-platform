"""
project_dependency_map.py — Project Dependency Map (PDM)

# Implements: architecture/reference/pipeline/project-dependency-map.md (pending EA spec)
# Constitutional basis: C-082 (build validation), C-059 (traceability)
# Office: Platform IT Expert (INST-010)
# IB: IB-009

Generic solution to LLM-generated cross-project reference violations.

The Problem
-----------
The LLM sees a USING_MAP entry such as "EvaluationContext → Waooaw.ConstitutionalEngine.Evaluators"
and adds `using Waooaw.ConstitutionalEngine.Evaluators;` to a business-platform file.
That namespace exists in the codebase but is NOT reachable from business-platform because
business-platform.csproj has no <ProjectReference> to constitutional-engine.csproj.
This causes CS0234, CS0246, CS0103, CS1061, etc. — different error codes, same root cause.

The Solution
------------
Derive the set of reachable namespace prefixes from a project's .csproj ONCE, then:
  1. Filter USING_MAP at prompt-time → LLM only sees types it can actually use
  2. Inject PROJECT_BOUNDARY block → explicit constraint in every prompt
  3. Single generic recovery handler → fires for any CS namespace error regardless of code

This is O(1) handlers for O(n) future project boundary violations, not O(n) handlers.

Reachable namespace prefixes come from:
  - Self:               RootNamespace from .csproj <PropertyGroup>
  - PackageReferences:  NuGet package ID → namespace prefix (known map + heuristic fallback)
  - ProjectReferences:  Read referenced .csproj → get its RootNamespace
  - Protobuf includes:  Read .proto file for `option csharp_namespace`
  - SDK implicit:       System.*, Microsoft.Extensions.*, Microsoft.AspNetCore.* (net9.0 web SDK)
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent

# ── Known NuGet package ID → reachable namespace prefix(es) ──────────────────
# Only the first two dot-segments of the package ID are used as key for matching.
# Value: one or more namespace prefixes that this package exposes.
_NUGET_NS_MAP: dict[str, list[str]] = {
    # Microsoft
    "Microsoft.AspNetCore":                        ["Microsoft.AspNetCore", "Microsoft.Extensions"],
    "Microsoft.EntityFrameworkCore":               ["Microsoft.EntityFrameworkCore"],
    "Microsoft.Extensions":                        ["Microsoft.Extensions"],
    "Npgsql.EntityFrameworkCore":                  ["Npgsql", "Microsoft.EntityFrameworkCore"],
    "Npgsql":                                      ["Npgsql"],
    # gRPC + Protobuf
    "Grpc.Net":                                    ["Grpc.Net.Client", "Grpc.Core"],
    "Grpc.AspNetCore":                             ["Grpc.AspNetCore", "Grpc.Core"],
    "Grpc.Tools":                                  [],   # codegen only — no runtime import
    "Google.Protobuf":                             ["Google.Protobuf"],
    # OpenTelemetry
    "OpenTelemetry":                               ["OpenTelemetry"],
    # Temporal
    "Temporalio":                                  ["Temporalio"],
    # Test
    "xunit":                                       ["Xunit"],
    "Moq":                                         ["Moq"],
    "FluentAssertions":                            ["FluentAssertions"],
    "Microsoft.NET.Test":                          [],   # no runtime namespace
    "coverlet.collector":                          [],   # no runtime namespace
}

# Namespace prefixes always reachable in any net9.0 project (SDK implicit usings)
_IMPLICIT_PREFIXES: list[str] = [
    "System",
    "Microsoft.Extensions.Logging",
    "Microsoft.Extensions.Configuration",
    "Microsoft.Extensions.DependencyInjection",
]

# ── Public API ────────────────────────────────────────────────────────────────

def find_csproj_for_file(file_path: str | Path, repo_root: Path = REPO_ROOT) -> Optional[Path]:
    """
    Walk up the directory tree from file_path to find the nearest .csproj.
    Returns absolute path or None if not found within repo_root.
    """
    target = (repo_root / file_path).resolve()
    # Start from directory of the file (or the path itself if directory)
    current = target if target.is_dir() else target.parent

    while True:
        candidates = list(current.glob("*.csproj"))
        if candidates:
            return candidates[0]
        # Stop if we've reached or passed the repo root
        if current == repo_root.resolve() or current.parent == current:
            return None
        current = current.parent


@lru_cache(maxsize=32)
def get_reachable_prefixes(csproj_path: Path) -> frozenset[str]:
    """
    Return the set of namespace prefixes reachable from this project.
    Result is cached (csproj rarely changes within a sprint run).
    """
    prefixes: set[str] = set(_IMPLICIT_PREFIXES)

    try:
        tree = ET.parse(csproj_path)
        root = tree.getroot()
    except Exception:
        return frozenset(prefixes)

    csproj_dir = csproj_path.parent

    # ── Self namespace ──────────────────────────────────────────────────────
    for prop in root.iter("RootNamespace"):
        if prop.text:
            prefixes.add(prop.text.strip())

    # ── PackageReferences ──────────────────────────────────────────────────
    for ref in root.iter("PackageReference"):
        pkg_id = ref.get("Include", "")
        prefixes.update(_namespaces_for_package(pkg_id))

    # ── ProjectReferences ──────────────────────────────────────────────────
    for ref in root.iter("ProjectReference"):
        rel_path = ref.get("Include", "").replace("\\", "/")
        ref_csproj = (csproj_dir / rel_path).resolve()
        if ref_csproj.exists():
            try:
                ref_tree = ET.parse(ref_csproj)
                ref_root = ref_tree.getroot()
                for prop in ref_root.iter("RootNamespace"):
                    if prop.text:
                        prefixes.add(prop.text.strip())
                # Also read proto-generated namespaces from referenced project
                for proto in ref_root.iter("Protobuf"):
                    proto_include = proto.get("Include", "")
                    if proto_include:
                        proto_path = (ref_csproj.parent / proto_include).resolve()
                        ns = _read_proto_namespace(proto_path)
                        if ns:
                            prefixes.add(ns)
            except Exception:
                pass

    # ── Protobuf includes in this project ─────────────────────────────────
    for proto in root.iter("Protobuf"):
        proto_include = proto.get("Include", "").replace("\\", "/")
        if proto_include:
            proto_path = (csproj_dir / proto_include).resolve()
            ns = _read_proto_namespace(proto_path)
            if ns:
                prefixes.add(ns)

    return frozenset(prefixes)


def is_namespace_reachable(namespace: str, csproj_path: Path) -> bool:
    """
    True if namespace is reachable from the given project.
    Uses prefix matching: reachable if any allowed prefix is a prefix of namespace.
    """
    prefixes = get_reachable_prefixes(csproj_path)
    return _matches_any_prefix(namespace, prefixes)


def filter_using_map(using_map: dict[str, str], csproj_path: Path) -> dict[str, str]:
    """
    Return only the subset of using_map whose namespaces are reachable from csproj_path.
    Used by context_builder to prevent injecting unreachable types into prompts.
    """
    prefixes = get_reachable_prefixes(csproj_path)
    return {
        cls: ns for cls, ns in using_map.items()
        if _matches_any_prefix(ns, prefixes)
    }


def get_boundary_injection_text(csproj_path: Path) -> str:
    """
    Return PROJECT_BOUNDARY text for injection into the SYSTEM prompt slot.
    Replaces the hard-coded FORBIDDEN_PATTERNS namespace entries.
    """
    prefixes = sorted(get_reachable_prefixes(csproj_path))
    project_name = csproj_path.stem
    lines = [
        f"PROJECT BOUNDARY ({project_name} — derived from {csproj_path.name}):",
        "Only generate `using` directives for namespace prefixes listed below.",
        "Any namespace NOT starting with a listed prefix is UNREACHABLE and will cause a build error.",
        "Reachable prefixes:",
    ]
    for p in prefixes:
        lines.append(f"  ✓ {p}.*")
    lines.append(
        "⛔ Do NOT import namespaces from projects not listed in this project's "
        "<ProjectReference> or <PackageReference> entries."
    )
    return "\n".join(lines)


def get_forbidden_namespaces_in_context(
    csproj_path: Path,
    candidate_namespaces: set[str],
) -> list[str]:
    """
    Given a set of namespaces present in the codebase, return those that are NOT
    reachable from csproj_path. Used to build explicit ⛔ lists for the prompt.
    """
    prefixes = get_reachable_prefixes(csproj_path)
    return sorted(
        ns for ns in candidate_namespaces
        if not _matches_any_prefix(ns, prefixes)
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _namespaces_for_package(package_id: str) -> list[str]:
    """
    Map a NuGet package ID to namespace prefixes.
    Tries the known map first; falls back to a two-segment heuristic.
    """
    if not package_id:
        return []

    # Try progressively shorter prefixes in the known map
    parts = package_id.split(".")
    for length in range(len(parts), 0, -1):
        key = ".".join(parts[:length])
        if key in _NUGET_NS_MAP:
            return _NUGET_NS_MAP[key]

    # Heuristic: use the package name itself as a namespace prefix
    # e.g. "Serilog.Sinks.Console" → "Serilog"
    # Strip version suffixes and known suffix-only packages
    if parts[0].lower() in ("microsoft", "system"):
        # Microsoft/System packages: use first 2 segments
        return [".".join(parts[:2])]
    # Third-party: use first segment
    return [parts[0]]


def _read_proto_namespace(proto_path: Path) -> Optional[str]:
    """Extract `option csharp_namespace = "..."` from a .proto file."""
    if not proto_path.exists():
        return None
    try:
        content = proto_path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'option\s+csharp_namespace\s*=\s*"([^"]+)"', content)
        return m.group(1) if m else None
    except Exception:
        return None


def _matches_any_prefix(namespace: str, prefixes: frozenset[str]) -> bool:
    """True if namespace starts with any of the given prefixes."""
    for prefix in prefixes:
        if namespace == prefix or namespace.startswith(prefix + "."):
            return True
    return False
