#!/bin/sh
set -eu

mkdir -p /tmp/mutation/src /tmp/mutation/tests/unit
cp -a src/ai-runtime /tmp/mutation/src/ai-runtime
cp -a tests/unit/ai-runtime /tmp/mutation/tests/unit/ai-runtime
cd /tmp/mutation/src/ai-runtime
mutmut run --paths-to-mutate=. --tests-dir=../../tests/unit/ai-runtime/
mutmut results
score=$(mutmut results | grep -oE '[0-9]+%' | head -1 | tr -d '%')
if [ "${score:-0}" -lt 60 ]; then
    echo "Mutation score ${score:-0}% < 60% - C-072"
    exit 1
fi