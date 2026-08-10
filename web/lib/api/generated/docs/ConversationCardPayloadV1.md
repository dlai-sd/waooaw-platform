# ConversationCardPayloadV1

## Properties

| Name   | Type                                                        |
| ------ | ----------------------------------------------------------- |
| `card` | [GovernedConversationCardV1](GovernedConversationCardV1.md) |

## Example

```typescript
import type { ConversationCardPayloadV1 } from "";

// TODO: Update the object below with actual values
const example = {
  card: null,
} satisfies ConversationCardPayloadV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationCardPayloadV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
