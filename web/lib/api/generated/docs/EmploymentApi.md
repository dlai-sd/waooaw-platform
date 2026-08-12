# EmploymentApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                               | HTTP request                                                                                             | Description                                                               |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [**acceptEmploymentContract**](EmploymentApi.md#acceptemploymentcontractoperation)                   | **POST** /api/v1/employment/relationships/{relationshipId}/contracts/{version}/accept                    | Explicitly accept one exact employment contract version                   |
| [**activateEmploymentContract**](EmploymentApi.md#activateemploymentcontract)                        | **PUT** /api/v1/employment/contracts/{contractId}/activate                                               | Activate an employment contract                                           |
| [**activateRelationshipHandoff**](EmploymentApi.md#activaterelationshiphandoffoperation)             | **POST** /api/v1/employment/relationships/{relationshipId}/handoffs/{handoffId}/activate                 | Authenticate the target channel and activate a prepared handoff           |
| [**admitEmploymentRelationship**](EmploymentApi.md#admitemploymentrelationshipoperation)             | **POST** /api/v1/employment/relationships                                                                | Admit or replay an employment relationship                                |
| [**convertTrialToPaid**](EmploymentApi.md#converttrialtopaid)                                        | **POST** /api/v1/employment/contracts/{contractId}/convert-trial                                         | Convert a trial contract to paid subscription (FR-002)                    |
| [**createRelationshipOnboardingOrder**](EmploymentApi.md#createrelationshiponboardingorder)          | **POST** /api/v1/employment/relationships/{relationshipId}/contracts/{version}/payments/onboarding-order | Record explicit payment consent and create a contract-linked hosted order |
| [**formEmploymentContract**](EmploymentApi.md#formemploymentcontract)                                | **POST** /api/v1/employment/contracts                                                                    | Compatibility adapter for relationship admission                          |
| [**getEmploymentContract**](EmploymentApi.md#getemploymentcontract)                                  | **GET** /api/v1/employment/contracts/{contractId}                                                        | Compatibility projection of an employment relationship                    |
| [**getEmploymentRelationship**](EmploymentApi.md#getemploymentrelationship)                          | **GET** /api/v1/employment/relationships/{relationshipId}                                                | Get an employment relationship                                            |
| [**getEmploymentRelationshipTimeline**](EmploymentApi.md#getemploymentrelationshiptimeline)          | **GET** /api/v1/employment/relationships/{relationshipId}/timeline                                       | Get the evidence-linked relationship state timeline                       |
| [**getPhaseBundle**](EmploymentApi.md#getphasebundle)                                                | **GET** /api/v1/employment/contracts/{contractId}/phase-bundle                                           | Get active phase bundle                                                   |
| [**getRelationshipContractJourney**](EmploymentApi.md#getrelationshipcontractjourney)                | **GET** /api/v1/employment/relationships/{relationshipId}/contract-journey                               | Read the latest exact contract and activation journey                     |
| [**hireAgentCompatibilityUnversioned**](EmploymentApi.md#hireagentcompatibilityunversioned)          | **POST** /api/agents/hire                                                                                | Deprecated unversioned hire compatibility adapter                         |
| [**hireAgentCompatibilityV1**](EmploymentApi.md#hireagentcompatibilityv1)                            | **POST** /api/v1/agents/hire                                                                             | Deprecated v1 hire compatibility adapter                                  |
| [**listEmploymentContracts**](EmploymentApi.md#listemploymentcontracts)                              | **GET** /api/v1/employment/contracts                                                                     | List employment contracts for the authenticated customer                  |
| [**prepareRelationshipHandoff**](EmploymentApi.md#preparerelationshiphandoffoperation)               | **POST** /api/v1/employment/relationships/{relationshipId}/handoffs                                      | Prepare a channel handoff for the same employment relationship            |
| [**proposeEmploymentContract**](EmploymentApi.md#proposeemploymentcontractoperation)                 | **POST** /api/v1/employment/relationships/{relationshipId}/contracts                                     | Compose or replay the presented employment contract                       |
| [**releaseEmploymentRelationshipStop**](EmploymentApi.md#releaseemploymentrelationshipstopoperation) | **POST** /api/v1/employment/relationships/{relationshipId}/emergency-stop/release                        | Release the active relationship Stop with fresh Tier-4 employer proof     |
| [**renewEmploymentContract**](EmploymentApi.md#renewemploymentcontract)                              | **POST** /api/v1/employment/contracts/{contractId}/renew                                                 | Renew an employment contract                                              |
| [**startEmploymentRelationshipTrial**](EmploymentApi.md#startemploymentrelationshiptrial)            | **POST** /api/v1/employment/relationships/{relationshipId}/trial                                         | Start the relationship evaluation trial                                   |
| [**startPaidRelationshipActivation**](EmploymentApi.md#startpaidrelationshipactivationoperation)     | **POST** /api/v1/employment/relationships/{relationshipId}/activation                                    | Start or join durable paid relationship activation                        |
| [**stopEmploymentRelationship**](EmploymentApi.md#stopemploymentrelationshipoperation)               | **POST** /api/v1/employment/relationships/{relationshipId}/emergency-stop                                | Stop the complete AE-01 Employment Relationship                           |
| [**suspendEmploymentContract**](EmploymentApi.md#suspendemploymentcontract)                          | **PUT** /api/v1/employment/contracts/{contractId}/suspend                                                | Suspend an employment contract                                            |
| [**terminateEmploymentContract**](EmploymentApi.md#terminateemploymentcontract)                      | **DELETE** /api/v1/employment/contracts/{contractId}                                                     | Terminate an employment contract                                          |
| [**transitionEmploymentRelationship**](EmploymentApi.md#transitionemploymentrelationshipoperation)   | **POST** /api/v1/employment/relationships/{relationshipId}/transitions                                   | Transition relationship state from an authorized internal service         |
| [**updatePhaseBundle**](EmploymentApi.md#updatephasebundleoperation)                                 | **PUT** /api/v1/employment/contracts/{contractId}/phase-bundle                                           | Upgrade or change phase bundle                                            |

## acceptEmploymentContract

> EmploymentContractAcceptance acceptEmploymentContract(relationshipId, version, acceptEmploymentContractRequest)

Explicitly accept one exact employment contract version

Tier-4 web-only command. Requires a Keycloak portal authentication no older than five minutes, an active same-tenant EMPLOYER binding, the exact presented version and hash, and the separate fixed authority-scope confirmation statement. WhatsApp, MPIN, deep-link possession, trial consent, silence, or a default selection cannot accept a contract.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { AcceptEmploymentContractOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // number
    version: 56,
    // AcceptEmploymentContractRequest
    acceptEmploymentContractRequest: ...,
  } satisfies AcceptEmploymentContractOperationRequest;

  try {
    const data = await api.acceptEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                | Type                                                                  | Description                                        | Notes                     |
| ----------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                  | `string`                                                              | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **version**                         | `number`                                                              |                                                    | [Defaults to `undefined`] |
| **acceptEmploymentContractRequest** | [AcceptEmploymentContractRequest](AcceptEmploymentContractRequest.md) |                                                    |                           |

### Return type

[**EmploymentContractAcceptance**](EmploymentContractAcceptance.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                            | Response headers |
| ----------- | ---------------------------------------------------------------------- | ---------------- |
| **201**     | Exact contract accepted with committed constitutional evidence         | -                |
| **200**     | Existing exact acceptance replayed                                     | -                |
| **400**     | Request body failed validation                                         | -                |
| **401**     | JWT missing, expired, or invalid                                       | -                |
| **403**     | Fresh portal assurance or active same-tenant EMPLOYER authority denied | -                |
| **404**     | Resource not found (or not accessible to this tenant)                  | -                |
| **409**     | Operation not valid in current state                                   | -                |
| **503**     | Constitutional validation or evidence commitment is unavailable        | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## activateEmploymentContract

> EmploymentContract activateEmploymentContract(contractId)

Activate an employment contract

Transitions contract from EVALUATION to ACTIVE. Constitutional Engine evidence record created before return.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ActivateEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies ActivateEmploymentContractRequest;

  try {
    const data = await api.activateEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name           | Type     | Description              | Notes                     |
| -------------- | -------- | ------------------------ | ------------------------- |
| **contractId** | `string` | Employment contract UUID | [Defaults to `undefined`] |

### Return type

[**EmploymentContract**](EmploymentContract.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Contract activated                                    | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **409**     | Operation not valid in current state                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## activateRelationshipHandoff

> RelationshipHandoff activateRelationshipHandoff(relationshipId, handoffId, idempotencyKey, activateRelationshipHandoffRequest)

Authenticate the target channel and activate a prepared handoff

Freshly authenticates the target participant, re-verifies tenant, role, assurance, current authority, and Stop state, then commits the target binding and continuity checkpoint only after constitutional evidence is durable. Failure or uncertainty preserves the active source binding. A lower-assurance target receives reduced capability and never reduced protection.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ActivateRelationshipHandoffOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Opaque handoff identifier bound to one tenant and employment relationship
    handoffId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ActivateRelationshipHandoffRequest
    activateRelationshipHandoffRequest: ...,
  } satisfies ActivateRelationshipHandoffOperationRequest;

  try {
    const data = await api.activateRelationshipHandoff(body);
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
| **handoffId**                          | `string`                                                                    | Opaque handoff identifier bound to one tenant and employment relationship                | [Defaults to `undefined`] |
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **activateRelationshipHandoffRequest** | [ActivateRelationshipHandoffRequest](ActivateRelationshipHandoffRequest.md) |                                                                                          |                           |

### Return type

[**RelationshipHandoff**](RelationshipHandoff.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                              | Response headers |
| ----------- | ------------------------------------------------------------------------ | ---------------- |
| **200**     | Target binding activated or prior identical outcome replayed             | -                |
| **400**     | Request body failed validation                                           | -                |
| **401**     | JWT missing, expired, or invalid                                         | -                |
| **403**     | Target authentication, role, or assurance is insufficient                | -                |
| **404**     | Resource not found (or not accessible to this tenant)                    | -                |
| **409**     | Operation not valid in current state                                     | -                |
| **423**     | Relationship is stopped and activation is blocked                        | -                |
| **503**     | Target authentication, evidence, or checkpoint commitment is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## admitEmploymentRelationship

> EmploymentRelationship admitEmploymentRelationship(admitEmploymentRelationshipRequest)

Admit or replay an employment relationship

Mints the tenant\&#39;s durable employment relationship for the authenticated participant and canonical evaluation intent. Replaying the same participant, professional type, and evaluation intent returns the existing relationship. Constitutional validation and evidence commitment complete before persistence.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { AdmitEmploymentRelationshipOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // AdmitEmploymentRelationshipRequest
    admitEmploymentRelationshipRequest: ...,
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

| Name                                   | Type                                                                        | Description | Notes |
| -------------------------------------- | --------------------------------------------------------------------------- | ----------- | ----- |
| **admitEmploymentRelationshipRequest** | [AdmitEmploymentRelationshipRequest](AdmitEmploymentRelationshipRequest.md) |             |       |

### Return type

[**EmploymentRelationship**](EmploymentRelationship.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                     | Response headers |
| ----------- | --------------------------------------------------------------- | ---------------- |
| **201**     | Relationship admitted                                           | -                |
| **200**     | Existing relationship returned for an idempotent replay         | -                |
| **400**     | Request body failed validation                                  | -                |
| **401**     | JWT missing, expired, or invalid                                | -                |
| **403**     | Authenticated identity lacks tenant or participant authority    | -                |
| **503**     | Constitutional validation or evidence commitment is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## convertTrialToPaid

> EmploymentContract convertTrialToPaid(contractId)

Convert a trial contract to paid subscription (FR-002)

Converts an active trial contract to a paid subscription. Trial outputs produced during the trial period are retained by the customer regardless of conversion (FR-002 — trial outputs owned by customer). A Constitutional Engine evidence record is created before this returns 200.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ConvertTrialToPaidRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies ConvertTrialToPaidRequest;

  try {
    const data = await api.convertTrialToPaid(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name           | Type     | Description              | Notes                     |
| -------------- | -------- | ------------------------ | ------------------------- |
| **contractId** | `string` | Employment contract UUID | [Defaults to `undefined`] |

### Return type

[**EmploymentContract**](EmploymentContract.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Trial converted to paid subscription                         | -                |
| **401**     | JWT missing, expired, or invalid                             | -                |
| **404**     | Resource not found (or not accessible to this tenant)        | -                |
| **409**     | Contract is not a trial, or trial has already been converted | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## createRelationshipOnboardingOrder

> RelationshipHostedOnboardingOrder createRelationshipOnboardingOrder(relationshipId, version, relationshipPaymentProceedRequest)

Record explicit payment consent and create a contract-linked hosted order

Requires fresh Keycloak portal authentication, an active same-tenant EMPLOYER binding, one exact accepted contract, and itemization whose subscription plus wallet seed equals the accepted INR gross amount. Records constitutional proceed evidence before asking WBE for a Razorpay-hosted order. Payment secrets and bypass coupons are never accepted. Payment capture does not activate the relationship; durable activation is a separate flow.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { CreateRelationshipOnboardingOrderRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // number
    version: 56,
    // RelationshipPaymentProceedRequest
    relationshipPaymentProceedRequest: ...,
  } satisfies CreateRelationshipOnboardingOrderRequest;

  try {
    const data = await api.createRelationshipOnboardingOrder(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                  | Type                                                                      | Description                                        | Notes                     |
| ------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                    | `string`                                                                  | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **version**                           | `number`                                                                  |                                                    | [Defaults to `undefined`] |
| **relationshipPaymentProceedRequest** | [RelationshipPaymentProceedRequest](RelationshipPaymentProceedRequest.md) |                                                    |                           |

### Return type

[**RelationshipHostedOnboardingOrder**](RelationshipHostedOnboardingOrder.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                        | Response headers |
| ----------- | ---------------------------------------------------------------------------------- | ---------------- |
| **200**     | Contract-linked Razorpay-hosted order created                                      | -                |
| **400**     | Request body failed validation                                                     | -                |
| **401**     | JWT missing, expired, or invalid                                                   | -                |
| **403**     | Fresh portal assurance or active same-tenant EMPLOYER authority denied             | -                |
| **404**     | Resource not found (or not accessible to this tenant)                              | -                |
| **409**     | Exact contract acceptance is absent or itemization differs from the contract       | -                |
| **503**     | Constitutional evidence or WBE hosted-order outcome is unavailable or inconsistent | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## formEmploymentContract

> LegacyEmploymentRelationshipAdapterResponse formEmploymentContract(legacyFormEmploymentContractRequest)

Compatibility adapter for relationship admission

Deprecated compatibility route. Admits or replays a canonical employment relationship and returns a legacy-shaped projection. Use POST /api/v1/employment/relationships for new integrations.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { FormEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // LegacyFormEmploymentContractRequest
    legacyFormEmploymentContractRequest: ...,
  } satisfies FormEmploymentContractRequest;

  try {
    const data = await api.formEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                    | Type                                                                          | Description | Notes |
| --------------------------------------- | ----------------------------------------------------------------------------- | ----------- | ----- |
| **legacyFormEmploymentContractRequest** | [LegacyFormEmploymentContractRequest](LegacyFormEmploymentContractRequest.md) |             |       |

### Return type

[**LegacyEmploymentRelationshipAdapterResponse**](LegacyEmploymentRelationshipAdapterResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                       | Response headers                                                                                            |
| ----------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **201**     | Canonical relationship admitted through the compatibility adapter | _ Deprecation - <br> _ Link - Canonical relationship URL with rel&#x3D;\&quot;successor-version\&quot; <br> |
| **200**     | Existing canonical relationship returned for adapter replay       | _ Deprecation - <br> _ Link - <br>                                                                          |
| **400**     | Malformed request                                                 | -                                                                                                           |
| **401**     | JWT missing, expired, or invalid                                  | -                                                                                                           |
| **422**     | Request body failed validation                                    | -                                                                                                           |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getEmploymentContract

> LegacyEmploymentRelationshipAdapterResponse getEmploymentContract(contractId)

Compatibility projection of an employment relationship

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { GetEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetEmploymentContractRequest;

  try {
    const data = await api.getEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name           | Type     | Description              | Notes                     |
| -------------- | -------- | ------------------------ | ------------------------- |
| **contractId** | `string` | Employment contract UUID | [Defaults to `undefined`] |

### Return type

[**LegacyEmploymentRelationshipAdapterResponse**](LegacyEmploymentRelationshipAdapterResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers                   |
| ----------- | ----------------------------------------------------- | ---------------------------------- |
| **200**     | Legacy-shaped relationship projection                 | _ Deprecation - <br> _ Link - <br> |
| **401**     | JWT missing, expired, or invalid                      | -                                  |
| **404**     | Resource not found (or not accessible to this tenant) | -                                  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getEmploymentRelationship

> EmploymentRelationship getEmploymentRelationship(relationshipId)

Get an employment relationship

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { GetEmploymentRelationshipRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetEmploymentRelationshipRequest;

  try {
    const data = await api.getEmploymentRelationship(body);
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

[**EmploymentRelationship**](EmploymentRelationship.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Tenant-scoped employment relationship                 | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getEmploymentRelationshipTimeline

> Array&lt;RelationshipTimelineEntry&gt; getEmploymentRelationshipTimeline(relationshipId)

Get the evidence-linked relationship state timeline

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { GetEmploymentRelationshipTimelineRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetEmploymentRelationshipTimelineRequest;

  try {
    const data = await api.getEmploymentRelationshipTimeline(body);
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

[**Array&lt;RelationshipTimelineEntry&gt;**](RelationshipTimelineEntry.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Ordered relationship state history                    | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getPhaseBundle

> PhaseBundleSubscription getPhaseBundle(contractId)

Get active phase bundle

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { GetPhaseBundleRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetPhaseBundleRequest;

  try {
    const data = await api.getPhaseBundle(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name           | Type     | Description | Notes                     |
| -------------- | -------- | ----------- | ------------------------- |
| **contractId** | `string` |             | [Defaults to `undefined`] |

### Return type

[**PhaseBundleSubscription**](PhaseBundleSubscription.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                      | Response headers |
| ----------- | -------------------------------- | ---------------- |
| **200**     | Active phase bundle subscription | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipContractJourney

> RelationshipContractJourney getRelationshipContractJourney(relationshipId)

Read the latest exact contract and activation journey

Returns the latest immutable contract material and BP-owned relationship progress for an active same-tenant relationship participant. Payment capture remains evidence rather than relationship activation; pending or unavailable owner outcomes never appear as success.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { GetRelationshipContractJourneyRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipContractJourneyRequest;

  try {
    const data = await api.getRelationshipContractJourney(body);
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

[**RelationshipContractJourney**](RelationshipContractJourney.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Exact contract and current journey projection         | -                |
| **204**     | No employment contract has been presented             | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **403**     | Authenticated tenant or participant context is absent | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **503**     | Contract projection is unavailable                    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## hireAgentCompatibilityUnversioned

> LegacyHireAgentResponse hireAgentCompatibilityUnversioned(legacyHireAgentRequest)

Deprecated unversioned hire compatibility adapter

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { HireAgentCompatibilityUnversionedRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // LegacyHireAgentRequest
    legacyHireAgentRequest: ...,
  } satisfies HireAgentCompatibilityUnversionedRequest;

  try {
    const data = await api.hireAgentCompatibilityUnversioned(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                       | Type                                                | Description | Notes |
| -------------------------- | --------------------------------------------------- | ----------- | ----- |
| **legacyHireAgentRequest** | [LegacyHireAgentRequest](LegacyHireAgentRequest.md) |             |       |

### Return type

[**LegacyHireAgentResponse**](LegacyHireAgentResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                       | Response headers                   |
| ----------- | ----------------------------------------------------------------- | ---------------------------------- |
| **200**     | Canonical relationship projected through the legacy hire response | _ Deprecation - <br> _ Link - <br> |
| **401**     | JWT missing, expired, or invalid                                  | -                                  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## hireAgentCompatibilityV1

> LegacyHireAgentResponse hireAgentCompatibilityV1(legacyHireAgentRequest)

Deprecated v1 hire compatibility adapter

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { HireAgentCompatibilityV1Request } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // LegacyHireAgentRequest
    legacyHireAgentRequest: ...,
  } satisfies HireAgentCompatibilityV1Request;

  try {
    const data = await api.hireAgentCompatibilityV1(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                       | Type                                                | Description | Notes |
| -------------------------- | --------------------------------------------------- | ----------- | ----- |
| **legacyHireAgentRequest** | [LegacyHireAgentRequest](LegacyHireAgentRequest.md) |             |       |

### Return type

[**LegacyHireAgentResponse**](LegacyHireAgentResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                    | Response headers                   |
| ----------- | ---------------------------------------------- | ---------------------------------- |
| **201**     | Relationship admitted through the hire adapter | _ Deprecation - <br> _ Link - <br> |
| **200**     | Existing relationship returned for hire replay | _ Deprecation - <br> _ Link - <br> |
| **401**     | JWT missing, expired, or invalid               | -                                  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listEmploymentContracts

> EmploymentContractPage listEmploymentContracts(state, page, pageSize)

List employment contracts for the authenticated customer

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ListEmploymentContractsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // EmploymentState | Filter by contract state (optional)
    state: ...,
    // number (optional)
    page: 56,
    // number (optional)
    pageSize: 56,
  } satisfies ListEmploymentContractsRequest;

  try {
    const data = await api.listEmploymentContracts(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name         | Type              | Description              | Notes                                                                                  |
| ------------ | ----------------- | ------------------------ | -------------------------------------------------------------------------------------- |
| **state**    | `EmploymentState` | Filter by contract state | [Optional] [Defaults to `undefined`] [Enum: EVALUATION, ACTIVE, SUSPENDED, TERMINATED] |
| **page**     | `number`          |                          | [Optional] [Defaults to `1`]                                                           |
| **pageSize** | `number`          |                          | [Optional] [Defaults to `20`]                                                          |

### Return type

[**EmploymentContractPage**](EmploymentContractPage.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                      | Response headers |
| ----------- | -------------------------------- | ---------------- |
| **200**     | List of employment contracts     | -                |
| **401**     | JWT missing, expired, or invalid | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## prepareRelationshipHandoff

> RelationshipHandoff prepareRelationshipHandoff(relationshipId, idempotencyKey, prepareRelationshipHandoffRequest)

Prepare a channel handoff for the same employment relationship

Prepares a target-channel binding and continuity checkpoint without changing relationship lifecycle, authority, contract, billing, or the active source binding. Tenant, relationship, participant, role, and authority values are resolved by the server. The source remains active until target authentication and checkpoint evidence commit. Identical idempotency key and request hash replay the prior outcome; divergent reuse conflicts with zero mutation.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { PrepareRelationshipHandoffOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // PrepareRelationshipHandoffRequest
    prepareRelationshipHandoffRequest: ...,
  } satisfies PrepareRelationshipHandoffOperationRequest;

  try {
    const data = await api.prepareRelationshipHandoff(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                  | Type                                                                      | Description                                                                              | Notes                     |
| ------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**                    | `string`                                                                  | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**                    | `string`                                                                  | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **prepareRelationshipHandoffRequest** | [PrepareRelationshipHandoffRequest](PrepareRelationshipHandoffRequest.md) |                                                                                          |                           |

### Return type

[**RelationshipHandoff**](RelationshipHandoff.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                         | Response headers |
| ----------- | ------------------------------------------------------------------- | ---------------- |
| **201**     | Target binding and continuity checkpoint prepared                   | -                |
| **200**     | Prior identical preparation outcome replayed                        | -                |
| **400**     | Request body failed validation                                      | -                |
| **401**     | JWT missing, expired, or invalid                                    | -                |
| **403**     | Authenticated participant lacks authority for the requested handoff | -                |
| **404**     | Resource not found (or not accessible to this tenant)               | -                |
| **409**     | Operation not valid in current state                                | -                |
| **423**     | Relationship is stopped and the handoff is blocked                  | -                |
| **503**     | Constitutional evidence or continuity persistence is unavailable    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## proposeEmploymentContract

> EmploymentContractVersion proposeEmploymentContract(relationshipId, proposeEmploymentContractRequest)

Compose or replay the presented employment contract

Composes immutable contract material from the latest evidenced Decision Space, accepted goals and skills, professional disclosure, and exact commercial terms. Identical canonical material replays the existing version and amendments create a new version.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ProposeEmploymentContractOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ProposeEmploymentContractRequest
    proposeEmploymentContractRequest: ...,
  } satisfies ProposeEmploymentContractOperationRequest;

  try {
    const data = await api.proposeEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                 | Type                                                                    | Description                                        | Notes                     |
| ------------------------------------ | ----------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                   | `string`                                                                | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **proposeEmploymentContractRequest** | [ProposeEmploymentContractRequest](ProposeEmploymentContractRequest.md) |                                                    |                           |

### Return type

[**EmploymentContractVersion**](EmploymentContractVersion.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                    | Response headers |
| ----------- | -------------------------------------------------------------- | ---------------- |
| **201**     | New immutable contract version presented                       | -                |
| **200**     | Existing identical contract version replayed                   | -                |
| **400**     | Request body failed validation                                 | -                |
| **401**     | JWT missing, expired, or invalid                               | -                |
| **403**     | Active same-tenant participant authority denied                | -                |
| **404**     | Resource not found (or not accessible to this tenant)          | -                |
| **409**     | Operation not valid in current state                           | -                |
| **503**     | Contract composition or constitutional evidence is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## releaseEmploymentRelationshipStop

> EmploymentRelationship releaseEmploymentRelationshipStop(relationshipId, releaseEmploymentRelationshipStopRequest)

Release the active relationship Stop with fresh Tier-4 employer proof

Portal only. Requires an active same-tenant EMPLOYER, authentication no older than five minutes, literal confirmation, justification, and exact originating Stop evidence and correlation. Reconnect, conversation, timeout, channel possession, and service operator contexts cannot release Stop.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { ReleaseEmploymentRelationshipStopOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ReleaseEmploymentRelationshipStopRequest
    releaseEmploymentRelationshipStopRequest: ...,
  } satisfies ReleaseEmploymentRelationshipStopOperationRequest;

  try {
    const data = await api.releaseEmploymentRelationshipStop(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                         | Type                                                                                    | Description                                        | Notes                     |
| -------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                           | `string`                                                                                | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **releaseEmploymentRelationshipStopRequest** | [ReleaseEmploymentRelationshipStopRequest](ReleaseEmploymentRelationshipStopRequest.md) |                                                    |                           |

### Return type

[**EmploymentRelationship**](EmploymentRelationship.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **200**     | Stop released after release evidence commitment                       | -                |
| **401**     | JWT missing, expired, or invalid                                      | -                |
| **403**     | Role, assurance, freshness, confirmation, or originating proof denied | -                |
| **404**     | Resource not found (or not accessible to this tenant)                 | -                |
| **409**     | Operation not valid in current state                                  | -                |
| **503**     | Release unresolved; relationship remains stopped                      | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## renewEmploymentContract

> EmploymentContract renewEmploymentContract(contractId, renewContractRequest)

Renew an employment contract

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { RenewEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // RenewContractRequest
    renewContractRequest: ...,
  } satisfies RenewEmploymentContractRequest;

  try {
    const data = await api.renewEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                     | Type                                            | Description              | Notes                     |
| ------------------------ | ----------------------------------------------- | ------------------------ | ------------------------- |
| **contractId**           | `string`                                        | Employment contract UUID | [Defaults to `undefined`] |
| **renewContractRequest** | [RenewContractRequest](RenewContractRequest.md) |                          |                           |

### Return type

[**EmploymentContract**](EmploymentContract.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Contract renewed                                      | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startEmploymentRelationshipTrial

> RelationshipTrial startEmploymentRelationshipTrial(relationshipId, startRelationshipTrialRequest)

Start the relationship evaluation trial

Starts the WBE-owned 14-day entitlement and the PR-owned evaluation workflow. The relationship becomes TRIAL_ACTIVE only after both owners confirm the same trial window.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { StartEmploymentRelationshipTrialRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartRelationshipTrialRequest
    startRelationshipTrialRequest: ...,
  } satisfies StartEmploymentRelationshipTrialRequest;

  try {
    const data = await api.startEmploymentRelationshipTrial(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                              | Type                                                              | Description                                        | Notes                     |
| --------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                | `string`                                                          | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **startRelationshipTrialRequest** | [StartRelationshipTrialRequest](StartRelationshipTrialRequest.md) |                                                    |                           |

### Return type

[**RelationshipTrial**](RelationshipTrial.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                  | Response headers |
| ----------- | ------------------------------------------------------------ | ---------------- |
| **200**     | Owner-confirmed trial is active                              | -                |
| **401**     | JWT missing, expired, or invalid                             | -                |
| **403**     | Authenticated identity lacks tenant or participant authority | -                |
| **404**     | Resource not found (or not accessible to this tenant)        | -                |
| **409**     | Operation not valid in current state                         | -                |
| **503**     | WBE or PR owner outcome is unavailable or inconsistent       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startPaidRelationshipActivation

> PaidRelationshipActivationOutcome startPaidRelationshipActivation(relationshipId, startPaidRelationshipActivationRequest)

Start or join durable paid relationship activation

Requires fresh Keycloak portal authentication and an active same-tenant EMPLOYER binding. BP derives the accepted contract, acceptance evidence, authority snapshot, actor, and stable correlation from canonical relationship state. WBE remains payment owner and revalidates the supplied payment reference and evidence identifier against its signature-verified CAPTURED row. Identical replay joins the stable Temporal workflow; unresolved owner outcomes never report success.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { StartPaidRelationshipActivationOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartPaidRelationshipActivationRequest
    startPaidRelationshipActivationRequest: ...,
  } satisfies StartPaidRelationshipActivationOperationRequest;

  try {
    const data = await api.startPaidRelationshipActivation(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                       | Type                                                                                | Description                                        | Notes                     |
| ------------------------------------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                         | `string`                                                                            | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **startPaidRelationshipActivationRequest** | [StartPaidRelationshipActivationRequest](StartPaidRelationshipActivationRequest.md) |                                                    |                           |

### Return type

[**PaidRelationshipActivationOutcome**](PaidRelationshipActivationOutcome.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------- | ---------------- |
| **200**     | Stored successful activation outcome returned                                   | -                |
| **400**     | Request body failed validation                                                  | -                |
| **401**     | JWT missing, expired, or invalid                                                | -                |
| **403**     | Fresh portal assurance or active same-tenant EMPLOYER authority denied          | -                |
| **409**     | Relationship is ineligible or canonical activation material conflicts           | -                |
| **503**     | Temporal, constitutional evidence, or WBE activation outcome remains unresolved | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## stopEmploymentRelationship

> EmploymentRelationship stopEmploymentRelationship(relationshipId, stopEmploymentRelationshipRequest)

Stop the complete AE-01 Employment Relationship

Any authenticated active participant may invoke fail-safe Stop. BP commits the relationship STOPPED_EMERGENCY projection while PR halts the relationship\&#39;s known evaluation and trial sessions. Repeated Stop returns the existing stopped projection.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { StopEmploymentRelationshipOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StopEmploymentRelationshipRequest
    stopEmploymentRelationshipRequest: ...,
  } satisfies StopEmploymentRelationshipOperationRequest;

  try {
    const data = await api.stopEmploymentRelationship(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                  | Type                                                                      | Description                                        | Notes                     |
| ------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                    | `string`                                                                  | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **stopEmploymentRelationshipRequest** | [StopEmploymentRelationshipRequest](StopEmploymentRelationshipRequest.md) |                                                    |                           |

### Return type

[**EmploymentRelationship**](EmploymentRelationship.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                    | Response headers |
| ----------- | -------------------------------------------------------------- | ---------------- |
| **200**     | Relationship Stop is durably projected                         | -                |
| **401**     | JWT missing, expired, or invalid                               | -                |
| **404**     | Resource not found (or not accessible to this tenant)          | -                |
| **409**     | Operation not valid in current state                           | -                |
| **503**     | Stop remains unresolved and must not be presented as confirmed | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## suspendEmploymentContract

> EmploymentContract suspendEmploymentContract(contractId, suspendContractRequest)

Suspend an employment contract

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { SuspendEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // SuspendContractRequest
    suspendContractRequest: ...,
  } satisfies SuspendEmploymentContractRequest;

  try {
    const data = await api.suspendEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                       | Type                                                | Description              | Notes                     |
| -------------------------- | --------------------------------------------------- | ------------------------ | ------------------------- |
| **contractId**             | `string`                                            | Employment contract UUID | [Defaults to `undefined`] |
| **suspendContractRequest** | [SuspendContractRequest](SuspendContractRequest.md) |                          |                           |

### Return type

[**EmploymentContract**](EmploymentContract.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Contract suspended                                    | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **409**     | Operation not valid in current state                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## terminateEmploymentContract

> EmploymentContract terminateEmploymentContract(contractId, terminateContractRequest)

Terminate an employment contract

Terminates the contract (transitions to TERMINATED state). A Constitutional Engine evidence record is created before this returns 200. Termination is irreversible.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { TerminateEmploymentContractRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Employment contract UUID
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // TerminateContractRequest
    terminateContractRequest: ...,
  } satisfies TerminateEmploymentContractRequest;

  try {
    const data = await api.terminateEmploymentContract(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                         | Type                                                    | Description              | Notes                     |
| ---------------------------- | ------------------------------------------------------- | ------------------------ | ------------------------- |
| **contractId**               | `string`                                                | Employment contract UUID | [Defaults to `undefined`] |
| **terminateContractRequest** | [TerminateContractRequest](TerminateContractRequest.md) |                          |                           |

### Return type

[**EmploymentContract**](EmploymentContract.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Contract terminated                                   | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **409**     | Operation not valid in current state                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## transitionEmploymentRelationship

> EmploymentRelationship transitionEmploymentRelationship(relationshipId, transitionEmploymentRelationshipRequest)

Transition relationship state from an authorized internal service

Internal-service endpoint. The actor must have the asserted active participant-role binding in the same tenant. Legal-state, Emergency Stop release, constitutional validation, and evidence commitment checks all complete before state mutation.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { TransitionEmploymentRelationshipOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // TransitionEmploymentRelationshipRequest
    transitionEmploymentRelationshipRequest: ...,
  } satisfies TransitionEmploymentRelationshipOperationRequest;

  try {
    const data = await api.transitionEmploymentRelationship(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                        | Type                                                                                  | Description                                        | Notes                     |
| ------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------- |
| **relationshipId**                          | `string`                                                                              | Tenant-scoped durable employment relationship UUID | [Defaults to `undefined`] |
| **transitionEmploymentRelationshipRequest** | [TransitionEmploymentRelationshipRequest](TransitionEmploymentRelationshipRequest.md) |                                                    |                           |

### Return type

[**EmploymentRelationship**](EmploymentRelationship.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                     | Response headers |
| ----------- | --------------------------------------------------------------- | ---------------- |
| **200**     | Relationship transitioned with evidence committed               | -                |
| **401**     | JWT missing, expired, or invalid                                | -                |
| **403**     | Service or participant-role authority denied                    | -                |
| **404**     | Resource not found (or not accessible to this tenant)           | -                |
| **409**     | Operation not valid in current state                            | -                |
| **503**     | Constitutional validation or evidence commitment is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updatePhaseBundle

> PhaseBundleSubscription updatePhaseBundle(contractId, updatePhaseBundleRequest)

Upgrade or change phase bundle

Changes the active phase bundle. Bundle upgrades are Decision Space expansions (C-003). CE.GrantAuthorityLicense is called. Customer must have selected the new bundle explicitly. DP-014 — maturity score at activation is recorded.

### Example

```ts
import {
  Configuration,
  EmploymentApi,
} from '';
import type { UpdatePhaseBundleOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new EmploymentApi(config);

  const body = {
    // string
    contractId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // UpdatePhaseBundleRequest
    updatePhaseBundleRequest: ...,
  } satisfies UpdatePhaseBundleOperationRequest;

  try {
    const data = await api.updatePhaseBundle(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                         | Type                                                    | Description | Notes                     |
| ---------------------------- | ------------------------------------------------------- | ----------- | ------------------------- |
| **contractId**               | `string`                                                |             | [Defaults to `undefined`] |
| **updatePhaseBundleRequest** | [UpdatePhaseBundleRequest](UpdatePhaseBundleRequest.md) |             |                           |

### Return type

[**PhaseBundleSubscription**](PhaseBundleSubscription.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`

### HTTP response details

| Status code | Description          | Response headers |
| ----------- | -------------------- | ---------------- |
| **200**     | Phase bundle updated | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
