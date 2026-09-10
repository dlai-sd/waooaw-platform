# RelationshipEvaluationSkillV1

## Properties

| Name                  | Type   |
| --------------------- | ------ |
| `configurationId`     | string |
| `skillId`             | string |
| `skillVersion`        | string |
| `subjectVersion`      | string |
| `applicability`       | string |
| `applicabilityReason` | string |
| `authorityState`      | string |
| `status`              | string |

## Example

```typescript
import type { RelationshipEvaluationSkillV1 } from "";

// TODO: Update the object below with actual values
const example = {
  configurationId: null,
  skillId: null,
  skillVersion: null,
  subjectVersion: null,
  applicability: null,
  applicabilityReason: null,
  authorityState: null,
  status: null,
} satisfies RelationshipEvaluationSkillV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipEvaluationSkillV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
