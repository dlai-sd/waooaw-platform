# RelationshipEvidenceExportOutcomeV1

A COMPLETED outcome exposes a BP-signed HTTPS URL for a UTF-8 JSON document with media type application/vnd.waooaw.relationship-evidence+json;version=1.0. The URL is bound to the authenticated tenant, relationship, participant, and role projection and expires no later than 15 minutes after completion. PENDING, PARTIAL, UNKNOWN, REJECTED, CONFLICT, and BLOCKED outcomes contain no download fields.

## Properties

| Name                     | Type                                                                            |
| ------------------------ | ------------------------------------------------------------------------------- |
| `schemaVersion`          | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md)     |
| `exportId`               | string                                                                          |
| `status`                 | [RelationshipCommandStatus](RelationshipCommandStatus.md)                       |
| `downloadAvailableUntil` | Date                                                                            |
| `downloadUrl`            | string                                                                          |
| `mediaType`              | string                                                                          |
| `documentSha256`         | string                                                                          |
| `document`               | [RelationshipEvidenceExportDocumentV1](RelationshipEvidenceExportDocumentV1.md) |

## Example

```typescript
import type { RelationshipEvidenceExportOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  exportId: null,
  status: null,
  downloadAvailableUntil: null,
  downloadUrl: null,
  mediaType: null,
  documentSha256: null,
  document: null,
} satisfies RelationshipEvidenceExportOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipEvidenceExportOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
