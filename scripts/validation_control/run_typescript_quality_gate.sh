#!/bin/sh
set -eu

cd web
biome lint --reporter=github .
biome format .
cd /workspace
cp -a web /tmp/web
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
cd /tmp/web
next build 2>&1 | grep -E "First Load JS|Route" || true