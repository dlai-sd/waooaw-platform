# RelationshipContractJourney

## Properties

| Name                | Type                                                          |
| ------------------- | ------------------------------------------------------------- |
| `contractId`        | string                                                        |
| `version`           | number                                                        |
| `contractHash`      | string                                                        |
| `document`          | object                                                        |
| `relationshipState` | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `acceptanceState`   | string                                                        |
| `paymentState`      | string                                                        |
| `activationState`   | string                                                        |

## Example

```typescript
import type { RelationshipContractJourney } from "";

// TODO: Update the object below with actual values
const example = {
  contractId: null,
  version: null,
  contractHash: null,
  document: null,
  relationshipState: null,
  acceptanceState: null,
  paymentState: null,
  activationState: null,
} satisfies RelationshipContractJourney;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipContractJourney;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
