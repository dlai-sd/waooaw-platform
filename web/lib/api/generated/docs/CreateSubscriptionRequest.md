# CreateSubscriptionRequest

## Properties

| Name         | Type   |
| ------------ | ------ |
| `contractId` | string |
| `tierId`     | string |
| `totalCount` | number |

## Example

```typescript
import type { CreateSubscriptionRequest } from "";

// TODO: Update the object below with actual values
const example = {
  contractId: null,
  tierId: null,
  totalCount: null,
} satisfies CreateSubscriptionRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateSubscriptionRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
