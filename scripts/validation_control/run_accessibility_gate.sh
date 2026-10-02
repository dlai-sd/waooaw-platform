#!/bin/sh
set -eu

workspace=/workspace
web_copy=/tmp/waooaw-web-accessibility
report_directory="$workspace/test-results/playwright-report"

rm -rf "$web_copy" "$report_directory"
cp -a "$workspace/web" "$web_copy"
ln -s /opt/waooaw-web/node_modules "$web_copy/node_modules"
mkdir -p "$report_directory"

cd "$web_copy"
PLAYWRIGHT_HTML_OPEN=never \
PLAYWRIGHT_HTML_OUTPUT_DIR="$report_directory" \
PLAYWRIGHT_JUNIT_OUTPUT_FILE="$workspace/test-results/accessibility.xml" \
pnpm exec playwright test tests/e2e/f1-acceptance.spec.ts \
    --grep "UX-RESP-01|CCT-UX-A11Y-01|active relationship Stop" \
    --project chromium-expanded \
    --project chromium-compact-360 \
    --reporter=line,junit,html
