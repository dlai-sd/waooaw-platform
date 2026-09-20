#!/bin/sh
set -eu

violations=0
for pattern in \
    'SetTag.*tenant_id[^_]' \
    'SetTag.*customer_name' \
    'SetTag.*email' \
    'SetTag.*phone' \
    'set_attribute.*tenant_id[^_]' \
    'set_attribute.*customer_name'; do
    matches=$(grep -rn "$pattern" src/ --include="*.cs" --include="*.py" 2>/dev/null || true)
    if [ -n "$matches" ]; then
        echo "OBSERVABILITY SECURITY VIOLATION: raw PII in OTel span tags"
        echo "Pattern: $pattern"
        echo "$matches"
        violations=$((violations + 1))
    fi
done

if [ "$violations" -ne 0 ]; then
    exit 1
fi
echo "No PII in OTel spans"