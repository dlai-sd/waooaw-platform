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

existing_setting() {
  [ -f "$runtime_environment" ] || return 0
  sed -n "s/^$1=//p" "$runtime_environment" | head -n 1
}

secret_value() {
  value=$(existing_setting "$1")
  if [ -n "$value" ]; then
    printf '%s' "$value"
  else
    openssl rand -hex "$2"
  fi
}

base64_secret_value() {
  value=$(existing_setting "$1")
  if [ -n "$value" ]; then
    printf '%s' "$value"
  else
    openssl rand -base64 "$2" | tr -d '\n'
  fi
}

case ${1:-start} in
  prepare | start | stop) action=${1:-start} ;;
  *) fail "usage: $0 [prepare|start|stop]" ;;
esac

[ -z "${WAOOAW_WEB_IMAGE:-}" ] || printf '%s' "$WAOOAW_WEB_IMAGE" \
  | grep -Eq '^[A-Za-z0-9._:/-]+@sha256:[0-9a-f]{64}$' \
  || fail "WAOOAW_WEB_IMAGE must be an immutable sha256 digest reference when supplied"

if [ -n "${AUTH_PREVIEW_ORIGIN:-}" ]; then
  preview_origin=$AUTH_PREVIEW_ORIGIN
else
  [ -n "${CODESPACE_NAME:-}" ] || fail "CODESPACE_NAME or AUTH_PREVIEW_ORIGIN is required"
  preview_origin="https://${CODESPACE_NAME}-${preview_port}.${forwarding_domain}"
fi
printf '%s' "$preview_origin" | grep -Eq '^https://[a-z0-9-]+-[0-9]+[.]app[.]github[.]dev$' \
  || fail "preview origin must be one exact Codespaces HTTPS origin"

keycloak_issuer=${KEYCLOAK_ISSUER:-https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io/realms/waooaw}
printf '%s' "$keycloak_issuer" | grep -Eq '^https://[A-Za-z0-9.-]+/realms/waooaw$' \
  || fail "KEYCLOAK_ISSUER must be an HTTPS waooaw realm URL"

mkdir -p "$state_directory"
chmod 700 "$state_directory"
source_revision=$(git -C "$repository_root" rev-parse HEAD)
source_tag=$(printf '%s' "$source_revision" | cut -c1-12)
source_tree_digest=$(
  git -C "$repository_root" ls-files --cached --others --exclude-standard -z \
    | sort -z \
    | xargs -0 -I{} sha256sum "$repository_root/{}" \
    | sha256sum \
    | cut -d ' ' -f 1
)
auth_preview_deployment_id=$(openssl rand -hex 16)
generated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

if [ "$action" = stop ]; then
  [ -f "$runtime_environment" ] || fail "no prepared preview exists"
  docker compose --project-name waooaw-auth-preview --env-file "$runtime_environment" -f "$compose_file" down
  exit 0
fi

nextauth_secret=$(secret_value NEXTAUTH_SECRET 32)
postgres_password=$(secret_value POSTGRES_PASSWORD 24)
identity_hmac_key=$(secret_value IDENTITY_HMAC_KEY 32)
identity_event_signing_key=$(secret_value IDENTITY_EVENT_SIGNING_KEY 32)
phone_identity_signing_key=$(secret_value PHONE_IDENTITY_SIGNING_KEY 32)
whatsapp_webhook_secret=$(secret_value WHATSAPP_WEBHOOK_SECRET 32)
whatsapp_tenant_token_key=$(secret_value WHATSAPP_TENANT_TOKEN_KEY 32)
conversation_cursor_hmac_key=$(secret_value CONVERSATION_CURSOR_HMAC_KEY 32)
channel_continuity_hmac_key=$(base64_secret_value CHANNEL_CONTINUITY_HMAC_KEY 32)
data_protection_certificate_password=$(secret_value DATA_PROTECTION_CERTIFICATE_PASSWORD 24)
data_protection_certificate="$state_directory/data-protection.pfx"
if [ ! -f "$data_protection_certificate" ]; then
  certificate_key=$(mktemp)
  certificate_pem=$(mktemp)
  trap 'rm -f "$certificate_key" "$certificate_pem"' EXIT
  openssl req -x509 -newkey rsa:2048 -sha256 -days 30 -nodes \
    -subj '/CN=WAOOAW Codespaces Data Protection' \
    -keyout "$certificate_key" -out "$certificate_pem" >/dev/null 2>&1
  openssl pkcs12 -export -out "$data_protection_certificate" -inkey "$certificate_key" \
    -in "$certificate_pem" -passout "pass:$data_protection_certificate_password"
  chmod 644 "$data_protection_certificate"
fi

umask 077
cat >"$runtime_environment" <<EOF
AUTH_PREVIEW_PORT=$preview_port
AUTH_PREVIEW_ORIGIN=$preview_origin
AUTH_PREVIEW_SOURCE_TAG=$source_tag
AUTH_PREVIEW_DEPLOYMENT_ID=$auth_preview_deployment_id
WAOOAW_WEB_IMAGE=${WAOOAW_WEB_IMAGE:-}
NEXTAUTH_SECRET=$nextauth_secret
AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS=3600
KEYCLOAK_ISSUER=$keycloak_issuer
POSTGRES_PASSWORD=$postgres_password
IDENTITY_HMAC_KEY=$identity_hmac_key
IDENTITY_EVENT_SIGNING_KEY=$identity_event_signing_key
PHONE_IDENTITY_SIGNING_KEY=$phone_identity_signing_key
WHATSAPP_WEBHOOK_SECRET=$whatsapp_webhook_secret
WHATSAPP_TENANT_TOKEN_KEY=$whatsapp_tenant_token_key
CONVERSATION_CURSOR_HMAC_KEY=$conversation_cursor_hmac_key
CHANNEL_CONTINUITY_HMAC_KEY=$channel_continuity_hmac_key
DATA_PROTECTION_CERTIFICATE_PASSWORD=$data_protection_certificate_password
EOF

compose="docker compose --project-name waooaw-auth-preview --env-file $runtime_environment -f $compose_file"
$compose config --quiet

if [ "$action" = start ]; then
  if [ -n "${WAOOAW_WEB_IMAGE:-}" ]; then
    $compose pull auth-preview
    $compose up -d --build --wait --wait-timeout 600 postgres temporal jaeger constitutional-engine business-platform
    $compose up -d --no-build --wait --wait-timeout 180 auth-preview
  else
    $compose up -d --build --wait --wait-timeout 900
  fi
  $compose exec -T postgres psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /auth-preview/ensure-ce-audit-role.sql
  $compose exec -T postgres psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /docker-entrypoint-initdb.d/41-relationship-acquisition-mode.sql
  $compose exec -T postgres psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /auth-preview/seed-marketplace.sql
fi

web_image=${WAOOAW_WEB_IMAGE:-waooaw/auth-preview-web:$source_tag}
web_image_id=$(docker image inspect --format '{{.Id}}' "$web_image" 2>/dev/null || true)
cat >"$release_manifest" <<EOF
{
  "generatedAt": "$generated_at",
  "sourceRevision": "$source_revision",
  "sourceTreeDigest": "sha256:$source_tree_digest",
  "webImage": "$web_image",
  "webImageId": "${web_image_id:-not-built}",
  "previewOrigin": "$preview_origin",
  "keycloakIssuer": "$keycloak_issuer",
  "keycloakClientId": "waooaw-web-preview",
  "businessPlatform": "local-compose"
}
EOF

printf 'Prepared %s\n' "$release_manifest"
[ "$action" = prepare ] && exit 0
printf 'WAOOAW portal: %s\nLogin: %s/login\nRegister: %s/register\nMarketplace: %s/marketplace\nMy Agents: %s/professionals/mine\n' \
  "$preview_origin" "$preview_origin" "$preview_origin" "$preview_origin" "$preview_origin"