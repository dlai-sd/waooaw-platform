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


def _classify_cs0117(error: str) -> Optional[RetryDiagnosis]:
    """
    CS0117: 'X' does not contain a definition for 'Y'
    Root cause: Claude invented a property/field name that doesn't exist.
    Fix: Tell Claude to use default() or empty constructors for proto-generated types.
    constitutional_trace: C-082 (build validation — generated code must compile)
    """
    m = re.search(r"'([^']+)' does not contain a definition for '([^']+)'", error)
    if not m:
        return None

    class_name, field_name = m.group(1), m.group(2)

    fix = (
        f"FIELD ERROR: '{class_name}' does not have a property '{field_name}'. "
        f"You invented a field name that does not exist in the proto-generated class. "
        f"For proto-generated response types: use empty constructors (new {class_name}()) "
        f"rather than object initializers. Do NOT set properties unless you have verified "
        f"the exact property name from the proto definition. "
        f"The proto is in Protos/constitutional_service.proto — check the actual field names."
    )
    return RetryDiagnosis(
        error_type=WRONG_FIELD_NAME,
        fix_instruction=fix,
        should_retry=True,
        confidence=0.85,
        constitutional_trace="C-082 (Build Validation — generated code must compile before commit)"
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


# ── LLM-assisted classifier for UNKNOWN patterns ──────────────────────────────

def _classify_with_llm(task_id: str, error: str) -> RetryDiagnosis:
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

    print(f"  Retry Advisor: {task_id} — error codes: {sorted(error_codes)}")

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
                f"Check the BRANCH CONTEXT section for the exact class/enum names. "
                f"For EvaluationResult: use EvaluationVerdict (not EvaluationDecision). "
                f"For EvaluationVerdict values: Allow, Deny, Escalate (exact case). "
                f"Never invent new type names — only use types visible in the spec or branch context."
            )
            print(f"  Retry Advisor: WRONG_FIELD_NAME/undefined name CS0103 (confidence=88%)")
            return RetryDiagnosis(
                error_type=WRONG_FIELD_NAME,
                fix_instruction=fix,
                should_retry=True,
                confidence=0.88,
                constitutional_trace="C-082 (Build Validation — generated code must use defined types)"
            )

    # ── Fallback: LLM classification ───────────────────────────────────────────
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
