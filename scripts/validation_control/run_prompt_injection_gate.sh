#!/bin/sh
set -eu

pytest tests/ai-runtime/test_injection_guard.py \
    -v --tb=short \
    --junit-xml=test-results/prompt-injection.xml
