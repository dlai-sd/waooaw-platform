#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_directory="$repository_root/.auth-preview"
runtime_environment="$state_directory/runtime.env"
release_manifest="$state_directory/release-manifest.json"
compose_file="$repository_root/docker-compose.auth-preview.yml"
preview_port=${AUTH_PREVIEW_PORT:-3100}
forwarding_domain=${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}

fail() {
  printf 'auth-preview: %s\n' "$1" >&2
  exit 1
}

case ${1:-start} in
  prepare | start) action=${1:-start} ;;
  *) fail "usage: WAOOAW_WEB_IMAGE=<image@sha256:digest> $0 [prepare|start]" ;;
esac

[ -n "${WAOOAW_WEB_IMAGE:-}" ] || fail "WAOOAW_WEB_IMAGE is required"
printf '%s' "$WAOOAW_WEB_IMAGE" | grep -Eq '^[A-Za-z0-9._:/-]+@sha256:[0-9a-f]{64}$' \
  || fail "WAOOAW_WEB_IMAGE must be an immutable sha256 digest reference"

if [ -n "${AUTH_PREVIEW_ORIGIN:-}" ]; then
  preview_origin=$AUTH_PREVIEW_ORIGIN
else
  [ -n "${CODESPACE_NAME:-}" ] || fail "CODESPACE_NAME or AUTH_PREVIEW_ORIGIN is required"
  preview_origin="https://${CODESPACE_NAME}-${preview_port}.${forwarding_domain}"
fi
printf '%s' "$preview_origin" | grep -Eq '^https://[a-z0-9-]+-[0-9]+[.]app[.]github[.]dev$' \
  || fail "preview origin must be one exact Codespaces HTTPS origin"

keycloak_issuer=${KEYCLOAK_ISSUER:-https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io/realms/waooaw}
business_platform_url=${BUSINESS_PLATFORM_URL:-https://ca-demo-business-platform.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io}
printf '%s' "$keycloak_issuer" | grep -Eq '^https://[A-Za-z0-9.-]+/realms/waooaw$' \
  || fail "KEYCLOAK_ISSUER must be an HTTPS waooaw realm URL"
printf '%s' "$business_platform_url" | grep -Eq '^https://[A-Za-z0-9.-]+$' \
  || fail "BUSINESS_PLATFORM_URL must be an HTTPS origin"

mkdir -p "$state_directory"
chmod 700 "$state_directory"
nextauth_secret=$(openssl rand -hex 32)
source_revision=$(git -C "$repository_root" rev-parse HEAD)
generated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

umask 077
cat >"$runtime_environment" <<EOF
AUTH_PREVIEW_PORT=$preview_port
AUTH_PREVIEW_ORIGIN=$preview_origin
WAOOAW_WEB_IMAGE=$WAOOAW_WEB_IMAGE
NEXTAUTH_SECRET=$nextauth_secret
KEYCLOAK_ISSUER=$keycloak_issuer
BUSINESS_PLATFORM_URL=$business_platform_url
EOF

cat >"$release_manifest" <<EOF
{
  "generatedAt": "$generated_at",
  "sourceRevision": "$source_revision",
  "webImage": "$WAOOAW_WEB_IMAGE",
  "previewOrigin": "$preview_origin",
  "keycloakClientId": "waooaw-web-preview"
}
EOF

printf 'Prepared %s\n' "$release_manifest"
[ "$action" = prepare ] && exit 0

docker compose --env-file "$runtime_environment" -f "$compose_file" up -d --pull always
printf 'Authentication preview: %s/login\nRegistration preview: %s/register\n' "$preview_origin" "$preview_origin"