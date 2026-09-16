# RelationshipProviderConfigurationPending

## Properties

| Name                     | Type    |
| ------------------------ | ------- |
| `outcomeKind`            | string  |
| `checkoutIntentId`       | string  |
| `relationshipId`         | string  |
| `contractVersion`        | number  |
| `producedAt`             | Date    |
| `reasonCode`             | string  |
| `accountableOwner`       | string  |
| `retryable`              | boolean |
| `customerSafeNextAction` | string  |

## Example

```typescript
import type { RelationshipProviderConfigurationPending } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeKind: null,
  checkoutIntentId: null,
  relationshipId: null,
  contractVersion: null,
  producedAt: null,
  reasonCode: null,
  accountableOwner: null,
  retryable: null,
  customerSafeNextAction: null,
} satisfies RelationshipProviderConfigurationPending;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipProviderConfigurationPending;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
