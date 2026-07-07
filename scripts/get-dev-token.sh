#!/usr/bin/env bash
# get-dev-token.sh — Get a Keycloak JWT for local development testing
# Usage: ./scripts/get-dev-token.sh [--full] [--tenant-id UUID]
#
# Without --full: prints only the access_token (ready to use in Authorization header)
# With --full:    prints the full JSON response (includes token_type, expires_in, etc.)
#
# Requires: curl, python3, .env file with DEV_TEST_USER and DEV_TEST_PASSWORD

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env
if [[ -f "$REPO_ROOT/.env" ]]; then
    # shellcheck disable=SC1091
    set -o allexport
    source "$REPO_ROOT/.env"
    set +o allexport
else
    echo "ERROR: .env not found. Run: cp .env.example .env && edit .env" >&2
    exit 1
fi

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8443}"
REALM="waooaw"
CLIENT_ID="waooaw-dev-client"
USER="${DEV_TEST_USER:-dev@waooaw.local}"
PASS="${DEV_TEST_PASSWORD:?DEV_TEST_PASSWORD not set in .env}"

FULL_OUTPUT=false
for arg in "$@"; do
    case $arg in
        --full) FULL_OUTPUT=true ;;
    esac
done

RESPONSE=$(curl -sf -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$USER" \
    -d "password=$PASS" \
    2>/dev/null) || {
    echo "ERROR: Failed to get token. Is Keycloak running? (docker compose up keycloak)" >&2
    exit 1
}

if $FULL_OUTPUT; then
    echo "$RESPONSE" | python3 -m json.tool
else
    echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
fi
