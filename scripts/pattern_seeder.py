#!/usr/bin/env python3
"""
pattern_seeder.py — Canonical Pattern Library Seeder

# Implements: architecture/reference/ptr/architecture.md §6 Canonical Pattern Library
# Constitutional basis: C-069 (Platform Self-Improvement), C-059 (Traceability)
# GOAL-003 Phase C

After each successful sprint merge, this script:
  1. Scans the newly merged source files
  2. Extracts canonical patterns (DI registration, test structure, error handling,
     constitutional annotation conventions)
  3. Writes them to architecture/reference/ptr/canonical-patterns/{stack}/

Canonical patterns are initially CANDIDATE status.
Constitutional Analyst review promotes them to CANONICAL.
CANONICAL patterns are injected into PTR 2.0 Layer 4 for future sprints.

Run after a sprint merge:
  python3 scripts/pattern_seeder.py WC-012
  python3 scripts/pattern_seeder.py --last-merge
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
PATTERNS_ROOT = REPO_ROOT / "architecture" / "reference" / "ptr" / "canonical-patterns"


@dataclass
class CanonicalPattern:
    pattern_id: str
    stack: str
    category: str           # di-registration | test-structure | error-handling | annotations | naming
    status: str = "CANDIDATE"  # CANDIDATE | CANONICAL | REJECTED
    description: str = ""
    pattern_text: str = ""
    source_file: str = ""
    source_goal: str = ""
    confidence_weight: float = 0.5  # 0.5 until CA reviews → 1.0 or 0.0
    created_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_md_block(self) -> str:
        return (
            f"### {self.pattern_id}\n\n"
            f"**Status:** {self.status}  \n"
            f"**Category:** {self.category}  \n"
            f"**Confidence:** {self.confidence_weight}  \n"
            f"**Source:** `{self.source_file}` (from {self.source_goal})  \n"
            f"**Created:** {self.created_at}\n\n"
            f"{self.description}\n\n"
            f"```\n{self.pattern_text}\n```\n"
        )


# ── Pattern extractors per stack ──────────────────────────────────────────────

def _extract_dotnet_patterns(cs_content: str, file_path: str, sprint: str) -> list[CanonicalPattern]:
    """Extract canonical .NET/C# patterns from merged source files."""
    patterns = []
    file_name = Path(file_path).name

    # Pattern 1: DI registration extension method
    di_match = re.search(
        r'public static IServiceCollection (Add\w+Services)\s*\([^)]*\)',
        cs_content
    )
    if di_match:
        method_name = di_match.group(1)
        # Extract the full method body if available
        body_match = re.search(
            rf'{re.escape(method_name)}\s*\([^)]*\)[^{{]*\{{([^}}]+)\}}',
            cs_content, re.DOTALL
        )
        body = body_match.group(1).strip()[:400] if body_match else ""
        patterns.append(CanonicalPattern(
            pattern_id=f"DOTNET-DI-{sprint.replace('-', '')}-{method_name}",
            stack="dotnet",
            category="di-registration",
            description=(
                f"DI registration pattern from {sprint}: services registered via static "
                f"extension method '{method_name}(IServiceCollection)'. "
                f"Follow this pattern for all future .NET services."
            ),
            pattern_text=(
                f"// In Program.cs or startup:\n"
                f"builder.Services.{method_name}(builder.Configuration);\n\n"
                f"// Implementation pattern:\n"
                f"public static IServiceCollection {method_name}(this IServiceCollection services, ...)\n"
                f"{{\n{body}\n    return services;\n}}"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    # Pattern 2: gRPC service method pattern
    grpc_method = re.search(
        r'public override async Task<(\w+Response)> (\w+)\s*\(\s*(\w+Request)',
        cs_content
    )
    if grpc_method:
        resp_type = grpc_method.group(1)
        method_name = grpc_method.group(2)
        req_type = grpc_method.group(3)
        patterns.append(CanonicalPattern(
            pattern_id=f"DOTNET-GRPC-{sprint.replace('-', '')}-{method_name}",
            stack="dotnet",
            category="grpc-service",
            description=f"gRPC service method pattern from {sprint}: async override with proper cancellation.",
            pattern_text=(
                f"public override async Task<{resp_type}> {method_name}(\n"
                f"    {req_type} request, ServerCallContext context)\n"
                f"{{\n"
                f"    // 1. Validate (CE.ValidateAction if needed)\n"
                f"    // 2. Record evidence BEFORE returning (C-023)\n"
                f"    // 3. Execute business logic\n"
                f"    return new {resp_type} {{ /* ... */ }};\n"
                f"}}"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    # Pattern 3: Constitutional annotation usage
    if "// Implements:" in cs_content and "// Constitutional basis:" in cs_content:
        patterns.append(CanonicalPattern(
            pattern_id=f"DOTNET-ANNO-{sprint.replace('-', '')}-{file_name}",
            stack="dotnet",
            category="annotations",
            description=f"Constitutional annotation pattern confirmed in {sprint} (C-059 + C-073).",
            pattern_text=(
                "// Implements: architecture/reference/components/{service}.md §{Section}\n"
                "// Constitutional basis: C-NNN ({Claim Name})"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    # Pattern 4: Unit test class structure
    if "[Fact]" in cs_content or "[Theory]" in cs_content:
        patterns.append(CanonicalPattern(
            pattern_id=f"DOTNET-TEST-{sprint.replace('-', '')}-{file_name}",
            stack="dotnet",
            category="test-structure",
            description=f"xUnit test structure from {sprint}: AAA pattern with FluentAssertions.",
            pattern_text=(
                "[Fact]\n"
                "public async Task Method_Scenario_ExpectedResult()\n"
                "{\n"
                "    // Arrange\n"
                "    var sut = new SomeClass(Mock.Of<IDep>());\n\n"
                "    // Act\n"
                "    var result = await sut.DoSomethingAsync();\n\n"
                "    // Assert\n"
                "    result.Should().NotBeNull();\n"
                "    result.SomeProperty.Should().Be(expectedValue);\n"
                "}"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    return patterns


def _extract_python_patterns(py_content: str, file_path: str, sprint: str) -> list[CanonicalPattern]:
    """Extract canonical Python patterns from merged source files."""
    patterns = []
    file_name = Path(file_path).name

    # Pattern: FastAPI router structure
    if "APIRouter" in py_content or "@router." in py_content:
        patterns.append(CanonicalPattern(
            pattern_id=f"PYTHON-FASTAPI-{sprint.replace('-', '')}-{file_name}",
            stack="python",
            category="fastapi-router",
            description=f"FastAPI router pattern from {sprint}: async routes with dependency injection.",
            pattern_text=(
                "from fastapi import APIRouter, Depends\n\n"
                "router = APIRouter(prefix='/endpoint', tags=['tag'])\n\n"
                "@router.get('/{id}')\n"
                "async def get_item(id: str, db: AsyncSession = Depends(get_db)):\n"
                "    # Implementation\n"
                "    pass"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    # Pattern: file header convention
    if "# Implements:" in py_content and "# Constitutional basis:" in py_content:
        patterns.append(CanonicalPattern(
            pattern_id=f"PYTHON-ANNO-{sprint.replace('-', '')}-{file_name}",
            stack="python",
            category="annotations",
            description=f"Python file header convention from {sprint} (C-059).",
            pattern_text=(
                "# Implements: architecture/reference/components/{service}.md §{Section}\n"
                "# Constitutional basis: C-NNN ({Claim Name})"
            ),
            source_file=file_path,
            source_goal=f"GOAL-{sprint.replace('-', '')}",
        ))

    return patterns


# ── Pattern Library writer ────────────────────────────────────────────────────

def _write_patterns(patterns: list[CanonicalPattern], sprint: str) -> int:
    """Write extracted patterns to the Canonical Pattern Library."""
    if not patterns:
        return 0

    by_stack: dict[str, list[CanonicalPattern]] = {}
    for p in patterns:
        by_stack.setdefault(p.stack, []).append(p)

    written = 0
    for stack, stack_patterns in by_stack.items():
        stack_dir = PATTERNS_ROOT / stack
        stack_dir.mkdir(parents=True, exist_ok=True)

        out_file = stack_dir / f"{sprint.lower()}-patterns.md"
        content_lines = [
            f"# Canonical Patterns — {sprint} ({stack})\n",
            f"**Status:** CANDIDATE — awaiting Constitutional Analyst review  \n",
            f"**Source sprint:** {sprint}  \n",
            f"**Extracted:** {date.today().isoformat()}  \n",
            f"**Confidence:** 0.5 (CANDIDATE) — promoted to 1.0 after CA review\n",
            f"\n---\n",
        ]
        for p in stack_patterns:
            content_lines.append(p.to_md_block())
            content_lines.append("\n---\n")

        out_file.write_text("\n".join(content_lines), encoding="utf-8")
        print(f"  ✓ Wrote {len(stack_patterns)} patterns → {out_file.relative_to(REPO_ROOT)}")
        written += len(stack_patterns)

    return written


# ── Sprint file scanner ───────────────────────────────────────────────────────

def seed_from_sprint(sprint_id: str) -> int:
    """Extract and seed patterns from a specific sprint's merged files."""
    print(f"\n{'='*70}")
    print(f"  PATTERN SEEDER: {sprint_id}")
    print(f"{'='*70}")

    # Find files modified in this sprint (from git log)
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--oneline", "-20", "--", "src/*", "tests/*"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        all_files = [
            line.strip() for line in result.stdout.splitlines()
            if line.strip() and not line.startswith(tuple("0123456789abcdef"))
            and (line.endswith(".cs") or line.endswith(".py"))
        ]
    except Exception:
        # Fallback: scan src/ directly
        all_files = (
            [str(f.relative_to(REPO_ROOT)) for f in (REPO_ROOT / "src").rglob("*.cs")] +
            [str(f.relative_to(REPO_ROOT)) for f in (REPO_ROOT / "src").rglob("*.py")]
        )

    if not all_files:
        print("  No source files found to extract patterns from")
        return 0

    all_patterns: list[CanonicalPattern] = []
    seen_ids: set[str] = set()

    for file_path_str in all_files[:50]:  # cap at 50 files
        file_path = REPO_ROOT / file_path_str
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if file_path.suffix == ".cs":
            new_patterns = _extract_dotnet_patterns(content, file_path_str, sprint_id)
        elif file_path.suffix == ".py":
            new_patterns = _extract_python_patterns(content, file_path_str, sprint_id)
        else:
            continue

        for p in new_patterns:
            if p.pattern_id not in seen_ids:
                all_patterns.append(p)
                seen_ids.add(p.pattern_id)

    print(f"  Scanned {len(all_files)} files → extracted {len(all_patterns)} patterns")
    written = _write_patterns(all_patterns, sprint_id)
    print(f"  Seeded {written} patterns to Canonical Pattern Library (CANDIDATE status)")
    print(f"  Next: Constitutional Analyst review → promote to CANONICAL")
    return written


def main() -> int:
    args = sys.argv[1:]
    if not args:
        # Auto-detect from latest sprint state
        try:
            content = (REPO_ROOT / "constitution" / "PROJECT_STATE.md").read_text()
            m = re.search(r'current_sprint[:\s]+["\']?(WC-\d+)', content)
            sprint = m.group(1) if m else "WC-012"
        except Exception:
            sprint = "WC-012"
        print(f"  Auto-detected sprint: {sprint}")
    elif args[0] == "--last-merge":
        # Extract from last git merge commit message
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        m = re.search(r'WC-\d+', result.stdout)
        sprint = m.group(0) if m else "WC-012"
    else:
        sprint = args[0].upper()

    count = seed_from_sprint(sprint)
    return 0 if count >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
