# RelationshipConfigurationStepV1

## Properties

| Name                      | Type                                                                            |
| ------------------------- | ------------------------------------------------------------------------------- |
| `stepKey`                 | string                                                                          |
| `label`                   | string                                                                          |
| `state`                   | [RelationshipConfigurationStepStateV1](RelationshipConfigurationStepStateV1.md) |
| `summary`                 | string                                                                          |
| `confirmedContextVersion` | string                                                                          |
| `continuationTarget`      | [CustomerPortalDestinationV1](CustomerPortalDestinationV1.md)                   |

## Example

```typescript
import type { RelationshipConfigurationStepV1 } from "";

// TODO: Update the object below with actual values
const example = {
  stepKey: null,
  label: null,
  state: null,
  summary: null,
  confirmedContextVersion: null,
  continuationTarget: null,
} satisfies RelationshipConfigurationStepV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipConfigurationStepV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
