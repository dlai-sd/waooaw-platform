# VoiceContributionSessionV1

## Properties

| Name              | Type                                                    |
| ----------------- | ------------------------------------------------------- |
| `schemaVersion`   | string                                                  |
| `sessionId`       | string                                                  |
| `relationshipId`  | string                                                  |
| `state`           | [VoiceContributionStateV1](VoiceContributionStateV1.md) |
| `locale`          | string                                                  |
| `confidenceBand`  | [VoiceConfidenceBandV1](VoiceConfidenceBandV1.md)       |
| `durationSeconds` | number                                                  |
| `audioSizeBytes`  | number                                                  |
| `allowedCommands` | Array&lt;string&gt;                                     |
| `createdAt`       | Date                                                    |
| `updatedAt`       | Date                                                    |

## Example

```typescript
import type { VoiceContributionSessionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  sessionId: null,
  relationshipId: null,
  state: null,
  locale: null,
  confidenceBand: null,
  durationSeconds: null,
  audioSizeBytes: null,
  allowedCommands: null,
  createdAt: null,
  updatedAt: null,
} satisfies VoiceContributionSessionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VoiceContributionSessionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
