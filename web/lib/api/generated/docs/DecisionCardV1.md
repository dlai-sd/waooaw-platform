# DecisionCardV1

## Properties

| Name              | Type                                                                   |
| ----------------- | ---------------------------------------------------------------------- |
| `schemaVersion`   | [ConversationSchemaVersion](ConversationSchemaVersion.md)              |
| `cardId`          | string                                                                 |
| `cardType`        | string                                                                 |
| `owner`           | string                                                                 |
| `state`           | string                                                                 |
| `effect`          | string                                                                 |
| `commands`        | [Array&lt;ConversationCardCommandV1&gt;](ConversationCardCommandV1.md) |
| `decisionState`   | string                                                                 |
| `authorityImpact` | string                                                                 |
| `alternatives`    | [Array&lt;DecisionAlternativeV1&gt;](DecisionAlternativeV1.md)         |

## Example

```typescript
import type { DecisionCardV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  cardId: null,
  cardType: null,
  owner: null,
  state: null,
  effect: null,
  commands: null,
  decisionState: null,
  authorityImpact: null,
  alternatives: null,
} satisfies DecisionCardV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DecisionCardV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
