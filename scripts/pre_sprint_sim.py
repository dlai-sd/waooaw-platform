#!/usr/bin/env python3
"""
pre_sprint_sim.py — Pre-Sprint Work Contract Gap Analyser

# Implements: architecture/reference/magic-llm/architecture.md §0 The Disruption
# Constitutional basis: C-086 (Pre-Execution Simulation Gate), C-082 (Build Validation),
#                       C-059 (Traceability), C-032 (Spec-Code Drift)
# GOAL-003 Phase C

Proactive simulation: identifies probable failure modes BEFORE the autonomous
sprint runs. Converts the system from reactive (fail → classify → retry) to
proactive (predict → prevent → succeed).

Checks per task in a Work Contract:
  1. Type gaps   — types referenced in spec that are NOT in PTR 2.0
  2. Package gaps — packages referenced in spec with no handler in Retry Advisor
  3. SDK gaps    — known-risky SDK patterns (Temporal, Vertex AI, etc.) in spec
  4. Dep gaps    — dependent tasks/WCs not yet merged to main
  5. Ambiguities — spec sections with multiple valid interpretations
  6. CCT gaps    — CCT gate required but no corresponding test pattern exists

Run before a sprint trigger:
  python3 scripts/pre_sprint_sim.py work-contracts/WC-013-*.md
  python3 scripts/pre_sprint_sim.py --all  (all remaining WCs)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent


# ── Known-risky patterns per stack ────────────────────────────────────────────

_RISKY_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "python": [
        (r"\btemporalio\b|\btemporal\b", "TEMPORAL_SDK",
         "Temporal SDK — ensure @workflow.defn and @activity.defn decorators. "
         "Import: 'from temporalio import activity, workflow'"),
        (r"vertexai|google\.cloud\.aiplatform|gemini", "VERTEX_AI_SDK",
         "Vertex AI — import 'from google.cloud import aiplatform'. "
         "Model: 'gemini-2.0-flash' NOT 'gemini-pro'. SA key from GOOGLE_VERTEX_SA_KEY env."),
        (r"sarvam", "SARVAM_SDK",
         "Sarvam AI — NO Python SDK exists. Use httpx REST calls ONLY."),
        (r"asyncio\.run\s*\(", "ASYNCIO_RUN_IN_HANDLER",
         "asyncio.run() inside FastAPI/Temporal handler — event loop already running. Use 'await' directly."),
        (r"\.result\(\)|\.wait\(\)", "SYNC_BLOCK_IN_ASYNC",
         "Blocking .result()/.wait() in async context. Use 'await' instead."),
    ],
    "dotnet": [
        (r"TryGetValue\s*\(", "CS1061_TRY_GET_VALUE",
         "TryGetValue on non-dictionary. EvaluationContext.GetParameter() returns string directly."),
        (r"\.Protos\.", "WRONG_NAMESPACE_PROTOS",
         "Namespace 'Protos' does not exist. Use Waooaw.ConstitutionalEngine.Grpc"),
        (r"async void\b", "ASYNC_VOID",
         "async void is dangerous — use async Task instead. Only allowed for event handlers."),
        (r"\bnew \w+Context\(\)", "DBCONTEXT_NO_DI",
         "DbContext must be injected via DI, never instantiated with new()."),
    ],
    "terraform": [
        (r"azurerm_\w+", "TERRAFORM_RESOURCE",
         "Azure resource — verify attribute names against azurerm 4.x docs. "
         "Never hardcode subscription/tenant IDs."),
        (r"\".*password.*\"", "TERRAFORM_HARDCODED_SECRET",
         "Hardcoded password/secret — use var.* or key vault data source."),
    ],
    "typescript": [
        (r"useState|useEffect|useRef|onClick|onChange", "NEXTJS_CLIENT_NEEDED",
         "Using React hooks or event handlers — add 'use client'; as FIRST line of file."),
        (r"import.*from.*['\"]\.\.\/\.\.\/", "NEXTJS_RELATIVE_IMPORT",
         "Deep relative imports — use @/ alias (tsconfig paths). e.g. '@/components/...'"),
        (r"useRouter\(\)|usePathname\(\)|useSearchParams\(\)", "NEXTJS_ROUTER_HOOK",
         "useRouter/usePathname/useSearchParams only work in Client Components. Add 'use client';"),
    ],
}

# Known SDK patterns that require Retry Advisor handlers
_SDK_HANDLERS: dict[str, list[str]] = {
    "python": ["TEMPORAL_SDK", "VERTEX_AI_SDK", "SARVAM_SDK", "ASYNCIO_RUN_IN_HANDLER"],
    "dotnet": ["CS1061_TRY_GET_VALUE", "WRONG_NAMESPACE_PROTOS"],
    "terraform": [],  # Retry Advisor handles TERRAFORM_UNSUPPORTED_ARGUMENT etc.
    "typescript": ["NEXTJS_CLIENT_NEEDED"],
}


@dataclass
class TaskGap:
    task_id: str
    gap_type: str          # TYPE_GAP | PACKAGE_GAP | SDK_GAP | DEP_GAP | AMBIGUITY | CCT_GAP
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW
    description: str
    fix_suggestion: str


@dataclass
class WCSimResult:
    wc_file: str
    wc_id: str
    stack: str
    tasks_analysed: int
    gaps: list[TaskGap] = field(default_factory=list)
    ptr_summary: dict[str, int] = field(default_factory=dict)

    @property
    def critical_gaps(self) -> list[TaskGap]:
        return [g for g in self.gaps if g.severity == "CRITICAL"]

    @property
    def high_gaps(self) -> list[TaskGap]:
        return [g for g in self.gaps if g.severity == "HIGH"]

    @property
    def sprint_confidence(self) -> str:
        if self.critical_gaps:
            return "LOW — address CRITICAL gaps before triggering sprint"
        if len(self.high_gaps) >= 3:
            return "MEDIUM — address HIGH gaps to improve first-attempt success rate"
        if self.high_gaps:
            return "MEDIUM-HIGH — likely to succeed with 1-2 retries"
        return "HIGH — sprint likely to succeed on first attempt"


# ── PTR gap detection ──────────────────────────────────────────────────────────

def _detect_type_gaps(spec_text: str, ptr: dict, stack: str) -> list[tuple[str, str]]:
    """Find PascalCase type names in spec that are NOT in the PTR."""
    gaps = []
    type_names = set(re.findall(r'\b([A-Z][a-zA-Z0-9]{3,})\b', spec_text))
    stack_types = ptr.get(stack, {}).get("types", {})
    stack_packages = ptr.get(stack, {}).get("packages", {})

    # Filter: only names that look like types, not common words
    ignore = {"This", "The", "Note", "For", "Use", "When", "With", "Returns",
              "Each", "Any", "All", "New", "True", "False", "None", "List",
              "Dict", "Optional", "Union", "Type", "Class", "Task", "Step"}

    for name in sorted(type_names - ignore):
        # Check if any PTR key contains this name
        in_ptr = any(name in k for k in stack_types.keys())
        in_packages = any(name.lower() in p.lower() for p in stack_packages.keys())
        if not in_ptr and not in_packages:
            # Only flag if it looks like a WAOOAW-specific or SDK-specific type
            if any(c in name for c in ("Context", "Service", "Request", "Response",
                                        "Handler", "Manager", "Registry", "Client",
                                        "Worker", "Workflow", "Activity")):
                gaps.append((name, "Not found in PTR — model may invent wrong signature"))
    return gaps


def _detect_package_gaps(spec_text: str, ptr: dict, stack: str) -> list[tuple[str, str]]:
    """Find package imports/references in spec not in PTR."""
    gaps = []
    packages = ptr.get(stack, {}).get("packages", {})

    if stack == "python":
        # Find 'import X' or 'from X import' patterns
        imports = re.findall(r'(?:^from|^import)\s+(\w+)', spec_text, re.MULTILINE)
        for imp in imports:
            if imp not in ("os", "sys", "re", "json", "typing", "datetime",
                           "pathlib", "dataclasses", "enum", "abc", "asyncio"):
                if not any(imp in p.lower() for p in packages.keys()):
                    gaps.append((imp, f"Package '{imp}' not in PTR — verify it's in requirements.txt"))

    if stack == "dotnet":
        # Find 'using X' patterns
        usings = re.findall(r'using\s+([\w.]+);', spec_text)
        for using in usings:
            pkg = using.split(".")[0]
            if pkg not in ("System", "Microsoft", "Grpc", "Waooaw"):
                if not any(pkg.lower() in p.lower() for p in packages.keys()):
                    gaps.append((using, f"Namespace '{using}' not in PTR — verify package is in .csproj"))

    return gaps


def _detect_sdk_risks(spec_text: str, stack: str) -> list[tuple[str, str, str]]:
    """Find known-risky SDK patterns in spec text."""
    risks = []
    for pattern, risk_id, description in _RISKY_PATTERNS.get(stack, []):
        if re.search(pattern, spec_text, re.IGNORECASE):
            risks.append((pattern, risk_id, description))
    return risks


# ── WC file parser ────────────────────────────────────────────────────────────

def _parse_wc_file(wc_path: Path) -> dict[str, Any]:
    """Parse a Work Contract .md file for task metadata."""
    content = wc_path.read_text(encoding="utf-8", errors="ignore")

    # Extract WC ID
    wc_id_match = re.search(r"Work Contract (\d+)", content)
    wc_id = f"WC-{wc_id_match.group(1):0>3}" if wc_id_match else wc_path.stem[:6]

    # Extract stack — check explicit primary-stack signals first (most specific wins)
    # IMPORTANT: Temporal is used across stacks (CE/.NET consuming Temporal signals).
    # Do NOT use 'temporal' alone as a Python signal — require python-only keywords.
    if re.search(r'\.net\s*9|\.csproj|dotnet\s+build|dotnet\s+test|setup-dotnet|csharp|using\s+\w+;', content, re.I):
        stack = "dotnet"
    elif re.search(r'terraform|azurerm|\.tf\b', content, re.I):
        stack = "terraform"
    elif re.search(r'typescript|next\.js|react|tailwind|\.tsx?\b', content, re.I):
        stack = "typescript"
    elif re.search(r'fastapi|asyncio|pydantic|requirements\.txt|pip install|python\s+\d', content, re.I):
        stack = "python"
    else:
        stack = "dotnet"  # default — most WCs are .NET

    # Extract task IDs and their descriptions
    tasks = []
    task_pattern = re.compile(
        r'###\s+(WC\d{3}-\d+[a-z]?)\s+[—–-]\s+([^\n]+)\n(.*?)(?=###|\Z)',
        re.DOTALL
    )
    for m in task_pattern.finditer(content):
        task_id = m.group(1)
        description = m.group(2).strip()
        body = m.group(3)

        # Extract spec_sections references
        spec_refs = re.findall(r'`([^`]+\.md[^`]*)`|architecture/reference/[^\s]+', body)
        has_cct = bool(re.search(r'CCT-|cct_', body, re.I))
        model_hint = re.search(r'model_hint.*?(reasoning|auto|none)', body, re.I)

        tasks.append({
            "task_id": task_id,
            "description": description,
            "body": body,
            "spec_refs": spec_refs,
            "has_cct": has_cct,
            "model_hint": model_hint.group(1).lower() if model_hint else "reasoning",
        })

    # Extract dependencies
    deps = re.findall(r'Depends on.*?(WC-\d+)', content, re.I)

    return {
        "wc_id": wc_id,
        "stack": stack,
        "tasks": tasks,
        "dependencies": deps,
        "content": content,
    }


# ── Main simulation ────────────────────────────────────────────────────────────

def simulate_wc(wc_path: Path) -> WCSimResult:
    """Run pre-sprint simulation for a single Work Contract."""
    print(f"\n{'='*70}")
    print(f"  PRE-SPRINT SIMULATION: {wc_path.name}")
    print(f"{'='*70}")

    wc_data = _parse_wc_file(wc_path)
    wc_id = wc_data["wc_id"]
    stack = wc_data["stack"]

    # Assemble PTR 2.0
    try:
        from scripts.ptr_assembler import PTR2Assembler
        assembler = PTR2Assembler()
        ptr = assembler.assemble(scope=["src", "scripts"])
        print(f"  PTR 2.0 assembled: {len(ptr.get(stack, {}).get('types', {}))} {stack} types "
              f"· {len(ptr.get(stack, {}).get('packages', {}))} packages")
    except Exception as e:
        print(f"  WARN: PTR assembly failed ({e}) — using empty PTR")
        ptr = {}

    ptr_summary = {
        s: len(ptr.get(s, {}).get("types", {}))
        for s in ("dotnet", "python", "terraform", "typescript")
    }

    result = WCSimResult(
        wc_file=str(wc_path),
        wc_id=wc_id,
        stack=stack,
        tasks_analysed=len(wc_data["tasks"]),
        ptr_summary=ptr_summary,
    )

    # Check dependencies
    for dep in wc_data["dependencies"]:
        dep_path = list(REPO_ROOT.glob(f"work-contracts/{dep}*.md"))
        # Check if dep is merged (src/ files exist from it)
        dep_wc_num = re.search(r"WC-(\d+)", dep)
        if dep_wc_num:
            dep_src = list((REPO_ROOT / "src").glob(f"**/*.cs")) + \
                      list((REPO_ROOT / "src").glob(f"**/*.py"))
            if not dep_src:  # crude check
                result.gaps.append(TaskGap(
                    task_id=wc_id,
                    gap_type="DEP_GAP",
                    severity="CRITICAL",
                    description=f"Dependency {dep} has not been merged yet — src/ is empty",
                    fix_suggestion=f"Complete and merge {dep} before triggering this sprint"
                ))

    # Analyse each task
    for task in wc_data["tasks"]:
        task_id = task["task_id"]
        spec_text = task["body"] + " " + task["description"]
        print(f"\n  Analysing {task_id}: {task['description'][:50]}...")

        # 1. Type gaps
        type_gaps = _detect_type_gaps(spec_text, ptr, stack)
        for type_name, reason in type_gaps[:5]:  # cap per task
            result.gaps.append(TaskGap(
                task_id=task_id,
                gap_type="TYPE_GAP",
                severity="HIGH",
                description=f"Type '{type_name}' referenced but not in PTR: {reason}",
                fix_suggestion=(
                    f"Add '{type_name}' to PTR before sprint: "
                    f"if it's from a prior WC, ensure that WC is merged first. "
                    f"If it's a new type, add a forward declaration in the Engineering Design Record."
                )
            ))
            print(f"    ⚠️  TYPE_GAP (HIGH): '{type_name}' not in PTR")

        # 2. Package gaps
        pkg_gaps = _detect_package_gaps(spec_text, ptr, stack)
        for pkg_name, reason in pkg_gaps[:3]:
            result.gaps.append(TaskGap(
                task_id=task_id,
                gap_type="PACKAGE_GAP",
                severity="MEDIUM",
                description=f"Package/namespace '{pkg_name}' in spec but not confirmed in PTR",
                fix_suggestion=f"Verify '{pkg_name}' is in the project's package manifest and PTR"
            ))
            print(f"    ℹ️  PACKAGE_GAP (MEDIUM): '{pkg_name}'")

        # 3. SDK risks
        sdk_risks = _detect_sdk_risks(spec_text, stack)
        for _, risk_id, description in sdk_risks:
            severity = "CRITICAL" if risk_id in (
                "SARVAM_SDK", "ASYNCIO_RUN_IN_LOOP", "TERRAFORM_HARDCODED_SECRET"
            ) else "HIGH"
            result.gaps.append(TaskGap(
                task_id=task_id,
                gap_type="SDK_GAP",
                severity=severity,
                description=f"SDK risk [{risk_id}]: {description[:100]}",
                fix_suggestion=(
                    f"Retry Advisor handler exists for {risk_id} — "
                    f"model will receive correction on first failure. "
                    f"Pre-empt by adding the correct pattern to the spec."
                )
            ))
            sym = "🔴" if severity == "CRITICAL" else "🟡"
            print(f"    {sym}  SDK_GAP ({severity}): [{risk_id}]")

        # 4. CCT gap
        if task.get("has_cct"):
            # Check if a CCT simulation exists for this task
            # SKIP framework-level CCTs — these are platform-wide tests, not sprint-specific.
            # CCT-EF (Evidence First), CCT-HO (Human Override), CCT-MT (Multi-Tenant),
            # CCT-ES (Emergency Stop), CCT-PIPE (Pipeline) are constitutional infrastructure.
            # Sprint authors write task-specific CCTs; framework CCTs already have suites.
            _FRAMEWORK_CCTS = {"EF", "HO", "MT", "ES", "PIPE", "CE"}
            cct_refs = re.findall(r'CCT-([A-Z]+)', spec_text)
            for cct in cct_refs:
                if cct in _FRAMEWORK_CCTS:
                    continue  # Framework CCT — no sprint-specific simulation required
                cct_files = list(REPO_ROOT.glob(f"simulation/*{cct}*"))
                if not cct_files:
                    result.gaps.append(TaskGap(
                        task_id=task_id,
                        gap_type="CCT_GAP",
                        severity="HIGH",
                        description=f"CCT-{cct} gate required but no simulation exists",
                        fix_suggestion=f"Create simulation/SIM-CCT-{cct}.md per C-086 before sprint"
                    ))
                    print(f"    🟡  CCT_GAP (HIGH): CCT-{cct} has no pre-execution simulation")

    # Print summary
    print(f"\n  {'─'*68}")
    print(f"  SUMMARY: {result.wc_id} | stack={result.stack} | tasks={result.tasks_analysed}")
    print(f"  Gaps: {len(result.critical_gaps)} CRITICAL · {len(result.high_gaps)} HIGH · "
          f"{len([g for g in result.gaps if g.severity == 'MEDIUM'])} MEDIUM")
    print(f"  Sprint confidence: {result.sprint_confidence}")

    return result


def main() -> int:
    args = sys.argv[1:]
    if not args or args == ["--help"]:
        print("Usage: python3 scripts/pre_sprint_sim.py <wc-file.md> [wc-file2.md ...]")
        print("       python3 scripts/pre_sprint_sim.py --all")
        return 0

    if args == ["--all"]:
        wc_files = sorted((REPO_ROOT / "work-contracts").glob("WC-0[1-9]*.md"))
    else:
        wc_files = [Path(a) for a in args if Path(a).exists()]

    if not wc_files:
        print("No Work Contract files found")
        return 1

    all_results = []
    for wc_file in wc_files:
        result = simulate_wc(wc_file)
        all_results.append(result)

    # Overall report
    print(f"\n{'='*70}")
    print("  PRE-SPRINT SIMULATION — OVERALL REPORT")
    print(f"{'='*70}")
    for r in all_results:
        print(f"  {r.wc_id:10} | {r.sprint_confidence}")

    critical_total = sum(len(r.critical_gaps) for r in all_results)
    if critical_total:
        print(f"\n  ⛔  {critical_total} CRITICAL gap(s) must be resolved before sprints trigger.")
    else:
        print(f"\n  ✅  No CRITICAL gaps. Sprint execution can proceed.")

    return 1 if critical_total else 0


if __name__ == "__main__":
    sys.exit(main())
