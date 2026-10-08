# ConversationalEmploymentApi

All URIs are relative to *https://api.waooaw.com*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getEmploymentCommand**](ConversationalEmploymentApi.md#getemploymentcommand) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/commands/{commandId} | Reconcile one command by its durable BP identity |
| [**getEmploymentPhase**](ConversationalEmploymentApi.md#getemploymentphase) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/phases/{phase} | Read one phase with requirement-derived progress |
| [**getEmploymentPlan**](ConversationalEmploymentApi.md#getemploymentplan) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/plans/current | Read the current plan version |
| [**getEmploymentPlanVersion**](ConversationalEmploymentApi.md#getemploymentplanversion) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/plans/{planVersion} | Read one immutable plan version |
| [**getEmploymentReadiness**](ConversationalEmploymentApi.md#getemploymentreadiness) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment/readiness | Read all independent readiness facets |
| [**getEmploymentWorkspace**](ConversationalEmploymentApi.md#getemploymentworkspace) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/employment | Read the complete conversational employment projection |
| [**submitEmploymentCommand**](ConversationalEmploymentApi.md#submitemploymentcommand) | **POST** /api/v1/employment/relationships/{relationshipId}/workspace/employment/commands | Submit or replay one closed typed employment command |



## getEmploymentCommand

> EmploymentCommandOutcomeV1 getEmploymentCommand(relationshipId, commandId)

Reconcile one command by its durable BP identity

Returns the owner-by-owner command state and prevents blind retry after an ambiguous outcome.

### Example

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

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |
| **commandId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**EmploymentCommandOutcomeV1**](EmploymentCommandOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Current authoritative command outcome |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getEmploymentPhase

> EmploymentPhaseV1 getEmploymentPhase(relationshipId, phase)

Read one phase with requirement-derived progress

Returns one phase whose progress is derived from declared requirements and owner-confirmed item states.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentPhaseRequest } from '@waooaw/employment-client';

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
    // EmploymentPhaseKind
    phase: ...,
  } satisfies GetEmploymentPhaseRequest;

  try {
    const data = await api.getEmploymentPhase(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |
| **phase** | `EmploymentPhaseKind` |  | [Defaults to `undefined`] [Enum: INDUCTION, PLANNING, OPERATIONS] |

### Return type

[**EmploymentPhaseV1**](EmploymentPhaseV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Phase projection |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getEmploymentPlan

> EmploymentPlanV1 getEmploymentPlan(relationshipId)

Read the current plan version

Returns the current immutable plan projection and its exact owner source version.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentPlanRequest } from '@waooaw/employment-client';

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
  } satisfies GetEmploymentPlanRequest;

  try {
    const data = await api.getEmploymentPlan(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**EmploymentPlanV1**](EmploymentPlanV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Current plan |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getEmploymentPlanVersion

> EmploymentPlanV1 getEmploymentPlanVersion(relationshipId, planVersion)

Read one immutable plan version

Returns an authorized historical plan version without promoting it to current.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentPlanVersionRequest } from '@waooaw/employment-client';

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
    planVersion: planVersion_example,
  } satisfies GetEmploymentPlanVersionRequest;

  try {
    const data = await api.getEmploymentPlanVersion(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |
| **planVersion** | `string` |  | [Defaults to `undefined`] |

### Return type

[**EmploymentPlanV1**](EmploymentPlanV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Exact plan version |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getEmploymentReadiness

> EmploymentReadinessV1 getEmploymentReadiness(relationshipId)

Read all independent readiness facets

Returns induction, plan, operations and performance facets without changing the C-034 lifecycle.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentReadinessRequest } from '@waooaw/employment-client';

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
  } satisfies GetEmploymentReadinessRequest;

  try {
    const data = await api.getEmploymentReadiness(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**EmploymentReadinessV1**](EmploymentReadinessV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Readiness projection |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getEmploymentWorkspace

> EmploymentWorkspaceV1 getEmploymentWorkspace(relationshipId)

Read the complete conversational employment projection

Returns BP-composed owner truth without transferring CE, WBE, PR or adapter authority.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { GetEmploymentWorkspaceRequest } from '@waooaw/employment-client';

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
  } satisfies GetEmploymentWorkspaceRequest;

  try {
    const data = await api.getEmploymentWorkspace(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**EmploymentWorkspaceV1**](EmploymentWorkspaceV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Authoritative BP-composed projection |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## submitEmploymentCommand

> EmploymentCommandOutcomeV1 submitEmploymentCommand(relationshipId, idempotencyKey, employmentCommandRequestV1)

Submit or replay one closed typed employment command

Accepts a version-bound command; transport acceptance never represents owner commit or governed success.

### Example

```ts
import {
  Configuration,
  ConversationalEmploymentApi,
} from '@waooaw/employment-client';
import type { SubmitEmploymentCommandRequest } from '@waooaw/employment-client';

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
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // EmploymentCommandRequestV1
    employmentCommandRequestV1: ...,
  } satisfies SubmitEmploymentCommandRequest;

  try {
    const data = await api.submitEmploymentCommand(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **relationshipId** | `string` |  | [Defaults to `undefined`] |
| **idempotencyKey** | `string` |  | [Defaults to `undefined`] |
| **employmentCommandRequestV1** | [EmploymentCommandRequestV1](EmploymentCommandRequestV1.md) |  | |

### Return type

[**EmploymentCommandOutcomeV1**](EmploymentCommandOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **202** | BP accepted durable responsibility; no business success is implied |  -  |
| **200** | Prior identical terminal outcome replayed |  -  |
| **400** | Invalid request |  -  |
| **401** | Identity session is missing, invalid, or expired |  -  |
| **403** | Accepted assurance is insufficient |  -  |
| **404** | Resource absent or inaccessible |  -  |
| **409** | Expected-version, reassessment or idempotency conflict |  -  |
| **423** | Known policy, dependency or commercial condition blocks the command |  -  |
| **503** | Required source unavailable or command outcome unknown |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

