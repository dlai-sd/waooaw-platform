# RelationshipWorkPageV1AllOfItems

## Properties

| Name              | Type   |
| ----------------- | ------ |
| `itemId`          | string |
| `agentInstanceId` | string |
| `skillId`         | string |
| `skillVersion`    | string |
| `invocationId`    | string |
| `revision`        | number |
| `state`           | string |
| `effect`          | string |
| `resultRef`       | string |
| `updatedAt`       | Date   |

## Example

```typescript
import type { RelationshipWorkPageV1AllOfItems } from "";

// TODO: Update the object below with actual values
const example = {
  itemId: null,
  agentInstanceId: null,
  skillId: null,
  skillVersion: null,
  invocationId: null,
  revision: null,
  state: null,
  effect: null,
  resultRef: null,
  updatedAt: null,
} satisfies RelationshipWorkPageV1AllOfItems;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkPageV1AllOfItems;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
