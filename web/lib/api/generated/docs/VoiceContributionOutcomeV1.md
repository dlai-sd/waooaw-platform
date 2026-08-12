# VoiceContributionOutcomeV1

## Properties

| Name                     | Type                                                    |
| ------------------------ | ------------------------------------------------------- |
| `schemaVersion`          | string                                                  |
| `sessionId`              | string                                                  |
| `contributionId`         | string                                                  |
| `state`                  | [VoiceContributionStateV1](VoiceContributionStateV1.md) |
| `evidenceReference`      | string                                                  |
| `reconciliationRequired` | boolean                                                 |
| `outcomeAt`              | Date                                                    |

## Example

```typescript
import type { VoiceContributionOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  sessionId: null,
  contributionId: null,
  state: null,
  evidenceReference: null,
  reconciliationRequired: null,
  outcomeAt: null,
} satisfies VoiceContributionOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VoiceContributionOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
