# IdentityMobileStatus

## Properties

| Name             | Type    |
| ---------------- | ------- |
| `mobileVerified` | boolean |
| `maskedMobile`   | string  |
| `verifiedAt`     | Date    |

## Example

```typescript
import type { IdentityMobileStatus } from "";

// TODO: Update the object below with actual values
const example = {
  mobileVerified: null,
  maskedMobile: null,
  verifiedAt: null,
} satisfies IdentityMobileStatus;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityMobileStatus;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
