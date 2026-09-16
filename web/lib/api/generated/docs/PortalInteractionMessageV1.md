# PortalInteractionMessageV1

## Properties

| Name              | Type                                                                         |
| ----------------- | ---------------------------------------------------------------------------- |
| `schemaVersion`   | [ConversationSchemaVersion](ConversationSchemaVersion.md)                    |
| `messageId`       | string                                                                       |
| `sequence`        | number                                                                       |
| `actor`           | string                                                                       |
| `content`         | [Array&lt;ConversationTextBlockV1&gt;](ConversationTextBlockV1.md)           |
| `capabilities`    | [Array&lt;PortalNavigationCapabilityV1&gt;](PortalNavigationCapabilityV1.md) |
| `currentSurface`  | [PortalInteractionSurfaceV1](PortalInteractionSurfaceV1.md)                  |
| `clientMessageId` | string                                                                       |
| `acceptedAt`      | Date                                                                         |

## Example

```typescript
import type { PortalInteractionMessageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  messageId: null,
  sequence: null,
  actor: null,
  content: null,
  capabilities: null,
  currentSurface: null,
  clientMessageId: null,
  acceptedAt: null,
} satisfies PortalInteractionMessageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PortalInteractionMessageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
