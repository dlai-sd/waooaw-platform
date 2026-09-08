# BillingAllowanceSummaryV1

## Properties

| Name             | Type   |
| ---------------- | ------ |
| `label`          | string |
| `consumed`       | string |
| `remaining`      | string |
| `renewalMeaning` | string |

## Example

```typescript
import type { BillingAllowanceSummaryV1 } from "";

// TODO: Update the object below with actual values
const example = {
  label: null,
  consumed: null,
  remaining: null,
  renewalMeaning: null,
} satisfies BillingAllowanceSummaryV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BillingAllowanceSummaryV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
