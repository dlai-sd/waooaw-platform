# ConversationApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                  | HTTP request                                                                                       | Description                                                  |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [**cancelConversationExecution**](ConversationApi.md#cancelconversationexecution)       | **DELETE** /api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId} | Request cancellation of one professional response execution  |
| [**listConversationMessages**](ConversationApi.md#listconversationmessages)             | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/messages                    | Read the authoritative durable conversation timeline         |
| [**retryConversationMessage**](ConversationApi.md#retryconversationmessage)             | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/retry | Reconcile and retry one failed or unresolved contribution    |
| [**sendConversationMessage**](ConversationApi.md#sendconversationmessage)               | **POST** /api/v1/employment/relationships/{relationshipId}/conversation/messages                   | Send or replay one customer text contribution                |
| [**streamConversation**](ConversationApi.md#streamconversation)                         | **GET** /api/v1/employment/relationships/{relationshipId}/conversation/stream                      | Stream canonical conversation state as Server-Sent Events    |
| [**updateConversationReadPosition**](ConversationApi.md#updateconversationreadposition) | **PUT** /api/v1/employment/relationships/{relationshipId}/conversation/read-position               | Advance the authenticated participant\&#39;s unread position |

## cancelConversationExecution

> ConversationExecutionStatusV1 cancelConversationExecution(relationshipId, executionId, idempotencyKey)

Request cancellation of one professional response execution

Routes cancellation through BP to PR. Accepted partial content remains canonical and labelled incomplete. Cancellation does not delete history or release Emergency Stop.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { CancelConversationExecutionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Opaque professional execution UUID, authorized within the relationship
    executionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies CancelConversationExecutionRequest;

  try {
    const data = await api.cancelConversationExecution(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                                                              | Notes                     |
| ------------------ | -------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **executionId**    | `string` | Opaque professional execution UUID, authorized within the relationship                   | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**ConversationExecutionStatusV1**](ConversationExecutionStatusV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **202**     | Cancellation accepted                                                                                                | -                |
| **200**     | Existing terminal outcome replayed                                                                                   | -                |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                |
| **409**     | Idempotency identity conflicts or authoritative state must be reconciled                                             | -                |
| **423**     | Relationship execution is stopped; ordinary reconnect, retry, or cancellation cannot release it                      | -                |
| **503**     | Professional execution or constitutional dependency is unavailable and the outcome remains explicit                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listConversationMessages

> ConversationTimelinePageV1 listConversationMessages(relationshipId, cursor, afterCursor, limit)

Read the authoritative durable conversation timeline

Returns tenant- and relationship-authorized messages in ascending canonical sequence. &#x60;cursor&#x60; pages backward and &#x60;afterCursor&#x60; reconciles forward; they are mutually exclusive. Cursors are opaque and relationship-bound. This read does not advance the unread position.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { ListConversationMessagesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Opaque relationship-bound cursor for older timeline pages; mutually exclusive with afterCursor (optional)
    cursor: cursor_example,
    // string | Opaque relationship-bound cursor for forward reconnect reconciliation; mutually exclusive with cursor (optional)
    afterCursor: afterCursor_example,
    // number (optional)
    limit: 56,
  } satisfies ListConversationMessagesRequest;

  try {
    const data = await api.listConversationMessages(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                                                                           | Notes                                |
| ------------------ | -------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID                                                    | [Defaults to `undefined`]            |
| **cursor**         | `string` | Opaque relationship-bound cursor for older timeline pages; mutually exclusive with afterCursor        | [Optional] [Defaults to `undefined`] |
| **afterCursor**    | `string` | Opaque relationship-bound cursor for forward reconnect reconciliation; mutually exclusive with cursor | [Optional] [Defaults to `undefined`] |
| **limit**          | `number` |                                                                                                       | [Optional] [Defaults to `50`]        |

### Return type

[**ConversationTimelinePageV1**](ConversationTimelinePageV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Authoritative timeline page                                                                                          | -                |
| **400**     | Conversation request or schema version is malformed or unsupported                                                   | -                |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                |
| **410**     | Cursor can no longer be resumed; fetch a fresh authoritative timeline snapshot                                       | -                |
| **503**     | Professional execution or constitutional dependency is unavailable and the outcome remains explicit                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## retryConversationMessage

> ConversationSubmissionV1 retryConversationMessage(relationshipId, messageId, idempotencyKey)

Reconcile and retry one failed or unresolved contribution

Requires the original Idempotency-Key. BP verifies the stored canonical payload hash and retries the same logical message; it never mints a duplicate message. Completed outcomes replay. Changed content must be sent as a new message with a new key.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { RetryConversationMessageRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Opaque BP canonical message UUID, authorized within the relationship
    messageId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies RetryConversationMessageRequest;

  try {
    const data = await api.retryConversationMessage(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                                                              | Notes                     |
| ------------------ | -------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **messageId**      | `string` | Opaque BP canonical message UUID, authorized within the relationship                     | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**ConversationSubmissionV1**](ConversationSubmissionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **202**     | Existing logical message accepted for retry                                                                          | -                |
| **200**     | Prior terminal or accepted outcome replayed                                                                          | -                |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                |
| **409**     | Idempotency identity conflicts or authoritative state must be reconciled                                             | -                |
| **422**     | Message is not failed/unresolved or the original retry identity was not supplied                                     | -                |
| **423**     | Relationship execution is stopped; ordinary reconnect, retry, or cancellation cannot release it                      | -                |
| **503**     | Professional execution or constitutional dependency is unavailable and the outcome remains explicit                  | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## sendConversationMessage

> ConversationSubmissionV1 sendConversationMessage(relationshipId, idempotencyKey, sendConversationMessageRequestV1)

Send or replay one customer text contribution

Accepts durable responsibility for one customer contribution. A 202 response means accepted by BP; it does not mean delivered, professionally completed, or evidenced. Same actor, relationship, key, and canonical payload hash replay one outcome.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { SendConversationMessageRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // SendConversationMessageRequestV1
    sendConversationMessageRequestV1: ...,
  } satisfies SendConversationMessageRequest;

  try {
    const data = await api.sendConversationMessage(body);
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
| **relationshipId**                   | `string`                                                                | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**                   | `string`                                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **sendConversationMessageRequestV1** | [SendConversationMessageRequestV1](SendConversationMessageRequestV1.md) |                                                                                          |                           |

### Return type

[**ConversationSubmissionV1**](ConversationSubmissionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers      |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **202**     | Message accepted and professional execution queued                                                                   | -                     |
| **200**     | Prior identical outcome replayed                                                                                     | -                     |
| **400**     | Conversation request or schema version is malformed or unsupported                                                   | -                     |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                     |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                     |
| **409**     | Idempotency identity conflicts or authoritative state must be reconciled                                             | -                     |
| **423**     | Relationship execution is stopped; ordinary reconnect, retry, or cancellation cannot release it                      | -                     |
| **429**     | Conversation command is rate limited without losing its idempotency identity                                         | \* Retry-After - <br> |
| **503**     | Professional execution or constitutional dependency is unavailable and the outcome remains explicit                  | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## streamConversation

> ConversationStreamEventV1 streamConversation(relationshipId, lastEventID)

Stream canonical conversation state as Server-Sent Events

Authenticated BP public stream. The browser never connects to PR or a model provider. Last-Event-ID resumes within retention; expired state requires timeline reconciliation. Heartbeats contain no protected payload and the stream is never service-worker cached.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { StreamConversationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Last BP canonical SSE event ID received; never supplied in a URL (optional)
    lastEventID: lastEventID_example,
  } satisfies StreamConversationRequest;

  try {
    const data = await api.streamConversation(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                                      | Notes                                |
| ------------------ | -------- | ---------------------------------------------------------------- | ------------------------------------ |
| **relationshipId** | `string` | Tenant-scoped durable employment relationship UUID               | [Defaults to `undefined`]            |
| **lastEventID**    | `string` | Last BP canonical SSE event ID received; never supplied in a URL | [Optional] [Defaults to `undefined`] |

### Return type

[**ConversationStreamEventV1**](ConversationStreamEventV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `text/event-stream`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers                                  |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **200**     | Canonical versioned conversation event stream                                                                        | _ Cache-Control - <br> _ X-Accel-Buffering - <br> |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                                                 |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                                                 |
| **410**     | Cursor can no longer be resumed; fetch a fresh authoritative timeline snapshot                                       | -                                                 |
| **423**     | Relationship execution is stopped; ordinary reconnect, retry, or cancellation cannot release it                      | -                                                 |
| **503**     | Professional execution or constitutional dependency is unavailable and the outcome remains explicit                  | -                                                 |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateConversationReadPosition

> ConversationReadPositionV1 updateConversationReadPosition(relationshipId, idempotencyKey, updateConversationReadPositionRequestV1)

Advance the authenticated participant\&#39;s unread position

Advances monotonically to a visible canonical message. It cannot mark unseen content read and cannot move backward. The tenant and participant come only from the JWT.

### Example

```ts
import {
  Configuration,
  ConversationApi,
} from '';
import type { UpdateConversationReadPositionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ConversationApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // UpdateConversationReadPositionRequestV1
    updateConversationReadPositionRequestV1: ...,
  } satisfies UpdateConversationReadPositionRequest;

  try {
    const data = await api.updateConversationReadPosition(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                        | Type                                                                                  | Description                                                                              | Notes                     |
| ------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**                          | `string`                                                                              | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **idempotencyKey**                          | `string`                                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **updateConversationReadPositionRequestV1** | [UpdateConversationReadPositionRequestV1](UpdateConversationReadPositionRequestV1.md) |                                                                                          |                           |

### Return type

[**ConversationReadPositionV1**](ConversationReadPositionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                          | Response headers |
| ----------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Read position advanced or identical outcome replayed                                                                 | -                |
| **400**     | Conversation request or schema version is malformed or unsupported                                                   | -                |
| **401**     | Authenticated customer session is missing, invalid, or expired                                                       | -                |
| **404**     | Relationship or message is absent, inaccessible, or cross-tenant; one normalized shape prevents existence disclosure | -                |
| **409**     | Idempotency identity conflicts or authoritative state must be reconciled                                             | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
