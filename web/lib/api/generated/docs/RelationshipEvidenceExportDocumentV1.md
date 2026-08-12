# RelationshipEvidenceExportDocumentV1

Canonical logical content of the downloadable UTF-8 JSON artifact. Object members are serialized in RFC 8785 canonical order for documentSha256. Items use the same current participant-role projection and erased-payload behavior as the Evidence Reader.

## Properties

| Name             | Type                                                                         |
| ---------------- | ---------------------------------------------------------------------------- |
| `schemaVersion`  | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md)  |
| `exportId`       | string                                                                       |
| `relationshipId` | string                                                                       |
| `generatedAt`    | Date                                                                         |
| `evidence`       | [Array&lt;RelationshipEvidenceDetailV1&gt;](RelationshipEvidenceDetailV1.md) |

## Example

```typescript
import type { RelationshipEvidenceExportDocumentV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  exportId: null,
  relationshipId: null,
  generatedAt: null,
  evidence: null,
} satisfies RelationshipEvidenceExportDocumentV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipEvidenceExportDocumentV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
