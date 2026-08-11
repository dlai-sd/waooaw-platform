# RelationshipWorkspaceV1

## Properties

| Name                  | Type                                                                             |
| --------------------- | -------------------------------------------------------------------------------- |
| `schemaVersion`       | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md)      |
| `relationshipId`      | string                                                                           |
| `workspaceVersion`    | string                                                                           |
| `snapshotState`       | [RelationshipWorkspaceSnapshotState](RelationshipWorkspaceSnapshotState.md)      |
| `currencyState`       | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md)      |
| `authoritativeCursor` | string                                                                           |
| `producedAt`          | Date                                                                             |
| `context`             | [RelationshipContextV1](RelationshipContextV1.md)                                |
| `sections`            | [Array&lt;RelationshipWorkspaceSectionV1&gt;](RelationshipWorkspaceSectionV1.md) |

## Example

```typescript
import type { RelationshipWorkspaceV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  workspaceVersion: null,
  snapshotState: null,
  currencyState: null,
  authoritativeCursor: null,
  producedAt: null,
  context: null,
  sections: null,
} satisfies RelationshipWorkspaceV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipWorkspaceV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
