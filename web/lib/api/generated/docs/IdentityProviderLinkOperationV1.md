# IdentityProviderLinkOperationV1

## Properties

| Name                 | Type                                                  |
| -------------------- | ----------------------------------------------------- |
| `schemaVersion`      | string                                                |
| `operationReference` | string                                                |
| `linkReference`      | string                                                |
| `command`            | string                                                |
| `provider`           | [IdentityProviderClassV1](IdentityProviderClassV1.md) |
| `state`              | string                                                |
| `expiresAt`          | Date                                                  |
| `replayed`           | boolean                                               |

## Example

```typescript
import type { IdentityProviderLinkOperationV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  operationReference: null,
  linkReference: null,
  command: null,
  provider: null,
  state: null,
  expiresAt: null,
  replayed: null,
} satisfies IdentityProviderLinkOperationV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as IdentityProviderLinkOperationV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
