# @waooaw/employment-client@1.0.0-candidate.2

A TypeScript SDK client for the api.waooaw.com API.

## Usage

First, install the SDK from npm.

```bash
npm install @waooaw/employment-client --save
```

Next, try it out.


```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentCommandRequest } from '@waooaw/employment-client';

async function example() {
  console.log("🚀 Testing @waooaw/employment-client SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationalEmploymentApi(config);

  const body = {
    // string
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    commandId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetEmploymentCommandRequest;

  try {
    const data = await api.getEmploymentCommand(body);
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
*ConversationalEmploymentApi* | [**getEmploymentCommand**](docs/ConversationalEmploymentApi.md#getemploymentcommand) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/commands/{commandId} | Reconcile one command by its durable BP identity
*ConversationalEmploymentApi* | [**getEmploymentPhase**](docs/ConversationalEmploymentApi.md#getemploymentphase) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/phases/{phase} | Read one phase with requirement-derived progress
*ConversationalEmploymentApi* | [**getEmploymentPlan**](docs/ConversationalEmploymentApi.md#getemploymentplan) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/plans/current | Read the current plan version
*ConversationalEmploymentApi* | [**getEmploymentPlanVersion**](docs/ConversationalEmploymentApi.md#getemploymentplanversion) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/plans/{planVersion} | Read one immutable plan version
*ConversationalEmploymentApi* | [**getEmploymentReadiness**](docs/ConversationalEmploymentApi.md#getemploymentreadiness) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/readiness | Read all independent readiness facets
*ConversationalEmploymentApi* | [**getEmploymentWorkspace**](docs/ConversationalEmploymentApi.md#getemploymentworkspace) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment | Read the complete conversational employment projection
*ConversationalEmploymentApi* | [**submitEmploymentCommand**](docs/ConversationalEmploymentApi.md#submitemploymentcommand) | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/employment/commands | Submit or replay one closed typed employment command


### Models

- [AcceptPlanVersionCommandV1](docs/AcceptPlanVersionCommandV1.md)
- [AcknowledgeCorrectiveProposalCommandV1](docs/AcknowledgeCorrectiveProposalCommandV1.md)
- [AcknowledgeMaterialChangeCommandV1](docs/AcknowledgeMaterialChangeCommandV1.md)
- [ApplyCandidatePatchCommandV1](docs/ApplyCandidatePatchCommandV1.md)
- [AvailableCommandV1](docs/AvailableCommandV1.md)
- [BlockedEffectV1](docs/BlockedEffectV1.md)
- [CalendarCommitmentV1](docs/CalendarCommitmentV1.md)
- [CalendarTolerancePolicyRefV1](docs/CalendarTolerancePolicyRefV1.md)
- [ConfirmInductionItemCommandV1](docs/ConfirmInductionItemCommandV1.md)
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
- [InductionReadinessState](docs/InductionReadinessState.md)
- [InlineObject](docs/InlineObject.md)
- [OperationsEligibilityState](docs/OperationsEligibilityState.md)
- [OwnerStepV1](docs/OwnerStepV1.md)
- [PerformanceAssuranceState](docs/PerformanceAssuranceState.md)
- [PlanReadinessState](docs/PlanReadinessState.md)
- [PlanState](docs/PlanState.md)
- [RequestReassessmentCommandV1](docs/RequestReassessmentCommandV1.md)
- [RequirementProgressV1](docs/RequirementProgressV1.md)
- [RescheduleWithinToleranceCommandV1](docs/RescheduleWithinToleranceCommandV1.md)
- [SourceState](docs/SourceState.md)
- [SubmitPlanForReviewCommandV1](docs/SubmitPlanForReviewCommandV1.md)

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
