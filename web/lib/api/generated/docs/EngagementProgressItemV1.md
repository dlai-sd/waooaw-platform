# EngagementProgressItemV1

## Properties

| Name            | Type                                                            |
| --------------- | --------------------------------------------------------------- |
| `itemId`        | string                                                          |
| `title`         | string                                                          |
| `state`         | string                                                          |
| `owner`         | string                                                          |
| `required`      | boolean                                                         |
| `truth`         | [EngagementTruthDimensionsV1](EngagementTruthDimensionsV1.md)   |
| `provenance`    | [EngagementSourceProvenanceV1](EngagementSourceProvenanceV1.md) |
| `updatedAt`     | Date                                                            |
| `summary`       | string                                                          |
| `blockedEffect` | string                                                          |
| `nextAction`    | [EngagementNextActionV1](EngagementNextActionV1.md)             |

## Example

```typescript
import type { EngagementProgressItemV1 } from "";

// TODO: Update the object below with actual values
const example = {
  itemId: null,
  title: null,
  state: null,
  owner: null,
  required: null,
  truth: null,
  provenance: null,
  updatedAt: null,
  summary: null,
  blockedEffect: null,
  nextAction: null,
} satisfies EngagementProgressItemV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EngagementProgressItemV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
