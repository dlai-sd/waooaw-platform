# RelationshipWorkspaceApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                                 | HTTP request                                                                                    | Description                                                        |
| ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [**getRelationshipAttention**](RelationshipWorkspaceApi.md#getrelationshipattention)                   | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/attention                   | Read authoritative needs-your-attention items in BP-owned order    |
| [**getRelationshipCommand**](RelationshipWorkspaceApi.md#getrelationshipcommand)                       | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/commands/{commandId}        | Reconcile one command to an authoritative outcome                  |
| [**getRelationshipEvidence**](RelationshipWorkspaceApi.md#getrelationshipevidence)                     | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence/{evidenceId}       | Read one relationship-authorized evidence detail projection        |
| [**getRelationshipEvidenceExport**](RelationshipWorkspaceApi.md#getrelationshipevidenceexport)         | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports/{exportId} | Reconcile one relationship evidence export request                 |
| [**getRelationshipPlan**](RelationshipWorkspaceApi.md#getrelationshipplan)                             | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/plan                        | Read relationship plan, goals, and available typed commands        |
| [**getRelationshipResults**](RelationshipWorkspaceApi.md#getrelationshipresults)                       | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/results                     | Read relationship business outcomes and attribution context        |
| [**getRelationshipRightsControls**](RelationshipWorkspaceApi.md#getrelationshiprightscontrols)         | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/rights-controls             | Read relationship rights, scope, authority, and lifecycle controls |
| [**getRelationshipUsageBudget**](RelationshipWorkspaceApi.md#getrelationshipusagebudget)               | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/usage-budget                | Read WBE-authoritative usage and budget projection relayed by BP   |
| [**getRelationshipWork**](RelationshipWorkspaceApi.md#getrelationshipwork)                             | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/work                        | Read relationship work and deliverable status                      |
| [**getRelationshipWorkspace**](RelationshipWorkspaceApi.md#getrelationshipworkspace)                   | **GET** /api/v1/employment/relationships/{relationshipId}/workspace                             | Read the complete relationship workspace projection                |
| [**getRelationshipWorkspaceChanges**](RelationshipWorkspaceApi.md#getrelationshipworkspacechanges)     | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/changes                     | Read incremental workspace changes after an authoritative cursor   |
| [**listRelationshipEvidence**](RelationshipWorkspaceApi.md#listrelationshipevidence)                   | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/evidence                    | List relationship-authorized evidence summaries                    |
| [**requestRelationshipEvidenceExport**](RelationshipWorkspaceApi.md#requestrelationshipevidenceexport) | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports           | Request or replay one relationship evidence export                 |
| [**submitRelationshipCommand**](RelationshipWorkspaceApi.md#submitrelationshipcommand)                 | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/commands                   | Submit or replay a typed relationship command                      |

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Attention items in exact authoritative order                            | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Command outcome                                                         | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipEvidence

> RelationshipEvidenceDetailV1 getRelationshipEvidence(relationshipId, evidenceId)

Read one relationship-authorized evidence detail projection

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Evidence detail                                                         | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipEvidenceExport

> RelationshipEvidenceExportOutcomeV1 getRelationshipEvidenceExport(relationshipId, exportId)

Reconcile one relationship evidence export request

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Export outcome                                                          | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Workspace change page                                                   | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **410**     | Workspace cursor expired and a fresh snapshot is required               | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listRelationshipEvidence

> RelationshipEvidencePageV1 listRelationshipEvidence(relationshipId, limit)

List relationship-authorized evidence summaries

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Evidence summary page                                                   | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## requestRelationshipEvidenceExport

> RelationshipEvidenceExportReceiptV1 requestRelationshipEvidenceExport(relationshipId, idempotencyKey, requestRelationshipEvidenceExportV1)

Request or replay one relationship evidence export

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **202**     | Export request accepted                                                 | -                |
| **200**     | Prior identical export request replayed                                 | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

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
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **202**     | Command accepted with durable reconciliation responsibility             | -                |
| **200**     | Prior identical command outcome replayed                                | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
