#!/bin/sh
set -eu

sh scripts/validation_control/run_postgres_migrations.sh
pytest tests/integration/test_multi_tenant_*.py \
    -v --tb=short \
    --junit-xml=test-results/multi-tenant.xml
