# BillingLineItem

## Properties

| Name                    | Type   |
| ----------------------- | ------ |
| `skillId`               | string |
| `skillName`             | string |
| `activeDurationMinutes` | number |
| `pricePerMonth`         | number |
| `chargeAmount`          | number |

## Example

```typescript
import type { BillingLineItem } from "";

// TODO: Update the object below with actual values
const example = {
  skillId: null,
  skillName: null,
  activeDurationMinutes: null,
  pricePerMonth: null,
  chargeAmount: null,
} satisfies BillingLineItem;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BillingLineItem;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
