# EmploymentContractCommercialTerms

## Properties

| Name                         | Type   |
| ---------------------------- | ------ |
| `currency`                   | string |
| `grossAmountInrPaise`        | number |
| `gstAmountInrPaise`          | number |
| `cadence`                    | string |
| `subscriptionTerms`          | string |
| `adSpendTreatment`           | string |
| `cancellationAndRefundTerms` | string |

## Example

```typescript
import type { EmploymentContractCommercialTerms } from "";

// TODO: Update the object below with actual values
const example = {
  currency: null,
  grossAmountInrPaise: null,
  gstAmountInrPaise: null,
  cadence: null,
  subscriptionTerms: null,
  adSpendTreatment: null,
  cancellationAndRefundTerms: null,
} satisfies EmploymentContractCommercialTerms;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as EmploymentContractCommercialTerms;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
