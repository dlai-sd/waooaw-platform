"""DMA component test import paths."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §19
# Constitutional basis: C-059, C-076, C-080

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/digital-marketing-agent"))
sys.path.insert(0, str(ROOT / "src/agent-adapters"))
sys.path.insert(0, str(ROOT / "src/professional-runtime"))
os.environ.setdefault("DMA_ARTIFACT_DIGEST", "sha256:" + "ab" * 32)
os.environ.setdefault("DMA_ADMISSION_CONTENT_DIGEST", "sha256:" + "cd" * 32)
os.environ.setdefault("PR_SERVICE_JWT_SECRET", "test-service-assertion")
