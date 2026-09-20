#!/bin/sh
set -eu

python scripts/scan-traceability.py --changed-only
python scripts/scan-traceability.py --amended-claims
python scripts/scan-traceability.py --report test-results/traceability-report.json || true