# IdentityMembershipV1

## Properties

| Name                  | Type                                                      |
| --------------------- | --------------------------------------------------------- |
| `membershipReference` | string                                                    |
| `tenantReference`     | string                                                    |
| `role`                | string                                                    |
| `state`               | [IdentityMembershipStateV1](IdentityMembershipStateV1.md) |
| `selectionEligible`   | boolean                                                   |

## Example

```typescript
import type { IdentityMembershipV1 } from "";

// TODO: Update the object below with actual values
const example = {
  membershipReference: null,
  tenantReference: null,
  role: null,
  state: null,
  selectionEligible: null,
} satisfies IdentityMembershipV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityMembershipV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
