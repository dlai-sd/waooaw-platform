# RelationshipCommandOutcomeV1

## Properties

| Name             | Type                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------ |
| `schemaVersion`  | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md)          |
| `commandId`      | string                                                                               |
| `commandKind`    | [RelationshipCommandKindV1](RelationshipCommandKindV1.md)                            |
| `status`         | [RelationshipCommandStatus](RelationshipCommandStatus.md)                            |
| `relationshipId` | string                                                                               |
| `steps`          | [Array&lt;RelationshipCommandOutcomeStepV1&gt;](RelationshipCommandOutcomeStepV1.md) |
| `resolvedAt`     | Date                                                                                 |

## Example

```typescript
import type { RelationshipCommandOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  commandId: null,
  commandKind: null,
  status: null,
  relationshipId: null,
  steps: null,
  resolvedAt: null,
} satisfies RelationshipCommandOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipCommandOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
