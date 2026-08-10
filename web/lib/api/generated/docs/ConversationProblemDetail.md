# ConversationProblemDetail

Privacy-safe RFC 9457 problem; submitted content and internal dependency detail are never echoed

## Properties

| Name                | Type                                                  |
| ------------------- | ----------------------------------------------------- |
| `type`              | string                                                |
| `title`             | string                                                |
| `status`            | number                                                |
| `code`              | [ConversationProblemCode](ConversationProblemCode.md) |
| `correlationId`     | string                                                |
| `retryAfterSeconds` | number                                                |

## Example

```typescript
import type { ConversationProblemDetail } from "";

// TODO: Update the object below with actual values
const example = {
  type: null,
  title: null,
  status: null,
  code: null,
  correlationId: null,
  retryAfterSeconds: null,
} satisfies ConversationProblemDetail;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationProblemDetail;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
