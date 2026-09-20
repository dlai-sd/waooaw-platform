#!/bin/sh
set -eu

pytest tests/integration/test_pr_ce_*.py tests/integration/test_air_pse_*.py \
    -v --tb=short \
    --junit-xml=test-results/service-integration.xml
