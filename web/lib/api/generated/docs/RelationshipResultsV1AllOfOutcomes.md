# RelationshipResultsV1AllOfOutcomes

## Properties

| Name               | Type   |
| ------------------ | ------ |
| `outcomeId`        | string |
| `agentInstanceId`  | string |
| `skillId`          | string |
| `skillVersion`     | string |
| `invocationId`     | string |
| `revision`         | number |
| `label`            | string |
| `attributionBasis` | string |
| `updatedAt`        | Date   |

## Example

```typescript
import type { RelationshipResultsV1AllOfOutcomes } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeId: null,
  agentInstanceId: null,
  skillId: null,
  skillVersion: null,
  invocationId: null,
  revision: null,
  label: null,
  attributionBasis: null,
  updatedAt: null,
} satisfies RelationshipResultsV1AllOfOutcomes;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipResultsV1AllOfOutcomes;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
