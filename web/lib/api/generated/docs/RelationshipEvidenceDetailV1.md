# RelationshipEvidenceDetailV1

## Properties

| Name            | Type                                                                        |
| --------------- | --------------------------------------------------------------------------- |
| `schemaVersion` | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md) |
| `evidenceId`    | string                                                                      |
| `subject`       | string                                                                      |
| `state`         | [RelationshipEvidenceState](RelationshipEvidenceState.md)                   |
| `completeness`  | string                                                                      |

## Example

```typescript
import type { RelationshipEvidenceDetailV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  evidenceId: null,
  subject: null,
  state: null,
  completeness: null,
} satisfies RelationshipEvidenceDetailV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipEvidenceDetailV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
