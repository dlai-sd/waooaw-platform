# ConversationDeltaPayloadV1

## Properties

| Name           | Type    |
| -------------- | ------- |
| `contentIndex` | number  |
| `appendText`   | string  |
| `partial`      | boolean |

## Example

```typescript
import type { ConversationDeltaPayloadV1 } from "";

// TODO: Update the object below with actual values
const example = {
  contentIndex: null,
  appendText: null,
  partial: null,
} satisfies ConversationDeltaPayloadV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationDeltaPayloadV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
