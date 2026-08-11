# RelationshipEvidenceSummaryV1

## Properties

| Name         | Type                                                      |
| ------------ | --------------------------------------------------------- |
| `evidenceId` | string                                                    |
| `subject`    | string                                                    |
| `state`      | [RelationshipEvidenceState](RelationshipEvidenceState.md) |

## Example

```typescript
import type { RelationshipEvidenceSummaryV1 } from "";

// TODO: Update the object below with actual values
const example = {
  evidenceId: null,
  subject: null,
  state: null,
} satisfies RelationshipEvidenceSummaryV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipEvidenceSummaryV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
