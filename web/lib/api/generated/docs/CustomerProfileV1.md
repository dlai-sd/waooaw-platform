# CustomerProfileV1

## Properties

| Name                      | Type                                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------- |
| `schemaVersion`           | [CustomerPortalSchemaVersion](CustomerPortalSchemaVersion.md)                                        |
| `displayName`             | string                                                                                               |
| `organizationDisplayName` | string                                                                                               |
| `email`                   | string                                                                                               |
| `emailVerified`           | boolean                                                                                              |
| `mobileVerified`          | boolean                                                                                              |
| `activeRole`              | string                                                                                               |
| `switchableAccounts`      | [Array&lt;CustomerProfileV1SwitchableAccountsInner&gt;](CustomerProfileV1SwitchableAccountsInner.md) |
| `updatedAt`               | Date                                                                                                 |

## Example

```typescript
import type { CustomerProfileV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  displayName: null,
  organizationDisplayName: null,
  email: null,
  emailVerified: null,
  mobileVerified: null,
  activeRole: null,
  switchableAccounts: null,
  updatedAt: null,
} satisfies CustomerProfileV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CustomerProfileV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
