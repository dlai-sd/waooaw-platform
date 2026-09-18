# PerformanceReviewDimensionV1

## Properties

| Name                | Type                                                      |
| ------------------- | --------------------------------------------------------- |
| `state`             | string                                                    |
| `summary`           | string                                                    |
| `evidenceState`     | [RelationshipEvidenceState](RelationshipEvidenceState.md) |
| `attributionLimits` | string                                                    |
| `uncertainty`       | string                                                    |

## Example

```typescript
import type { PerformanceReviewDimensionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  state: null,
  summary: null,
  evidenceState: null,
  attributionLimits: null,
  uncertainty: null,
} satisfies PerformanceReviewDimensionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PerformanceReviewDimensionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
