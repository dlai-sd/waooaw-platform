# RelationshipAttentionItemV1

## Properties

| Name                    | Type   |
| ----------------------- | ------ |
| `attentionItemId`       | string |
| `reason`                | string |
| `consequence`           | string |
| `authoritativeSequence` | number |

## Example

```typescript
import type { RelationshipAttentionItemV1 } from "";

// TODO: Update the object below with actual values
const example = {
  attentionItemId: null,
  reason: null,
  consequence: null,
  authoritativeSequence: null,
} satisfies RelationshipAttentionItemV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipAttentionItemV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
