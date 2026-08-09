# IdentityRegistration

## Properties

| Name                 | Type                                                          |
| -------------------- | ------------------------------------------------------------- |
| `registrationId`     | string                                                        |
| `state`              | [IdentityRegistrationState](IdentityRegistrationState.md)     |
| `nextAction`         | [IdentityNextAction](IdentityNextAction.md)                   |
| `authenticationPath` | [IdentityAuthenticationPath](IdentityAuthenticationPath.md)   |
| `providerLabel`      | string                                                        |
| `emailVerified`      | boolean                                                       |
| `mobileVerified`     | boolean                                                       |
| `maskedEmail`        | string                                                        |
| `maskedMobile`       | string                                                        |
| `profile`            | [IdentityRegistrationProfile](IdentityRegistrationProfile.md) |
| `expiresAt`          | Date                                                          |
| `updatedAt`          | Date                                                          |

## Example

```typescript
import type { IdentityRegistration } from "";

// TODO: Update the object below with actual values
const example = {
  registrationId: null,
  state: null,
  nextAction: null,
  authenticationPath: null,
  providerLabel: null,
  emailVerified: null,
  mobileVerified: null,
  maskedEmail: null,
  maskedMobile: null,
  profile: null,
  expiresAt: null,
  updatedAt: null,
} satisfies IdentityRegistration;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityRegistration;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
