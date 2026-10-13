# @waooaw/conversation-client@1.0.0-candidate.2

A TypeScript SDK client for the api.waooaw.com API.

## Usage

First, install the SDK from npm.

```bash
npm install @waooaw/conversation-client --save
```

Next, try it out.


```ts
import {
  Configuration,
  ChannelHandoffApi,
} from '@waooaw/conversation-client';
import type { ActivateConversationHandoffRequest } from '@waooaw/conversation-client';

async function example() {
  console.log("🚀 Testing @waooaw/conversation-client SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChannelHandoffApi(config);

  const body = {
    // string
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    handoffId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    xCorrelationID: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // HandoffActivateRequestV1
    handoffActivateRequestV1: ...,
  } satisfies ActivateConversationHandoffRequest;

  try {
    const data = await api.activateConversationHandoff(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```


## Documentation

### API Endpoints

All URIs are relative to *https://api.waooaw.com*

| Class | Method | HTTP request | Description
| ----- | ------ | ------------ | -------------
*ChannelHandoffApi* | [**activateConversationHandoff**](docs/ChannelHandoffApi.md#activateconversationhandoff) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/handoffs/{handoffId}/activate | Activate a prepared handoff after fresh target authentication
*ChannelHandoffApi* | [**prepareConversationHandoff**](docs/ChannelHandoffApi.md#prepareconversationhandoff) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/handoffs | Prepare a short-lived target-channel handoff
*ChannelHandoffApi* | [**revertConversationHandoff**](docs/ChannelHandoffApi.md#revertconversationhandoff) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/handoffs/{handoffId}/revert | Idempotently revert a prepared or uncertain handoff to its source binding
*ContextAndProfileApi* | [**correctConversationContextProfile**](docs/ContextAndProfileApi.md#correctconversationcontextprofile) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/profile/corrections | Append a correction or dispute without overwriting source observations
*ContextAndProfileApi* | [**getConversationContextProfile**](docs/ContextAndProfileApi.md#getconversationcontextprofile) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/profile | Read the authorized current context profile and lineage references
*ContextAndProfileApi* | [**listAvailableInteractionContexts**](docs/ContextAndProfileApi.md#listavailableinteractioncontexts) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/contexts | List server-authorized registered contexts and commands
*DataRightsApi* | [**requestConversationDataRight**](docs/DataRightsApi.md#requestconversationdataright) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/data-rights | Request authorized export, correction, or erasure processing
*SharedConversationApi* | [**getCanonicalConversation**](docs/SharedConversationApi.md#getcanonicalconversation) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation | Read the canonical relationship conversation and exact current references
*SharedConversationApi* | [**getConversationMessageStates**](docs/SharedConversationApi.md#getconversationmessagestates) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/states | Inspect independent delivery, execution, customer-decision, and evidence states
*SharedConversationApi* | [**getConversationOperation**](docs/SharedConversationApi.md#getconversationoperation) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/operations/{operationId} | Reconcile one durable contribution, command, cancellation, handoff, or rights request
*SharedConversationApi* | [**requestConversationCancellation**](docs/SharedConversationApi.md#requestconversationcancellation) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/cancellations | Request cancellation without deleting canonical history
*SharedConversationApi* | [**streamCanonicalConversationEvents**](docs/SharedConversationApi.md#streamcanonicalconversationevents) | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/events | Stream canonical events after an authorized sequence cursor
*SharedConversationApi* | [**submitConversationCommand**](docs/SharedConversationApi.md#submitconversationcommand) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/commands | Submit or replay one registered typed command
*SharedConversationApi* | [**submitConversationContribution**](docs/SharedConversationApi.md#submitconversationcontribution) | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/contributions | Submit or replay a text or reviewed voice contribution
*SharedConversationApi* | [**updateConversationReadPosition**](docs/SharedConversationApi.md#updateconversationreadposition) | **PUT** /api/v1/employment/relationships/{relationshipId}/conversation/read-position | Monotonically advance the authenticated participant\&#39;s durable read position
*WhatsAppProviderCallbackApi* | [**acceptWhatsAppWebhook**](docs/WhatsAppProviderCallbackApi.md#acceptwhatsappwebhook) | **POST** /api/v1/channels/whatsapp/webhook | Verify exact raw bytes and durably accept or replay a provider event
*WhatsAppProviderCallbackApi* | [**verifyWhatsAppWebhook**](docs/WhatsAppProviderCallbackApi.md#verifywhatsappwebhook) | **GET** /api/v1/channels/whatsapp/webhook | Complete exact environment-bound Meta subscription challenge


### Models

- [AcceptPlanVersionCommandV1](docs/AcceptPlanVersionCommandV1.md)
- [AcknowledgeCorrectiveProposalCommandV1](docs/AcknowledgeCorrectiveProposalCommandV1.md)
- [AcknowledgeMaterialChangeCommandV1](docs/AcknowledgeMaterialChangeCommandV1.md)
- [ApplyCandidatePatchCommandV1](docs/ApplyCandidatePatchCommandV1.md)
- [AvailableCommandV1](docs/AvailableCommandV1.md)
- [AvailableInteractionContextV1](docs/AvailableInteractionContextV1.md)
- [BlockedEffectV1](docs/BlockedEffectV1.md)
- [CalendarCommitmentV1](docs/CalendarCommitmentV1.md)
- [CalendarTolerancePolicyRefV1](docs/CalendarTolerancePolicyRefV1.md)
- [CancellationRequestV1](docs/CancellationRequestV1.md)
- [CanonicalConversationV1](docs/CanonicalConversationV1.md)
- [CanonicalMessageV1](docs/CanonicalMessageV1.md)
- [ChannelKind](docs/ChannelKind.md)
- [ConfirmInductionItemCommandV1](docs/ConfirmInductionItemCommandV1.md)
- [ContextCorrectionRequestV1](docs/ContextCorrectionRequestV1.md)
- [ContextFreshness](docs/ContextFreshness.md)
- [ContextProfileItemV1](docs/ContextProfileItemV1.md)
- [ContextProfileV1](docs/ContextProfileV1.md)
- [ConversationContributionRequestV1](docs/ConversationContributionRequestV1.md)
- [ConversationOperationOutcomeV1](docs/ConversationOperationOutcomeV1.md)
- [ConversationOperationReceiptV1](docs/ConversationOperationReceiptV1.md)
- [ConversationPolicyReferenceV1](docs/ConversationPolicyReferenceV1.md)
- [ConversationProblemV1](docs/ConversationProblemV1.md)
- [ConversationReadPositionV1](docs/ConversationReadPositionV1.md)
- [ConversationStateDimensionsV1](docs/ConversationStateDimensionsV1.md)
- [DataRightRequestV1](docs/DataRightRequestV1.md)
- [DeferInductionItemCommandV1](docs/DeferInductionItemCommandV1.md)
- [EmploymentCommandKind](docs/EmploymentCommandKind.md)
- [EmploymentCommandOutcomeV1](docs/EmploymentCommandOutcomeV1.md)
- [EmploymentCommandOutcomeV1AllOfResultingVersions](docs/EmploymentCommandOutcomeV1AllOfResultingVersions.md)
- [EmploymentCommandReceiptV1](docs/EmploymentCommandReceiptV1.md)
- [EmploymentCommandRequestV1](docs/EmploymentCommandRequestV1.md)
- [EmploymentCommandState](docs/EmploymentCommandState.md)
- [EmploymentItemState](docs/EmploymentItemState.md)
- [EmploymentOperationMode](docs/EmploymentOperationMode.md)
- [EmploymentOperationsV1](docs/EmploymentOperationsV1.md)
- [EmploymentPhaseKind](docs/EmploymentPhaseKind.md)
- [EmploymentPhaseOwnerSummaryV1](docs/EmploymentPhaseOwnerSummaryV1.md)
- [EmploymentPhaseV1](docs/EmploymentPhaseV1.md)
- [EmploymentPlanV1](docs/EmploymentPlanV1.md)
- [EmploymentProblemCode](docs/EmploymentProblemCode.md)
- [EmploymentProblemDetailV1](docs/EmploymentProblemDetailV1.md)
- [EmploymentReadinessV1](docs/EmploymentReadinessV1.md)
- [EmploymentSchemaVersion](docs/EmploymentSchemaVersion.md)
- [EmploymentSourceV1](docs/EmploymentSourceV1.md)
- [EmploymentWorkspaceItemV1](docs/EmploymentWorkspaceItemV1.md)
- [EmploymentWorkspaceV1](docs/EmploymentWorkspaceV1.md)
- [HandoffActivateRequestV1](docs/HandoffActivateRequestV1.md)
- [HandoffPrepareRequestV1](docs/HandoffPrepareRequestV1.md)
- [HandoffReceiptV1](docs/HandoffReceiptV1.md)
- [HandoffRevertRequestV1](docs/HandoffRevertRequestV1.md)
- [InductionReadinessState](docs/InductionReadinessState.md)
- [InteractionContextV1](docs/InteractionContextV1.md)
- [OperationsEligibilityState](docs/OperationsEligibilityState.md)
- [OwnerStepV1](docs/OwnerStepV1.md)
- [PerformanceAssuranceState](docs/PerformanceAssuranceState.md)
- [PlanReadinessState](docs/PlanReadinessState.md)
- [PlanState](docs/PlanState.md)
- [RegisteredCommandDescriptorV1](docs/RegisteredCommandDescriptorV1.md)
- [RegisteredContextHintV1](docs/RegisteredContextHintV1.md)
- [RequestReassessmentCommandV1](docs/RequestReassessmentCommandV1.md)
- [RequirementProgressV1](docs/RequirementProgressV1.md)
- [RescheduleWithinToleranceCommandV1](docs/RescheduleWithinToleranceCommandV1.md)
- [ReviewedVoiceConversationContributionRequestV1](docs/ReviewedVoiceConversationContributionRequestV1.md)
- [SourceState](docs/SourceState.md)
- [SourceVersionV1](docs/SourceVersionV1.md)
- [SubmitPlanForReviewCommandV1](docs/SubmitPlanForReviewCommandV1.md)
- [TextConversationContributionRequestV1](docs/TextConversationContributionRequestV1.md)
- [UpdateConversationReadPositionRequestV1](docs/UpdateConversationReadPositionRequestV1.md)

### Authorization


Authentication schemes defined for the API:
<a id="BearerAuth"></a>
#### BearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)

## About

This TypeScript SDK client supports the [Fetch API](https://fetch.spec.whatwg.org/)
and is automatically generated by the
[OpenAPI Generator](https://openapi-generator.tech) project:

- API version: `1.0.0-candidate.2`
- Package version: `1.0.0-candidate.2`
- Generator version: `7.17.0`
- Build package: `org.openapitools.codegen.languages.TypeScriptFetchClientCodegen`

The generated npm module supports the following:

- Environments
  * Node.js
  * Webpack
  * Browserify
- Language levels
  * ES5 - you must have a Promises/A+ library installed
  * ES6
- Module systems
  * CommonJS
  * ES6 module system


## Development

### Building

To build the TypeScript source code, you need to have Node.js and npm installed.
After cloning the repository, navigate to the project directory and run:

```bash
npm install
npm run build
```

### Publishing

Once you've built the package, you can publish it to npm:

```bash
npm publish
```

## License

[]()
