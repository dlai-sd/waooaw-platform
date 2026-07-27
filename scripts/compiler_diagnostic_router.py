#!/usr/bin/env python3
"""
compiler_diagnostic_router.py

Family-level compiler diagnostic parsing/routing for autonomous code repair.
This avoids brittle per-error-code handling by normalizing diagnostics first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


FAMILY_SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
FAMILY_NULLABILITY = "NULLABILITY_MISMATCH"
FAMILY_SYMBOL_RESOLUTION = "SYMBOL_RESOLUTION"
FAMILY_INTERFACE_CONTRACT = "INTERFACE_CONTRACT"
FAMILY_ASYNC_FLOW = "ASYNC_FLOW"
FAMILY_REFERENCE_CONFIG = "REFERENCE_CONFIG"
FAMILY_UNKNOWN = "UNKNOWN"


@dataclass
class DiagnosticFact:
    code: str
    message: str
    file_path: str | None = None
    line: int | None = None


def parse_diagnostic_facts(build_error: str) -> list[DiagnosticFact]:
    """Parse C#/MSBuild diagnostic lines into structured facts."""
    facts: list[DiagnosticFact] = []
    if not build_error:
        return facts

    # Typical format:
    # /path/File.cs(52,20): error CS7036: There is no argument given ...
    pattern = re.compile(
        r"(?P<file>[^\n:]+\.(?:cs|csproj|targets|props))"
        r"(?:\((?P<line>\d+)(?:,\d+)?\))?"
        r":\s*(?:error|warning)\s*(?P<code>CS\d+|NU\d+|MSB\d+)"
        r":\s*(?P<msg>[^\n]+)",
        re.IGNORECASE,
    )

    for m in pattern.finditer(build_error):
        line = int(m.group("line")) if m.group("line") else None
        facts.append(
            DiagnosticFact(
                code=m.group("code").upper(),
                message=m.group("msg").strip(),
                file_path=m.group("file").strip(),
                line=line,
            )
        )

    # Fallback parser for lines that include code but not file details.
    if not facts:
        loose = re.compile(r"\b(CS\d+|NU\d+|MSB\d+)\b[:\s-]*(.+)", re.IGNORECASE)
        for line in build_error.splitlines():
            m = loose.search(line)
            if not m:
                continue
            facts.append(DiagnosticFact(code=m.group(1).upper(), message=m.group(2).strip()))

    return facts


def classify_diagnostic_family(facts: list[DiagnosticFact]) -> str:
    """Classify diagnostics into semantic repair families."""
    if not facts:
        return FAMILY_UNKNOWN

    codes = {f.code for f in facts}

    if codes & {"CS7036", "CS1501", "CS1503", "CS1729"}:
        return FAMILY_SIGNATURE_DRIFT

    if codes & {"CS0266", "CS8629", "CS8600", "CS8602", "CS8604", "CS8618", "CS0019"}:
        return FAMILY_NULLABILITY

    if codes & {"CS0246", "CS0103", "CS0117", "CS1061"}:
        return FAMILY_SYMBOL_RESOLUTION

    if codes & {"CS0539", "CS0505", "CS0115", "CS0738"}:
        return FAMILY_INTERFACE_CONTRACT

    if codes & {"CS1998", "CS4014", "CS4032"}:
        return FAMILY_ASYNC_FLOW

    if any(c.startswith("NU") or c.startswith("MSB") for c in codes):
        return FAMILY_REFERENCE_CONFIG

    return FAMILY_UNKNOWN


def summarize_facts(facts: list[DiagnosticFact]) -> str:
    """Compact human-readable diagnostic summary for prompt injection."""
    if not facts:
        return "No diagnostic facts parsed."
    chunks = []
    for f in facts[:6]:
        loc = f"{f.file_path}:{f.line}" if f.file_path and f.line else (f.file_path or "<unknown>")
        chunks.append(f"{f.code} @ {loc} :: {f.message}")
    return " | ".join(chunks)
