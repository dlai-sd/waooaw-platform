#!/bin/sh
set -eu

cp -a src/constitutional-engine /tmp/constitutional-engine
cd /tmp/constitutional-engine
dotnet-stryker \
    --threshold-high 80 --threshold-low 75 --break-at 65 \
    --reporter json --output /workspace/test-results/stryker-ce-results