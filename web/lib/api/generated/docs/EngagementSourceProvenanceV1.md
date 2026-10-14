# EngagementSourceProvenanceV1

## Properties

| Name                              | Type   |
| --------------------------------- | ------ |
| `sourceOwner`                     | string |
| `sourceSubjectRef`                | string |
| `sourceVersion`                   | string |
| `sourceContractVersion`           | string |
| `producedAt`                      | Date   |
| `lastAuthoritativeConfirmationAt` | Date   |
| `freshness`                       | string |
| `evidenceState`                   | string |
| `evidenceRef`                     | string |
| `observedAt`                      | Date   |
| `validUntil`                      | Date   |

## Example

```typescript
import type { EngagementSourceProvenanceV1 } from "";

// TODO: Update the object below with actual values
const example = {
  sourceOwner: null,
  sourceSubjectRef: null,
  sourceVersion: null,
  sourceContractVersion: null,
  producedAt: null,
  lastAuthoritativeConfirmationAt: null,
  freshness: null,
  evidenceState: null,
  evidenceRef: null,
  observedAt: null,
  validUntil: null,
} satisfies EngagementSourceProvenanceV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EngagementSourceProvenanceV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
