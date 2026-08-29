# IdentitySession

## Properties

| Name                 | Type                                                                      |
| -------------------- | ------------------------------------------------------------------------- |
| `accountReference`   | string                                                                    |
| `roles`              | Set&lt;string&gt;                                                         |
| `capabilities`       | Set&lt;string&gt;                                                         |
| `assuranceLevel`     | [IdentityAssuranceLevel](IdentityAssuranceLevel.md)                       |
| `authenticationPath` | [IdentitySessionAuthenticationPath](IdentitySessionAuthenticationPath.md) |
| `emailVerified`      | boolean                                                                   |
| `mobileVerified`     | boolean                                                                   |
| `authenticatedAt`    | Date                                                                      |
| `expiresAt`          | Date                                                                      |
| `nextAction`         | string                                                                    |

## Example

```typescript
import type { IdentitySession } from "";

// TODO: Update the object below with actual values
const example = {
  accountReference: null,
  roles: null,
  capabilities: null,
  assuranceLevel: null,
  authenticationPath: null,
  emailVerified: null,
  mobileVerified: null,
  authenticatedAt: null,
  expiresAt: null,
  nextAction: null,
} satisfies IdentitySession;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentitySession;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
