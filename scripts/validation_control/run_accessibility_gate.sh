#!/bin/sh
set -eu

cp -a web /tmp/web
ln -s /opt/waooaw-web/node_modules /tmp/web/node_modules
cd /tmp/web
playwright test tests/accessibility/ \
    --reporter=html --output=/tmp/playwright-accessibility
