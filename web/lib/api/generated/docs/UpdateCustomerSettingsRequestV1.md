# UpdateCustomerSettingsRequestV1

## Properties

| Name                      | Type                                                          |
| ------------------------- | ------------------------------------------------------------- |
| `schemaVersion`           | [CustomerPortalSchemaVersion](CustomerPortalSchemaVersion.md) |
| `locale`                  | string                                                        |
| `theme`                   | string                                                        |
| `timestampVisibility`     | string                                                        |
| `notificationPreferences` | [NotificationPreferences](NotificationPreferences.md)         |

## Example

```typescript
import type { UpdateCustomerSettingsRequestV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  locale: null,
  theme: null,
  timestampVisibility: null,
  notificationPreferences: null,
} satisfies UpdateCustomerSettingsRequestV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as UpdateCustomerSettingsRequestV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
