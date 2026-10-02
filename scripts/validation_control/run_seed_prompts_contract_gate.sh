#!/bin/sh
set -eu

pytest tests/validation_control/test_seed_prompts_contract.py \
    -v --tb=short \
    --junitxml=test-results/seed-prompts-contract.xml
