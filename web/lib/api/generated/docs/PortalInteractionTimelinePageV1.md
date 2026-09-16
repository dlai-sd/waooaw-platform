# PortalInteractionTimelinePageV1

## Properties

| Name                  | Type                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| `schemaVersion`       | [ConversationSchemaVersion](ConversationSchemaVersion.md)                |
| `scope`               | string                                                                   |
| `contextId`           | string                                                                   |
| `items`               | [Array&lt;PortalInteractionMessageV1&gt;](PortalInteractionMessageV1.md) |
| `authoritativeCursor` | string                                                                   |
| `nextCursor`          | string                                                                   |
| `hasMore`             | boolean                                                                  |
| `serverTime`          | Date                                                                     |

## Example

```typescript
import type { PortalInteractionTimelinePageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  scope: null,
  contextId: null,
  items: null,
  authoritativeCursor: null,
  nextCursor: null,
  hasMore: null,
  serverTime: null,
} satisfies PortalInteractionTimelinePageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as PortalInteractionTimelinePageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
