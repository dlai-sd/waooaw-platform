# IdentitySessionRevocation

## Properties

| Name           | Type   |
| -------------- | ------ |
| `scope`        | string |
| `revokedCount` | number |

## Example

```typescript
import type { IdentitySessionRevocation } from "";

// TODO: Update the object below with actual values
const example = {
  scope: null,
  revokedCount: null,
} satisfies IdentitySessionRevocation;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentitySessionRevocation;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
