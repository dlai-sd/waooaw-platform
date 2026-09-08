# BillingApi

All URIs are relative to _http://localhost:5001_

| Method                                                                                      | HTTP request                                | Description                                                       |
| ------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------- |
| [**createSubscription**](BillingApi.md#createsubscriptionoperation)                         | **POST** /api/v1/payments/subscriptions     | Create a Razorpay subscription for a contract                     |
| [**generateWhatsappUpiAutopayLink**](BillingApi.md#generatewhatsappupiautopaylinkoperation) | **POST** /api/v1/billing/whatsapp-upi-link  | Generate WhatsApp UPI AutoPay mandate link (Agricultural Advisor) |
| [**getBillingPortalSummary**](BillingApi.md#getbillingportalsummary)                        | **GET** /api/v1/billing/summary             | Get the customer portal billing summary                           |
| [**getBillingPreference**](BillingApi.md#getbillingpreference)                              | **GET** /api/v1/billing/preference          | Get billing preference (SEPARATE or COMBINED)                     |
| [**getBillingStatement**](BillingApi.md#getbillingstatement)                                | **GET** /api/v1/billing                     | Get itemised billing statement (C-038, AD-014)                    |
| [**getSubscriptionTiers**](BillingApi.md#getsubscriptiontiers)                              | **GET** /api/v1/billing/subscription-tiers  | List available subscription tiers for an agent type               |
| [**listInvoices**](BillingApi.md#listinvoices)                                              | **GET** /api/v1/billing/invoices            | List all GST invoices                                             |
| [**razorpayWebhook**](BillingApi.md#razorpaywebhook)                                        | **POST** /api/v1/payments/webhooks/razorpay | Razorpay webhook receiver                                         |
| [**updateBillingPreference**](BillingApi.md#updatebillingpreferenceoperation)               | **PUT** /api/v1/billing/preference          | Update billing preference                                         |

## createSubscription

> SubscriptionCreated createSubscription(createSubscriptionRequest)

Create a Razorpay subscription for a contract

Creates a recurring subscription in Razorpay for the given employment contract. Called when trial converts to paid hire. Razorpay subscription_id is stored in subscription_billing_events.payment_processor_reference. ADR-022 (Razorpay India).

### Example

```ts
import {
  Configuration,
  BillingApi,
} from '';
import type { CreateSubscriptionOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // CreateSubscriptionRequest
    createSubscriptionRequest: ...,
  } satisfies CreateSubscriptionOperationRequest;

  try {
    const data = await api.createSubscription(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                          | Type                                                      | Description | Notes |
| ----------------------------- | --------------------------------------------------------- | ----------- | ----- |
| **createSubscriptionRequest** | [CreateSubscriptionRequest](CreateSubscriptionRequest.md) |             |       |

### Return type

[**SubscriptionCreated**](SubscriptionCreated.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                                              | Response headers |
| ----------- | -------------------------------------------------------- | ---------------- |
| **201**     | Subscription created. Razorpay payment link returned.    | -                |
| **402**     | Payment required — Razorpay subscription creation failed | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## generateWhatsappUpiAutopayLink

> GenerateWhatsappUpiAutopayLink200Response generateWhatsappUpiAutopayLink(generateWhatsappUpiAutopayLinkRequest)

Generate WhatsApp UPI AutoPay mandate link (Agricultural Advisor)

Generates a Razorpay UPI AutoPay (Standing Instruction) mandate link for WhatsApp delivery. This is a ONE-TIME SETUP — the farmer taps the link, approves a ₹200/month standing instruction in their UPI app (GPay/PhonePe/Paytm), and Razorpay auto-collects every month. NOT a one-time payment link — this creates a recurring mandate. Only applicable for AGRICULTURAL_ADVISOR_INDIA professional type. WhatsApp message template (HSM required — pre-approved): \&quot;नमस्कार {{farmer_name}}! शेतकरी मित्र सेवा ₹200/महिना. एकदाच approve करा — दर महिना आपोआप होईल: {{mandate_link}}\&quot; R016-01 fix: Changed from one-time UPI link to UPI AutoPay mandate (ADR-022).

### Example

```ts
import {
  Configuration,
  BillingApi,
} from '';
import type { GenerateWhatsappUpiAutopayLinkOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // GenerateWhatsappUpiAutopayLinkRequest
    generateWhatsappUpiAutopayLinkRequest: ...,
  } satisfies GenerateWhatsappUpiAutopayLinkOperationRequest;

  try {
    const data = await api.generateWhatsappUpiAutopayLink(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                                      | Type                                                                              | Description | Notes |
| ----------------------------------------- | --------------------------------------------------------------------------------- | ----------- | ----- |
| **generateWhatsappUpiAutopayLinkRequest** | [GenerateWhatsappUpiAutopayLinkRequest](GenerateWhatsappUpiAutopayLinkRequest.md) |             |       |

### Return type

[**GenerateWhatsappUpiAutopayLink200Response**](GenerateWhatsappUpiAutopayLink200Response.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                                                              | Response headers |
| ----------- | ------------------------------------------------------------------------ | ---------------- |
| **200**     | UPI AutoPay mandate link ready for WhatsApp delivery                     | -                |
| **422**     | Agent type not eligible for UPI AutoPay or farmer language not available | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getBillingPortalSummary

> BillingPortalSummaryV1 getBillingPortalSummary()

Get the customer portal billing summary

Returns BP-mediated WBE billing truth for the authenticated customer portal, including allowance, forecast, assumptions, payment state, invoices, and typed commercial consequence. The browser performs no monetary calculation.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { GetBillingPortalSummaryRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  try {
    const data = await api.getBillingPortalSummary();
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

[**BillingPortalSummaryV1**](BillingPortalSummaryV1.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                      | Response headers |
| ----------- | -------------------------------- | ---------------- |
| **200**     | Portal billing summary           | -                |
| **401**     | JWT missing, expired, or invalid | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getBillingPreference

> GetBillingPreference200Response getBillingPreference()

Get billing preference (SEPARATE or COMBINED)

Returns the customer\&#39;s current multi-agent billing preference.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { GetBillingPreferenceRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  try {
    const data = await api.getBillingPreference();
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

[**GetBillingPreference200Response**](GetBillingPreference200Response.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                | Response headers |
| ----------- | -------------------------- | ---------------- |
| **200**     | Current billing preference | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getBillingStatement

> BillingStatement getBillingStatement(month)

Get itemised billing statement (C-038, AD-014)

Pro-rata billing calculated from event ledger. Itemised per skill. For COMBINED billing preference, returns the consolidated invoice; for SEPARATE, returns per-agent invoices.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { GetBillingStatementRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // Date | Billing period (YYYY-MM). Defaults to current month. (optional)
    month: 2013 - 10 - 20,
  } satisfies GetBillingStatementRequest;

  try {
    const data = await api.getBillingStatement(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name      | Type   | Description                                          | Notes                                |
| --------- | ------ | ---------------------------------------------------- | ------------------------------------ |
| **month** | `Date` | Billing period (YYYY-MM). Defaults to current month. | [Optional] [Defaults to `undefined`] |

### Return type

[**BillingStatement**](BillingStatement.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`, `application/problem+json`

### HTTP response details

| Status code | Description                      | Response headers |
| ----------- | -------------------------------- | ---------------- |
| **200**     | Itemised billing statement       | -                |
| **401**     | JWT missing, expired, or invalid | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## getSubscriptionTiers

> Array&lt;SubscriptionTier&gt; getSubscriptionTiers(professionalType)

List available subscription tiers for an agent type

Returns available tiers and pricing for a given professional_type.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { GetSubscriptionTiersRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // string | e.g. DIGITAL_MARKETING_HEALTHCARE, TRADING_FO_CRYPTO, AGRICULTURAL_ADVISOR_INDIA
    professionalType: professionalType_example,
  } satisfies GetSubscriptionTiersRequest;

  try {
    const data = await api.getSubscriptionTiers(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                 | Type     | Description                                                                      | Notes                     |
| -------------------- | -------- | -------------------------------------------------------------------------------- | ------------------------- |
| **professionalType** | `string` | e.g. DIGITAL_MARKETING_HEALTHCARE, TRADING_FO_CRYPTO, AGRICULTURAL_ADVISOR_INDIA | [Defaults to `undefined`] |

### Return type

[**Array&lt;SubscriptionTier&gt;**](SubscriptionTier.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description                  | Response headers |
| ----------- | ---------------------------- | ---------------- |
| **200**     | Available subscription tiers | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## listInvoices

> Array&lt;GstInvoiceSummary&gt; listInvoices(fromDate, toDate, agentType)

List all GST invoices

Returns all GST invoices for the customer. For COMBINED preference, includes consolidated parent invoices. Each invoice includes a signed PDF URL valid for 1 hour.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { ListInvoicesRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // Date (optional)
    fromDate: 2013 - 10 - 20,
    // Date (optional)
    toDate: 2013 - 10 - 20,
    // string | Filter by professional_type. Omit to get all agents. (optional)
    agentType: agentType_example,
  } satisfies ListInvoicesRequest;

  try {
    const data = await api.listInvoices(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name          | Type     | Description                                          | Notes                                |
| ------------- | -------- | ---------------------------------------------------- | ------------------------------------ |
| **fromDate**  | `Date`   |                                                      | [Optional] [Defaults to `undefined`] |
| **toDate**    | `Date`   |                                                      | [Optional] [Defaults to `undefined`] |
| **agentType** | `string` | Filter by professional_type. Omit to get all agents. | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;GstInvoiceSummary&gt;**](GstInvoiceSummary.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`

### HTTP response details

| Status code | Description          | Response headers |
| ----------- | -------------------- | ---------------- |
| **200**     | List of GST invoices | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## razorpayWebhook

> razorpayWebhook(body)

Razorpay webhook receiver

Receives Razorpay webhook events (payment.captured, subscription.charged, subscription.cancelled, payment.failed). Validates webhook signature using RAZORPAY_WEBHOOK_SECRET. Updates employment contract state and billing events. ADR-022. NOT authenticated via Keycloak — authenticated via Razorpay signature.

### Example

```ts
import { Configuration, BillingApi } from "";
import type { RazorpayWebhookRequest } from "";

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BillingApi();

  const body = {
    // object
    body: Object,
  } satisfies RazorpayWebhookRequest;

  try {
    const data = await api.razorpayWebhook(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name     | Type     | Description | Notes |
| -------- | -------- | ----------- | ----- |
| **body** | `object` |             |       |

### Return type

`void` (Empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: Not defined

### HTTP response details

| Status code | Description                                  | Response headers |
| ----------- | -------------------------------------------- | ---------------- |
| **200**     | Webhook processed                            | -                |
| **400**     | Invalid signature or unrecognised event type | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

## updateBillingPreference

> updateBillingPreference(updateBillingPreferenceRequest)

Update billing preference

Changes between SEPARATE and COMBINED billing. Effective from next billing period. Requires at least 2 active employment contracts for COMBINED to be meaningful.

### Example

```ts
import {
  Configuration,
  BillingApi,
} from '';
import type { UpdateBillingPreferenceOperationRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: BearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new BillingApi(config);

  const body = {
    // UpdateBillingPreferenceRequest
    updateBillingPreferenceRequest: ...,
  } satisfies UpdateBillingPreferenceOperationRequest;

  try {
    const data = await api.updateBillingPreference(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

| Name                               | Type                                                                | Description | Notes |
| ---------------------------------- | ------------------------------------------------------------------- | ----------- | ----- |
| **updateBillingPreferenceRequest** | [UpdateBillingPreferenceRequest](UpdateBillingPreferenceRequest.md) |             |       |

### Return type

`void` (Empty response body)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/problem+json`

### HTTP response details

| Status code | Description                                             | Response headers |
| ----------- | ------------------------------------------------------- | ---------------- |
| **200**     | Preference updated. Effective from next billing period. | -                |
| **422**     | Request body failed validation                          | -                |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
