# RelationshipWorkspaceProvenanceV1

## Properties

| Name                      | Type   |
| ------------------------- | ------ |
| `owner`                   | string |
| `sourceProjectionVersion` | string |
| `producedAt`              | Date   |
| `validUntil`              | Date   |

## Example

```typescript
import type { RelationshipWorkspaceProvenanceV1 } from "";

// TODO: Update the object below with actual values
const example = {
  owner: null,
  sourceProjectionVersion: null,
  producedAt: null,
  validUntil: null,
} satisfies RelationshipWorkspaceProvenanceV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkspaceProvenanceV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
