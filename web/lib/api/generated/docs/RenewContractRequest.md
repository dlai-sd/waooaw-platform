# RenewContractRequest

## Properties

| Name            | Type                                         |
| --------------- | -------------------------------------------- |
| `decisionSpace` | [DecisionSpaceInput](DecisionSpaceInput.md)  |
| `goals`         | [Array&lt;BusinessGoal&gt;](BusinessGoal.md) |
| `reviewCadence` | [ReviewCadence](ReviewCadence.md)            |

## Example

```typescript
import type { RenewContractRequest } from "";

// TODO: Update the object below with actual values
const example = {
  decisionSpace: null,
  goals: null,
  reviewCadence: null,
} satisfies RenewContractRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RenewContractRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
