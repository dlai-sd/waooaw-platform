#!/usr/bin/env bash
# Implements: WC120-R024, WC120-R041, WC120-R044 exact-candidate qualification
# Constitutional basis: C-023, C-026, C-059, C-065

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "WC-120 qualification requires a clean exact candidate." >&2
  exit 1
fi
candidate_commit="$(git rev-parse HEAD)"
if [[ ! "${candidate_commit}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "WC-120 qualification requires an exact 40-character candidate commit." >&2
  exit 1
fi

./scripts/generate_wc120_clients.sh
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Generated clients differ from the committed exact candidate." >&2
  exit 1
fi

result_root="${repo_root}/test-results/wc120"
mkdir -p "${result_root}"

service_image_digest() {
  local profile="$1"
  local service="$2"
  local compose_config
  local image

  if [[ -n "${profile}" ]]; then
    compose_config="$(docker compose --profile "${profile}" config --format json)"
  else
    compose_config="$(docker compose config --format json)"
  fi
  image="$(
    jq -r --arg service "${service}" \
      '.services[$service].image // (.name + "-" + $service)' \
      <<<"${compose_config}"
  )"
  docker image inspect --format='{{.Id}}' "${image}"
}

dotnet_runner_digest="$(service_image_digest test-dotnet test-runner-dotnet)"
python_runner_digest="$(service_image_digest test-python test-runner-python)"
browser_runner_digest="$(service_image_digest test test-runner)"

container_path() {
  printf '/workspace/%s' "${1#"${repo_root}/"}"
}

run_selector() {
  local ce_fit_id="$1"
  local runner_digest="$2"
  local node="$3"
  shift 3
  local evidence_dir="${result_root}/${ce_fit_id}"
  local log="${evidence_dir}/selector.log"
  local started_at
  local command_text
  mkdir -p "${evidence_dir}"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -v command_text '%q ' "$@"
  set +e
  "$@" 2>&1 | tee "${log}"
  local status="${PIPESTATUS[0]}"
  set -e
  docker compose --profile test-python run --rm test-runner-python \
    python scripts/validation_control/wc120_evidence.py selector \
    --source-commit "${candidate_commit}" \
    --ce-fit-id "${ce_fit_id}" \
    --command "${command_text}" \
    --node "${node}" \
    --started-at "${started_at}" \
    --exit-status "${status}" \
    --runner-image-digest "${runner_digest}" \
    --log "$(container_path "${log}")"
  if [[ "${status}" -ne 0 ]]; then
    return "${status}"
  fi
}

run_summary() {
  local name="$1"
  local output="$2"
  shift 2
  local log="${result_root}/${name}.log"
  local started_at
  local command_text
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -v command_text '%q ' "$@"
  set +e
  "$@" 2>&1 | tee "${log}"
  local status="${PIPESTATUS[0]}"
  set -e
  docker compose --profile test-python run --rm test-runner-python \
    python scripts/validation_control/wc120_evidence.py summary \
    --source-commit "${candidate_commit}" \
    --name "${name}" \
    --command "${command_text}" \
    --started-at "${started_at}" \
    --exit-status "${status}" \
    --log "$(container_path "${log}")" \
    --output "$(container_path "${output}")"
  if [[ "${status}" -ne 0 ]]; then
    return "${status}"
  fi
}

declare -a dotnet_nodes=(
  "CE-FIT-01|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit01CanonicalContinuityTests.WebWhatsAppWeb_RetainsCanonicalIdentitySequencePlanAndAuthority_WithoutDuplicateConversation"
  "CE-FIT-02|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit02ServerContextTests.RegisteredContext_UsesAuthenticatedCurrentServerState_AndRejectsForgedUnknownCrossSubjectReferences"
  "CE-FIT-03|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit03ContextStalenessTests.SourceVersionChange_MarksAffectedContextStaleBeforeExecution_AndPreventsCurrentPresentation"
  "CE-FIT-04|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit04SemanticEquivalenceTests.ConfirmedContextAndPolicy_ProduceEquivalentWebAndWhatsAppRecommendations"
  "CE-FIT-05|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit05RepeatQuestionCorpusTests.ApprovedCorpus_ReportsRepeatedConfirmedFacts_WithoutPromotingInference"
  "CE-FIT-06|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit06ConclusionContractTests.MaterialConversation_RequiresConclusionFieldsOrTypedContinuation_AndRejectsFalseSuccess"
  "CE-FIT-07|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit07IndependentStateTests.TransportExecutionDecisionAndEvidence_TransitionIndependently_WithoutSyntheticSuccess"
  "CE-FIT-08|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit08ConcurrentIntentTests.ConcurrentWebAndWhatsAppIntent_CommitsOnce_ReplaysPriorOutcome_AndRejectsDivergentReuse"
  "CE-FIT-09|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit09WebhookIngressTests.ChallengeRawHmacLimitsBindingsAndAtomicClaim_FailClosed_AndCommitOneDurableOutcome"
  "CE-FIT-10|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit10EligibilityTests.ConsentWindowAndTemplateMatrix_IsDeterministic_AndIneligibleCasesDispatchZero"
  "CE-FIT-11|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit11MediaVoiceSafetyTests.MediaCorpus_ScansBeforeReasoning_AndRequiresCorrectedTranscriptConfirmationAndSendConsent"
  "CE-FIT-13|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit13StopResilienceTests.TypedStop_MeetsAcceptedLatency_AndSurvivesOutageDuplicateSimultaneousRestartAndRelease"
  "CE-FIT-14|Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness.CeFit14TelemetryLeakageTests.SuccessFailureRetryScannerAndTracePaths_ContainZeroProhibitedTelemetryOrDeadLetterData"
)

for entry in "${dotnet_nodes[@]}"; do
  IFS='|' read -r ce_fit_id node <<<"${entry}"
  run_selector "${ce_fit_id}" "${dotnet_runner_digest}" "${node}" \
    docker compose --profile test-dotnet run --rm test-runner-dotnet \
    sh scripts/validation_control/run_wc120_dotnet_test.sh \
    --filter "FullyQualifiedName=${node}" \
    --logger "trx;LogFileName=test-results.trx" \
    --results-directory "/workspace/test-results/wc120/${ce_fit_id}"
done

run_selector "CE-FIT-12" "${python_runner_digest}" \
  "tests/contract/test_wc120_environment_isolation.py::test_ce_fit_12_rejects_cross_environment_identity_credentials_hosts_state_and_imports" \
  docker compose --profile test-python run --rm test-runner-python pytest -q \
  --junitxml test-results/wc120/CE-FIT-12/junit.xml \
  tests/contract/test_wc120_environment_isolation.py::test_ce_fit_12_rejects_cross_environment_identity_credentials_hosts_state_and_imports
run_selector "CE-FIT-15" "${python_runner_digest}" \
  "tests/contract/test_wc120_second_client.py::test_ce_fit_15_second_generated_client_preserves_public_semantics_and_bp_authority" \
  docker compose --profile test-python run --rm test-runner-python pytest -q \
  --junitxml test-results/wc120/CE-FIT-15/junit.xml \
  tests/contract/test_wc120_second_client.py::test_ce_fit_15_second_generated_client_preserves_public_semantics_and_bp_authority
run_selector "CE-FIT-16" "${python_runner_digest}" \
  "tests/contract/test_wc120_demo_teardown.py::test_ce_fit_16_demo_teardown_disables_callback_and_preserves_uat_production_or_denies_open_obligations" \
  docker compose --profile test-python run --rm test-runner-python pytest -q \
  --junitxml test-results/wc120/CE-FIT-16/junit.xml \
  tests/contract/test_wc120_demo_teardown.py::test_ce_fit_16_demo_teardown_disables_callback_and_preserves_uat_production_or_denies_open_obligations

for entry in \
  "CE-FIT-10|CE-FIT-10 presents consent and eligibility states accessibly" \
  "CE-FIT-11|CE-FIT-11 presents voice and media states accessibly" \
  "CE-FIT-13|CE-FIT-13 keeps Stop reachable and truthful in degraded states"
do
  IFS='|' read -r ce_fit_id node <<<"${entry}"
  run_selector "${ce_fit_id}" "${browser_runner_digest}" \
    "tests/e2e/wc120-product-state-accessibility.spec.ts::${node}" \
    docker compose --profile test run --rm \
    test-runner sh -lc \
    "rm -rf /tmp/wc120-web && cp -a web /tmp/wc120-web && rm -rf /tmp/wc120-web/node_modules && ln -s /opt/waooaw-web/node_modules /tmp/wc120-web/node_modules && cd /tmp/wc120-web && PLAYWRIGHT_HTML_OPEN=never PLAYWRIGHT_HTML_OUTPUT_DIR=/workspace/test-results/wc120/${ce_fit_id}/playwright-report pnpm exec playwright test tests/e2e/wc120-product-state-accessibility.spec.ts --grep '${node}$' --reporter=html"
done

run_summary "targeted-tests" "${result_root}/targeted-test-results.json" \
  docker compose --profile test-dotnet run --rm test-runner-dotnet \
  sh scripts/validation_control/run_wc120_dotnet_test.sh \
  --filter "FullyQualifiedName~Waooaw.BusinessPlatform.Tests.ConversationWhatsApp"
run_summary "recovery-tests" "${result_root}/recovery-test-results.json" \
  docker compose --profile test-python run --rm test-runner-python pytest -q \
  tests/contract/test_wc120_contract_and_recovery.py \
  tests/contract/test_wc120_environment_isolation.py \
  tests/contract/test_wc120_second_client.py \
  tests/contract/test_wc120_demo_teardown.py
run_summary "final-docker-qualification" "${result_root}/final-docker-qualification.json" \
  docker compose --profile test run --rm test-runner sh -lc \
  "sh scripts/validation_control/run_wc120_dotnet_test.sh && pytest -q tests/contract && rm -rf /tmp/wc120-web && cp -a web /tmp/wc120-web && rm -rf /tmp/wc120-web/node_modules && ln -s /opt/waooaw-web/node_modules /tmp/wc120-web/node_modules && cd /tmp/wc120-web && pnpm test -- --runInBand && pnpm exec playwright test tests/e2e/wc120-product-state-accessibility.spec.ts --grep 'CE-FIT-10 presents consent and eligibility states accessibly$' && pnpm exec playwright test tests/e2e/wc120-product-state-accessibility.spec.ts --grep 'CE-FIT-11 presents voice and media states accessibly$' && pnpm exec playwright test tests/e2e/wc120-product-state-accessibility.spec.ts --grep 'CE-FIT-13 keeps Stop reachable and truthful in degraded states$'"

docker compose build business-platform
business_platform_digest="$(service_image_digest "" business-platform)"
cat >"${result_root}/image-digests.json" <<EOF
{
  "business_platform": "${business_platform_digest}",
  "test_runners": {
    "dotnet": "${dotnet_runner_digest}",
    "python": "${python_runner_digest}",
    "browser": "${browser_runner_digest}"
  }
}
EOF
docker compose --profile test-python run --rm test-runner-python \
  python scripts/validation_control/wc120_evidence.py candidate \
  --source-commit "${candidate_commit}" \
  --image-digests /workspace/test-results/wc120/image-digests.json \
  --targeted-results /workspace/test-results/wc120/targeted-test-results.json \
  --recovery-results /workspace/test-results/wc120/recovery-test-results.json \
  --final-qualification /workspace/test-results/wc120/final-docker-qualification.json
