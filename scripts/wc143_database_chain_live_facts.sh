#!/usr/bin/env bash
# Print the live database and credential facts a recorded WC-124 chain must still match (WC-143).
# Reads only; any missing resource makes the script fail so the caller runs the full chain.
set -euo pipefail

: "${TARGET_ENVIRONMENT:?}" "${RESOURCE_GROUP:?}" "${KEY_VAULT_NAME:?}"
catalog="${SECRET_CATALOG:-infrastructure/environment-readiness/secret-catalog.json}"
server_name="psql-waooaw-${TARGET_ENVIRONMENT}-state"

server=$(az postgres flexible-server show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$server_name" \
  --query '{id: id, created_at: systemData.createdAt, password_auth: authConfig.passwordAuth}' \
  --output json)

credentials='[]'
while IFS=$'\t' read -r secret_id vault_name; do
  record=$(az keyvault secret show \
    --vault-name "$KEY_VAULT_NAME" \
    --name "$vault_name" \
    --query '{id: id, enabled: attributes.enabled}' \
    --output json)
  version_id=$(jq -er 'select(.enabled == true) | .id | split("/")[-1]' <<< "$record")
  credentials=$(jq -c \
    --arg secret_id "$secret_id" \
    --arg vault_name "$vault_name" \
    --arg version_id "$version_id" \
    '. + [{logical_secret_id: $secret_id, vault_secret_name: $vault_name, version_id: $version_id}]' \
    <<< "$credentials")
done < <(jq -r \
  --arg environment "$TARGET_ENVIRONMENT" \
  '.entries[]
   | select(.provisioner == "wc124-db-provisioner" and (.environments | index($environment)))
   | [.id, .vaultSecretName]
   | @tsv' \
  "$catalog")

test "$(jq 'length' <<< "$credentials")" -gt 0
jq -nS \
  --arg environment "$TARGET_ENVIRONMENT" \
  --argjson server "$server" \
  --argjson credentials "$credentials" \
  '{environment: $environment, server: $server, credentials: ($credentials | sort_by(.logical_secret_id))}'
