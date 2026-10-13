#!/bin/sh
set -eu

artifact_directory=/tmp/artifacts/wc120-dotnet
package_directory=/tmp/nuget-packages/wc120-dotnet

mkdir -p "$artifact_directory" "$package_directory"
cp -a /opt/nuget/packages/. "$package_directory/"
export NUGET_PACKAGES="$package_directory"

exec dotnet test tests/business-platform.Tests/business-platform.Tests.csproj \
    --artifacts-path "$artifact_directory" \
    "$@"
