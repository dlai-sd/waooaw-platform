#!/usr/bin/env sh
set -eu

image=${1:?usage: smoke_business_platform_image.sh IMAGE}
suffix=$$
postgres_container="waooaw-bp-smoke-postgres-$suffix"
app_container="waooaw-bp-smoke-app-$suffix"
hmac_key=$(printf 'waooaw-bp-smoke-%s' "$suffix" | sha256sum | cut -d' ' -f1)

cleanup() {
  docker rm -f "$app_container" "$postgres_container" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker run --detach --name "$postgres_container" \
  --cpus 0.25 --memory 512m \
  --env POSTGRES_DB=waooaw \
  --env POSTGRES_HOST_AUTH_METHOD=trust \
  --publish 127.0.0.1::5001 \
  postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685 >/dev/null

attempt=0
until docker exec "$postgres_container" pg_isready --username postgres --dbname waooaw >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 30 ] || { docker logs "$postgres_container" >&2; exit 1; }
  sleep 1
done

docker run --detach --name "$app_container" \
  --network "container:$postgres_container" \
  --cpus 0.5 --memory 1g \
  --env ASPNETCORE_ENVIRONMENT=Production \
  --env ASPNETCORE_URLS=http://+:5001 \
  --env ConnectionStrings__DefaultConnection='Host=localhost;Port=5432;Database=waooaw;Username=postgres' \
  --env BP_SERVICE_JWT_SECRET=synthetic-service-jwt-secret-32-bytes-minimum \
  --env Keycloak__Authority=https://identity.invalid/realms/waooaw \
  --env Keycloak__Audience=waooaw-platform \
  --env Keycloak__RequireHttpsMetadata=true \
  --env Identity__Hmac__ActiveVersion=v1 \
  --env Identity__Hmac__Key="$hmac_key" \
  --env IdentityBrokerRead__Enabled=true \
  --env IdentityBrokerRead__ActorIssuer=https://identity.invalid/realms/waooaw \
  --env IdentityBrokerRead__PrivateOrigin=https://keycloak.private.invalid \
  --env IdentityBrokerRead__AllowedPrivateHosts__0=keycloak.private.invalid \
  --env IdentityBrokerRead__ClientId=waooaw-bp-identity-reader \
  --env IdentityBrokerRead__ClientSecret=synthetic-reader-secret \
  --env IdentityBrokerRead__AllowedAuthorizedParties__0=waooaw-web \
  --env IdentityBrokerRead__AllowedAuthorizedParties__1=waooaw-web-preview \
  --env IdentityBrokerRead__Providers__google__ProviderNamespace=urn:waooaw:identity:smoke:google:customer-login:v1 \
  --env IdentityBrokerRead__Providers__google__TrustConfigDigest=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --env IdentityBrokerRead__Providers__facebook__ProviderNamespace=urn:waooaw:identity:smoke:facebook:customer-login:v1 \
  --env IdentityBrokerRead__Providers__facebook__TrustConfigDigest=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  "$image" >/dev/null

host_port=$(docker port "$postgres_container" 5001/tcp | sed 's/.*://')
if ! curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 1 \
  "http://127.0.0.1:$host_port/health/ready" >/dev/null; then
  docker logs "$app_container" >&2
  exit 1
fi

test "$(docker inspect "$app_container" --format '{{.State.Running}}')" = true
test "$(docker inspect "$app_container" --format '{{.RestartCount}}')" = 0
printf 'Business Platform deployment-shaped image smoke passed: %s\n' "$image"