# RelationshipBusinessOutcomeV1

## Properties

| Name                | Type                                                          |
| ------------------- | ------------------------------------------------------------- |
| `outcomeId`         | string                                                        |
| `label`             | string                                                        |
| `skillId`           | string                                                        |
| `goalId`            | string                                                        |
| `measure`           | string                                                        |
| `frequency`         | string                                                        |
| `reviewPeriod`      | string                                                        |
| `status`            | [RelationshipOutcomeStatusV1](RelationshipOutcomeStatusV1.md) |
| `evidenceState`     | [RelationshipEvidenceState](RelationshipEvidenceState.md)     |
| `attributionBasis`  | string                                                        |
| `attributionLimits` | string                                                        |
| `uncertainty`       | string                                                        |
| `agentPerformance`  | [OutcomeInterpretationV1](OutcomeInterpretationV1.md)         |
| `externalOutcome`   | [OutcomeInterpretationV1](OutcomeInterpretationV1.md)         |

## Example

```typescript
import type { RelationshipBusinessOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeId: null,
  label: null,
  skillId: null,
  goalId: null,
  measure: null,
  frequency: null,
  reviewPeriod: null,
  status: null,
  evidenceState: null,
  attributionBasis: null,
  attributionLimits: null,
  uncertainty: null,
  agentPerformance: null,
  externalOutcome: null,
} satisfies RelationshipBusinessOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipBusinessOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
