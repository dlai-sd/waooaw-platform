#!/usr/bin/env bash
set -euo pipefail
set +x

test -n "${RUNNER_ACTIVATION_STATE:-}" || {
  printf 'Required runner environment is missing: RUNNER_ACTIVATION_STATE\n' >&2
  exit 64
}
test "$RUNNER_ACTIVATION_STATE" = ACTIVE || exit 0

required_environment=(
  RUNNER_NAME
  RUNNER_GROUP
  RUNNER_LABEL
  RUNNER_CORRELATION_ID
  GITHUB_ORGANIZATION
  GITHUB_WORKFLOW_RUN_ID
  GITHUB_WORKFLOW_RUN_ATTEMPT
  RUNNER_VAULT_URL
  RUNNER_TOKEN_SECRET_NAME
)
for variable in "${required_environment[@]}"; do
  test -n "${!variable:-}" || {
    printf 'Required runner environment is missing: %s\n' "$variable" >&2
    exit 64
  }
done
runner_environment="${RUNNER_LABEL#goal006-}"
runner_environment="${runner_environment%-private}"
test "$RUNNER_NAME" = "goal006-${runner_environment}-${GITHUB_WORKFLOW_RUN_ID}-${GITHUB_WORKFLOW_RUN_ATTEMPT}" || exit 64
test "$RUNNER_CORRELATION_ID" = "goal006:${runner_environment}:${GITHUB_WORKFLOW_RUN_ID}:${GITHUB_WORKFLOW_RUN_ATTEMPT}" || exit 64

RUNNER_REGISTRATION_TOKEN="$(python3 /opt/waooaw/goal006_runner_lifecycle.py read-secret \
  --vault-url "$RUNNER_VAULT_URL" \
  --secret-name "$RUNNER_TOKEN_SECRET_NAME" \
  --correlation "$RUNNER_CORRELATION_ID")"
export RUNNER_REGISTRATION_TOKEN

./config.sh \
  --unattended \
  --ephemeral \
  --disableupdate \
  --url "https://github.com/$GITHUB_ORGANIZATION" \
  --token "$RUNNER_REGISTRATION_TOKEN" \
  --name "$RUNNER_NAME" \
  --runnergroup "$RUNNER_GROUP" \
  --labels "$RUNNER_LABEL,$RUNNER_CORRELATION_ID,github-run-$GITHUB_WORKFLOW_RUN_ID"

unset RUNNER_REGISTRATION_TOKEN
exec ./run.sh