# RelationshipWorkspaceApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                                             | HTTP request                                                                                    | Description                                                            |
| ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [**admitEmploymentRelationship**](RelationshipWorkspaceApi.md#admitemploymentrelationshipoperation)                | **POST** /api/v1/employment/relationships                                                       | Admit or replay an employment relationship                             |
| [**getCustomerEngagementProgress**](RelationshipWorkspaceApi.md#getcustomerengagementprogress)                     | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/engagement-progress         | Get owner-composed customer engagement progress                        |
| [**getRelationshipAttention**](RelationshipWorkspaceApi.md#getrelationshipattention)                               | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/attention                   | Read authoritative needs-your-attention items in BP-owned order        |
| [**getRelationshipBusinessOutcomes**](RelationshipWorkspaceApi.md#getrelationshipbusinessoutcomes)                 | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/business-outcomes           | Read relationship business outcomes with explicit traceability         |
| [**getRelationshipCommand**](RelationshipWorkspaceApi.md#getrelationshipcommand)                                   | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/commands/{commandId}        | Reconcile one command to an authoritative outcome                      |
| [**getRelationshipEvaluation**](RelationshipWorkspaceApi.md#getrelationshipevaluation)                             | **GET** /api/v1/employment/relationships/{relationshipId}/evaluation                            | Read the authoritative relationship evaluation and skill configuration |
| [**getRelationshipEvidence**](RelationshipWorkspaceApi.md#getrelationshipevidence)                                 | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence/{evidenceId}       | Read one relationship-authorized evidence detail projection            |
| [**getRelationshipEvidenceExport**](RelationshipWorkspaceApi.md#getrelationshipevidenceexport)                     | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports/{exportId} | Reconcile one relationship evidence export request                     |
| [**getRelationshipGoals**](RelationshipWorkspaceApi.md#getrelationshipgoals)                                       | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/goals                       | Read active and historical relationship goals                          |
| [**getRelationshipOperations**](RelationshipWorkspaceApi.md#getrelationshipoperations)                             | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/operations                  | Read Operations eligibility and reassessment state                     |
| [**getRelationshipPerformance**](RelationshipWorkspaceApi.md#getrelationshipperformance)                           | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/performance                 | Read immutable relationship performance reviews                        |
| [**getRelationshipPlan**](RelationshipWorkspaceApi.md#getrelationshipplan)                                         | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/plan                        | Read relationship plan, goals, and available typed commands            |
| [**getRelationshipResults**](RelationshipWorkspaceApi.md#getrelationshipresults)                                   | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/results                     | Read relationship business outcomes and attribution context            |
| [**getRelationshipRightsControls**](RelationshipWorkspaceApi.md#getrelationshiprightscontrols)                     | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/rights-controls             | Read relationship rights, scope, authority, and lifecycle controls     |
| [**getRelationshipUsageBudget**](RelationshipWorkspaceApi.md#getrelationshipusagebudget)                           | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/usage-budget                | Read WBE-authoritative usage and budget projection relayed by BP       |
| [**getRelationshipWork**](RelationshipWorkspaceApi.md#getrelationshipwork)                                         | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/work                        | Read relationship work and deliverable status                          |
| [**getRelationshipWorkspace**](RelationshipWorkspaceApi.md#getrelationshipworkspace)                               | **GET** /api/v1/employment/relationships/{relationshipId}/workspace                             | Read the complete relationship workspace projection                    |
| [**getRelationshipWorkspaceChanges**](RelationshipWorkspaceApi.md#getrelationshipworkspacechanges)                 | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/changes                     | Read incremental workspace changes after an authoritative cursor       |
| [**getRelationshipWorkspacePreferences**](RelationshipWorkspaceApi.md#getrelationshipworkspacepreferences)         | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/preferences                 | Get relationship-specific presentation preferences                     |
| [**listRelationshipEvidence**](RelationshipWorkspaceApi.md#listrelationshipevidence)                               | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence                    | List relationship-authorized evidence summaries                        |
| [**replaceRelationshipWorkspacePreferences**](RelationshipWorkspaceApi.md#replacerelationshipworkspacepreferences) | **PUT** /api/v1/employment/relationships/{relationshipId}/workspace/preferences                 | Replace relationship-specific presentation preferences                 |
| [**requestRelationshipEvidenceExport**](RelationshipWorkspaceApi.md#requestrelationshipevidenceexport)             | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports           | Request or replay one relationship evidence export                     |
| [**resolveWorkspaceFocus**](RelationshipWorkspaceApi.md#resolveworkspacefocus)                                     | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/focus-resolutions          | Resolve a protected short-lived workspace focus reference              |
| [**submitRelationshipCommand**](RelationshipWorkspaceApi.md#submitrelationshipcommand)                             | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/commands                   | Submit or replay a typed relationship command                          |

## admitEmploymentRelationship

> AdmitEmploymentRelationship201Response admitEmploymentRelationship(admitEmploymentRelationshipRequest, idempotencyKey)

Admit or replay an employment relationship

Mints the tenant\&#39;s durable employment relationship for the authenticated participant, canonical evaluation intent, and exact active professional admission. Replaying the same participant, professional type, version, and evaluation intent returns the existing relationship and immutable agent instance. Constitutional validation and evidence commitment complete before persistence.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { AdmitEmploymentRelationshipOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // AdmitEmploymentRelationshipRequest
    admitEmploymentRelationshipRequest: ...,
    // string | Required for the customer-engagement admission shape; omitted only by legacy callers. (optional)
    idempotencyKey: idempotencyKey_example,
  } satisfies AdmitEmploymentRelationshipOperationRequest;

  try {
    const data = await api.admitEmploymentRelationship(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                   | Type                                                                        | Description                                                                           | Notes                                |
| -------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------ |
| **admitEmploymentRelationshipRequest** | [AdmitEmploymentRelationshipRequest](AdmitEmploymentRelationshipRequest.md) |                                                                                       |                                      |
| **idempotencyKey**                     | `string`                                                                    | Required for the customer-engagement admission shape; omitted only by legacy callers. | [Optional] [Defaults to `undefined`] |

### Return type

[**AdmitEmploymentRelationship201Response**](AdmitEmploymentRelationship201Response.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                         | Response headers |
| ----------- | --------------------------------------------------------------------------------------------------- | ---------------- |
| **415**     | Request content type is not supported                                                               | -                |
| **201**     | Relationship admitted                                                                               | -                |
| **200**     | Existing relationship returned for an idempotent replay                                             | -                |
| **400**     | Request body failed validation                                                                      | -                |
| **401**     | JWT missing, expired, or invalid                                                                    | -                |
| **403**     | Authenticated identity lacks tenant or participant authority                                        | -                |
| **409**     | Professional admission is inactive, mismatched, or conflicts with the existing relationship binding | -                |
| **503**     | Constitutional validation or evidence commitment is unavailable                                     | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getCustomerEngagementProgress

> CustomerEngagementProgressV1 getCustomerEngagementProgress(relationshipId)

Get owner-composed customer engagement progress

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetCustomerEngagementProgressRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetCustomerEngagementProgressRequest;

  try {
    const data = await api.getCustomerEngagementProgress(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**CustomerEngagementProgressV1**](CustomerEngagementProgressV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                  | Response headers |
| ----------- | ---------------------------------------------------------------------------- | ---------------- |
| **200**     | Current progress with truth dimensions, provenance, and server-ranked action | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant      | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipAttention

> RelationshipAttentionPageV1 getRelationshipAttention(relationshipId, limit)

Read authoritative needs-your-attention items in BP-owned order

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipAttentionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // number (optional)
    limit: 56,
  } satisfies GetRelationshipAttentionRequest;

  try {
    const data = await api.getRelationshipAttention(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                         |
| ------------------ | -------- | -------------------------------------------------- | ----------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`]     |
| **limit**          | `number` |                                                    | [Optional] [Defaults to `50`] |

### Return type

[**RelationshipAttentionPageV1**](RelationshipAttentionPageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Attention items in exact authoritative order                            | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipBusinessOutcomes

> RelationshipBusinessOutcomesV1 getRelationshipBusinessOutcomes(relationshipId)

Read relationship business outcomes with explicit traceability

Returns customer-facing business outcomes traced to skill, goal, measure, review frequency, status, and evidence while separating agent performance from external outcome.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipBusinessOutcomesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipBusinessOutcomesRequest;

  try {
    const data = await api.getRelationshipBusinessOutcomes(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipBusinessOutcomesV1**](RelationshipBusinessOutcomesV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship business outcomes                                          | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipCommand

> RelationshipCommandOutcomeV1 getRelationshipCommand(relationshipId, commandId)

Reconcile one command to an authoritative outcome

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipCommandRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    commandId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipCommandRequest;

  try {
    const data = await api.getRelationshipCommand(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **commandId**      | `string` |                                                    | [Defaults to `undefined`] |

### Return type

[**RelationshipCommandOutcomeV1**](RelationshipCommandOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Command outcome                                                         | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipEvaluation

> RelationshipEvaluationV1 getRelationshipEvaluation(relationshipId)

Read the authoritative relationship evaluation and skill configuration

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipEvaluationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipEvaluationRequest;

  try {
    const data = await api.getRelationshipEvaluation(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipEvaluationV1**](RelationshipEvaluationV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship-local evaluation projection                                | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipEvidence

> RelationshipEvidenceDetailV1 getRelationshipEvidence(relationshipId, evidenceId)

Read one relationship-authorized evidence detail projection

Applies the same participant-role projection and no-existence-disclosure rules as the evidence list. An evidence ID outside the authorized tenant, relationship, or role scope is indistinguishable from an unknown ID. Payload references appear only when the caller\&#39;s role permits them and the tenant-owned payload has not been erased.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipEvidenceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    evidenceId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipEvidenceRequest;

  try {
    const data = await api.getRelationshipEvidence(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **evidenceId**     | `string` |                                                    | [Defaults to `undefined`] |

### Return type

[**RelationshipEvidenceDetailV1**](RelationshipEvidenceDetailV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Evidence detail                                                         | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipEvidenceExport

> RelationshipEvidenceExportOutcomeV1 getRelationshipEvidenceExport(relationshipId, exportId)

Reconcile one relationship evidence export request

Rechecks the current tenant, relationship, participant role, and evidence scope before returning a short-lived authenticated download. Revoked authority, erased payload, or cross-scope export IDs disclose no protected evidence or storage location.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipEvidenceExportRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    exportId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipEvidenceExportRequest;

  try {
    const data = await api.getRelationshipEvidenceExport(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **exportId**       | `string` |                                                    | [Defaults to `undefined`] |

### Return type

[**RelationshipEvidenceExportOutcomeV1**](RelationshipEvidenceExportOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Export outcome                                                          | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipGoals

> RelationshipGoalsV1 getRelationshipGoals(relationshipId)

Read active and historical relationship goals

Returns every active goal with its declared skill, measure, review frequency, explicit customer verification, amendment lineage, and history. Goal mutation continues through the existing typed workspace command contract.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipGoalsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipGoalsRequest;

  try {
    const data = await api.getRelationshipGoals(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipGoalsV1**](RelationshipGoalsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship goals and history                                          | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipOperations

> RelationshipOperationsV1 getRelationshipOperations(relationshipId)

Read Operations eligibility and reassessment state

Returns whether Operations is locked, eligible, active, paused, or blocked based on server-verified goals and dependent work or outcome reassessment state.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipOperationsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipOperationsRequest;

  try {
    const data = await api.getRelationshipOperations(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipOperationsV1**](RelationshipOperationsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship Operations state                                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipPerformance

> RelationshipPerformanceV1 getRelationshipPerformance(relationshipId)

Read immutable relationship performance reviews

Returns current and historical Skill review windows with work delivery, agent quality, constitutional performance, commercial usage, customer business outcome, explicit customer assessment, and relationship-specific trust/autonomy kept as seven separate dimensions.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipPerformanceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipPerformanceRequest;

  try {
    const data = await api.getRelationshipPerformance(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipPerformanceV1**](RelationshipPerformanceV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship performance review projection                              | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipPlan

> RelationshipPlanV1 getRelationshipPlan(relationshipId)

Read relationship plan, goals, and available typed commands

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipPlanRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipPlanRequest;

  try {
    const data = await api.getRelationshipPlan(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipPlanV1**](RelationshipPlanV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship plan section                                               | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipResults

> RelationshipResultsV1 getRelationshipResults(relationshipId)

Read relationship business outcomes and attribution context

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipResultsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipResultsRequest;

  try {
    const data = await api.getRelationshipResults(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipResultsV1**](RelationshipResultsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship results section                                            | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipRightsControls

> RelationshipRightsControlsV1 getRelationshipRightsControls(relationshipId)

Read relationship rights, scope, authority, and lifecycle controls

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipRightsControlsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipRightsControlsRequest;

  try {
    const data = await api.getRelationshipRightsControls(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipRightsControlsV1**](RelationshipRightsControlsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship rights and controls section                                | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipUsageBudget

> RelationshipUsageBudgetV1 getRelationshipUsageBudget(relationshipId)

Read WBE-authoritative usage and budget projection relayed by BP

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipUsageBudgetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipUsageBudgetRequest;

  try {
    const data = await api.getRelationshipUsageBudget(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipUsageBudgetV1**](RelationshipUsageBudgetV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship usage and budget section                                   | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipWork

> RelationshipWorkPageV1 getRelationshipWork(relationshipId)

Read relationship work and deliverable status

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipWorkRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipWorkRequest;

  try {
    const data = await api.getRelationshipWork(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipWorkPageV1**](RelationshipWorkPageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Relationship work section                                               | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipWorkspace

> RelationshipWorkspaceV1 getRelationshipWorkspace(relationshipId)

Read the complete relationship workspace projection

Returns one tenant-authorized, relationship-bound workspace projection. Tenant authority is derived from JWT only; no request field can override it.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipWorkspaceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipWorkspaceRequest;

  try {
    const data = await api.getRelationshipWorkspace(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipWorkspaceV1**](RelationshipWorkspaceV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Workspace projection snapshot                                           | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipWorkspaceChanges

> RelationshipWorkspaceChangePageV1 getRelationshipWorkspaceChanges(relationshipId, afterCursor, limit)

Read incremental workspace changes after an authoritative cursor

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipWorkspaceChangesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    afterCursor: afterCursor_example,
    // number (optional)
    limit: 56,
  } satisfies GetRelationshipWorkspaceChangesRequest;

  try {
    const data = await api.getRelationshipWorkspaceChanges(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                         |
| ------------------ | -------- | -------------------------------------------------- | ----------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`]     |
| **afterCursor**    | `string` |                                                    | [Defaults to `undefined`]     |
| **limit**          | `number` |                                                    | [Optional] [Defaults to `50`] |

### Return type

[**RelationshipWorkspaceChangePageV1**](RelationshipWorkspaceChangePageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Workspace change page                                                   | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **410**     | Workspace cursor expired and a fresh snapshot is required               | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipWorkspacePreferences

> RelationshipWorkspacePreferencesV1 getRelationshipWorkspacePreferences(relationshipId)

Get relationship-specific presentation preferences

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { GetRelationshipWorkspacePreferencesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipWorkspacePreferencesRequest;

  try {
    const data = await api.getRelationshipWorkspacePreferences(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                     |
| ------------------ | -------- | -------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |

### Return type

[**RelationshipWorkspacePreferencesV1**](RelationshipWorkspacePreferencesV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Current relationship workspace preferences                              | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listRelationshipEvidence

> RelationshipEvidencePageV1 listRelationshipEvidence(relationshipId, limit)

List relationship-authorized evidence summaries

Returns only BP-authorized, customer-visible proof metadata for the selected relationship. EVALUATOR receives own disclosures, trial/configuration evidence, limitations, and Stop evidence. EMPLOYER receives the full customer-visible timeline, including contract, payment, activation, charges, handoffs, Stop, and release. RELATIONSHIP_MANAGER excludes restricted payment and personal payload references unless separately authorized. Other tenant or relationship scope returns no existence disclosure. Erased payload content, credentials, prompts, policy internals, and storage coordinates are never returned.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { ListRelationshipEvidenceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // number (optional)
    limit: 56,
  } satisfies ListRelationshipEvidenceRequest;

  try {
    const data = await api.listRelationshipEvidence(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                        | Notes                         |
| ------------------ | -------- | -------------------------------------------------- | ----------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`]     |
| **limit**          | `number` |                                                    | [Optional] [Defaults to `50`] |

### Return type

[**RelationshipEvidencePageV1**](RelationshipEvidencePageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **200**     | Evidence summary page                                                   | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## replaceRelationshipWorkspacePreferences

> RelationshipWorkspacePreferencesV1 replaceRelationshipWorkspacePreferences(relationshipId, replaceRelationshipWorkspacePreferencesRequestV1)

Replace relationship-specific presentation preferences

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { ReplaceRelationshipWorkspacePreferencesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ReplaceRelationshipWorkspacePreferencesRequestV1
    replaceRelationshipWorkspacePreferencesRequestV1: ...,
  } satisfies ReplaceRelationshipWorkspacePreferencesRequest;

  try {
    const data = await api.replaceRelationshipWorkspacePreferences(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                                 | Type                                                                                                    | Description                                        | Notes                     |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                                   | `string`                                                                                                | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **replaceRelationshipWorkspacePreferencesRequestV1** | [ReplaceRelationshipWorkspacePreferencesRequestV1](ReplaceRelationshipWorkspacePreferencesRequestV1.md) |                                                    |                           |

### Return type

[**RelationshipWorkspacePreferencesV1**](RelationshipWorkspacePreferencesV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Preferences replaced without changing relationship authority            | -                |
| **400**     | Request body failed validation                                          | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Operation not valid in current state                                    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## requestRelationshipEvidenceExport

> RelationshipEvidenceExportReceiptV1 requestRelationshipEvidenceExport(relationshipId, idempotencyKey, requestRelationshipEvidenceExportV1)

Request or replay one relationship evidence export

Builds an export from the same role-filtered projection as the Evidence Reader. BP is the export owner and records export evidence before releasing an outcome; CE, Audit Sink, and payload-store coordinates are never exposed to the browser.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { RequestRelationshipEvidenceExportRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // RequestRelationshipEvidenceExportV1
    requestRelationshipEvidenceExportV1: ...,
  } satisfies RequestRelationshipEvidenceExportRequest;

  try {
    const data = await api.requestRelationshipEvidenceExport(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                    | Type                                                                          | Description                                                                              | Notes                     |
| --------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**                      | `string`                                                                      | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**                      | `string`                                                                      | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **requestRelationshipEvidenceExportV1** | [RequestRelationshipEvidenceExportV1](RequestRelationshipEvidenceExportV1.md) |                                                                                          |                           |

### Return type

[**RelationshipEvidenceExportReceiptV1**](RelationshipEvidenceExportReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **415**     | Request content type is not supported                                   | -                |
| **202**     | Export request accepted                                                 | -                |
| **200**     | Prior identical export request replayed                                 | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## resolveWorkspaceFocus

> WorkspaceFocusResolutionV1 resolveWorkspaceFocus(relationshipId, resolveWorkspaceFocusRequestV1)

Resolve a protected short-lived workspace focus reference

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { ResolveWorkspaceFocusRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ResolveWorkspaceFocusRequestV1
    resolveWorkspaceFocusRequestV1: ...,
  } satisfies ResolveWorkspaceFocusRequest;

  try {
    const data = await api.resolveWorkspaceFocus(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                               | Type                                                                | Description                                        | Notes                     |
| ---------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                 | `string`                                                            | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **resolveWorkspaceFocusRequestV1** | [ResolveWorkspaceFocusRequestV1](ResolveWorkspaceFocusRequestV1.md) |                                                    |                           |

### Return type

[**WorkspaceFocusResolutionV1**](WorkspaceFocusResolutionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Current authorized canonical destination                                | -                |
| **400**     | Request body failed validation                                          | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Operation not valid in current state                                    | -                |
| **410**     | Focus reference expired                                                 | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## submitRelationshipCommand

> RelationshipCommandReceiptV1 submitRelationshipCommand(relationshipId, idempotencyKey, submitRelationshipCommandRequestV1)

Submit or replay a typed relationship command

Commands are discriminated and version-bound. Idempotency is required.

### Example

```ts
import {
  Configuration,
  RelationshipWorkspaceApi,
} from '';
import type { SubmitRelationshipCommandRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new RelationshipWorkspaceApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // SubmitRelationshipCommandRequestV1
    submitRelationshipCommandRequestV1: ...,
  } satisfies SubmitRelationshipCommandRequest;

  try {
    const data = await api.submitRelationshipCommand(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                   | Type                                                                        | Description                                                                              | Notes                     |
| -------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**                     | `string`                                                                    | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **submitRelationshipCommandRequestV1** | [SubmitRelationshipCommandRequestV1](SubmitRelationshipCommandRequestV1.md) |                                                                                          |                           |

### Return type

[**RelationshipCommandReceiptV1**](RelationshipCommandReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **403**     | Identity action is not available to the authenticated actor             | -                |
| **415**     | Request content type is not supported                                   | -                |
| **202**     | Command accepted with durable reconciliation responsibility             | -                |
| **200**     | Prior identical command outcome replayed                                | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
