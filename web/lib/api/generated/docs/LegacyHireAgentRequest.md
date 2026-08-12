# LegacyHireAgentRequest

## Properties

| Name                     | Type   |
| ------------------------ | ------ |
| `contractId`             | string |
| `professionalType`       | string |
| `skillId`                | string |
| `decisionSpaceVersion`   | string |
| `approvedBudgetInrPaise` | number |
| `billingCycleAnchorDay`  | string |

## Example

```typescript
import type { LegacyHireAgentRequest } from "";

// TODO: Update the object below with actual values
const example = {
  contractId: null,
  professionalType: null,
  skillId: null,
  decisionSpaceVersion: null,
  approvedBudgetInrPaise: null,
  billingCycleAnchorDay: null,
} satisfies LegacyHireAgentRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as LegacyHireAgentRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
