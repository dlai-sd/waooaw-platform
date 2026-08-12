# LegacyHireAgentResponse

## Properties

| Name                      | Type   |
| ------------------------- | ------ |
| `hireId`                  | string |
| `contractId`              | string |
| `relationshipId`          | string |
| `professionalType`        | string |
| `skillId`                 | string |
| `decisionSpaceVersion`    | string |
| `approvedBudgetInrPaise`  | number |
| `billingCycleAnchorDay`   | string |
| `proRataBillingStartDate` | Date   |
| `hiredAt`                 | Date   |
| `state`                   | string |

## Example

```typescript
import type { LegacyHireAgentResponse } from "";

// TODO: Update the object below with actual values
const example = {
  hireId: null,
  contractId: null,
  relationshipId: null,
  professionalType: null,
  skillId: null,
  decisionSpaceVersion: null,
  approvedBudgetInrPaise: null,
  billingCycleAnchorDay: null,
  proRataBillingStartDate: null,
  hiredAt: null,
  state: null,
} satisfies LegacyHireAgentResponse;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as LegacyHireAgentResponse;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
