# ReleaseEmploymentRelationshipStopRequest

## Properties

| Name                           | Type   |
| ------------------------------ | ------ |
| `originatingStopEvidenceId`    | string |
| `originatingStopCorrelationId` | string |
| `releaseConfirmation`          | string |
| `releaseJustification`         | string |
| `targetState`                  | string |
| `correlationId`                | string |

## Example

```typescript
import type { ReleaseEmploymentRelationshipStopRequest } from "";

// TODO: Update the object below with actual values
const example = {
  originatingStopEvidenceId: null,
  originatingStopCorrelationId: null,
  releaseConfirmation: null,
  releaseJustification: null,
  targetState: null,
  correlationId: null,
} satisfies ReleaseEmploymentRelationshipStopRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ReleaseEmploymentRelationshipStopRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
