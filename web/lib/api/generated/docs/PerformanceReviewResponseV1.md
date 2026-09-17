# PerformanceReviewResponseV1

## Properties

| Name               | Type                                                                          |
| ------------------ | ----------------------------------------------------------------------------- |
| `responseId`       | string                                                                        |
| `reviewId`         | string                                                                        |
| `reviewRevision`   | number                                                                        |
| `responseRevision` | number                                                                        |
| `decision`         | [PerformanceReviewCustomerDecisionV1](PerformanceReviewCustomerDecisionV1.md) |
| `reason`           | string                                                                        |
| `evidenceId`       | string                                                                        |
| `occurredAt`       | Date                                                                          |

## Example

```typescript
import type { PerformanceReviewResponseV1 } from "";

// TODO: Update the object below with actual values
const example = {
  responseId: null,
  reviewId: null,
  reviewRevision: null,
  responseRevision: null,
  decision: null,
  reason: null,
  evidenceId: null,
  occurredAt: null,
} satisfies PerformanceReviewResponseV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PerformanceReviewResponseV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
