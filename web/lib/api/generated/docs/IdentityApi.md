# IdentityApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                        | HTTP request                                                                          | Description                                                                           |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [**approveIdentityAccountLink**](IdentityApi.md#approveidentityaccountlink)                   | **POST** /api/v1/identity/account-links/{linkId}/approve                              | Explicitly approve a WhatsApp-to-web account link                                     |
| [**cancelIdentityAccountLink**](IdentityApi.md#cancelidentityaccountlink)                     | **POST** /api/v1/identity/account-links/{linkId}/cancel                               | Cancel a pending WhatsApp account link                                                |
| [**cancelIdentityPhoneChange**](IdentityApi.md#cancelidentityphonechange)                     | **POST** /api/v1/identity/phone-changes/{challengeId}/cancel                          | Cancel an uncompleted phone change without changing the current number                |
| [**completeIdentityRegistration**](IdentityApi.md#completeidentityregistration)               | **POST** /api/v1/identity/registrations/{registrationId}/complete                     | Complete registration by minting or reusing one account                               |
| [**confirmAccountMobileVerification**](IdentityApi.md#confirmaccountmobileverification)       | **POST** /api/v1/identity/mobile-verifications/confirm                                | Confirm progressive mobile verification                                               |
| [**confirmIdentityEmailVerification**](IdentityApi.md#confirmidentityemailverification)       | **POST** /api/v1/identity/registrations/{registrationId}/email-verifications/confirm  | Confirm mandatory email verification                                                  |
| [**confirmIdentityMobileVerification**](IdentityApi.md#confirmidentitymobileverification)     | **POST** /api/v1/identity/registrations/{registrationId}/mobile-verifications/confirm | Confirm required WhatsApp-number verification during registration                     |
| [**confirmIdentityPhoneChange**](IdentityApi.md#confirmidentityphonechange)                   | **POST** /api/v1/identity/phone-changes/confirm                                       | Confirm OTP and explicit consent; atomically replace the number and revoke old access |
| [**createIdentityProviderLink**](IdentityApi.md#createidentityproviderlink)                   | **POST** /api/v1/identity/provider-links                                              | Start provider-neutral proof-of-control linking                                       |
| [**createIdentitySessionRevocation**](IdentityApi.md#createidentitysessionrevocation)         | **POST** /api/v1/identity/session-revocations                                         | Record a provider-neutral application-session revocation intent                       |
| [**deleteIdentityProviderLink**](IdentityApi.md#deleteidentityproviderlink)                   | **DELETE** /api/v1/identity/provider-links/{linkId}                                   | Unlink one provider-neutral authentication method                                     |
| [**getCustomerProfile**](IdentityApi.md#getcustomerprofile)                                   | **GET** /api/v1/identity/profile                                                      | Get the current customer profile projection for the portal                            |
| [**getCustomerSettings**](IdentityApi.md#getcustomersettings)                                 | **GET** /api/v1/identity/settings                                                     | Get customer portal settings                                                          |
| [**getIdentityAccountLink**](IdentityApi.md#getidentityaccountlink)                           | **GET** /api/v1/identity/account-links/{linkId}                                       | Get caller-bound account-link status                                                  |
| [**getIdentityPhoneChange**](IdentityApi.md#getidentityphonechange)                           | **GET** /api/v1/identity/phone-changes                                                | Recover the current owner\&#39;s latest phone-change state without resending          |
| [**getIdentityRegistration**](IdentityApi.md#getidentityregistration)                         | **GET** /api/v1/identity/registrations/{registrationId}                               | Get the caller-bound registration state                                               |
| [**getIdentitySession**](IdentityApi.md#getidentitysession)                                   | **GET** /api/v1/identity/session                                                      | Get the current customer identity session projection                                  |
| [**getWorkspaceLayoutPreferences**](IdentityApi.md#getworkspacelayoutpreferences)             | **GET** /api/v1/identity/settings/workspace-layout                                    | Get account-wide customer engagement workspace layout                                 |
| [**listCustomerLoginMethods**](IdentityApi.md#listcustomerloginmethods)                       | **GET** /api/v1/identity/login-methods                                                | List minimised login-method summaries for the authenticated customer                  |
| [**listIdentityMemberships**](IdentityApi.md#listidentitymemberships)                         | **GET** /api/v1/identity/memberships                                                  | List current customer memberships visible to the validated actor                      |
| [**listIdentityProviders**](IdentityApi.md#listidentityproviders)                             | **GET** /api/v1/identity/providers                                                    | List customer authentication choices for this environment                             |
| [**replaceWorkspaceLayoutPreferences**](IdentityApi.md#replaceworkspacelayoutpreferences)     | **PUT** /api/v1/identity/settings/workspace-layout                                    | Replace account-wide customer engagement workspace layout                             |
| [**startAccountMobileVerification**](IdentityApi.md#startaccountmobileverification)           | **POST** /api/v1/identity/mobile-verifications                                        | Start or replay progressive mobile verification                                       |
| [**startIdentityAccountLink**](IdentityApi.md#startidentityaccountlinkoperation)              | **POST** /api/v1/identity/account-links                                               | Start or replay a WhatsApp-to-web account link                                        |
| [**startIdentityEmailVerification**](IdentityApi.md#startidentityemailverification)           | **POST** /api/v1/identity/registrations/{registrationId}/email-verifications          | Start or replay mandatory email verification                                          |
| [**startIdentityMobileVerification**](IdentityApi.md#startidentitymobileverification)         | **POST** /api/v1/identity/registrations/{registrationId}/mobile-verifications         | Start or replay required WhatsApp-number verification during registration             |
| [**startIdentityPhoneChange**](IdentityApi.md#startidentityphonechange)                       | **POST** /api/v1/identity/phone-changes                                               | Start customer-initiated destination-bound verification of a replacement number       |
| [**startIdentityRegistration**](IdentityApi.md#startidentityregistrationoperation)            | **POST** /api/v1/identity/registrations                                               | Start or replay a customer registration                                               |
| [**updateCustomerProfile**](IdentityApi.md#updatecustomerprofile)                             | **PUT** /api/v1/identity/profile                                                      | Update customer profile fields allowed within the portal                              |
| [**updateCustomerSettings**](IdentityApi.md#updatecustomersettings)                           | **PUT** /api/v1/identity/settings                                                     | Update customer portal settings                                                       |
| [**updateIdentityRegistrationProfile**](IdentityApi.md#updateidentityregistrationprofile)     | **PUT** /api/v1/identity/registrations/{registrationId}/profile                       | Set the minimum registration profile                                                  |
| [**validateIdentityMembershipSelection**](IdentityApi.md#validateidentitymembershipselection) | **POST** /api/v1/identity/membership-selections/validate                              | Validate one current membership for application-session selection                     |

## approveIdentityAccountLink

> IdentityAccountLink approveIdentityAccountLink(linkId, idempotencyKey)

Explicitly approve a WhatsApp-to-web account link

Returns an encrypted, expiring LINK instruction for the verified WhatsApp number. Only a fresh signed inbound message after this approval can complete the link. Completion rechecks the verified destination and current membership, records evidence, and grants no portal session, relationship, or transcript access.

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
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## cancelIdentityAccountLink

> IdentityAccountLink cancelIdentityAccountLink(linkId, idempotencyKey)

Cancel a pending WhatsApp account link

Requires the current owning account and fresh portal authentication. Records evidence and irrevocably cancels this pending challenge. Concurrent signed confirmation and cancellation serialize on the same row. This does not unlink a completed association or change relationship access.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { CancelIdentityAccountLinkRequest } from '';

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
  } satisfies CancelIdentityAccountLinkRequest;

  try {
    const data = await api.cancelIdentityAccountLink(body);
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
| **200**     | Pending challenge cancelled or identical cancellation replayed                                                                  | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## cancelIdentityPhoneChange

> IdentityPhoneChangeV1 cancelIdentityPhoneChange(challengeId, idempotencyKey)

Cancel an uncompleted phone change without changing the current number

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { CancelIdentityPhoneChangeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string
    challengeId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies CancelIdentityPhoneChangeRequest;

  try {
    const data = await api.cancelIdentityPhoneChange(body);
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
| **challengeId**    | `string` |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**IdentityPhoneChangeV1**](IdentityPhoneChangeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Challenge expired with constitutional cancellation evidence                                                                     | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## completeIdentityRegistration

> IdentityCompletion completeIdentityRegistration(registrationId, idempotencyKey)

Complete registration by minting or reusing one account

Requires confirmed email, the approved minimum profile, and verified WhatsApp number. Duplicate resolution is deterministic and proof-gated. ACCOUNT_CREATED and ACCOUNT_REUSED have the same customer-facing success treatment. No Employment Relationship is created.

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
    // string | A valid key is required to complete registration; omission produces an identity state conflict. (optional)
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

| Name               | Type     | Description                                                                                     | Notes                                |
| ------------------ | -------- | ----------------------------------------------------------------------------------------------- | ------------------------------------ |
| **registrationId** | `string` | Opaque registration identifier bound to the authenticated pre-account actor                     | [Defaults to `undefined`]            |
| **idempotencyKey** | `string` | A valid key is required to complete registration; omission produces an identity state conflict. | [Optional] [Defaults to `undefined`] |

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
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
| **200**     | Mobile proof accepted or replayed                                                                                               | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
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

Confirm required WhatsApp-number verification during registration

Confirms only the destination bound to this registration challenge. Five incorrect code submissions expire the challenge. Successful verification expires competing pending mobile challenges; registration proof cannot be consumed by account-level verification.

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
| **200**     | Mobile proof accepted or replayed                                                                                               | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## confirmIdentityPhoneChange

> IdentityPhoneChangeV1 confirmIdentityPhoneChange(idempotencyKey, confirmIdentityPhoneChangeRequestV1)

Confirm OTP and explicit consent; atomically replace the number and revoke old access

Revalidates current account, membership, registration source and challenge after constitutional evidence. Five failed codes expire the challenge. Old account links and participant WhatsApp channel bindings are revoked in one owning PostgreSQL transaction. Existing history stays with the account; no outbox work is retargeted and possibly submitted originals remain receipt-only. New signed LINK confirmation and explicit approval of each professional relationship remain required.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ConfirmIdentityPhoneChangeRequest } from '';

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
    // ConfirmIdentityPhoneChangeRequestV1
    confirmIdentityPhoneChangeRequestV1: ...,
  } satisfies ConfirmIdentityPhoneChangeRequest;

  try {
    const data = await api.confirmIdentityPhoneChange(body);
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
| **idempotencyKey**                      | `string`                                                                      | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **confirmIdentityPhoneChangeRequestV1** | [ConfirmIdentityPhoneChangeRequestV1](ConfirmIdentityPhoneChangeRequestV1.md) |                                                                                          |                           |

### Return type

[**IdentityPhoneChangeV1**](IdentityPhoneChangeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Change committed or original completed outcome recovered                                                                        | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **410**     | Verification or link challenge is no longer usable                                                                              | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## createIdentityProviderLink

> IdentityProviderLinkOperationV1 createIdentityProviderLink(idempotencyKey, identityProviderLinkRequestV1)

Start provider-neutral proof-of-control linking

Requires accepted recent step-up and starts one bounded lifecycle operation. Provider subjects, credentials, and tokens are never accepted from or returned to the browser.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { CreateIdentityProviderLinkRequest } from '';

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
    // IdentityProviderLinkRequestV1
    identityProviderLinkRequestV1: ...,
  } satisfies CreateIdentityProviderLinkRequest;

  try {
    const data = await api.createIdentityProviderLink(body);
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
| **idempotencyKey**                | `string`                                                          | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **identityProviderLinkRequestV1** | [IdentityProviderLinkRequestV1](IdentityProviderLinkRequestV1.md) |                                                                                          |                           |

### Return type

[**IdentityProviderLinkOperationV1**](IdentityProviderLinkOperationV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **202**     | Link proof operation started or replayed idempotently                       | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## createIdentitySessionRevocation

> IdentitySessionRevocationReceiptV1 createIdentitySessionRevocation(idempotencyKey, identitySessionRevocationRequestV1)

Record a provider-neutral application-session revocation intent

Records privacy-safe revocation evidence for one opaque session family or all application sessions. Business Platform never receives browser handles or token envelopes and does not manipulate Web cookies.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { CreateIdentitySessionRevocationRequest } from '';

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
    // IdentitySessionRevocationRequestV1
    identitySessionRevocationRequestV1: ...,
  } satisfies CreateIdentitySessionRevocationRequest;

  try {
    const data = await api.createIdentitySessionRevocation(body);
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
| **identitySessionRevocationRequestV1** | [IdentitySessionRevocationRequestV1](IdentitySessionRevocationRequestV1.md) |                                                                                          |                           |

### Return type

[**IdentitySessionRevocationReceiptV1**](IdentitySessionRevocationReceiptV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **202**     | Revocation intent was already recorded or is now durably recorded           | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Identity action is not available to the authenticated actor                 | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## deleteIdentityProviderLink

> IdentityProviderLinkOperationV1 deleteIdentityProviderLink(linkId, idempotencyKey)

Unlink one provider-neutral authentication method

Requires current proof, recent step-up, and proof that another usable authentication method remains. Retired opaque link references are never reassigned.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { DeleteIdentityProviderLinkRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // string
    linkId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
  } satisfies DeleteIdentityProviderLinkRequest;

  try {
    const data = await api.deleteIdentityProviderLink(body);
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
| **linkId**         | `string` |                                                                                          | [Defaults to `undefined`] |
| **idempotencyKey** | `string` | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |

### Return type

[**IdentityProviderLinkOperationV1**](IdentityProviderLinkOperationV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **202**     | Unlink operation started or replayed idempotently                                                                               | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getCustomerProfile

> CustomerProfileV1 getCustomerProfile()

Get the current customer profile projection for the portal

Returns the current identity-owned customer and organization profile projection. Tenant and role are derived only from the authenticated session. No provider subject, token, or private identity topology is exposed.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { GetCustomerProfileRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.getCustomerProfile();
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

[**CustomerProfileV1**](CustomerProfileV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **200**     | Current customer profile projection                                         | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getCustomerSettings

> CustomerSettingsV1 getCustomerSettings()

Get customer portal settings

Returns locale, theme, timestamp visibility, and channel preferences that are safe to project through Business Platform. Sensitive security operations remain separate step-up governed actions.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { GetCustomerSettingsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.getCustomerSettings();
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

[**CustomerSettingsV1**](CustomerSettingsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **200**     | Current customer settings                                                   | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

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
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getIdentityPhoneChange

> IdentityPhoneChangeV1 getIdentityPhoneChange()

Recover the current owner\&#39;s latest phone-change state without resending

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { GetIdentityPhoneChangeRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.getIdentityPhoneChange();
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

[**IdentityPhoneChangeV1**](IdentityPhoneChangeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | Current owning account request state                                                                                            | -                |
| **204**     | No phone-change request exists for this owner                                                                                   | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

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

| Status code | Description                                                                                                  | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------ | ---------------- |
| **200**     | Current privacy-safe customer session projection                                                             | -                |
| **401**     | Identity session is missing, invalid, or expired                                                             | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                  | -                |
| **409**     | The authenticated broker identity has no active customer account; registration requires explicit user intent | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                        | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getWorkspaceLayoutPreferences

> WorkspaceLayoutPreferencesV1 getWorkspaceLayoutPreferences()

Get account-wide customer engagement workspace layout

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { GetWorkspaceLayoutPreferencesRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.getWorkspaceLayoutPreferences();
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

[**WorkspaceLayoutPreferencesV1**](WorkspaceLayoutPreferencesV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                           | Response headers |
| ----------- | ----------------------------------------------------- | ---------------- |
| **200**     | Current presentation-only workspace layout            | -                |
| **401**     | Identity session is missing, invalid, or expired      | -                |
| **404**     | Resource not found (or not accessible to this tenant) | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listCustomerLoginMethods

> CustomerLoginMethodCollectionV1 listCustomerLoginMethods()

List minimised login-method summaries for the authenticated customer

Returns provider aliases, usability state, and masked identifiers only. Business Platform never exposes provider subjects, tokens, or another account\&#39;s existence.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { ListCustomerLoginMethodsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  try {
    const data = await api.listCustomerLoginMethods();
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

[**CustomerLoginMethodCollectionV1**](CustomerLoginMethodCollectionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **200**     | Customer login methods                                                      | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listIdentityMemberships

> IdentityMembershipCollectionV1 listIdentityMemberships(limit)

List current customer memberships visible to the validated actor

Resolves the exact validated issuer and subject against durable current membership. Returned membership and tenant references are opaque; token tenant and role claims are never used as authority. The response is bounded and contains no provider identity data.

### Example

```ts
import { Configuration, IdentityApi } from "";
import type { ListIdentityMembershipsRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new IdentityApi(config);

  const body = {
    // number (optional)
    limit: 56,
  } satisfies ListIdentityMembershipsRequest;

  try {
    const data = await api.listIdentityMemberships(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name      | Type     | Description | Notes                          |
| --------- | -------- | ----------- | ------------------------------ |
| **limit** | `number` |             | [Optional] [Defaults to `100`] |

### Return type

[**IdentityMembershipCollectionV1**](IdentityMembershipCollectionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                           | Response headers        |
| ----------- | --------------------------------------------------------------------- | ----------------------- |
| **200**     | Current provider-neutral membership projection                        | \* Cache-Control - <br> |
| **401**     | Identity session is missing, invalid, or expired                      | -                       |
| **403**     | Identity action is not available to the authenticated actor           | -                       |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved | -                       |

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

## replaceWorkspaceLayoutPreferences

> WorkspaceLayoutPreferencesV1 replaceWorkspaceLayoutPreferences(idempotencyKey, replaceWorkspaceLayoutPreferencesRequestV1)

Replace account-wide customer engagement workspace layout

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ReplaceWorkspaceLayoutPreferencesRequest } from '';

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
    // ReplaceWorkspaceLayoutPreferencesRequestV1
    replaceWorkspaceLayoutPreferencesRequestV1: ...,
  } satisfies ReplaceWorkspaceLayoutPreferencesRequest;

  try {
    const data = await api.replaceWorkspaceLayoutPreferences(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                           | Type                                                                                        | Description                                                                              | Notes                     |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **idempotencyKey**                             | `string`                                                                                    | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **replaceWorkspaceLayoutPreferencesRequestV1** | [ReplaceWorkspaceLayoutPreferencesRequestV1](ReplaceWorkspaceLayoutPreferencesRequestV1.md) |                                                                                          |                           |

### Return type

[**WorkspaceLayoutPreferencesV1**](WorkspaceLayoutPreferencesV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **200**     | Layout replaced or replayed without changing business authority             | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                |

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                 | Response headers      |
| ----------- | --------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                       | -                     |
| **202**     | Challenge accepted or replayed without identity-existence disclosure        | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                     |
| **401**     | Identity session is missing, invalid, or expired                            | -                     |
| **403**     | Identity action is not available to the authenticated actor                 | -                     |
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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
| **201**     | Link challenge started                                                                                                          | -                     |
| **200**     | Prior identical link outcome replayed                                                                                           | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
| **202**     | Challenge accepted or replayed without identity-existence disclosure                                                            | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityMobileVerification

> IdentityVerificationChallenge startIdentityMobileVerification(registrationId, idempotencyKey, startMobileVerificationRequest)

Start or replay required WhatsApp-number verification during registration

Sends a purpose-bound code only after the registrant explicitly requests it. Delivery requires the approved WhatsApp authentication-template path. Returns no account-existence information. New requests enforce the challenge\&#39;s one-minute resend boundary; same-key replay does not send another code.

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **415**     | Request content type is not supported                                                                                           | -                     |
| **202**     | Challenge accepted or replayed without identity-existence disclosure                                                            | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence                                                         | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## startIdentityPhoneChange

> IdentityPhoneChangeV1 startIdentityPhoneChange(idempotencyKey, startIdentityPhoneChangeRequestV1)

Start customer-initiated destination-bound verification of a replacement number

Requires current OWNER membership and nonfuture portal authentication no older than five minutes. OTP proves new number control, not account ownership or recovery. Dispatch uses the existing activation-gated authentication template and shared budget. Unknown delivery is never resent implicitly. Numbers held by another account require separate governed recovery.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { StartIdentityPhoneChangeRequest } from '';

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
    // StartIdentityPhoneChangeRequestV1
    startIdentityPhoneChangeRequestV1: ...,
  } satisfies StartIdentityPhoneChangeRequest;

  try {
    const data = await api.startIdentityPhoneChange(body);
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
| **idempotencyKey**                    | `string`                                                                  | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **startIdentityPhoneChangeRequestV1** | [StartIdentityPhoneChangeRequestV1](StartIdentityPhoneChangeRequestV1.md) |                                                                                          |                           |

### Return type

[**IdentityPhoneChangeV1**](IdentityPhoneChangeV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **200**     | Verification submitted or identical submitted challenge recovered                                                               | -                     |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                     |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                     |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run                                                     | -                     |
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
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                     |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                     |
| **415**     | Request content type is not supported                                       | -                     |
| **429**     | Identity operation is rate limited without disclosing account existence     | \* Retry-After - <br> |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                     |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateCustomerProfile

> CustomerProfileV1 updateCustomerProfile(idempotencyKey, updateCustomerProfileRequestV1)

Update customer profile fields allowed within the portal

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { UpdateCustomerProfileRequest } from '';

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
    // UpdateCustomerProfileRequestV1
    updateCustomerProfileRequestV1: ...,
  } satisfies UpdateCustomerProfileRequest;

  try {
    const data = await api.updateCustomerProfile(body);
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
| **updateCustomerProfileRequestV1** | [UpdateCustomerProfileRequestV1](UpdateCustomerProfileRequestV1.md) |                                                                                          |                           |

### Return type

[**CustomerProfileV1**](CustomerProfileV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **415**     | Request content type is not supported                                       | -                |
| **200**     | Profile updated or replayed                                                 | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateCustomerSettings

> CustomerSettingsV1 updateCustomerSettings(idempotencyKey, updateCustomerSettingsRequestV1)

Update customer portal settings

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { UpdateCustomerSettingsRequest } from '';

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
    // UpdateCustomerSettingsRequestV1
    updateCustomerSettingsRequestV1: ...,
  } satisfies UpdateCustomerSettingsRequest;

  try {
    const data = await api.updateCustomerSettings(body);
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
| **updateCustomerSettingsRequestV1** | [UpdateCustomerSettingsRequestV1](UpdateCustomerSettingsRequestV1.md) |                                                                                          |                           |

### Return type

[**CustomerSettingsV1**](CustomerSettingsV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                 | Response headers |
| ----------- | --------------------------------------------------------------------------- | ---------------- |
| **415**     | Request content type is not supported                                       | -                |
| **200**     | Settings updated or replayed                                                | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed | -                |
| **401**     | Identity session is missing, invalid, or expired                            | -                |
| **403**     | Fresh or stronger Keycloak assurance is required before the command can run | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path  | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved       | -                |

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
- **Accept**: `application/problem+json`, `application/json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **415**     | Request content type is not supported                                                                                           | -                |
| **200**     | Registration profile accepted or replayed                                                                                       | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **422**     | Mandatory identity verification or minimum profile completion remains outstanding                                               | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## validateIdentityMembershipSelection

> IdentityMembershipSelectionV1 validateIdentityMembershipSelection(idempotencyKey, identityMembershipSelectionRequestV1)

Validate one current membership for application-session selection

Revalidates one opaque membership reference for the exact validated actor without mutating membership, tenant, role, or business authority.

### Example

```ts
import {
  Configuration,
  IdentityApi,
} from '';
import type { ValidateIdentityMembershipSelectionRequest } from '';

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
    // IdentityMembershipSelectionRequestV1
    identityMembershipSelectionRequestV1: ...,
  } satisfies ValidateIdentityMembershipSelectionRequest;

  try {
    const data = await api.validateIdentityMembershipSelection(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                     | Type                                                                            | Description                                                                              | Notes                     |
| ---------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| **idempotencyKey**                       | `string`                                                                        | Same key and canonical request hash replay the prior outcome; divergent reuse conflicts. | [Defaults to `undefined`] |
| **identityMembershipSelectionRequestV1** | [IdentityMembershipSelectionRequestV1](IdentityMembershipSelectionRequestV1.md) |                                                                                          |                           |

### Return type

[**IdentityMembershipSelectionV1**](IdentityMembershipSelectionV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                                                                                                                     | Response headers |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **200**     | The membership is currently eligible for selection                                                                              | -                |
| **400**     | Identity request is malformed or unsupported; no submitted secret is echoed                                                     | -                |
| **401**     | Identity session is missing, invalid, or expired                                                                                | -                |
| **403**     | Identity action is not available to the authenticated actor                                                                     | -                |
| **404**     | Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure | -                |
| **409**     | Idempotency conflict or duplicate resolution requires a safe recovery path                                                      | -                |
| **503**     | Identity dependency is unavailable and the outcome remains unresolved                                                           | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
