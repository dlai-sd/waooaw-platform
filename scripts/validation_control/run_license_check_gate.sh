#!/bin/sh
set -eu

work_dir=/workspace/test-results/license-check-work
rm -rf "$work_dir"
mkdir -p "$work_dir/tmp"
trap 'rm -rf "$work_dir"' EXIT
export TMPDIR="$work_dir/tmp"
export PIP_DISABLE_PIP_VERSION_CHECK=1
python_executable=$(command -v python)

scan_professional_runtime=false
scan_ai_runtime=false
if test -z "${WAOOAW_CHANGED_FILES_FILE:-}"; then
    scan_professional_runtime=true
    scan_ai_runtime=true
elif grep -Eq '^(scripts/validation_control/run_license_check_gate\.sh|validation/engineering-validation\.yaml|architecture/reference/dockerfiles/Dockerfile\.test-runner-python)$' \
    "$WAOOAW_CHANGED_FILES_FILE"; then
    scan_professional_runtime=true
    scan_ai_runtime=true
else
    if grep -Eq '^(src/professional-runtime/(requirements\.txt|Dockerfile)|architecture/reference/dotfiles/requirements-professional-runtime\.txt)$' \
        "$WAOOAW_CHANGED_FILES_FILE"; then
        scan_professional_runtime=true
    fi
    if grep -Eq '^(src/ai-runtime/(requirements\.txt|Dockerfile)|architecture/reference/dotfiles/requirements-ai-runtime\.txt)$' \
        "$WAOOAW_CHANGED_FILES_FILE"; then
        scan_ai_runtime=true
    fi
fi

printf 'license_scope professional-runtime=%s ai-runtime=%s\n' "$scan_professional_runtime" "$scan_ai_runtime"
if test "$scan_professional_runtime" = false && test "$scan_ai_runtime" = false; then
    echo 'License check not applicable: no product dependency inputs changed.'
    exit 0
fi

professional_runtime_install=
ai_runtime_install=
if test "$scan_professional_runtime" = true; then
    mkdir -p "$work_dir/professional-runtime"
    python -m pip install --ignore-installed --no-warn-conflicts --target "$work_dir/professional-runtime" \
        -r src/professional-runtime/requirements.txt -q &
    professional_runtime_install=$!
fi
if test "$scan_ai_runtime" = true; then
    mkdir -p "$work_dir/ai-runtime"
    sed -e '/^--extra-index-url/d' \
        -e 's/torch==2.13.0+cpu/torch==2.13.0/' \
        src/ai-runtime/requirements.txt > "$work_dir/ai-runtime-requirements.txt"
    python -m pip install --ignore-installed --no-warn-conflicts --target "$work_dir/ai-runtime" \
        -r "$work_dir/ai-runtime-requirements.txt" -q &
    ai_runtime_install=$!
fi

professional_runtime_status=0
ai_runtime_status=0
if test -n "$professional_runtime_install"; then
    wait "$professional_runtime_install" || professional_runtime_status=$?
fi
if test -n "$ai_runtime_install"; then
    wait "$ai_runtime_install" || ai_runtime_status=$?
fi
if test "$professional_runtime_status" -ne 0 || test "$ai_runtime_status" -ne 0; then
    printf 'Dependency resolution failed: professional-runtime=%s ai-runtime=%s\n' \
        "$professional_runtime_status" "$ai_runtime_status" >&2
    exit 1
fi

if test "$scan_professional_runtime" = true; then
    printf '#!/bin/sh\nPYTHONPATH=%s exec %s -S "$@"\n' \
        "$work_dir/professional-runtime" "$python_executable" > "$work_dir/professional-runtime-python"
    chmod 0700 "$work_dir/professional-runtime-python"
    pip-licenses --python "$work_dir/professional-runtime-python" --fail-on='GPL;AGPL;LGPL'
fi
if test "$scan_ai_runtime" = true; then
    printf '#!/bin/sh\nPYTHONPATH=%s exec %s -S "$@"\n' \
        "$work_dir/ai-runtime" "$python_executable" > "$work_dir/ai-runtime-python"
    chmod 0700 "$work_dir/ai-runtime-python"
    pip-licenses --python "$work_dir/ai-runtime-python" --fail-on='GPL;AGPL;LGPL'
fi