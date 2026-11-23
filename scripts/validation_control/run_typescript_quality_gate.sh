#!/bin/sh
set -eu

cd web
biome lint --reporter=github .
biome format .
cd /workspace
cp -a web /tmp/web
rm -rf /tmp/web/node_modules
ln -s /opt/waooaw-web/node_modules /tmp/web/node_modules
cd /tmp/web
tsc --noEmit --incremental false
cd /workspace
if grep -rn "as any\|: any\b" web/src --include="*.ts" --include="*.tsx" \
    --exclude-dir=node_modules | grep -v "// biome-ignore"; then
    echo "C-072 violation: 'any' type found in TypeScript source"
    exit 1
fi
echo "No 'any' types in production TypeScript"
# ADR-054 / WC-158: the journey acceptance harness is type-checked and unit-tested with the built-in Node runner.
rm -rf /tmp/ja
cp -a tests/journey-acceptance /tmp/ja
ln -s /opt/waooaw-web/node_modules /tmp/ja/node_modules
cd /tmp/ja
tsc -p tsconfig.json
node --test --experimental-test-coverage --test-coverage-lines=90 --test-coverage-branches=80 __tests__/*.test.ts
cd /workspace
cd /tmp/web
next build 2>&1 | grep -E "First Load JS|Route" || true