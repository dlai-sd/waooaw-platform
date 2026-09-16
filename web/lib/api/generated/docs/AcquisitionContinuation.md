# AcquisitionContinuation

## Properties

| Name             | Type    |
| ---------------- | ------- |
| `relationshipId` | string  |
| `intent`         | string  |
| `status`         | string  |
| `resumePath`     | string  |
| `replayed`       | boolean |

## Example

```typescript
import type { AcquisitionContinuation } from "";

// TODO: Update the object below with actual values
const example = {
  relationshipId: null,
  intent: null,
  status: null,
  resumePath: null,
  replayed: null,
} satisfies AcquisitionContinuation;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AcquisitionContinuation;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
