# ConversationCardCommandV1

## Properties

| Name                | Type   |
| ------------------- | ------ |
| `commandId`         | string |
| `label`             | string |
| `availability`      | string |
| `unavailableReason` | string |

## Example

```typescript
import type { ConversationCardCommandV1 } from "";

// TODO: Update the object below with actual values
const example = {
  commandId: null,
  label: null,
  availability: null,
  unavailableReason: null,
} satisfies ConversationCardCommandV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationCardCommandV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
