# IdentityProvider

## Properties

| Name                 | Type                                                        |
| -------------------- | ----------------------------------------------------------- |
| `id`                 | string                                                      |
| `displayName`        | string                                                      |
| `authenticationPath` | [IdentityAuthenticationPath](IdentityAuthenticationPath.md) |
| `availability`       | string                                                      |
| `unavailableReason`  | string                                                      |

## Example

```typescript
import type { IdentityProvider } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  displayName: null,
  authenticationPath: null,
  availability: null,
  unavailableReason: null,
} satisfies IdentityProvider;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityProvider;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
