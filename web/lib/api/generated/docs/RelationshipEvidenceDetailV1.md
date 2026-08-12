# RelationshipEvidenceDetailV1

A retained proof record remains a 200 response after operational payload erasure. In that case payloadState is ERASED, payloadReference is absent, and erasedAt is present. Unknown or unauthorized proof IDs remain privacy-safe 404 responses.

## Properties

| Name               | Type                                                                        |
| ------------------ | --------------------------------------------------------------------------- |
| `schemaVersion`    | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md) |
| `evidenceId`       | string                                                                      |
| `subject`          | string                                                                      |
| `state`            | [RelationshipEvidenceState](RelationshipEvidenceState.md)                   |
| `completeness`     | string                                                                      |
| `payloadState`     | string                                                                      |
| `payloadReference` | string                                                                      |
| `erasedAt`         | Date                                                                        |

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
  payloadState: null,
  payloadReference: null,
  erasedAt: null,
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
