# RelationshipWorkspaceChangePageV1

## Properties

| Name                  | Type                                                                                     |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `schemaVersion`       | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md)              |
| `relationshipId`      | string                                                                                   |
| `authoritativeCursor` | string                                                                                   |
| `nextCursor`          | string                                                                                   |
| `items`               | [Array&lt;RelationshipWorkspaceChangeEntryV1&gt;](RelationshipWorkspaceChangeEntryV1.md) |

## Example

```typescript
import type { RelationshipWorkspaceChangePageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  authoritativeCursor: null,
  nextCursor: null,
  items: null,
} satisfies RelationshipWorkspaceChangePageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkspaceChangePageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
