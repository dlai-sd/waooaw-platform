#!/bin/sh
set -eu

pytest tests/scripts/test_seed_prompts.py \
    -v --tb=short \
    --junitxml=test-results/seed-prompts-contract.xml
