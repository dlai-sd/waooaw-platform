# ConversationSubmissionV1

## Properties

| Name                  | Type                                                      |
| --------------------- | --------------------------------------------------------- |
| `schemaVersion`       | [ConversationSchemaVersion](ConversationSchemaVersion.md) |
| `outcome`             | string                                                    |
| `message`             | [ConversationMessageV1](ConversationMessageV1.md)         |
| `executionId`         | string                                                    |
| `authoritativeCursor` | string                                                    |
| `replayed`            | boolean                                                   |

## Example

```typescript
import type { ConversationSubmissionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  outcome: null,
  message: null,
  executionId: null,
  authoritativeCursor: null,
  replayed: null,
} satisfies ConversationSubmissionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationSubmissionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
