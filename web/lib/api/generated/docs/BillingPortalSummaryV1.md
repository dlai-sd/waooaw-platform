# BillingPortalSummaryV1

## Properties

| Name                    | Type                                                                        |
| ----------------------- | --------------------------------------------------------------------------- |
| `schemaVersion`         | [CustomerPortalSchemaVersion](CustomerPortalSchemaVersion.md)               |
| `producedAt`            | Date                                                                        |
| `currencyState`         | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md) |
| `paymentState`          | string                                                                      |
| `billingPreference`     | string                                                                      |
| `allowanceSummary`      | [Array&lt;BillingAllowanceSummaryV1&gt;](BillingAllowanceSummaryV1.md)      |
| `forecastRange`         | string                                                                      |
| `assumptions`           | Array&lt;string&gt;                                                         |
| `commercialConsequence` | string                                                                      |
| `invoiceSummary`        | [Array&lt;GstInvoiceSummary&gt;](GstInvoiceSummary.md)                      |

## Example

```typescript
import type { BillingPortalSummaryV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  producedAt: null,
  currencyState: null,
  paymentState: null,
  billingPreference: null,
  allowanceSummary: null,
  forecastRange: null,
  assumptions: null,
  commercialConsequence: null,
  invoiceSummary: null,
} satisfies BillingPortalSummaryV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BillingPortalSummaryV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
