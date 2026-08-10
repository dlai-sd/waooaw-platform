# ConversationTimelinePageV1

## Properties

| Name                      | Type                                                           |
| ------------------------- | -------------------------------------------------------------- |
| `schemaVersion`           | [ConversationSchemaVersion](ConversationSchemaVersion.md)      |
| `relationshipId`          | string                                                         |
| `items`                   | [Array&lt;ConversationMessageV1&gt;](ConversationMessageV1.md) |
| `authoritativeCursor`     | string                                                         |
| `nextCursor`              | string                                                         |
| `unreadBoundaryMessageId` | string                                                         |
| `hasMore`                 | boolean                                                        |
| `serverTime`              | Date                                                           |

## Example

```typescript
import type { ConversationTimelinePageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  items: null,
  authoritativeCursor: null,
  nextCursor: null,
  unreadBoundaryMessageId: null,
  hasMore: null,
  serverTime: null,
} satisfies ConversationTimelinePageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationTimelinePageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
