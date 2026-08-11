# AmendGoalPayloadV1

## Properties

| Name          | Type   |
| ------------- | ------ |
| `commandKind` | string |
| `goalId`      | string |
| `amendment`   | string |

## Example

```typescript
import type { AmendGoalPayloadV1 } from "";

// TODO: Update the object below with actual values
const example = {
  commandKind: null,
  goalId: null,
  amendment: null,
} satisfies AmendGoalPayloadV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AmendGoalPayloadV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
