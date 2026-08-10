# ConversationStreamEventV1

## Properties

| Name             | Type                                                              |
| ---------------- | ----------------------------------------------------------------- |
| `schemaVersion`  | [ConversationSchemaVersion](ConversationSchemaVersion.md)         |
| `eventId`        | string                                                            |
| `eventType`      | [ConversationStreamEventType](ConversationStreamEventType.md)     |
| `relationshipId` | string                                                            |
| `sequence`       | number                                                            |
| `messageId`      | string                                                            |
| `executionId`    | string                                                            |
| `occurredAt`     | Date                                                              |
| `data`           | [ConversationStreamEventV1Data](ConversationStreamEventV1Data.md) |

## Example

```typescript
import type { ConversationStreamEventV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  eventId: null,
  eventType: null,
  relationshipId: null,
  sequence: null,
  messageId: null,
  executionId: null,
  occurredAt: null,
  data: null,
} satisfies ConversationStreamEventV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationStreamEventV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
