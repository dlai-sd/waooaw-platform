# RelationshipContextV1

## Properties

| Name              | Type                                                              |
| ----------------- | ----------------------------------------------------------------- |
| `relationshipId`  | string                                                            |
| `lifecycleState`  | [EmploymentRelationshipState](EmploymentRelationshipState.md)     |
| `policySelection` | [RelationshipPolicySelectionV1](RelationshipPolicySelectionV1.md) |

## Example

```typescript
import type { RelationshipContextV1 } from "";

// TODO: Update the object below with actual values
const example = {
  relationshipId: null,
  lifecycleState: null,
  policySelection: null,
} satisfies RelationshipContextV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipContextV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
