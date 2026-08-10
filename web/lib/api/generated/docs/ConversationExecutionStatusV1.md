# ConversationExecutionStatusV1

## Properties

| Name               | Type                                                            |
| ------------------ | --------------------------------------------------------------- |
| `schemaVersion`    | [ConversationSchemaVersion](ConversationSchemaVersion.md)       |
| `executionId`      | string                                                          |
| `state`            | [ConversationProcessingState](ConversationProcessingState.md)   |
| `partial`          | boolean                                                         |
| `completionReason` | [ConversationCompletionReason](ConversationCompletionReason.md) |
| `updatedAt`        | Date                                                            |

## Example

```typescript
import type { ConversationExecutionStatusV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  executionId: null,
  state: null,
  partial: null,
  completionReason: null,
  updatedAt: null,
} satisfies ConversationExecutionStatusV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationExecutionStatusV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
