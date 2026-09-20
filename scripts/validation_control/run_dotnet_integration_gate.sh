#!/bin/sh
set -eu

dotnet test tests/integration/constitutional-engine \
    --artifacts-path /tmp/artifacts/integration-constitutional-engine \
    --logger "junit;LogFileName=test-results/ce-integration.xml"
