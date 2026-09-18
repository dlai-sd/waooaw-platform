# RespondToPerformanceReviewPayloadV1

## Properties

| Name             | Type                                                                          |
| ---------------- | ----------------------------------------------------------------------------- |
| `commandKind`    | string                                                                        |
| `reviewId`       | string                                                                        |
| `reviewRevision` | number                                                                        |
| `decision`       | [PerformanceReviewCustomerDecisionV1](PerformanceReviewCustomerDecisionV1.md) |
| `reason`         | string                                                                        |

## Example

```typescript
import type { RespondToPerformanceReviewPayloadV1 } from "";

// TODO: Update the object below with actual values
const example = {
  commandKind: null,
  reviewId: null,
  reviewRevision: null,
  decision: null,
  reason: null,
} satisfies RespondToPerformanceReviewPayloadV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RespondToPerformanceReviewPayloadV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
