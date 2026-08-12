# RelationshipHostedOnboardingOrder

## Properties

| Name             | Type    |
| ---------------- | ------- |
| `orderId`        | string  |
| `amountInrPaise` | number  |
| `currency`       | string  |
| `isBypass`       | boolean |
| `checkoutMode`   | string  |

## Example

```typescript
import type { RelationshipHostedOnboardingOrder } from "";

// TODO: Update the object below with actual values
const example = {
  orderId: null,
  amountInrPaise: null,
  currency: null,
  isBypass: null,
  checkoutMode: null,
} satisfies RelationshipHostedOnboardingOrder;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipHostedOnboardingOrder;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
