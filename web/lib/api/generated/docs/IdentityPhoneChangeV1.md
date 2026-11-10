# IdentityPhoneChangeV1

## Properties

| Name                           | Type    |
| ------------------------------ | ------- |
| `challengeId`                  | string  |
| `state`                        | string  |
| `maskedMobile`                 | string  |
| `expiresAt`                    | Date    |
| `relationshipApprovalRequired` | boolean |

## Example

```typescript
import type { IdentityPhoneChangeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  challengeId: null,
  state: null,
  maskedMobile: null,
  expiresAt: null,
  relationshipApprovalRequired: null,
} satisfies IdentityPhoneChangeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityPhoneChangeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
