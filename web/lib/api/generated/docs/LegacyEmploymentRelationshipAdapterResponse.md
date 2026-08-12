# LegacyEmploymentRelationshipAdapterResponse

## Properties

| Name                | Type                                                          |
| ------------------- | ------------------------------------------------------------- |
| `id`                | string                                                        |
| `relationshipId`    | string                                                        |
| `professionalId`    | string                                                        |
| `professionalType`  | string                                                        |
| `state`             | string                                                        |
| `relationshipState` | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `createdAt`         | Date                                                          |
| `updatedAt`         | Date                                                          |

## Example

```typescript
import type { LegacyEmploymentRelationshipAdapterResponse } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  relationshipId: null,
  professionalId: null,
  professionalType: null,
  state: null,
  relationshipState: null,
  createdAt: null,
  updatedAt: null,
} satisfies LegacyEmploymentRelationshipAdapterResponse;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as LegacyEmploymentRelationshipAdapterResponse;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
