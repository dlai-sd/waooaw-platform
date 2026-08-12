# VoiceContributionsApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                              | HTTP request                                                                                                  | Description                                                     |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [**cancelVoiceContributionSession**](VoiceContributionsApi.md#cancelvoicecontributionsession)       | **POST** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}/cancel    | Cancel an unsent voice contribution session                     |
| [**createVoiceContributionSession**](VoiceContributionsApi.md#createvoicecontributionsession)       | **POST** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions                       | Create or replay a voice contribution session                   |
| [**getVoiceContributionSession**](VoiceContributionsApi.md#getvoicecontributionsession)             | **GET** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}            | Reconcile authoritative voice contribution state                |
| [**getVoiceContributionTranscript**](VoiceContributionsApi.md#getvoicecontributiontranscript)       | **GET** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}/transcript | Get the provider-neutral transcript review state                |
| [**requestVoicePayloadErasure**](VoiceContributionsApi.md#requestvoicepayloaderasure)               | **POST** /api/v1/employment/relationships/{relationshipId}/voice-contributions/{contributionId}/erasure       | Request Evidence First erasure of voice payload                 |
| [**sendVoiceContribution**](VoiceContributionsApi.md#sendvoicecontribution)                         | **POST** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}/send      | Explicitly send the reviewed voice contribution                 |
| [**submitVoiceContributionCorrection**](VoiceContributionsApi.md#submitvoicecontributioncorrection) | **PUT** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}/correction | Publish a new customer-reviewed transcript version              |
| [**uploadVoiceContributionAudio**](VoiceContributionsApi.md#uploadvoicecontributionaudio)           | **POST** /api/v1/employment/relationships/{relationshipId}/voice-contributions/sessions/{sessionId}/audio     | Upload one bounded voice draft for validation and transcription |

## cancelVoiceContributionSession

> VoiceContributionOutcomeV1 cancelVoiceContributionSession(relationshipId, sessionId, idempotencyKey, cancelVoiceContributionRequestV1)

Cancel an unsent voice contribution session

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { CancelVoiceContributionSessionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // CancelVoiceContributionRequestV1
    cancelVoiceContributionRequestV1: ...,
  } satisfies CancelVoiceContributionSessionRequest;

  try {
    const data = await api.cancelVoiceContributionSession(body);
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
| **sessionId**                        | `string`                                                                |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                   | `string`                                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **cancelVoiceContributionRequestV1** | [CancelVoiceContributionRequestV1](CancelVoiceContributionRequestV1.md) |                                                                                          |                           |

### Return type

[**VoiceContributionOutcomeV1**](VoiceContributionOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                 | Response headers |
| ----------- | ----------------------------------------------------------- | ---------------- |
| **200**     | Cancellation or prior terminal outcome                      | -                |
| **401**     | Authentication is required                                  | -                |
| **404**     | Voice session is absent or inaccessible without enumeration | -                |
| **409**     | State, version, or idempotency conflict                     | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped         | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## createVoiceContributionSession

> VoiceContributionSessionV1 createVoiceContributionSession(relationshipId, idempotencyKey, createVoiceContributionSessionRequestV1)

Create or replay a voice contribution session

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { CreateVoiceContributionSessionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // CreateVoiceContributionSessionRequestV1
    createVoiceContributionSessionRequestV1: ...,
  } satisfies CreateVoiceContributionSessionRequest;

  try {
    const data = await api.createVoiceContributionSession(body);
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
| **createVoiceContributionSessionRequestV1** | [CreateVoiceContributionSessionRequestV1](CreateVoiceContributionSessionRequestV1.md) |                                                                                          |                           |

### Return type

[**VoiceContributionSessionV1**](VoiceContributionSessionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **201**     | Session created                                                       | -                |
| **200**     | Prior identical session replayed                                      | -                |
| **400**     | Voice request or state is invalid                                     | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **409**     | State, version, or idempotency conflict                               | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped                   | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getVoiceContributionSession

> VoiceContributionSessionV1 getVoiceContributionSession(relationshipId, sessionId)

Reconcile authoritative voice contribution state

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { GetVoiceContributionSessionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetVoiceContributionSessionRequest;

  try {
    const data = await api.getVoiceContributionSession(body);
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
| **sessionId**      | `string` |                                                    | [Defaults to `undefined`] |

### Return type

[**VoiceContributionSessionV1**](VoiceContributionSessionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **200**     | Current authoritative session                                         | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getVoiceContributionTranscript

> VoiceTranscriptV1 getVoiceContributionTranscript(relationshipId, sessionId)

Get the provider-neutral transcript review state

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { GetVoiceContributionTranscriptRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetVoiceContributionTranscriptRequest;

  try {
    const data = await api.getVoiceContributionTranscript(body);
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
| **sessionId**      | `string` |                                                    | [Defaults to `undefined`] |

### Return type

[**VoiceTranscriptV1**](VoiceTranscriptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **200**     | Transcript state                                                      | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## requestVoicePayloadErasure

> VoicePayloadErasureReceiptV1 requestVoicePayloadErasure(relationshipId, contributionId, idempotencyKey, voicePayloadErasureRequestV1)

Request Evidence First erasure of voice payload

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { RequestVoicePayloadErasureRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    contributionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // VoicePayloadErasureRequestV1
    voicePayloadErasureRequestV1: ...,
  } satisfies RequestVoicePayloadErasureRequest;

  try {
    const data = await api.requestVoicePayloadErasure(body);
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
| **contributionId**               | `string`                                                        |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**               | `string`                                                        | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **voicePayloadErasureRequestV1** | [VoicePayloadErasureRequestV1](VoicePayloadErasureRequestV1.md) |                                                                                          |                           |

### Return type

[**VoicePayloadErasureReceiptV1**](VoicePayloadErasureReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **202**     | Erasure accepted                                                      | -                |
| **200**     | Prior identical outcome replayed                                      | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **409**     | State, version, or idempotency conflict                               | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped                   | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## sendVoiceContribution

> VoiceContributionOutcomeV1 sendVoiceContribution(relationshipId, sessionId, idempotencyKey, sendVoiceContributionRequestV1)

Explicitly send the reviewed voice contribution

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { SendVoiceContributionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // SendVoiceContributionRequestV1
    sendVoiceContributionRequestV1: ...,
  } satisfies SendVoiceContributionRequest;

  try {
    const data = await api.sendVoiceContribution(body);
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
| **relationshipId**                 | `string`                                                            | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **sessionId**                      | `string`                                                            |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**                 | `string`                                                            | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **sendVoiceContributionRequestV1** | [SendVoiceContributionRequestV1](SendVoiceContributionRequestV1.md) |                                                                                          |                           |

### Return type

[**VoiceContributionOutcomeV1**](VoiceContributionOutcomeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **200**     | Authoritative Evidence First outcome                                  | -                |
| **400**     | Voice request or state is invalid                                     | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **409**     | State, version, or idempotency conflict                               | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped                   | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## submitVoiceContributionCorrection

> VoiceCorrectionReceiptV1 submitVoiceContributionCorrection(relationshipId, sessionId, idempotencyKey, voiceCorrectionRequestV1)

Publish a new customer-reviewed transcript version

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { SubmitVoiceContributionCorrectionRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // VoiceCorrectionRequestV1
    voiceCorrectionRequestV1: ...,
  } satisfies SubmitVoiceContributionCorrectionRequest;

  try {
    const data = await api.submitVoiceContributionCorrection(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                         | Type                                                    | Description                                                                              | Notes                     |
| ---------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **relationshipId**           | `string`                                                | Tenant-scoped durable employment relationship UUID                                       | [Defaults to `undefined`] |
| **sessionId**                | `string`                                                |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey**           | `string`                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **voiceCorrectionRequestV1** | [VoiceCorrectionRequestV1](VoiceCorrectionRequestV1.md) |                                                                                          |                           |

### Return type

[**VoiceCorrectionReceiptV1**](VoiceCorrectionReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                 | Response headers |
| ----------- | ----------------------------------------------------------- | ---------------- |
| **200**     | Correction version recorded                                 | -                |
| **400**     | Voice request or state is invalid                           | -                |
| **401**     | Authentication is required                                  | -                |
| **404**     | Voice session is absent or inaccessible without enumeration | -                |
| **409**     | State, version, or idempotency conflict                     | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped         | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## uploadVoiceContributionAudio

> VoiceUploadReceiptV1 uploadVoiceContributionAudio(relationshipId, sessionId, idempotencyKey, audio)

Upload one bounded voice draft for validation and transcription

### Example

```ts
import {
  Configuration,
  VoiceContributionsApi,
} from '';
import type { UploadVoiceContributionAudioRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new VoiceContributionsApi(config);

  const body = {
    // string | Tenant-scoped durable employment relationship UUID
    relationshipId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    sessionId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // Blob
    audio: BINARY_DATA_HERE,
  } satisfies UploadVoiceContributionAudioRequest;

  try {
    const data = await api.uploadVoiceContributionAudio(body);
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
| **sessionId**      | `string` |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **audio**          | `Blob`   |                                                                                          | [Defaults to `undefined`] |

### Return type

[**VoiceUploadReceiptV1**](VoiceUploadReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `multipart/form-data`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **202**     | Audio accepted for fail-closed validation                             | -                |
| **400**     | Voice request or state is invalid                                     | -                |
| **401**     | Authentication is required                                            | -                |
| **404**     | Voice session is absent or inaccessible without enumeration           | -                |
| **409**     | State, version, or idempotency conflict                               | -                |
| **413**     | Product duration or size limit exceeded                               | -                |
| **415**     | Media type or validated content is unsupported                        | -                |
| **423**     | Voice operation is blocked, quarantined, or stopped                   | -                |
| **503**     | Required owner, scanner, provider, or evidence service is unavailable | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
