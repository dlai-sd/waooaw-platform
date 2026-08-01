#!/usr/bin/env python3
"""
context_builder.py — MagicLLM Context Builder

# Implements: architecture/reference/magic-llm/architecture.md §7 Context Management Strategy
# Constitutional basis:
#   C-032 (Spec-Code Alignment — ordered context assembly is mandatory)
#   C-085 (Idempotency — prior task output injection, not assumptions)
#   C-059 (Traceability — preamble pre-written with spec path + claims)
#   C-073 (Constitutional annotations — every file header produced here)
# Office: AI Architect (INST-008)
# ADR: ADR-032

Implements the §7.1 mandatory 9-step ordered context assembly:
  [1] SYSTEM      — constitutional obligations + forbidden patterns
  [2] PREAMBLE    — file header pre-written (C-073), LLM cannot alter
  [3] FROZEN      — frozen artifact signatures from prior compile gates
  [4] PTR         — compiled types, auto-populated from filesystem
  [5] USING_MAP   — namespace index, auto-populated from filesystem
  [6] SPEC        — spec sections from Work Contract only
  [7] PRIOR       — prior task compiled output signatures
  [8] TASK        — task description + output file list
  [9] FORMAT      — output format instruction

Key properties:
  - PTR and USING_MAP are auto-populated from the current filesystem (sprint branch)
  - Preamble is generated from USING_MAP + spec metadata (never from LLM)
  - Frozen registry is maintained across subtask executions
  - Context is 85-95% smaller than current runner prompts with higher precision
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent

# Forbidden patterns injected into every SYSTEM block (§14 constitutional constraints)
_FORBIDDEN_PATTERNS = (
    "⛔ FIRST LINE RULE: every .cs file MUST start with // or using — NEVER ## or markdown\n"
    "⛔ .AsTask() on Task<T> — use 'await task;' directly\n"
    "⛔ .TryGetValue() on EvaluationContext — use ctx.GetParameter('key')\n"
    "⛔ BudgetRemainingInrPaise — does not exist; compute from the three budget fields\n"
    "⛔ ValidationDecision.Authorized/Denied/Permit — use Allow/Deny/Escalate\n"
    "⛔ CS0019 CE gRPC ENUM MISMATCH: ValidateActionResponse.Decision is type ValidationDecision. "
    "Comparing it with PolicyDecision.* causes CS0019. "
    "CORRECT: ceResponse.Decision != ValidationDecision.Allow | ceResponse.Decision != ValidationDecision.Deny. "
    "WRONG: ceResponse.Decision != PolicyDecision.Permit (CS0019). "
    "PolicyDecision is only for EvaluatePolicyResponse.Decision (different RPC).\n"
    "⛔ new ConstitutionalDbContext() — inject via constructor DI only\n"
    "⛔ Mixed named+positional constructor args (CS1744) — use all positional\n"
    "⛔ NullLogger<T>() constructor — use NullLogger<T>.Instance\n"
    "⛔ ITemporalClient or any Temporalio.* namespace in WC012-02b — that is WC012-04b scope\n"
    "⛔ using Waooaw.*.Tests.* in src/ files — test namespaces must never appear in main project code\n"
    "⛔ using Waooaw.ConstitutionalEngine.Evaluators (or .Services, .Data, .EmergencyStop) in "
    "business-platform files — BP has NO ProjectReference to CE; CE is accessible ONLY via gRPC. "
    "Only valid CE namespace in BP files: Waooaw.ConstitutionalEngine.Grpc (proto-generated client). "
    "Remove ALL other CE usings. This rule applies even if PDM boundary text is not visible above."
)

# Python-specific ruff violations observed in prior sprints — C-069 static seed
_PYTHON_FORBIDDEN_PATTERNS = (
    "⛔ [ANN201] Every public function MUST have an explicit return type annotation: "
    "def f() -> None, def f() -> dict[str, Any], def f() -> list[X]. "
    "FastAPI endpoints: async def get_catalog(...) -> list[ThreadCatalogItem]: "
    "NEVER write 'async def get_catalog(...)' without a return type.\n"
    "⛔ [ANN001] Every function parameter MUST have a type annotation: "
    "def f(x: int, y: str) — never 'def f(x, y)' without types.\n"
    "⛔ [B017] NEVER use pytest.raises(Exception) — Exception is too broad and masks real bugs. "
    "Always use a specific exception type: pytest.raises(ValueError), pytest.raises(RuntimeError), "
    "pytest.raises(HTTPException). If you truly need Exception, add match=: "
    "pytest.raises(Exception, match='specific message').\n"
    "⛔ [B006] Never use mutable defaults in function signatures: NOT 'def f(x=[])' or 'def f(x={})'. "
    "Use None sentinel: 'def f(x: list | None = None): if x is None: x = []'.\n"
    "⛔ [F841] Never assign to a variable that is never used: NOT 'result = client.post(...)' if "
    "result is never read. Either assert on it or prefix with underscore: '_result = client.post(...)'.\n"
    "⛔ [B018] Never write a bare expression as a statement (useless expression). "
    "Every line must be an assignment, function call, return, raise, assert, import, or control flow.\n"
    "⛔ [ANN401] Avoid 'Any' as a type annotation unless the type genuinely cannot be specified. "
    "Use specific types: asyncpg.Pool, httpx.AsyncClient, or the actual Pydantic model.\n"
    "⛔ [G004] Never use f-strings in logging calls in src/ files: NOT 'logger.info(f\"val={x}\")'. "
    "Use lazy format: 'logger.info(\"val=%s\", x)'.\n"
)

# TypeScript/Next.js constitutional constraints
_TYPESCRIPT_FORBIDDEN_PATTERNS = (
    "⛔ [TS-NOANY] Never use 'any' type — use specific types or 'unknown' with type guards.\n"
    "⛔ [TS-JWT] JWTs MUST be cookie-only (httpOnly, secure, sameSite=strict). "
    "Never store JWTs in localStorage or sessionStorage.\n"
    "⛔ [TS-EMSTOP] Emergency Stop must be wired — all AgentSession components must subscribe "
    "to /api/emergency-stop SSE endpoint and render a visible STOPPED banner.\n"
    "⛔ [TS-CONSOLE] Never use console.log in src/ — use the platform logger utility.\n"
    "⛔ [TS-CLIENT] Mark components 'use client' ONLY when they use browser APIs or hooks. "
    "Default to server components for data-fetching.\n"
)

# Terraform constitutional constraints
_TERRAFORM_FORBIDDEN_PATTERNS = (
    "⛔ [TF-SECRETS] Never hardcode secrets in Terraform — use Key Vault references only. "
    "WRONG: var.db_password = 'abc123'. RIGHT: data.azurerm_key_vault_secret.db_password.value.\n"
    "⛔ [TF-STATE] Never put sensitive outputs in Terraform state — mark outputs sensitive=true.\n"
    "⛔ [TF-OUTPUTS] Every module MUST declare all required outputs listed in the SPEC section.\n"
    "⛔ [TF-PROVIDER] Only use provider versions pinned in versions.tf — never use 'latest'.\n"
)

# ── Module-level compiled regexes (P2: avoid recompile on every build call) ──
_RE_CAPITAL_WORDS = re.compile(r'\b([A-Z][a-zA-Z0-9]+)\b')
_RE_WHITESPACE    = re.compile(r'\s+')
_RE_NAMESPACE     = re.compile(r'^namespace\s+([\w.]+)', re.MULTILINE)
_RE_CLAIMS        = re.compile(r'C-\d{3}')
_RE_WC_CTOR       = re.compile(
    r'public\s+\w+\s*\(([^)]*)\)',
    re.MULTILINE,
)
_RE_METHODS       = re.compile(
    r'public\s+(?:async\s+)?(?:Task(?:<[^>]+>)?|void|bool|string|int|[A-Z]\w*)\s+'
    r'(\w+)\s*\([^)]*\)',
    re.MULTILINE,
)
_RE_CLASS_NAMES   = re.compile(
    r'public\s+(?:sealed\s+)?(?:class|interface|record)\s+(\w+)',
    re.MULTILINE,
)
_RE_PROPERTIES    = re.compile(
    r'public\s+(?:required\s+)?(\w[\w<>\[\]?]*)\s+(\w+)\s*\{[^}]*get',
    re.MULTILINE,
)

# Stack-specific using directives that must be present in every output file preamble
_STACK_BASE_USINGS: dict[str, list[str]] = {
    "dotnet": [],  # task-specific usings added per §7.5
    "python": ["from __future__ import annotations"],
    "typescript": [],
    "terraform": [],
}


@dataclass
class ContextBlock:
    """One slot in the §7.1 ordered context assembly."""
    slot: str
    content: str

    @property
    def chars(self) -> int:
        return len(self.content)


@dataclass
class AssembledContext:
    """Result of §7.1 ordered context assembly for one LLM invocation."""
    task_id: str
    output_file: str
    blocks: list[ContextBlock] = field(default_factory=list)
    preamble_lines: list[str] = field(default_factory=list)  # pre-written file header
    frozen_signatures_used: list[str] = field(default_factory=list)

    @property
    def full_prompt(self) -> str:
        """Concatenated prompt for LLM invocation."""
        return "\n\n---\n\n".join(b.content for b in self.blocks)

    @property
    def total_chars(self) -> int:
        return sum(b.chars for b in self.blocks)

    @property
    def preamble_text(self) -> str:
        """Pre-written file header (LLM receives this as already-written lines)."""
        return "\n".join(self.preamble_lines)


class ContextBuilder:
    """
    Implements MagicLLM §7 Context Management Strategy.

    Usage:
        builder = ContextBuilder()
        ctx = builder.build(
            task_id="WC012-02c",
            output_file="tests/.../CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1 Unit Tests"},
            constitutional_check="...",
            depends_on_tasks=["WC012-02a", "WC012-02b"],
            stack="dotnet",
        )
        print(ctx.full_prompt)  # ready to send to LLM
        print(ctx.preamble_text)  # tell LLM: these lines are already written
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or REPO_ROOT
        self._frozen_registry_path = self._root / "sprint-context" / "frozen-artifacts.json"
        self._frozen: dict[str, dict] = self._load_frozen_registry()
        self._assembler = self._get_ptr_assembler()
        # P3: per-instance file read cache — key=(path_str, mtime), value=content
        self._file_cache: dict[tuple[str, float], str] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def build(
        self,
        task_id: str,
        output_file: str,
        spec_sections: dict[str, str],
        constitutional_check: str,
        depends_on_tasks: list[str],
        stack: str = "dotnet",
        prior_output_files: list[str] | None = None,
    ) -> AssembledContext:
        """
        §7.1 ordered context assembly — 9 slots in mandatory order.
        Returns AssembledContext with full_prompt and preamble_text.
        """
        ctx = AssembledContext(task_id=task_id, output_file=output_file)

        # [1] SYSTEM
        ctx.blocks.append(ContextBlock("SYSTEM", self._build_system(stack, output_file)))

        # [2] PREAMBLE — pre-written file header (C-073, §7.5)
        preamble = self._build_preamble(output_file, spec_sections, stack, constitutional_check)
        ctx.preamble_lines = preamble
        ctx.blocks.append(ContextBlock(
            "PREAMBLE",
            "MANDATORY FILE HEADER — the file already starts with these exact lines. "
            "Extend from the line after the last using directive. "
            "NEVER alter or omit these lines:\n\n" + "\n".join(preamble)
        ))

        # [3] FROZEN — signatures from prior compile gates (§7.6)
        frozen_block = self._build_frozen_block(output_file, prior_output_files or [])
        if frozen_block:
            ctx.blocks.append(ContextBlock("FROZEN", frozen_block))

        # [4] PTR — auto-populated compiled types (§7.2)
        ptr_block = self._build_ptr_block(spec_sections, stack)
        if ptr_block:
            ctx.blocks.append(ContextBlock("PTR", ptr_block))

        # [4b] SKELETON — EA-produced type contracts for IMPLEMENTATION tasks (ADR-036, C-095)
        skeleton_block = self._build_skeleton_block(output_file, stack)
        if skeleton_block:
            ctx.blocks.append(ContextBlock("SKELETON", skeleton_block))

        # [5] USING_MAP — namespace index (§7.3)
        using_block = self._build_using_map_block(output_file, constitutional_check, stack)
        if using_block:
            ctx.blocks.append(ContextBlock("USING_MAP", using_block))

        # [6] SPEC — exact spec sections from Work Contract only
        spec_block = self._build_spec_block(spec_sections)
        if spec_block:
            ctx.blocks.append(ContextBlock("SPEC", spec_block))

        # [7] PRIOR — prior task compiled output injection (§7.4)
        prior_block = self._build_prior_block(prior_output_files or [])
        if prior_block:
            ctx.blocks.append(ContextBlock("PRIOR", prior_block))

        # [8] TASK — description + file target
        # If the output file already exists on the sprint branch, inject current
        # content so the LLM extends it instead of generating from scratch.
        existing_block = self._build_existing_file_block(output_file)
        if existing_block:
            ctx.blocks.append(ContextBlock("EXISTING_FILE", existing_block))

        # [8b] CONFTEST — auto-inject conftest.py when generating test files.
        # Provides the authoritative sys.path and fixture setup so the LLM derives
        # import conventions from the actual codebase rather than guessing.
        conftest_block = self._build_conftest_block(output_file)
        if conftest_block:
            ctx.blocks.append(ContextBlock("CONFTEST", conftest_block))

        ctx.blocks.append(ContextBlock("TASK", self._build_task_block(
            task_id, output_file, constitutional_check,
            file_exists=existing_block != ""
        )))

        # [9] FORMAT — output format instruction
        ctx.blocks.append(ContextBlock("FORMAT", self._build_format_block(output_file, preamble)))

        return ctx

    def freeze_artifact(self, file_path: str, task_id: str) -> bool:
        """
        §7.6: After compile gate PASS, freeze the public API surface.
        Extracts constructor signatures, methods, properties from the file.
        Returns True if freezing succeeded.
        """
        full_path = self._root / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text(encoding="utf-8", errors="replace")
        sigs = self._extract_public_signatures(content)
        if not sigs.get("namespace"):
            return False

        self._frozen[file_path] = {"frozen_at_task": task_id, **sigs}
        self._save_frozen_registry()
        return True

    def freeze_artifacts_from_task(self, output_files: list[str], task_id: str) -> int:
        """Freeze all output files from a completed task. Returns count frozen."""
        count = 0
        for f in output_files:
            if self.freeze_artifact(f, task_id):
                count += 1
        return count

    # ── Private: slot builders ─────────────────────────────────────────────────

    def _build_system(self, stack: str, output_file: str = "") -> str:
        base = (
            "PIPELINE SELF-MODEL (WAOOAW Platform — INST-010, C-059/C-082):\n"
            "OPERATING MODES: This pipeline handles greenfield code generation, enhancement\n"
            "of existing code, defect fixes, production fixes, and test additions on a live\n"
            "codebase. You are NOT always generating from scratch.\n"
            "When EXISTING_FILE or CONFTEST slots are present, read them FIRST to derive\n"
            "the existing conventions (imports, sys.path, fixtures, patterns) before writing\n"
            "a single line. Never invent a path or import that contradicts those slots.\n\n"
            "Your output passes through these 5 constitutional gates in sequence:\n"
            "  Gate FORMAT:     wrap every file in <file path=\"exact/path\">...</file>\n"
            "  Gate PATH:       the file must be at the EXACT path in the TASK block below\n"
            "  Gate COMPILE:    stack-specific: must exit 0 (syntax + style; ruff for Python)\n"
            "  Gate ANNOTATION: first lines must include '# Implements:' and '# constitutional_basis:'\n"
            "  Gate SPEC_ALIGN: no types or methods invented outside the SPEC block below\n"
            "If Gate COMPILE fails, you get 2 more attempts with the exact error injected into context.\n"
            "If all 3 attempts fail, EA Cascade activates — do NOT open spec-gap issues yourself.\n\n"
            "CONSTITUTIONAL OBLIGATIONS (C-059, C-073, C-032):\n"
            "Every file you produce MUST begin with:\n"
            "  // Implements: <spec-path> §<section>\n"
            "  // constitutional_basis: <C-NNN>\n"
            "Output format: <file path=\"relative/path.ext\">...content...</file>\n\n"
            "FORBIDDEN PATTERNS (non-negotiable — any violation = compile failure):\n"
            + _FORBIDDEN_PATTERNS
        )
        # Inject Python-specific ruff constraints (enforced by ruff check in COMPILE gate)
        if stack == "python":
            base += "\n\nPYTHON RUFF CONSTRAINTS (enforced by ruff check in COMPILE gate):\n" + _PYTHON_FORBIDDEN_PATTERNS
            # Inject violation history from learning cache (C-069 self-improvement)
            violations_path = Path(__file__).parent.parent.parent / "sprint-context" / "lint-violations.json"
            if violations_path.exists():
                try:
                    import json as _json
                    violations: dict = _json.loads(violations_path.read_text(encoding="utf-8"))
                    if violations:
                        history_lines = []
                        for code, v in violations.items():
                            last_task = v.get("last_task", "?")
                            fix = v.get("fix", "avoid this pattern")
                            history_lines.append(f"  ⛔ [{code}] seen in {last_task}: {fix}")
                        base += (
                            "\n\nVIOLATION HISTORY (do NOT repeat — seen in prior sprint runs):\n"
                            + "\n".join(history_lines)
                            + "\n"
                        )
                except Exception:
                    pass  # non-blocking — best-effort context injection
        # Inject TypeScript-specific constraints
        if stack == "typescript":
            base += "\n\nTYPESCRIPT CONSTITUTIONAL CONSTRAINTS:\n" + _TYPESCRIPT_FORBIDDEN_PATTERNS
        # Inject Terraform-specific constraints
        if stack == "terraform":
            base += "\n\nTERRAFORM CONSTITUTIONAL CONSTRAINTS:\n" + _TERRAFORM_FORBIDDEN_PATTERNS
        # Inject PROJECT_BOUNDARY — auto-derived from .csproj (replaces hard-coded namespace rules)
        if stack == "dotnet" and output_file:
            try:
                from project_dependency_map import find_csproj_for_file, get_boundary_injection_text
                csproj = find_csproj_for_file(output_file, self._root)
                if csproj:
                    base += "\n\n" + get_boundary_injection_text(csproj)
            except Exception as _pdm_e:
                pass  # non-blocking — boundary enforcement degrades gracefully
        # Inject EA-approved stack error-handling standards (STACK_BEHAVIORAL_RULES)
        try:
            from task_decomposer import STACK_BEHAVIORAL_RULES
            rules = STACK_BEHAVIORAL_RULES.get(stack, [])
            if rules:
                error_rules = [r for r in rules if r.startswith("ERROR HANDLING")]
                if error_rules:
                    base += (
                        "\n\nCONSTITUTIONAL ERROR HANDLING STANDARDS (C-082, C-059):\n"
                        + "\n".join(f"  • {r}" for r in error_rules)
                    )
        except Exception as _sbr_e:
            print(f"  [CB] STACK_BEHAVIORAL_RULES unavailable ({type(_sbr_e).__name__}: {_sbr_e})")
        return base

    def _build_preamble(
        self,
        output_file: str,
        spec_sections: dict[str, str],
        stack: str,
        constitutional_check: str,
    ) -> list[str]:
        """
        §7.5: Generate the pre-written file preamble.
        Returns list of lines that are ALREADY WRITTEN — LLM cannot alter them.
        """
        lines: list[str] = []
        ext = Path(output_file).suffix.lower()

        if ext == ".cs":
            # C-059/C-073 header
            spec_ref = list(spec_sections.keys())[0] if spec_sections else "architecture/reference"
            spec_section = list(spec_sections.values())[0] if spec_sections else "full"
            claims = self._extract_claims_from_check(constitutional_check)
            lines.append(f"// Implements: {spec_ref} {spec_section}")
            lines.append(f"// constitutional_basis: {claims}")

            # Required using directives — resolved from USING_MAP on sprint branch + known types
            usings = self._resolve_required_usings(output_file, constitutional_check, stack)
            for u in usings:
                lines.append(u)

        elif ext == ".py":
            spec_ref = list(spec_sections.keys())[0] if spec_sections else "architecture/reference"
            spec_section = list(spec_sections.values())[0] if spec_sections else "full"
            claims = self._extract_claims_from_check(constitutional_check)
            lines.append(f"# Implements: {spec_ref} {spec_section}")
            lines.append(f"# constitutional_basis: {claims}")
            lines.append("from __future__ import annotations")

        return lines

    def _build_frozen_block(self, output_file: str, prior_files: list[str]) -> str:
        """§7.3/§7.6: Inject frozen constructor/method signatures for referenced types."""
        if not self._frozen:
            return ""

        lines = ["COMPILED SIGNATURES (frozen after compile gate — constructor calls MUST match exactly):"]
        found = False

        for file_path, sigs in self._frozen.items():
            # Only inject signatures relevant to this file
            if not self._is_relevant_frozen(file_path, output_file, prior_files):
                continue
            ns = sigs.get("namespace", "")
            ctors = sigs.get("public_constructors", [])
            methods = sigs.get("public_methods", [])
            class_name = Path(file_path).stem

            lines.append(f"\n  // {class_name} — namespace: {ns}")
            for ctor in ctors[:2]:  # max 2 constructors
                ctor_clean = _RE_WHITESPACE.sub(' ', ctor).strip()
                lines.append(f"  constructor: {class_name}({ctor_clean})")
            for method in methods[:4]:  # max 4 methods
                lines.append(f"  method: {method}(...)")
            # Enum values — eliminates CS1503 string→EnumType pattern
            for enum_name, values in sigs.get("enum_values", {}).items():
                lines.append(f"  enum {enum_name}: {' | '.join(values)}")
                lines.append(f"  ⛔ Use {enum_name}.{values[0]} NOT \"{values[0]}\" (string causes CS1503)")

            sigs_note = sigs.get("frozen_at_task", "")
            if sigs_note:
                lines.append(f"  ⛔ Frozen at {sigs_note} — do NOT invent other signatures")
            found = True

        if not found:
            return ""

        lines.append(
            "\n⛔ CONSTRUCTOR RULE: use ALL-POSITIONAL args in this exact order. "
            "No named arguments after positional (causes CS1744).\n"
            "⛔ LOGGER RULE: use NullLogger<T>.Instance — not new NullLogger<T>() (causes CS1503)."
        )
        return "\n".join(lines)

    def _build_ptr_block(self, spec_sections: dict[str, str], stack: str) -> str:
        """§7.2: PTR auto-populated from filesystem."""
        if not self._assembler:
            return ""
        try:
            ptr = self._assembler.assemble(scope=["src", "tests"])
            spec_text = " ".join(spec_sections.values())
            task_ptr = self._assembler.extract_task_ptr(ptr, list(spec_sections.values()), stack=stack)
            types = task_ptr.get(stack, {}).get("types", {})
            if not types:
                return ""
            lines = ["PTR COMPILED TYPES (grounded in current codebase — use these, do not invent):"]
            for name, info in list(types.items())[:20]:
                props = list(info.get("properties", {}).keys())[:4] if isinstance(info, dict) else []
                prop_str = f" props=[{', '.join(props)}]" if props else ""
                lines.append(f"  {name}{prop_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"PTR: unavailable ({e})"

    def _build_skeleton_block(self, output_file: str, stack: str) -> str:
        """ADR-036 §3: Inject EA-produced skeleton for IMPLEMENTATION tasks.
        Skeleton files live in src/{service}/skeleton/. Provides type contracts
        so LLM fills bodies only — never invents class names or method signatures."""
        skeleton_dirs: dict[str, str] = {
            "constitutional-engine": "src/constitutional-engine/skeleton",
            "business-platform": "src/business-platform/skeleton",
            "professional-runtime": "src/professional-runtime/skeleton",
            "ai-runtime": "src/ai-runtime/skeleton",
            "billing-engine": "src/billing-engine/skeleton",
        }
        # Only inject skeleton for src/ implementation files — not tests
        if not (output_file or "").startswith("src/"):
            return ""
        # Match output_file to a service
        service_dir = None
        for service, skel_dir in skeleton_dirs.items():
            if service in (output_file or ""):
                service_dir = self._root / skel_dir
                break
        if not service_dir or not service_dir.exists():
            return ""
        ext = ".cs" if stack == "dotnet" else ".py"
        lines = [
            "EA SKELETON (ADR-036): These are the type contracts. "
            "DO NOT change class names, method signatures, or field types. "
            "Your task is to fill method bodies only. "
            "If a change to the interface is needed, raise SPEC_GAP — do not modify skeleton.",
            ""
        ]
        for skel_file in sorted(service_dir.glob(f"*{ext}")):
            lines.append(f"# --- {skel_file.name} ---")
            lines.append(skel_file.read_text()[:2000])  # cap per file to stay within context
        return "\n".join(lines) if len(lines) > 2 else ""

    def _build_using_map_block(self, output_file: str, constitutional_check: str, stack: str) -> str:
        """§7.3: USING_MAP structural injection — filtered by ProjectDependencyMap."""
        if not self._assembler or stack != "dotnet":
            return ""
        try:
            using_map = self._assembler.build_using_map()
            if not using_map:
                return ""

            # Filter using_map to only types reachable from the target project
            try:
                from project_dependency_map import find_csproj_for_file, filter_using_map as _pdm_filter
                csproj = find_csproj_for_file(output_file, self._root)
                if csproj:
                    using_map = _pdm_filter(using_map, csproj)
            except Exception:
                pass  # non-blocking — degrade to unfiltered map

            # Find types mentioned in the check or output file name
            scan_text = constitutional_check + " " + output_file
            mentioned = set(_RE_CAPITAL_WORDS.findall(scan_text))
            relevant = {cls: ns for cls, ns in using_map.items() if cls in mentioned}
            if not relevant:
                return ""
            lines = ["USING_MAP — add using directive for every type in this list that you reference:"]
            for cls, ns in sorted(relevant.items()):
                lines.append(f"  {cls} → using {ns};")
            return "\n".join(lines)
        except Exception as e:
            return ""

    def _build_spec_block(self, spec_sections: dict[str, str]) -> str:
        """§7.1 [6]: Load spec sections from Work Contract only."""
        parts = [f"SPECIFICATION CONTEXT:"]
        for file_path, section in spec_sections.items():
            full = self._root / file_path
            if not full.exists():
                parts.append(f"\n## {file_path} ({section})\n[file not found]")
                continue
            content = self._read_cached(full)
            # Truncate at structural boundary (heading) to max 3,000 chars
            if len(content) > 3000:
                lines = content.splitlines()
                truncated = []
                chars = 0
                for line in lines:
                    if chars + len(line) > 3000 and line.startswith("#"):
                        break
                    truncated.append(line)
                    chars += len(line) + 1
                content = "\n".join(truncated)
            parts.append(f"\n## {file_path} ({section})\n{content}")
        return "\n".join(parts)

    def _build_prior_block(self, prior_output_files: list[str]) -> str:
        """§7.4: Prior task compiled output injection."""
        if not prior_output_files:
            return ""
        lines = ["PRIOR TASK COMPILED OUTPUT (read from sprint branch — signatures are authoritative):"]
        found = False
        for file_path in prior_output_files:
            full = self._root / file_path
            if not full.exists():
                # Not on disk (main branch) — check frozen registry
                if file_path in self._frozen:
                    sigs = self._frozen[file_path]
                    ctors = sigs.get("public_constructors", [])
                    class_name = Path(file_path).stem
                    lines.append(f"\n  {class_name} (from frozen registry):")
                    for ctor in ctors[:2]:
                        ctor_clean = _RE_WHITESPACE.sub(' ', ctor).strip()
                        lines.append(f"    constructor: {class_name}({ctor_clean})")
                    found = True
                continue
            content = self._read_cached(full)
            sigs = self._extract_public_signatures(content)
            class_name = Path(file_path).stem
            ctors = sigs.get("public_constructors", [])
            if ctors:
                lines.append(f"\n  {class_name} — {sigs.get('namespace', '')}:")
                for ctor in ctors[:2]:
                    ctor_clean = _RE_WHITESPACE.sub(' ', ctor).strip()
                    lines.append(f"    constructor: {class_name}({ctor_clean})")
                lines.append(
                    f"    ⛔ Use this exact constructor — all positional, this order. "
                    "NullLogger<T>.Instance for logger params."
                )
                found = True
        if not found:
            return ""
        return "\n".join(lines)

    def _build_conftest_block(self, output_file: str) -> str:
        """Inject conftest.py from the target test directory as an authoritative reference.
        The LLM must derive all import paths from the sys.path.insert() calls it contains."""
        if not (output_file.startswith("tests/") or "/tests/" in output_file):
            return ""
        conftest = (self._root / output_file).parent / "conftest.py"
        if not conftest.exists():
            return ""
        content = self._read_cached(conftest)
        if not content.strip():
            return ""
        rel = str(conftest.relative_to(self._root))
        return (
            f"CONFTEST ({rel}) — authoritative source for test sys.path and shared fixtures.\n"
            f"Derive ALL import statements from the sys.path.insert() calls below. "
            f"Never use dotted paths that mirror the directory tree (e.g. "
            f"'from src.service_name.*') — use the flat names the conftest makes importable.\n\n"
            f"```python\n{content}\n```"
        )

    def _build_existing_file_block(self, output_file: str) -> str:
        """If the output file already exists on disk, inject its current content.
        This prevents the LLM from generating a replacement instead of an extension.
        Capped at 6,000 chars to stay within budget."""
        full = self._root / output_file
        if not full.exists():
            return ""
        content = self._read_cached(full)
        if not content.strip():
            return ""
        cap = 6000
        truncated = content[:cap]
        suffix = f"\n... [truncated at {cap} chars — full file is longer] ..." if len(content) > cap else ""
        return (
            f"EXISTING FILE CONTENT — THIS FILE ALREADY EXISTS ON THE SPRINT BRANCH.\n"
            f"⛔ DO NOT regenerate this file from scratch.\n"
            f"⛔ DO NOT remove any existing methods, classes, or using directives.\n"
            f"ONLY add or modify what the TASK REQUIREMENTS specify. "
            f"Output the COMPLETE file including all existing content plus your additions.\n\n"
            f"Current content of {output_file}:\n"
            f"```\n{truncated}{suffix}\n```"
        )

    def _build_task_block(
        self, task_id: str, output_file: str, constitutional_check: str,
        file_exists: bool = False
    ) -> str:
        action = "EXTEND" if file_exists else "Generate"
        note = " (EXISTING FILE — see EXISTING_FILE slot above)" if file_exists else ""
        return (
            f"TASK: {task_id}\n"
            f"{action} ONLY this file: {output_file}{note}\n"
            f"Do NOT generate any other file.\n\n"
            f"TASK-SPECIFIC REQUIREMENTS:\n{constitutional_check}"
        )

    def _build_format_block(self, output_file: str, preamble: list[str]) -> str:
        preamble_preview = "\n".join(preamble[:4]) if preamble else ""
        return (
            f"OUTPUT FORMAT:\n"
            f"Wrap the complete file in:\n"
            f"<file path=\"{output_file}\">\n"
            f"{preamble_preview}\n"
            f"... your code here ...\n"
            f"</file>\n\n"
            f"The file ALREADY starts with the lines shown in MANDATORY FILE HEADER above. "
            f"Start your output with those exact lines, then continue."
        )

    # ── Private: utilities ─────────────────────────────────────────────────────

    def _extract_public_signatures(self, content: str) -> dict:
        """Extract namespace, constructors, methods, properties, enum values from .cs source."""
        ns_m = _RE_NAMESPACE.search(content)
        namespace = ns_m.group(1) if ns_m else ""

        # Multi-line constructor: capture from opening paren to closing paren
        ctors: list[str] = []
        for m in re.finditer(
            r'public\s+\w+\s*\(\s*((?:[^()]*|\([^()]*\))*)\s*\)',
            content, re.DOTALL
        ):
            param_block = _RE_WHITESPACE.sub(' ', m.group(1)).strip()
            if param_block and len(param_block) > 2:
                ctors.append(param_block)

        # Methods
        methods = re.findall(
            r'public\s+(?:override\s+)?(?:async\s+)?(?:static\s+)?[\w<>?\[\]]+\s+(\w+)\s*\(',
            content
        )
        # Filter out constructors (same name as class)
        class_names = _RE_CLASS_NAMES.findall(content)
        methods = [m for m in methods if m not in class_names]

        # Properties
        properties = re.findall(
            r'public\s+(?:override\s+)?(?:static\s+)?[\w<>?\[\]]+\s+(\w+)\s*\{',
            content
        )

        # Enum values — captures public enum X { A, B, C } → {"X": ["A", "B", "C"]}
        # Critical for retry advisor: eliminates CS1503 string→EnumType pattern
        enum_values: dict[str, list[str]] = {}
        for m in re.finditer(
            r'public\s+enum\s+(\w+)\s*\{([^}]+)\}',
            content, re.DOTALL
        ):
            enum_name = m.group(1)
            raw_values = m.group(2)
            # Strip comments, parse comma-separated identifiers
            values = [
                v.strip().split('=')[0].strip().split('//')[0].strip()
                for v in raw_values.split(',')
                if v.strip() and not v.strip().startswith('//')
            ]
            values = [v for v in values if re.match(r'^\w+$', v)]
            if values:
                enum_values[enum_name] = values[:20]

        return {
            "namespace": namespace,
            "public_constructors": ctors[:3],
            "public_methods": methods[:8],
            "public_properties": properties[:8],
            "enum_values": enum_values,
        }

    def _resolve_required_usings(
        self, output_file: str, constitutional_check: str, stack: str
    ) -> list[str]:
        """
        §7.5: Resolve required using directives for the preamble.
        Combines: explicit mentions in constitutional_check + USING_MAP + stack base usings.
        """
        if stack != "dotnet":
            return []

        usings: set[str] = set()

        # Extract explicit using directives from constitutional_check
        for m in re.finditer(r'using\s+([\w.]+)\s*;', constitutional_check):
            usings.add(f"using {m.group(1)};")

        # Resolve type names mentioned in constitutional_check via USING_MAP
        # filtered through ProjectDependencyMap to only include reachable types
        if self._assembler:
            try:
                using_map = self._assembler.build_using_map()
                # Filter to only reachable namespaces for this project
                try:
                    from project_dependency_map import find_csproj_for_file, filter_using_map as _pdm_filter
                    csproj = find_csproj_for_file(output_file, self._root)
                    if csproj:
                        using_map = _pdm_filter(using_map, csproj)
                except Exception:
                    pass  # non-blocking
                mentioned = set(_RE_CAPITAL_WORDS.findall(constitutional_check))
                for cls in mentioned:
                    if cls in using_map:
                        usings.add(f"using {using_map[cls]};")
            except Exception as _um_e:
                print(f"  [CB] using_map lookup skipped ({type(_um_e).__name__}: {_um_e}).")

        # Frozen artifact namespaces for types that appear in check
        for file_path, sigs in self._frozen.items():
            ns = sigs.get("namespace", "")
            class_name = Path(file_path).stem
            if class_name in constitutional_check and ns:
                usings.add(f"using {ns};")

        # Sort: System first, then alphabetically
        sorted_usings = sorted(usings, key=lambda u: (not u.startswith("using System"), u))
        return sorted_usings

    def _extract_claims_from_check(self, constitutional_check: str) -> str:
        """Extract C-NNN references from constitutional check."""
        claims = _RE_CLAIMS.findall(constitutional_check)
        if not claims:
            return "C-059, C-076, C-082"
        return ", ".join(sorted(set(claims))[:5])

    def _is_relevant_frozen(
        self, frozen_file: str, output_file: str, prior_files: list[str]
    ) -> bool:
        """Determine if a frozen artifact is relevant to the current output file."""
        class_name = Path(frozen_file).stem
        # Relevant if: the class name appears in the output file name or path
        if class_name.lower() in output_file.lower():
            return True
        # Relevant if: it's in prior_files
        if frozen_file in prior_files:
            return True
        # Relevant if: it's a service class (broadly useful)
        if "Service" in frozen_file or "Context" in frozen_file:
            return True
        # Relevant if: FakeServerCallContext (always needed in tests)
        if "FakeServerCallContext" in frozen_file and "Tests" in output_file:
            return True
        return False

    # ── Private: infrastructure ───────────────────────────────────────────────

    def _read_cached(self, path: Path) -> str:
        """P3: Read file with mtime-keyed cache. Avoids re-reading unchanged files
        across the 3-attempt retry loop (spec files, prior outputs, frozen registry)."""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""
        key = (str(path), mtime)
        if key not in self._file_cache:
            self._file_cache[key] = path.read_text(encoding="utf-8", errors="replace")
        return self._file_cache[key]

    def _get_ptr_assembler(self):
        """Get PTR assembler, gracefully degrading if unavailable."""
        try:
            import sys
            scripts_path = str(self._root / "scripts")
            if scripts_path not in sys.path:
                sys.path.insert(0, scripts_path)
            from ptr_assembler import PTR2Assembler
            return PTR2Assembler(self._root)
        except Exception as _ptr_e:
            print(f"  [CB] PTR2Assembler unavailable ({type(_ptr_e).__name__}: {_ptr_e})")
            return None

    def _load_frozen_registry(self) -> dict:
        # P2 Fix 2 + P3 fix: Load current sprint frozen registry.
        # Cross-sprint archives loaded lazily and cached to avoid repeated disk reads.
        current = {}
        if self._frozen_registry_path.exists():
            try:
                current = json.loads(self._frozen_registry_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  ContextBuilder: frozen registry read failed ({type(e).__name__}: {e})")

        # Cross-sprint: merge but cache with module-level TTL to avoid N reads on N ContextBuilder()s
        cross_sprint_dir = self._frozen_registry_path.parent / "cross-sprint-context"
        if cross_sprint_dir.exists():
            # Module-level cache: {dir_path: (mtime, merged_dict)}
            _cache_key = str(cross_sprint_dir)
            _cross_cache = getattr(ContextBuilder, "_cross_sprint_cache", {})
            cached_mtime = _cross_cache.get(_cache_key, (0, {}))[0]
            try:
                dir_mtime = cross_sprint_dir.stat().st_mtime
            except OSError:
                dir_mtime = 0

            if dir_mtime != cached_mtime:
                # Cache miss — read all archives once
                merged: dict = {}
                for archive_file in sorted(cross_sprint_dir.glob("*-frozen-artifacts.json")):
                    try:
                        prior = json.loads(archive_file.read_text(encoding="utf-8"))
                        for k, v in prior.items():
                            merged.setdefault(k, {**v, "cross_sprint": True})
                    except Exception as e:
                        print(f"  ContextBuilder: cross-sprint archive read failed ({archive_file.name}: {e})")
                _cross_cache[_cache_key] = (dir_mtime, merged)
                ContextBuilder._cross_sprint_cache = _cross_cache

            _, cross_data = _cross_cache.get(_cache_key, (0, {}))
            for k, v in cross_data.items():
                if k not in current:
                    current[k] = v

        return current

    def _save_frozen_registry(self) -> None:
        self._frozen_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._frozen_registry_path.write_text(
            json.dumps(self._frozen, indent=2), encoding="utf-8"
        )
