#!/bin/sh
set -eu

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
