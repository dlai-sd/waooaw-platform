#!/bin/sh
set -eu

case "${1:-}" in
    python)
        pip-audit -r src/professional-runtime/requirements.txt --strict --cache-dir /tmp/pip-audit-cache
        sed -e '/^--extra-index-url/d' \
            -e 's/torch==2.13.0+cpu/torch==2.13.0/' \
            src/ai-runtime/requirements.txt > /tmp/ai-runtime-audit.txt
        pip-audit -r /tmp/ai-runtime-audit.txt --strict --cache-dir /tmp/pip-audit-cache
        pip-audit -r src/billing-engine/requirements.txt --strict --cache-dir /tmp/pip-audit-cache
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