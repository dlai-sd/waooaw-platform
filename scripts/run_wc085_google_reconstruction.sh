#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT_DIR=${1:-"$REPO_ROOT/test-results/wc085/google-reconstruction"}
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd)
WORK_DIR=$(mktemp -d)
NETWORK="wc085-google-$$"
KEYCLOAK="wc085-keycloak-$$"
KEYCLOAK_IMAGE="quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
AZURE_CLI_IMAGE="mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"

cleanup() {
  docker rm -f "$KEYCLOAK" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

docker run --rm -v "$REPO_ROOT:/repo:ro" -v "$WORK_DIR:/fixture" \
  --entrypoint /bin/sh hashicorp/terraform:1.9.8 -c '
    set -eu
    cp -R /repo/infrastructure/terraform/phase2/modules/workload /fixture/workload
    terraform -chdir=/fixture/workload init -backend=false -input=false -no-color >/dev/null
    printf "%s\n" "local.keycloak_realm_base64" | terraform -chdir=/fixture/workload console \
      -var-file=/repo/tests/fixtures/wc085-google.tfvars > /fixture/realm-base64.json
  '
docker run --rm -v "$WORK_DIR:/fixture" "$AZURE_CLI_IMAGE" /bin/sh -c '
  set -eu
  jq -r . /fixture/realm-base64.json | base64 --decode > /fixture/waooaw-realm.json
  openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
    -subj /CN=ca-demo-identity-edge.local.waooaw.test \
    -addext subjectAltName=DNS:ca-demo-identity-edge.local.waooaw.test \
    -keyout /fixture/fixture.key -out /fixture/fixture.crt >/dev/null 2>&1
  chmod 644 /fixture/fixture.key
  chmod 755 /fixture
  rm -rf /fixture/workload
  '
docker network create "$NETWORK" >/dev/null
for generation in 1 2; do
  docker run -d --rm --name "$KEYCLOAK" --network "$NETWORK" \
    --network-alias ca-demo-identity-edge.local.waooaw.test \
    -v "$WORK_DIR:/fixture:ro" \
    -v "$WORK_DIR/waooaw-realm.json:/opt/keycloak/data/import/waooaw-realm.json:ro" \
    -e KEYCLOAK_ADMIN=fixture-admin -e KEYCLOAK_ADMIN_PASSWORD=Synthetic-Admin-Only-123 \
    -e KEYCLOAK_CLIENT_SECRET=Synthetic-Web-Only-123 \
    -e DEMO_FOUNDER_PASSWORD=Synthetic-Founder-Only-123 \
    -e GOOGLE_CLIENT_ID=synthetic.apps.googleusercontent.com \
    -e GOOGLE_CLIENT_SECRET=Synthetic-Google-Only-123 \
    -e KC_HOSTNAME=https://ca-demo-identity-edge.local.waooaw.test \
    "$KEYCLOAK_IMAGE" start-dev --db=dev-file --import-realm --https-port=443 \
    --https-certificate-file=/fixture/fixture.crt --https-certificate-key-file=/fixture/fixture.key >/dev/null
  docker run --rm --network "$NETWORK" -e SSL_CERT_FILE=/fixture/fixture.crt \
    -e WC085_RECONSTRUCTION=true -e WC085_GENERATION="$generation" -e PYTHONPATH=/repo \
    -v "$REPO_ROOT:/repo:ro" -v "$WORK_DIR:/fixture:ro" -v "$OUTPUT_DIR:/evidence" \
    -w /repo pr408-test-runner-python:latest \
    pytest tests/identity-foundation/test_wc085_google_reconstruction.py -q -o cache_dir=/tmp/pytest-cache \
    --junitxml="/evidence/generation-$generation.xml"
  docker rm -f "$KEYCLOAK" >/dev/null
done
printf '%s\n' 'Two fresh Keycloak imports passed with synthetic credentials; real Google sign-in remains unverified.'