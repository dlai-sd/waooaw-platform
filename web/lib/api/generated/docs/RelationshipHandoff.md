# RelationshipHandoff

## Properties

| Name                   | Type                                                        |
| ---------------------- | ----------------------------------------------------------- |
| `handoffId`            | string                                                      |
| `relationshipId`       | string                                                      |
| `status`               | [RelationshipHandoffStatus](RelationshipHandoffStatus.md)   |
| `sourceBinding`        | [RelationshipChannelBinding](RelationshipChannelBinding.md) |
| `targetBinding`        | [RelationshipChannelBinding](RelationshipChannelBinding.md) |
| `continuityEnvelope`   | [NeutralContinuityEnvelope](NeutralContinuityEnvelope.md)   |
| `replayed`             | boolean                                                     |
| `resolutionEvidenceId` | string                                                      |
| `committedAt`          | Date                                                        |
| `resolutionReason`     | string                                                      |

## Example

```typescript
import type { RelationshipHandoff } from "";

// TODO: Update the object below with actual values
const example = {
  handoffId: null,
  relationshipId: null,
  status: null,
  sourceBinding: null,
  targetBinding: null,
  continuityEnvelope: null,
  replayed: null,
  resolutionEvidenceId: null,
  committedAt: null,
  resolutionReason: null,
} satisfies RelationshipHandoff;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipHandoff;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
