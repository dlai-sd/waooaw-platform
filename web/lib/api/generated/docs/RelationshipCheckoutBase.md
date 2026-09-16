# RelationshipCheckoutBase

## Properties

| Name               | Type   |
| ------------------ | ------ |
| `outcomeKind`      | string |
| `checkoutIntentId` | string |
| `relationshipId`   | string |
| `contractVersion`  | number |
| `producedAt`       | Date   |

## Example

```typescript
import type { RelationshipCheckoutBase } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeKind: null,
  checkoutIntentId: null,
  relationshipId: null,
  contractVersion: null,
  producedAt: null,
} satisfies RelationshipCheckoutBase;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipCheckoutBase;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
