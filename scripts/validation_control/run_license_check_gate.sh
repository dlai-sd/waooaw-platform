#!/bin/sh
set -eu

work_dir=/workspace/test-results/license-check-work
rm -rf "$work_dir"
mkdir -p "$work_dir/env" "$work_dir/tmp"
trap 'rm -rf "$work_dir"' EXIT
export TMPDIR="$work_dir/tmp"

pip install --target "$work_dir/env" -r src/professional-runtime/requirements.txt -q
sed -e '/^--extra-index-url/d' \
    -e 's/torch==2.13.0+cpu/torch==2.13.0/' \
    src/ai-runtime/requirements.txt > "$work_dir/ai-runtime-requirements.txt"
pip install --target "$work_dir/env" -r "$work_dir/ai-runtime-requirements.txt" -q
PYTHONPATH="$work_dir/env" pip-licenses --fail-on='GPL;AGPL;LGPL'