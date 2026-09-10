# RelationshipEvaluationV1

## Properties

| Name                  | Type                                                                           |
| --------------------- | ------------------------------------------------------------------------------ |
| `relationshipId`      | string                                                                         |
| `lifecycleState`      | [EmploymentRelationshipState](EmploymentRelationshipState.md)                  |
| `interviewState`      | string                                                                         |
| `context`             | Array&lt;object&gt;                                                            |
| `nextContextQuestion` | string                                                                         |
| `trial`               | object                                                                         |
| `goals`               | Array&lt;object&gt;                                                            |
| `skills`              | [Array&lt;RelationshipEvaluationSkillV1&gt;](RelationshipEvaluationSkillV1.md) |
| `decisionSpace`       | object                                                                         |

## Example

```typescript
import type { RelationshipEvaluationV1 } from "";

// TODO: Update the object below with actual values
const example = {
  relationshipId: null,
  lifecycleState: null,
  interviewState: null,
  context: null,
  nextContextQuestion: null,
  trial: null,
  goals: null,
  skills: null,
  decisionSpace: null,
} satisfies RelationshipEvaluationV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipEvaluationV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
