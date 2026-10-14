# CustomerEngagementProgressV1

## Properties

| Name                        | Type                                                                         |
| --------------------------- | ---------------------------------------------------------------------------- |
| `schemaVersion`             | string                                                                       |
| `relationshipId`            | string                                                                       |
| `projectionVersion`         | string                                                                       |
| `projectionContractVersion` | string                                                                       |
| `generatedAt`               | Date                                                                         |
| `projectionSources`         | [Array&lt;EngagementSourceProvenanceV1&gt;](EngagementSourceProvenanceV1.md) |
| `lifecycleStage`            | string                                                                       |
| `headline`                  | string                                                                       |
| `summary`                   | string                                                                       |
| `selectedFocus`             | [WorkspaceFocusRefV1](WorkspaceFocusRefV1.md)                                |
| `items`                     | [Array&lt;EngagementProgressItemV1&gt;](EngagementProgressItemV1.md)         |
| `availableFocuses`          | [Array&lt;WorkspaceFocusRefV1&gt;](WorkspaceFocusRefV1.md)                   |

## Example

```typescript
import type { CustomerEngagementProgressV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  projectionVersion: null,
  projectionContractVersion: null,
  generatedAt: null,
  projectionSources: null,
  lifecycleStage: null,
  headline: null,
  summary: null,
  selectedFocus: null,
  items: null,
  availableFocuses: null,
} satisfies CustomerEngagementProgressV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CustomerEngagementProgressV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
