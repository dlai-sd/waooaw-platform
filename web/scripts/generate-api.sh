#!/usr/bin/env sh
set -eu

# Implements: architecture/reference/components/conversation-core.md §3 and WC-034 F4 Public BP Contract
# Constitutional basis: C-032 (Spec Is Truth), C-059 (Implementation Traceability)

readonly GENERATOR_IMAGE="openapitools/openapi-generator-cli:v7.17.0"
readonly REPOSITORY_ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
readonly OUTPUT_PATH="$REPOSITORY_ROOT/web/lib/api/generated"
readonly STAGING_PATH="$REPOSITORY_ROOT/web/lib/api/generated.next"
readonly SLICE_PATH="$(mktemp "$REPOSITORY_ROOT/architecture/reference/api-specs/.web-openapi.XXXXXX.yaml")"
readonly CONTAINER_SLICE_PATH="/local${SLICE_PATH#"$REPOSITORY_ROOT"}"
readonly GENERATED_APIS="
ConversationApi
IdentityApi
RelationshipWorkspaceApi
"
readonly GENERATED_MODELS="
AcquisitionIntent
AdmitEmploymentRelationship201Response
AdmitEmploymentRelationshipRequest
ConversationChannelSessionEndOutcomeV1
CustomerEngagementAdmissionOutcomeV1
CustomerEngagementProgressV1
EndConversationChannelSessionRequestV1
EngagementNextActionV1
EngagementProgressItemV1
EngagementSourceProvenanceV1
EngagementTruthDimensionsV1
PaneVisibilityV1
RelationshipWorkspacePreferencesV1
ReplaceRelationshipWorkspacePreferencesRequestV1
ReplaceWorkspaceLayoutPreferencesRequestV1
ResolveWorkspaceFocusRequestV1
WorkspaceFocusRefV1
WorkspaceFocusResolutionV1
WorkspaceLayoutPreferencesV1
"

chmod 0666 "$SLICE_PATH"

cleanup() {
  rm -f "$SLICE_PATH"
  rm -rf "$STAGING_PATH"
}
trap cleanup EXIT HUP INT TERM

cd "$REPOSITORY_ROOT"
docker compose --profile test run --rm --no-deps \
  --volume "$SLICE_PATH:/tmp/web-openapi.yaml" \
  test-runner \
  python3 scripts/openapi_slice.py \
  --input architecture/reference/api-specs/business-platform.openapi.yaml \
  --output /tmp/web-openapi.yaml \
  --tag Identity \
  --tag Billing \
  --tag Configuration \
  --tag Conversation \
  --tag Employment \
  --tag Notifications \
  --tag Professionals \
  --tag "Relationship Workspace" \
  --tag "Voice Contributions" \
  --schema EmploymentRelationship \
  --schema RelationshipTimelineEntry \
  --schema BillingAllowanceSummaryV1 \
  --schema BillingLineItem \
  --schema BillingPortalSummaryV1 \
  --schema BillingStatement \
  --schema ConversationalConfigRequest \
  --schema ConversationalConfigResponse \
  --schema CreateSubscriptionRequest \
  --schema DigitalMarketingPhaseBundle \
  --schema EmploymentContractPage \
  --schema GstInvoiceSummary \
  --schema LegacyEmploymentRelationshipAdapterResponse \
  --schema LegacyFormEmploymentContractRequest \
  --schema LegacyHireAgentRequest \
  --schema LegacyHireAgentResponse \
  --schema PhaseBundleSubscription \
  --schema SubscriptionCreated \
  --schema SubscriptionTier \
  --schema TerminateContractRequest

rm -rf "$STAGING_PATH"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "$REPOSITORY_ROOT:/local" \
  "$GENERATOR_IMAGE" generate \
  --input-spec "$CONTAINER_SLICE_PATH" \
  --generator-name typescript-fetch \
  --output /local/web/lib/api/generated.next \
  --global-property "apis=Billing:Configuration:Conversation:Employment:Identity:Notifications:Professionals:RelationshipWorkspace:VoiceContributions,models,supportingFiles=runtime.ts:models/index.ts:index.ts" \
  --additional-properties supportsES6=true,typescriptThreePlus=true,useSingleRequestParameter=true,hideGenerationTimestamp=true

docker compose --profile test-ts run --rm --no-deps \
  --volume "$STAGING_PATH:/workspace/web/lib/api/generated" \
  test-runner-ts \
  sh -lc 'cd /workspace/web && node scripts/normalize-generated-api.mjs && pnpm exec prettier --write lib/api/generated'

for api in $GENERATED_APIS; do
  cp -a "$STAGING_PATH/apis/$api.ts" "$OUTPUT_PATH/apis/$api.ts"
  cp -a "$STAGING_PATH/docs/$api.md" "$OUTPUT_PATH/docs/$api.md"
done
sed -i \
  's/AdmitEmploymentRelationshipOperationRequest/AdmitCustomerEngagementRelationshipOperationRequest/g' \
  "$OUTPUT_PATH/apis/RelationshipWorkspaceApi.ts"
for model in $GENERATED_MODELS; do
  cp -a "$STAGING_PATH/models/$model.ts" "$OUTPUT_PATH/models/$model.ts"
  if [ -f "$STAGING_PATH/docs/$model.md" ]; then
    cp -a "$STAGING_PATH/docs/$model.md" "$OUTPUT_PATH/docs/$model.md"
  fi
  if ! grep -q "\"./$model\"" "$OUTPUT_PATH/models/index.ts"; then
    printf 'export * from "./%s";\n' "$model" >>"$OUTPUT_PATH/models/index.ts"
  fi
done

docker compose --profile test-ts run --rm --no-deps \
  --volume "$OUTPUT_PATH:/workspace/web/lib/api/generated" \
  test-runner-ts \
  sh -lc 'cd /workspace/web && pnpm exec prettier --write lib/api/generated/models/index.ts'