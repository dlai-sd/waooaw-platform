# IdentityProviderLinkRequestV1

## Properties

| Name                         | Type                                                  |
| ---------------------------- | ----------------------------------------------------- |
| `schemaVersion`              | string                                                |
| `provider`                   | [IdentityProviderClassV1](IdentityProviderClassV1.md) |
| `stepUpTransactionReference` | string                                                |

## Example

```typescript
import type { IdentityProviderLinkRequestV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  provider: null,
  stepUpTransactionReference: null,
} satisfies IdentityProviderLinkRequestV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityProviderLinkRequestV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
