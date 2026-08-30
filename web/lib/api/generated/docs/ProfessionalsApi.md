# ProfessionalsApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                       | HTTP request                                                                                                           | Description                                                         |
| -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [**activateAgentAdmission**](ProfessionalsApi.md#activateagentadmission)                     | **POST** /api/v1/professionals/{type}/versions/{version}/admission/activations                                         | Activate an approved and currently ready professional version       |
| [**approveAgentAdmission**](ProfessionalsApi.md#approveagentadmission)                       | **POST** /api/v1/professionals/{type}/versions/{version}/admission/approvals                                           | Independently approve an exact admission revision                   |
| [**createAgentAdmissionDraft**](ProfessionalsApi.md#createagentadmissiondraftoperation)      | **POST** /api/v1/professionals/{type}/versions/{version}/admission/drafts                                              | Create or replay an admission draft                                 |
| [**discoverProfessionals**](ProfessionalsApi.md#discoverprofessionals)                       | **GET** /api/v1/professionals                                                                                          | Discover suitable professionals for a business outcome              |
| [**getAgentAdmissionFindings**](ProfessionalsApi.md#getagentadmissionfindings)               | **GET** /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/validations/{validationId}/findings | Read safe deterministic admission findings                          |
| [**getOfferableProfessionalVersions**](ProfessionalsApi.md#getofferableprofessionalversions) | **GET** /api/v1/professionals/offerable-versions                                                                       | List active and currently offerable professional versions           |
| [**getProfessionalDisclosure**](ProfessionalsApi.md#getprofessionaldisclosure)               | **GET** /api/v1/professionals/{professionalType}/disclosure                                                            | Read the versioned professional disclosure before trial             |
| [**putAgentAdmissionRevision**](ProfessionalsApi.md#putagentadmissionrevisionoperation)      | **PUT** /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/revisions/{revision}                | Append an immutable admission draft revision                        |
| [**rejectAgentAdmission**](ProfessionalsApi.md#rejectagentadmission)                         | **POST** /api/v1/professionals/{type}/versions/{version}/admission/rejections                                          | Independently reject an exact admission revision                    |
| [**retireAgentAdmission**](ProfessionalsApi.md#retireagentadmission)                         | **POST** /api/v1/professionals/{type}/versions/{version}/admission/retirements                                         | Retire a professional version while preserving lineage              |
| [**submitAgentAdmission**](ProfessionalsApi.md#submitagentadmission)                         | **POST** /api/v1/professionals/{type}/versions/{version}/admission/submissions                                         | Submit an exact validated revision for independent review           |
| [**supersedeAgentAdmission**](ProfessionalsApi.md#supersedeagentadmission)                   | **POST** /api/v1/professionals/{type}/versions/{version}/admission/supersessions                                       | Supersede a professional version under an explicit migration policy |
| [**suspendAgentAdmission**](ProfessionalsApi.md#suspendagentadmission)                       | **POST** /api/v1/professionals/{type}/versions/{version}/admission/suspensions                                         | Suspend an active professional version immediately                  |
| [**validateAgentAdmission**](ProfessionalsApi.md#validateagentadmissionoperation)            | **POST** /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/validations                        | Validate an exact admission revision deterministically              |

## activateAgentAdmission

> AgentAdmission activateAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Activate an approved and currently ready professional version

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { ActivateAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies ActivateAgentAdmissionRequest;

  try {
    const data = await api.activateAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## approveAgentAdmission

> AgentAdmission approveAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Independently approve an exact admission revision

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { ApproveAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies ApproveAgentAdmissionRequest;

  try {
    const data = await api.approveAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## createAgentAdmissionDraft

> AgentAdmission createAgentAdmissionDraft(type, version, idempotencyKey, createAgentAdmissionDraftRequest)

Create or replay an admission draft

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { CreateAgentAdmissionDraftOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // CreateAgentAdmissionDraftRequest
    createAgentAdmissionDraftRequest: ...,
  } satisfies CreateAgentAdmissionDraftOperationRequest;

  try {
    const data = await api.createAgentAdmissionDraft(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                 | Type                                                                    | Description                                                                              | Notes                     |
| ------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                             | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **version**                          | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                   | `string`                                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **createAgentAdmissionDraftRequest** | [CreateAgentAdmissionDraftRequest](CreateAgentAdmissionDraftRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                  | Response headers |
| ----------- | -------------------------------------------- | ---------------- |
| **200**     | Existing identical draft replayed            | -                |
| **201**     | Draft created                                | -                |
| **400**     | Agent admission request is invalid           | -                |
| **401**     | Authentication is required                   | -                |
| **404**     | Admission resource is absent or inaccessible | -                |
| **409**     | Idempotency or aggregate state conflict      | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## discoverProfessionals

> Array&lt;ProfessionalDiscoveryResult&gt; discoverProfessionals(outcome)

Discover suitable professionals for a business outcome

Returns active professional projections that are lawfully eligible for the stated business outcome. Results explain suitability without preferred-customer scoring, ranking by customer value, or disclosure of protected eligibility facts.

### Example

```ts
import { Configuration, ProfessionalsApi } from "";
import type { DiscoverProfessionalsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    outcome: outcome_example,
  } satisfies DiscoverProfessionalsRequest;

  try {
    const data = await api.discoverProfessionals(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name        | Type     | Description | Notes                     |
| ----------- | -------- | ----------- | ------------------------- |
| **outcome** | `string` |             | [Defaults to `undefined`] |

### Return type

[**Array&lt;ProfessionalDiscoveryResult&gt;**](ProfessionalDiscoveryResult.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                      | Response headers |
| ----------- | ---------------------------------------------------------------- | ---------------- |
| **200**     | Suitable professional projections with customer-safe fit reasons | -                |
| **400**     | Request body failed validation                                   | -                |
| **401**     | JWT missing, expired, or invalid                                 | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getAgentAdmissionFindings

> Array&lt;AgentAdmissionFinding&gt; getAgentAdmissionFindings(type, version, draftId, validationId)

Read safe deterministic admission findings

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { GetAgentAdmissionFindingsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string
    draftId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    validationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetAgentAdmissionFindingsRequest;

  try {
    const data = await api.getAgentAdmissionFindings(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name             | Type     | Description | Notes                     |
| ---------------- | -------- | ----------- | ------------------------- |
| **type**         | `string` |             | [Defaults to `undefined`] |
| **version**      | `string` |             | [Defaults to `undefined`] |
| **draftId**      | `string` |             | [Defaults to `undefined`] |
| **validationId** | `string` |             | [Defaults to `undefined`] |

### Return type

[**Array&lt;AgentAdmissionFinding&gt;**](AgentAdmissionFinding.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                  | Response headers |
| ----------- | -------------------------------------------- | ---------------- |
| **200**     | Validation findings                          | -                |
| **401**     | Authentication is required                   | -                |
| **404**     | Admission resource is absent or inaccessible | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getOfferableProfessionalVersions

> Array&lt;OfferableProfessionalVersion&gt; getOfferableProfessionalVersions(environment)

List active and currently offerable professional versions

### Example

```ts
import { Configuration, ProfessionalsApi } from "";
import type { GetOfferableProfessionalVersionsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ProfessionalsApi();

  const body = {
    // 'demo' | 'uat' | 'prod'
    environment: environment_example,
  } satisfies GetOfferableProfessionalVersionsRequest;

  try {
    const data = await api.getOfferableProfessionalVersions(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name            | Type                  | Description | Notes                                             |
| --------------- | --------------------- | ----------- | ------------------------------------------------- |
| **environment** | `demo`, `uat`, `prod` |             | [Defaults to `undefined`] [Enum: demo, uat, prod] |

### Return type

[**Array&lt;OfferableProfessionalVersion&gt;**](OfferableProfessionalVersion.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                                 | Response headers |
| ----------- | ------------------------------------------- | ---------------- |
| **200**     | Public-safe offerable professional versions | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getProfessionalDisclosure

> ProfessionalDisclosure getProfessionalDisclosure(professionalType)

Read the versioned professional disclosure before trial

### Example

```ts
import { Configuration, ProfessionalsApi } from "";
import type { GetProfessionalDisclosureRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    professionalType: professionalType_example,
  } satisfies GetProfessionalDisclosureRequest;

  try {
    const data = await api.getProfessionalDisclosure(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                 | Type     | Description | Notes                     |
| -------------------- | -------- | ----------- | ------------------------- |
| **professionalType** | `string` |             | [Defaults to `undefined`] |

### Return type

[**ProfessionalDisclosure**](ProfessionalDisclosure.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                            | Response headers |
| ----------- | -------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Complete suitability, rights, limits, authority, trial, evidence, and price disclosure | -                |
| **401**     | JWT missing, expired, or invalid                                                       | -                |
| **404**     | Resource not found (or not accessible to this tenant)                                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## putAgentAdmissionRevision

> AgentAdmission putAgentAdmissionRevision(type, version, draftId, revision, idempotencyKey, putAgentAdmissionRevisionRequest)

Append an immutable admission draft revision

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { PutAgentAdmissionRevisionOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string
    draftId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // number
    revision: 56,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // PutAgentAdmissionRevisionRequest
    putAgentAdmissionRevisionRequest: ...,
  } satisfies PutAgentAdmissionRevisionOperationRequest;

  try {
    const data = await api.putAgentAdmissionRevision(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                 | Type                                                                    | Description                                                                              | Notes                     |
| ------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                             | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **version**                          | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **draftId**                          | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **revision**                         | `number`                                                                |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                   | `string`                                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **putAgentAdmissionRevisionRequest** | [PutAgentAdmissionRevisionRequest](PutAgentAdmissionRevisionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                  | Response headers |
| ----------- | -------------------------------------------- | ---------------- |
| **200**     | Revision stored                              | -                |
| **400**     | Agent admission request is invalid           | -                |
| **401**     | Authentication is required                   | -                |
| **404**     | Admission resource is absent or inaccessible | -                |
| **409**     | Idempotency or aggregate state conflict      | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## rejectAgentAdmission

> AgentAdmission rejectAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Independently reject an exact admission revision

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { RejectAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies RejectAgentAdmissionRequest;

  try {
    const data = await api.rejectAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## retireAgentAdmission

> AgentAdmission retireAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Retire a professional version while preserving lineage

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { RetireAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies RetireAgentAdmissionRequest;

  try {
    const data = await api.retireAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## submitAgentAdmission

> AgentAdmission submitAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Submit an exact validated revision for independent review

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { SubmitAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies SubmitAgentAdmissionRequest;

  try {
    const data = await api.submitAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **201**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## supersedeAgentAdmission

> AgentAdmission supersedeAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Supersede a professional version under an explicit migration policy

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { SupersedeAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies SupersedeAgentAdmissionRequest;

  try {
    const data = await api.supersedeAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## suspendAgentAdmission

> AgentAdmission suspendAgentAdmission(type, version, idempotencyKey, agentAdmissionTransitionRequest)

Suspend an active professional version immediately

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { SuspendAgentAdmissionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AgentAdmissionTransitionRequest
    agentAdmissionTransitionRequest: ...,
  } satisfies SuspendAgentAdmissionRequest;

  try {
    const data = await api.suspendAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                                                              | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                            | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **version**                         | `string`                                                              |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **agentAdmissionTransitionRequest** | [AgentAdmissionTransitionRequest](AgentAdmissionTransitionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmission**](AgentAdmission.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Admission transition committed with Evidence First reference | -                |
| **400**     | Agent admission request is invalid                           | -                |
| **401**     | Authentication is required                                   | -                |
| **404**     | Admission resource is absent or inaccessible                 | -                |
| **409**     | Idempotency or aggregate state conflict                      | -                |
| **423**     | Admission transition is blocked by policy or readiness       | -                |
| **503**     | A mandatory admission dependency is unavailable              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## validateAgentAdmission

> AgentAdmissionValidation validateAgentAdmission(type, version, draftId, idempotencyKey, validateAgentAdmissionRequest)

Validate an exact admission revision deterministically

### Example

```ts
import {
  Configuration,
  ProfessionalsApi,
} from '';
import type { ValidateAgentAdmissionOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ProfessionalsApi(config);

  const body = {
    // string
    type: type_example,
    // string
    version: version_example,
    // string
    draftId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ValidateAgentAdmissionRequest
    validateAgentAdmissionRequest: ...,
  } satisfies ValidateAgentAdmissionOperationRequest;

  try {
    const data = await api.validateAgentAdmission(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                              | Type                                                              | Description                                                                              | Notes                     |
| --------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **type**                          | `string`                                                          |                                                                                          | [Defaults to `undefined`] |
| **version**                       | `string`                                                          |                                                                                          | [Defaults to `undefined`] |
| **draftId**                       | `string`                                                          |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                | `string`                                                          | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **validateAgentAdmissionRequest** | [ValidateAgentAdmissionRequest](ValidateAgentAdmissionRequest.md) |                                                                                          |                           |

### Return type

[**AgentAdmissionValidation**](AgentAdmissionValidation.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                  | Response headers |
| ----------- | -------------------------------------------- | ---------------- |
| **200**     | Existing identical validation replayed       | -                |
| **202**     | Validation completed                         | -                |
| **400**     | Agent admission request is invalid           | -                |
| **401**     | Authentication is required                   | -                |
| **404**     | Admission resource is absent or inaccessible | -                |
| **409**     | Idempotency or aggregate state conflict      | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
