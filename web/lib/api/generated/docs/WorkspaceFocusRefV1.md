# WorkspaceFocusRefV1

## Properties

| Name              | Type   |
| ----------------- | ------ |
| `schemaVersion`   | string |
| `focusToken`      | string |
| `destination`     | string |
| `label`           | string |
| `accessibleLabel` | string |
| `issuedAt`        | Date   |
| `expiresAt`       | Date   |

## Example

```typescript
import type { WorkspaceFocusRefV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  focusToken: null,
  destination: null,
  label: null,
  accessibleLabel: null,
  issuedAt: null,
  expiresAt: null,
} satisfies WorkspaceFocusRefV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WorkspaceFocusRefV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
