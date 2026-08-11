# RelationshipWorkspaceChangeEntryV1

## Properties

| Name               | Type                                                                    |
| ------------------ | ----------------------------------------------------------------------- |
| `sequence`         | number                                                                  |
| `sectionType`      | [RelationshipWorkspaceSectionType](RelationshipWorkspaceSectionType.md) |
| `workspaceVersion` | string                                                                  |
| `occurredAt`       | Date                                                                    |

## Example

```typescript
import type { RelationshipWorkspaceChangeEntryV1 } from "";

// TODO: Update the object below with actual values
const example = {
  sequence: null,
  sectionType: null,
  workspaceVersion: null,
  occurredAt: null,
} satisfies RelationshipWorkspaceChangeEntryV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkspaceChangeEntryV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
