#!/bin/sh
set -eu

artifact_directory=/tmp/artifacts/integration-multi-tenant
package_directory=/tmp/nuget-packages/integration-multi-tenant

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
    --filter 'FullyQualifiedName~CCT_MT01_TenantIsolationTests|FullyQualifiedName~TenantDbConnectionInterceptorPostgresTests' \
    --logger 'trx;LogFileName=multi-tenant.trx' \
    --results-directory /workspace/test-results
