# AcquisitionIntent

## Properties

| Name                  | Type    |
| --------------------- | ------- |
| `acquisitionIntentId` | string  |
| `intent`              | string  |
| `status`              | string  |
| `contractDocumentUri` | string  |
| `contractHash`        | string  |
| `expiresAt`           | Date    |
| `replayed`            | boolean |

## Example

```typescript
import type { AcquisitionIntent } from "";

// TODO: Update the object below with actual values
const example = {
  acquisitionIntentId: null,
  intent: null,
  status: null,
  contractDocumentUri: null,
  contractHash: null,
  expiresAt: null,
  replayed: null,
} satisfies AcquisitionIntent;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AcquisitionIntent;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
