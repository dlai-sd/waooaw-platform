# HireQuote

The one customer price of a Hire, resolved by the Business Platform from the billing owner\'s for-sale monthly package. GST inclusive.

## Properties

| Name                  | Type   |
| --------------------- | ------ |
| `packageCode`         | string |
| `currency`            | string |
| `grossAmountInrPaise` | number |
| `gstAmountInrPaise`   | number |
| `basePriceInrPaise`   | number |
| `cadence`             | string |
| `billingPeriodDays`   | number |
| `quoteVersion`        | string |

## Example

```typescript
import type { HireQuote } from "";

// TODO: Update the object below with actual values
const example = {
  packageCode: null,
  currency: null,
  grossAmountInrPaise: null,
  gstAmountInrPaise: null,
  basePriceInrPaise: null,
  cadence: null,
  billingPeriodDays: null,
  quoteVersion: null,
} satisfies HireQuote;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HireQuote;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
