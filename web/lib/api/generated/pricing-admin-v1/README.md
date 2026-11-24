# @waooaw/pricing-admin-client@1.0.0

A TypeScript SDK client for the api.waooaw.com API.

## Usage

First, install the SDK from npm.

```bash
npm install @waooaw/pricing-admin-client --save
```

Next, try it out.


```ts
import {
  Configuration,
  PricingDraftsApi,
} from '@waooaw/pricing-admin-client';
import type { AuthorizePricingDraftRequest } from '@waooaw/pricing-admin-client';

async function example() {
  console.log("🚀 Testing @waooaw/pricing-admin-client SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new PricingDraftsApi(config);

  const body = {
    // string
    draftId: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string | Same key and canonical request replay the stored outcome; divergent reuse conflicts with `PRICING_IDEMPOTENCY_CONFLICT`.
    idempotencyKey: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // string
    xCorrelationID: 38400000-8cf0-11bd-b23e-10b96e4ef00d,
    // AuthorizePricingDraftRequestV1
    authorizePricingDraftRequestV1: ...,
  } satisfies AuthorizePricingDraftRequest;

  try {
    const data = await api.authorizePricingDraft(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```


## Documentation

### API Endpoints

All URIs are relative to *https://api.waooaw.com*

| Class | Method | HTTP request | Description
| ----- | ------ | ------------ | -------------
*PricingDraftsApi* | [**authorizePricingDraft**](docs/PricingDraftsApi.md#authorizepricingdraft) | **POST** /api/v1/admin/pricing/drafts/{draftId}/authorize | Authorize a submitted version
*PricingDraftsApi* | [**createPricingDraft**](docs/PricingDraftsApi.md#createpricingdraft) | **POST** /api/v1/admin/pricing/drafts | Create a draft
*PricingDraftsApi* | [**discardPricingDraft**](docs/PricingDraftsApi.md#discardpricingdraft) | **POST** /api/v1/admin/pricing/drafts/{draftId}/discard | Discard a version that is not effective
*PricingDraftsApi* | [**getPricingDraft**](docs/PricingDraftsApi.md#getpricingdraft) | **GET** /api/v1/admin/pricing/drafts/{draftId} | Read a draft
*PricingDraftsApi* | [**listPricingDrafts**](docs/PricingDraftsApi.md#listpricingdrafts) | **GET** /api/v1/admin/pricing/drafts | List pricing drafts
*PricingDraftsApi* | [**simulatePricingDraft**](docs/PricingDraftsApi.md#simulatepricingdraft) | **POST** /api/v1/admin/pricing/drafts/{draftId}/simulate | Simulate a draft
*PricingDraftsApi* | [**submitPricingDraft**](docs/PricingDraftsApi.md#submitpricingdraft) | **POST** /api/v1/admin/pricing/drafts/{draftId}/submit | Submit a simulated draft for authorization
*PricingDraftsApi* | [**updatePricingDraft**](docs/PricingDraftsApi.md#updatepricingdraft) | **PUT** /api/v1/admin/pricing/drafts/{draftId} | Replace the body of a draft
*PricingReportsApi* | [**getPricingFundingDashboard**](docs/PricingReportsApi.md#getpricingfundingdashboard) | **GET** /api/v1/admin/pricing/dashboard/funding | Read the funding dashboard
*PricingReportsApi* | [**getPricingLiveMargin**](docs/PricingReportsApi.md#getpricinglivemargin) | **GET** /api/v1/admin/pricing/live-margin | Read the live margin watch
*PricingReportsApi* | [**getPricingMarginDashboard**](docs/PricingReportsApi.md#getpricingmargindashboard) | **GET** /api/v1/admin/pricing/dashboard/margin | Read the margin dashboard
*PricingSafetyApi* | [**closePackageToNewCustomers**](docs/PricingSafetyApi.md#closepackagetonewcustomers) | **POST** /api/v1/admin/pricing/safety/close-package | Close a package to new customers immediately
*PricingSafetyApi* | [**disablePricingGrant**](docs/PricingSafetyApi.md#disablepricinggrant) | **POST** /api/v1/admin/pricing/safety/disable-grant | Disable a trial or setup grant immediately
*PricingSafetyApi* | [**lowerPricingCeiling**](docs/PricingSafetyApi.md#lowerpricingceiling) | **POST** /api/v1/admin/pricing/safety/lower-ceiling | Lower a budget ceiling immediately
*PricingVersionsApi* | [**activatePackageForSale**](docs/PricingVersionsApi.md#activatepackageforsale) | **POST** /api/v1/admin/pricing/packages/{packageId}/activate-for-sale | Activate an authorized package for sale
*PricingVersionsApi* | [**exportPricingVersions**](docs/PricingVersionsApi.md#exportpricingversions) | **GET** /api/v1/admin/pricing/versions/export | Export the effective and authorized versions
*PricingVersionsApi* | [**importPricingVersions**](docs/PricingVersionsApi.md#importpricingversions) | **POST** /api/v1/admin/pricing/versions/import | Import a signed bundle as drafts
*PricingVersionsApi* | [**listPricingVersions**](docs/PricingVersionsApi.md#listpricingversions) | **GET** /api/v1/admin/pricing/versions | List the versions of a subject


### Models

- [ActivatePackageForSaleRequestV1](docs/ActivatePackageForSaleRequestV1.md)
- [AuthorizePricingDraftRequestV1](docs/AuthorizePricingDraftRequestV1.md)
- [ClosePackageRequestV1](docs/ClosePackageRequestV1.md)
- [CreatePricingDraftRequestV1](docs/CreatePricingDraftRequestV1.md)
- [DisableGrantRequestV1](docs/DisableGrantRequestV1.md)
- [DiscardPricingDraftRequestV1](docs/DiscardPricingDraftRequestV1.md)
- [ImportPricingBundleRequestV1](docs/ImportPricingBundleRequestV1.md)
- [LowerCeilingRequestV1](docs/LowerCeilingRequestV1.md)
- [PricingAffectedPackageV1](docs/PricingAffectedPackageV1.md)
- [PricingBreakerStateV1](docs/PricingBreakerStateV1.md)
- [PricingBudgetBodyV1](docs/PricingBudgetBodyV1.md)
- [PricingBudgetScopeV1](docs/PricingBudgetScopeV1.md)
- [PricingBuildUpV1](docs/PricingBuildUpV1.md)
- [PricingBundleSignatureV1](docs/PricingBundleSignatureV1.md)
- [PricingComponentCadenceV1](docs/PricingComponentCadenceV1.md)
- [PricingComponentCostV1](docs/PricingComponentCostV1.md)
- [PricingComponentKindV1](docs/PricingComponentKindV1.md)
- [PricingCostLineV1](docs/PricingCostLineV1.md)
- [PricingCouponBodyV1](docs/PricingCouponBodyV1.md)
- [PricingEventCountV1](docs/PricingEventCountV1.md)
- [PricingExportBundleV1](docs/PricingExportBundleV1.md)
- [PricingExportEntryV1](docs/PricingExportEntryV1.md)
- [PricingFundingDashboardV1](docs/PricingFundingDashboardV1.md)
- [PricingFundingDashboardV1TrialToHire](docs/PricingFundingDashboardV1TrialToHire.md)
- [PricingGrantBodyV1](docs/PricingGrantBodyV1.md)
- [PricingGrantConsumptionV1](docs/PricingGrantConsumptionV1.md)
- [PricingImportCreatedV1](docs/PricingImportCreatedV1.md)
- [PricingImportRejectedV1](docs/PricingImportRejectedV1.md)
- [PricingImportResultV1](docs/PricingImportResultV1.md)
- [PricingLeadSpendV1](docs/PricingLeadSpendV1.md)
- [PricingLiveMarginBreachV1](docs/PricingLiveMarginBreachV1.md)
- [PricingLiveMarginV1](docs/PricingLiveMarginV1.md)
- [PricingMarginDashboardV1](docs/PricingMarginDashboardV1.md)
- [PricingMarginPackageV1](docs/PricingMarginPackageV1.md)
- [PricingPackageBodyV1](docs/PricingPackageBodyV1.md)
- [PricingPackageComponentBodyV1](docs/PricingPackageComponentBodyV1.md)
- [PricingPackageSaleV1](docs/PricingPackageSaleV1.md)
- [PricingPolicyBodyV1](docs/PricingPolicyBodyV1.md)
- [PricingPolicyTimingV1](docs/PricingPolicyTimingV1.md)
- [PricingProblemCodeV1](docs/PricingProblemCodeV1.md)
- [PricingProblemDetailV1](docs/PricingProblemDetailV1.md)
- [PricingProfileCostV1](docs/PricingProfileCostV1.md)
- [PricingRateBodyV1](docs/PricingRateBodyV1.md)
- [PricingRecipeEntryV1](docs/PricingRecipeEntryV1.md)
- [PricingSafetyResultV1](docs/PricingSafetyResultV1.md)
- [PricingSimulationResultV1](docs/PricingSimulationResultV1.md)
- [PricingSpendByAccountClassV1](docs/PricingSpendByAccountClassV1.md)
- [PricingSpendByCampaignV1](docs/PricingSpendByCampaignV1.md)
- [PricingSpendByTenantV1](docs/PricingSpendByTenantV1.md)
- [PricingUsageProfileV1](docs/PricingUsageProfileV1.md)
- [PricingVersionDiffEntryV1](docs/PricingVersionDiffEntryV1.md)
- [PricingVersionDiffV1](docs/PricingVersionDiffV1.md)
- [PricingVersionKindV1](docs/PricingVersionKindV1.md)
- [PricingVersionListV1](docs/PricingVersionListV1.md)
- [PricingVersionStateV1](docs/PricingVersionStateV1.md)
- [PricingVersionV1](docs/PricingVersionV1.md)
- [PricingViolationV1](docs/PricingViolationV1.md)
- [PricingWarningV1](docs/PricingWarningV1.md)
- [SimulatePricingDraftRequestV1](docs/SimulatePricingDraftRequestV1.md)
- [SubmitPricingDraftRequestV1](docs/SubmitPricingDraftRequestV1.md)
- [UpdatePricingDraftRequestV1](docs/UpdatePricingDraftRequestV1.md)

### Authorization


Authentication schemes defined for the API:
<a id="bearerAuth"></a>
#### bearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)

## About

This TypeScript SDK client supports the [Fetch API](https://fetch.spec.whatwg.org/)
and is automatically generated by the
[OpenAPI Generator](https://openapi-generator.tech) project:

- API version: `1.0.0`
- Package version: `1.0.0`
- Generator version: `7.17.0`
- Build package: `org.openapitools.codegen.languages.TypeScriptFetchClientCodegen`

The generated npm module supports the following:

- Environments
  * Node.js
  * Webpack
  * Browserify
- Language levels
  * ES5 - you must have a Promises/A+ library installed
  * ES6
- Module systems
  * CommonJS
  * ES6 module system


## Development

### Building

To build the TypeScript source code, you need to have Node.js and npm installed.
After cloning the repository, navigate to the project directory and run:

```bash
npm install
npm run build
```

### Publishing

Once you've built the package, you can publish it to npm:

```bash
npm publish
```

## License

[]()
