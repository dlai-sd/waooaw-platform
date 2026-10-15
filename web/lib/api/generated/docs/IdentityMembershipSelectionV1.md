# IdentityMembershipSelectionV1

## Properties

| Name            | Type                                            |
| --------------- | ----------------------------------------------- |
| `schemaVersion` | string                                          |
| `membership`    | [IdentityMembershipV1](IdentityMembershipV1.md) |
| `validatedAt`   | Date                                            |

## Example

```typescript
import type { IdentityMembershipSelectionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  membership: null,
  validatedAt: null,
} satisfies IdentityMembershipSelectionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityMembershipSelectionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
