# Implements: scripts/runner/constants.py
# constitutional_basis: C-059 (Evidence First), C-077 (Cost Ceiling — write boundary)
# ib_item: IB-009
"""
Repository-level path constants and ADR-030 write-boundary enforcement.
All runner modules import from here — single source of truth for paths.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
EVIDENCE_LOG = REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"

# ADR-030: File write boundary enforcement (C-059 + C-065)
# LLM-generated files may only land in these subtrees.
ALLOWED_WRITE_ROOTS: list[str] = [
    "src/",
    "tests/",
    "infrastructure/postgres/",
    "infrastructure/keycloak/",
    "logs/",
]
