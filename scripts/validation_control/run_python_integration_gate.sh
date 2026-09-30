#!/bin/sh
set -eu

pytest \
    tests/professional-runtime/test_paas_runtime.py \
    tests/professional-runtime/test_conversation_execution.py \
    tests/ai-runtime/test_pse_router.py \
    tests/trust-layer/test_ctg.py \
    -v --tb=short \
    --junitxml=test-results/python-service-integration.xml
