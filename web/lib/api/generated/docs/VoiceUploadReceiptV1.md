# VoiceUploadReceiptV1

## Properties

| Name            | Type                                                    |
| --------------- | ------------------------------------------------------- |
| `schemaVersion` | string                                                  |
| `sessionId`     | string                                                  |
| `state`         | [VoiceContributionStateV1](VoiceContributionStateV1.md) |
| `receiptId`     | string                                                  |
| `acceptedAt`    | Date                                                    |

## Example

```typescript
import type { VoiceUploadReceiptV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  sessionId: null,
  state: null,
  receiptId: null,
  acceptedAt: null,
} satisfies VoiceUploadReceiptV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VoiceUploadReceiptV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
