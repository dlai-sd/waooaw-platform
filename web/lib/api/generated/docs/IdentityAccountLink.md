# IdentityAccountLink

## Properties

| Name                | Type                                                    |
| ------------------- | ------------------------------------------------------- |
| `linkId`            | string                                                  |
| `state`             | [IdentityAccountLinkState](IdentityAccountLinkState.md) |
| `requiredAssurance` | [IdentityAssuranceLevel](IdentityAssuranceLevel.md)     |
| `maskedMobile`      | string                                                  |
| `expiresAt`         | Date                                                    |
| `updatedAt`         | Date                                                    |

## Example

```typescript
import type { IdentityAccountLink } from "";

// TODO: Update the object below with actual values
const example = {
  linkId: null,
  state: null,
  requiredAssurance: null,
  maskedMobile: null,
  expiresAt: null,
  updatedAt: null,
} satisfies IdentityAccountLink;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityAccountLink;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
