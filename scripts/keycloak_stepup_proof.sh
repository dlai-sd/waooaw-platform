#!/usr/bin/env bash
# Proves the Keycloak step-up realm behaviour against a real, pinned Keycloak container.
#
#   scripts/keycloak_stepup_proof.sh [--terraform] [--realm-dir DIR] [--client-id ID] [--keep]
#
# Everything executable runs in Docker (Keycloak + a python container for TOTP codes).
# The host only needs docker, bash, curl, jq and openssl for HTTP/PKCE plumbing.
# The default realm is infrastructure/keycloak/waooaw-realm.json (local dev realm).
# --terraform renders the Demo realm straight from the keycloak_realm local in
# infrastructure/terraform/phase2/modules/workload/main.tf (terraform runs in Docker) and proves that instead.
# --realm-dir imports an arbitrary realm directory; set CLIENT_SECRET when the client is confidential.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REALM_DIR="$ROOT/infrastructure/keycloak"
CLIENT_ID="waooaw-web"
CLIENT_SECRET="${CLIENT_SECRET:-}"
REDIRECT_URI="${REDIRECT_URI:-http://localhost:3000/api/auth/callback/keycloak}"
KEEP=0
TERRAFORM=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --realm-dir) REALM_DIR="$(cd "$2" && pwd)"; shift 2 ;;
    --client-id) CLIENT_ID="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    --terraform) TERRAFORM=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

IMAGE="$(grep -o 'quay.io/keycloak/keycloak@sha256:[0-9a-f]*' "$ROOT/docker-compose.yml" | head -1)"
TOTP_IMAGE="python:3.12-slim"
TERRAFORM_IMAGE="hashicorp/terraform:1.9"
NAME="kc-stepup-proof-$$"
WORK="$ROOT/.stepup-proof-work-$$"
mkdir -p "$WORK"
ADMIN_PASSWORD="proof-admin-only"
USER_NAME="founder-stepup@waooaw.local"
USER_PASSWORD="Stepup-proof-only-1!"

cleanup() {
  [[ "$KEEP" == 1 ]] || docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
b64url_decode() { local s="${1//-/+}"; s="${s//_//}"; while (( ${#s} % 4 )); do s+="="; done; printf '%s' "$s" | base64 -d; }
claims() { b64url_decode "$(cut -d. -f2 <<<"$1")"; }

if [[ "$TERRAFORM" == 1 ]]; then
  echo "== Rendering the Demo realm from the Terraform keycloak_realm local"
  TF_MAIN="$ROOT/infrastructure/terraform/phase2/modules/workload/main.tf"
  mkdir -p "$WORK/tf" "$WORK/tf-realm"
  {
    cat <<'HCL'
variable "environment" { default = "demo" }
variable "google_login_enabled" { default = false }
variable "facebook_login_enabled" { default = false }
variable "auth_preview_origin" { default = "http://localhost:3000" }
locals {
  google_identity_providers   = []
  facebook_identity_providers = []
  service_urls                = { web = "http://localhost:3000" }
HCL
    sed -n '/^  keycloak_realm = {/,/^  keycloak_realm_base64/p' "$TF_MAIN" | sed '$d'
    echo '}'
    echo 'output "realm" { value = jsonencode(local.keycloak_realm) }'
  } > "$WORK/tf/main.tf"
  tf() { docker run --rm --user "$(id -u):$(id -g)" -e TF_IN_AUTOMATION=1 -v "$WORK/tf:/w" -w /w "$TERRAFORM_IMAGE" "$@"; }
  tf init -input=false -no-color >/dev/null
  tf apply -auto-approve -no-color >/dev/null
  tf output -raw realm > "$WORK/tf-realm/waooaw-realm.json"
  jq -e '.browserFlow == "waooaw step-up browser"' "$WORK/tf-realm/waooaw-realm.json" >/dev/null || fail "rendered terraform realm lacks the step-up flow"
  chmod -R a+rX "$WORK/tf-realm"
  REALM_DIR="$WORK/tf-realm"
  CLIENT_SECRET="${CLIENT_SECRET:-proof-client-secret}"
fi

echo "== Booting $IMAGE (realm import from $REALM_DIR)"
docker run -d --name "$NAME" -p 127.0.0.1::8080 \
  -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  -e DEV_TEST_PASSWORD="$USER_PASSWORD" -e KEYCLOAK_CLIENT_SECRET="${CLIENT_SECRET:-unused}" \
  -e GOOGLE_CLIENT_ID=unused -e GOOGLE_CLIENT_SECRET=unused \
  -e META_LOGIN_CLIENT_ID=unused -e META_LOGIN_CLIENT_SECRET=unused \
  -e BP_IDENTITY_READER_CLIENT_SECRET=unused -e BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET=unused \
  -e DEMO_FOUNDER_PASSWORD="$USER_PASSWORD" \
  -v "$REALM_DIR:/opt/keycloak/data/import:ro" \
  "$IMAGE" start-dev --import-realm >/dev/null
PORT="$(docker port "$NAME" 8080/tcp | head -1 | sed 's/.*://')"
KC="http://localhost:$PORT"
for _ in $(seq 90); do
  curl -sf "$KC/realms/waooaw" >/dev/null 2>&1 && break
  docker inspect -f '{{.State.Running}}' "$NAME" | grep -q true || { docker logs "$NAME" | tail -30; fail "keycloak exited"; }
  sleep 2
done
curl -sf "$KC/realms/waooaw" >/dev/null || fail "keycloak realm 'waooaw' never became ready"

admin_token() {
  curl -sf -d client_id=admin-cli -d username=admin -d "password=$ADMIN_PASSWORD" -d grant_type=password \
    "$KC/realms/master/protocol/openid-connect/token" | jq -r .access_token
}
api() { local m="$1" p="$2"; shift 2; curl -sf -X "$m" -H "Authorization: Bearer $(admin_token)" -H 'Content-Type: application/json' "$KC/admin/realms/waooaw$p" "$@"; }

echo "== Creating test user $USER_NAME (realm roles: customer, founder; no OTP enrolled)"
api POST /users -d "$(jq -n --arg u "$USER_NAME" --arg p "$USER_PASSWORD" '{username:$u,email:$u,enabled:true,emailVerified:true,firstName:"Step",lastName:"Up",credentials:[{type:"password",value:$p,temporary:false}]}')"
UID_="$(api GET "/users?username=$USER_NAME&exact=true" | jq -r '.[0].id')"
api POST "/users/$UID_/role-mappings/realm" -d "$(jq -c '[.[]|select(.name=="founder" or .name=="customer")]' <<<"$(api GET /roles)")"

totp() { docker run --rm -i "$TOTP_IMAGE" python - "$1" <<'PY'
import base64, hashlib, hmac, struct, sys, time
key = base64.b32decode(sys.argv[1].replace(" ", "").upper() + "=" * (-len(sys.argv[1].replace(" ", "")) % 8))
counter = int(time.time()) // 30
digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
offset = digest[-1] & 0xF
print("%06d" % ((struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 10**6))
PY
}

html_action() { grep -o '<form[^>]*action="[^"]*"' "$1" | head -1 | sed 's/.*action="//;s/"$//;s/&amp;/\&/g'; }
html_input() { grep -o "<input[^>]*name=\"$2\"[^>]*>" "$1" | head -1 | grep -o 'value="[^"]*"' | head -1 | sed 's/value="//;s/"$//;s/&amp;/\&/g'; }

TOTP_SECRET=""
LAST_CODE=""
fresh_totp() {
  local code
  for _ in $(seq 40); do
    code="$(totp "$TOTP_SECRET")"
    if [[ "$code" != "$LAST_CODE" ]]; then LAST_CODE="$code"; OTP="$code"; return; fi
    sleep 2
  done
  fail "could not obtain a fresh TOTP code"
}

# login "<extra authorize params>" -> sets ACCESS_TOKEN; records which pages were shown in SEEN
login() {
  local extra="$1" jar="$WORK/jar" verifier challenge url state="st$RANDOM" step status loc code
  rm -f "$jar"; SEEN=""
  verifier="$(head -c 48 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n')"
  challenge="$(printf '%s' "$verifier" | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '=\n')"
  url="$KC/realms/waooaw/protocol/openid-connect/auth?client_id=$CLIENT_ID&response_type=code&scope=openid&state=$state&nonce=n$RANDOM&code_challenge=$challenge&code_challenge_method=S256&redirect_uri=$(jq -rn --arg u "$REDIRECT_URI" '$u|@uri')${extra:+&$extra}"
  local have_page=0 otp action manual
  for step in $(seq 12); do
    if [[ "$url" == "$REDIRECT_URI"* ]]; then
      [[ "$url" == *"state=$state"* ]] || fail "state mismatch in $url"
      code="$(sed -n 's/.*[?&]code=\([^&]*\).*/\1/p' <<<"$url")"
      [[ -n "$code" ]] || fail "redirect without code: $url"
      ACCESS_TOKEN="$(curl -sf "$KC/realms/waooaw/protocol/openid-connect/token" -d grant_type=authorization_code \
        -d client_id="$CLIENT_ID" ${CLIENT_SECRET:+-d client_secret="$CLIENT_SECRET"} -d code="$code" \
        -d code_verifier="$verifier" --data-urlencode "redirect_uri=$REDIRECT_URI" | jq -r .access_token)"
      return 0
    fi
    if (( have_page == 0 )); then
      status="$(curl -s -o "$WORK/page.html" -D "$WORK/hdr" -w '%{http_code}' -b "$jar" -c "$jar" "$url")"
    fi
    have_page=0
    if [[ "$status" =~ ^30 ]]; then
      url="$(grep -i '^location:' "$WORK/hdr" | tr -d '\r' | sed 's/^[Ll]ocation: *//')"
      continue
    fi
    [[ "$status" == 200 ]] || { head -c 600 "$WORK/page.html"; fail "unexpected HTTP $status at $url"; }
    grep -q 'pf-m-danger\|alert-error' "$WORK/page.html" && { grep -io 'kc-feedback-text[^<]*<' "$WORK/page.html" | head -3; fail "keycloak rejected the form post"; }
    action="$(html_action "$WORK/page.html")"
    if grep -q 'name="totpSecret"' "$WORK/page.html"; then
      SEEN+=" CONFIGURE_TOTP"
      manual="$(grep -o 'href="[^"]*mode=manual[^"]*"' "$WORK/page.html" | head -1 | sed 's/href="//;s/"$//;s/&amp;/\&/g')"
      curl -s -b "$jar" -c "$jar" "$manual" -o "$WORK/manual.html"
      TOTP_SECRET="$(sed -n 's/.*id="kc-totp-secret-key"[^>]*>\([^<]*\)<.*/\1/p' "$WORK/manual.html" | tr -d ' \n')"
      [[ -n "$TOTP_SECRET" ]] || fail "could not read TOTP secret from setup page"
      LAST_CODE=""; fresh_totp; otp="$OTP"
      status="$(curl -s -o "$WORK/page.html" -D "$WORK/hdr" -w '%{http_code}' -b "$jar" -c "$jar" "$(html_action "$WORK/manual.html")" \
        --data-urlencode "totp=$otp" --data-urlencode "totpSecret=$(html_input "$WORK/manual.html" totpSecret)" \
        --data-urlencode "userLabel=stepup-proof" --data-urlencode "saveTOTPBtn=")"
    elif grep -q 'name="otp"' "$WORK/page.html"; then
      SEEN+=" OTP"
      [[ -n "$TOTP_SECRET" ]] || fail "OTP requested but no secret is enrolled"
      fresh_totp; otp="$OTP"
      status="$(curl -s -o "$WORK/page.html" -D "$WORK/hdr" -w '%{http_code}' -b "$jar" -c "$jar" "$action" \
        --data-urlencode "otp=$otp" --data-urlencode "login=Sign In")"
    elif grep -q 'name="password"' "$WORK/page.html"; then
      SEEN+=" PASSWORD"
      status="$(curl -s -o "$WORK/page.html" -D "$WORK/hdr" -w '%{http_code}' -b "$jar" -c "$jar" "$action" \
        --data-urlencode "username=$USER_NAME" --data-urlencode "password=$USER_PASSWORD" --data-urlencode "credentialId=")"
    else
      head -c 1500 "$WORK/page.html"; fail "unrecognised login page"
    fi
    have_page=1
  done
  grep -o "kc-feedback-text[^<]*<\|id=\"input-error[^<]*<" "$WORK/page.html" | head -3 || true; echo "SEEN:$SEEN"; fail "login did not complete"
}

show() { jq -c '{acr,amr,auth_time,realm_roles:.realm_access.roles,azp}' <<<"$(claims "$ACCESS_TOKEN")"; }
# Mirrors PricingAdminController.HasStepUp.
has_step_up() {
  claims "$ACCESS_TOKEN" | jq -e --argjson now "$(date +%s)" '
    (.auth_time // 0) as $t
    | ($now - $t) >= -30 and ($now - $t) <= 300
    and (.acr == "2" or .acr == "3" or .acr == "urn:waooaw:aal2" or .acr == "urn:waooaw:aal3")
    and ([.amr] | flatten | map(tostring | split(" ")) | flatten | any(. == "mfa" or . == "otp" or . == "webauthn"))' >/dev/null
}
claim_is() { claims "$ACCESS_TOKEN" | jq -e "$1" >/dev/null || fail "$2 (claims: $(show))"; }
saw() { [[ "$SEEN" == *"$1"* ]] || fail "expected page $1 to be shown, saw:$SEEN"; }
not_saw() { [[ "$SEEN" != *"$1"* ]] || fail "page $1 must not be shown, saw:$SEEN"; }
STEPUP='prompt=login&max_age=0&acr_values=2'

echo "== 1. Normal login, no acr_values, no OTP enrolled: password only, acr 1"
login ""
echo "   pages:$SEEN"; show
saw PASSWORD; not_saw OTP; not_saw CONFIGURE_TOTP
claim_is '.acr == "1"' "normal login must have acr 1"
claim_is '.realm_access.roles | index("founder") != null' "founder realm role missing from token"
claim_is '[.amr]|flatten|index("otp") == null' "normal login must not claim otp"
has_step_up && fail "normal login must NOT satisfy HasStepUp"

echo "== 2. Step-up for a user WITHOUT OTP: forced TOTP enrolment (acr 2, but enrolment alone is not an OTP proof)"
login "$STEPUP"
echo "   pages:$SEEN"; show
saw PASSWORD; saw CONFIGURE_TOTP
claim_is '.acr == "2"' "step-up must give acr 2"
claim_is '[.amr]|flatten|index("pwd") != null and index("otp") == null' "enrolment pass must carry amr pwd only"
has_step_up && fail "enrolment pass must NOT satisfy HasStepUp; the user has to step up again"

echo "== 3. Normal login AFTER enrolment: still password only, acr 1"
login ""
echo "   pages:$SEEN"; show
saw PASSWORD; not_saw OTP; not_saw CONFIGURE_TOTP
claim_is '.acr == "1"' "normal login after enrolment must stay acr 1"
has_step_up && fail "normal login after enrolment must NOT satisfy HasStepUp"

echo "== 4. Step-up for an enrolled user: asked for the OTP code, then acr 2 / amr otp"
login "$STEPUP"
echo "   pages:$SEEN"; show
saw PASSWORD; saw OTP; not_saw CONFIGURE_TOTP
claim_is '.acr == "2"' "step-up must give acr 2"
claim_is '[.amr]|flatten|map(tostring|split(" "))|flatten|index("otp") != null' "step-up must carry amr otp"
has_step_up || fail "step-up token does not satisfy HasStepUp"

echo "== 5. SSO session still open (cookie kept): step-up request must still re-prompt"
login ""
SSO_STATUS="$(curl -s -o /dev/null -w '%{http_code}' -b "$WORK/jar" \
  "$KC/realms/waooaw/protocol/openid-connect/auth?client_id=$CLIENT_ID&response_type=code&scope=openid&code_challenge=$(printf 'x%.0s' $(seq 43))&code_challenge_method=S256&redirect_uri=$(jq -rn --arg u "$REDIRECT_URI" '$u|@uri')&$STEPUP")"
[[ "$SSO_STATUS" == 200 ]] || fail "step-up with a live SSO cookie must show a login page, got HTTP $SSO_STATUS"
echo "   with live SSO cookie, step-up request returned a login page (HTTP 200), not a silent redirect"

echo "== 6. Direct grant cannot step up (limit): password(+totp) grant ignores acr_values"
DG_CLIENT="waooaw-dev-client"
if api GET "/clients?clientId=$DG_CLIENT" | jq -e 'length==1' >/dev/null 2>&1; then
  fresh_totp
  DG="$(curl -s "$KC/realms/waooaw/protocol/openid-connect/token" -d grant_type=password -d client_id="$DG_CLIENT" \
    -d "username=$USER_NAME" --data-urlencode "password=$USER_PASSWORD" -d scope=openid -d acr_values=2 -d "totp=$OTP")"
  DG_TOKEN="$(jq -r '.access_token // empty' <<<"$DG")"
  if [[ -n "$DG_TOKEN" ]]; then
    echo "   direct-grant claims: $(claims "$DG_TOKEN" | jq -c '{acr,amr,auth_time}')"
    ACCESS_TOKEN="$DG_TOKEN"
    has_step_up && fail "direct grant unexpectedly satisfies step-up" || echo "   direct grant token does NOT satisfy HasStepUp (as expected)"
  else
    echo "   direct grant rejected: $(jq -c . <<<"$DG")"
  fi
else
  echo "   (client $DG_CLIENT not in this realm; skipped)"
fi

echo
echo "PASS: step-up realm behaviour proven on $IMAGE"
