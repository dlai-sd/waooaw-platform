# RelationshipGoalV1

## Properties

| Name                  | Type                                                                            |
| --------------------- | ------------------------------------------------------------------------------- |
| `goalId`              | string                                                                          |
| `goalVersion`         | string                                                                          |
| `skillId`             | string                                                                          |
| `skillLabel`          | string                                                                          |
| `measure`             | string                                                                          |
| `frequency`           | string                                                                          |
| `baseline`            | string                                                                          |
| `attributionBoundary` | string                                                                          |
| `verificationStatus`  | [RelationshipGoalVerificationStatusV1](RelationshipGoalVerificationStatusV1.md) |
| `customerVerifiedAt`  | Date                                                                            |
| `status`              | [RelationshipGoalStatusV1](RelationshipGoalStatusV1.md)                         |
| `amendedFromGoalId`   | string                                                                          |
| `supersededByGoalId`  | string                                                                          |
| `evidenceState`       | [RelationshipEvidenceState](RelationshipEvidenceState.md)                       |

## Example

```typescript
import type { RelationshipGoalV1 } from "";

// TODO: Update the object below with actual values
const example = {
  goalId: null,
  goalVersion: null,
  skillId: null,
  skillLabel: null,
  measure: null,
  frequency: null,
  baseline: null,
  attributionBoundary: null,
  verificationStatus: null,
  customerVerifiedAt: null,
  status: null,
  amendedFromGoalId: null,
  supersededByGoalId: null,
  evidenceState: null,
} satisfies RelationshipGoalV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipGoalV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
