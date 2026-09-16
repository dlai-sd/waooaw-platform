# RelationshipActivationOutcome

## Properties

| Name                 | Type   |
| -------------------- | ------ |
| `activationIntentId` | string |
| `subscriptionId`     | string |
| `evidenceId`         | string |
| `status`             | string |

## Example

```typescript
import type { RelationshipActivationOutcome } from "";

// TODO: Update the object below with actual values
const example = {
  activationIntentId: null,
  subscriptionId: null,
  evidenceId: null,
  status: null,
} satisfies RelationshipActivationOutcome;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipActivationOutcome;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
