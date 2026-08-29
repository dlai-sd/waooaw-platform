# IdentityApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                    | HTTP request                                                                          | Description                                                        |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [**approveIdentityAccountLink**](IdentityApi.md#approveidentityaccountlink)               | **POST** /api/v1/identity/account-links/{linkId}/approve                              | Explicitly approve a WhatsApp-to-web account link                  |
| [**completeIdentityRegistration**](IdentityApi.md#completeidentityregistration)           | **POST** /api/v1/identity/registrations/{registrationId}/complete                     | Complete registration by minting or reusing one account            |
| [**confirmAccountMobileVerification**](IdentityApi.md#confirmaccountmobileverification)   | **POST** /api/v1/identity/mobile-verifications/confirm                                | Confirm progressive mobile verification                            |
| [**confirmIdentityEmailVerification**](IdentityApi.md#confirmidentityemailverification)   | **POST** /api/v1/identity/registrations/{registrationId}/email-verifications/confirm  | Confirm mandatory email verification                               |
| [**confirmIdentityMobileVerification**](IdentityApi.md#confirmidentitymobileverification) | **POST** /api/v1/identity/registrations/{registrationId}/mobile-verifications/confirm | Confirm optional mobile verification during registration           |
| [**getIdentityAccountLink**](IdentityApi.md#getidentityaccountlink)                       | **GET** /api/v1/identity/account-links/{linkId}                                       | Get caller-bound account-link status                               |
| [**getIdentityRegistration**](IdentityApi.md#getidentityregistration)                     | **GET** /api/v1/identity/registrations/{registrationId}                               | Get the caller-bound registration state                            |
| [**getIdentitySession**](IdentityApi.md#getidentitysession)                               | **GET** /api/v1/identity/session                                                      | Get the current customer identity session projection               |
| [**listIdentityProviders**](IdentityApi.md#listidentityproviders)                         | **GET** /api/v1/identity/providers                                                    | List customer authentication choices for this environment          |
| [**startAccountMobileVerification**](IdentityApi.md#startaccountmobileverification)       | **POST** /api/v1/identity/mobile-verifications                                        | Start or replay progressive mobile verification                    |
| [**startIdentityAccountLink**](IdentityApi.md#startidentityaccountlinkoperation)          | **POST** /api/v1/identity/account-links                                               | Start or replay a WhatsApp-to-web account link                     |
| [**startIdentityEmailVerification**](IdentityApi.md#startidentityemailverification)       | **POST** /api/v1/identity/registrations/{registrationId}/email-verifications          | Start or replay mandatory email verification                       |
| [**startIdentityMobileVerification**](IdentityApi.md#startidentitymobileverification)     | **POST** /api/v1/identity/registrations/{registrationId}/mobile-verifications         | Optionally start or replay mobile verification during registration |
| [**startIdentityRegistration**](IdentityApi.md#startidentityregistrationoperation)        | **POST** /api/v1/identity/registrations                                               | Start or replay a customer registration                            |
| [**updateIdentityRegistrationProfile**](IdentityApi.md#updateidentityregistrationprofile) | **PUT** /api/v1/identity/registrations/{registrationId}/profile                       | Set the minimum registration profile                               |

## approveIdentityAccountLink

> IdentityAccountLink approveIdentityAccountLink(linkId, idempotencyKey)

Explicitly approve a WhatsApp-to-web account link

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ApproveIdentityAccountLinkRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque account-link challenge identifier bound to the authenticated account
    linkId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies ApproveIdentityAccountLinkRequest;

  try {
    const data = await api.approveIdentityAccountLink(body);
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
| **linkId**         | `string` | Opaque account-link challenge identifier bound to the authenticated account              | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**IdentityAccountLink**](IdentityAccountLink.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Approval recorded; fresh ADR-023 confirmation remains required                                                                  | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## completeIdentityRegistration

> IdentityCompletion completeIdentityRegistration(registrationId, idempotencyKey)

Complete registration by minting or reusing one account

Requires confirmed email and the approved minimum profile; mobile verification is optional until a server-classified consequential action. Duplicate resolution is deterministic and proof-gated. ACCOUNT_CREATED and ACCOUNT_REUSED have the same customer-facing success treatment. No Employment Relationship is created.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { CompleteIdentityRegistrationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies CompleteIdentityRegistrationRequest;

  try {
    const data = await api.completeIdentityRegistration(body);
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
| **registrationId** | `string` | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**IdentityCompletion**](IdentityCompletion.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Account created, reused, or replayed                                                                                            | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **422**     | Mandatory identity verification or minimum profile completion remains outstanding                                               | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## confirmAccountMobileVerification

> IdentityMobileStatus confirmAccountMobileVerification(idempotencyKey, confirmIdentityVerificationRequest)

Confirm progressive mobile verification

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ConfirmAccountMobileVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ConfirmIdentityVerificationRequest
    confirmIdentityVerificationRequest: ...,
  } satisfies ConfirmAccountMobileVerificationRequest;

  try {
    const data = await api.confirmAccountMobileVerification(body);
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
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **confirmIdentityVerificationRequest** | [ConfirmIdentityVerificationRequest](ConfirmIdentityVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityMobileStatus**](IdentityMobileStatus.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **200**     | Mobile proof accepted or replayed                                           | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **410**     | Verification or link challenge is no longer usable                          | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## confirmIdentityEmailVerification

> IdentityRegistration confirmIdentityEmailVerification(registrationId, idempotencyKey, confirmIdentityVerificationRequest)

Confirm mandatory email verification

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ConfirmIdentityEmailVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ConfirmIdentityVerificationRequest
    confirmIdentityVerificationRequest: ...,
  } satisfies ConfirmIdentityEmailVerificationRequest;

  try {
    const data = await api.confirmIdentityEmailVerification(body);
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
| **registrationId**                     | `string`                                                                    | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **confirmIdentityVerificationRequest** | [ConfirmIdentityVerificationRequest](ConfirmIdentityVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityRegistration**](IdentityRegistration.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **200**     | Email proof accepted or replayed                                                                                                | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## confirmIdentityMobileVerification

> IdentityRegistration confirmIdentityMobileVerification(registrationId, idempotencyKey, confirmIdentityVerificationRequest)

Confirm optional mobile verification during registration

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ConfirmIdentityMobileVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // ConfirmIdentityVerificationRequest
    confirmIdentityVerificationRequest: ...,
  } satisfies ConfirmIdentityMobileVerificationRequest;

  try {
    const data = await api.confirmIdentityMobileVerification(body);
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
| **registrationId**                     | `string`                                                                    | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **confirmIdentityVerificationRequest** | [ConfirmIdentityVerificationRequest](ConfirmIdentityVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityRegistration**](IdentityRegistration.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **200**     | Mobile proof accepted or replayed                                                                                               | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getIdentityAccountLink

> IdentityAccountLink getIdentityAccountLink(linkId)

Get caller-bound account-link status

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { GetIdentityAccountLinkRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque account-link challenge identifier bound to the authenticated account
    linkId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetIdentityAccountLinkRequest;

  try {
    const data = await api.getIdentityAccountLink(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name       | Type     | Description                                                                 | Notes                     |
| ---------- | -------- | --------------------------------------------------------------------------- | ------------------------- |
| **linkId** | `string` | Opaque account-link challenge identifier bound to the authenticated account | [Defaults to `undefined`] |

### Return type

[**IdentityAccountLink**](IdentityAccountLink.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Privacy-safe link status                                                                                                        | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getIdentityRegistration

> IdentityRegistration getIdentityRegistration(registrationId)

Get the caller-bound registration state

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { GetIdentityRegistrationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies GetIdentityRegistrationRequest;

  try {
    const data = await api.getIdentityRegistration(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name               | Type     | Description                                                                 | Notes                     |
| ------------------ | -------- | --------------------------------------------------------------------------- | ------------------------- |
| **registrationId** | `string` | Opaque registration identifier bound to the authenticated pre-account actor | [Defaults to `undefined`] |

### Return type

[**IdentityRegistration**](IdentityRegistration.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Privacy-safe registration projection                                                                                            | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getIdentitySession

> IdentitySession getIdentitySession()

Get the current customer identity session projection

Returns current customer roles and capabilities after Business Platform validates the Keycloak token and reloads current account and membership state. Capabilities are server-derived authorization hints for user experience only; every command is authorized again at execution time. Institutional identity is excluded.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { GetIdentitySessionRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.getIdentitySession();
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

[**IdentitySession**](IdentitySession.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **200**     | Current privacy-safe customer session projection                            | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listIdentityProviders

> IdentityProviderCollection listIdentityProviders()

List customer authentication choices for this environment

Returns the reviewed Google, Facebook, Apple, and email choices in display order. Availability is an environment projection, not a provider health probe, and exposes no client secret, internal endpoint, readiness evidence, or account-existence fact.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { ListIdentityProvidersRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new IdentityApi();

  try {
    const data = await api.listIdentityProviders();
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

[**IdentityProviderCollection**](IdentityProviderCollection.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers |
| ----------- | --------------------------------------------------------------------- | ---------------- |
| **200**     | Ordered customer authentication choices                               | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startAccountMobileVerification

> IdentityVerificationChallenge startAccountMobileVerification(idempotencyKey, startMobileVerificationRequest)

Start or replay progressive mobile verification

Starts mobile proof for an authenticated account. Basic entry and exploration do not require this proof. A consequential command may require it through server-owned step-up. The accepted response does not disclose whether the mobile is associated elsewhere.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartAccountMobileVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartMobileVerificationRequest
    startMobileVerificationRequest: ...,
  } satisfies StartAccountMobileVerificationRequest;

  try {
    const data = await api.startAccountMobileVerification(body);
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
| **idempotencyKey**                 | `string`                                                            | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startMobileVerificationRequest** | [StartMobileVerificationRequest](StartMobileVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityVerificationChallenge**](IdentityVerificationChallenge.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **202**     | Challenge accepted or replayed without identity-existence disclosure        | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityAccountLink

> IdentityAccountLink startIdentityAccountLink(idempotencyKey, startIdentityAccountLinkRequest)

Start or replay a WhatsApp-to-web account link

Requires a freshly authenticated AAL3 portal session. The server selects or validates an opaque verified-mobile proof; raw mobile and client-generated hashes are not authority.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartIdentityAccountLinkOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartIdentityAccountLinkRequest
    startIdentityAccountLinkRequest: ...,
  } satisfies StartIdentityAccountLinkOperationRequest;

  try {
    const data = await api.startIdentityAccountLink(body);
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
| **idempotencyKey**                  | `string`                                                              | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startIdentityAccountLinkRequest** | [StartIdentityAccountLinkRequest](StartIdentityAccountLinkRequest.md) |                                                                                          |                           |

### Return type

[**IdentityAccountLink**](IdentityAccountLink.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **201**     | Link challenge started                                                      | -                     |
| **200**     | Prior identical link outcome replayed                                       | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityEmailVerification

> IdentityVerificationChallenge startIdentityEmailVerification(registrationId, idempotencyKey, startEmailVerificationRequest)

Start or replay mandatory email verification

Returns the same accepted shape and timing class whether or not the email is already known.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartIdentityEmailVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartEmailVerificationRequest
    startEmailVerificationRequest: ...,
  } satisfies StartIdentityEmailVerificationRequest;

  try {
    const data = await api.startIdentityEmailVerification(body);
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
| **registrationId**                | `string`                                                          | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey**                | `string`                                                          | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startEmailVerificationRequest** | [StartEmailVerificationRequest](StartEmailVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityVerificationChallenge**](IdentityVerificationChallenge.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **202**     | Challenge accepted or replayed without identity-existence disclosure                                                            | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityMobileVerification

> IdentityVerificationChallenge startIdentityMobileVerification(registrationId, idempotencyKey, startMobileVerificationRequest)

Optionally start or replay mobile verification during registration

Uses an approved OTP path when no ADR-023 Meta-verified proof is already bound. Returns no account-existence information.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartIdentityMobileVerificationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartMobileVerificationRequest
    startMobileVerificationRequest: ...,
  } satisfies StartIdentityMobileVerificationRequest;

  try {
    const data = await api.startIdentityMobileVerification(body);
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
| **registrationId**                 | `string`                                                            | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey**                 | `string`                                                            | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startMobileVerificationRequest** | [StartMobileVerificationRequest](StartMobileVerificationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityVerificationChallenge**](IdentityVerificationChallenge.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **202**     | Challenge accepted or replayed without identity-existence disclosure                                                            | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityRegistration

> IdentityRegistration startIdentityRegistration(idempotencyKey, startIdentityRegistrationRequest)

Start or replay a customer registration

Starts registration from a validated Keycloak pre-account session. Provider claims and authentication path are derived only from that brokered session. Duplicate resolution occurs only after verified identity proof; this operation never exposes whether an arbitrary email or mobile already exists and never creates an Employment Relationship. ADR-023 WhatsApp continuation uses an internal server-to-server Identity Boundary adapter, never this browser operation or a browser-held Phone Identity Service token.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartIdentityRegistrationOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // StartIdentityRegistrationRequest
    startIdentityRegistrationRequest: ...,
  } satisfies StartIdentityRegistrationOperationRequest;

  try {
    const data = await api.startIdentityRegistration(body);
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
| **idempotencyKey**                   | `string`                                                                | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startIdentityRegistrationRequest** | [StartIdentityRegistrationRequest](StartIdentityRegistrationRequest.md) |                                                                                          |                           |

### Return type

[**IdentityRegistration**](IdentityRegistration.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **201**     | Registration started                                                        | -                     |
| **200**     | Prior identical outcome replayed                                            | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateIdentityRegistrationProfile

> IdentityRegistration updateIdentityRegistrationProfile(registrationId, idempotencyKey, identityRegistrationProfileRequest)

Set the minimum registration profile

Accepts only display name, business name, business domain, and language preference.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { UpdateIdentityRegistrationProfileRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: PreAccountBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string | Opaque registration identifier bound to the authenticated pre-account actor
    registrationId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // IdentityRegistrationProfileRequest
    identityRegistrationProfileRequest: ...,
  } satisfies UpdateIdentityRegistrationProfileRequest;

  try {
    const data = await api.updateIdentityRegistrationProfile(body);
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
| **registrationId**                     | `string`                                                                    | Opaque registration identifier bound to the authenticated pre-account actor              | [Defaults to `undefined`] |
| **idempotencyKey**                     | `string`                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **identityRegistrationProfileRequest** | [IdentityRegistrationProfileRequest](IdentityRegistrationProfileRequest.md) |                                                                                          |                           |

### Return type

[**IdentityRegistration**](IdentityRegistration.md)

### Authorization

[PreAccountBearerAuth](../README.md#PreAccountBearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Registration profile accepted or replayed                                                                                       | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **422**     | Mandatory identity verification or minimum profile completion remains outstanding                                               | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
