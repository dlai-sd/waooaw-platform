# IdentityManagedSession

## Properties

| Name             | Type                                                |
| ---------------- | --------------------------------------------------- |
| `sessionId`      | string                                              |
| `issuedAt`       | Date                                                |
| `lastSeenAt`     | Date                                                |
| `expiresAt`      | Date                                                |
| `assuranceLevel` | [IdentityAssuranceLevel](IdentityAssuranceLevel.md) |
| `provider`       | string                                              |
| `deviceLabel`    | string                                              |
| `current`        | boolean                                             |

## Example

```typescript
import type { IdentityManagedSession } from "";

// TODO: Update the object below with actual values
const example = {
  sessionId: null,
  issuedAt: null,
  lastSeenAt: null,
  expiresAt: null,
  assuranceLevel: null,
  provider: null,
  deviceLabel: null,
  current: null,
} satisfies IdentityManagedSession;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityManagedSession;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
