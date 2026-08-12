# DecisionSpaceInput

## Properties

| Name                      | Type                                                  |
| ------------------------- | ----------------------------------------------------- |
| `executionModel`          | [ExecutionModel](ExecutionModel.md)                   |
| `professionalType`        | string                                                |
| `authorizedActions`       | [Array&lt;ActionDefinition&gt;](ActionDefinition.md)  |
| `prohibitedActions`       | [Array&lt;ActionDefinition&gt;](ActionDefinition.md)  |
| `alwaysAskActions`        | [Array&lt;ActionDefinition&gt;](ActionDefinition.md)  |
| `budgetConstraints`       | [BudgetConstraints](BudgetConstraints.md)             |
| `creativeStandardProfile` | [CreativeStandardProfile](CreativeStandardProfile.md) |
| `paasParameters`          | [PAASParameters](PAASParameters.md)                   |

## Example

```typescript
import type { DecisionSpaceInput } from "";

// TODO: Update the object below with actual values
const example = {
  executionModel: null,
  professionalType: null,
  authorizedActions: null,
  prohibitedActions: null,
  alwaysAskActions: null,
  budgetConstraints: null,
  creativeStandardProfile: null,
  paasParameters: null,
} satisfies DecisionSpaceInput;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DecisionSpaceInput;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
