#!/usr/bin/env bash
set -euo pipefail
set +x

for variable in AZURE_CLIENT_ID RUNNER_VAULT_NAME GITHUB_APP_KEY_NAME; do
  test -n "${!variable:-}" || {
    printf 'Required importer environment is missing: %s\n' "$variable" >&2
    exit 64
  }
done

umask 077
pem_file=$(mktemp)
terminal_echo_disabled=false

cleanup() {
  if "$terminal_echo_disabled"; then
    stty echo 2>/dev/null || true
  fi
  if command -v shred >/dev/null 2>&1; then
    shred --remove "$pem_file" 2>/dev/null || rm -f "$pem_file"
  else
    rm -f "$pem_file"
  fi
}
trap cleanup EXIT HUP INT TERM

printf 'Paste the replacement GitHub App PEM, then press Ctrl-D. Input is not echoed.\n' >&2
stty -echo
terminal_echo_disabled=true
cat >"$pem_file"
stty echo
terminal_echo_disabled=false
printf '\n' >&2

openssl pkey -in "$pem_file" -check -noout >/dev/null 2>&1 || {
  printf 'The supplied PEM is not a valid private key.\n' >&2
  exit 65
}

az login --identity --client-id "$AZURE_CLIENT_ID" --allow-no-subscriptions --output none
expires=$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ)
key_id=$(az keyvault key import \
  --vault-name "$RUNNER_VAULT_NAME" \
  --name "$GITHUB_APP_KEY_NAME" \
  --pem-file "$pem_file" \
  --protection software \
  --exportable false \
  --ops sign verify \
  --expires "$expires" \
  --query key.kid \
  --output tsv \
  --only-show-errors)

test -n "$key_id" || {
  printf 'Key Vault did not return an imported key version.\n' >&2
  exit 69
}
printf 'Imported key version: %s\n' "${key_id##*/}"