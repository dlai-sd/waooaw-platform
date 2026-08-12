# RelationshipTrial

## Properties

| Name        | Type   |
| ----------- | ------ |
| `trialId`   | string |
| `startsAt`  | Date   |
| `expiresAt` | Date   |
| `status`    | string |

## Example

```typescript
import type { RelationshipTrial } from "";

// TODO: Update the object below with actual values
const example = {
  trialId: null,
  startsAt: null,
  expiresAt: null,
  status: null,
} satisfies RelationshipTrial;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipTrial;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
