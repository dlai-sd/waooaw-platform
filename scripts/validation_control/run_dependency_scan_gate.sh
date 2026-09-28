#!/bin/sh
set -eu

audit_python_requirements() {
    pip_audit_attempts=${PIP_AUDIT_TRANSIENT_ATTEMPTS:-3}
    pip_audit_delay=${PIP_AUDIT_RETRY_DELAY_SECONDS:-2}
    case "$pip_audit_attempts:$pip_audit_delay" in
        *[!0-9:]* | :* | *:)
            echo "pip-audit retry settings must be non-negative integers" >&2
            return 2
            ;;
    esac
    if [ "$pip_audit_attempts" -lt 1 ]; then
        echo "PIP_AUDIT_TRANSIENT_ATTEMPTS must be at least 1" >&2
        return 2
    fi

    pip_audit_attempt=1
    while [ "$pip_audit_attempt" -le "$pip_audit_attempts" ]; do
        pip_audit_output=$(mktemp)
        if pip-audit -r "$1" --strict --cache-dir /tmp/pip-audit-cache >"$pip_audit_output" 2>&1; then
            cat "$pip_audit_output"
            rm -f "$pip_audit_output"
            return 0
        else
            pip_audit_status=$?
        fi
        cat "$pip_audit_output" >&2
        if [ "$pip_audit_attempt" -ge "$pip_audit_attempts" ] ||
            ! grep -Eqi 'ConnectionResetError|requests\.exceptions\.ConnectionError|urllib3\.exceptions\.(ProtocolError|ReadTimeoutError|ConnectTimeoutError)|Temporary failure in name resolution|NameResolutionError|RemoteDisconnected' "$pip_audit_output"; then
            rm -f "$pip_audit_output"
            return "$pip_audit_status"
        fi
        rm -f "$pip_audit_output"
        echo "pip-audit transient transport failure; retrying ($pip_audit_attempt/$pip_audit_attempts)" >&2
        sleep "$pip_audit_delay"
        pip_audit_attempt=$((pip_audit_attempt + 1))
    done
}

case "${1:-}" in
    python)
        audit_python_requirements src/professional-runtime/requirements.txt
        sed -e '/^--extra-index-url/d' \
            -e 's/torch==2.13.0+cpu/torch==2.13.0/' \
            src/ai-runtime/requirements.txt > /tmp/ai-runtime-audit.txt
        audit_python_requirements /tmp/ai-runtime-audit.txt
        audit_python_requirements src/billing-engine/requirements.txt
        ;;
    dotnet)
        audit_dotnet_project() {
            project_name=$(basename "$1")
            export BaseIntermediateOutputPath="/tmp/dependency-audit/$project_name/obj/"
            dotnet restore "$1" --nologo >/dev/null
            output=$(dotnet list "$1" package --vulnerable --include-transitive 2>&1)
            printf '%s\n' "$output"
            if printf '%s\n' "$output" | grep -qi 'has the following vulnerable packages'; then
                return 1
            fi
        }
        audit_dotnet_project src/constitutional-engine
        audit_dotnet_project src/business-platform
        ;;
    typescript)
        cd /opt/waooaw-web
        pnpm audit --audit-level high
        ;;
    *)
        echo "usage: run_dependency_scan_gate.sh {python|dotnet|typescript}" >&2
        exit 2
        ;;
esac