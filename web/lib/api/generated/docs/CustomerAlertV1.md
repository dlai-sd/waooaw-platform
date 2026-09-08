# CustomerAlertV1

## Properties

| Name              | Type                                                          |
| ----------------- | ------------------------------------------------------------- |
| `alertId`         | string                                                        |
| `version`         | string                                                        |
| `alertType`       | string                                                        |
| `severity`        | string                                                        |
| `source`          | string                                                        |
| `relationshipId`  | string                                                        |
| `occurredAt`      | Date                                                          |
| `dueMeaning`      | string                                                        |
| `readState`       | [CustomerAlertReadStateV1](CustomerAlertReadStateV1.md)       |
| `destination`     | [CustomerPortalDestinationV1](CustomerPortalDestinationV1.md) |
| `availableAction` | string                                                        |

## Example

```typescript
import type { CustomerAlertV1 } from "";

// TODO: Update the object below with actual values
const example = {
  alertId: null,
  version: null,
  alertType: null,
  severity: null,
  source: null,
  relationshipId: null,
  occurredAt: null,
  dueMeaning: null,
  readState: null,
  destination: null,
  availableAction: null,
} satisfies CustomerAlertV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CustomerAlertV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
