# RelationshipChannelBinding

## Properties

| Name             | Type                                                                          |
| ---------------- | ----------------------------------------------------------------------------- |
| `bindingId`      | string                                                                        |
| `channel`        | [RelationshipChannel](RelationshipChannel.md)                                 |
| `conversationId` | string                                                                        |
| `assurance`      | [RelationshipAuthenticationAssurance](RelationshipAuthenticationAssurance.md) |
| `status`         | [RelationshipChannelBindingStatus](RelationshipChannelBindingStatus.md)       |

## Example

```typescript
import type { RelationshipChannelBinding } from "";

// TODO: Update the object below with actual values
const example = {
  bindingId: null,
  channel: null,
  conversationId: null,
  assurance: null,
  status: null,
} satisfies RelationshipChannelBinding;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipChannelBinding;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
