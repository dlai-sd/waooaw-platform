#!/usr/bin/env bash
# Runs one customer-journey-acceptance journey locally in Docker, mirroring .github/workflows/customer-journey-acceptance.yaml,
# against customers made by scripts/demo_synthetic_customer.py (create ... --harness-private DIR).
# usage: run_acceptance_with_synthetic_customers.sh JOURNEY [desktop|mobile]   (env: HARNESS_PRIVATE, WAOOAW_RUNNER_PYTHON_IMAGE, WAOOAW_RUNNER_TYPESCRIPT_IMAGE)
set -uo pipefail
J=$1; D=${2:-desktop}
REPO=${REPO:-$PWD}
PY=${WAOOAW_RUNNER_PYTHON_IMAGE:?set WAOOAW_RUNNER_PYTHON_IMAGE}
TS=${WAOOAW_RUNNER_TYPESCRIPT_IMAGE:?set WAOOAW_RUNNER_TYPESCRIPT_IMAGE}
OUT=${OUT_ROOT:-test-results/acceptance-local}/$J-$D; PRIVATE=${PRIVATE_ROOT:-/tmp/acceptance-private}/$J-$D
rm -rf "$OUT" "$PRIVATE"; mkdir -p "$OUT" "$PRIVATE"; chmod 0777 "$OUT"; chmod 0700 "$PRIVATE"; cp ${HARNESS_PRIVATE:?set HARNESS_PRIVATE to the directory used with --harness-private}/run-state.json "$PRIVATE/run-state.json"; chmod 600 "$PRIVATE/run-state.json"
U="$(id -u):$(id -g)"
docker run --rm --user "$U" -v "$REPO:/workspace:ro" -v "$OUT:/out" -w /workspace "$PY" python scripts/acceptance_static_gates.py compile --journey "$J" --environment demo --out /out || { echo "COMPILE FAILED"; exit 2; }
set -a; . /workspaces/.codespaces/shared/.env; set +a
: > "$PRIVATE/run.env"; chmod 600 "$PRIVATE/run.env"; : > "$OUT/unreadable-secrets.txt"
VAULT=$(jq -r .azure.key_vault "$OUT/profile.json")
jq -c '.secrets[]' "$OUT/profile.json" | while read -r e; do
  n=$(jq -r .name <<<"$e"); v=$(jq -r .env <<<"$e")
  val=$(az keyvault secret show --vault-name "$VAULT" --name "$n" --query value -o tsv 2>/dev/null || true)
  if [ -n "$val" ]; then printf '%s=%s\n' "$v" "$val" >> "$PRIVATE/run.env"; else echo "$n" >> "$OUT/unreadable-secrets.txt"; fi
done
echo "secrets read: $(wc -l < "$PRIVATE/run.env") unreadable: $(wc -l < "$OUT/unreadable-secrets.txt")"
jq -n --arg started "$(date -u +%FT%TZ)" '{services: [], provider_mode_findings: [], synthetic_volume: {customers_created: 0, customers_removed: 0, left_over: []}, started_at: $started}' > "$OUT/run-meta.json"
echo "flags: effective-flags capture skipped locally"; echo '{}' > "$OUT/flags.json"
docker run --rm --user "$U" -v "$REPO:/workspace:ro" -v "$OUT:/out" -w /workspace "$TS" node tests/journey-acceptance/run.ts probe --profile /out/profile.json --out /out; P=$?
echo "probe exit $P"
if [ $P = 0 ]; then
  docker run --rm --user "$U" -v "$REPO:/workspace:ro" -v "$OUT:/out" -v "$PRIVATE:/private" --env-file "$PRIVATE/run.env" -e ACCEPTANCE_OUT=/out -e ACCEPTANCE_PRIVATE=/private -e ACCEPTANCE_JOURNEY="$J" -e ACCEPTANCE_DEVICE="$D" -e HOME=/tmp -w /workspace "$TS" sh -c 'rm -rf /tmp/ja && cp -a /workspace/tests/journey-acceptance /tmp/ja && ln -s /opt/waooaw-web/node_modules /tmp/ja/node_modules && cd /tmp/ja && playwright test -c playwright.config.ts'
  echo "journey exit $?"
  echo "cleanup skipped (customers are removed with scripts/demo_synthetic_customer.py)"
fi
docker run --rm --user "$U" -v "$REPO:/workspace:ro" -v "$OUT:/out" -v "$PRIVATE:/private" -w /workspace "$TS" node tests/journey-acceptance/run.ts finalize --plan /out/plan.json --profile /out/profile.json --out /out --private-dir /private --commit "$(git -C $REPO rev-parse HEAD)" --device "$D"
echo "finalize exit $?"
rm -rf "$PRIVATE"
echo "DONE $J $D"
