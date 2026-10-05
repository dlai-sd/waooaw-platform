#!/bin/sh
set -eu

scope_environment=/tmp/dotnet-integration-scope.env
python_command=$(command -v python3 || command -v python)
"$python_command" scripts/validation_control/qualification_change_scope.py \
    --gate integration:dotnet \
    --changed-files "${WAOOAW_CHANGED_FILES_FILE:-}" > "$scope_environment"
. "$scope_environment"
if test "$QUALIFICATION_GATE_APPLICABLE" = false; then
    echo 'Dotnet integration not applicable: Business Platform integration inputs did not change.'
    exit 0
fi

artifact_directory=/tmp/artifacts/integration-dotnet
package_directory=/tmp/nuget-packages/integration-dotnet

mkdir -p "$package_directory"
cp -a /opt/nuget/packages/. "$package_directory/"
export NUGET_PACKAGES="$package_directory"

dotnet restore tests/business-platform.Tests/business-platform.Tests.csproj \
    --artifacts-path "$artifact_directory"
dotnet build tests/business-platform.Tests/business-platform.Tests.csproj \
    --no-restore \
    --artifacts-path "$artifact_directory"
dotnet test tests/business-platform.Tests/business-platform.Tests.csproj \
    --no-build \
    --artifacts-path "$artifact_directory" \
    --filter 'FullyQualifiedName~IntegrationTests|FullyQualifiedName~PostgresTests' \
    --logger 'trx;LogFileName=dotnet-integration.trx' \
    --results-directory /workspace/test-results
