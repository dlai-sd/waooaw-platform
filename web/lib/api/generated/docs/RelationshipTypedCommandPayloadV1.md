# RelationshipTypedCommandPayloadV1

## Properties

| Name                 | Type   |
| -------------------- | ------ |
| `commandKind`        | string |
| `planId`             | string |
| `resultId`           | string |
| `reason`             | string |
| `goalId`             | string |
| `amendment`          | string |
| `replacement`        | string |
| `boundaryId`         | string |
| `acknowledgmentText` | string |
| `amountInrPaise`     | number |
| `pacingChoice`       | string |

## Example

```typescript
import type { RelationshipTypedCommandPayloadV1 } from "";

// TODO: Update the object below with actual values
const example = {
  commandKind: null,
  planId: null,
  resultId: null,
  reason: null,
  goalId: null,
  amendment: null,
  replacement: null,
  boundaryId: null,
  acknowledgmentText: null,
  amountInrPaise: null,
  pacingChoice: null,
} satisfies RelationshipTypedCommandPayloadV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipTypedCommandPayloadV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
