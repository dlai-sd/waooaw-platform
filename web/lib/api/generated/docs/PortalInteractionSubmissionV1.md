# PortalInteractionSubmissionV1

## Properties

| Name                  | Type                                                        |
| --------------------- | ----------------------------------------------------------- |
| `schemaVersion`       | [ConversationSchemaVersion](ConversationSchemaVersion.md)   |
| `scope`               | string                                                      |
| `outcome`             | string                                                      |
| `customerMessage`     | [PortalInteractionMessageV1](PortalInteractionMessageV1.md) |
| `guideMessage`        | [PortalInteractionMessageV1](PortalInteractionMessageV1.md) |
| `authoritativeCursor` | string                                                      |
| `replayed`            | boolean                                                     |

## Example

```typescript
import type { PortalInteractionSubmissionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  scope: null,
  outcome: null,
  customerMessage: null,
  guideMessage: null,
  authoritativeCursor: null,
  replayed: null,
} satisfies PortalInteractionSubmissionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PortalInteractionSubmissionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
