# ActivateRelationshipHandoffRequest

## Properties

| Name                   | Type   |
| ---------------------- | ------ |
| `targetConversationId` | string |
| `correlationId`        | string |

## Example

```typescript
import type { ActivateRelationshipHandoffRequest } from "";

// TODO: Update the object below with actual values
const example = {
  targetConversationId: null,
  correlationId: null,
} satisfies ActivateRelationshipHandoffRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ActivateRelationshipHandoffRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
