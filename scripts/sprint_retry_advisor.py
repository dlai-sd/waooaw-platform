#!/usr/bin/env python3
"""
sprint_retry_advisor.py — Layer 1 Inline Build Error Classifier

# Implements: architecture/reference/pipeline/sprint-retry-advisor.md
# constitutional_basis: C-077 (FinOps — cheap classification before expensive retry),
#                       C-082 (build validation for all stacks),
#                       C-059 (Traceability — every diagnosis traces to a claim),
#                       ADR-030 (LLM code generation protocol)
# office: Platform IT Expert (Inline Retry Advisor hat)
# IB: IB-009

Layer 1 of the two-layer reasoning architecture:
  Layer 1 (this): runs INSIDE execute_with_llm() between retry attempts
                  fast, cheap, rule-based for known patterns
                  turns dumb retry into intelligent retry
  Layer 2 (RSA):  runs AFTER sprint execution, handles persistent patterns

Classification is rule-based for the 4 known .NET error patterns observed in
WC-012 runs. LLM-assisted only for UNKNOWN patterns (cheap model, ~1k tokens).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from compiler_diagnostic_router import (
    FAMILY_INTERFACE_CONTRACT,
    FAMILY_NULLABILITY,
    FAMILY_REFERENCE_CONFIG,
    FAMILY_SIGNATURE_DRIFT,
    classify_diagnostic_family,
    parse_diagnostic_facts,
    summarize_facts,
)


# ── Error type constants ───────────────────────────────────────────────────────

EXTEND_NOT_REPLACE = "EXTEND_NOT_REPLACE"   # CS0101: duplicate class — Claude replaced existing file
WRONG_NAMESPACE    = "WRONG_NAMESPACE"       # CS0246: type not found — wrong generated namespace
WRONG_FIELD_NAME   = "WRONG_FIELD_NAME"      # CS0117: field not found — Claude invented property name
MISSING_USING      = "MISSING_USING"         # CS0246 (general): missing using directive
UNKNOWN            = "UNKNOWN"               # Cannot classify — skip remaining retries


@dataclass
class RetryDiagnosis:
    """
    Result from Sprint Retry Advisor diagnosis.
    C-059: every diagnosis must include constitutional_trace.
    """
    error_type: str
    fix_instruction: str           # Injected into next attempt's context
    should_retry: bool             # False = skip remaining attempts, flag spec-gap immediately
    confidence: float              # 0.0-1.0; < 0.6 → should_retry=False regardless of type
    duplicate_files: list[str] = field(default_factory=list)   # For EXTEND_NOT_REPLACE
    constitutional_trace: str = ""  # Which claim this error pattern violates


# ── Rule-based classifiers (no LLM cost) ──────────────────────────────────────

def _classify_cs0101(error: str, written_files: list[str]) -> Optional[RetryDiagnosis]:
    """
    CS0101: The namespace '...' already contains a definition for '...'
    Root cause: Claude regenerated a file that already existed on the sprint branch.
    Fix: Explicit "DO NOT regenerate this file" instruction.
    constitutional_trace: C-085 (Idempotency) — completed work must not be re-executed.
    """
    # Extract the duplicate type name
    m = re.search(r"already contains a definition for '([^']+)'", error)
    if not m:
        return None

    duplicate_type = m.group(1)

    # Find which of the written files contains this type
    duplicate_files = [f for f in written_files if duplicate_type.replace("_", "").lower()
                       in Path(f).stem.lower().replace("_", "")]

    fix = (
        f"CRITICAL — DUPLICATE CLASS DETECTED: '{duplicate_type}' already exists on the branch "
        f"from a prior task. You MUST NOT generate any file that defines this class. "
        f"If you need to ADD a method to an existing class, output ONLY the complete updated file "
        f"with the new method added — do not create a new file with the same class definition. "
        f"Files that already exist and must NOT be regenerated (check BRANCH CONTEXT): "
        f"{', '.join(duplicate_files) if duplicate_files else 'see branch context section'}"
    )

    return RetryDiagnosis(
        error_type=EXTEND_NOT_REPLACE,
        fix_instruction=fix,
        should_retry=True,
        confidence=0.95,
        duplicate_files=duplicate_files,
        constitutional_trace="C-085 (Idempotency Obligation — completed steps must not be re-executed)"
    )


def _classify_cs0246_namespace(error: str) -> Optional[RetryDiagnosis]:
    """
    CS0246 with namespace hint: type not found because Claude used wrong namespace.
    Most common: Waooaw.ConstitutionalEngine.Protos instead of Waooaw.ConstitutionalEngine.Grpc
    constitutional_trace: C-082 (build validation) + C-059 (traceability)
    """
    # Known wrong namespace patterns → correct namespace.
    # Also covers proto-generated request/response types (ValidateActionRequest, etc.)
    # which live in Waooaw.ConstitutionalEngine.Grpc and need 'using Grpc;'
    NAMESPACE_MAP = {
        "Protos":                    "Waooaw.ConstitutionalEngine.Grpc",
        "Proto":                     "Waooaw.ConstitutionalEngine.Grpc",
        "ConstitutionalService":     "Waooaw.ConstitutionalEngine.Grpc",
        "Grpc.ConstitutionalService": "Waooaw.ConstitutionalEngine.Grpc",
        # Proto-generated message types — all end in Request/Response/Reply
        "Request":                   "Waooaw.ConstitutionalEngine.Grpc",
        "Response":                  "Waooaw.ConstitutionalEngine.Grpc",
        "Reply":                     "Waooaw.ConstitutionalEngine.Grpc",
    }

    # Extract the missing type
    type_match = re.search(r"type or namespace name '([^']+)' could not be found", error)
    namespace_match = re.search(r"does not exist in the namespace '([^']+)'", error)

    if not (type_match or namespace_match):
        return None

    missing = (type_match.group(1) if type_match else namespace_match.group(1))

    for wrong, correct in NAMESPACE_MAP.items():
        if wrong.lower() in missing.lower() or wrong.lower() in error.lower():
            fix = (
                f"NAMESPACE ERROR: '{missing}' does not exist. "
                f"The proto compiler generates types into namespace '{correct}'. "
                f"Ensure your using directive is: using {correct}; "
                f"Do NOT use Waooaw.ConstitutionalEngine.Protos — that namespace does not exist. "
                f"The service base class is: ConstitutionalService.ConstitutionalServiceBase "
                f"(from namespace {correct})."
            )
            return RetryDiagnosis(
                error_type=WRONG_NAMESPACE,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.90,
                constitutional_trace="C-059 (Traceability — implementation must reference correct spec types)"
            )

    return None


def _lookup_type_in_ptr(type_name: str) -> Optional[dict]:
    """
    Look up a type's members in the Platform Type Registry.
    Returns the PTR entry if found, None otherwise.
    Best-effort — never raises.
    C-085: prior compiled state is authoritative for fix instructions.
    """
    try:
        from platform_type_registry import load_ptr
        ptr = load_ptr()
        for task_entry in ptr.get("tasks", {}).values():
            if type_name in task_entry.get("types", {}):
                return task_entry["types"][type_name]
    except Exception:
        pass
    return None


def _build_ptr_fix_instruction(type_name: str, field_name: str, ptr_entry: dict) -> str:
    """
    Build a precise fix instruction from a PTR entry.
    Lists actual members so LLM can correct invented names immediately.
    Works for any type in any sprint — zero per-type hardcoding.
    """
    kind = ptr_entry.get("kind", "unknown")
    actual: list[str] = []

    if kind in ("record", "class") and "properties" in ptr_entry:
        actual = list(ptr_entry["properties"].keys())
    elif kind == "proto_message" and "fields" in ptr_entry:
        actual = list(ptr_entry["fields"].keys())
    elif kind == "interface" and "methods" in ptr_entry:
        actual = [
            m["name"] if isinstance(m, dict) else str(m)
            for m in ptr_entry.get("methods", [])
        ]
    elif kind in ("enum", "proto_enum") and "values" in ptr_entry:
        actual = ptr_entry["values"]

    if not actual:
        return (
            f"FIELD NOT FOUND: '{type_name}' does not have '{field_name}'. "
            f"Check BRANCH CONTEXT for the actual definition of '{type_name}'."
        )

    display = ", ".join(actual[:20]) + ("..." if len(actual) > 20 else "")
    ns = ptr_entry.get("namespace", "")
    note = ptr_entry.get("note", "")

    fix = (
        f"PTR-VERIFIED: '{type_name}' ({kind}{f', namespace: {ns}' if ns else ''}) "
        f"does NOT have '{field_name}'. "
        f"Actual members: {display}. "
        f"Use ONLY members from this list — do NOT invent names. "
    )
    if note:
        fix += f"{note} "

    # Add well-known behavioral notes for specific patterns
    methods_str = str(ptr_entry.get("methods", []))
    props_str = str(ptr_entry.get("properties", {}).keys())
    if "ActionParameters" in props_str or "GetParameter" in methods_str:
        fix += (
            "For ActionParameters: use ctx.GetParameter(\"key\") — "
            "it is a JSON-encoded string, NOT a Dictionary. "
        )
    if "EvaluateAllAsync" in methods_str:
        fix += (
            "For EvaluatorRegistry: _registry.EvaluateAllAsync(ctx, ct) is the ONLY public method. "
        )

    return fix


def _classify_cs0117(error: str) -> Optional[RetryDiagnosis]:
    """
    CS0117: 'X' does not contain a definition for 'Y'.
    Generalized: looks up X in PTR to generate machine-verified fix instruction.
    Falls back to generic advice if type not in PTR.
    Covers any type in any sprint — no per-type hardcoding.
    constitutional_trace: C-082, C-085
    """
    m = re.search(r"'([^']+)' does not contain a definition for '([^']+)'", error)
    if not m:
        return None

    class_name, field_name = m.group(1), m.group(2)

    # Try PTR first — fully generalized across all sprints
    ptr_entry = _lookup_type_in_ptr(class_name)
    if ptr_entry:
        fix = _build_ptr_fix_instruction(class_name, field_name, ptr_entry)
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.95,
            constitutional_trace="C-082 + C-085 (PTR-verified — prior compiled state is authoritative)"
        )

    # PTR miss — generic fallback
    fix = (
        f"FIELD ERROR: '{class_name}' does not have '{field_name}'. "
        f"Check BRANCH CONTEXT for the exact definition of '{class_name}'. "
        f"Do not invent field/method/property names. "
        f"For proto-generated response types: use empty constructors (new {class_name}()) "
        f"rather than object initializers with invented fields. "
        f"Check the actual field names in Protos/constitutional_service.proto."
    )
    return RetryDiagnosis(
        error_type=WRONG_FIELD_NAME,
        fix_instruction=fix,
        should_retry=True,
        confidence=0.75,
        constitutional_trace="C-082 (Build Validation — generated code must compile)"
    )


def _classify_cs0019_nullable_operator(error: str) -> Optional[RetryDiagnosis]:
    """
    CS0019: Operator '??' (or similar) cannot be applied to non-nullable type.
    Root cause: LLM uses 'field ?? default' on a non-nullable long/int field.
    In EvaluationContext all budget fields are non-nullable long — no ?? needed.
    constitutional_trace: C-082
    """
    if "CS0019" not in error:
        return None
    if "'??'" not in error and "operator" not in error.lower():
        return None

    # Extract the type name if available
    type_match = re.search(r"operands of type '([^']+)'", error)
    offending_type = type_match.group(1) if type_match else "long"

    fix = (
        f"NULL-COALESCING ERROR: '??' cannot be applied to non-nullable '{offending_type}'.\n"
        f"In EvaluationContext all budget fields (ApprovedBudgetInrPaise, CurrentSpendInrPaise, "
        f"ProposedSpendInrPaise) are non-nullable 'long' — they are NEVER null.\n"
        f"REMOVE all '?? 0L' operators on these fields.\n"
        f"For C043 budget ceiling: compute directly:\n"
        f"  bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) "
        f"> ctx.ApprovedBudgetInrPaise;\n"
        f"Do NOT call ctx.BudgetRemainingInrPaise — that field does not exist on EvaluationContext."
    )
    return RetryDiagnosis(
        error_type="NULLABLE_OPERATOR_ON_VALUE_TYPE",
        fix_instruction=fix,
        should_retry=True,
        confidence=0.95,
        constitutional_trace="C-082 (Build Validation)"
    )


def _classify_cs7036_constructor_args(error: str) -> Optional[RetryDiagnosis]:
    """
    CS7036: constructor/method call missing required argument.

    Common WC-012 pattern: service constructor gained a new dependency and older
    test call-sites were not updated.
    """
    if "CS7036" not in error:
        return None

    m = re.search(r"required parameter '([^']+)'", error)
    missing_param = m.group(1) if m else "<unknown>"

    ctor_m = re.search(r"'([^']+)\(([^)]*)\)'", error)
    target_ctor = ctor_m.group(1) if ctor_m else "constructor"

    fix = (
        f"MISSING CONSTRUCTOR ARG (CS7036): call-site does not provide required parameter '{missing_param}' for {target_ctor}. "
        f"Update ALL affected call-sites to pass the new dependency. "
        f"For tests, either inject a mock for the new dependency, or keep backward compatibility by adding "
        f"a constructor overload / optional parameter with a safe default (for ILogger use NullLogger<T>.Instance)."
    )

    return RetryDiagnosis(
        error_type=WRONG_FIELD_NAME,
        fix_instruction=fix,
        should_retry=True,
        confidence=0.92,
        constitutional_trace="C-082 (Build Validation — constructor contract must match all call sites)",
    )


def _classify_cs0246_missing_using(error: str) -> Optional[RetryDiagnosis]:
    """
    CS0246 general: type not found, likely missing using directive.
    constitutional_trace: C-082
    """
    type_match = re.search(r"type or namespace name '([^']+)' could not be found", error)
    if not type_match:
        return None

    missing_type = type_match.group(1)

    # Test-namespace type in a main project file (e.g., FakeServerCallContext, NullLogger<T>.Instance issues)
    # This happens when LLM adds 'using Waooaw.*.Tests.*' to src/ files
    if re.search(r'Tests?\b|Fake[A-Z]|Mock[A-Z]|InMemory', missing_type):
        fix = (
            f"TEST NAMESPACE IN MAIN PROJECT: '{missing_type}' is a test helper and "
            f"MUST NOT be used in src/ files. "
            f"⛔ Remove any 'using Waooaw.*.Tests.*' directives from this file. "
            f"⛔ Do NOT reference FakeServerCallContext, Mock<T>, or InMemory helpers in main project code. "
            f"Use CancellationToken.None for cancellation, not ServerCallContext. "
            f"If this is a service/evaluator file, it must not depend on test assemblies."
        )
        return RetryDiagnosis(
            error_type=WRONG_NAMESPACE,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.95,
            constitutional_trace="C-082 (Build Validation) — test types must not leak into main project"
        )

    # Known type → namespace mappings
    TYPE_NAMESPACES = {
        "ServerCallContext":   "Grpc.Core",
        "ILogger":             "Microsoft.Extensions.Logging",
        "ActivitySource":      "System.Diagnostics",
        "DbContext":           "Microsoft.EntityFrameworkCore",
        "ActivityKind":        "System.Diagnostics",
        "DbSet":               "Microsoft.EntityFrameworkCore",
    }

    for known_type, namespace in TYPE_NAMESPACES.items():
        if known_type.lower() in missing_type.lower():
            fix = (
                f"MISSING USING: '{missing_type}' requires: using {namespace}; "
                f"Add this using directive to the top of the file."
            )
            return RetryDiagnosis(
                error_type=MISSING_USING,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.80,
                constitutional_trace="C-082 (Build Validation)"
            )

    return None


# ── Multi-stack classifiers (WC013-022 coverage) ──────────────────────────────

def _classify_python_import_error(error: str) -> Optional[RetryDiagnosis]:
    """Python ImportError / ModuleNotFoundError — wrong package/module name."""
    if "ImportError" not in error and "ModuleNotFoundError" not in error:
        return None

    # Temporal SDK — most common wrong import patterns
    if "temporalio" in error or "temporal" in error.lower():
        if "No module named" in error:
            return RetryDiagnosis(
                error_type="PYTHON_IMPORT_TEMPORAL",
                fix_instruction=(
                    "TEMPORAL IMPORT FIX: Use ONLY these imports:\n"
                    "  from temporalio import activity, workflow\n"
                    "  from temporalio.client import Client\n"
                    "  from temporalio.worker import Worker\n"
                    "NEVER use: 'temporal-sdk', 'temporal-python', 'temporal.client'. "
                    "The package is 'temporalio' — installed from PyPI as temporalio."
                ),
                should_retry=True, confidence=0.95,
                constitutional_trace="C-082 (Build Validation — Python stack)"
            )

    # Vertex AI SDK
    if "vertexai" in error or "google.cloud.aiplatform" in error:
        return RetryDiagnosis(
            error_type="PYTHON_IMPORT_VERTEX",
            fix_instruction=(
                "VERTEX AI IMPORT FIX: Use 'from google.cloud import aiplatform' "
                "NOT 'import vertexai'. "
                "Gemini model name: 'gemini-2.0-flash' NOT 'gemini-pro' (deprecated). "
                "SA key from env: os.environ.get('GOOGLE_VERTEX_SA_KEY'). "
                "Region: 'asia-south1' for DPDPA compliance."
            ),
            should_retry=True, confidence=0.90,
            constitutional_trace="C-082 + C-063 (DPDPA — data residency)"
        )

    # Sarvam AI
    if "sarvam" in error.lower():
        return RetryDiagnosis(
            error_type="PYTHON_IMPORT_SARVAM",
            fix_instruction=(
                "SARVAM FIX: There is NO Sarvam Python SDK. "
                "Use httpx REST calls ONLY: "
                "async with httpx.AsyncClient() as client: "
                "resp = await client.post('https://api.sarvam.ai/v1/...', json=..., headers=...)"
            ),
            should_retry=True, confidence=0.95,
            constitutional_trace="C-082 (Build Validation)"
        )

    # Generic Python import
    m = re.search(r"No module named '([^']+)'", error)
    if m:
        mod = m.group(1)
        return RetryDiagnosis(
            error_type="PYTHON_IMPORT_MISSING",
            fix_instruction=(
                f"IMPORT FIX: Module '{mod}' not found. "
                f"Check requirements.txt / pyproject.toml for the correct package name. "
                f"Do NOT invent package names. Use packages listed in the PTR. "
                f"httpx replaces requests. asyncpg replaces psycopg2 for async Postgres."
            ),
            should_retry=True, confidence=0.75,
            constitutional_trace="C-082 (Build Validation)"
        )
    return None


def _classify_python_async_error(error: str) -> Optional[RetryDiagnosis]:
    """Python async/await misuse — blocking calls inside async context."""
    if ("RuntimeError" not in error and "coroutine" not in error
            and "await" not in error.lower()):
        return None

    if "coroutine was never awaited" in error or "RuntimeWarning" in error:
        return RetryDiagnosis(
            error_type="PYTHON_ASYNC_NOT_AWAITED",
            fix_instruction=(
                "ASYNC FIX: A coroutine was called without 'await'. "
                "All async functions must be called with 'await'. "
                "Never use asyncio.run() inside a Temporal activity or FastAPI handler — "
                "the event loop is already running. "
                "For Temporal: activities must be 'async def' and 'await'ed. "
                "For FastAPI: route handlers must be 'async def'."
            ),
            should_retry=True, confidence=0.90,
            constitutional_trace="C-082 (Build Validation — Python async)"
        )

    if "asyncio.run() cannot be called" in error:
        return RetryDiagnosis(
            error_type="PYTHON_ASYNCIO_RUN_IN_LOOP",
            fix_instruction=(
                "ASYNC FIX: asyncio.run() cannot be called inside a running event loop. "
                "In Temporal activities and FastAPI handlers, the loop is already running. "
                "Use 'await coro()' directly. "
                "For one-off async calls: use 'await asyncio.ensure_future(coro())'."
            ),
            should_retry=True, confidence=0.95,
            constitutional_trace="C-082 (Build Validation)"
        )
    return None


def _classify_temporal_error(error: str) -> Optional[RetryDiagnosis]:
    """Temporal SDK registration and workflow definition errors."""
    if "temporalio" not in error.lower() and "temporal" not in error.lower():
        return None

    if "@workflow.defn" in error or "not a workflow" in error.lower():
        return RetryDiagnosis(
            error_type="TEMPORAL_WORKFLOW_DEFN_MISSING",
            fix_instruction=(
                "TEMPORAL FIX: Workflow class must have @workflow.defn decorator. "
                "Workflow run method must have @workflow.run decorator. "
                "Pattern:\n"
                "  @workflow.defn\n"
                "  class MyWorkflow:\n"
                "      @workflow.run\n"
                "      async def run(self, input: MyInput) -> MyOutput:\n"
                "          return await workflow.execute_activity(my_activity, ...)\n"
                "NEVER call activities directly — always via workflow.execute_activity()."
            ),
            should_retry=True, confidence=0.90,
            constitutional_trace="C-082 (Build Validation — Temporal SDK)"
        )

    if "not an activity" in error.lower() or "@activity.defn" in error:
        return RetryDiagnosis(
            error_type="TEMPORAL_ACTIVITY_DEFN_MISSING",
            fix_instruction=(
                "TEMPORAL FIX: Activity function must have @activity.defn decorator. "
                "Pattern:\n"
                "  @activity.defn\n"
                "  async def my_activity(input: MyInput) -> MyOutput:\n"
                "      ...\n"
                "Register activities in Worker: worker = Worker(client, ..., "
                "activities=[my_activity]). "
                "Activity input/output must be serializable (Pydantic or dataclass)."
            ),
            should_retry=True, confidence=0.90,
            constitutional_trace="C-082 (Build Validation)"
        )
    return None


def _classify_terraform_error(error: str) -> Optional[RetryDiagnosis]:
    """Terraform plan/apply errors — provider and resource configuration."""
    if "Error:" not in error and "error" not in error.lower():
        return None
    # Only process if looks like a Terraform error
    if not any(kw in error for kw in ["azurerm", "terraform", "Unsupported argument",
                                        "Invalid reference", "provider"]):
        return None

    if "Unsupported argument" in error:
        m = re.search(r'An argument named "([^"]+)" is not expected', error)
        attr = m.group(1) if m else "unknown"
        return RetryDiagnosis(
            error_type="TERRAFORM_UNSUPPORTED_ARGUMENT",
            fix_instruction=(
                f"TERRAFORM FIX: Attribute '{attr}' does not exist on this resource. "
                f"Check the Azure provider docs for the exact attribute name. "
                f"Common mistakes: 'sku' vs 'sku_name', 'resource_group' vs 'resource_group_name', "
                f"'location' is always required. "
                f"Pin provider version: azurerm ~> 4.0 in required_providers."
            ),
            should_retry=True, confidence=0.85,
            constitutional_trace="C-082 (Build Validation — Terraform)"
        )

    if "Invalid reference" in error or "Variables not allowed" in error:
        return RetryDiagnosis(
            error_type="TERRAFORM_INVALID_REFERENCE",
            fix_instruction=(
                "TERRAFORM FIX: Invalid variable or output reference. "
                "Use var.name for input variables, local.name for locals, "
                "module.name.output for module outputs, data.type.name.attr for data sources. "
                "NEVER hardcode subscription IDs, tenant IDs, or resource IDs. "
                "NEVER use string interpolation for resource names — use var.* references."
            ),
            should_retry=True, confidence=0.85,
            constitutional_trace="C-082 + C-059 (Terraform — no hardcoded credentials)"
        )

    if "provider" in error.lower() and "configuration" in error.lower():
        return RetryDiagnosis(
            error_type="TERRAFORM_PROVIDER_CONFIG",
            fix_instruction=(
                "TERRAFORM FIX: Provider configuration missing or incorrect. "
                "Add to provider.tf (root module only — NEVER inside a module):\n"
                "  provider \"azurerm\" {\n"
                "    features {}\n"
                "    subscription_id = var.subscription_id\n"
                "  }\n"
                "required_providers block: azurerm = { source = 'hashicorp/azurerm', version = '~> 4.0' }"
            ),
            should_retry=True, confidence=0.85,
            constitutional_trace="C-082 (Build Validation)"
        )
    return None


def _classify_typescript_error(error: str) -> Optional[RetryDiagnosis]:
    """TypeScript/Next.js compilation and runtime boundary errors."""
    # TypeScript compile errors
    if "TS" in error and re.search(r'TS\d{4}', error):
        ts_code = re.search(r'TS(\d{4})', error)
        code = int(ts_code.group(1)) if ts_code else 0

        if code == 2307:  # Cannot find module
            m = re.search(r"Cannot find module '([^']+)'", error)
            mod = m.group(1) if m else "unknown"
            return RetryDiagnosis(
                error_type="TS_MODULE_NOT_FOUND",
                fix_instruction=(
                    f"TS FIX: Module '{mod}' not found. "
                    f"Use @/ alias for absolute imports (configured in tsconfig.json). "
                    f"Example: import {{ Button }} from '@/components/ui/button' "
                    f"NEVER use relative paths like '../../components' from src root. "
                    f"Check package.json for available packages before importing."
                ),
                should_retry=True, confidence=0.85,
                constitutional_trace="C-082 (Build Validation — TypeScript)"
            )

        if code == 2339:  # Property does not exist
            m = re.search(r"Property '([^']+)' does not exist on type '([^']+)'", error)
            if m:
                prop, typ = m.group(1), m.group(2)
                return RetryDiagnosis(
                    error_type="TS_PROPERTY_NOT_EXIST",
                    fix_instruction=(
                        f"TS FIX: Property '{prop}' does not exist on '{typ}'. "
                        f"Check the type definition in the codebase. "
                        f"For Next.js types: SearchParams are string | string[] | undefined, not string. "
                        f"For React props: ensure the interface/type includes this prop. "
                        f"NEVER use 'any' to bypass this — narrow the type properly."
                    ),
                    should_retry=True, confidence=0.85,
                    constitutional_trace="C-082 (Build Validation)"
                )

    # Next.js runtime boundary errors (not compile errors — need special handling)
    if "Event handlers cannot be passed to Client Component" in error:
        return RetryDiagnosis(
            error_type="NEXTJS_CLIENT_COMPONENT_MISSING",
            fix_instruction=(
                "NEXT.JS FIX: Add 'use client'; as the FIRST line of the component file. "
                "This error means a Server Component is passing event handlers (onClick, etc.) "
                "or using hooks (useState, useEffect). "
                "Rule: if you use onClick, onChange, useState, useEffect, useRef, or browser APIs "
                "→ add 'use client'; to the file. "
                "Default is Server Component. Only add 'use client' when needed."
            ),
            should_retry=True, confidence=0.95,
            constitutional_trace="C-082 (Build Validation — Next.js App Router)"
        )

    if "useRouter" in error and "only works in a Client Component" in error:
        return RetryDiagnosis(
            error_type="NEXTJS_USE_ROUTER_SERVER",
            fix_instruction=(
                "NEXT.JS FIX: useRouter(), usePathname(), useSearchParams() only work in Client Components. "
                "Add 'use client'; as the first line of the file. "
                "Alternative: pass the value as a prop from a Server Component parent."
            ),
            should_retry=True, confidence=0.95,
            constitutional_trace="C-082 (Build Validation)"
        )
    return None


# ── Industry Item 11: Post-run failure learning cache ─────────────────────────
# After a retry succeeds, store error→fix pair to a local JSONL cache.
# Next run loads cache before LLM fallback — eliminates repeat LLM calls for
# the same error pattern.

_LEARNING_CACHE_PATH = Path(__file__).parent.parent / "sprint-context" / "retry-learning-cache.jsonl"


def record_successful_fix(error_snippet: str, fix_instruction: str, error_type: str, task_id: str) -> None:
    """Append a successful error→fix pair to the learning cache (C-069 self-improvement)."""
    import json as _json
    try:
        entry = {
            "error_snippet": error_snippet[:200],
            "error_type": error_type,
            "fix_instruction": fix_instruction[:400],
            "task_id": task_id,
        }
        _LEARNING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LEARNING_CACHE_PATH.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
    except Exception:
        pass  # Learning cache is best-effort — never blocks execution


def lookup_learning_cache(error_snippet: str) -> Optional[RetryDiagnosis]:
    """Check learning cache for a known fix before calling LLM.
    P2 Fix 2: Also checks cross-sprint learning cache archives (Instinct 2 compounds).
    """
    import json as _json

    cache_files = [_LEARNING_CACHE_PATH]

    # Also load cross-sprint archived caches
    cross_dir = _LEARNING_CACHE_PATH.parent / "cross-sprint-context"
    if cross_dir.exists():
        cache_files.extend(sorted(cross_dir.glob("*-retry-learning-cache.jsonl")))

    for cache_path in cache_files:
        if not cache_path.exists():
            continue
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                for line in f:
                    entry = _json.loads(line.strip())
                    if entry.get("error_snippet", "") and entry["error_snippet"][:80] in error_snippet:
                        source = "cross-sprint" if "cross-sprint" in str(cache_path) else "current-sprint"
                        print(f"  Retry Advisor: CACHE HIT ({source}) — using learned fix for {entry['error_type']}")
                        return RetryDiagnosis(
                            error_type=entry["error_type"],
                            fix_instruction=entry["fix_instruction"],
                            should_retry=True,
                            confidence=0.82,
                            constitutional_trace="C-069 (Self-Improvement — learned from prior successful retry)",
                        )
        except Exception:
            pass
    return None


# ── LLM-assisted classifier for UNKNOWN patterns ──────────────────────────────

def _classify_with_llm(task_id: str, error: str) -> RetryDiagnosis:  # pragma: no cover
    """
    Fallback: use cheap LLM call to classify an unknown build error.
    Uses a small model (~1,000 tokens) — not FRONTIER.
    C-077: minimum token spend for classification before committing to full retry.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return RetryDiagnosis(
            error_type=UNKNOWN,
            fix_instruction="Cannot classify — no API key. Manual diagnosis required.",
            should_retry=False,
            confidence=0.0,
            constitutional_trace="C-077 (FinOps — cannot classify without API)"
        )

    try:
        import urllib.request
        import json

        prompt = (
            f"You are diagnosing a .NET 9 build error in a gRPC service.\n\n"
            f"Task: {task_id}\n"
            f"Build error:\n{error[:500]}\n\n"
            f"Respond in JSON only:\n"
            f"{{\"error_type\": \"EXTEND_NOT_REPLACE|WRONG_NAMESPACE|WRONG_FIELD_NAME|MISSING_USING|UNKNOWN\",\n"
            f" \"fix_instruction\": \"one sentence telling the developer exactly what to change\",\n"
            f" \"confidence\": 0.0-1.0,\n"
            f" \"should_retry\": true/false}}"
        )

        payload = {
            "model": "claude-haiku-4-5",   # cheapest model — classification only
            "max_tokens": 200,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            text = result["content"][0]["text"].strip()
            # Parse JSON from response
            parsed = json.loads(text)
            return RetryDiagnosis(
                error_type=parsed.get("error_type", UNKNOWN),
                fix_instruction=parsed.get("fix_instruction", ""),
                should_retry=parsed.get("should_retry", False),
                confidence=float(parsed.get("confidence", 0.5)),
                constitutional_trace="C-077 (LLM-assisted classification — cheap model)"
            )
    except Exception as e:
        return RetryDiagnosis(
            error_type=UNKNOWN,
            fix_instruction=f"LLM classification failed: {str(e)[:100]}",
            should_retry=False,
            confidence=0.0,
            constitutional_trace="C-082 (Build Validation — cannot retry without diagnosis)"
        )


# ── Main entry point ───────────────────────────────────────────────────────────

def diagnose_build_error(
    task_id: str,
    build_error: str,
    written_files: list[str],
    branch_files: Optional[list[str]] = None,
) -> RetryDiagnosis:
    """
    Classify a build error and return a targeted fix instruction.

    Called between retry attempts in execute_with_llm().
    Rule-based for known patterns (zero LLM cost).
    LLM-assisted for unknowns (cheap model, ~1k tokens).

    constitutional_basis: C-077 (FinOps), C-082 (build validation), C-059 (traceability)
    """
    # Collect all CS error codes from the error output
    error_codes = set(re.findall(r'CS\d+', build_error))
    facts = parse_diagnostic_facts(build_error)
    family = classify_diagnostic_family(facts)

    print(f"  Retry Advisor: {task_id} — error codes: {sorted(error_codes)}")
    print(f"  Retry Advisor: diagnostic family={family}")

    # ── Rule 1: CS0101 — duplicate class definition ────────────────────────────
    if "CS0101" in error_codes:
        diagnosis = _classify_cs0101(build_error, written_files)
        if diagnosis:
            print(f"  Retry Advisor: EXTEND_NOT_REPLACE (confidence={diagnosis.confidence:.0%})")
            return diagnosis

    # ── Rule 2: CS0246 — namespace/type not found ──────────────────────────────
    if "CS0246" in error_codes:
        # Try namespace-specific classification first
        diagnosis = _classify_cs0246_namespace(build_error)
        if diagnosis:
            print(f"  Retry Advisor: WRONG_NAMESPACE (confidence={diagnosis.confidence:.0%})")
            return diagnosis

        # Try missing-using classification
        diagnosis = _classify_cs0246_missing_using(build_error)
        if diagnosis:
            print(f"  Retry Advisor: MISSING_USING (confidence={diagnosis.confidence:.0%})")
            return diagnosis

    # ── Rule 3: CS0117 — field/property not found ─────────────────────────────
    if "CS0117" in error_codes:
        diagnosis = _classify_cs0117(build_error)
        if diagnosis:
            print(f"  Retry Advisor: WRONG_FIELD_NAME (confidence={diagnosis.confidence:.0%})")
            return diagnosis

    # ── Rule 4: CS0103 — undefined name (invented type/enum) ──────────────────
    if "CS0103" in error_codes:
        m = re.search(r"The name '([^']+)' does not exist in the current context", build_error)
        if m:
            bad_name = m.group(1)
            fix = (
                f"UNDEFINED NAME: '{bad_name}' does not exist. "
                f"You invented a type or enum name that is not defined anywhere in the project. "
                f"Check the BRANCH CONTEXT for exact class/enum names. "
                f"For EvaluationResult: use EvaluationVerdict (not EvaluationDecision). "
                f"For EvaluationVerdict values: Allow, Deny, Escalate (exact case)."
            )
            print(f"  Retry Advisor: WRONG_FIELD_NAME/undefined name CS0103 (confidence=88%)")
            return RetryDiagnosis(
                error_type=WRONG_FIELD_NAME,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.88,
                constitutional_trace="C-082 (Build Validation — generated code must use defined types)"
            )


    # ── Rule 5: CS1061 — member not found on type ─────────────────────────────
    if "CS1061" in error_codes:
        m = re.search(r"'([^']+)' does not contain a definition for '([^']+)'", build_error)
        if m:
            type_name, field_name = m.group(1), m.group(2)

            # Try PTR first — fully generalized, works for any type in any sprint
            ptr_entry = _lookup_type_in_ptr(type_name)
            if ptr_entry:
                fix = _build_ptr_fix_instruction(type_name, field_name, ptr_entry)
                print(f"  Retry Advisor: CS1061 PTR-verified fix for {type_name}.{field_name} (confidence=95%)")
                return RetryDiagnosis(
                    error_type=WRONG_FIELD_NAME,
                    fix_instruction=fix,
                    should_retry=True,
                    confidence=0.95,
                    constitutional_trace="C-082 + C-085 (PTR-verified — prior compiled state is authoritative)"
                )

            # PTR miss — fall back to known behavioral patterns
            fix = (
                f"FIELD NOT FOUND: '{type_name}.{field_name}' does not exist. "
                f"Check BRANCH CONTEXT for the exact API of '{type_name}'. "
                f"If this is EvaluationContext: use ctx.GetParameter(\"key\") for ActionParameters JSON — "
                f"NEVER call ActionParameters.TryGetValue(). "
                f"If this is EvaluatorRegistry: use _registry.EvaluateAllAsync(ctx, ct) — the only public method."
            )
            print(f"  Retry Advisor: CS1061 generic fallback for {type_name}.{field_name} (confidence=75%)")
            return RetryDiagnosis(
                error_type=WRONG_FIELD_NAME,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.75,
                constitutional_trace="C-082 (Build Validation — use types from BRANCH CONTEXT)"
            )

    # ── Rule 6: CS0266 / CS0037 — null/nullable-to-non-nullable conversion ──────
    if "CS0266" in error_codes or "CS0037" in error_codes:
        m = re.search(r"Cannot implicitly convert type '([^']+)' to '([^']+)'", build_error)
        if m:
            from_type, to_type = m.group(1), m.group(2)
            # PTR-aware: look up the field that is nullable
            field_m = re.search(r"error CS0266:.*\[.*\]\s*$", build_error, re.MULTILINE)
            ptr_entry = None
            # Try to find which field is nullable from PTR
            try:
                from platform_type_registry import load_ptr
                ptr = load_ptr()
                for task_entry in ptr.get("tasks", {}).values():
                    for type_entry in task_entry.get("types", {}).values():
                        for field_name, field_type in type_entry.get("fields", {}).items():
                            if "?" in field_type and field_type.replace("?", "").strip() == to_type:
                                ptr_entry = (field_name, field_type)
                                break
            except Exception:
                pass
            if ptr_entry:
                field_name, field_type = ptr_entry
                fix = (
                    f"NULLABLE CONVERSION (CS0266/CS0037): '{from_type}' cannot be assigned to '{to_type}' directly. "
                    f"The field '{field_name}' is declared as '{field_type}' (nullable). "
                    f"Use '.Value' to assert non-null: {field_name}.Value "
                    f"OR use null-coalescing: {field_name} ?? 0L "
                    f"Example: response.{to_type.capitalize()} = someNullable ?? 0L;"
                )
            else:
                fix = (
                    f"NULLABLE CONVERSION (CS0266/CS0037): '{from_type}' cannot be assigned to '{to_type}' directly. "
                    f"The source value is nullable or null. "
                    f"Use null-coalescing: nullableValue ?? default({to_type}) "
                    f"OR use .Value if you know it is non-null: nullableValue.Value "
                    f"For proto optional long fields: field ?? 0L"
                )
            print(f"  Retry Advisor: CS0266/CS0037 nullable-to-non-nullable (confidence=90%)")
            return RetryDiagnosis(
                error_type=WRONG_FIELD_NAME,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.90,
                constitutional_trace="C-082 (Build Validation — nullable types require explicit conversion)"
            )

    # ── Rule 6b: CS8629 / CS8600 / CS8602 / CS8604 — nullable dereference warnings-as-errors ──
    if error_codes & {"CS8629", "CS8600", "CS8602", "CS8604", "CS8618"}:
        hit = sorted(error_codes & {"CS8629", "CS8600", "CS8602", "CS8604", "CS8618"})[0]
        fix = (
            f"NULLABLE DEREFERENCE ({hit}): "
            "A nullable reference or value type is used without null check. "
            "Pattern: if (x == null) return DENY; var safe = x.Value; "
            "For optional proto fields that map to long?: use `x ?? 0L` (zero-default) or `x.GetValueOrDefault(0L)`. "
            "Never assign nullable directly to non-nullable local or field."
        )
        print(f"  Retry Advisor: {hit} nullable dereference (confidence=88%)")
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.88,
            constitutional_trace="C-082 (Build Validation — nullable dereference must be explicit)"
        )

    # ── Rule 6c: CS1503 — argument type mismatch ──────────────────────────────
    if "CS1503" in error_codes:
        m = re.search(
            r"Argument (\d+).*?cannot convert from '([^']+)' to '([^']+)'",
            build_error, re.DOTALL
        )
        arg_n = m.group(1) if m else "?"
        from_t = m.group(2) if m else "?"
        to_t = m.group(3) if m else "?"
        fix = (
            f"CONSTRUCTOR/METHOD ARGUMENT TYPE MISMATCH (CS1503): "
            f"Argument {arg_n} is '{from_t}' but the parameter expects '{to_t}'. "
            "Check the BRANCH CONTEXT for the exact constructor or method signature. "
            "Common causes: (1) passing NullLogger<T> where ILogger<T> expected — use ILogger<T> directly; "
            "(2) passing a mock where a concrete type expected — use mock.Object; "
            "(3) wrong generic type parameter — check PTR snapshot for exact class name."
        )
        print(f"  Retry Advisor: CS1503 argument type mismatch arg={arg_n} ({from_t}→{to_t}) (confidence=85%)")
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.85,
            constitutional_trace="C-082 (Build Validation — constructor argument types must match signature)"
        )

    # ── Rule 6d: CS1744 — named argument after positional ────────────────────
    if "CS1744" in error_codes:
        m = re.search(r"Named argument '(\w+)' specifies a parameter for which a positional", build_error)
        bad_arg = m.group(1) if m else "unknown"
        fix = (
            f"NAMED ARGUMENT AFTER POSITIONAL (CS1744): "
            f"Named argument '{bad_arg}' is used after positional arguments — this is invalid in C#. "
            "Rule: either ALL arguments are named, or ALL are positional. Do NOT mix. "
            "Fix: convert all arguments to positional order matching the constructor/method signature, "
            "OR convert all arguments to named form. Check PTR/BRANCH CONTEXT for exact parameter order."
        )
        print(f"  Retry Advisor: CS1744 named+positional arg conflict on '{bad_arg}' (confidence=92%)")
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.92,
            constitutional_trace="C-082 (Build Validation — named and positional args cannot be mixed)"
        )

    # ── Rule 6e: CS1729 — no matching constructor ─────────────────────────────
    if "CS1729" in error_codes:
        m = re.search(r"'([^']+)' does not contain a constructor that takes (\d+) argument", build_error)
        type_n = m.group(1) if m else "unknown"
        arg_c = m.group(2) if m else "?"
        fix = (
            f"WRONG CONSTRUCTOR ARITY (CS1729): "
            f"'{type_n}' has no constructor taking {arg_c} argument(s). "
            "Check BRANCH CONTEXT and PTR for the exact constructor signature. "
            "Fix: match constructor arguments exactly to what is defined on this branch."
        )
        print(f"  Retry Advisor: CS1729 wrong constructor arity for '{type_n}' ({arg_c} args) (confidence=88%)")
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.88,
            constitutional_trace="C-082 (Build Validation — constructor arity must match definition)"
        )

    # ── Rule 7: CS0019 — operator applied to non-nullable type ──────────────────
    if "CS0019" in error_codes:
        diagnosis = _classify_cs0019_nullable_operator(build_error)
        if diagnosis:
            print(f"  Retry Advisor: CS0019 null-coalescing on non-nullable (confidence={diagnosis.confidence:.0%})")
            return diagnosis

    # ── Rule 7b: CS7036 — missing constructor argument ──────────────────────────
    if "CS7036" in error_codes:
        diagnosis = _classify_cs7036_constructor_args(build_error)
        if diagnosis:
            print(f"  Retry Advisor: CS7036 constructor-arg mismatch (confidence={diagnosis.confidence:.0%})")
            return diagnosis

    # ── Rule 8: CS0539 — explicit interface member not in interface ──────────────
    if "CS0539" in error_codes:
        m = re.search(r"'[^.]+\.([^']+)' in explicit interface declaration is not found", build_error)
        bad_member = m.group(1) if m else "unknown"
        fix = (
            f"INVENTED INTERFACE MEMBER (CS0539): '{bad_member}' does not exist on IClaimEvaluator.\n"
            f"IClaimEvaluator has EXACTLY TWO members:\n"
            f"  1. string ClaimId {{ get; }}\n"
            f"  2. Task<EvaluationResult> EvaluateAsync(EvaluationContext context, CancellationToken ct = default);\n"
            f"Remove the explicit interface declaration for '{bad_member}' entirely.\n"
            f"If you need per-evaluator metadata, add it as a PRIVATE field — not on the interface."
        )
        print(f"  Retry Advisor: CS0539 invented interface member '{bad_member}' (confidence=95%)")
        return RetryDiagnosis(
            error_type="WRONG_FIELD_NAME",
            fix_instruction=fix,
            should_retry=True,
            confidence=0.95,
            constitutional_trace="C-082 (Build Validation — do not invent interface members)"
        )

    # ── Rule 9: CS0505 — overriding property as method ────────────────────────
    if "CS0505" in error_codes:
        m = re.search(r"'([^.]+)\.(\w+)\(\)'.*'([^']+)' is not a function", build_error)
        if not m:
            m = re.search(r"cannot override.*'([^']+)'.*is not a function", build_error)
        fix = (
            "PROPERTY OVERRIDE ERROR (CS0505): You tried to override a property as a method. "
            "In Grpc.Core.ServerCallContext, ALL core members are abstract PROPERTIES — "
            "NEVER use parentheses '()' when overriding them. "
            "CORRECT form: protected override string MethodCore => \"value\"; "
            "WRONG form:   protected override string MethodCore() => \"value\"; "
            "Members that are properties (no parentheses): "
            "MethodCore, HostCore, DeadlineCore, RequestHeadersCore, "
            "CancellationTokenCore, PeerCore, AuthContextCore, StatusCore, WriteOptionsCore. "
            "Members that ARE methods (use parentheses): "
            "CreatePropagationTokenCore(options), WriteResponseHeadersAsyncCore(headers)."
        )
        print(f"  Retry Advisor: CS0505 property-as-method override (confidence=95%)")
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=fix,
            should_retry=True,
            confidence=0.95,
            constitutional_trace="C-082 (Build Validation — Grpc.Core.ServerCallContext members are properties)"
        )

    # ── Rules 10-14: Multi-stack classifiers (WC013-022) ─────────────────────
    # Python/Temporal/Vertex AI/Terraform/TypeScript — added for future sprints

    diagnosis = _classify_python_import_error(build_error)
    if diagnosis:
        print(f"  Retry Advisor: Python import error → {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
        return diagnosis

    diagnosis = _classify_python_async_error(build_error)
    if diagnosis:
        print(f"  Retry Advisor: Python async error → {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
        return diagnosis

    diagnosis = _classify_temporal_error(build_error)
    if diagnosis:
        print(f"  Retry Advisor: Temporal error → {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
        return diagnosis

    diagnosis = _classify_terraform_error(build_error)
    if diagnosis:
        print(f"  Retry Advisor: Terraform error → {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
        return diagnosis

    diagnosis = _classify_typescript_error(build_error)
    if diagnosis:
        print(f"  Retry Advisor: TypeScript/Next.js error → {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
        return diagnosis

    # ── Family fallback (semantic) before expensive LLM fallback ──────────────
    # This avoids code-by-code whack-a-mole for large C# diagnostic spaces.
    if family == FAMILY_SIGNATURE_DRIFT:
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=(
                "SIGNATURE DRIFT: public constructor/method contract changed without updating all call sites. "
                "Patch all invocations to match the new signature OR add backward-compatible overload/optional arg. "
                f"Diagnostics: {summarize_facts(facts)}"
            ),
            should_retry=True,
            confidence=0.85,
            constitutional_trace="C-082 (Build Validation — signature contracts must remain call-site compatible)",
        )

    if family == FAMILY_NULLABILITY:
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=(
                "NULLABILITY MISMATCH: add explicit nullable handling (HasValue/Value or GetValueOrDefault) "
                "and avoid implicit nullable→non-nullable assignment. "
                f"Diagnostics: {summarize_facts(facts)}"
            ),
            should_retry=True,
            confidence=0.82,
            constitutional_trace="C-082 (Build Validation — nullability contracts must be explicit)",
        )

    if family == FAMILY_INTERFACE_CONTRACT:
        return RetryDiagnosis(
            error_type=WRONG_FIELD_NAME,
            fix_instruction=(
                "INTERFACE/OVERRIDE CONTRACT MISMATCH: align implementation signatures exactly with interface/base members. "
                "Remove invented members and correct property-vs-method override forms. "
                f"Diagnostics: {summarize_facts(facts)}"
            ),
            should_retry=True,
            confidence=0.80,
            constitutional_trace="C-082 (Build Validation — interface and override contracts must match exactly)",
        )

    if family == FAMILY_REFERENCE_CONFIG:
        return RetryDiagnosis(
            error_type=MISSING_USING,
            fix_instruction=(
                "REFERENCE/BUILD CONFIG ISSUE: resolve package/project references first (restore/update refs), "
                "then retry code generation. "
                f"Diagnostics: {summarize_facts(facts)}"
            ),
            should_retry=False,
            confidence=0.90,
            constitutional_trace="C-082 (Build Validation — project reference graph must be valid before code retries)",
        )

    # ── Fallback 1: Learning cache (C-069 self-improvement) ──────────────────
    cache_hit = lookup_learning_cache(build_error[:200])
    if cache_hit:
        return cache_hit

    # ── Fallback 2: LLM classification ───────────────────────────────────────
    print(f"  Retry Advisor: pattern not recognized — calling cheap LLM classifier")
    diagnosis = _classify_with_llm(task_id, build_error)
    print(f"  Retry Advisor: LLM says {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")

    # Apply confidence gate — if confidence < 0.6, don't waste the retry
    if diagnosis.confidence < 0.6:
        diagnosis.should_retry = False
        diagnosis.fix_instruction = (
            f"Cannot diagnose with sufficient confidence ({diagnosis.confidence:.0%}). "
            f"Original error: {build_error[:200]}"
        )

    return diagnosis
