#!/usr/bin/env bash
# Implements: architecture/reference/runbooks/acceptance-sandbox-setup.md (WC-165)
# Constitutional basis: C-063 (no secret in argv, logs or chat), C-065 (the Founder supplies the values), C-080 (Docker-only)
#
# Seeds the acceptance Key Vault from one private file the Founder fills once. Values travel only through
# stdin into a disposable Azure CLI container; they are never printed, never in a command line, never in git.
#
#   scripts/acceptance_seed_secrets.sh init     create the empty template (mode 600) outside every repository
#   scripts/acceptance_seed_secrets.sh login    sign in to Azure with a device code (once)
#   scripts/acceptance_seed_secrets.sh seed     store every filled value, then shred the file
#   scripts/acceptance_seed_secrets.sh status   list which secret names are present (names only)
set -euo pipefail

IMAGE="${ACCEPTANCE_AZ_IMAGE:-mcr.microsoft.com/azure-cli:latest}"
VAULT="${ACCEPTANCE_VAULT:-kv-waooaw-demo-acc}"
SECRETS_FILE="${ACCEPTANCE_SECRETS_FILE:-/workspaces/.acceptance-secrets.env}"
AZ_CONFIG="${ACCEPTANCE_AZ_CONFIG:-$HOME/.waooaw-acceptance-az}"
KEEP_FILE=0
OVERWRITE=0

# Template key -> Key Vault secret name. Must equal the secrets in validation/acceptance/environments/demo.yaml
# (a test enforces this) minus the Keycloak provisioner secret, which the Keycloak step generates.
ENTRIES="
ACCEPTANCE_META_APP_ID=acceptance-meta-app-id
ACCEPTANCE_META_APP_SECRET=acceptance-meta-app-secret
ACCEPTANCE_META_TEST_USER_SESSION=acceptance-meta-test-user-session
ACCEPTANCE_META_TEST_PAGE_ID=acceptance-meta-test-page-id
ACCEPTANCE_META_TEST_PAGE_TOKEN=acceptance-meta-test-page-token
ACCEPTANCE_DEMO_COUPON_CODE=acceptance-demo-coupon-code
ACCEPTANCE_WHATSAPP_SANDBOX_RECIPIENT=acceptance-whatsapp-sandbox-recipient
ACCEPTANCE_WHATSAPP_WEBHOOK_SECRET=acceptance-whatsapp-webhook-secret
ACCEPTANCE_RAZORPAY_KEY_ID=razorpay-test-key-id
ACCEPTANCE_RAZORPAY_KEY_SECRET=razorpay-test-key-secret
ACCEPTANCE_RAZORPAY_WEBHOOK_SECRET=razorpay-test-webhook-secret
"

az_run() {
  docker run --rm -i -v "$AZ_CONFIG:/cfg" -e AZURE_CONFIG_DIR=/cfg "$IMAGE" az "$@"
}

secret_name_for() {
  printf '%s\n' "$ENTRIES" | sed -n "s/^$1=//p"
}

cmd_init() {
  if [ -e "$SECRETS_FILE" ]; then
    echo "Already exists: $SECRETS_FILE (not overwritten)"
    return 0
  fi
  umask 077
  {
    echo "# One KEY=VALUE per line. Leave a line empty to skip it. Value @/path/to/file reads that file."
    echo "# Test or development values only. This file is deleted after a successful seed."
    printf '%s\n' "$ENTRIES" | sed -n 's/=.*$/=/p'
  } > "$SECRETS_FILE"
  echo "Created $SECRETS_FILE (mode 600). Fill it in, then run: scripts/acceptance_seed_secrets.sh seed"
}

cmd_login() {
  mkdir -p "$AZ_CONFIG"
  chmod 700 "$AZ_CONFIG"
  az_run login --use-device-code --output none
  az_run account show --query '{user:user.name,subscription:name}' -o table
}

cmd_status() {
  az_run keyvault secret list --vault-name "$VAULT" --query "[].name" -o tsv | sort
}

cmd_seed() {
  [ -f "$SECRETS_FILE" ] || { echo "No file at $SECRETS_FILE; run init first." >&2; exit 2; }
  if [ -n "$(find "$SECRETS_FILE" -perm /077 2>/dev/null)" ]; then
    echo "Refusing: $SECRETS_FILE is readable by others (chmod 600 it)." >&2
    exit 2
  fi
  az_run account show --query id -o tsv > /dev/null || { echo "Not signed in; run login first." >&2; exit 2; }

  stored=0
  skipped=0
  failed=0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"
    value="${line#*=}"
    name="$(secret_name_for "$key")"
    if [ -z "$name" ]; then
      echo "Unknown key $key in $SECRETS_FILE; nothing for it is stored." >&2
      failed=$((failed + 1))
      continue
    fi
    if [ -z "$value" ]; then
      echo "skip   $name (empty)"
      skipped=$((skipped + 1))
      continue
    fi
    case "$value" in
      @*) value="$(cat "${value#@}")" ;;
    esac
    if [ "$key" = "ACCEPTANCE_RAZORPAY_KEY_ID" ] && [ "${value#rzp_test_}" = "$value" ]; then
      echo "Refusing $name: a Razorpay key id must begin rzp_test_ (test mode only)." >&2
      failed=$((failed + 1))
      continue
    fi
    if [ "$OVERWRITE" -eq 0 ] && az_run keyvault secret show --vault-name "$VAULT" --name "$name" --query id -o tsv < /dev/null > /dev/null 2>&1; then
      echo "exists $name (kept; use --overwrite to add a new version)"
      skipped=$((skipped + 1))
      continue
    fi
    if printf '%s' "$value" | az_run keyvault secret set --vault-name "$VAULT" --name "$name" --file /dev/stdin --encoding utf-8 --output none; then
      echo "stored $name"
      stored=$((stored + 1))
    else
      echo "FAILED $name" >&2
      failed=$((failed + 1))
    fi
    value=""
  done < "$SECRETS_FILE"

  echo "stored=$stored skipped=$skipped failed=$failed"
  if [ "$failed" -ne 0 ]; then
    echo "The file was kept because something failed." >&2
    exit 1
  fi
  if [ "$KEEP_FILE" -eq 0 ]; then
    shred -u "$SECRETS_FILE" 2>/dev/null || rm -f "$SECRETS_FILE"
    echo "Deleted $SECRETS_FILE"
  fi
  echo "Names now in $VAULT:"
  cmd_status
}

action="${1:-}"
[ -n "$action" ] && shift
while [ $# -gt 0 ]; do
  case "$1" in
    --keep-file) KEEP_FILE=1 ;;
    --overwrite) OVERWRITE=1 ;;
    *) echo "Unknown option $1" >&2; exit 2 ;;
  esac
  shift
done

case "$action" in
  init) cmd_init ;;
  login) cmd_login ;;
  seed) cmd_seed ;;
  status) cmd_status ;;
  *) echo "Usage: $0 init | login | seed [--keep-file] [--overwrite] | status" >&2; exit 2 ;;
esac
