# WorkspaceFocusResolutionV1

## Properties

| Name               | Type   |
| ------------------ | ------ |
| `schemaVersion`    | string |
| `relationshipId`   | string |
| `destination`      | string |
| `canonicalRoute`   | string |
| `resolvedAt`       | Date   |
| `authorityVersion` | string |
| `subjectRef`       | string |
| `subjectVersion`   | string |

## Example

```typescript
import type { WorkspaceFocusResolutionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  destination: null,
  canonicalRoute: null,
  resolvedAt: null,
  authorityVersion: null,
  subjectRef: null,
  subjectVersion: null,
} satisfies WorkspaceFocusResolutionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WorkspaceFocusResolutionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
