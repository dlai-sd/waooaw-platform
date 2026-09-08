# NotificationsApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                 | HTTP request                                                | Description                                            |
| -------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------ |
| [**acknowledgeCustomerAlert**](NotificationsApi.md#acknowledgecustomeralert)           | **POST** /api/v1/notifications/alerts/{alertId}/acknowledge | Acknowledge an alert without approving underlying work |
| [**getNotificationPreferences**](NotificationsApi.md#getnotificationpreferences)       | **GET** /api/v1/notifications/preferences                   | Get customer notification preferences                  |
| [**listCustomerAlerts**](NotificationsApi.md#listcustomeralerts)                       | **GET** /api/v1/notifications/alerts                        | Read the customer portal alerts feed                   |
| [**markCustomerAlertRead**](NotificationsApi.md#markcustomeralertread)                 | **POST** /api/v1/notifications/alerts/{alertId}/read        | Mark an alert as read                                  |
| [**updateNotificationPreferences**](NotificationsApi.md#updatenotificationpreferences) | **PUT** /api/v1/notifications/preferences                   | Update customer notification preferences               |

## acknowledgeCustomerAlert

> CustomerAlertV1 acknowledgeCustomerAlert(alertId, idempotencyKey, customerAlertMutationRequestV1)

Acknowledge an alert without approving underlying work

Records that the authenticated actor acknowledged the alert itself. This does not execute or approve the underlying relationship, billing, or authority action.

### Example

```ts
import {
  Configuration,
  NotificationsApi,
} from '';
import type { AcknowledgeCustomerAlertRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new NotificationsApi(config);

  const body = {
    // string | Opaque customer alert identifier bound to the authenticated tenant and actor
    alertId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // CustomerAlertMutationRequestV1
    customerAlertMutationRequestV1: ...,
  } satisfies AcknowledgeCustomerAlertRequest;

  try {
    const data = await api.acknowledgeCustomerAlert(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                               | Type                                                                | Description                                                                              | Notes                     |
| ---------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **alertId**                        | `string`                                                            | Opaque customer alert identifier bound to the authenticated tenant and actor             | [Defaults to `undefined`] |
| **idempotencyKey**                 | `string`                                                            | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **customerAlertMutationRequestV1** | [CustomerAlertMutationRequestV1](CustomerAlertMutationRequestV1.md) |                                                                                          |                           |

### Return type

[**CustomerAlertV1**](CustomerAlertV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Alert acknowledged or replayed                        | -                |
| **400**     | Malformed request                                     | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **409**     | Operation not valid in current state                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getNotificationPreferences

> NotificationPreferences getNotificationPreferences()

Get customer notification preferences

### Example

```ts
import { Configuration, NotificationsApi } from "";
import type { GetNotificationPreferencesRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new NotificationsApi(config);

  try {
    const data = await api.getNotificationPreferences();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**NotificationPreferences**](NotificationPreferences.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description              | Response headers |
| ----------- | ------------------------ | ---------------- |
| **200**     | Notification preferences | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listCustomerAlerts

> CustomerAlertPageV1 listCustomerAlerts(cursor, limit)

Read the customer portal alerts feed

Returns a cursor-paginated cross-relationship alerts feed that preserves server-owned order, type, destination, and read versus acknowledge semantics.

### Example

```ts
import { Configuration, NotificationsApi } from "";
import type { ListCustomerAlertsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new NotificationsApi(config);

  const body = {
    // string (optional)
    cursor: cursor_example,
    // number (optional)
    limit: 56,
  } satisfies ListCustomerAlertsRequest;

  try {
    const data = await api.listCustomerAlerts(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name       | Type     | Description | Notes                                |
| ---------- | -------- | ----------- | ------------------------------------ |
| **cursor** | `string` |             | [Optional] [Defaults to `undefined`] |
| **limit**  | `number` |             | [Optional] [Defaults to `20`]        |

### Return type

[**CustomerAlertPageV1**](CustomerAlertPageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                      | Response headers |
| ----------- | -------------------------------- | ---------------- |
| **200**     | Customer alerts page             | -                |
| **401**     | JWT missing, expired, or invalid | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## markCustomerAlertRead

> CustomerAlertV1 markCustomerAlertRead(alertId, idempotencyKey, customerAlertMutationRequestV1)

Mark an alert as read

Marks an alert as read for the authenticated actor. Read is not approval, evidence, or completion.

### Example

```ts
import {
  Configuration,
  NotificationsApi,
} from '';
import type { MarkCustomerAlertReadRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new NotificationsApi(config);

  const body = {
    // string | Opaque customer alert identifier bound to the authenticated tenant and actor
    alertId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // CustomerAlertMutationRequestV1
    customerAlertMutationRequestV1: ...,
  } satisfies MarkCustomerAlertReadRequest;

  try {
    const data = await api.markCustomerAlertRead(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                               | Type                                                                | Description                                                                              | Notes                     |
| ---------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **alertId**                        | `string`                                                            | Opaque customer alert identifier bound to the authenticated tenant and actor             | [Defaults to `undefined`] |
| **idempotencyKey**                 | `string`                                                            | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **customerAlertMutationRequestV1** | [CustomerAlertMutationRequestV1](CustomerAlertMutationRequestV1.md) |                                                                                          |                           |

### Return type

[**CustomerAlertV1**](CustomerAlertV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Alert marked read or replayed                         | -                |
| **400**     | Malformed request                                     | -                |
| **401**     | JWT missing, expired, or invalid                      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |
| **409**     | Operation not valid in current state                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateNotificationPreferences

> updateNotificationPreferences(notificationPreferences)

Update customer notification preferences

Sets which channels receive which notification types. Channel preferences are stored per organisation and used by all delivery pipelines (Maturity Report, monthly narratives, approval requests, self-governance alerts).

### Example

```ts
import {
  Configuration,
  NotificationsApi,
} from '';
import type { UpdateNotificationPreferencesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new NotificationsApi(config);

  const body = {
    // NotificationPreferences
    notificationPreferences: ...,
  } satisfies UpdateNotificationPreferencesRequest;

  try {
    const data = await api.updateNotificationPreferences(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                        | Type                                                  | Description | Notes |
| --------------------------- | ----------------------------------------------------- | ----------- | ----- |
| **notificationPreferences** | [NotificationPreferences](NotificationPreferences.md) |             |       |

### Return type

`void` (Empty response body)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: Not defined

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Preferences updated | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
