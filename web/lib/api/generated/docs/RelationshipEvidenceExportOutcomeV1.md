# RelationshipEvidenceExportOutcomeV1

## Properties

| Name                     | Type                                                                        |
| ------------------------ | --------------------------------------------------------------------------- |
| `schemaVersion`          | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md) |
| `exportId`               | string                                                                      |
| `status`                 | [RelationshipCommandStatus](RelationshipCommandStatus.md)                   |
| `downloadAvailableUntil` | Date                                                                        |

## Example

```typescript
import type { RelationshipEvidenceExportOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  exportId: null,
  status: null,
  downloadAvailableUntil: null,
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
