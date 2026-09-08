# SubscriptionCreated

## Properties

| Name                     | Type   |
| ------------------------ | ------ |
| `contractId`             | string |
| `tierId`                 | string |
| `razorpaySubscriptionId` | string |
| `paymentLink`            | string |
| `shortUrl`               | string |

## Example

```typescript
import type { SubscriptionCreated } from "";

// TODO: Update the object below with actual values
const example = {
  contractId: null,
  tierId: null,
  razorpaySubscriptionId: null,
  paymentLink: null,
  shortUrl: null,
} satisfies SubscriptionCreated;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SubscriptionCreated;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
