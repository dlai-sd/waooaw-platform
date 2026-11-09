# ConversationReconciliationOutcomeV1

## Properties

| Name                | Type                                                      |
| ------------------- | --------------------------------------------------------- |
| `schemaVersion`     | [ConversationSchemaVersion](ConversationSchemaVersion.md) |
| `executionId`       | string                                                    |
| `state`             | string                                                    |
| `nextAction`        | string                                                    |
| `projectionVersion` | number                                                    |
| `replayed`          | boolean                                                   |

## Example

```typescript
import type { ConversationReconciliationOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  executionId: null,
  state: null,
  nextAction: null,
  projectionVersion: null,
  replayed: null,
} satisfies ConversationReconciliationOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ConversationReconciliationOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
