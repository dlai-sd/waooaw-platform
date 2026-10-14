# CustomerEngagementAdmissionOutcomeV1

## Properties

| Name               | Type                                          |
| ------------------ | --------------------------------------------- |
| `schemaVersion`    | string                                        |
| `relationshipId`   | string                                        |
| `agentInstanceId`  | string                                        |
| `conversationId`   | string                                        |
| `lifecycleState`   | string                                        |
| `engagementIntent` | string                                        |
| `replayed`         | boolean                                       |
| `admittedAt`       | Date                                          |
| `evidenceRef`      | string                                        |
| `resumeFocus`      | [WorkspaceFocusRefV1](WorkspaceFocusRefV1.md) |

## Example

```typescript
import type { CustomerEngagementAdmissionOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  agentInstanceId: null,
  conversationId: null,
  lifecycleState: null,
  engagementIntent: null,
  replayed: null,
  admittedAt: null,
  evidenceRef: null,
  resumeFocus: null,
} satisfies CustomerEngagementAdmissionOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as CustomerEngagementAdmissionOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
