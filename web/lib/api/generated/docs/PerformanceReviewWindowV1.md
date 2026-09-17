# PerformanceReviewWindowV1

## Properties

| Name                        | Type                                                                      |
| --------------------------- | ------------------------------------------------------------------------- |
| `reviewId`                  | string                                                                    |
| `agentInstanceId`           | string                                                                    |
| `skillId`                   | string                                                                    |
| `skillVersion`              | string                                                                    |
| `revision`                  | number                                                                    |
| `policyVersion`             | string                                                                    |
| `periodStart`               | Date                                                                      |
| `periodEnd`                 | Date                                                                      |
| `sourceVersions`            | { [key: string]: string; }                                                |
| `workDelivery`              | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `agentQuality`              | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `constitutionalPerformance` | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `commercialUsage`           | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `customerBusinessOutcome`   | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `customerAssessment`        | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `trustAutonomy`             | [PerformanceReviewDimensionV1](PerformanceReviewDimensionV1.md)           |
| `recommendation`            | [PerformanceReviewRecommendationV1](PerformanceReviewRecommendationV1.md) |
| `evidenceId`                | string                                                                    |
| `createdAt`                 | Date                                                                      |
| `customerResponse`          | [PerformanceReviewResponseV1](PerformanceReviewResponseV1.md)             |
| `reassessmentRequired`      | boolean                                                                   |

## Example

```typescript
import type { PerformanceReviewWindowV1 } from "";

// TODO: Update the object below with actual values
const example = {
  reviewId: null,
  agentInstanceId: null,
  skillId: null,
  skillVersion: null,
  revision: null,
  policyVersion: null,
  periodStart: null,
  periodEnd: null,
  sourceVersions: null,
  workDelivery: null,
  agentQuality: null,
  constitutionalPerformance: null,
  commercialUsage: null,
  customerBusinessOutcome: null,
  customerAssessment: null,
  trustAutonomy: null,
  recommendation: null,
  evidenceId: null,
  createdAt: null,
  customerResponse: null,
  reassessmentRequired: null,
} satisfies PerformanceReviewWindowV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PerformanceReviewWindowV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
