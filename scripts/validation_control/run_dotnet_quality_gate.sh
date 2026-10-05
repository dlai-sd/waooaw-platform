#!/bin/sh
set -eu

project=${1:?project path is required}
artifact_name=${2:?artifact name is required}

csharpier check "$project"
dotnet build "$project" \
    --artifacts-path "/tmp/artifacts/$artifact_name" \
    -warnaserror /p:TreatWarningsAsErrors=true