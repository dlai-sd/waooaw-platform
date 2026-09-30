#!/bin/sh
set -eu

result_directory=/workspace/test-results/emergency-stop
artifact_directory=/tmp/artifacts/emergency-stop

rm -rf "$result_directory" "$artifact_directory"
mkdir -p "$result_directory" "$artifact_directory"

pytest tests/constitutional/test_cct_ho_01_emergency_stop_latency.py \
    -v --tb=short \
    --junit-xml="$result_directory/websocket.xml"

dotnet restore tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj \
    --artifacts-path "$artifact_directory"
dotnet build tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj \
    --no-restore -warnaserror \
    --artifacts-path "$artifact_directory"
dotnet test tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj \
    --no-build \
    --artifacts-path "$artifact_directory" \
    --filter "FullyQualifiedName~CCT_HO01_EmergencyStopLatencyTests" \
    --logger "trx;LogFileName=constitutional-engine.trx" \
    --results-directory "$result_directory"