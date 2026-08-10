# DeliverableCardV1

## Properties

| Name               | Type                                                                   |
| ------------------ | ---------------------------------------------------------------------- |
| `schemaVersion`    | [ConversationSchemaVersion](ConversationSchemaVersion.md)              |
| `cardId`           | string                                                                 |
| `cardType`         | string                                                                 |
| `owner`            | string                                                                 |
| `state`            | string                                                                 |
| `effect`           | string                                                                 |
| `commands`         | [Array&lt;ConversationCardCommandV1&gt;](ConversationCardCommandV1.md) |
| `title`            | string                                                                 |
| `deliverableState` | string                                                                 |

## Example

```typescript
import type { DeliverableCardV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  cardId: null,
  cardType: null,
  owner: null,
  state: null,
  effect: null,
  commands: null,
  title: null,
  deliverableState: null,
} satisfies DeliverableCardV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DeliverableCardV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
