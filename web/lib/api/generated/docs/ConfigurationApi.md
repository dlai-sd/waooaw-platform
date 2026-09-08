# ConfigurationApi

All URIs are relative to _http://localhost:5001_

| Method                                                                               | HTTP request                                                                              | Description                                                       |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [**conversationalConfigure**](ConfigurationApi.md#conversationalconfigure)           | **POST** /api/v1/configure/conversational                                                 | Configure agent via natural language conversation (C-039, AD-013) |
| [**getRelationshipConfiguration**](ConfigurationApi.md#getrelationshipconfiguration) | **GET** /api/v1/employment/relationships/{relationshipId}/workspace/configuration         | Read the universal relationship configuration state               |
| [**updateRelationshipOnboard**](ConfigurationApi.md#updaterelationshiponboard)       | **PUT** /api/v1/employment/relationships/{relationshipId}/workspace/configuration/onboard | Update lightweight Onboard presentation preferences               |

## conversationalConfigure

> ConversationalConfigResponse conversationalConfigure(conversationalConfigRequest)

Configure agent via natural language conversation (C-039, AD-013)

Accepts a natural language message from the customer and returns either: - A clarifying question (when more information is needed) - A proposed DecisionSpaceInput (when enough information has been gathered) The customer confirms the proposed Decision Space before it is committed. Target: complete configuration in under 15 minutes (AD-013).

### Example

```ts
import {
  Configuration,
  ConfigurationApi,
} from '';
import type { ConversationalConfigureRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConfigurationApi(config);

  const body = {
    // ConversationalConfigRequest
    conversationalConfigRequest: ...,
  } satisfies ConversationalConfigureRequest;

  try {
    const data = await api.conversationalConfigure(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                            | Type                                                          | Description | Notes |
| ------------------------------- | ------------------------------------------------------------- | ----------- | ----- |
| **conversationalConfigRequest** | [ConversationalConfigRequest](ConversationalConfigRequest.md) |             |       |

### Return type

[**ConversationalConfigResponse**](ConversationalConfigResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                   | Response headers |
| ----------- | --------------------------------------------- | ---------------- |
| **200**     | Clarifying question or proposed configuration | -                |
| **401**     | JWT missing, expired, or invalid              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getRelationshipConfiguration

> RelationshipConfigurationV1 getRelationshipConfiguration(relationshipId)

Read the universal relationship configuration state

Returns exactly two configuration items: Onboard and Induct. Induct is a customer-facing continuation surface over accepted relationship and conversation truth, not a new lifecycle service state.

### Example

```ts
import {
  Configuration,
  ConfigurationApi,
} from '';
import type { GetRelationshipConfigurationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConfigurationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetRelationshipConfigurationRequest;

  try {
    const data = await api.getRelationshipConfiguration(body);
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

[**RelationshipConfigurationV1**](RelationshipConfigurationV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Relationship configuration state                                        | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateRelationshipOnboard

> RelationshipConfigurationV1 updateRelationshipOnboard(relationshipId, idempotencyKey, relationshipOnboardRequestV1)

Update lightweight Onboard presentation preferences

Persists only accepted Onboard preferences for the relationship. Induct progression, employment lifecycle, authority, and conversation truth are not mutated by this operation.

### Example

```ts
import {
  Configuration,
  ConfigurationApi,
} from '';
import type { UpdateRelationshipOnboardRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConfigurationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // RelationshipOnboardRequestV1
    relationshipOnboardRequestV1: ...,
  } satisfies UpdateRelationshipOnboardRequest;

  try {
    const data = await api.updateRelationshipOnboard(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                             | Type                                                            | Description                                                                              | Notes                     |
| -------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**               | `string`                                                        | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**               | `string`                                                        | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **relationshipOnboardRequestV1** | [RelationshipOnboardRequestV1](RelationshipOnboardRequestV1.md) |                                                                                          |                           |

### Return type

[**RelationshipConfigurationV1**](RelationshipConfigurationV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                             | Response headers |
| ----------- | ----------------------------------------------------------------------- | ---------------- |
| **200**     | Onboard preferences updated or replayed                                 | -                |
| **400**     | Workspace request is malformed or unsupported                           | -                |
| **401**     | Workspace session is missing, invalid, or expired                       | -                |
| **404**     | Relationship or child resource is absent, inaccessible, or cross-tenant | -                |
| **409**     | Idempotency or expected-version conflict requires reconciliation        | -                |
| **423**     | Command is blocked by policy, assurance, authority, or owner dependency | -                |
| **503**     | Required owner projection or constitutional dependency is unavailable   | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
