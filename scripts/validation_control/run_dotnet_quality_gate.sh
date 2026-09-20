#!/bin/sh
set -eu

project=${1:?project path is required}
artifact_name=${2:?artifact name is required}

csharpier check "$project"
dotnet build "$project" \
    --artifacts-path "/tmp/artifacts/$artifact_name" \
    -warnaserror /p:TreatWarningsAsErrors=true
dotnet list "$project" package --vulnerable --include-transitive \
    '-p:BaseIntermediateOutputPath=/tmp/obj/$(MSBuildProjectName)/' \
    2>&1 | grep -i "has the following vulnerable packages" && exit 1 || true