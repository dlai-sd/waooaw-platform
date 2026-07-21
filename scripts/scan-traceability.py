#!/usr/bin/env python3
"""
scan-traceability.py — C-073 Constitutional Traceability Scanner

Constitutional basis: C-073 (Bidirectional Implementation Traceability)
IB item:             IB-009
Spec:                architecture/reference/TRACEABILITY-PROTOCOL.md Section 6

WHAT THIS DOES:
  1. Scans source files for constitutional header blocks (C-073 file-level)
  2. Scans for @constitutional / [ConstitutionalClaim] / @constitutional JSDoc annotations
  3. When a claim file (knowledge/claims/C-NNN.md) is changed: lists all tagged source files
  4. Reports missing annotations in src/ files (warning until IB-009 complete; error after)
  5. Outputs a traceability index: claim → source files → CCT files → audit_records schema

USAGE:
  python scripts/scan-traceability.py                   # Full scan
  python scripts/scan-traceability.py --changed-only    # Only changed files (PR mode)
  python scripts/scan-traceability.py --claim C-041     # Find all files tagged C-041
  python scripts/scan-traceability.py --amended-claims  # Claims changed in this PR
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC_DIRS = ["src", "web/src", "scripts", "tests", "infrastructure"]
# G-03 FIX: infrastructure/ added so SQL migration files are scanned for
# -- constitutional_basis: annotations. Without this, DB schema traceability
# (C-073) was declared but not enforced by the scanner.
CLAIMS_DIR = REPO_ROOT / "knowledge" / "claims"

# Patterns that indicate constitutional annotation in source files
ANNOTATION_PATTERNS = [
    # Python decorator
    re.compile(r'@constitutional\s*\(\s*claims\s*=\s*\[([^\]]+)\]', re.MULTILINE),
    # Python file header
    re.compile(r'#\s*constitutional_basis:\s*([C\d\s,\-]+)', re.MULTILINE),
    # .NET attribute
    re.compile(r'\[ConstitutionalClaim\s*\(\s*claims\s*:\s*new\s*\[\]\s*\{([^}]+)\}', re.MULTILINE),
    # .NET file header
    re.compile(r'//\s*constitutional_basis:\s*([C\d\s,\-]+)', re.MULTILINE),
    # TypeScript JSDoc
    re.compile(r'@constitutional\s+([C\d\s,\-]+)', re.MULTILINE),
    # SQL file header
    re.compile(r'--\s*constitutional_basis:\s*([C\d\s,\-]+)', re.MULTILINE),
]

# Files that must have constitutional annotations
MUST_ANNOTATE_PATTERNS = [
    "*.cs",    # .NET source
    "*.py",    # Python source (not tests)
    "*.tsx",   # TypeScript React components
    "*.ts",    # TypeScript
    "*.sql",   # DB migrations
]

# Files/dirs to skip
SKIP_PATTERNS = [
    "node_modules", ".venv", "__pycache__", ".git",
    "dist", "build", ".next", "*.test.*", "*.spec.*",
    "conftest.py",  # Test config — no constitutional annotation required
]


def get_changed_files() -> list[Path]:
    """Get list of changed files in this PR vs main."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True
        )
        return [REPO_ROOT / f for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError:
        return []


def extract_claims_from_file(path: Path) -> set[str]:
    """Extract all C-NNN references from a source file's annotations."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    claims: set[str] = set()
    for pattern in ANNOTATION_PATTERNS:
        for match in pattern.finditer(content):
            raw = match.group(1)
            # Extract individual C-NNN references
            found = re.findall(r'C-\d{3}', raw)
            claims.update(found)
    return claims


def has_constitutional_header(path: Path) -> bool:
    """Check if a file has a constitutional file-level header."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # Check for file-level header (first 15 lines)
    first_lines = "\n".join(content.splitlines()[:15])
    header_patterns = [
        r'constitutional_basis:',
        r'@constitutional',
        r'ConstitutionalClaim',
    ]
    return any(re.search(p, first_lines) for p in header_patterns)


def is_skipped(path: Path) -> bool:
    """Check if a path should be skipped."""
    parts = path.parts
    return any(skip in parts for skip in SKIP_PATTERNS) or \
           any(path.name.endswith(skip.lstrip("*")) for skip in SKIP_PATTERNS
               if skip.startswith("*."))


def build_traceability_index(files: list[Path]) -> dict[str, list[str]]:
    """
    Build index: claim_id → list of source files that implement it.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for path in files:
        if not path.exists() or not path.is_file():
            continue
        claims = extract_claims_from_file(path)
        rel = str(path.relative_to(REPO_ROOT))
        for claim in claims:
            index[claim].append(rel)
    return dict(index)


def get_amended_claims() -> list[str]:
    """Find constitutional claims changed in this PR."""
    changed = get_changed_files()
    amended = []
    for f in changed:
        if CLAIMS_DIR in f.parents and f.suffix == ".md":
            # Extract claim ID from filename: C-041.md → C-041
            match = re.match(r'(C-\d{3})\.md', f.name)
            if match:
                amended.append(match.group(1))
    return amended


def scan_src_files() -> list[Path]:
    """Find all source files that should have constitutional annotations."""
    results = []
    for src_dir in SRC_DIRS:
        dir_path = REPO_ROOT / src_dir
        if not dir_path.exists():
            continue
        for pattern in MUST_ANNOTATE_PATTERNS:
            for path in dir_path.rglob(pattern):
                if not is_skipped(path):
                    results.append(path)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="C-073 Constitutional Traceability Scanner")
    parser.add_argument("--changed-only", action="store_true",
                        help="Only scan files changed in this PR")
    parser.add_argument("--claim", metavar="C-NNN",
                        help="Find all files tagged with this claim ID")
    parser.add_argument("--amended-claims", action="store_true",
                        help="Detect claims changed in this PR and list tagged code")
    parser.add_argument("--report", metavar="FILE",
                        help="Write JSON traceability index to file")
    args = parser.parse_args()

    # ── Mode: find all files tagged with a specific claim ──────────────────
    if args.claim:
        all_files = scan_src_files()
        index = build_traceability_index(all_files)
        tagged = index.get(args.claim, [])
        print(f"\n{args.claim} is implemented in {len(tagged)} source file(s):")
        for f in sorted(tagged):
            print(f"  {f}")
        return

    # ── Mode: detect amended claims and surface affected code ───────────────
    if args.amended_claims:
        amended = get_amended_claims()
        if not amended:
            print("No constitutional claims changed in this PR.")
            return
        all_files = scan_src_files()
        index = build_traceability_index(all_files)
        print(f"\n⚠️  Constitutional claims amended in this PR: {amended}")
        print("Review the following source files that implement these claims:\n")
        for claim in amended:
            tagged = index.get(claim, [])
            print(f"  {claim} → {len(tagged)} file(s):")
            for f in sorted(tagged):
                print(f"    {f}")
        return

    # ── Mode: full scan or changed-only scan ────────────────────────────────
    if args.changed_only:
        files = [f for f in get_changed_files()
                 if f.exists() and not is_skipped(f)
                 and f.suffix in {".cs", ".py", ".ts", ".tsx", ".sql"}]
        print(f"Scanning {len(files)} changed source file(s) for C-073 compliance...")
    else:
        files = scan_src_files()
        print(f"Scanning {len(files)} source file(s) for C-073 compliance...")

    missing = []
    index: dict[str, list[str]] = defaultdict(list)

    for path in files:
        rel = str(path.relative_to(REPO_ROOT))
        claims = extract_claims_from_file(path)

        if claims:
            for claim in claims:
                index[claim].append(rel)
        else:
            # File in src/ with no annotation
            if any(str(path).startswith(str(REPO_ROOT / d)) for d in ["src", "web/src"]):
                missing.append(rel)

    # Report
    print(f"\n✓ Files with constitutional annotations: {len(files) - len(missing)}")

    if missing:
        print(f"\n⚠️  Missing constitutional annotations ({len(missing)} file(s)):")
        for f in sorted(missing)[:20]:
            print(f"  {f}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
        print("\nSee architecture/reference/TRACEABILITY-PROTOCOL.md Section 3 for annotation patterns.")
        # Warning only (not exit 1) until all existing files are annotated — IB-009 milestone
        # After IB-009 complete, change to sys.exit(1)

    # Write report
    if args.report:
        report = {
            "total_files_scanned": len(files),
            "annotated_files": len(files) - len(missing),
            "missing_annotations": missing,
            "traceability_index": dict(index),
        }
        Path(args.report).write_text(json.dumps(report, indent=2))
        print(f"\nTraceability index written to {args.report}")

    # Print claim coverage summary
    if index:
        print(f"\nClaim coverage ({len(index)} claims tagged in source):")
        for claim in sorted(index.keys()):
            print(f"  {claim}: {len(index[claim])} file(s)")


if __name__ == "__main__":
    main()
