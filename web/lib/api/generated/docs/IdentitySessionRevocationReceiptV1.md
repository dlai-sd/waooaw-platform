# IdentitySessionRevocationReceiptV1

## Properties

| Name                  | Type    |
| --------------------- | ------- |
| `schemaVersion`       | string  |
| `revocationReference` | string  |
| `scope`               | string  |
| `state`               | string  |
| `recordedAt`          | Date    |
| `replayed`            | boolean |

## Example

```typescript
import type { IdentitySessionRevocationReceiptV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  revocationReference: null,
  scope: null,
  state: null,
  recordedAt: null,
  replayed: null,
} satisfies IdentitySessionRevocationReceiptV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as IdentitySessionRevocationReceiptV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
