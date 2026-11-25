# @waooaw/workbench-client@1.0.0

A TypeScript SDK client for the api.waooaw.com API.

## Usage

First, install the SDK from npm.

```bash
npm install @waooaw/workbench-client --save
```

Next, try it out.


```ts
import {
  Configuration,
  MarketplacePackagesApi,
} from '@waooaw/workbench-client';
import type { ListMarketplaceAgentPackagesRequest } from '@waooaw/workbench-client';

async function example() {
  console.log("🚀 Testing @waooaw/workbench-client SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new MarketplacePackagesApi(config);

  const body = {
    // string
    agentType: agentType_example,
    // string
    agentVersion: agentVersion_example,
    // string | Opaque cursor from the previous page. (optional)
    cursor: cursor_example,
    // number (optional)
    limit: 56,
    // string (optional)
    xCorrelationID: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies ListMarketplaceAgentPackagesRequest;

  try {
    const data = await api.listMarketplaceAgentPackages(body);
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
*MarketplacePackagesApi* | [**listMarketplaceAgentPackages**](docs/MarketplacePackagesApi.md#listmarketplaceagentpackages) | **GET** /api/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages | List the packages on sale for an agent version
*SubscriptionApi* | [**changeSubscription**](docs/SubscriptionApi.md#changesubscription) | **POST** /api/v1/employment/relationships/{relationshipId}/subscription/changes | Change the subscription
*WorkbenchApi* | [**acceptWorkbenchPlan**](docs/WorkbenchApi.md#acceptworkbenchplan) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/plans/{planVersion}/accept | Accept a plan version
*WorkbenchApi* | [**commandWorkbenchCapability**](docs/WorkbenchApi.md#commandworkbenchcapability) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/capabilities/{skillId}/commands | Command one capability
*WorkbenchApi* | [**consumeWorkbenchHandoff**](docs/WorkbenchApi.md#consumeworkbenchhandoff) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/handoffs/consume | Redeem a single-use handoff
*WorkbenchApi* | [**createWorkbenchGoal**](docs/WorkbenchApi.md#createworkbenchgoal) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/goals | Create a goal
*WorkbenchApi* | [**createWorkbenchHandoff**](docs/WorkbenchApi.md#createworkbenchhandoff) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/handoffs | Create a single-use handoff to the web workbench
*WorkbenchApi* | [**createWorkbenchTopup**](docs/WorkbenchApi.md#createworkbenchtopup) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/topups | Top up one component
*WorkbenchApi* | [**exportWorkbenchEvidence**](docs/WorkbenchApi.md#exportworkbenchevidence) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/evidence/exports | Request an evidence export
*WorkbenchApi* | [**getCurrentWorkbenchPlan**](docs/WorkbenchApi.md#getcurrentworkbenchplan) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/plans/current | Read the current plan
*WorkbenchApi* | [**getWorkbench**](docs/WorkbenchApi.md#getworkbench) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench | Read the workbench projection
*WorkbenchApi* | [**getWorkbenchGoal**](docs/WorkbenchApi.md#getworkbenchgoal) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/goals/{goalId} | Read one goal
*WorkbenchApi* | [**getWorkbenchMonitor**](docs/WorkbenchApi.md#getworkbenchmonitor) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/monitor | Read the monitor
*WorkbenchApi* | [**getWorkbenchWallet**](docs/WorkbenchApi.md#getworkbenchwallet) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/wallet | Read the component wallet
*WorkbenchApi* | [**listWorkbenchCapabilities**](docs/WorkbenchApi.md#listworkbenchcapabilities) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/capabilities | List the capabilities of the agent
*WorkbenchApi* | [**listWorkbenchDecisions**](docs/WorkbenchApi.md#listworkbenchdecisions) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/decisions | List pending decisions
*WorkbenchApi* | [**listWorkbenchEvidence**](docs/WorkbenchApi.md#listworkbenchevidence) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/evidence | List evidence
*WorkbenchApi* | [**listWorkbenchGoalVersions**](docs/WorkbenchApi.md#listworkbenchgoalversions) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/goals/{goalId}/versions | List the versions of a goal
*WorkbenchApi* | [**listWorkbenchGoals**](docs/WorkbenchApi.md#listworkbenchgoals) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/goals | List goals
*WorkbenchApi* | [**listWorkbenchNarratives**](docs/WorkbenchApi.md#listworkbenchnarratives) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/monitor/narratives | List performance narratives
*WorkbenchApi* | [**listWorkbenchWorkItems**](docs/WorkbenchApi.md#listworkbenchworkitems) | **GET** /api/v1/employment/relationships/{relationshipId}/workbench/work-items | List work items
*WorkbenchApi* | [**pauseWorkbenchRelationship**](docs/WorkbenchApi.md#pauseworkbenchrelationship) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/controls/pause | Pause the relationship
*WorkbenchApi* | [**proposeWorkbenchPlan**](docs/WorkbenchApi.md#proposeworkbenchplan) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/plans | Propose a plan
*WorkbenchApi* | [**resolveWorkbenchDecision**](docs/WorkbenchApi.md#resolveworkbenchdecision) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/decisions/{decisionId}/resolve | Resolve a decision
*WorkbenchApi* | [**reviseWorkbenchGoal**](docs/WorkbenchApi.md#reviseworkbenchgoal) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/goals/{goalId}/revisions | Revise a goal
*WorkbenchApi* | [**stopWorkbenchRelationship**](docs/WorkbenchApi.md#stopworkbenchrelationship) | **POST** /api/v1/employment/relationships/{relationshipId}/workbench/controls/stop | Stop the relationship now


### Models

- [AcceptWorkbenchPlanRequestV1](docs/AcceptWorkbenchPlanRequestV1.md)
- [ConsumeWorkbenchHandoffRequestV1](docs/ConsumeWorkbenchHandoffRequestV1.md)
- [CreateWorkbenchGoalRequestV1](docs/CreateWorkbenchGoalRequestV1.md)
- [CreateWorkbenchHandoffRequestV1](docs/CreateWorkbenchHandoffRequestV1.md)
- [CreateWorkbenchTopupRequestV1](docs/CreateWorkbenchTopupRequestV1.md)
- [EmploymentItemState](docs/EmploymentItemState.md)
- [EmploymentPhaseKind](docs/EmploymentPhaseKind.md)
- [ExperienceBlockV2](docs/ExperienceBlockV2.md)
- [ExperienceFallbackBlockV2](docs/ExperienceFallbackBlockV2.md)
- [ExportWorkbenchEvidenceRequestV1](docs/ExportWorkbenchEvidenceRequestV1.md)
- [InductionReadinessState](docs/InductionReadinessState.md)
- [MarketplacePackageComponentV1](docs/MarketplacePackageComponentV1.md)
- [MarketplacePackageListV1](docs/MarketplacePackageListV1.md)
- [MarketplacePackageV1](docs/MarketplacePackageV1.md)
- [OperationsEligibilityState](docs/OperationsEligibilityState.md)
- [PerformanceAssuranceState](docs/PerformanceAssuranceState.md)
- [PlanReadinessState](docs/PlanReadinessState.md)
- [ProjectionEvidenceStateV1](docs/ProjectionEvidenceStateV1.md)
- [ProjectionFreshnessV1](docs/ProjectionFreshnessV1.md)
- [ProposeWorkbenchPlanRequestV1](docs/ProposeWorkbenchPlanRequestV1.md)
- [ProposeWorkbenchPlanRequestV1MilestonesInner](docs/ProposeWorkbenchPlanRequestV1MilestonesInner.md)
- [ResolveWorkbenchDecisionRequestV1](docs/ResolveWorkbenchDecisionRequestV1.md)
- [ReviseWorkbenchGoalRequestV1](docs/ReviseWorkbenchGoalRequestV1.md)
- [SubscriptionChangeReceiptV1](docs/SubscriptionChangeReceiptV1.md)
- [SubscriptionChangeRequestV1](docs/SubscriptionChangeRequestV1.md)
- [SubscriptionChangeRequestV1SelectionsInner](docs/SubscriptionChangeRequestV1SelectionsInner.md)
- [WorkbenchAlertV1](docs/WorkbenchAlertV1.md)
- [WorkbenchAudienceV1](docs/WorkbenchAudienceV1.md)
- [WorkbenchAvailableCommandV1](docs/WorkbenchAvailableCommandV1.md)
- [WorkbenchCalendarEntryV1](docs/WorkbenchCalendarEntryV1.md)
- [WorkbenchCapabilityCommandRequestV1](docs/WorkbenchCapabilityCommandRequestV1.md)
- [WorkbenchCapabilityCommandResultV1](docs/WorkbenchCapabilityCommandResultV1.md)
- [WorkbenchCapabilityListV1](docs/WorkbenchCapabilityListV1.md)
- [WorkbenchCapabilityV1](docs/WorkbenchCapabilityV1.md)
- [WorkbenchCommandReceiptV1](docs/WorkbenchCommandReceiptV1.md)
- [WorkbenchComponentBalanceV1](docs/WorkbenchComponentBalanceV1.md)
- [WorkbenchControlRequestV1](docs/WorkbenchControlRequestV1.md)
- [WorkbenchDecisionListV1](docs/WorkbenchDecisionListV1.md)
- [WorkbenchDecisionV1](docs/WorkbenchDecisionV1.md)
- [WorkbenchEvidenceEntryV1](docs/WorkbenchEvidenceEntryV1.md)
- [WorkbenchEvidenceListV1](docs/WorkbenchEvidenceListV1.md)
- [WorkbenchGoalListV1](docs/WorkbenchGoalListV1.md)
- [WorkbenchGoalMeasureV1](docs/WorkbenchGoalMeasureV1.md)
- [WorkbenchGoalSummaryV1](docs/WorkbenchGoalSummaryV1.md)
- [WorkbenchGoalV1](docs/WorkbenchGoalV1.md)
- [WorkbenchGoalVersionListV1](docs/WorkbenchGoalVersionListV1.md)
- [WorkbenchGoalVersionV1](docs/WorkbenchGoalVersionV1.md)
- [WorkbenchHandoffConsumptionV1](docs/WorkbenchHandoffConsumptionV1.md)
- [WorkbenchHandoffV1](docs/WorkbenchHandoffV1.md)
- [WorkbenchMilestoneV1](docs/WorkbenchMilestoneV1.md)
- [WorkbenchMonitorV1](docs/WorkbenchMonitorV1.md)
- [WorkbenchNarrativeListV1](docs/WorkbenchNarrativeListV1.md)
- [WorkbenchNarrativePartV1](docs/WorkbenchNarrativePartV1.md)
- [WorkbenchNarrativeV1](docs/WorkbenchNarrativeV1.md)
- [WorkbenchNavigationEntryV1](docs/WorkbenchNavigationEntryV1.md)
- [WorkbenchPlanV1](docs/WorkbenchPlanV1.md)
- [WorkbenchProblemCodeV1](docs/WorkbenchProblemCodeV1.md)
- [WorkbenchProblemDetailV1](docs/WorkbenchProblemDetailV1.md)
- [WorkbenchProjectionV1](docs/WorkbenchProjectionV1.md)
- [WorkbenchReadinessV1](docs/WorkbenchReadinessV1.md)
- [WorkbenchRecommendedActionV1](docs/WorkbenchRecommendedActionV1.md)
- [WorkbenchTileV1](docs/WorkbenchTileV1.md)
- [WorkbenchTopupReceiptV1](docs/WorkbenchTopupReceiptV1.md)
- [WorkbenchWalletV1](docs/WorkbenchWalletV1.md)
- [WorkbenchWorkItemListV1](docs/WorkbenchWorkItemListV1.md)
- [WorkbenchWorkItemV1](docs/WorkbenchWorkItemV1.md)

### Authorization


Authentication schemes defined for the API:
<a id="bearerAuth"></a>
#### bearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)

## About

This TypeScript SDK client supports the [Fetch API](https://fetch.spec.whatwg.org/)
and is automatically generated by the
[OpenAPI Generator](https://openapi-generator.tech) project:

- API version: `1.0.0`
- Package version: `1.0.0`
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
