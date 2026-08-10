# ConversationStreamEventV1Data

## Properties

| Name                  | Type                                                        |
| --------------------- | ----------------------------------------------------------- |
| `contentIndex`        | number                                                      |
| `appendText`          | string                                                      |
| `partial`             | boolean                                                     |
| `message`             | [ConversationMessageV1](ConversationMessageV1.md)           |
| `card`                | [GovernedConversationCardV1](GovernedConversationCardV1.md) |
| `code`                | string                                                      |
| `retryable`           | boolean                                                     |
| `reason`              | string                                                      |
| `authoritativeCursor` | string                                                      |
| `serverTime`          | Date                                                        |

## Example

```typescript
import type { ConversationStreamEventV1Data } from "";

// TODO: Update the object below with actual values
const example = {
  contentIndex: null,
  appendText: null,
  partial: null,
  message: null,
  card: null,
  code: null,
  retryable: null,
  reason: null,
  authoritativeCursor: null,
  serverTime: null,
} satisfies ConversationStreamEventV1Data;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationStreamEventV1Data;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
