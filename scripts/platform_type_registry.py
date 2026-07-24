#!/usr/bin/env python3
"""
platform_type_registry.py — Platform Type Registry (PTR)

# Implements: architecture/reference/pipeline/platform-type-registry.md
# constitutional_basis:
#   C-083 (Emit-Transport-Listen — compiled types ARE the signal from prior tasks)
#   C-085 (Idempotency — next task checks prior compiled state before acting)
#   C-032 (Implementation may not create architecture — spec-code drift fails pre-flight)
#   C-059 (Traceability — every implementation traces to a verified spec)
#   DP-009 (API First — proto and compiled types are source of truth, not spec prose)
# office: Platform IT Expert (Architecture Improvement hat)
# ib_item: IB-009 / WC-019

The PTR solves the type-contract propagation problem across multi-sprint code generation:
  - After each task compiles, extract public API surface from generated source files
  - Write to sprint-context/platform-type-registry.json (C-083 structured signal)
  - Inject the PTR excerpt for each task's needed types into the LLM prompt
  - Pre-flight: check spec pseudocode property references against PTR (C-032 gate)

This prevents the class of failures where LLM generates code using properties
that don't exist on the actual compiled type (e.g., string.TryGetValue() in WC012-02b).

Stack support:
  .NET / C#    — parse record/class/enum from .cs files using regex (no Roslyn needed)
  Python       — parse class/TypedDict/BaseModel from .py files using ast stdlib
  TypeScript   — parse interface/type from .ts files using regex
  Terraform    — parse output blocks from .tf files using regex
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
PTR_PATH  = REPO_ROOT / "sprint-context" / "platform-type-registry.json"


# ══════════════════════════════════════════════════════════════════════════════
# .NET / C# extractor
# ══════════════════════════════════════════════════════════════════════════════

def extract_dotnet_types(cs_content: str) -> dict[str, Any]:
    """
    Parse C# source content and extract public record/class/interface/enum types
    with their public properties, methods, and namespace.

    Returns a dict suitable for PTR storage. Zero external dependencies — regex only.
    C-083: this is the "emit" step after a deterministic or LLM task compiles.
    """
    result: dict[str, Any] = {}

    # Extract namespace
    ns_match = re.search(r'^namespace\s+([\w.]+)', cs_content, re.MULTILINE)
    namespace = ns_match.group(1) if ns_match else ""

    # Extract record types: public sealed record Foo(string Bar, int Baz)
    for m in re.finditer(
        r'public\s+(?:sealed\s+)?record\s+(\w+)\s*\(([^)]*)\)',
        cs_content,
    ):
        type_name = m.group(1)
        params_str = m.group(2)
        properties: dict[str, str] = {}
        for param in params_str.split(","):
            param = param.strip()
            # Match: type? name  or  type name  (with possible default)
            pm = re.match(r'([\w.<>?\[\]]+\??)\s+(\w+)', param)
            if pm:
                properties[pm.group(2)] = pm.group(1)
        result[type_name] = {
            "kind": "record",
            "namespace": namespace,
            "properties": properties,
        }
        # Look for methods on this record (in the record body after the params)
        _extract_methods_into(cs_content, type_name, result[type_name])

    # Extract enum types
    for m in re.finditer(
        r'public\s+enum\s+(\w+)\s*\{([^}]+)\}',
        cs_content,
        re.DOTALL,
    ):
        enum_name = m.group(1)
        values = [v.strip().split("//")[0].strip()
                  for v in m.group(2).split(",")
                  if v.strip()]
        result[enum_name] = {
            "kind": "enum",
            "namespace": namespace,
            "values": [v for v in values if v],
        }

    # Extract class types (sealed class, abstract class, regular class)
    for m in re.finditer(
        r'public\s+(?:sealed\s+|abstract\s+|static\s+)?class\s+(\w+)',
        cs_content,
    ):
        class_name = m.group(1)
        if class_name not in result:
            result[class_name] = {
                "kind": "class",
                "namespace": namespace,
                "properties": {},
                "methods": [],
            }
            _extract_public_props_into(cs_content, class_name, result[class_name])
            _extract_methods_into(cs_content, class_name, result[class_name])

    # Extract interface types
    for m in re.finditer(r'public\s+interface\s+(\w+)', cs_content):
        iface_name = m.group(1)
        if iface_name not in result:
            result[iface_name] = {
                "kind": "interface",
                "namespace": namespace,
                "methods": [],
            }
            _extract_methods_into(cs_content, iface_name, result[iface_name])

    return result


def _extract_public_props_into(cs_content: str, type_name: str, entry: dict) -> None:
    """Extract public property declarations from a class body."""
    # Simplified: find public <type> <Name> { get; ... } patterns
    for pm in re.finditer(
        r'public\s+([\w<>?\[\]]+)\s+(\w+)\s*\{[^}]*get[^}]*\}',
        cs_content,
    ):
        prop_type = pm.group(1)
        prop_name = pm.group(2)
        if prop_name not in ("get", "set", "init"):
            entry.setdefault("properties", {})[prop_name] = prop_type


def _extract_methods_into(cs_content: str, type_name: str, entry: dict) -> None:
    """Extract public method signatures (return type + name + params)."""
    for mm in re.finditer(
        r'public\s+(?:static\s+|override\s+|async\s+|virtual\s+)*'
        r'([\w<>?\[\]Task]+)\s+(\w+)\s*\(([^)]*)\)',
        cs_content,
    ):
        method_name = mm.group(2)
        if method_name in (type_name, "get", "set"):  # skip constructors / accessors
            continue
        entry.setdefault("methods", []).append({
            "name": method_name,
            "return_type": mm.group(1),
            "params": mm.group(3).strip(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# Python extractor
# ══════════════════════════════════════════════════════════════════════════════

def extract_python_types(py_content: str) -> dict[str, Any]:
    """
    Parse Python source and extract class definitions with their fields.
    Handles: Pydantic BaseModel, dataclass, TypedDict, plain classes.

    Uses ast stdlib — zero external dependencies. C-083.
    """
    result: dict[str, Any] = {}
    try:
        tree = ast.parse(py_content)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        class_name = node.name
        bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
        kind = "class"
        if any("BaseModel" in b for b in bases):
            kind = "pydantic_model"
        elif any("TypedDict" in b for b in bases):
            kind = "typed_dict"
        elif any("dataclass" in ast.unparse(d) for d in node.decorator_list
                 if hasattr(ast, "unparse")):
            kind = "dataclass"

        fields: dict[str, str] = {}
        methods: list[str] = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                try:
                    field_type = ast.unparse(item.annotation) if hasattr(ast, "unparse") else "Any"
                except Exception:
                    field_type = "Any"
                fields[field_name] = field_type
            elif isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.AsyncFunctionDef):
                methods.append(f"async {item.name}")

        result[class_name] = {
            "kind": kind,
            "bases": bases,
            "fields": fields,
            "methods": methods,
        }

    return result


# ══════════════════════════════════════════════════════════════════════════════
# TypeScript extractor
# ══════════════════════════════════════════════════════════════════════════════

def extract_typescript_types(ts_content: str) -> dict[str, Any]:
    """
    Parse TypeScript source and extract interface/type/class declarations.
    Regex-based — no TS parser dependency. C-083.
    """
    result: dict[str, Any] = {}

    # Interfaces: interface Foo { bar: string; baz?: number }
    for m in re.finditer(r'(?:export\s+)?interface\s+(\w+)\s*\{([^}]*)\}', ts_content, re.DOTALL):
        iface_name = m.group(1)
        props: dict[str, str] = {}
        for pm in re.finditer(r'(\w+)\??\s*:\s*([\w<>|\[\]]+)', m.group(2)):
            props[pm.group(1)] = pm.group(2)
        result[iface_name] = {"kind": "interface", "properties": props}

    # Type aliases: export type Foo = { bar: string }
    for m in re.finditer(r'(?:export\s+)?type\s+(\w+)\s*=\s*\{([^}]*)\}', ts_content, re.DOTALL):
        type_name = m.group(1)
        props: dict[str, str] = {}
        for pm in re.finditer(r'(\w+)\??\s*:\s*([\w<>|\[\]]+)', m.group(2)):
            props[pm.group(1)] = pm.group(2)
        result[type_name] = {"kind": "type_alias", "properties": props}

    # Enums
    for m in re.finditer(r'(?:export\s+)?enum\s+(\w+)\s*\{([^}]+)\}', ts_content, re.DOTALL):
        enum_name = m.group(1)
        values = [v.strip().split("=")[0].strip() for v in m.group(2).split(",") if v.strip()]
        result[enum_name] = {"kind": "enum", "values": [v for v in values if v]}

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Terraform extractor
# ══════════════════════════════════════════════════════════════════════════════

def extract_terraform_outputs(tf_content: str) -> dict[str, Any]:
    """
    Parse Terraform output blocks — these become the "service endpoints" PTR entries
    that downstream sprints reference (e.g., WC016 outputs for WC017/WC018).
    C-083.
    """
    result: dict[str, Any] = {}
    for m in re.finditer(
        r'output\s+"(\w+)"\s*\{([^}]+)\}',
        tf_content,
        re.DOTALL,
    ):
        output_name = m.group(1)
        body = m.group(2)
        desc_m = re.search(r'description\s*=\s*"([^"]+)"', body)
        val_m  = re.search(r'value\s*=\s*(.+)', body)
        result[output_name] = {
            "kind": "terraform_output",
            "description": desc_m.group(1) if desc_m else "",
            "value_expr": val_m.group(1).strip() if val_m else "",
        }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# PTR read / write
# ══════════════════════════════════════════════════════════════════════════════

def load_ptr() -> dict:
    """Load the Platform Type Registry from disk. Returns empty dict if not found."""
    if PTR_PATH.is_file():
        try:
            return json.loads(PTR_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_ptr(ptr: dict) -> None:
    """Persist the Platform Type Registry. C-083: write the signal."""
    PTR_PATH.parent.mkdir(parents=True, exist_ok=True)
    PTR_PATH.write_text(json.dumps(ptr, indent=2, ensure_ascii=False), encoding="utf-8")


def update_ptr_from_task(task_id: str, written_files: list[str]) -> None:
    """
    After a task's compile gate passes: extract types from written files → update PTR.
    This is the C-083 Emit step for the code generation pipeline.

    Called by execute_with_llm() and execute_subtask_chain() on SUCCESS.
    """
    ptr = load_ptr()
    service_types: dict[str, Any] = {}

    for rel_path in written_files:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if rel_path.endswith(".cs"):
            extracted = extract_dotnet_types(content)
            service_types.update(extracted)
        elif rel_path.endswith(".py"):
            extracted = extract_python_types(content)
            service_types.update(extracted)
        elif rel_path.endswith((".ts", ".tsx")):
            extracted = extract_typescript_types(content)
            service_types.update(extracted)
        elif rel_path.endswith(".tf"):
            extracted = extract_terraform_outputs(content)
            service_types.update(extracted)

    if service_types:
        ptr.setdefault("tasks", {})[task_id] = {
            "types": service_types,
            "files": written_files,
        }
        save_ptr(ptr)
        print(f"  PTR: {task_id} emitted {len(service_types)} type(s) → {PTR_PATH.name}")


def build_ptr_prompt_block(type_names: list[str], ptr: dict | None = None) -> str:
    """
    Build a TYPE CONTRACT block for injection into the LLM prompt.

    Replaces hand-crafted constitutional_check type lists with machine-verified
    type information from the PTR. The LLM sees actual property names and types,
    not spec pseudocode that may have drifted.

    C-085: prior compiled state is the authoritative source.
    DP-009: compiled types (not spec prose) are source of truth.
    """
    if ptr is None:
        ptr = load_ptr()

    if not ptr or not type_names:
        return ""

    # Collect all types across all tasks
    all_types: dict[str, Any] = {}
    for task_entry in ptr.get("tasks", {}).values():
        all_types.update(task_entry.get("types", {}))

    if not all_types:
        return ""

    lines = [
        "\n\n# ═══ TYPE CONTRACT (machine-verified from compiled code) ═══",
        "# These types are extracted from compiled source — NOT spec pseudocode.",
        "# Use ONLY the properties listed here. Any other property does NOT exist.",
        "# C-085 (Idempotency): prior compiled state is authoritative.\n",
    ]

    found_any = False
    for type_name in type_names:
        if type_name not in all_types:
            continue
        found_any = True
        entry = all_types[type_name]
        kind  = entry.get("kind", "unknown")
        ns    = entry.get("namespace", "")
        lines.append(f"## {type_name} ({kind}){f' — namespace: {ns}' if ns else ''}")

        if kind in ("record", "class") and "properties" in entry:
            for prop_name, prop_type in entry["properties"].items():
                note = ""
                if "ActionParameters" in prop_name:
                    note = "  # JSON-encoded string — use GetParameter(key) to parse"
                elif "TenantId" in prop_name:
                    note = "  # from gRPC metadata x-tenant-id"
                lines.append(f"  {prop_name}: {prop_type}{note}")

        elif kind == "enum" and "values" in entry:
            lines.append(f"  Values: {', '.join(entry['values'])}")

        elif kind in ("pydantic_model", "typed_dict", "dataclass") and "fields" in entry:
            for field_name, field_type in entry["fields"].items():
                lines.append(f"  {field_name}: {field_type}")

        if "methods" in entry and entry["methods"]:
            for m in entry["methods"][:5]:  # cap at 5 for prompt size
                if isinstance(m, dict):
                    lines.append(f"  Method: {m['return_type']} {m['name']}({m['params']})")
                else:
                    lines.append(f"  Method: {m}")

        lines.append("")

    if not found_any:
        return ""

    lines.append("# ═══ END TYPE CONTRACT ═══\n")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Spec Contract Checker (C-032 gate)
# ══════════════════════════════════════════════════════════════════════════════

def check_spec_against_ptr(
    spec_content: str,
    ptr: dict | None = None,
) -> list[str]:
    """
    Pre-flight gate: extract ctx.X / context.X property references from spec
    pseudocode and verify each exists in the PTR.

    Returns list of gap strings. Empty list = no gaps, LLM call authorized.
    Non-empty = spec-code drift found → raise flag_spec_gap immediately (C-032).

    C-032 (LAW): implementation may not create architecture; spec gaps must be
    escalated, not silently resolved in code.
    DP-009: proto and compiled types are source of truth.
    """
    if ptr is None:
        ptr = load_ptr()

    # Collect all compiled property names across all tasks
    all_property_names: set[str] = set()
    all_types: dict[str, Any] = {}
    for task_entry in ptr.get("tasks", {}).values():
        for type_name, type_entry in task_entry.get("types", {}).items():
            all_types[type_name] = type_entry
            for prop in type_entry.get("properties", {}):
                all_property_names.add(prop)
            for field in type_entry.get("fields", {}):
                all_property_names.add(field)

    if not all_property_names:
        # No PTR data yet — can't validate (first task). Allow through.
        return []

    # Extract ctx.X and context.X references from spec markdown
    ctx_refs = set(re.findall(r'ctx\.(\w+)', spec_content))
    ctx_refs |= set(re.findall(r'context\.(\w+)', spec_content))

    # Well-known non-property references to ignore
    ignore = {
        # Common method calls on EvaluationContext
        "GetParameter", "FromRequest",
        # Standard C# / gRPC things often written as ctx.X in prose
        "CancellationToken", "RequestHeaders", "Peer", "Host", "Method",
        # Terraform / Python context references
        "tenant_id", "request_id", "session_id",
    }

    gaps = []
    for ref in sorted(ctx_refs - ignore):
        if ref not in all_property_names:
            # Find which type would be most relevant
            gaps.append(
                f"ctx.{ref} referenced in spec but NOT found on any compiled type in PTR. "
                f"Available properties: {', '.join(sorted(all_property_names)[:15])}..."
            )

    return gaps


if __name__ == "__main__":  # pragma: no cover
    import sys
    print("Platform Type Registry — current state:")
    ptr = load_ptr()
    if not ptr:
        print("  (empty — no tasks have emitted types yet)")
    else:
        for task_id, entry in ptr.get("tasks", {}).items():
            types = list(entry.get("types", {}).keys())
            print(f"  {task_id}: {len(types)} types — {', '.join(types)}")
